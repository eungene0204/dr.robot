"""Collector (ported from buildmate pipeline/). Cases mirror buildmate's tests/pipeline, expansion, popularity, daily, window tests."""

import os

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg:///pcquote_test")

import json  # noqa: E402
import zipfile  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

from pcquote.collector import blender  # noqa: E402
from pcquote.collector.client import Robots, SourceClient, utc_iso  # noqa: E402
from pcquote.collector.daily import daily  # noqa: E402
from pcquote.collector.expand import can_advance, expand_catalog  # noqa: E402
from pcquote.collector.parse import (  # noqa: E402
    SourceError,
    benchmark_name,
    parse_popularity,
    parse_product,
    parse_search,
    parse_specs,
)
from pcquote.collector.run import build_snapshot, publish, run_pipeline  # noqa: E402
from pcquote.collector.store import Busy, PipelineStore, advisory_lock, lock_held  # noqa: E402
from pcquote.collector.window import collection_window, seoul_day, window_coverage  # noqa: E402
from pcquote.db import Base, PartRow, engine, put_document, session_factory  # noqa: E402

AT = utc_iso()
PRODUCT = {"id": "cpu", "category": "cpu", "danawaPcode": "123"}
META = {"fetchedAt": AT, "hash": "evidence-sha256"}


def html(**overrides):
    data = {"@type": "Product", "sku": "123", "name": "AMD 라이젠5 9600X", "brand": {"name": "AMD"},
            "description": "AMD(소켓AM5) / 6코어 / 12스레드 / DDR5 / AMD Radeon Graphics / TDP: 65W / PPT: 88W",
            "offers": {"lowPrice": "250000", "priceCurrency": "KRW", "offerCount": "10"}, **overrides}
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'


@pytest.fixture
def store():
    Base.metadata.drop_all(engine())
    Base.metadata.create_all(engine())
    s = PipelineStore(session_factory()())
    yield s
    s.close()


# Parsers -----------------------------------------------------------------------------------------

def test_product_checks_sku_currency_price_and_keeps_evidence():
    o = parse_product(html(), PRODUCT, META)
    assert (o["price"]["amount"], o["part"]["watts"], o["price"]["shipping"], o["price"]["availability"], o["price"]["hash"]) == (
        250000, 88, None, "listed-unconfirmed", META["hash"])
    assert o["part"]["brand"] == "AMD" and o["part"]["socket"] == "AM5" and o["part"]["igpu"] is True
    for bad in (html(sku="999"), html(offers={"lowPrice": "0", "priceCurrency": "KRW"}), html(offers={"lowPrice": "1", "priceCurrency": "USD"})):
        with pytest.raises(SourceError):
            parse_product(bad, PRODUCT, META)


def test_specs_gpu_power_connectors_and_ram_kits():
    gpu = parse_specs("gpu", "RTX 5070 / 650W 이상 / 전원 포트: 16핀(12V2x6) x1 / 사용전력: 250W / 가로(길이): 304.4mm / 두께: 41.6mm", "RTX 5070 12GB")
    assert (gpu["connectorCount"], gpu["watts"], gpu["minPsu"], gpu["thickness"], gpu["length"], gpu["connector"]) == (1, 250, 650, None, 304.4, "12v2x6")
    ram = parse_specs("ram", "DDR5 / 32GB(16Gx2) / 6000MHz / CL30", "32GB(16Gx2)")
    assert (ram["capacity"], ram["sticks"], ram["speedMHz"], ram["cl"]) == (32, 2, 6000, 30)
    assert parse_specs("gpu", "", "GPU")["watts"] is None


def test_specs_intel_notation_and_board_slots():
    p = parse_specs("cpu", "인텔(소켓1851) / P8+E16코어 / 24스레드 / 인텔 그래픽스(Xe LPG) / PBP-MTP: 125-250W", "인텔 코어 울트라9 285K")
    assert (p["socket"], p["cores"], p["watts"], p["igpu"]) == ("LGA1851", 24, 250, True)
    k = parse_specs("cpu", "인텔(1700소켓) / 8+12코어 / 16+12쓰레드 / PBP-MTP: 125~253W / UHD 770", "14700K")
    assert (k["socket"], k["watts"], k["cores"], k["igpu"]) == ("LGA1700", 253, 20, True)
    f = parse_specs("cpu", "인텔(소켓1700) / 6코어 / 12스레드 / 미탑재 / TDP: 65~117W", "12400F")
    assert (f["watts"], f["tdp"], f["igpu"]) == (117, 65, False)
    assert parse_specs("cpu", "인텔(1700소켓) / 16+12쓰레드")["cores"] is None
    b = parse_specs("board", "인텔(소켓1851) / DDR5 / M-ATX (24.4x24.4cm) / [메모리] / 9066MHz (PC5-72500) / 4개 / 메모리 용량: 최대 256GB / M.2: 2개")
    assert (b["slots"], b["maxRam"], b["m2"], b["form"]) == (4, 256, 2, "mATX")
    assert parse_specs("board", "인텔(소켓1851) / DDR5 / [확장슬롯] / PCIex16: 1개 / SATA3: 4개")["slots"] is None


