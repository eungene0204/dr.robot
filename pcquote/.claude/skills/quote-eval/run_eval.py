"""Customer-scenario evaluation of the quote pipeline: interpretation → screen requirement → engine plans.

Runs every case in cases.json the way the consultation screen does (buildmate main.jsx ``send``),
then judges the result against the case's expectations and the store rules.

    cd pcquote/backend
    uv run python ../.claude/skills/quote-eval/run_eval.py              # LLM interpretation (OpenRouter)
    uv run python ../.claude/skills/quote-eval/run_eval.py --local      # rules only, no LLM
    uv run python ../.claude/skills/quote-eval/run_eval.py --only G03,X04

Prices are not refreshed from Danawa (collect=None), so plans use the stored snapshot.
Verdicts: FAIL = spec'd behaviour broken, GAP = customer demand the system does not serve,
WARN = suspicious but allowed, INFO = context only (e.g. stale snapshot prices; does not change the case status). Report: pcquote/reports/quote-eval/<timestamp>.{json,md}.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from pcquote import importer, llm, screen
from pcquote.consult import _resolution_of, budget_change, detect_profile, explicit_budget, model_key, parse_requirement, unlimited_budget_requested
from pcquote.engine.requirements import POOL_FLOOR, min_specs
from pcquote.policy import price_state
from pcquote.service import CatalogService

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # pcquote/
PLAN_ORDER = ("enhanced", "balanced", "saving")


# --- screen requirement (mirror of buildmate main.jsx send/applyText) -----------------------

def screen_requirement(turns: list[str], interpret) -> dict:
    req = None
    interpretation_steps = []
    for prompt in turns:
        own = parse_requirement(prompt)
        fresh = req is None or (not req.get("needsPurpose") and bool(detect_profile(prompt) and detect_profile(prompt) != req["profile"]))
        context = prompt if fresh else f"{req['text']}\n추가 요청: {prompt}"
        interpreted = interpret(context)
        interpretation_steps.append({"method": interpreted.get("method"), "fallback": interpreted.get("fallback")})
        if fresh:
            ui = {"white": own["white"], "wifi": own["wifi"], "os": own["os"]}
        else:  # applyText sets the UI state from the local parse of the combined context
            p = parse_requirement(context)
            ui = {k: p[k] for k in ("white", "wifi", "os")}
            if any(detect_profile(v) for v in context.split("\n추가 요청:")):
                ui["profile"] = p["profile"]
            if any(_resolution_of(v) for v in context.split("\n추가 요청:")):
                ui["resolution"] = p["resolution"]
        stated, change = explicit_budget(prompt), budget_change(prompt)
        if unlimited_budget_requested(prompt):
            budget = None
        elif not fresh and req.get("budget") is not None and change is not None:  # "10만원만 더 올려줘"
            budget = req["budget"] + change
        else:
            budget = stated if stated is not None else (None if fresh else req.get("budget"))
        req = parse_requirement(context, {**interpreted, **ui, "budget": budget, "allowOver": False})
        if interpreted.get("needsPurpose"):
            req.update(profile=None, needsPurpose=True)
    req["interpretationSteps"] = interpretation_steps
    return req


# --- judging -----------------------------------------------------------------------------------

class Verdicts:
    def __init__(self):
        self.items: list[dict] = []

    def add(self, level: str, check: str, detail: str, plan: str | None = None):
        self.items.append({"level": level, "check": check, "detail": detail, **({"plan": plan} if plan else {})})


def lowered(notice: str, pattern: str, default: int) -> int:
    """Minimum size after the engine lowered it ("메모리 32GB → 16GB"), else the rule's minimum."""
    found = re.findall(pattern, notice)
    if not found:
        return default
    number = float(re.match(r"[\d.]+", found[-1]).group())
    return int(number * 1000) if found[-1].endswith("TB") else int(number)


def won(n) -> str:
    return f"{int(n):,}원"


def check_interpretation(v: Verdicts, req: dict, expect: dict):
    for key in ("profile", "resolution"):
        if key in expect and req.get(key) != expect[key]:
            v.add("FAIL", f"해석:{key}", f"기대 {expect[key]}, 실제 {req.get(key)}")
    if "budget" in expect:
        want, got = expect["budget"], req.get("budget")
        ok = (got is None) if want is None else (
            got is not None and (want[0] <= got <= want[1] if isinstance(want, list) else got == want))
        if not ok:
            v.add("FAIL", "해석:budget", f"기대 {want}, 실제 {got}")
    for key in ("white", "wifi", "os"):
        if bool(req.get(key)) != bool(expect.get(key, False)):
            v.add("FAIL", f"해석:{key}", f"기대 {bool(expect.get(key, False))}, 실제 {bool(req.get(key))}")


