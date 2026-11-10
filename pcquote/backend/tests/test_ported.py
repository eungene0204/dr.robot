"""Modules ported from buildmate: catalog import, Danawa price collection, pipeline documents, consultation text."""

import os

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg:///pcquote_test")

import json  # noqa: E402
import sqlite3  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

from pcquote import importer, pipeline  # noqa: E402
from pcquote.consult import explicit_budget, model_tokens, parse_requirement  # noqa: E402
from pcquote.danawa import SourceClient, SourceError, collect_price, parse_price  # noqa: E402
from pcquote.db import Base, PartRow, PriceHistoryRow, engine, get_document, session_factory  # noqa: E402
from pcquote.policy import policy_issue, usable_part  # noqa: E402

NOW = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)


def snap_part(pid, price, observed, **extra):
    return {"id": pid, "category": "psu", "name": f"{pid} 850W", "price": price, "capacity": 850, "connectors": ["8pin"],
            "priceEvidence": {"amount": price, "sourceUrl": "https://prod.danawa.com/", "observedAt": observed}, **extra}


def snapshot(parts, version="v1"):
    return {"schemaVersion": 2, "mode": "live", "catalogVersion": version, "policy": {}, "parts": parts}


@pytest.fixture
def db():
    Base.metadata.drop_all(engine())
    Base.metadata.create_all(engine())
    with session_factory()() as s:
        yield s


def test_import_keeps_newer_live_price_and_hides_removed_parts(db):
    importer.import_snapshot(db, snapshot([snap_part("p1", 100_000, "2026-11-05T00:00:00Z"),
                                           snap_part("p2", 90_000, "2026-11-05T00:00:00Z")]), overrides=None)
    row = db.get(PartRow, "p1")
    row.raw = {**row.raw, "price": 95_000, "priceEvidence": {**row.raw["priceEvidence"], "observedAt": "2026-11-06T00:00:00Z"}}
    row.price, row.price_observed_at = 95_000, datetime(2026, 11, 6, tzinfo=timezone.utc)
    db.commit()

    result = importer.import_snapshot(db, snapshot([snap_part("p1", 100_000, "2026-11-05T12:00:00Z")], "v2"), overrides=None)
    db.expire_all()
    assert result["keptNewerPrices"] == 1 and result["removed"] == 1
    assert db.get(PartRow, "p1").price == 95_000 and db.get(PartRow, "p1").raw["price"] == 95_000
    assert db.get(PartRow, "p2").raw is None
    assert get_document(db, "catalog-meta")["catalogVersion"] not in ("v1", "v2")  # content differs from the snapshot
    assert db.query(PriceHistoryRow).filter_by(part_id="p1").count() == 2


def test_import_classifies_ssd_and_keeps_virtual_options(db):
    parts = [{"id": "g0", "category": "gpu", "name": "CPU 내장 그래픽 사용", "price": 0, "virtual": True},
             {"id": "s1", "category": "ssd", "name": "타무즈 GKM330 M.2 SATA (512GB)", "price": 40_000, "capacity": 512},
             {"id": "s2", "category": "ssd", "name": "삼성 990 PRO M.2 NVMe (1TB)", "price": 150_000, "capacity": 1000}]
    importer.import_snapshot(db, snapshot(parts), overrides=None)
    assert db.get(PartRow, "g0").raw["virtual"] is True
    assert db.get(PartRow, "s1").specs["interface"] == "sata"
    assert db.get(PartRow, "s2").specs["interface"] == "nvme"


def test_sync_reads_documents_db_only_when_changed(db, tmp_path, monkeypatch):
    data = tmp_path / "backend/data"
    data.mkdir(parents=True)
    monkeypatch.setenv("BUILDMATE_DATA_DIR", str(data))
    path = str(tmp_path / importer.CATALOG_DOC)
    with sqlite3.connect(data / "documents.db") as conn:
        conn.execute("CREATE TABLE documents(path TEXT PRIMARY KEY,payload TEXT NOT NULL,updated_at TEXT NOT NULL)")
        conn.execute("INSERT INTO documents VALUES(?,?,?)",
                     (path, json.dumps(snapshot([snap_part("p1", 1, "2026-11-05T00:00:00Z")])), "t1"))
    assert importer.sync(db, tmp_path)["parts"] == {"psu": 1}
    assert importer.sync(db, tmp_path) is None
    with sqlite3.connect(data / "documents.db") as conn:
        conn.execute("UPDATE documents SET updated_at='t2'")
    assert importer.sync(db, tmp_path) is not None