def test_listing_month_is_not_a_release_date_and_unpriced_skus_can_be_kept():
    result = parse_product("<body>등록월: 2024.11." + html() + "</body>", PRODUCT, META)
    assert result["part"]["listingMonth"] == "2024-11" and "releaseDate" not in result["part"]
    unpriced = parse_product(html(offers={"priceCurrency": "KRW", "lowPrice": 0, "offerCount": 0}), PRODUCT, META, allow_missing_price=True)
    assert unpriced["price"] is None and unpriced["part"]["name"] == "AMD 라이젠5 9600X"


def test_search_keeps_kit_names_and_reads_server_rendered_bundles():
    page = ('<script type="application/ld+json">' + json.dumps({"itemListElement": [{"url": "https://prod.danawa.com/info/?pcode=123",
            "name": "DDR5 32GB(16Gx2) 패키지"}]}) + '</script><li data-product-seq="123"><a href="?pcode=123">DDR5 패키지 상세 상품</a></li>')
    assert parse_search(page)[0]["name"] == "DDR5 32GB(16Gx2) 패키지"
    data = {"productUrl": "https://prod.danawa.com/info/?pcode=123", "name": "CPU 모델 멀티팩", "bundleProducts": [{"productCode": 124, "bundleName": "정품"}]}
    frame = [1, "a:" + json.dumps(data, ensure_ascii=False) + "\n"]
    assert {p["pcode"] for p in parse_search(f"<script>self.__next_f.push({json.dumps(frame, ensure_ascii=False)})</script>")} == {"123", "124"}


def test_benchmark_names():
    assert benchmark_name("cpu", "AMD 라이젠7-6세대 9700X (멀티팩 정품)") == "AMD Ryzen 7 9700X"
    assert benchmark_name("cpu", "인텔 코어 울트라9 시리즈2 285K (애로우레이크)") == "Intel Core Ultra 9 285K"
    assert benchmark_name("cpu", "인텔 코어i7-14세대 14700K (랩터레이크 리프레시)") == "Intel Core i7-14700K"
    assert benchmark_name("gpu", "MSI 지포스 RTX 5060 Ti 16GB") == "NVIDIA GeForce RTX 5060 Ti"


def item(rank, code):
    return (f'<div class="dnw-catalog-item"><div data-testid="ProductListTitle"><span aria-label="인기순위 {rank}위"></span>'
            f'<a href="https://prod.danawa.com/info/?pcode={code}">제품</a></div></div>')


def test_popularity_ignores_ads_other_sorts_and_missing_ranks():
    page = f'<button role="tab" aria-selected="true">인기상품순</button><div class="dnw-ad-item">{item(1, 111)}</div><div class="dnw-product-list">{item(2, 222)}</div>'
    rows = parse_popularity(page, "cooler", "https://prod.danawa.com/list/?cate=1", AT)
    assert [(r["pcode"], r["popularity"]["rank"], r["popularity"]["familyPcode"]) for r in rows] == [("222", 2, "222")]
    assert parse_popularity(page.replace('aria-selected="true"', 'aria-selected="false"'), "cooler", "u", AT) == []


# Client ------------------------------------------------------------------------------------------

def test_robots_wildcards_longest_match_and_agent_groups():
    r = Robots("User-agent: *\nDisallow: /list/ajax/\nDisallow: /*.php$\nAllow: /list/ajax/public\nCrawl-delay: 10\n\n"
               "User-agent: DrRobot\nDisallow: /private/\n")
    assert r.allowed("https://x/private/a") is False and r.allowed("https://x/list/ajax/") is True  # DrRobot group only
    star = Robots("User-agent: *\nDisallow: /list/ajax/\nDisallow: /*.php$\nAllow: /list/ajax/public\nCrawl-delay: 10\n")
    assert star.allowed("https://x/list/ajax/a") is False and star.allowed("https://x/list/ajax/public/1") is True
    assert star.allowed("https://x/a.php") is False and star.allowed("https://x/a.php?x=1") is True
    assert star.crawl_delay() == 10 and star.allowed("https://x/info/?pcode=1") is True


