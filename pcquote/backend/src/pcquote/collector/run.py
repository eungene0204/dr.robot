"""Collection run: prices and specs for every registered product, Blender benchmarks, then the catalog snapshot.

Ported from buildmate (pipeline/run.mjs, publish.mjs). The snapshot is imported into
the server's parts table when the collector owns the catalog (after cutover);
before that it is stored as the ``collector/catalog-shadow`` document for comparison.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

from pcquote import importer
from pcquote.collector import blender
from pcquote.collector.client import SourceClient, utc_iso
from pcquote.collector.expand import collect_product, expand_catalog
from pcquote.collector.parse import SourceError, benchmark_name
from pcquote.collector.store import Busy, PgPageCache, PipelineStore, advisory_lock
from pcquote.collector.window import window_coverage
from pcquote.db import get_document, put_document
from pcquote.policy import benchmark_state, hydrate_snapshot, price_state

DATA_DIR = Path(os.environ.get("PCQUOTE_DATA_DIR", Path(__file__).resolve().parents[3] / "data"))
OWNER_DOC = "catalog-owner"

POLICY = {"priceMaxAgeHours": 24, "benchmarkMaxAgeDays": 45, "benchmarkMinSamples": 3, "scoreLabel": "Blender 렌더링 지수",
          "scoreMethod": "동일 버전의 monster+junkshop+classroom 합산 점수 중앙값. CPU 9600X=100 / GPU RTX 5060 Ti=100. 게임 FPS/AI 처리량 아님.",
          "shipping": "대부분 배송비 미확인: 표시가에 미포함", "stock": "가격비교에 등록된 판매 제안. 실재고 미확인"}
VIRTUAL = [
    {"id": "g0", "category": "gpu", "name": "CPU 내장 그래픽 사용", "price": 0, "virtual": True, "watts": 0, "vram": 0, "length": 0,
     "thickness": 0, "connector": "none", "minPsu": 0},
    {"id": "o0", "category": "os", "name": "OS 미포함", "price": 0, "virtual": True, "included": False},
]


def collector_owns_catalog(session) -> bool:
    return (get_document(session, OWNER_DOC) or {}).get("owner") == "collector"


def js_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def js_round(x: float) -> float:
    return math.floor(x + 0.5)


def build_snapshot(registry: dict, records: list[dict], job_id: str, reviews: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    by_id = {r["id"]: r for r in records}
    overrides = reviews.get("specOverrides") or {}
    parts = []
    for product in registry["products"]:
        if not (product.get("danawaPcode") or product.get("naverProductId")):
            continue
        record = by_id.get(product["id"])
        price = (record or {}).get("priceEvidence")
        override = overrides.get(product["id"]) or {}
        valid = override.get("reviewed") is True and str(override.get("sourceUrl") or "").startswith("https://") and bool(override.get("reviewedAt"))
        b = (record or {}).get("benchmark") or None
        part = {**product, **(record or {}), **(override.get("specs") or {} if valid else {})}
        part.update({
            "id": product["id"], "category": product["category"], "name": (record or {}).get("name") or product.get("name"),
            "dataMode": "live", "verified": True, "virtual": False,
            "price": price.get("amount") if price else None, "observedAt": price.get("observedAt") if price else None,
            "source": (price or {}).get("source") or "미수집", "sourceUrl": price.get("sourceUrl") if price else None,
            "priceEvidence": price or None,
            "inStock": False if (price or {}).get("availability") == "out-of-stock" else bool(price),
            "specStatus": "reviewed" if valid else "parsed" if record else "missing",
            "specReview": {"sourceUrl": override["sourceUrl"], "reviewedAt": override["reviewedAt"],
                           "sources": override.get("sources") or [override["sourceUrl"]], "notes": override.get("notes")} if valid else None,
            "benchmark": b, "score": (b or {}).get("normalizedScore"),
        })
        parts.append(part)
    virtual = [{**p, "dataMode": "live", "verified": True, "inStock": True, "source": "선택 옵션 (실물 상품 아님)", "benchmark": None} for p in VIRTUAL]
    snapshot = hydrate_snapshot({"schemaVersion": 2, "mode": "live", "catalogVersion": job_id, "generatedAt": utc_iso(now),
                                 "parts": [*parts, *virtual], "policy": POLICY}, now)
    snapshot["collectionWindow"] = window_coverage(snapshot["parts"])
    snapshot["coverage"] = {**snapshot["coverage"], "total": len(parts),
                            "freshPrices": sum(price_state(p, now) == "fresh" for p in parts),
                            "measuredBenchmarks": sum(benchmark_state(p, now) == "measured" for p in parts),
                            "benchmarkTargets": sum(p["category"] in ("cpu", "gpu") for p in parts),
                            "reviewedSpecs": sum(p["specStatus"] == "reviewed" for p in parts)}
    return snapshot


def publish(store: PipelineStore, snapshot: dict, job_id: str, *, force_publish: bool | None = None) -> str:
    """Hand the snapshot to the server (owner = collector) or keep it as a shadow document."""
    registry = store.doc("products")
    if force_publish if force_publish is not None else collector_owns_catalog(store.s):
        importer.import_snapshot(store.s, snapshot, source={"kind": "collector", "jobId": job_id, "generatedAt": snapshot["generatedAt"]})
        target = "parts"
    else:
        store.put_doc("catalog-shadow", snapshot)
        target = "collector/catalog-shadow"
    state = store.doc("discovery-state")
    if state:
        counts: dict[str, int] = {}
        for c in (state.get("candidates") or {}).values():
            counts[c.get("status")] = counts.get(c.get("status"), 0) + 1
        store.put_doc("discovery-status", {"updatedAt": state.get("updatedAt"), "discovered": len(state.get("candidates") or {}),
                                           "collectionWindow": snapshot["collectionWindow"], **counts})
    histories = store.histories([p["id"] for p in registry["products"]])
    store.put_doc("price-history", histories)
    return target


def publish_catalog(store: PipelineStore) -> dict:
    """Rebuild and publish the snapshot from stored observations without collecting (publish.mjs)."""
    registry, reviews, records = store.doc("products"), store.doc("reviews", {}), store.products()
    version = hashlib.sha256(js_json({"registry": registry, "reviews": reviews,
                                      "records": sorted(records, key=lambda r: r["id"])}).encode()).hexdigest()[:20]
    snapshot = build_snapshot(registry, records, version, reviews)
    publish(store, snapshot, version)
    return snapshot


def _benchmarks(store: PipelineStore, client: SourceClient, registry: dict, summary: dict, options: dict) -> None:
    archive = Path(options.get("benchmark_archive") or DATA_DIR / "blender-latest.zip")
    if not options.get("benchmark_archive"):
        meta = blender.download(client, archive, force=bool(options.get("refresh_benchmarks")))
        if meta:
            store.put_doc("blender-meta", meta)
    registry_hash = hashlib.sha256(js_json(registry).encode()).hexdigest()
    mtime = archive.stat().st_mtime
    parsed = store.doc("blender-aggregate")
    if not parsed or parsed.get("registryHash") != registry_hash or parsed.get("archiveMtime") != mtime:
        print(json.dumps({"stage": "benchmark", "message": "공식 CC0 스냅샷 스트리밍 집계 중"}, ensure_ascii=False), flush=True)
        parsed = {**blender.aggregate(str(archive), registry["products"]), "registryHash": registry_hash, "archiveMtime": mtime}
        store.put_doc("blender-aggregate", parsed)
    evidence_hash = blender.file_hash(archive)
    # A cached snapshot keeps its original collection time; re-aggregating never refreshes evidence age.
    meta = store.doc("blender-meta") or {}
    observed = meta.get("observedAt") or utc_iso(datetime.fromtimestamp(mtime, timezone.utc))
    selected = blender.select_benchmarks(parsed["groups"])
    refs = registry.get("benchmarkReferences") or {}
    references = {"cpu": next((b for b in selected if b["partId"] == (refs.get("cpu") or "c2")), None),
                  "gpu": next((b for b in selected if b["partId"] == (refs.get("gpu") or "g2")), None)}
    products = {p["id"]: p for p in registry["products"]}
    for b in selected:
        product = products.get(b["partId"])
        ref = references.get(product["category"]) if product else None
        if not ref:
            continue
        store.put_benchmark(b["partId"], {**b, "normalizedScore": js_round(b["score"] / ref["score"] * 1000) / 10,
                                          "referencePartId": ref["partId"], "referenceScore": ref["score"], "source": "Blender Open Data",
                                          "sourceUrl": blender.BLENDER_URL, "license": "CC0-1.0", "observedAt": observed,
                                          "evidenceHash": evidence_hash, "snapshotFile": parsed["snapshotFile"]})
        summary["benchmarks"] += 1


def run_pipeline(options: dict | None = None, *, store: PipelineStore | None = None, client: SourceClient | None = None,
                 log=lambda value: print(json.dumps(value, ensure_ascii=False), flush=True)) -> dict:
    options = options or {}
    if options.get("prices_only") and options.get("benchmarks_only"):
        raise ValueError("가격 전용과 벤치마크 전용 옵션은 함께 지정할 수 없습니다.")
    own_store = store is None
    store = store or PipelineStore()
    client = client or SourceClient(cache=PgPageCache(), cache_ttl=24 * 3600 if options.get("reparse_cache") else 0)
    summary = {"products": 0, "prices": 0, "benchmarks": 0, "errors": [], "quarantined": 0}
    job = None
    try:
        with advisory_lock("pipeline"):
            if options.get("expand"):
                expand_catalog(store, client, daily=bool(options.get("daily")), on_progress=log)
            job = store.start()
            registry = store.doc("products")
            enriched = False
            for product in registry["products"]:
                if not product.get("benchmarkName"):
                    name = benchmark_name(product["category"], product.get("name") or "")
                    if name:
                        product["benchmarkName"] = name
                        enriched = True
            if enriched:
                store.put_doc("products", registry)
            reviews = store.doc("reviews", {})
            ids = [p["id"] for p in registry.get("products") or []]
            if not ids or len(set(ids)) != len(ids):
                raise ValueError("상품 레지스트리가 비어 있거나 중복되었습니다.")
            if not options.get("benchmarks_only"):
                for product in registry["products"]:
                    if not product.get("danawaPcode"):
                        continue
                    summary["products"] += 1
                    try:
                        observation = collect_product(client, product)
                        if store.accept_product(observation, reviews):
                            summary["prices"] += 1
                        else:
                            summary["quarantined"] += 1
                        log({"stage": "price", "partId": product["id"], "name": observation["part"]["name"],
                             "price": observation["price"]["amount"]})
                    except Exception as e:  # noqa: BLE001 — one product's failure never stops the run
                        code = getattr(e, "code", None)
                        summary["errors"].append({"partId": product["id"], "source": "danawa", "code": code or "error", "message": str(e)})
                        store.s.rollback()
                        store.queue("source", product["id"], str(e), code or str(e))
                        log({"stage": "error", "partId": product["id"], "message": str(e)})
            if not options.get("prices_only"):
                try:
                    _benchmarks(store, client, registry, summary, options)
                except Exception as e:  # noqa: BLE001
                    store.s.rollback()
                    summary["errors"].append({"source": "blender", "message": str(e)})
                    log({"stage": "error", "source": "blender", "message": str(e)})
            snapshot = build_snapshot(registry, store.products(), job, reviews)
            summary["coverage"] = snapshot["coverage"]
            summary["quarantined"] += len(store.reviews())
            c = snapshot["coverage"]
            status = "partial" if (summary["errors"] or c["freshPrices"] < c["total"] or c["measuredBenchmarks"] < c["benchmarkTargets"]) else "succeeded"
            store.finish(job, status, summary)
            target = publish(store, snapshot, job, force_publish=options.get("publish"))
            store.put_doc("pipeline-status", {"schemaVersion": 1, "generatedAt": snapshot["generatedAt"], "jobId": job, "status": status,
                                              "summary": summary, "reviews": store.reviews(), "jobs": store.jobs()})
            log({"jobId": job, "status": status, **summary, "output": target})
            return {"snapshot": snapshot, "summary": summary, "status": status}
    except Busy as e:
        raise Busy("다른 수집 실행이 진행 중입니다.") from e
    except Exception as e:
        if job:
            store.s.rollback()
            store.finish(job, "failed", {**summary, "error": str(e)})
        raise
    finally:
        if own_store:
            store.close()


__all__ = ["run_pipeline", "build_snapshot", "publish_catalog", "collector_owns_catalog", "SourceError", "put_document"]
