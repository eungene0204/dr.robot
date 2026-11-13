"""The single API server for the consultation screen (buildmate React UI) and the recommendation engine.

Screen endpoints keep the request/response shapes the UI already uses
(``{error: ...}`` on failure). Engine endpoints (``/api/recommend``,
``/api/options``, ``/api/catalog/summary``) expose the engine directly.
"""

from __future__ import annotations

import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Body, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from . import importer, llm, screen
from .knowledge import graph
from .game_search import steam_games, game_answer
from .consult import parse_requirement, detect_profile
from .catalog import CATEGORIES
from .collector.store import PgPageCache, lock_held
from .danawa import SourceClient, collect_price, quote_source_client
from .db import AppSettingRow, LlmUsageRow, SavedQuoteRow, create_schema, session_factory
from .engine.recommend import recommend
from .engine.requirements import RESOLUTIONS, USES, Request as EngineRequest
from .pipeline import PipelineRunner, collector_owns_catalog, read_doc
from .service import CatalogService, iso, utcnow

ALLOWED_ORIGIN = re.compile(r"^http://(localhost|127\.0\.0\.1):(5173|5174|4173|5588|8000|8001)$")
STATE_NAMES = {"consult-live", "consult-demo", "theme"}
BACKEND = Path(__file__).resolve().parents[2]


def error(status: int, message: str, **extra) -> JSONResponse:
    return JSONResponse({"error": message, **extra}, status_code=status)


def _number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _record_usage(u: dict) -> None:
    with session_factory()() as s:
        s.add(LlmUsageRow(model=u.get("model"), tokens=u.get("tokens"), cost=u.get("cost")))
        s.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_schema()
    llm.load_env_files([BACKEND / ".env", importer.BUILDMATE / ".env"])
    app.state.complete = llm.configured_llm(on_usage=_record_usage)
    source = quote_source_client(cache=PgPageCache())
    app.state.collect = lambda record: collect_price(source, record)
    yield


app = FastAPI(title="Dr.Robot PC 견적 API", version="0.2.0", lifespan=lifespan)
app.state.service = CatalogService()
app.state.pipeline = PipelineRunner()
app.state.complete = None
app.state.collect = None


@app.middleware("http")
async def api_guard(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        origin = request.headers.get("origin")
        if origin and not ALLOWED_ORIGIN.match(origin):
            return error(403, "허용되지 않은 출처입니다.")
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(screen.ScreenError)
async def screen_error(_: Request, e: screen.ScreenError):
    return error(422, str(e))


def service() -> CatalogService:
    return app.state.service


# --- status and settings -------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "mode": "live", "llm": app.state.complete is not None, "storage": "postgresql", "engine": "pcquote",
            "requirementsTimeoutMs": llm.REQUIREMENTS_TIMEOUT_MS, "knowledgeGames": graph().games()}


@app.get("/api/knowledge/graph")
def game_graph():
    return graph().data


@app.get("/api/knowledge/resolve")
def game_knowledge(text: str, resolution: str = "FHD"):
    if resolution not in RESOLUTIONS:
        return error(422, "해상도는 FHD, QHD, 4K 중 하나입니다.")
    return graph().resolve(text[:2000], resolution)


@app.get("/api/settings")
def get_settings():
    with session_factory()() as s:
        row = s.get(AppSettingRow, "store")
        return row.payload if row else None


def _put_setting(name: str, value) -> None:
    with session_factory()() as s:
        stmt = insert(AppSettingRow).values(name=name, payload=value)
        s.execute(stmt.on_conflict_do_update(index_elements=[AppSettingRow.name], set_={"payload": stmt.excluded.payload}))
        s.commit()


@app.put("/api/settings")
def put_settings(value: dict = Body(...)):
    store, assembly, hours = value.get("store"), value.get("assembly"), value.get("validHours")
    if (not isinstance(store, str) or len(store) > 100 or not _number(assembly) or not 0 <= assembly <= 500_000
            or not _number(hours) or not 1 <= hours <= 168):
        return error(400, "매장 설정이 올바르지 않습니다.")
    _put_setting("store", value)
    return value


@app.get("/api/state/{name}")
def get_state(name: str):
    if name not in STATE_NAMES:
        return error(404, "알 수 없는 상태")
    with session_factory()() as s:
        row = s.get(AppSettingRow, name)
        return row.payload if row else None


@app.put("/api/state/{name}")
def put_state(name: str, value=Body(...)):
    if name not in STATE_NAMES:
        return error(404, "알 수 없는 상태")
    _put_setting(name, value)
    return {"ok": True}


# --- catalog and pipeline ----------------------------------------------------------

@app.get("/api/catalog")
def get_catalog():
    return Response(service().get().snapshot_bytes(), media_type="application/json")


@app.get("/api/pipeline/status")
def pipeline_status():
    running = app.state.pipeline.running or (collector_owns_catalog() and lock_held("pipeline"))
    return {**(read_doc("pipeline-status") or {"status": "not_initialized"}), "running": running}