class MemoryCache:
    def __init__(self):
        self.pages = {}

    def get(self, url):
        return self.pages.get(url)

    def put(self, page):
        self.pages[url := page["url"]] = page
        return url


def test_client_sends_conditional_requests_and_reuses_cached_text_on_304():
    seen = []

    def handler(request):
        seen.append(dict(request.headers))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:\n")
        if request.headers.get("if-none-match") == '"v1"':
            return httpx.Response(304)
        return httpx.Response(200, text="page", headers={"etag": '"v1"'})

    cache = MemoryCache()
    client = SourceClient(httpx.Client(transport=httpx.MockTransport(handler)), min_delay=0, sleep=lambda s: None, cache=cache)
    first = client.text("https://prod.danawa.com/info/?pcode=1")
    second = client.text("https://prod.danawa.com/info/?pcode=1")
    assert first["text"] == second["text"] == "page" and second["etag"] == '"v1"'
    assert seen[-1]["if-none-match"] == '"v1"' and seen[-1]["user-agent"].startswith("DrRobot/")


def test_client_refuses_oversized_pages_and_unknown_hosts():
    big = SourceClient(httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, text="" if r.url.path == "/robots.txt" else "x" * 8_000_001))), min_delay=0, sleep=lambda s: None)
    with pytest.raises(SourceError, match="크기"):
        big.text("https://prod.danawa.com/info/?pcode=1")
    with pytest.raises(SourceError, match="허용되지 않은"):
        big.text("https://example.com/")


# Store -------------------------------------------------------------------------------------------

def test_price_spike_goes_to_review_and_keeps_last_price(store):
    obs = parse_product(html(), PRODUCT, META)
    assert store.accept_product(obs) is True
    spike = {**obs, "price": {**obs["price"], "amount": 1000, "hash": "spike", "observedAt": utc_iso(datetime.now(timezone.utc) + timedelta(seconds=1))}}
    assert store.accept_product(spike) is False
    assert store.latest_price("cpu")["amount"] == 250000 and store.latest_price("cpu")["observedAt"] == AT
    assert len(store.reviews()) == 1
    assert store.accept_product(spike, {"approvedPriceHashes": ["spike"]}) is True
    store.accept_product(obs)
    assert len(store.history("cpu")) == 2


def test_advisory_lock_is_exclusive(store):
    with advisory_lock("pipeline"):
        assert lock_held("pipeline")
        with pytest.raises(Busy):
            with advisory_lock("pipeline"):
                pass
    assert not lock_held("pipeline")


# Blender -----------------------------------------------------------------------------------------

def test_benchmarks_never_mix_versions_and_need_three_samples():
    groups = [{"partId": "c2", "version": "4.5.0", "backend": "CPU", "samples": 10, "score": 100},
              {"partId": "g2", "version": "4.5.0", "backend": "OPTIX", "samples": 10, "score": 1000},
              {"partId": "c2", "version": "5.0.0", "backend": "CPU", "samples": 2, "score": 200}]
    rows = blender.select_benchmarks(groups)
    assert len(rows) == 2 and all(r["version"] == "4.5.0" for r in rows)


def test_blender_counts_only_complete_single_device_submissions(tmp_path):
    def row(scene, score, devices=1):
        return {"device_info": {"compute_devices": [{"name": "AMD Ryzen 5 9600X 6-Core Processor"}] * devices, "device_type": "CPU"},
                "blender_version": {"version": "5.2.0"}, "scene": {"label": scene, "checksum": scene}, "stats": {"samples_per_minute": score}}
    good = {"created_at": AT, "data": [row("monster", 100), row("junkshop", 50), row("classroom", 25)]}
    partial = {"created_at": AT, "data": [row("monster", 999)]}
    multi = {"created_at": AT, "data": [row("monster", 1, 2), row("junkshop", 1, 2), row("classroom", 1, 2)]}
    archive = tmp_path / "sample.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("opendata.jsonl", "\n".join(json.dumps(x) for x in (good, good, good, partial, multi)))
    out = blender.aggregate(str(archive), [{"id": "c2", "benchmarkName": "AMD Ryzen 5 9600X"}, {"id": "c3", "benchmarkName": "AMD Ryzen 5 9600X"}])
    assert sorted((g["partId"], g["samples"], g["score"]) for g in out["groups"]) == [("c2", 3, 175), ("c3", 3, 175)]


