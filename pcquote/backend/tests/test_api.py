"""Screen API tests against the pcquote_test PostgreSQL database."""

import os

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg:///pcquote_test")

from datetime import datetime, timedelta, timezone  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from conftest import sample_parts  # noqa: E402
from pcquote.db import (  # noqa: E402
    Base, PartRow, PriceHistoryRow, PriceReviewRow, engine, put_document, session_factory,
)
from pcquote.knowledge import graph
from pcquote.main import app  # noqa: E402
from pcquote.service import CatalogService, iso  # noqa: E402

REQ = {"profile": "gaming", "budget": 1_800_000, "resolution": "QHD", "white": False, "wifi": False, "os": False,
       "text": "게임 180만"}
SETTINGS = {"assembly": 0}


def now_iso(hours_ago: float = 0) -> str:
    return iso(datetime.now(timezone.utc) - timedelta(hours=hours_ago))


def raw_part(p, observed: str) -> dict:
    """Screen-format record for an engine fixture part."""
    raw = {"id": p.id, "category": p.category, "name": p.name, "brand": p.brand, "price": p.price, "inStock": True,
           "danawaPcode": "1" + str(abs(hash(p.id)) % 10**8), **p.specs,
           "priceEvidence": {"amount": p.price, "sourceUrl": f"https://prod.danawa.com/info/?pcode={p.id}",
                             "observedAt": observed, "source": "danawa"}}
    if p.category == "board":
        raw.setdefault("maxRam", 128)
    if p.benchmark:
        raw["benchmarkName"] = p.benchmark_name
        raw["benchmark"] = {"score": p.benchmark, "normalizedScore": p.benchmark, "samples": 5,
                            "sourceUrl": "https://opendata.blender.org/", "observedAt": observed}
    return raw


def seed(stale: set[str] = frozenset()):
    Base.metadata.drop_all(engine())
    Base.metadata.create_all(engine())
    with session_factory()() as s:
        for p in sample_parts():
            observed = now_iso(48 if p.id in stale else 1)
            s.add(PartRow(id=p.id, category=p.category, name=p.name, brand=p.brand, price=p.price, in_stock=True,
                          specs=p.specs, benchmark=p.benchmark, benchmark_name=p.benchmark_name,
                          price_observed_at=datetime.fromisoformat(observed.replace("Z", "+00:00")),
                          popularity_rank=p.popularity_rank, popularity_observed_at=p.popularity_observed_at,
                          raw=raw_part(p, observed)))
            s.add(PriceHistoryRow(part_id=p.id, price=p.price, source="test",
                                  observed_at=datetime.fromisoformat(observed.replace("Z", "+00:00"))))
        s.add(PartRow(id="g0", category="gpu", name="CPU 내장 그래픽 사용", price=0,
                      raw={"id": "g0", "category": "gpu", "name": "CPU 내장 그래픽 사용", "price": 0, "virtual": True}))
        s.add(PartRow(id="o0", category="os", name="OS 미포함", price=0,
                      raw={"id": "o0", "category": "os", "name": "OS 미포함", "price": 0, "virtual": True}))
        put_document(s, "catalog-meta", {"schemaVersion": 2, "mode": "live", "catalogVersion": "v1",
                                         "policy": {"scoreMethod": "CPU 9600X=100 / GPU RTX 5060 Ti=100."}})
        s.commit()


@pytest.fixture
def client():
    seed()
    app.state.service = CatalogService(sync_source=False)
    with TestClient(app) as c:
        app.state.complete = None
        app.state.collect = None
        yield c


def fresh(c, req=REQ):
    r = c.post("/api/recommend/fresh", json={"requirement": req, "settings": SETTINGS})
    assert r.status_code == 200, r.text
    return r.json()


def test_health_settings_and_state(client):
    assert client.get("/api/health").json() == {"ok": True, "mode": "live", "llm": False, "storage": "postgresql",
                                                "engine": "pcquote", "requirementsTimeoutMs": 160000,
                                                "knowledgeGames": graph().games()}
    assert client.get("/api/settings").json() is None
    store = {"store": "Dr.Robot", "assembly": 30000, "validHours": 24}
    assert client.put("/api/settings", json=store).json() == store
    assert client.get("/api/settings").json() == store
    assert client.put("/api/settings", json={**store, "assembly": -1}).status_code == 400
    assert client.put("/api/state/theme", json={"theme": "dark"}).json() == {"ok": True}
    assert client.get("/api/state/theme").json() == {"theme": "dark"}
    assert client.get("/api/state/nope").status_code == 404
    assert client.get("/api/health", headers={"Origin": "http://evil.example"}).status_code == 403


