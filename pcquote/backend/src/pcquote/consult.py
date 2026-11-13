"""Consultation text rules, ported from buildmate (src/engine.mjs, question-answer.mjs, budget-policy.mjs).

The screen runs the same JavaScript rules locally; the server copy must give the
same result (tests compare both on sample sentences).
"""

from __future__ import annotations

import math
import re

from .policy import usable_part

_ADD = re.compile(r"\n추가 요청:\s*")
# Digits ("150만원", "1,500,000원") or Korean numerals mixed with digits ("백오십만원", "2백만원", "1.5백만원").
_BUDGET = re.compile(r"((?:\d[\d,]*(?:\.\d+)?|[일이삼사오육칠팔구십백천])+)\s*(억\s*원?|만\s*원?|원|won|krw)", re.I)
# "예산 이백 정도", "삼백 내외": a Korean numeral with 백/천 and no unit means 만 원 in a PC budget.
_BARE_BUDGET = re.compile(r"(?<![가-힣\d])((?:(?:\d+|[일이삼사오육칠팔구])?[백천])+(?:\d+|[일이삼사오육칠팔구십])*)(?=\s*(?:정도|쯤|내외|언저리|선|으로|로|이하|이내|까지|안쪽|만큼)|\s*$|[\s,.])")
# Bare digits: six or more are won ("예산 1500000"); 30~2000 mean 만 원 when the budget context is clear
# ("예산 200", "배그컴 170" at the end, "300 정도요", "150에서 200 사이", "예산만 200으로"). Resolutions are not budgets.
_RAW_WON = re.compile(r"(?<![\d.,a-z])(\d{1,3}(?:,\d{3}){2,}|\d{6,})(?![\d,a-z가-힣])", re.I)
_BARE_DIGITS = re.compile(r"(?:(?<=예산)|(?<=예산은)|(?<=예산을)|(?<=예산만)|(?<=예산이)|(?<=예산도)|(?<=[\s(]))(\d{2,4})"
                          r"(?=\s*(?:정도|쯤|내외|언저리|선(?![가-힣])|으로|로(?![가-힣])|에서|사이|이하|이내|까지|언더|안쪽)|\s*[.!?~]*\s*$)")
_BUDGET_WORD = re.compile(r"예산\s*(?:은|는|을|만|이|도)?\s*$")
# "램 32로", "모니터 27로", "파워 750으로" name a part size, not money.
_PART_WORD = re.compile(r"(?:램|메모리|ram|ssd|vram|파워|모니터|인치|주사율|hz|cpu|그래픽\s*카드|글카|용량|와트)\s*(?:은|는|을|를|도|만|이)?\s*$", re.I)
# Relative change in a follow-up: "예산 10만원만 더 올려줘", "30만원 줄여주세요".
_BUDGET_UP = re.compile(r"(?:만|정도|쯤|가량)?\s*(?:더\s*)?(?:올|늘|추가|높|증액|써도|쓸게)")
_BUDGET_DOWN = re.compile(r"(?:만|정도|쯤|가량)?\s*(?:더\s*)?(?:줄|낮|깎|빼|내려|내리|감액|덜)")
_KOREAN_DIGITS = {c: i for i, c in enumerate("일이삼사오육칠팔구", 1)}
_KOREAN_UNITS = {"십": 10, "백": 100, "천": 1000}
# "3D" only as a word: the X3D in a CPU model name (9800X3D) is not 3D work.
_EDITING = re.compile(r"편집|프리미어|다빈치|렌더|(?<![a-z0-9])3D|어도비|adobe|premiere|포토샵|photoshop|라이트룸|lightroom|"
                      r"일러스트레이터|illustrator|애프터\s*이펙트|after\s*effects|블렌더|blender|캐드|(?<![a-z])(?:auto)?cad(?![a-z])|"
                      r"스케치업|sketchup|솔리드웍스|solidworks|마야|maya|라이노|rhino|그래스\s*호퍼|grasshopper|레빗|revit|"
                      r"클립\s*스튜디오|clip\s*studio|웹툰|3ds\s*max|시네마\s*4d|c4d|지브러시|zbrush|캡컷|capcut|브이레이|v-?ray|"
                      r"루미온|lumion|키샷|keyshot|후디니|houdini|퓨전\s*360|fusion\s*360|카티아|catia|인벤터|inventor", re.I)
_AI = re.compile(r"로컬|딥러닝|머신\s*러닝|LLM|(?<!웹)(?<!웹 )(?<!앱)(?<!앱 )개발|(?<![a-z])AI(?![a-z])|스테이블\s*디퓨전|stable\s*diffusion|파이토치|pytorch|sdxl|로라\s*학습|"
                 r"(?<![a-z])lora(?![a-z])|comfy\s*ui|컴피\s*ui|ollama|올라마|파인\s*튜닝|fine-?tun|whisper|cuda|쿠다|llama|vllm|허깅\s*페이스|hugging\s*face|텐서\s*플로|tensorflow|케라스|keras|"
                 r"(?<![a-z])(?:rag|yolo|tts)(?![a-z])|강화\s*학습|음성\s*합성|객체\s*인식", re.I)
