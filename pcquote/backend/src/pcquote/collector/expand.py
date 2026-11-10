"""Catalog expansion: find new products on public Danawa category and search pages, ported from buildmate (pipeline/expand.mjs).

Discovered product codes are checked against the product page's JSON-LD SKU, the
category and the required specs before they enter the registry. Search progress is
saved so an interrupted pass resumes where it stopped.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from urllib.parse import urlencode

from pcquote.collector.client import SourceClient, utc_iso
from pcquote.collector.parse import benchmark_name, parse_popularity, parse_product, parse_search, valid_discovered
from pcquote.collector.store import PipelineStore, advisory_lock
from pcquote.collector.window import collection_window

PROGRESS_INTERVAL = 10.0  # seconds between discovery-state saves (always saved at the end)


def can_advance(cursor: dict | None, config: dict) -> bool:
    if not cursor or cursor.get("done"):
        return False
    limit = config.get("maxPagesPerQuery")
    return limit is None or cursor["page"] <= limit


def collect_product(client: SourceClient, product: dict, allow_missing_price: bool = False) -> dict:
    from pcquote.collector.parse import SourceError
    from pcquote.collector.jsre import js

    if not js(r"^\d+$").search(str(product.get("danawaPcode") or "")):
        raise SourceError("등록된 상품 코드가 없습니다.", "unmapped")
    page = client.text(f"https://prod.danawa.com/info/?pcode={product['danawaPcode']}")
    return parse_product(page["text"], product, page, allow_missing_price=allow_missing_price)


def _search_url(query: str, page: int, sort: str | None = None) -> str:
    params = {"query": query, "page": str(page)}
    if sort:
        params["sort"] = sort
    return "https://search.danawa.com/?" + urlencode(params)


def _epoch(value) -> float:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def expand_catalog(store: PipelineStore, client: SourceClient, *, daily: bool = False, on_progress=print, now=None) -> dict:
    with advisory_lock("expansion"):
        config = store.doc("discovery")
        registry = store.doc("products")
        state = store.doc("discovery-state", {"queries": {}, "candidates": {}})
        state.setdefault("queries", {})
        state.setdefault("candidates", {})
        if state.get("parserVersion") != 3:
            for c in state["candidates"].values():
                if c.get("status") == "rejected":
                    c["status"] = "pending"
            state["parserVersion"] = 3
        if state.get("scopeVersion") != 4:
            if not state.get("scopeVersion") or state["scopeVersion"] < 3:
                state["queries"] = {}
            for c in state["candidates"].values():
                if c.get("status") == "rejected":
                    c["status"] = "pending"
            state["scopeVersion"] = 4
        state["collectionWindow"] = {**collection_window(now, config.get("releaseWindowYears") or 2), "complete": False}
        known = {str(p.get("danawaPcode")): p for p in registry["products"]}
        summary = {"pages": 0, "discovered": 0, "added": 0, "rejected": 0, "errors": 0}
        last_save = [0.0]

        def progress(force: bool = False):
            state["updatedAt"] = utc_iso()
            state["summary"] = summary
            if force or time.monotonic() - last_save[0] >= PROGRESS_INTERVAL:
                store.put_doc("discovery-state", state)
                last_save[0] = time.monotonic()
            on_progress({"stage": "expand", **summary, "registered": len(registry["products"])})

        def remember(candidate: dict, category: str, url: str):
            if candidate["pcode"] not in known and candidate["pcode"] not in state["candidates"]:
                state["candidates"][candidate["pcode"]] = {**candidate, "category": category, "status": "pending", "searchUrl": url}
                summary["discovered"] += 1

        for seed in config["queries"]:
            key = f"{seed['category']}:{seed['query']}"
            cursor = state["queries"].get(key) or {"page": 1, "seen": []}
            if seed.get("source") == "category-index":
                if not cursor.get("done") or daily:
                    try:
                        url = f"https://prod.danawa.com/list/?cate={seed['categoryCode']}"
                        page = client.text(url)
                        found = parse_search(page["text"])
                        for record in parse_popularity(page["text"], seed["category"], url, page["fetchedAt"]):
                            existing = known.get(record["pcode"])
                            if existing:
                                existing["popularity"] = record["popularity"]
                                store.update_popularity(existing["id"], record["popularity"])
                            elif record["pcode"] in state["candidates"]:
                                state["candidates"][record["pcode"]]["popularity"] = record["popularity"]
                            candidate = next((c for c in found if c["pcode"] == record["pcode"]), None)
                            if candidate:
                                candidate["popularity"] = record["popularity"]
                        if not found:
                            raise ValueError("카테고리 공개 HTML에서 상품을 확인할 수 없습니다.")
                        summary["pages"] += 1
                        for candidate in found:
                            remember(candidate, seed["category"], url)
                        cursor.update(done=True, indexOnly=True, coverageLimited=True, stopReason="public-category-index")
                    except Exception as e:  # noqa: BLE001 — recorded on the cursor, the pass continues
                        summary["errors"] += 1
                        cursor["error"] = str(e)
                state["queries"][key] = cursor
                progress()
                continue
            if daily:
                try:
                    url = _search_url(seed["query"], 1, "dateDESC")
                    page = client.text(url)
                    summary["pages"] += 1
                    for candidate in parse_search(page["text"]):
                        remember(candidate, seed["category"], url)
                except Exception as e:  # noqa: BLE001
                    summary["errors"] += 1
                    cursor["error"] = str(e)
            if cursor.get("done"):
                state["queries"][key] = cursor
                progress()
                continue
            step = 0
            while step < (config.get("pagesPerPass") or 1) and can_advance(cursor, config):
                step += 1
                try:
                    url = _search_url(seed["query"], cursor["page"])
                    page = client.text(url)
                    found = parse_search(page["text"])
                    fresh = [p for p in found if p["pcode"] not in cursor["seen"]]
                    summary["pages"] += 1
                    if not fresh:
                        if not found and cursor["page"] == 1:
                            raise ValueError("공개 검색 페이지의 결과를 확인하지 못했습니다. 수집 완료로 처리하지 않습니다.")
                        cursor["done"] = True
                        cursor["stopReason"] = "repeated-page" if found else "empty-page"
                        break
                    for candidate in fresh:
                        cursor["seen"].append(candidate["pcode"])
                        remember(candidate, seed["category"], url)
                    cursor["page"] += 1
                except Exception as e:  # noqa: BLE001
                    summary["errors"] += 1
                    cursor["error"] = str(e)
                    break
            state["queries"][key] = cursor
            progress()

        cutoff = state["collectionWindow"]["start"][:7]

        def priority(c):
            month = c.get("listingMonth")
            return (0 if month >= cutoff else 2) if month else 1

        for candidate in sorted(state["candidates"].values(), key=lambda c: (priority(c), -int(c["pcode"]))):
            if candidate["pcode"] in known or candidate.get("status") == "rejected":
                continue
            if candidate.get("status") == "failed" and time.time() - _epoch(candidate.get("at") or 0) < 3600:
                continue
            product = {"id": "dw-" + candidate["pcode"], "category": candidate["category"], "name": candidate["name"],
                       "danawaPcode": candidate["pcode"], "discoveredAt": state["updatedAt"] if "updatedAt" in state else None,
                       "discoverySource": candidate.get("searchUrl")}
            try:
                observation = collect_product(client, product, allow_missing_price=True)
                part = observation["part"]
                candidate["listingMonth"] = part["listingMonth"]
                candidate["dateStatus"] = "registration-month" if part["listingMonth"] else "unknown"
                if not valid_discovered(part):
                    candidate["status"] = "rejected"
                    candidate["reason"] = "품목 불일치 또는 필수 스펙 누락"
                    summary["rejected"] += 1
                else:
                    product["name"] = part["name"]
                    bench = benchmark_name(product["category"], product["name"])
                    if bench is not None:
                        product["benchmarkName"] = bench
                    same_chip = next((p for p in registry["products"] if bench and p.get("benchmarkName") == bench), None)
                    if same_chip:
                        product["compatibilityCpuId"] = same_chip.get("compatibilityCpuId") or same_chip["id"]
                    if candidate.get("popularity"):
                        product["popularity"] = candidate["popularity"]
                    part.update(product)
                    if not observation["price"]:
                        store.record_product(part)
                    if not observation["price"] or store.accept_product(observation):
                        registry["products"].append(product)
                        known[candidate["pcode"]] = product
                        candidate["status"] = "collected"
                        candidate["priceStatus"] = "priced" if observation["price"] else "unavailable"
                        summary["added"] += 1
                        store.put_doc("products", registry)
                    else:
                        candidate["status"] = "failed"
                        candidate["reason"] = "가격 검수 필요"
            except Exception as e:  # noqa: BLE001
                candidate["status"] = "failed"
                candidate["reason"] = str(e)
                summary["errors"] += 1
            candidate["at"] = utc_iso()
            progress()
        store.put_doc("products", registry)
        progress(force=True)
        return summary
