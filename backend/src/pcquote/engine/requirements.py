"""Usage profiles: budget allocation, minimum specs and performance weights (plan §4)."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..catalog import Catalog

USES = ("gaming", "editing", "office", "ai")
USE_LABELS = {"gaming": "고사양 게임", "editing": "영상편집·3D", "office": "사무·학습", "ai": "AI·개발"}
RESOLUTIONS = ("FHD", "QHD", "4K")

# Plan §4 initial allocation (본체 기준). "rest" = 파워·케이스·쿨러.
ALLOCATION: dict[str, dict[str, float]] = {
    "gaming": {"cpu": 0.18, "gpu": 0.42, "board": 0.10, "ram": 0.07, "ssd": 0.07, "rest": 0.16},
    "editing": {"cpu": 0.27, "gpu": 0.30, "board": 0.11, "ram": 0.12, "ssd": 0.08, "rest": 0.12},
    "office": {"cpu": 0.35, "gpu": 0.00, "board": 0.15, "ram": 0.13, "ssd": 0.15, "rest": 0.22},
    "ai": {"cpu": 0.20, "gpu": 0.45, "board": 0.09, "ram": 0.11, "ssd": 0.06, "rest": 0.09},
}
# Split of the combined 파워·케이스·쿨러 share; the plan gives only the total.
REST_SPLIT = {"psu": 0.45, "case": 0.35, "cooler": 0.20}

# (CPU, GPU) weights of the performance score.
PERF_WEIGHTS = {"gaming": (0.25, 0.75), "editing": (0.5, 0.5), "office": (1.0, 0.0), "ai": (0.3, 0.7)}

# Minimum GPU by gaming resolution, as a reference chip present in the catalog.
GPU_REFERENCE = {"FHD": "RTX 4060", "QHD": "RTX 5060 Ti", "4K": "RTX 5070 Ti"}

BUDGET_BAND = 0.05  # plan: 예산 ±5%


@dataclass(frozen=True)
class Request:
    budget: int
    uses: tuple[str, ...] = ("gaming",)
    resolution: str = "FHD"
    white: bool = False
    wifi: bool = False
    exclude_brands: tuple[str, ...] = ()
    exclude_parts: tuple[str, ...] = ()  # part ids, e.g. parts whose price could not be refreshed
    assembly_fee: int = 0
    memo: str = ""

    def __post_init__(self):
        if not self.uses or any(u not in USES for u in self.uses):
            raise ValueError(f"용도는 {', '.join(USES)} 중에서 고르세요.")
        if self.resolution not in RESOLUTIONS:
            raise ValueError("해상도는 FHD, QHD, 4K 중 하나입니다.")
        if not 300_000 <= self.budget <= 20_000_000:
            raise ValueError("예산은 30만~2,000만 원 사이로 입력하세요.")

    @property
    def parts_budget(self) -> int:
        return self.budget - self.assembly_fee

    @property
    def needs_gpu(self) -> bool:
        return any(u != "office" for u in self.uses)


@dataclass(frozen=True)
class MinSpecs:
    ram_gb: int
    ssd_gb: int
    gpu_benchmark: float = 0.0
    gpu_reference: str | None = None
    gpu_vram_gb: int = 0
    notes: tuple[str, ...] = field(default_factory=tuple)


def allocation(req: Request) -> dict[str, int]:
    """Won per category: the plan's ratios averaged over the selected uses."""
    shares = {k: sum(ALLOCATION[u][k] for u in req.uses) / len(req.uses) for k in ALLOCATION["gaming"]}
    if not req.needs_gpu:
        shares["gpu"] = 0.0
    total = sum(shares.values())
    won = {k: req.parts_budget * v / total for k, v in shares.items() if k != "rest"}
    for k, ratio in REST_SPLIT.items():
        won[k] = req.parts_budget * shares["rest"] / total * ratio
    return {k: int(v) for k, v in won.items()}


def allocation_shares(req: Request) -> dict[str, float]:
    won = allocation(req)
    return {k: v / req.parts_budget for k, v in won.items()}


def perf_weights(req: Request) -> tuple[float, float]:
    cpu = sum(PERF_WEIGHTS[u][0] for u in req.uses) / len(req.uses)
    gpu = sum(PERF_WEIGHTS[u][1] for u in req.uses) / len(req.uses)
    if not req.needs_gpu:
        return 1.0, 0.0
    return cpu / (cpu + gpu), gpu / (cpu + gpu)


def min_specs(req: Request, catalog: Catalog) -> MinSpecs:
    ram, ssd, vram, notes = 16, 500, 0, []
    gpu_ref = None
    if "gaming" in req.uses:
        ram = max(ram, 32 if req.resolution != "FHD" else 16)
        ssd = max(ssd, 1000)
        gpu_ref = GPU_REFERENCE[req.resolution]
        notes.append(f"{req.resolution} 게임: {gpu_ref}급 이상 그래픽카드")
    if "editing" in req.uses:
        ram, ssd = max(ram, 32), max(ssd, 1000)
        gpu_ref = gpu_ref or GPU_REFERENCE["FHD"]
        notes.append("영상편집: 메모리 32GB 이상, SSD 1TB 이상")
    if "ai" in req.uses:
        ram, ssd, vram = max(ram, 32), max(ssd, 1000), 12
        notes.append("AI·개발: 그래픽카드 VRAM 12GB 이상, 메모리 32GB 이상")
    if not req.needs_gpu:
        notes.append("사무·학습: CPU 내장그래픽 사용")
    gpu_bench = (catalog.benchmark_of("gpu", gpu_ref) or 0.0) if gpu_ref else 0.0
    return MinSpecs(ram, ssd, gpu_bench, gpu_ref, vram, tuple(notes))