# Window, daily, expansion ------------------------------------------------------------------------

def test_window_uses_korea_dates_and_keeps_listing_months_apart():
    assert seoul_day(datetime(2026, 11, 4, 14, 59, 59, tzinfo=timezone.utc)) == "2026-11-04"
    assert seoul_day(datetime(2026, 11, 4, 15, tzinfo=timezone.utc)) == "2026-11-05"
    window = collection_window(datetime(2026, 11, 4, 15, tzinfo=timezone.utc))
    assert (window["start"], window["end"]) == ("2024-11-05", "2026-11-05")
    c = window_coverage([{"listingMonth": "2025-01"}, {"listingMonth": "2024-11"}, {"listingMonth": "2020-01"}, {"listingMonth": None}], window)
    assert (c["confirmedRelease"], c["recentListing"], c["boundaryListingMonth"], c["dateUnknown"], c["complete"]) == (0, 1, 1, 1, False)


def test_can_advance_has_no_arbitrary_page_cap():
    assert can_advance({"page": 10001}, {"maxPagesPerQuery": None}) and not can_advance({"page": 4}, {"maxPagesPerQuery": 3})
    assert not can_advance({"page": 3, "done": True}, {})


class FakeClient:
    def __init__(self):
        self.urls = []

    def text(self, url, **_):
        self.urls.append(url)
        if "search.danawa" in url:
            body = ('<li data-product-seq="124"><a href="?pcode=124">새 메모리 DDR5 32GB</a></li>' if "sort=dateDESC" in url else
                    '<li data-product-seq="123"><a href="?pcode=123">메모리 DDR5 32GB</a></li>' if "page=1" in url else "")
            return {"url": url, "text": body, "fetchedAt": utc_iso(), "hash": "search"}
        pcode = url.rsplit("=", 1)[1]
        data = {"@type": "Product", "sku": pcode, "name": "메모리 DDR5-5600 (32GB)", "description": "DDR5 / 메모리 용량: 32GB / 5600MHz",
                "offers": {"lowPrice": "100000", "priceCurrency": "KRW", "offerCount": 3}}
        return {"url": url, "text": f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>',
                "fetchedAt": utc_iso(), "hash": "product-" + pcode}


def test_expansion_resumes_on_the_next_page_and_daily_search_finds_new_skus(store):
    store.put_doc("discovery", {"queries": [{"category": "ram", "query": "DDR5"}], "pagesPerPass": 1, "maxPagesPerQuery": 3})
    store.put_doc("products", {"products": []})
    client = FakeClient()
    assert expand_catalog(store, client, on_progress=lambda v: None)["added"] == 1
    assert expand_catalog(store, client, on_progress=lambda v: None)["added"] == 0
    assert len(store.doc("products")["products"]) == 1 and any("page=2" in u for u in client.urls)
    assert expand_catalog(store, client, daily=True, on_progress=lambda v: None)["added"] == 1
    assert len(store.doc("products")["products"]) == 2 and any("sort=dateDESC" in u for u in client.urls)


def test_daily_runs_once_per_korea_day_and_records_failures(store):
    calls = []

    def run(options):
        assert options == {"expand": True, "daily": True}
        calls.append(1)
        return {"status": "partial", "snapshot": {"parts": [{"id": "one"}], "coverage": {"total": 1}}, "summary": {"errors": []}}

    when = datetime(2026, 11, 4, 15, tzinfo=timezone.utc)
    assert daily(store, run=run, now=when)["status"] == "partial" and store.doc("daily-2026-11-05")["day"] == "2026-11-05"
    assert daily(store, run=run, now=when)["status"] == "already-ran" and len(calls) == 1
    attempts = []

    def failing(options):
        attempts.append(1)
        if len(attempts) == 1:
            raise Busy("pipeline")
        raise RuntimeError("source unavailable")

    with pytest.raises(RuntimeError, match="source unavailable"):
        daily(store, run=failing, now=when + timedelta(days=1), poll=0, sleep=lambda s: None)
    assert len(attempts) == 2 and store.doc("daily-2026-11-06")["status"] == "failed"


# Run and publish ---------------------------------------------------------------------------------

def registry_doc():
    return {"products": [{"id": "cpu", "category": "cpu", "name": "등록 이름", "danawaPcode": "123"},
                         {"id": "naver-only", "category": "ram", "name": "N", "naverProductId": "9"},
                         {"id": "unmapped", "category": "ram", "name": "U"}]}