def test_pipeline_docs_prefer_documents_db_then_file(tmp_path, monkeypatch):
    data = tmp_path / "backend/data"
    (tmp_path / "public/data").mkdir(parents=True)
    data.mkdir(parents=True)
    monkeypatch.setenv("BUILDMATE_DATA_DIR", str(data))
    (tmp_path / "public/data/discovery-status.json").write_text('{"from": "file"}')
    assert pipeline.read_doc("discovery-status", tmp_path) == {"from": "file"}
    with sqlite3.connect(data / "documents.db") as conn:
        conn.execute("CREATE TABLE documents(path TEXT PRIMARY KEY,payload TEXT NOT NULL,updated_at TEXT NOT NULL)")
        conn.execute("INSERT INTO documents VALUES(?,?,?)", (str(data / "pipeline-status.json"), '{"status": "ok"}', "t"))
    assert pipeline.read_doc("pipeline-status", tmp_path) == {"status": "ok"}
    assert pipeline.read_doc("price-history", tmp_path) is None


PAGE = """<html><script type="application/ld+json">{"@type":"BreadcrumbList","itemListElement":[]}</script>
<script type="application/ld+json">{"@type":"Product","sku":"122676813","name":"MSI RTX 5060",
"offers":{"@type":"AggregateOffer","priceCurrency":"KRW","lowPrice":"688990","offerCount":63}}</script></html>"""
PART = {"id": "g1", "danawaPcode": "122676813"}
META = {"fetchedAt": "2026-11-06T00:00:00.000Z", "hash": "abc"}


def test_parse_price_reads_matching_json_ld():
    price = parse_price(PAGE, PART, META)
    assert (price["amount"], price["offerCount"], price["sourceUrl"], price["observedAt"]) == (
        688990, 63, "https://prod.danawa.com/info/?pcode=122676813", META["fetchedAt"])
    with pytest.raises(SourceError, match="SKU"):
        parse_price(PAGE, {"id": "x", "danawaPcode": "1"}, META)
    with pytest.raises(SourceError, match="KRW"):
        parse_price(PAGE.replace('"offerCount":63', '"offerCount":0'), PART, META)


def client_with(routes):
    calls = []

    def handler(request: httpx.Request):
        calls.append(str(request.url))
        status, body = routes(str(request.url))
        return httpx.Response(status, text=body)

    return SourceClient(httpx.Client(transport=httpx.MockTransport(handler)), min_delay=0, sleep=lambda s: None), calls


def test_collect_honors_robots_and_hosts():
    client, calls = client_with(lambda url: (200, "User-agent: *\nDisallow:\n") if url.endswith("robots.txt") else (200, PAGE))
    assert collect_price(client, PART)["amount"] == 688990
    assert calls[0] == "https://prod.danawa.com/robots.txt"
    blocked, _ = client_with(lambda url: (200, "User-agent: *\nDisallow: /info/\n") if url.endswith("robots.txt") else (200, PAGE))
    with pytest.raises(SourceError, match="robots"):
        collect_price(blocked, PART)
    with pytest.raises(SourceError, match="허용되지 않은"):
        client.text("https://example.com/")
    with pytest.raises(SourceError, match="상품 코드"):
        collect_price(client, {"id": "x"})


def test_collect_retries_then_reports_http_errors():
    client, calls = client_with(lambda url: (200, "") if url.endswith("robots.txt") else (503, ""))
    with pytest.raises(SourceError, match="HTTP 503"):
        collect_price(client, PART)
    assert len(calls) == 4  # robots + 3 attempts


def test_policy_issue_ignores_only_price_age():
    stale = snap_part("p", 1, "2026-01-01T00:00:00Z")
    assert not usable_part(stale, NOW) and not policy_issue(stale, NOW)
    assert policy_issue({**stale, "connectors": None}, NOW)


@pytest.mark.parametrize("text, expected", [
    # Expected values produced by buildmate's JavaScript parseRequirement on 2026-11-06.
    ("조용한 사무용 PC, 엑셀과 POS, 100만 원", ("office", 1_000_000, "FHD", "text")),
    ("예산 상관없이 4K 게임용", ("gaming", None, "4K", "unlimited")),
    ("게임용 200만\n추가 요청: 사무용으로 바꿔줘 150만원 와이파이 윈도우 포함", ("office", 1_500_000, "FHD", "text")),
    ("인터넷 전용 컴퓨터 1.5만원", ("office", 15_000, "FHD", "text")),
])
def test_parse_requirement_matches_javascript(text, expected):
    r = parse_requirement(text)
    assert (r["profile"], r["budget"], r["resolution"], r["budgetSource"]) == expected


def test_model_tokens_match_javascript():
    assert model_tokens("5060ti랑 9800x3d 차이 뭐야?") == ["5060ti", "9800x3d"]
    assert model_tokens("rtx 5070 ti super 가격 얼마?") == ["5070tisuper"]
    assert model_tokens("9700X 1440p 27인치 2560x1440 32gb") == ["9700x", "2560"]
    assert model_tokens("300w 4090 64gb 2tb") == ["4090"]
    assert explicit_budget("2,500,000원") == 2_500_000