def test_catalog_serves_screen_records(client):
    body = client.get("/api/catalog").json()
    assert body["schemaVersion"] == 2 and body["catalogVersion"] == "v1"
    ids = {p["id"] for p in body["parts"]}
    assert {"g0", "o0", "c-7500f"} <= ids


def test_recommend_returns_screen_plans(client):
    body = fresh(client)
    assert body["refresh"] == {"updated": 0, "errors": []}
    # Three plans in price order, none above the budget.
    assert [p and p["id"] for p in body["plans"]] == ["balanced", "enhanced", "saving"]
    totals = [p["total"] for p in body["plans"]]
    assert totals[1] > totals[0] > totals[2]
    plan = body["plans"][0]
    assert set(plan["parts"]) == {"cpu", "board", "ram", "gpu", "ssd", "psu", "case", "cooler", "os"}
    assert plan["parts"]["os"]["id"] == "o0" and plan["engine"] == "pcquote"
    assert plan["budgetCap"] == 1_800_000 and plan["total"] <= plan["budgetCap"]
    assert plan["catalogVersion"] == body["catalogVersion"] == "v1"
    assert all(c["ok"] for c in plan["checks"])


def test_unlimited_quote_can_be_generated_evaluated_and_issued(client):
    req = {**REQ, "budget": None, "text": "QHD 게임용 예산 제한 없음"}
    body = fresh(client, req)
    plan = body["plans"][0]
    assert plan and plan["budgetCap"] is None
    ids = {c: p["id"] for c, p in plan["parts"].items()}
    ev = client.post("/api/quotes/evaluate", json={"requirement": req, "settings": SETTINGS, "parts": ids})
    assert ev.status_code == 200 and all(c["ok"] for c in ev.json()["checks"])
    saved = client.post("/api/quotes", json={**issue_body(plan, body), "req": req})
    assert saved.status_code == 201, saved.text
    assert saved.json()["req"]["budget"] is None
    assert client.post("/api/recommend/fresh", json={"requirement": {**REQ, "profile": "x"}, "settings": SETTINGS}).status_code == 400


def test_stale_prices_are_refreshed_and_failures_excluded(client):
    first = fresh(client)["plans"][0]
    gpu, cpu = first["parts"]["gpu"]["id"], first["parts"]["cpu"]["id"]
    seed(stale={gpu, cpu})
    app.state.service.invalidate()
    calls = []

    def collect(record):
        calls.append(record["id"])
        if record["id"] == cpu:
            raise RuntimeError("차단")
        return {"partId": record["id"], "amount": record["price"] + 1000, "sourceUrl": record["priceEvidence"]["sourceUrl"],
                "observedAt": now_iso(), "hash": "h-" + record["id"], "availability": "listed-unconfirmed"}

    app.state.collect = collect
    body = fresh(client)
    assert gpu in calls and cpu in calls
    assert body["refresh"]["errors"] == [{"id": cpu, "error": "차단"}]
    assert all(p["parts"]["cpu"]["id"] != cpu for p in body["plans"] if p)
    assert body["catalogVersion"] != "v1"
    with session_factory()() as s:
        row = s.get(PartRow, gpu)
        assert row.raw["price"] == row.price and row.raw["priceEvidence"]["hash"] == "h-" + gpu
        assert s.scalars(select(PriceHistoryRow).where(PriceHistoryRow.part_id == gpu,
                                                       PriceHistoryRow.source == "danawa-refresh")).first()


def test_large_price_move_waits_for_review(client):
    gpu = fresh(client)["plans"][0]["parts"]["gpu"]["id"]
    seed(stale={gpu})
    app.state.service.invalidate()
    app.state.collect = lambda record: {"partId": record["id"], "amount": record["price"] * 2, "observedAt": now_iso(),
                                        "sourceUrl": "https://prod.danawa.com/", "hash": "jump"}
    body = fresh(client)
    assert {"id": gpu, "error": "가격 변동 검수 대기"} in body["refresh"]["errors"]
    with session_factory()() as s:
        assert s.scalars(select(PriceReviewRow).where(PriceReviewRow.part_id == gpu)).one().status == "pending"