def cheaper_equivalent(state, record: dict) -> dict | None:
    """Cheapest usable part with the same key spec, when ≥30% and ≥30,000원 cheaper."""
    category = record["category"]
    keyers = {"ram": lambda r: (r.get("ddr"), r.get("capacity"), r.get("sticks")),
              "ssd": lambda r: (r.get("capacity"),),
              "gpu": lambda r: (model_key(r), r.get("vram")),
              "cpu": lambda r: (model_key(r),)}
    if category not in keyers or record.get("virtual"):
        return None
    key = keyers[category](record)
    if None in key:
        return None
    best = None
    for part in state.catalog.usable(category):
        other = state.parts.get(part.id)
        if other and keyers[category](other) == key and (best is None or part.price < best["price"]):
            best = other
    price = record.get("price") or 0
    if best and best["id"] != record["id"] and best["price"] <= price * 0.7 and price - best["price"] >= 30_000:
        return best
    return None


def check_plan(v: Verdicts, state, plan: dict, req: dict, settings: dict, expect: dict, specs, notice: str):
    pid, parts = plan["id"], plan["parts"]
    total, cap = plan["total"], plan["budgetCap"]
    summed = sum(p.get("price") or 0 for p in parts.values()) + int(settings.get("assembly") or 0)
    if summed != total:
        v.add("FAIL", "합계", f"부품 합 {won(summed)} ≠ 표시 합계 {won(total)}", pid)
    if cap is not None and total > cap:
        v.add("FAIL", "예산 초과", f"{won(total)} > 예산 {won(cap)}", pid)
    elif cap is not None and total < cap * POOL_FLOOR:
        v.add("WARN", "예산 활용", f"{won(total)}는 예산의 {total / cap:.0%}", pid)
    for c in plan["checks"]:
        if not c["ok"]:
            v.add("FAIL", "호환성", f"{c['label']}: {c['detail']}", pid)

    cpu, board, ram, gpu, ssd, psu, case = (parts.get(k) or {} for k in ("cpu", "board", "ram", "gpu", "ssd", "psu", "case"))
    if cpu.get("socket") != board.get("socket"):
        v.add("FAIL", "소켓", f"CPU {cpu.get('socket')} / 보드 {board.get('socket')}", pid)
    if ram.get("ddr") != board.get("ddr"):
        v.add("FAIL", "메모리 규격", f"RAM DDR{ram.get('ddr')} / 보드 DDR{board.get('ddr')}", pid)
    if not gpu.get("virtual") and (psu.get("capacity") or 0) < (gpu.get("minPsu") or 0):
        v.add("FAIL", "파워 용량", f"{psu.get('capacity')}W < 그래픽카드 권장 {gpu.get('minPsu')}W", pid)
    if not gpu.get("virtual") and (gpu.get("watts") or 0) >= 150 and (psu.get("price") or 0) < 30_000:
        v.add("WARN", "저가 파워", f"{gpu.get('watts')}W 그래픽카드에 {won(psu.get('price') or 0)} 파워({psu.get('name')})", pid)

    relaxed = notice or ""
    declined = "반영하지 못했어요" in relaxed  # preference given up and told to the customer
    ram_min = lowered(relaxed, r"메모리 \S+ → (\S+?)[,.]", specs.ram_gb)
    ssd_min = lowered(relaxed, r"SSD \S+ → (\S+?)[,.]", specs.ssd_gb)
    gpu_ref = (re.findall(r"그래픽카드 기준 .+? → (.+?)급", relaxed) or [specs.gpu_reference])[-1]
    gpu_floor = (state.catalog.benchmark_of("gpu", gpu_ref) or 0) if gpu_ref else 0
    gap = "WARN" if declined else "GAP"
    if (ram.get("capacity") or 0) < max(ram_min, expect.get("minRamGb", 0)):
        level = "FAIL" if (ram.get("capacity") or 0) < ram_min else gap
        v.add(level, "메모리 용량", f"{ram.get('capacity')}GB < {max(ram_min, expect.get('minRamGb', 0))}GB", pid)
    if (ssd.get("capacity") or 0) < max(ssd_min, expect.get("minSsdGb", 0)):
        level = "FAIL" if (ssd.get("capacity") or 0) < ssd_min else gap
        v.add(level, "SSD 용량", f"{ssd.get('capacity')}GB < {max(ssd_min, expect.get('minSsdGb', 0))}GB", pid)
    if specs.gpu_vram_gb and (gpu.get("vram") or 0) < specs.gpu_vram_gb:
        v.add("FAIL", "VRAM", f"{gpu.get('vram')}GB < 규칙 {specs.gpu_vram_gb}GB", pid)
    if expect.get("minVramGb") and (gpu.get("vram") or 0) < expect["minVramGb"]:
        v.add(gap, "VRAM 요청", f"{gpu.get('vram')}GB < 고객 요청 {expect['minVramGb']}GB", pid)
    engine_gpu = state.catalog.by_id.get(gpu.get("id"))
    if gpu_floor and (not engine_gpu or (engine_gpu.benchmark or 0) < gpu_floor * 0.999):
        v.add("FAIL", "GPU 하한", f"{gpu.get('name')}가 {gpu_ref}급 미만", pid)
    if req.get("profile") == "office" and not gpu.get("virtual"):
        v.add("WARN", "사무용 그래픽카드", f"사무용에 {gpu.get('name')} 포함", pid)

    if req.get("white") and case.get("color") != "white":
        v.add("FAIL", "화이트", f"케이스 {case.get('name')}", pid)
    if req.get("white"):
        dark = [c for c in ("cooler",) if (parts.get(c) or {}).get("color") not in (None, "white")]
        if dark:
            v.add("GAP", "화이트 통일", ", ".join(f"{c}: {parts[c].get('name')}" for c in dark), pid)
    if req.get("wifi") and not board.get("wifi"):
        v.add("FAIL", "와이파이", f"보드 {board.get('name')}", pid)
    os_part = parts.get("os") or {}
    if req.get("os") and (os_part.get("virtual") or not os_part.get("price")):
        v.add("FAIL", "윈도우", "OS가 견적에 없음", pid)
    for brand in settings.get("excludedBrands") or []:
        hit = [c for c, p in parts.items() if brand.lower() in f"{p.get('brand') or ''} {p.get('name') or ''}".lower()]
        if hit:
            v.add("FAIL", "제외 브랜드", f"{brand}: {', '.join(hit)}", pid)

    stale = [c for c, p in parts.items() if not p.get("virtual") and p.get("category") != "os"
             and price_state(p, state.loaded_at) != "fresh"]
    if stale:
        v.add("INFO", "가격 신선도", f"갱신 필요 {len(stale)}개: {', '.join(stale)}", pid)
    for c, p in parts.items():
        alt = cheaper_equivalent(state, p)
        if alt:
            v.add("WARN", "같은 사양 더 저렴", f"{c} {p.get('name')} {won(p['price'])} → {alt.get('name')} {won(alt['price'])}", pid)

    if pid == "balanced":
        for category, tokens in (expect.get("models") or {}).items():
            if model_key(parts.get(category) or {}) not in tokens:
                v.add(gap, "모델 지정", f"{category} 요청 {'/'.join(tokens)}, 실제 {(parts.get(category) or {}).get('name')}", pid)
        for category, names in (expect.get("brands") or {}).items():
            text = f"{(parts.get(category) or {}).get('brand') or ''} {(parts.get(category) or {}).get('name') or ''}"
            if not any(n.lower() in text.lower() for n in names):
                v.add(gap, "브랜드 지정", f"{category} 요청 {'/'.join(names)}, 실제 {(parts.get(category) or {}).get('name')}", pid)