def test_snapshot_uses_reviewed_overrides_and_virtual_options():
    reviews = {"specOverrides": {"cpu": {"reviewed": True, "reviewedAt": AT, "sourceUrl": "https://amd.com/x", "specs": {"watts": 99}},
                                 "naver-only": {"reviewed": True, "reviewedAt": AT, "sourceUrl": "http://insecure", "specs": {"capacity": 1}}}}
    record = {**parse_product(html(), PRODUCT, META)["part"], "priceEvidence": parse_product(html(), PRODUCT, META)["price"], "benchmark": None}
    snap = build_snapshot(registry_doc(), [record], "job", reviews)
    parts = {p["id"]: p for p in snap["parts"]}
    assert set(parts) == {"cpu", "naver-only", "g0", "o0"}
    assert parts["cpu"]["watts"] == 99 and parts["cpu"]["specStatus"] == "reviewed" and parts["cpu"]["price"] == 250000
    assert parts["naver-only"]["specStatus"] == "missing" and parts["naver-only"]["inStock"] is False
    assert snap["coverage"]["total"] == 2 and snap["coverage"]["freshPrices"] == 1 and snap["coverage"]["reviewedSpecs"] == 1


class PageClient:
    def text(self, url, **_):
        return {"url": url, "text": html(), "fetchedAt": AT, "hash": "h"}


def test_run_records_prices_and_errors_and_publishes_only_after_cutover(store):
    store.put_doc("products", {"products": [{"id": "cpu", "category": "cpu", "name": "AMD 라이젠5 9600X", "danawaPcode": "123"},
                                            {"id": "bad", "category": "cpu", "name": "y", "danawaPcode": "999"}]})
    result = run_pipeline({"prices_only": True}, store=store, client=PageClient(), log=lambda v: None)
    assert result["status"] == "partial" and result["summary"]["prices"] == 1
    assert result["summary"]["errors"][0]["partId"] == "bad" and result["summary"]["errors"][0]["code"] == "schema_changed"
    assert store.doc("catalog-shadow")["catalogVersion"] == store.doc("pipeline-status")["jobId"]
    assert store.s.get(PartRow, "cpu") is None  # shadow mode leaves the server catalog alone
    assert store.doc("products")["products"][0]["benchmarkName"] == "AMD Ryzen 5 9600X"
    put_document(store.s, "catalog-owner", {"owner": "collector"})
    store.s.commit()
    run_pipeline({"prices_only": True}, store=store, client=PageClient(), log=lambda v: None)
    assert store.s.get(PartRow, "cpu").price == 250000


def test_publish_writes_status_documents(store):
    store.put_doc("products", registry_doc())
    store.put_doc("discovery-state", {"updatedAt": AT, "candidates": {"1": {"status": "collected"}, "2": {"status": "rejected"}}})
    snap = build_snapshot(registry_doc(), [], "job", {})
    assert publish(store, snap, "job") == "collector/catalog-shadow"
    assert store.doc("discovery-status")["collected"] == 1 and store.doc("discovery-status")["discovered"] == 2
    assert set(store.doc("price-history")) == {"cpu", "naver-only", "unmapped"}


def test_after_cutover_server_reads_collector_documents_and_ignores_buildmate(store, tmp_path, monkeypatch):
    from pcquote import importer, pipeline

    monkeypatch.setenv("BUILDMATE_DATA_DIR", str(tmp_path))  # no buildmate data at all
    store.put_doc("pipeline-status", {"status": "succeeded", "jobId": "j1"})
    assert pipeline.read_doc("pipeline-status", tmp_path) is None
    put_document(store.s, "catalog-owner", {"owner": "collector"})
    store.s.commit()
    assert pipeline.read_doc("pipeline-status", tmp_path) == {"status": "succeeded", "jobId": "j1"}
    assert importer.sync(store.s, tmp_path, force=True) is None


def test_shadow_comparison_ignores_float_noise_and_evaluation_time():
    from pcquote.collector.shadow import compare_catalogs

    node = {"parts": [{"id": "a", "score": 17.781722051149995, "priceStatus": "fresh", "socket": None}]}
    python = {"parts": [{"id": "a", "score": 17.78172205114999, "priceStatus": "stale", "socket": None}]}
    assert compare_catalogs(node, python)["equal"]
    python["parts"][0]["socket"] = "LGA1700"
    assert compare_catalogs(node, python)["differentFields"] == {"socket": 1}
