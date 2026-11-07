"""Usage profiles: budget allocation, minimum specs and performance weights (plan §4)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

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

BUDGET_CEILING = 1.0  # 예산은 상한: 어떤 견적도 예산(조립비 포함)을 넘지 않는다
POOL_FLOOR = 0.55  # 예산의 55% 미만 조합은 후보에서 제외
# 세 안의 가격 간격: 성능 우선형은 균형형보다 12% 이상 비싸고, 가성비형은 15% 이상 싸다
STRONG_GAP = 1.12
CHEAP_GAP = 0.85


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
    # Customer-stated preferences: hard while a build fits, dropped with a note otherwise (recommend()).
    min_ram_gb: int = 0
    min_ssd_gb: int = 0
    min_vram_gb: int = 0
    cpu_brand: str | None = None  # "intel" | "amd"
    gpu_brand: str | None = None  # "nvidia" | "amd"
    cpu_models: tuple[str, ...] = ()  # model tokens, e.g. "9800x3d"
    gpu_models: tuple[str, ...] = ()  # e.g. "5070", "5060ti"

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

    def preference_labels(self) -> list[str]:
        out = []
        if self.cpu_models:
            out.append(f"CPU {'/'.join(m.upper() for m in self.cpu_models)}")
        elif self.cpu_brand:
            out.append(f"{BRAND_LABELS[self.cpu_brand]} CPU")
        if self.gpu_models:
            out.append(f"그래픽카드 {'/'.join(m.upper() for m in self.gpu_models)}")
        elif self.gpu_brand:
            out.append(f"{GPU_BRAND_LABELS[self.gpu_brand]} 그래픽카드")
        if self.min_ram_gb:
            out.append(f"메모리 {size(self.min_ram_gb)} 이상")
        if self.min_ssd_gb:
            out.append(f"SSD {size(self.min_ssd_gb)} 이상")
        if self.min_vram_gb:
            out.append(f"VRAM {size(self.min_vram_gb)} 이상")
        return out

    def without_preferences(self) -> Request:
        return replace(self, min_ram_gb=0, min_ssd_gb=0, min_vram_gb=0, cpu_brand=None, gpu_brand=None,
                       cpu_models=(), gpu_models=())


BRAND_LABELS = {"intel": "인텔", "amd": "AMD"}
GPU_BRAND_LABELS = {"nvidia": "지포스", "amd": "라데온"}


def size(gb: int) -> str:
    return f"{gb // 1000}TB" if gb >= 1000 and gb % 1000 == 0 else f"{gb}GB"


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
    if req.min_ram_gb > ram:
        ram = req.min_ram_gb
        notes.append(f"고객 요청: 메모리 {size(ram)} 이상")
    if req.min_ssd_gb > ssd:
        ssd = req.min_ssd_gb
        notes.append(f"고객 요청: SSD {size(ssd)} 이상")
    if req.needs_gpu and req.min_vram_gb > vram:
        vram = req.min_vram_gb
        notes.append(f"고객 요청: 그래픽카드 VRAM {size(vram)} 이상")
    gpu_bench = (catalog.benchmark_of("gpu", gpu_ref) or 0.0) if gpu_ref else 0.0
    return MinSpecs(ram, ssd, gpu_bench, gpu_ref, vram, tuple(notes))


LOWER_RESOLUTION = {"4K": "QHD", "QHD": "FHD"}
# Entry gaming GPUs below the FHD reference, tried in order when even FHD does not fit (e.g. 100만 원 게임용).
ENTRY_GPUS = ("RTX 5050", "RTX 3050")
# Office floors below the normal 16GB / 500GB (e.g. POS, 인강용 30~40만 원).
OFFICE_FLOOR = (8, 256)


def relaxed_specs(req: Request, specs: MinSpecs, catalog: Catalog) -> list[tuple[MinSpecs, tuple[str, ...]]]:
    """Cumulative lower minimums for a budget below the normal minimum build.

    Order: memory, SSD, the gaming GPU reference one resolution down, then entry GPUs;
    for office, memory and SSD below the normal floor. Each entry is (specs, changes so far).
    AI VRAM and customer-stated minimums are never lowered.
    """
    out: list[tuple[MinSpecs, tuple[str, ...]]] = []
    changes: list[str] = []
    current = specs

    def lower_ram(floor: int):
        nonlocal current
        floor = max(floor, req.min_ram_gb)
        if current.ram_gb > floor:
            changes.append(f"메모리 {size(current.ram_gb)} → {size(floor)}")
            current = replace(current, ram_gb=floor)
            out.append((current, tuple(changes)))

    def lower_ssd(floor: int):
        nonlocal current
        floor = max(floor, req.min_ssd_gb)
        if current.ssd_gb > floor:
            changes.append(f"SSD {size(current.ssd_gb)} → {size(floor)}")
            current = replace(current, ssd_gb=floor)
            out.append((current, tuple(changes)))

    gpu_from = specs.gpu_reference

    def lower_gpu(ref: str, resolution: str):
        nonlocal current
        bench = catalog.benchmark_of("gpu", ref)
        if not bench or bench >= current.gpu_benchmark:
            return
        if changes and changes[-1].startswith("그래픽카드 기준"):
            changes.pop()  # one line for the whole GPU chain: "RTX 4060급 → RTX 3050급"
        changes.append(f"그래픽카드 기준 {gpu_from}급 → {ref}급")
        notes = tuple(n for n in current.notes if not n.endswith("급 이상 그래픽카드"))
        current = replace(current, gpu_reference=ref, gpu_benchmark=bench,
                          notes=notes + (f"{resolution} 게임(예산 맞춤): {ref}급 이상 그래픽카드",))
        out.append((current, tuple(changes)))

    lower_ram(16)
    lower_ssd(500)
    if "gaming" in req.uses:
        lower = LOWER_RESOLUTION.get(req.resolution)
        if lower and current.gpu_reference == GPU_REFERENCE[req.resolution]:
            lower_gpu(GPU_REFERENCE[lower], req.resolution)
        if current.gpu_reference == GPU_REFERENCE["FHD"]:
            for ref in ENTRY_GPUS:
                lower_gpu(ref, req.resolution)
    if not req.needs_gpu:
        lower_ram(OFFICE_FLOOR[0])
        lower_ssd(OFFICE_FLOOR[1])
    return out