def check_plans(v: Verdicts, out: dict, expect: dict):
    plans = {p["id"]: p for p in out["plans"] if p}
    want = expect.get("plans", "any")
    if want == "none":
        if plans:
            v.add("FAIL", "견적 수", f"견적이 없어야 하는데 {len(plans)}안 생성")
        elif not out.get("message"):
            v.add("FAIL", "안내", "견적이 없는데 안내 메시지가 없음")
        return plans
    if not plans:
        v.add("FAIL", "견적 수", f"견적 없음: {out.get('message')}")
    elif want == "full" and len(plans) < 3:
        missing = [k for k in PLAN_ORDER if k not in plans]
        v.add("FAIL", "견적 수", f"3안 기대, 누락 {missing}: {' / '.join(out.get('notes') or [])}")
    ordered = [plans[k] for k in PLAN_ORDER if k in plans]
    for hi, lo in zip(ordered, ordered[1:]):
        if hi["total"] < lo["total"]:
            v.add("FAIL", "안 순서", f"{hi['id']} {won(hi['total'])} < {lo['id']} {won(lo['total'])}")
    if "enhanced" in plans and "balanced" in plans and plans["enhanced"]["performance"] < plans["balanced"]["performance"]:
        v.add("FAIL", "안 순서", f"성능 강화안 성능 {plans['enhanced']['performance']} < 균형안 {plans['balanced']['performance']}")
    seen = {}
    for p in ordered:
        key = tuple(sorted((c, x.get("id")) for c, x in p["parts"].items()))
        if key in seen:
            v.add("WARN", "중복 안", f"{p['id']}가 {seen[key]}와 부품이 같음")
        seen[key] = p["id"]
    return plans


