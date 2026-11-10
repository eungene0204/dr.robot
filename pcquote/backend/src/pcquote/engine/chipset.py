"""Chipset ↔ CPU generation support rules.

The plan's rule is "메인보드 칩셋이 CPU 세대 지원". Boards that shipped before a
CPU generation launched usually need a BIOS update first, so those pairs are
allowed with a ``bios`` condition the quote must show. Sockets and chipset
series not listed here are not recommended (legacy platforms).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..catalog import Part

_CHIPSET = re.compile(r"(?<![A-Za-z0-9])([ABHXZ]\d{3})(?!\d)")
_INTEL_ULTRA = re.compile(r"(?:Ultra|울트라)\s*[3579]\s*(?:시리즈\s*2\s*)?(2\d{2})[A-Z]*\s*(Plus)?", re.I)
_INTEL_CORE = re.compile(r"i[3579]\s*-?\s*(?:\d+세대\s*)?(1[0-4])\d{3}", re.I)
_AMD_RYZEN = re.compile(r"(?:Ryzen|라이젠)\s*[3579](?:\s*-\s*\d+세대)?\s*(?:PRO\s*)?([3-9])\d{3}", re.I)


@dataclass(frozen=True)
class Support:
    full: frozenset[str]
    bios: frozenset[str] = frozenset()


def _s(full: set[str], bios: set[str] | None = None) -> Support:
    return Support(frozenset(full), frozenset(bios or ()))


# (socket, chipset series) → supported CPU generations.
SUPPORT: dict[tuple[str, str], Support] = {
    ("LGA1700", "600"): _s({"intel-12"}, {"intel-13", "intel-14"}),
    ("LGA1700", "700"): _s({"intel-12", "intel-13"}, {"intel-14"}),
    ("LGA1851", "800"): _s({"intel-ultra-200"}, {"intel-ultra-200-plus"}),
    ("AM5", "600"): _s({"amd-7000"}, {"amd-8000", "amd-9000"}),
    ("AM5", "800"): _s({"amd-7000", "amd-8000", "amd-9000"}),
    ("AM4", "500"): _s({"amd-3000", "amd-4000", "amd-5000"}),
    ("AM4", "400"): _s({"amd-3000", "amd-zen+"}, {"amd-4000", "amd-5000"}),
}

# Entry chipsets: boards with these usually have small VRMs.
ENTRY_CHIPSETS = {"H610", "H810", "A520", "A620"}
ENTRY_MAX_CPU_WATTS = 160

GENERATION_LABELS = {
    "intel-12": "인텔 12세대",
    "intel-13": "인텔 13세대",
    "intel-14": "인텔 14세대",
    "intel-ultra-200": "인텔 코어 울트라 200S",
    "intel-ultra-200-plus": "인텔 코어 울트라 200S Plus",
    "amd-zen+": "라이젠 2세대(Zen+) APU",
    "amd-3000": "라이젠 3000",
    "amd-4000": "라이젠 4000",
    "amd-5000": "라이젠 5000",
    "amd-7000": "라이젠 7000",
    "amd-8000": "라이젠 8000",
    "amd-9000": "라이젠 9000",
}


def board_chipset(board: Part) -> str | None:
    if board.spec("chipset"):
        return str(board.spec("chipset")).upper()
    m = _CHIPSET.search(board.name)
    return m.group(1).upper() if m else None


def chipset_series(chipset: str | None) -> str | None:
    return f"{chipset[1]}00" if chipset and len(chipset) == 4 else None


def cpu_generation(cpu: Part) -> str | None:
    for text in (cpu.benchmark_name or "", cpu.name):
        if m := _INTEL_ULTRA.search(text):
            return "intel-ultra-200-plus" if m.group(2) else "intel-ultra-200"
        if m := _INTEL_CORE.search(text):
            return f"intel-{m.group(1)}"
        if m := _AMD_RYZEN.search(text):
            # Ryzen 3200G/3400G are Zen+ (Picasso) APUs despite the 3000 number.
            if m.group(1) == "3" and re.search(r"3[24]00GE?\b", text):
                return "amd-zen+"
            return f"amd-{m.group(1)}000"
    return None


def chipset_support(cpu: Part, board: Part) -> tuple[str, str]:
    """Return (status, detail) with status ``ok``, ``warn`` (BIOS update) or ``fail``."""
    chipset = board_chipset(board)
    generation = cpu_generation(cpu)
    rule = SUPPORT.get((board.spec("socket"), chipset_series(chipset)))
    gen_label = GENERATION_LABELS.get(generation or "", "세대 미확인")
    if chipset is None or generation is None:
        return "fail", f"칩셋 {chipset or '미확인'} / CPU {gen_label} — 지원 여부를 판단할 수 없음"
    if rule is None:
        return "fail", f"{board.spec('socket')} {chipset} 칩셋은 추천 지원 대상이 아님"
    if generation in rule.full:
        return "ok", f"{chipset} 칩셋이 {gen_label} 지원"
    if generation in rule.bios:
        return "warn", f"{chipset} 칩셋은 {gen_label}를 BIOS 업데이트 후 지원 — 조립 전 최신 BIOS 적용 필요"
    return "fail", f"{chipset} 칩셋은 {gen_label} 미지원"