@app.get("/api/discovery/status")
def discovery_status():
    return read_doc("discovery-status") or {}


@app.get("/api/prices/snapshot")
def prices_snapshot():
    return read_doc("price-history") or {}


@app.post("/api/pipeline/run", status_code=202)
def pipeline_run():
    try:
        started = app.state.pipeline.start()
    except RuntimeError as e:
        return error(500, str(e))
    return {"status": "running"} if started else error(409, "이미 수집 중입니다.")


@app.post("/api/admin/catalog/reload")
def reload_catalog() -> dict:
    with session_factory()() as s:
        imported = importer.sync(s, force=True)
    service().invalidate()
    return {"reloadedAt": iso(utcnow()), "imported": imported, "parts": len(service().get().parts)}


# --- consultation --------------------------------------------------------------------

def _text(data: dict, message: str) -> str | None:
    text = data.get("text")
    return text if isinstance(text, str) and text.strip() and len(text) <= 2000 else None


@app.post("/api/requirements")
def requirements(data: dict = Body(...)):
    text = _text(data, "")
    if text is None:
        return error(400, "요청 내용을 1~2,000자로 입력하세요.")
    lookup = steam_games.lookup(text) if detect_profile(text) in (None, "gaming") else None
    if lookup:
        found = lookup['status'] == 'found'
        return {**parse_requirement(text), 'profile': 'gaming' if found else None,
                'method': 'local', 'questions': [], 'needsGame': not found,
                'gameLookup': lookup, 'message': game_answer(lookup)['text'] if not found else None}
    try:
        return llm.interpret(text, app.state.complete)
    except RuntimeError as e:
        return error(400, str(e))


@app.post("/api/answer")
def answer(data: dict = Body(...)):
    text = _text(data, "")
    if text is None:
        return error(400, "질문을 1~2,000자로 입력하세요.")
    lookup = steam_games.lookup(text)
    if lookup:
        return game_answer(lookup)
    state = service().get()
    history = [m for m in data.get("history") or [] if isinstance(m, dict) and isinstance(m.get("text"), str)]
    return llm.answer(text.strip(), complete=app.state.complete, catalog=list(state.parts.values()),
                      policy=state.meta.get("policy"), quote=data.get("quote"), history=history, now=utcnow())


def _valid_quote_request(requirement, settings) -> bool:
    assembly = (settings or {}).get("assembly")
    return (isinstance(requirement, dict) and requirement.get("profile") in screen.PROFILES
            and not requirement.get("needsPurpose") and screen.valid_budget(requirement) and _number(assembly) and 0 <= assembly <= 500_000)


@app.post("/api/recommend/fresh")
def recommend_fresh(data: dict = Body(...)):
    requirement, settings = data.get("requirement"), data.get("settings") or {}
    if not _valid_quote_request(requirement, settings):
        return error(400, "용도·예산·조립비를 확인해 주세요.")
    return screen.recommend_fresh(service(), requirement, settings, app.state.collect)


def _quote_parts(data: dict) -> tuple[dict, dict, dict] | JSONResponse:
    requirement, parts = data.get("requirement"), data.get("parts")
    if not isinstance(requirement, dict) or not isinstance(parts, dict):
        return error(400, "견적 정보가 필요합니다.")
    return requirement, data.get("settings") or {}, parts


@app.post("/api/quotes/evaluate")
def quotes_evaluate(data: dict = Body(...)):
    parsed = _quote_parts(data)
    if isinstance(parsed, JSONResponse):
        return parsed
    target = data.get("refreshPartId")
    state = service().get()
    if target is not None:
        selected = [value.get("id") if isinstance(value, dict) else value for value in parsed[2].values()]
        if not isinstance(target, str) or target not in selected or target not in state.parts:
            return error(400, "교체 구성에 있는 부품만 가격을 확인할 수 있습니다.")
        record = state.parts[target]
        if not record.get("virtual"):
            if app.state.collect is None:
                return error(503, "현재 가격 확인에 연결하지 못했습니다.")
            try:
                service().accept_price(target, app.state.collect(record))
            except Exception as e:
                return error(422, f"교체 부품의 현재 가격을 확인하지 못했습니다: {e}")
            state = service().get()
    result = screen.evaluate_quote(state, *parsed)
    if target is not None:
        result.update(parts={c: state.parts[pid] for c, value in parsed[2].items()
                             if (pid := value.get("id") if isinstance(value, dict) else value) in state.parts},
                      catalogVersion=state.version)
    return result


@app.post("/api/quotes/alternatives")
def quotes_alternatives(data: dict = Body(...)):
    parsed = _quote_parts(data)
    if isinstance(parsed, JSONResponse):
        return parsed
    category = str(data.get("category") or "")
    if category not in CATEGORIES:
        return error(422, "알 수 없는 부품군")
    return {"items": screen.alternative_ids(service().get(), *parsed, category)}


# --- issued quotes ---------------------------------------------------------------------