def summarize_plan(p: dict) -> dict:
    return {"id": p["id"], "total": p["total"], "performance": p["performance"], "popularity": p["popularity"],
            "parts": {c: {"name": x.get("name"), "price": x.get("price")} for c, x in p["parts"].items()}}


def run_case(case: dict, state_service: CatalogService, interpret) -> dict:
    started = time.perf_counter()
    expect, settings = case.get("expect") or {}, {"assembly": 0, **(case.get("settings") or {})}
    v = Verdicts()
    try:
        req = screen_requirement(case["turns"], interpret)
    except Exception as e:  # noqa: BLE001 — reported as a case failure
        v.add("FAIL", "해석 오류", str(e))
        return {"id": case["id"], "group": case["group"], "turns": case["turns"], "verdicts": v.items,
                "ms": round((time.perf_counter() - started) * 1000)}
    if req.get("needsPurpose"):
        # A declined interpretation is a distinct, safe outcome; never run the engine with a guessed use.
        if req.get("profile") is not None or not req.get("questions"):
            v.add("FAIL", "용도 확인", "미확인 용도를 가정했거나 확인 질문이 없음")
        v.add("INFO" if expect.get("clarificationOnFallback") else "FAIL", "용도 확인 필요",
              "용도가 확인되지 않아 견적을 생성하지 않고 추가 답변을 요청함")
        return {"id": case["id"], "group": case["group"], "turns": case["turns"],
                "requirement": req, "needsPurpose": True, "message": llm.USE_QUESTION,
                "plans": [], "verdicts": v.items, "ms": round((time.perf_counter() - started) * 1000)}
    check_interpretation(v, req, expect)
    out, plans = {"plans": [], "notes": [], "message": None, "notice": None}, {}
    try:
        out = screen.recommend_fresh(state_service, req, settings, None)
    except screen.ScreenError as e:
        out["message"] = str(e)
    state = state_service.get()
    plans = check_plans(v, out, expect)
    if plans:
        engine_req = screen.to_request(req, settings, state.parts)
        if "반영하지 못했어요" in (out.get("notice") or ""):  # the engine dropped the customer's preferences
            engine_req = engine_req.without_preferences()
        specs = min_specs(engine_req, state.catalog)
        for p in plans.values():
            check_plan(v, state, p, req, settings, expect, specs, out.get("notice") or "")
    return {"id": case["id"], "group": case["group"], "turns": case["turns"],
            "requirement": {k: req.get(k) for k in ("profile", "budget", "budgetSource", "resolution", "white", "wifi", "os",
                                                     "models", "method", "questions", "interpretationSteps")},
            "message": out.get("message"), "notice": out.get("notice"), "notes": out.get("notes"),
            "plans": [summarize_plan(p) for p in plans.values()], "verdicts": v.items,
            "ms": round((time.perf_counter() - started) * 1000)}


def status(result: dict) -> str:
    levels = {i["level"] for i in result["verdicts"]}
    return next((l for l in ("FAIL", "GAP", "WARN") if l in levels), "PASS")