def test_evaluate_and_alternatives(client):
    plan = fresh(client)["plans"][0]
    ids = {c: p["id"] for c, p in plan["parts"].items()}
    ev = client.post("/api/quotes/evaluate", json={"requirement": REQ, "settings": SETTINGS, "parts": ids}).json()
    assert all(c["ok"] for c in ev["checks"]) and "warnings" in ev
    alt = client.post("/api/quotes/alternatives", json={"requirement": REQ, "settings": SETTINGS, "parts": ids,
                                                        "category": "ram"}).json()
    assert alt["items"] and all(i["id"] != ids["ram"] for i in alt["items"])
    bad = client.post("/api/quotes/evaluate", json={"requirement": REQ, "settings": SETTINGS,
                                                    "parts": {**ids, "board": "nope"}})
    assert bad.status_code == 422


def issue_body(plan, body):
    return {"plan": plan, "req": REQ, "settings": SETTINGS, "customerName": "홍길동",
            "catalogVersion": body["catalogVersion"], "name": "최적 균형안"}


def test_issue_quote_validates_and_stores(client):
    body = fresh(client)
    plan = body["plans"][0]
    r = client.post("/api/quotes", json=issue_body(plan, body))
    assert r.status_code == 201, r.text
    saved = r.json()
    assert saved["plan"]["total"] == plan["total"] and saved["customerName"] == "홍길동"
    assert [q["id"] for q in client.get("/api/quotes").json()] == [saved["id"]]

    assert client.post("/api/quotes", json={**issue_body(plan, body), "catalogVersion": "old"}).status_code == 409
    cheaper = {**plan, "parts": {**plan["parts"], "ram": {**plan["parts"]["ram"], "price": 1}}}
    assert client.post("/api/quotes", json=issue_body(cheaper, body)).status_code == 409
    over = client.post("/api/quotes", json={**issue_body(plan, body), "req": {**REQ, "budget": 1_000_000}})
    assert over.status_code == 422

    assert client.delete(f"/api/quotes/{saved['id']}").json() == {"ok": True}
    assert client.delete(f"/api/quotes/{saved['id']}").status_code == 404


def test_issue_accepts_bios_update_boards(client):
    """Chipset rule warnings (BIOS update) are issuable — the old board-list rule rejected these."""
    req = {**REQ, "budget": 1_500_000}
    body = fresh(client, req)
    assert any(c.get("warning") for p in body["plans"] if p for c in p["checks"]), "fixture must include a BIOS-update plan"
    for plan in [p for p in body["plans"] if p]:
        r = client.post("/api/quotes", json={**issue_body(plan, body), "req": req})
        assert r.status_code == 201, r.text


def test_import_quote_is_idempotent(client):
    entry = {"id": "old-1", "date": "2026-11-05T12:00:00.000Z", "plan": {"parts": {}}, "req": {"profile": "office"},
             "settings": {"assembly": 0}}
    assert client.post("/api/quotes/import", json=entry).json() == {"ok": True}
    assert client.post("/api/quotes/import", json=entry).json() == {"ok": True}
    assert [q["id"] for q in client.get("/api/quotes").json()] == ["old-1"]
    assert client.post("/api/quotes/import", json={"id": ""}).status_code == 400


def test_requirements_and_answer_without_llm(client):
    r = client.post("/api/requirements", json={"text": "조용한 사무용 PC, 엑셀과 POS, 100만 원"}).json()
    assert (r["profile"], r["budget"], r["resolution"], r["method"]) == ("office", 1_000_000, "FHD", "local")
    assert client.post("/api/requirements", json={"text": " "}).status_code == 400
    a = client.post("/api/answer", json={"text": "4060 어때?"}).json()
    assert a["method"] == "local" and "RTX 4060" in a["text"] and "FPS" in a["text"]


def test_answer_with_llm_is_checked(client):
    prompts = []

    def complete(**kwargs):
        prompts.append(kwargs)
        return {"answer": "RTX 4060은 일반적으로 FHD 게임에 알맞고 가격은 999,999원입니다.", "sources": ["catalog"]}

    app.state.complete = complete
    a = client.post("/api/answer", json={"text": "4060 어때?"}).json()
    assert len(prompts) == 2 and a["method"] == "local" and "근거에 없는 금액" in a["reason"]

    app.state.complete = lambda **k: {"answer": "RTX 4060은 일반적으로 FHD 게임에 알맞습니다.", "sources": ["general", "x"]}
    a = client.post("/api/answer", json={"text": "4060 어때?"}).json()
    assert a == {"text": "RTX 4060은 일반적으로 FHD 게임에 알맞습니다.", "sources": ["general"], "method": "llm", "rounds": 1}