# Web development and coding classes need no graphics card ("웹 개발 공부용", "코딩 학원").
_OFFICE = re.compile(r"사무|회계|엑셀|학습|POS|키오스크|kiosk|cctv|녹화|감시|웹\s*개발|앱\s*개발|코딩|프로그래밍|주식|hts|차트", re.I)
# 롤 = League of Legends, not 컨트롤·스크롤·롤러.
_GAMING = re.compile(r"게임|게이밍|배그|오버\s*워치|overwatch|(?<![컨트스크])롤(?![러백])|gaming", re.I)
_LIGHT = re.compile(r"인터넷|웹\s*서핑|웹\s*브라우|문서|인강|온라인\s*강의|유튜브|동영상\s*시청|"
                    r"줌\s*(?:수업|회의|강의)|zoom|화상\s*(?:수업|회의|강의)|(?:온라인|원격|비대면)\s*수업", re.I)
# Options are judged by their last mention; a mention followed in the same clause by a refusal turns it off
# ("화이트 말고 블랙", "와이파이는 필요 없어요", "윈도우는 집에 있는 거 쓸게요", "윈도우는 빼주세요").
_WHITE = re.compile(r"화이트|흰색|하얀|흰\s*(?:케이스|컬러|본체)|white", re.I)
_WIFI = re.compile(r"와이파이|wi-?fi|무선(?!\s*(?:마우스|키보드|이어폰|헤드셋|헤드폰|충전|패드|컨트롤러))", re.I)
_OS = re.compile(r"윈도우|windows|운영\s*체제|OS\s*포함", re.I)
# The window ends at a clause joint ("윈도우 넣고 와이파이는 빼줘": the 빼 belongs to 와이파이).
_REFUSAL = re.compile(r"(?:(?!고\s)[^,.\n]){0,10}?(?:말고|빼|제외|필요\s*없|없어도|없이|안\s*넣|넣지|아니|싫|집에\s*있|(?<!수도 )(?:있는\s*거|있어요|있습니다)|따로)")
_UNLIMITED = re.compile(r"예산\s*(?:은|는|이)?\s*(?:제한\s*없|상관\s*없|무관|무제한)|(?:돈|가격|비용)\s*(?:은|는|이)?\s*상관\s*없|금액\s*제한\s*없", re.I)
# JavaScript \b is ASCII-only; re.ASCII keeps "p\b" etc. behaving the same before Korean text.
_MODEL = re.compile(r"(rtx|gtx|rx|i[3579]-?)?\s?(\d{3,5})\s?(x3d2?|xtx|xt|gre|ti\s?super|ti|super|kf|ks|k|f|x|g)?"
                    r"(?![\d만원]|[,.]\d|\s?(?:만|원|p\b|hz|gb|tb|w\b))", re.I | re.ASCII)


def money(n: int | float) -> str:
    return f"{round(n):,}원"


def _amount(number: str) -> float:
    """'1,500' → 1500, '백오십' → 150, '2백' → 200, '1.5백' → 150, '1천5백' → 1500."""
    total, current = 0.0, None
    for token in re.findall(r"\d+(?:\.\d+)?|\D", number.replace(",", "")):
        if token in _KOREAN_UNITS:
            total += (1 if current is None else current) * _KOREAN_UNITS[token]
            current = None
        else:
            current = float(_KOREAN_DIGITS.get(token, token))
    return total + (current or 0)


def _amounts(text: str) -> list[tuple[re.Match, int]]:
    # Korean numerals only count before 만: a bare "이원" is a word, not 2원.
    out = []
    for m in _BUDGET.finditer(text):
        number, unit = m.groups()
        if unit[0] in "만억" or number[0].isdigit():
            scale = 100_000_000 if unit.startswith("억") else 10000 if unit.startswith("만") else 1
            out.append((m, int(math.floor(_amount(number) * scale + 0.5))))  # JS Math.round
    return out


# "모니터 30만원 포함해서 총 200만원": the PC budget is the total minus the monitor.
_INCLUDED = re.compile(r"(?:모니터|키보드|마우스|주변\s*기기)[^,.\d\n]{0,8}$")
_INCLUDES = re.compile(r"\s*(?:까지|도)?\s*(?:포함|합쳐|같이)")


