"""Consultation-screen formats: requirement → engine request, engine plans → screen quotes.

The screen (buildmate React UI) sends ``requirement`` (profile, budget, resolution,
white, wifi, os…) and ``settings`` (assembly fee, excluded brands) and shows
quotes whose parts are full catalog records, including OS and the virtual
"no discrete GPU" option.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import datetime

from .engine.recommend import BUDGET_BAND, alternatives, evaluate, recommend
from .engine.requirements import Request
from .policy import price_state
from .service import CatalogService, PriceReviewPending, State

PROFILES = ("gaming", "editing", "office", "ai")
PLAN_SLOTS = {"balanced": 0, "performance": 1, "value": 2}
PLAN_IDS = ("balanced", "enhanced", "saving")
MIN_BUDGET = 300_000
NO_GPU, NO_OS, WITH_OS = "g0", "o0", "o1"


class ScreenError(Exception):
    """Request the engine cannot serve; the message is shown to staff."""


def has_budget(req: dict) -> bool:
    return req.get("budget") is not None


def valid_budget(req: dict) -> bool:
    b = req.get("budget")
    return b is None or (isinstance(b, (int, float)) and not isinstance(b, bool) and 200_000 <= b <= 20_000_000)


def budget_cap(req: dict) -> int:
    return math.floor(req["budget"] * (1 + BUDGET_BAND))


def os_part(req: dict, parts: dict[str, dict]) -> dict | None:
    return parts.get(WITH_OS) if req.get("os") else None


def to_request(req: dict, settings: dict, parts: dict[str, dict], exclude_parts: list[str] = ()) -> Request:
    """OS is not an engine category, so its price comes off the budget."""
    if not has_budget(req):
        raise ScreenError("예산을 알려 주세요. 추천 엔진은 예산 비율로 부품을 고릅니다.")
    os_price = (os_part(req, parts) or {}).get("price") or 0
    budget = int(req["budget"]) - os_price
    if budget < MIN_BUDGET:
        raise ScreenError(f"예산은 {MIN_BUDGET + os_price:,}원 이상이어야 합니다.")
    try:
        return Request(budget=budget, uses=(req.get("profile") or "gaming",), resolution=req.get("resolution") or "QHD",
                       white=bool(req.get("white")), wifi=bool(req.get("wifi")),
                       exclude_brands=tuple(settings.get("excludedBrands") or ()), exclude_parts=tuple(exclude_parts),
                       assembly_fee=int(settings.get("assembly") or 0), memo=str(req.get("text") or "")[:2000])
    except ValueError as e:
        raise ScreenError(str(e)) from e


def to_check(c: dict) -> dict:
    """warn = supported after a BIOS update: allowed, but shown to staff before shipping."""
    warn = c["status"] == "warn"
    return {"label": f"{c['label']} (출고 전 확인)" if warn else c["label"], "ok": c["status"] != "fail",
            "detail": c["detail"], **({"warning": True} if warn else {})}


def quote_total(parts: dict[str, dict], settings: dict) -> int:
    return sum(p.get("price") or 0 for p in parts.values()) + int(settings.get("assembly") or 0)


def engine_ids(parts: dict) -> dict[str, str | None]:
    """Screen part map (category → record or id) → engine ids; OS dropped, virtual GPU → None."""
    out = {}
    for category, value in parts.items():
        if category == "os":
            continue
        record = value if isinstance(value, dict) else None
        pid = record.get("id") if record else value
        out[category] = None if (record and record.get("virtual")) or pid == NO_GPU else pid
    return out


def bios_note(board: dict, warnings: list[str]) -> dict:
    board = {k: v for k, v in board.items() if not (k == "biosPreparation" and str(v).startswith("출고 전 확인:"))}
    return {**board, "biosPreparation": f"출고 전 확인: {' · '.join(warnings)}"} if warnings else board


def map_plan(plan: dict, state: State, req: dict, settings: dict, slot: int) -> dict | None:
    parts: dict[str, dict] = {}
    for category, part in plan["parts"].items():
        record = state.parts.get(part["id"] if part else NO_GPU if category == "gpu" else "")
        if record is None:
            return None
        parts[category] = record
    parts["os"] = os_part(req, state.parts) or state.parts.get(NO_OS) or {"id": NO_OS, "category": "os", "name": "OS 미포함",
                                                                         "price": 0, "virtual": True}
    warnings = [c["detail"] for c in plan["checks"] if c["status"] == "warn"]
    parts["board"] = bios_note(parts["board"], warnings)
    ranked = [p for p in plan["parts"].values() if p]
    return {
        "id": PLAN_IDS[slot], "engine": "pcquote", "label": plan["label"], "summary": plan["summary"], "parts": parts,
        "checks": [to_check(c) for c in plan["checks"]], "total": quote_total(parts, settings), "budgetCap": budget_cap(req),
        "performance": plan["performance"], "popularity": plan["popularity"], "balance": plan["balance"],
        "performanceBasis": {"label": f"성능 지수 {plan['performance']}",
                             "limitation": "CPU·GPU Blender 실측 점수를 용도 가중치로 합친 값입니다. 게임 FPS 실측이 아닙니다."},
        "selection": {"popularity": {"known": sum(1 for p in ranked if p.get("popularityRank")), "total": len(ranked)}},
        "reasons": {c: p["reason"] for c, p in plan["parts"].items() if p and p.get("reason")},
        "warnings": plan.get("warnings") or [], "dataMode": "live", "catalogVersion": state.version,
    }


def map_result(result: dict, state: State, req: dict, settings: dict) -> dict:
    plans: list[dict | None] = [None, None, None]
    for plan in result["plans"]:
        slot = PLAN_SLOTS.get(plan["type"])
        mapped = map_plan(plan, state, req, settings, slot) if slot is not None else None
        if mapped:
            plans[slot] = mapped
    notes = result.get("notes") or []
    message = None if any(plans) else (" ".join(notes) or "조건을 만족하는 견적을 만들지 못했습니다.")
    return {"plans": plans, "message": message, "notes": notes}


def recommend_fresh(service: CatalogService, req: dict, settings: dict, collect: Callable[[dict], dict] | None,
                    rounds: int = 6) -> dict:
    """Recommend, refresh stale prices of the chosen parts, re-plan until every chosen part is current.

    ``collect(record)`` returns a Danawa price observation. Parts whose refresh fails
    are excluded from the next round.
    """
    failed: list[str] = []
    attempted: set[str] = set()
    errors: list[dict] = []
    updated = 0
    for round_ in range(rounds + 1):
        state = service.get()
        result = recommend(state.catalog, to_request(req, settings, state.parts, failed)).as_dict(state.catalog)
        if collect is None or round_ == rounds:
            break
        now = state.loaded_at
        chosen = {p["id"] for plan in result["plans"] for p in plan["parts"].values() if p}
        stale = [state.parts[i] for i in sorted(chosen)
                 if i in state.parts and i not in attempted and price_state(state.parts[i], now) != "fresh"]
        if not stale:
            break
        for record in stale:
            attempted.add(record["id"])
            try:
                service.accept_price(record["id"], collect(record))
                updated += 1
            except (PriceReviewPending, Exception) as e:  # noqa: BLE001 — any collection failure excludes the part
                failed.append(record["id"])
                errors.append({"id": record["id"], "error": str(e)})
    state = service.get()
    return {**map_result(result, state, req, settings), "catalogVersion": state.version, "engine": "pcquote",
            "refresh": {"updated": updated, "errors": errors}}


def evaluate_quote(state: State, req: dict, settings: dict, parts: dict) -> dict:
    data = evaluate(state.catalog, to_request(req, settings, state.parts), engine_ids(parts))
    if data.get("ok") is False and data.get("error"):
        raise ScreenError(data["error"])
    return {"checks": [to_check(c) for c in data["checks"]], "performance": data["performance"],
            "popularity": data["popularity"], "warnings": [c["detail"] for c in data["checks"] if c["status"] == "warn"],
            "total": data["total"]}


def alternative_ids(state: State, req: dict, settings: dict, parts: dict, category: str) -> list[dict]:
    return alternatives(state.catalog, to_request(req, settings, state.parts), engine_ids(parts), category, limit=2000)


def validate_issue(state: State, data: dict, now: datetime) -> tuple[int, dict] | dict:
    """Server-side check before an issued quote is stored; returns the stored plan or (status, error)."""
    from .policy import usable_part

    plan, req, settings = data.get("plan") or {}, data.get("req") or {}, data.get("settings") or {}
    if not isinstance(plan.get("parts"), dict):
        return 400, {"error": "견적이 없습니다."}
    parts: dict[str, dict] = {}
    for category, p in plan["parts"].items():
        known = state.parts.get((p or {}).get("id"))
        if not known or known.get("category") != category:
            return 400, {"error": "등록되지 않은 부품입니다."}
        if not usable_part(known, now):
            return 422, {"error": "누락·만료·품절 데이터가 포함되어 있습니다."}
        if known.get("price") != p.get("price"):
            return 409, {"error": "부품 가격이 변경되었습니다. 최신 데이터로 다시 생성해 주세요."}
        parts[category] = known
    if data.get("catalogVersion") != state.version:
        return 409, {"error": "가격 스냅샷이 변경되었습니다. 최신 데이터로 다시 생성해 주세요."}
    assembly = settings.get("assembly", 0)
    if not isinstance(assembly, (int, float)) or not 0 <= assembly <= 500_000:
        return 400, {"error": "조립비 오류"}
    if req.get("profile") not in PROFILES or not has_budget(req) or not valid_budget(req):
        return 422, {"error": "허용 예산을 초과했습니다."}
    try:
        result = evaluate_quote(state, req, settings, parts)
    except ScreenError as e:
        return 422, {"error": str(e)}
    if any(not c["ok"] for c in result["checks"]):
        return 422, {"error": "호환성 오류가 있습니다.", "checks": result["checks"]}
    amount = quote_total(parts, settings)
    if amount > budget_cap(req):
        return 422, {"error": "허용 예산을 초과했습니다."}
    parts["board"] = bios_note(parts["board"], result["warnings"])
    return {**plan, "parts": parts, "total": amount, "checks": result["checks"], "performance": result["performance"],
            "performanceBasis": {"label": f"성능 지수 {result['performance']}",
                                 "limitation": "CPU·GPU Blender 실측 점수를 용도 가중치로 합친 값입니다. 게임 FPS 실측이 아닙니다."}}
