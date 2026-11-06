"""Consultation text rules, ported from buildmate (src/engine.mjs, question-answer.mjs, budget-policy.mjs).

The screen runs the same JavaScript rules locally; the server copy must give the
same result (tests compare both on sample sentences).
"""

from __future__ import annotations

import math
import re

from .policy import usable_part

_ADD = re.compile(r"\n추가 요청:\s*")
_BUDGET = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(만\s*원?|원)")
_EDITING = re.compile(r"편집|프리미어|다빈치|렌더|3D|어도비|adobe|premiere|포토샵|photoshop|라이트룸|lightroom|일러스트레이터|"
                      r"illustrator|애프터\s*이펙트|after\s*effects|블렌더|blender", re.I)
_AI = re.compile(r"로컬|딥러닝|LLM|개발|AI", re.I)
_OFFICE = re.compile(r"사무|엑셀|학습|POS", re.I)
_GAMING = re.compile(r"게임|게이밍|배그|롤|gaming", re.I)
_LIGHT = re.compile(r"인터넷|웹\s*서핑|웹\s*브라우|문서|인강|온라인\s*강의|유튜브|동영상\s*시청", re.I)
_UNLIMITED = re.compile(r"예산\s*(?:제한\s*없|상관\s*없|무관|무제한)|(?:돈|가격|비용)\s*(?:은|는|이)?\s*상관\s*없|금액\s*제한\s*없", re.I)
# JavaScript \b is ASCII-only; re.ASCII keeps "p\b" etc. behaving the same before Korean text.
_MODEL = re.compile(r"(rtx|gtx|rx|i[3579]-?)?\s?(\d{3,5})\s?(x3d2?|xtx|xt|gre|ti\s?super|ti|super|kf|ks|k|f|x|g)?"
                    r"(?![\d만원,.]|\s?(?:만|원|p\b|hz|gb|tb|w\b))", re.I | re.ASCII)


def money(n: int | float) -> str:
    return f"{round(n):,}원"


def explicit_budget(text: str) -> int | None:
    matches = list(_BUDGET.finditer(text))
    if not matches:
        return None
    number, unit = matches[-1].groups()
    value = float(number.replace(",", "")) * (10000 if unit.startswith("만") else 1)
    return int(math.floor(value + 0.5))  # JavaScript Math.round


def detect_profile(value: str) -> str | None:
    if _EDITING.search(value):
        return "editing"
    if _AI.search(value):
        return "ai"
    if _OFFICE.search(value):
        return "office"
    if _GAMING.search(value):
        return "gaming"
    if _LIGHT.search(value):
        return "office"
    return None


def unlimited_budget_requested(text: str) -> bool:
    return bool(_UNLIMITED.search(_ADD.split(text)[-1]))


def model_tokens(text) -> list[str]:
    tokens: list[str] = []
    for m in _MODEL.finditer(str(text or "").lower()):
        prefix, digits, suffix = m.groups()
        if not prefix and not suffix and (len(digits) != 4 or digits in ("1080", "1440", "2160")):
            continue
        token = digits + re.sub(r"\s", "", suffix or "")
        if token not in tokens:
            tokens.append(token)
    return tokens


def model_key(part: dict) -> str | None:
    if part.get("category") not in ("cpu", "gpu") or part.get("virtual"):
        return None
    tokens = model_tokens(part.get("benchmarkName") or part.get("name"))
    return tokens[-1] if tokens else None


def _resolution_of(value: str) -> str | None:
    if re.search(r"4k", value, re.I):
        return "4K"
    if re.search(r"FHD|1080", value, re.I):
        return "FHD"
    if re.search(r"QHD|1440", value, re.I):
        return "QHD"
    return "FHD" if detect_profile(value) == "office" else None