@app.get("/api/quotes")
def list_quotes():
    with session_factory()() as s:
        rows = s.scalars(select(SavedQuoteRow).order_by(SavedQuoteRow.created_at.desc()).limit(100))
        return [r.payload for r in rows]


@app.post("/api/quotes", status_code=201)
def save_quote(data: dict = Body(...)):
    state = service().get()
    plan = screen.validate_issue(state, data, utcnow())
    if isinstance(plan, tuple):
        status, body = plan
        return JSONResponse(body, status_code=status)
    now = utcnow()
    entry = {**data, "id": str(uuid.uuid4()), "date": iso(now), "plan": plan}
    with session_factory()() as s:
        s.add(SavedQuoteRow(id=entry["id"], created_at=now, payload=entry))
        s.commit()
    return entry


@app.post("/api/quotes/import")
def import_quote(entry: dict = Body(...)):
    try:
        date = datetime.fromisoformat(str(entry.get("date")).replace("Z", "+00:00"))
    except ValueError:
        date = None
    if (not isinstance(entry.get("id"), str) or not entry["id"] or date is None
            or not isinstance((entry.get("plan") or {}).get("parts"), dict) or not entry.get("req") or not entry.get("settings")):
        return error(400, "기존 견적 형식이 올바르지 않습니다.")
    with session_factory()() as s:
        s.execute(insert(SavedQuoteRow).values(id=entry["id"], created_at=date if date.tzinfo else date.replace(tzinfo=timezone.utc),
                                               payload=entry).on_conflict_do_nothing())
        s.commit()
    return {"ok": True}


@app.delete("/api/quotes/{quote_id}")
def delete_quote(quote_id: str):
    with session_factory()() as s:
        row = s.get(SavedQuoteRow, quote_id)
        if row is None:
            return error(404, "견적을 찾을 수 없습니다.")
        s.delete(row)
        s.commit()
    return {"ok": True}


# --- engine endpoints --------------------------------------------------------------------

class Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RecommendIn(Camel):
    budget: int | None = Field(default=None, ge=300_000, le=20_000_000)
    uses: list[str] = Field(default_factory=lambda: ["gaming"], min_length=1)
    resolution: str = "FHD"
    white: bool = False
    wifi: bool = False
    exclude_brands: list[str] = Field(default_factory=list)
    exclude_parts: list[str] = Field(default_factory=list, max_length=20_000)
    assembly_fee: int = Field(default=0, ge=0, le=500_000)
    memo: str = Field(default="", max_length=2000)


@app.get("/api/options")
def options() -> dict:
    return {"uses": list(USES), "resolutions": list(RESOLUTIONS), "categories": list(CATEGORIES)}


@app.get("/api/catalog/summary")
def catalog_summary() -> dict:
    catalog = service().get().catalog
    observed = [p.price_observed_at for p in catalog.parts if p.price_observed_at]
    return {
        "categories": {c: {"total": len(catalog.by_category[c]), "usable": len(catalog.usable(c))} for c in CATEGORIES},
        "oldestPriceAt": min(observed).isoformat() if observed else None,
        "newestPriceAt": max(observed).isoformat() if observed else None,
    }


@app.post("/api/recommend")
def recommend_endpoint(body: dict = Body(...)):
    """Engine output as is (no price refresh), for diagnosis."""
    try:
        data = RecommendIn.model_validate(body)
        req = EngineRequest(budget=data.budget, uses=tuple(dict.fromkeys(data.uses)), resolution=data.resolution,
                            white=data.white, wifi=data.wifi, exclude_brands=tuple(data.exclude_brands),
                            exclude_parts=tuple(data.exclude_parts), assembly_fee=data.assembly_fee, memo=data.memo)
    except (ValidationError, ValueError) as e:
        return error(422, str(e))
    started = time.perf_counter()
    catalog = service().get().catalog
    out = recommend(catalog, req).as_dict(catalog)
    out["elapsedMs"] = round((time.perf_counter() - started) * 1000)
    return out


# Agent API keeps the existing validated quote payload intact.
from .quote_agent import AgentRequest, create_quote

@app.post('/api/agent/quote')
async def agent_quote(data: AgentRequest):
    import asyncio
    try:
        return await create_quote(data, service(), app.state.collect)
    except ValueError as exc:
        return error(400, str(exc))
    except asyncio.TimeoutError:
        return error(504, '견적 생성 시간이 초과되었습니다.')
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Quote agent failed')
        return error(503, '견적 에이전트에 연결하지 못했습니다. 다시 시도해 주세요.')

@app.get('/api/agent/runs/{run_id}')
def agent_run(run_id: uuid.UUID):
    from .db import get_document
    with session_factory()() as session:
        result = get_document(session, f'agent-run:{run_id}')
    return result if result is not None else error(404, '실행 기록을 찾지 못했습니다.')


# The built consultation screen (``npm run build`` in buildmate) is served from the same server.
_DIST = importer.BUILDMATE / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="screen")