def test_requirements_with_llm_keeps_stated_text(client):
    app.state.complete = lambda **k: {"profile": "ai", "budget": 5_000_000, "resolution": "4K", "white": False,
                                      "wifi": False, "os": False, "questions": ["예산은요?", "모니터는요?"]}
    r = client.post("/api/requirements", json={"text": "배그용 화이트 QHD"}).json()
    assert (r["profile"], r["budget"], r["resolution"], r["white"], r["questions"], r["method"]) == ("gaming", None, "QHD", True, [], "local")


def test_engine_recommend_endpoint(client):
    r = client.post("/api/recommend", json={"budget": 1_800_000, "uses": ["gaming"]})
    assert r.status_code == 200 and [p["label"] for p in r.json()["plans"]] == ["균형형", "성능 우선형", "가성비형"]
    assert client.post("/api/recommend", json={"budget": 1}).status_code == 422


def test_recommend_tells_staff_when_specs_were_lowered(client):
    body = fresh(client, {**REQ, "budget": 1_200_000})
    assert any(body["plans"])
    assert body["notice"] == "예산에 맞추기 위해 최소 사양을 낮췄어요: 메모리 32GB → 16GB."
    assert fresh(client)["notice"] is None


def test_requirements_fall_back_to_rules_when_the_llm_fails(client):
    def outage(**k):
        raise RuntimeError("LLM 응답 오류 (429)")

    app.state.complete = outage
    r = client.post("/api/requirements", json={"text": "배그용 PC"})
    assert r.status_code == 200
    body = r.json()
    assert (body["profile"], body["budget"], body["method"]) == ("gaming", None, "local")
    assert "fallback" not in body  # Known game avoids the model entirely.
    assert body["questions"] == []
    assert any(fresh(client, body)["plans"])  # quota exhaustion still reaches the quote engine
    unknown = client.post("/api/requirements", json={"text": "컴퓨터 하나 120만원"}).json()
    assert unknown["questions"] == ["주로 어떤 용도로 쓰실 예정인가요? (게임, 영상 편집, 사무, AI 등)"]  # no silent guess


def test_pending_purpose_cannot_generate_a_quote(client):
    response = client.post('/api/recommend/fresh', json={
        'requirement': {**REQ, 'needsPurpose': True}, 'settings': SETTINGS})
    assert response.status_code == 400
    assert '용도' in response.json()['error']



def test_unknown_purpose_timeout_then_clarification_keeps_budget(client):
    def timeout(**kwargs):
        raise TimeoutError('timeout')
    app.state.complete = timeout
    first = client.post('/api/requirements', json={'text': 'LaTeX로 논문을 작성할 본체 150만원'}).json()
    assert first['needsPurpose'] is True and first['profile'] is None
    assert client.post('/api/recommend/fresh', json={'requirement': first, 'settings': SETTINGS}).status_code == 400
    clarified = client.post('/api/requirements', json={'text': first['text']+'\n추가 요청: 사무용이에요'}).json()
    assert clarified['profile'] == 'office' and clarified['resolution'] == 'FHD' and clarified['budget'] == 1500000
    assert not clarified.get('needsPurpose')
    assert any(fresh(client, clarified)['plans'])


def test_game_graph_api_and_normalized_quote(client):
    graph_data=client.get('/api/knowledge/graph').json()
    assert len([n for n in graph_data['nodes'] if n['kind']=='game'])==28
    resolved=client.get('/api/knowledge/resolve',params={'text':'오버워치 200fps'}).json()
    assert resolved['gpuModels']==['5060'] and not resolved['fpsGuaranteed']
    req={**REQ,'budget':None,'text':'오버워치용 견적','resolutionExplicit':False}
    body=fresh(client,req)
    assert body['requirement']['resolution']=='FHD'
    assert body['requirement']['resolutionBasis']=='service_default'
    assert body['gameEvidence']['selectionApplied']
    assert all(p['parts']['gpu']['id']=='g-4060' for p in body['plans'] if p)
    explicit=fresh(client,{**req,'resolution':'QHD','resolutionExplicit':True})
    assert explicit['requirement']['resolution']=='QHD'
    assert not explicit['gameEvidence']['restrictGpu']
    assert client.get('/api/knowledge/resolve',params={'text':'오버워치','resolution':'bogus'}).status_code==422
