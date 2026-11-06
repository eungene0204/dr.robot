"""Store data policy, ported from buildmate (src/data-policy.mjs, product-ontology.mjs, storage-policy.mjs).

A part may be quoted only when its required facts are known, its storage type is
recommendable, its price is fresh (24 h) and, for CPU/GPU, a measured benchmark
(≥3 samples, ≤45 days) exists. Parts are buildmate-format dicts.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone

PRICE_MAX_AGE_HOURS = 24
BENCHMARK_MAX_AGE_DAYS = 45
CATEGORIES = ("cpu", "board", "ram", "gpu", "ssd", "psu", "case", "cooler", "os")

REQUIRED_FACTS = {
    "cpu": ("socket", "watts"),
    "board": ("socket", "ddr", "form", "slots", "maxRam"),
    "ram": ("ddr", "capacity", "sticks"),
    "gpu": ("vram", "watts", "length"),
    "ssd": ("capacity",),
    "psu": ("capacity", "connectors"),
    "case": ("forms", "gpuLength", "coolerHeight"),
    "cooler": ("sockets", "height", "coolingWatts"),
    "os": (),
}
_LIST_FACTS = {"sockets", "forms", "connectors"}
_TEXT_FACTS = {"socket", "form"}

_ACCESSORY = re.compile(r"컨버터|변환|어댑터|아답터|adapter|converter|인클로저|enclosure|외장|external|케이블|cable|확장카드|"
                        r"브라켓|방열판|히트싱크|복사기|도킹|클론|케이스|USB", re.I)
_CACHE = re.compile(r"Optane\s*Memory|옵테인\s*메모리|캐시\s*(?:모듈|메모리)|cache\s*(?:module|memory)", re.I)
_SATA = re.compile(r"SATA|Serial\s*ATA|사타", re.I)
_SERVER = re.compile(r"U\.[23]\b|EDSFF|E[13]\.[SL]", re.I)


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _parse_time(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def is_fresh(when, max_hours: float, now: datetime) -> bool:
    t = _parse_time(when)
    if t is None:
        return False
    age = (now - t).total_seconds()
    return age >= -300 and age <= max_hours * 3600


def storage_issue(part: dict) -> str | None:
    if part.get("category") != "ssd":
        return None
    description = f"{part.get('name') or ''} {part.get('productType') or ''}"
    if _ACCESSORY.search(description):
        return "저장장치 액세서리 또는 외장 제품"
    if _CACHE.search(description):
        return "주 저장장치로 사용할 수 없는 캐시 모듈"
    capacity = part.get("capacity")
    if not _number(capacity) or capacity <= 0:
        return "저장 용량 미확인"
    return None


def storage_recommendation_issue(part: dict) -> str | None:
    issue = storage_issue(part)
    if issue or part.get("category") != "ssd":
        return issue
    protocol = f"{part.get('interface') or ''} {part.get('protocol') or ''} {part.get('name') or ''} {part.get('productType') or ''}"
    if _SATA.search(protocol):
        return "SATA 스토리지는 추천에서 제외합니다."
    if _SERVER.search(protocol):
        return "별도 장착·연결 검증이 필요한 서버용 스토리지"
    if not re.search("NVMe", protocol, re.I):
        return "NVMe 인터페이스 확인이 필요합니다."
    return None


def ssd_interface(part: dict) -> str | None:
    """"nvme", "sata", or None when the drive cannot fill a recommended storage slot."""
    part = {**part, "category": "ssd"}
    if storage_issue(part):
        return None
    issue = storage_recommendation_issue(part)
    if issue is None:
        return "nvme"
    return "sata" if issue.startswith("SATA") else None


def product_issues(part: dict) -> list[str]:
    category = part.get("category")
    if category not in REQUIRED_FACTS:
        return ["알 수 없는 제품 유형"]
    if part.get("virtual"):
        return []
    issues: list[str] = []
    issue = storage_issue(part)
    if issue:
        issues.append(issue)
    for key in REQUIRED_FACTS[category]:
        value = part.get(key)
        if value is None:
            issues.append(f"필수 속성 미확인: {key}")
        elif key in _LIST_FACTS:
            if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
                issues.append(f"속성 형식 오류: {key}")
        elif key in _TEXT_FACTS:
            if not isinstance(value, str):
                issues.append(f"속성 형식 오류: {key}")
        elif not _number(value) or value <= 0:
            issues.append(f"양수 속성 필요: {key}")
    return list(dict.fromkeys(issues))


def price_state(part: dict, now: datetime) -> str:
    if part.get("virtual"):
        return "not-applicable"
    evidence = part.get("priceEvidence") or {}
    price = part.get("price")
    if not _number(price) or price <= 0 or not evidence.get("sourceUrl"):
        return "missing"
    return "fresh" if is_fresh(evidence.get("observedAt"), PRICE_MAX_AGE_HOURS, now) else "stale"


def benchmark_state(part: dict, now: datetime) -> str:
    if part.get("category") not in ("cpu", "gpu") or part.get("virtual"):
        return "not-applicable"
    b = part.get("benchmark")
    if not b or not _number(b.get("score")) or b["score"] <= 0 or (b.get("samples") or 0) < 3 or not b.get("sourceUrl"):
        return "missing"
    return "measured" if is_fresh(b.get("observedAt"), BENCHMARK_MAX_AGE_DAYS * 24, now) else "stale"


def usable_part(part: dict, now: datetime) -> bool:
    if product_issues(part) or storage_recommendation_issue(part):
        return False
    if part.get("virtual"):
        return True
    return (price_state(part, now) == "fresh" and part.get("inStock") is not False
            and (part.get("category") not in ("cpu", "gpu") or benchmark_state(part, now) == "measured"))


def policy_issue(part: dict, now: datetime) -> bool:
    """True when the part fails a rule other than price age — refreshing the price would not make it quotable."""
    if part.get("virtual"):
        return False
    evidence = part.get("priceEvidence")
    current = {**part, "priceEvidence": {**evidence, "observedAt": now.isoformat()}} if evidence else part
    return not usable_part(current, now)


def hydrate_snapshot(snapshot: dict, now: datetime) -> dict:
    """Validate a published snapshot and attach price / benchmark states and coverage counts (data-policy.mjs)."""
    parts = snapshot.get("parts") if isinstance(snapshot, dict) else None
    if snapshot.get("schemaVersion") != 2 or snapshot.get("mode") != "live" or not isinstance(parts, list) or len(parts) > 100000:
        raise ValueError("실제 데이터 스냅샷 형식이 올바르지 않습니다.")
    ids = set()
    for p in parts:
        if not isinstance(p, dict) or not isinstance(p.get("id"), str) or p["id"] in ids or p.get("category") not in CATEGORIES \
                or not isinstance(p.get("name"), str):
            raise ValueError("카탈로그 식별자 오류")
        ids.add(p["id"])
    parts = [{**p, "dataMode": "live", "priceStatus": price_state(p, now), "benchmarkStatus": benchmark_state(p, now)} for p in parts]
    real = [p for p in parts if not p.get("virtual")]
    return {**snapshot, "parts": parts, "coverage": {
        **(snapshot.get("coverage") or {}),
        "freshPrices": sum(price_state(p, now) == "fresh" for p in real),
        "measuredBenchmarks": sum(benchmark_state(p, now) == "measured" for p in parts),
        "ready": sum(usable_part(p, now) for p in real),
        "stalePrices": sum(price_state(p, now) == "stale" for p in parts),
        "missingPrices": sum(price_state(p, now) == "missing" for p in parts),
    }}