def explicit_budget(text: str) -> int | None:
    amounts = _amounts(text)
    # Classify amounts by their role instead of assuming the last two are extra → total.
    pc = [(m, v) for m, v in amounts if not _INCLUDED.search(text, 0, m.start())]
    if pc:
        total = pc[-1][1]
        extras = 0
        for m, value in amounts:
            peripheral = _INCLUDED.search(text, 0, m.start())
            if (peripheral and not re.search(r"따로|별도", peripheral.group())
                    and _INCLUDES.match(text, m.end())):
                extras += value
        return total - extras if 0 < extras < total else total
    if amounts:
        return amounts[-1][1]
    bare = list(_BARE_BUDGET.finditer(text))
    if bare:
        return int(_amount(bare[-1].group(1)) * 10000)
    raw = list(_RAW_WON.finditer(text))
    if raw:
        return int(raw[-1].group(1).replace(",", ""))
    digits = [m for m in _BARE_DIGITS.finditer(text)
              if 30 <= int(m.group(1)) <= 2000 and m.group(1) not in ("1080", "1440")
              and (_BUDGET_WORD.search(text, 0, m.start())
                   or not (re.search(r"[a-z]\s*$", text[:m.start()], re.I) or _PART_WORD.search(text, 0, m.start())))]
    return int(digits[-1].group(1)) * 10000 if digits else None


def budget_change(text: str) -> int | None:
    """Signed won for "10만원 더 올려줘" / "30만원 줄여주세요"; None when the text states an amount, not a change.

    Only a text whose single amount is followed by an up/down verb counts, so
    "모니터 30만원 빼고 170만원" stays an explicit 170만 원.
    """
    amounts = _amounts(text)
    if len(amounts) != 1:
        return None
    m, value = amounts[0]
    if _BUDGET_UP.match(text, m.end()):
        return value
    if _BUDGET_DOWN.match(text, m.end()):
        return -value
    return None


_BLACK = re.compile(r"(?:블랙|검정\s*색?|검은\s*색|black)\s*(?:으로|로)(?![가-힣]*\s*포인트)", re.I)


def option_requested(pattern: re.Pattern, text: str) -> bool:
    """The last mention decides; a refusal in its clause, or for white a later "블랙으로 바꿔주세요", turns it off."""
    mentions = list(pattern.finditer(text))
    if not mentions or _REFUSAL.match(text, mentions[-1].end()):
        return False
    return not (pattern is _WHITE and _BLACK.search(text, mentions[-1].end()))


def broadcast_purpose(value: str) -> bool:
    return bool(re.search(r'송출|\bOBS\b|스트림랩스|streamlabs', value, re.I) or
                (re.search(r'방송|스트리밍|스트리머|streaming', value, re.I) and
                 not re.search(r'시청|감상|보기|보는|볼\s*용', value)))


def detect_profile(value: str) -> str | None:
    """Gaming beats office: "사무용인데 가끔 배그도 해요" needs a graphics card."""
    if broadcast_purpose(value) or _EDITING.search(value):
        return "editing"
    if _AI.search(value):
        return "ai"
    if _GAMING.search(value):
        return "gaming"
    if _OFFICE.search(value):
        return "office"
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


_SIZE = r"(\d+(?:\.\d+)?)\s*(tb|테라|gb|기가|g)(?![a-z])"
_PARTICLE = r"(?:[^,.\n\d]|ddr\d|\d+\s*(?:개|장))(?:[^,.\n\d]|ddr\d|\d+\s*(?:개|장)){0,11}?"  # "SSD는 ", "저장공간 넉넉하게 "
_RAM_SIZE = [re.compile(r"(?:램|메모리|ram)" + _PARTICLE + _SIZE, re.I),
             re.compile(_SIZE + r"\s*(?:ddr\d\s*)?(?:램|메모리|ram)", re.I)]
_SSD_SIZE = [re.compile(r"(?:ssd|nvme|저장\s*(?:공간|장치|용량))" + _PARTICLE + _SIZE, re.I),
             re.compile(_SIZE + r"\s*(?:ssd|nvme)", re.I)]
_VRAM_SIZE = [re.compile(r"(?:(?:rtx|gtx|rx)\s*\d{4}\s*(?:ti\s*super|ti|super|xtx|xt)?\s*|(?<![\d.])[2345]0[5-9]0\s*(?:ti\s*super|ti|super)?\s*)" + _SIZE, re.I),
              re.compile(r"(?:vram|비램|브이램|(?:그래픽|비디오)\s*(?:카드\s*)?메모리|video\s*memory)" + _PARTICLE + _SIZE, re.I),
              re.compile(_SIZE + r"\s*(?:vram|비램|브이램)", re.I)]
# A bare "AMD" ("AMD로 맞춰주세요") means the CPU; "AMD 그래픽카드" means Radeon.
_AMD_GPU = r"amd\s*(?:그래픽|gpu|글카|라데온)"
_INTEL_GPU = r"(?:인텔|intel)\s*(?:아크|arc|그래픽)"
_CPU_BRANDS = {"intel": re.compile(r"(?:인텔|intel)(?!\s*(?:아크|arc|그래픽))|코어\s*i[3579]", re.I),
               "amd": re.compile(r"라이젠|ryzen|amd(?!\s*(?:그래픽|gpu|글카|라데온))", re.I)}
