"""Compatibility rules (plan §4 "호환성 규칙").

Each rule declares the categories it needs so the search can prune partial
builds with the same code that validates a finished quote. Missing data is a
failure: the plan's goal is zero compatibility errors, so unknown never passes.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from ..catalog import Part
from .chipset import ENTRY_CHIPSETS, ENTRY_MAX_CPU_WATTS, board_chipset, chipset_support

PSU_HEADROOM = 1.3
LIQUID = re.compile(r"수랭|수냉|AIO|리퀴드|Liquid", re.I)

Parts = dict[str, Part | None]


@dataclass(frozen=True)
class Check:
    label: str
    status: str  # ok | warn | fail
    detail: str

    def as_dict(self) -> dict:
        return {"label": self.label, "status": self.status, "detail": self.detail}


def cpu_power(cpu: Part) -> int:
    """Maximum sustained CPU power (Intel PL2 / AMD PPT) — safer than base TDP for PSU sizing."""
    return int(max(cpu.spec("watts", 0), cpu.spec("tdp", 0)))


def required_psu_watts(cpu: Part, gpu: Part | None) -> int:
    gpu_watts = gpu.spec("watts", 0) if gpu else 0
    return int((cpu_power(cpu) + gpu_watts) * PSU_HEADROOM + 0.999)


def _socket(p: Parts) -> Check:
    cpu, board = p["cpu"], p["board"]
    ok = cpu.spec("socket") == board.spec("socket")
    return Check("CPU 소켓", "ok" if ok else "fail", f"{cpu.spec('socket')} / {board.spec('socket')}")


def _chipset(p: Parts) -> Check:
    status, detail = chipset_support(p["cpu"], p["board"])
    return Check("칩셋 세대 지원", status, detail)


def _vrm_tier(p: Parts) -> Check:
    """Store policy: no high-power CPU on an entry-chipset board (weak VRM)."""
    cpu, board = p["cpu"], p["board"]
    chipset = board_chipset(board)
    if chipset not in ENTRY_CHIPSETS:
        return Check("전원부 등급", "ok", f"{chipset or '칩셋 미확인'} 보드")
    ok = cpu_power(cpu) <= ENTRY_MAX_CPU_WATTS
    detail = f"엔트리 칩셋 {chipset}: CPU 최대 {cpu_power(cpu)}W / 권장 한도 {ENTRY_MAX_CPU_WATTS}W"
    return Check("전원부 등급", "ok" if ok else "fail", detail)


def _memory_type(p: Parts) -> Check:
    ram, board = p["ram"], p["board"]
    ok = ram.spec("ddr") == board.spec("ddr")
    return Check("메모리 규격", "ok" if ok else "fail", f"DDR{ram.spec('ddr')} / 보드 DDR{board.spec('ddr')}")


def _memory_fit(p: Parts) -> Check:
    ram, board = p["ram"], p["board"]
    max_ram = board.spec("maxRam")
    ok = ram.spec("sticks") <= board.spec("slots") and (max_ram is None or ram.spec("capacity") <= max_ram)
    detail = f"{ram.spec('capacity')}GB({ram.spec('sticks')}개) / 슬롯 {board.spec('slots')}개, 최대 {max_ram or '?'}GB"
    return Check("메모리 슬롯·용량", "ok" if ok else "fail", detail)


def _psu_capacity(p: Parts) -> Check:
    cpu, gpu, psu = p["cpu"], p["gpu"], p["psu"]
    need = max(required_psu_watts(cpu, gpu), gpu.spec("minPsu", 0) if gpu else 0)
    ok = psu.spec("capacity") >= need
    gpu_watts = gpu.spec("watts", 0) if gpu else 0
    detail = f"(CPU {cpu_power(cpu)}W + GPU {gpu_watts}W) × {PSU_HEADROOM} = {need}W 필요 / 파워 {psu.spec('capacity')}W"
    return Check("파워 용량", "ok" if ok else "fail", detail)


def _gpu_power_connector(p: Parts) -> Check:
    gpu, psu = p["gpu"], p["psu"]
    if gpu is None:
        return Check("GPU 보조전원", "ok", "외장 그래픽카드 없음")
    connector = gpu.spec("connector")
    if connector in (None, "") and gpu.spec("watts", 0) > 75:
        return Check("GPU 보조전원", "fail", "그래픽카드 보조전원 규격 미확인")
    if connector in (None, "", "none"):
        return Check("GPU 보조전원", "ok", "보조전원 불필요")
    available = psu.spec("connectors") or []
    ok = connector in available
    return Check("GPU 보조전원", "ok" if ok else "fail", f"필요 {connector} / 파워 제공 {', '.join(available) or '미확인'}")


def _gpu_length(p: Parts) -> Check:
    gpu, case = p["gpu"], p["case"]
    if gpu is None:
        return Check("GPU 길이", "ok", "외장 그래픽카드 없음")
    ok = gpu.spec("length") <= case.spec("gpuLength")
    return Check("GPU 길이", "ok" if ok else "fail", f"{gpu.spec('length')}mm / 케이스 허용 {case.spec('gpuLength')}mm")


def _form_factor(p: Parts) -> Check:
    board, case = p["board"], p["case"]
    ok = board.spec("form") in (case.spec("forms") or [])
    return Check("메인보드 폼팩터", "ok" if ok else "fail", f"{board.spec('form')} / 케이스 지원 {', '.join(case.spec('forms') or [])}")


def _cooler_socket(p: Parts) -> Check:
    cooler, cpu = p["cooler"], p["cpu"]
    ok = cpu.spec("socket") in (cooler.spec("sockets") or [])
    return Check("쿨러 소켓", "ok" if ok else "fail", f"CPU {cpu.spec('socket')}")


def _cooler_capacity(p: Parts) -> Check:
    cooler, cpu = p["cooler"], p["cpu"]
    base = cpu.spec("tdp") or cpu.spec("watts")
    ok = cooler.spec("coolingWatts") >= base
    detail = f"쿨러 {cooler.spec('coolingWatts')}W / CPU 기본 {base}W (최대 {cpu_power(cpu)}W)"
    return Check("쿨링 용량", "ok" if ok else "fail", detail)


def _cooler_height(p: Parts) -> Check:
    cooler, case = p["cooler"], p["case"]
    if LIQUID.search(cooler.name):
        return Check("쿨러 높이", "fail", "수랭 쿨러는 라디에이터 장착 정보가 없어 자동 추천에서 제외")
    ok = cooler.spec("height") <= case.spec("coolerHeight")
    return Check("쿨러 높이", "ok" if ok else "fail", f"{cooler.spec('height')}mm / 케이스 허용 {case.spec('coolerHeight')}mm")


def _m2_slot(p: Parts) -> Check:
    ssd, board = p["ssd"], p["board"]
    if not ssd.spec("m2"):
        return Check("M.2 슬롯", "ok", "SATA SSD")
    ok = board.spec("m2", 0) >= 1
    return Check("M.2 슬롯", "ok" if ok else "fail", f"보드 M.2 {board.spec('m2', 0)}개")


def _integrated_graphics(p: Parts) -> Check:
    cpu, gpu = p["cpu"], p["gpu"]
    if gpu is not None:
        return Check("화면 출력", "ok", "외장 그래픽카드")
    ok = cpu.spec("igpu") is True
    return Check("화면 출력", "ok" if ok else "fail", "CPU 내장그래픽 사용" if ok else "외장 그래픽카드 없음 + 내장그래픽 없는 CPU")


# (categories needed, rule). "gpu" may be None for builds on integrated graphics.
RULES: list[tuple[tuple[str, ...], Callable[[Parts], Check]]] = [
    (("cpu", "board"), _socket),
    (("cpu", "board"), _chipset),
    (("cpu", "board"), _vrm_tier),
    (("ram", "board"), _memory_type),
    (("ram", "board"), _memory_fit),
    (("cpu", "gpu", "psu"), _psu_capacity),
    (("gpu", "psu"), _gpu_power_connector),
    (("gpu", "case"), _gpu_length),
    (("board", "case"), _form_factor),
    (("cooler", "cpu"), _cooler_socket),
    (("cooler", "cpu"), _cooler_capacity),
    (("cooler", "case"), _cooler_height),
    (("ssd", "board"), _m2_slot),
    (("cpu", "gpu"), _integrated_graphics),
]


def check(parts: Parts, only_with: str | None = None) -> list[Check]:
    """Run every rule whose categories are present.

    ``parts`` must contain a key for each category already decided (``gpu`` may
    map to None). With ``only_with``, only rules involving that category run —
    used when a part is added during search.
    """
    out = []
    for needs, rule in RULES:
        if only_with and only_with not in needs:
            continue
        if all(k in parts for k in needs) and all(parts[k] is not None for k in needs if k != "gpu"):
            out.append(rule(parts))
    return out


def passes(parts: Parts, only_with: str | None = None) -> bool:
    return all(c.status != "fail" for c in check(parts, only_with))