def write_report(results: list[dict], meta: dict, tag: str = "") -> Path:
    out_dir = ROOT / "reports" / "quote-eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S") + (f"-{tag}" if tag else "")
    (out_dir / f"{stamp}.json").write_text(json.dumps({"meta": meta, "results": results}, ensure_ascii=False, indent=1))
    counts = {s: sum(status(r) == s for r in results) for s in ("PASS", "WARN", "GAP", "FAIL")}
    lines = [f"# 견적 시나리오 평가 {stamp}", "",
             f"해석: {meta['interpret']} · 카탈로그 {meta['catalogVersion']} · 케이스 {len(results)}개 · "
             + " · ".join(f"{k} {v}" for k, v in counts.items()), "",
             "| ID | 그룹 | 결과 | 고객 요청 | 해석 | 균형안 |", "| --- | --- | --- | --- | --- | --- |"]
    for r in results:
        req = r.get("requirement") or {}
        bal = next((p for p in r.get("plans") or [] if p["id"] == "balanced"), None)
        interp = f"{req.get('profile')}/{req.get('budget')}/{req.get('resolution')}" + "".join(
            f"/{k}" for k in ("white", "wifi", "os") if req.get(k))
        lines.append(f"| {r['id']} | {r['group']} | {status(r)} | {' → '.join(r['turns'])} | {interp} | "
                     f"{won(bal['total']) if bal else (r.get('message') or '-')} |")
    lines += ["", "## 판정 상세", ""]
    for r in results:
        if not r["verdicts"]:
            continue
        lines.append(f"### {r['id']} {status(r)} — {' → '.join(r['turns'])}")
        for i in r["verdicts"]:
            lines.append(f"- **{i['level']}** {i['check']}{' (' + i['plan'] + ')' if i.get('plan') else ''}: {i['detail']}")
        lines.append("")
    path = out_dir / f"{stamp}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def replay_llm(path: Path, missing: dict):
    """A stand-in for the OpenRouter call that answers from a file of recorded interpretations.

    merge_interpretation keeps only the LLM's profile (when the rules detect none) and its questions, so only texts
    without a rule-detected profile need a recorded answer; others get the rule reading. Texts with no answer are
    collected in `missing` and also fall back to the rule reading.
    """
    answers = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def complete(messages, **_):
        text = messages[-1]["content"]
        if text in answers:
            return answers[text]
        local = parse_requirement(text)
        stub = {k: local[k] for k in ("resolution", "white", "wifi", "os")}
        stub |= {"profile": local["profile"], "budget": local["budget"] if 200_000 <= (local["budget"] or 0) <= 20_000_000 else None,
                 "questions": []}
        if not any(detect_profile(v) for v in text.split("\n추가 요청:")):
            missing[text] = stub
        return stub
    return complete


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", action="store_true", help="LLM 없이 규칙 해석만 사용")
    ap.add_argument("--only", help="쉼표로 구분한 케이스 ID")
    ap.add_argument("--cases", default=str(HERE / "cases.json"))
    ap.add_argument("--tag", default="", help="보고서 파일 이름 뒤에 붙일 표시(병렬 실행 구분)")
    ap.add_argument("--replay", help="LLM 대신 쓸 해석 답 파일(JSON: 화면이 보낸 문장 → REQUIREMENT_SCHEMA 답)")
    args = ap.parse_args()

    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))["cases"]
    if args.only:
        wanted = set(args.only.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    complete, missing = None, {}
    if args.replay:
        complete = replay_llm(Path(args.replay), missing)
    elif not args.local:
        llm.load_env_files([ROOT / "backend" / ".env", importer.BUILDMATE / ".env"])
        complete = llm.configured_llm()
        if complete is None:
            print("LLM API 키/모델 설정이 없습니다. --local로 실행하세요.", file=sys.stderr)
            return 2
    interpret = lambda text: llm.interpret(text, complete)  # noqa: E731
    service = CatalogService()
    results = []
    for case in cases:
        r = run_case(case, service, interpret)
        results.append(r)
        print(f"{status(r):4} {r['id']} {r['ms']:>6}ms  {' → '.join(r['turns'])[:60]}", flush=True)
        for i in r["verdicts"]:
            if i["level"] in ("FAIL", "GAP"):
                print(f"       {i['level']} {i['check']}{' (' + i['plan'] + ')' if i.get('plan') else ''}: {i['detail']}")
    if missing:
        out = Path(args.replay).with_suffix(f".missing{('-' + args.tag) if args.tag else ''}.json")
        out.write_text(json.dumps(missing, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"답이 없는 문장 {len(missing)}개(규칙 해석으로 대신함): {out}", file=sys.stderr)
    meta = {"interpret": f"replay:{Path(args.replay).name}" if args.replay else "local" if args.local else (os.environ.get("EXAONE_MODEL", "k-exaone_v2.5") if getattr(complete, "provider", None) == "exaone" else os.environ.get("OPENROUTER_MODEL")),
            "catalogVersion": service.get().version, "ranAt": datetime.now().isoformat(timespec="seconds")}
    path = write_report(results, meta, args.tag)
    counts = {s: sum(status(r) == s for r in results) for s in ("PASS", "WARN", "GAP", "FAIL")}
    print("\n" + " · ".join(f"{k} {v}" for k, v in counts.items()) + f"\n보고서: {path}")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