_GPU_BRANDS = {"nvidia": re.compile(r"지포스|geforce|엔비디아|nvidia|rtx|gtx", re.I),
               "amd": re.compile(r"라데온|radeon|(?<![a-z])rx\s*\d|" + _AMD_GPU, re.I),
               "intel": re.compile(r"아크(?!릴)|(?<![a-z])arc(?![a-z])|" + _INTEL_GPU, re.I)}
# A GPU-looking model the catalog lacks ("RTX 4090", "4070 Ti SUPER") stays a preference, so the engine drops it with a notice.
_GPU_LIKE = re.compile(r"[12345]0[5-9]0(?:ti|super|tisuper)?|\d{4}(?:ti|super|tisuper)")


def _last_size(patterns: list[re.Pattern], text: str) -> int:
    found = [(m.start(), m) for pattern in patterns for m in pattern.finditer(text)]
    if not found:
        return 0
    m = max(found, key=lambda f: f[0])[1]
    number, unit = float(m.group(1)), m.group(2).lower()
    return int(number * 1000) if unit in ("tb", "테라") else int(number)


def _last_brand(brands: dict[str, re.Pattern], text: str) -> str | None:
    found = [(m.start(), name) for name, pattern in brands.items() for m in pattern.finditer(text)
             if not _REFUSAL.match(text, m.end())]  # "엔비디아 말고 AMD 그래픽카드"
    return max(found)[1] if found else None


def customer_preferences(text: str, parts) -> dict:
    """Engine Request preferences stated in the request text: models, brands, minimum sizes.

    Model tokens are assigned to CPU or GPU by the catalog; a token both could be is skipped.
    The last mention wins, so a later "추가 요청" replaces an earlier one.
    """
    keys = {"cpu": set(), "gpu": set()}
    for part in parts:
        key = model_key(part)
        if key:
            keys[part["category"]].add(key)
    tokens = model_tokens(text)
    cpu_models = tuple(t for t in tokens if t in keys["cpu"] and t not in keys["gpu"])
    gpu_models = tuple(t for t in tokens if (t in keys["gpu"] and t not in keys["cpu"])
                       or (t not in keys["gpu"] and t not in keys["cpu"] and _GPU_LIKE.fullmatch(t)))
    without_vram = text
    for pattern in _VRAM_SIZE:  # "VRAM 16GB", "그래픽 메모리 16GB" are not system memory
        without_vram = pattern.sub(" ", without_vram)
    return {"min_ram_gb": _last_size(_RAM_SIZE, without_vram), "min_ssd_gb": _last_size(_SSD_SIZE, text),
            "min_vram_gb": _last_size(_VRAM_SIZE, text), "cpu_models": cpu_models, "gpu_models": gpu_models,
            "cpu_brand": _last_brand(_CPU_BRANDS, text), "gpu_brand": _last_brand(_GPU_BRANDS, text)}


# Owning a monitor specifies the target resolution; unlike an owned OS, it is not an opt-out.
_RESOLUTION_REFUSAL = re.compile(r"(?:(?!고\s)[^,.\n]){0,10}?(?:말고|빼|제외|필요\s*없|없어도|없이|안\s*넣|넣지|아니|싫)")
_RESOLUTIONS = {"4K": re.compile(r"[458]k|uhd|2160", re.I), "FHD": re.compile(r"fhd|1080|풀\s*hd|full\s*hd", re.I),
                "QHD": re.compile(r"qhd|1440", re.I)}


def _resolution_of(value: str) -> str | None:
    """Last mentioned resolution that is not refused ("4K 말고 QHD로" → QHD); 5K·8K use the 4K floor."""
    found = [(m.start(), name) for name, pattern in _RESOLUTIONS.items() for m in pattern.finditer(value)
             if not _RESOLUTION_REFUSAL.match(value, m.end())]
    if found:
        return max(found)[1]
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
        "resolutionExplicit": any(pattern.search(text) for pattern in _RESOLUTIONS.values()),
        "white": option_requested(_WHITE, text), "wifi": option_requested(_WIFI, text),
        "os": option_requested(_OS, text), "allowOver": False, **options,
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
    profile = local["profile"] if stated else llm.get("profile")
    if profile == "office" and not any(_resolution_of(v) for v in _ADD.split(text)):
        local["resolution"] = "FHD"
    return {**local, "profile": profile,
            "questions": [q for q in (llm.get("questions") or []) if "예산" not in q]}


def _resolution_question(text: str) -> str | None:
    if re.search(r"4k|uhd|2160", text, re.I):
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