def parse_requirement(text: str, options: dict | None = None) -> dict:
    options = options or {}
    stated = explicit_budget(text)
    requests = _ADD.split(text)
    profiles = [p for p in map(detect_profile, requests) if p]
    resolutions = [r for r in map(_resolution_of, requests) if r]
    unlimited = unlimited_budget_requested(text)
    out = {
        "text": text, "profile": profiles[-1] if profiles else "gaming", "budget": stated,
        "resolution": resolutions[-1] if resolutions else "QHD", "models": model_tokens(text),
        "white": bool(re.search(r"화이트|흰색", text)), "wifi": bool(re.search(r"와이파이|무선|wifi", text, re.I)),
        "os": bool(re.search(r"윈도우|windows|OS 포함", text, re.I)), "allowOver": False, **options,
    }
    if unlimited:
        out.update(budget=None, allowOver=False)
    if unlimited:
        out["budgetSource"] = "unlimited"
    elif options.get("budget") is not None:
        out["budgetSource"] = "text" if stated is not None else "manual"
    else:
        out["budgetSource"] = "text" if stated is not None else "unspecified"
    return out


def merge_interpretation(text: str, llm: dict) -> dict:
    """Text the customer stated wins; the LLM only names a purpose the rules cannot detect and adds questions."""
    local = parse_requirement(text)
    stated = any(detect_profile(v) for v in _ADD.split(text))
    return {**local, "profile": local["profile"] if stated else llm.get("profile"),
            "questions": [q for q in (llm.get("questions") or []) if "예산" not in q]}


def _resolution_question(text: str) -> str | None:
    if re.search(r"4k|2160", text, re.I):
        return "4K"
    if re.search(r"qhd|1440", text, re.I):
        return "QHD"
    if re.search(r"fhd|1080", text, re.I):
        return "FHD"
    return None


def _js_number(value) -> str:
    return str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)


def answer_question(text: str, catalog: list[dict], policy: dict | None, now) -> dict:
    """Catalog-only answer; never asserts game FPS, which the catalog does not hold."""
    policy = policy or {}
    tokens = model_tokens(text)
    resolution = _resolution_question(text)
    gaming = bool(re.search(r"게임|게이밍|fps|프레임|배그|롤", text, re.I)) or bool(resolution)
    groups = [(t, [p for p in catalog if model_key(p) == t]) for t in tokens]
    groups = [(t, parts) for t, parts in groups if parts]
    if not groups:
        return {"text": "질문에 나온 제품을 카탈로그에서 찾지 못했어요. 제품 모델명(예: RTX 5060 Ti, 9800X3D)으로 다시 물어봐 주세요."}
    lines = []
    for _, parts in groups:
        sample = next((p for p in parts if p.get("benchmarkName")), parts[0])
        name = sample.get("benchmarkName") or sample.get("name")
        usable = [p for p in parts if usable_part(p, now)]
        priced = [p for p in (usable or parts) if isinstance(p.get("price"), (int, float)) and p["price"] > 0]
        low = min((p["price"] for p in priced), default=None)
        vram = sorted({p["vram"] for p in parts if isinstance(p.get("vram"), (int, float))}) if sample.get("category") == "gpu" else []
        score = (sample.get("benchmark") or {}).get("normalizedScore")
        bits = [f"{name}: 카탈로그 {len(parts)}개 제품",
                f"VRAM {'·'.join(_js_number(v) for v in vram)}GB" if vram else None,
                f"최저 {money(low)}{'' if usable else ' (가격 갱신 필요)'}" if low is not None else None,
                f"Blender 렌더링 지수 {_js_number(score)}" if isinstance(score, (int, float)) else None]
        lines.append(" · ".join(b for b in bits if b))
    notes = []
    if any(isinstance((p.get("benchmark") or {}).get("normalizedScore"), (int, float)) for _, parts in groups for p in parts):
        m = re.search(r"CPU[^.]*=100[^.]*", policy.get("scoreMethod") or "")
        notes.append(f"Blender 지수는 렌더링 성능{f'({m.group(0).strip()} 기준)' if m else ''}이며 게임 FPS가 아니에요.")
    if gaming:
        notes.append(f"{resolution + ' ' if resolution else ''}게임 FPS 실측 자료가 없어 실행 가능 여부나 프레임을 단정할 수 없어요.")
    return {"text": "\n".join(lines + notes)}
