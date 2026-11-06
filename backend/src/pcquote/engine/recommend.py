"""Quote generation (plan §4 처리 단계 2–5).

1. Minimum specs per use (rules).
2. Budget allocation per category (plan ratios).
3. Candidate search: each category is limited to its allocation ± tolerance;
   each CPU×GPU pair gets two sets of remaining parts — the cheapest and the
   most popular compatible ones.
4. Three plans from one score function with different weights. Popularity
   (Danawa rank: proven by buyers) carries the largest weight in every plan;
   compatibility, minimum specs and the ±5% budget band stay hard rules.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..catalog import CATEGORIES, CATEGORY_LABELS, Catalog, Part
from . import compatibility as compat
from .chipset import board_chipset, cpu_generation
from .requirements import (
    BUDGET_BAND,
    MinSpecs,
    Request,
    allocation,
    min_specs,
    perf_weights,
)

# Allocation tolerance tried in order until three distinct builds fit the band.
# None drops the per-category ranges (market prices far from the plan ratios).
TOLERANCES: tuple[float | None, ...] = (0.5, 1.0, 2.0, None)
BASE_TOLERANCE = 1.0  # always searched: a popular part may sit above the narrow range

# Share of each part in a build's popularity score.
PART_POPULARITY_WEIGHTS = {"cpu": 0.20, "gpu": 0.20, "board": 0.15, "ram": 0.10, "ssd": 0.10,
                           "psu": 0.10, "case": 0.10, "cooler": 0.05}


@dataclass(frozen=True)
class PlanType:
    key: str
    label: str
    popularity_weight: float
    performance_weight: float
    value_weight: float
    balance_weight: float
    summary: str


# Popularity 0.60 in every plan (store decision 2026-11-07, up from 0.50/0.45): buyers'
# choices outweigh the small performance/value edge of cheaper DDR4 platforms.
PLAN_TYPES = (
    PlanType("balanced", "균형형", 0.60, 0.20, 0.20, 2.0,
             "많이 팔린 검증된 부품 위주, 성능과 가격의 균형, CPU·GPU 병목을 가장 강하게 피함"),
    PlanType("performance", "성능 우선형", 0.60, 0.29, 0.11, 1.0, "검증된 부품 중 예산 +5% 안에서 성능 위주"),
    PlanType("value", "가성비형", 0.60, 0.11, 0.29, 1.0, "검증된 부품 중 가격 대비 성능 위주"),
)


@dataclass
class Build:
    parts: dict[str, Part | None]
    total: int
    performance: float
    balance: float
    popularity: float
    checks: list[compat.Check]

    @property
    def key(self) -> tuple[str | None, str | None]:
        gpu = self.parts.get("gpu")
        return self.parts["cpu"].id, gpu.id if gpu else None

    @property
    def value(self) -> float:
        return self.performance / self.total


@dataclass(frozen=True)
class Scorer:
    """Plan score with performance and value normalised to the best candidate (0–1)."""

    max_performance: float
    max_value: float

    @classmethod
    def over(cls, builds: list[Build]) -> Scorer:
        return cls(max((b.performance for b in builds), default=1.0) or 1.0,
                   max((b.value for b in builds), default=1.0) or 1.0)

    def score(self, build: Build, plan: PlanType) -> float:
        base = (plan.popularity_weight * build.popularity
                + plan.performance_weight * build.performance / self.max_performance
                + plan.value_weight * build.value / self.max_value)
        return base * build.balance**plan.balance_weight


@dataclass
class Plan:
    rank: int
    type: PlanType
    build: Build
    reasons: dict[str, str]
    warnings: list[str]

    def as_dict(self, catalog: Catalog, alloc: dict[str, int]) -> dict:
        parts = {}
        for c in CATEGORIES:
            p = self.build.parts.get(c)
            parts[c] = None if p is None else {
                "id": p.id,
                "name": p.name,
                "brand": p.brand,
                "price": p.price,
                "allocation": alloc.get(c, 0),
                "benchmark": round(catalog.norm(p), 1) if c in ("cpu", "gpu") else None,
                "popularityRank": catalog.rank(p),
                "sourceUrl": p.source_url,
                "priceObservedAt": p.price_observed_at.isoformat() if p.price_observed_at else None,
                "reason": self.reasons.get(c),
            }
        observed = [p.price_observed_at for p in self.build.parts.values() if p and p.price_observed_at]
        return {
            "rank": self.rank,
            "type": self.type.key,
            "label": self.type.label,
            "summary": self.type.summary,
            "parts": parts,
            "total": self.build.total,
            "performance": round(self.build.performance, 1),
            "popularity": round(self.build.popularity, 3),
            "balance": round(self.build.balance, 3),
            "checks": [c.as_dict() for c in self.build.checks],
            "warnings": self.warnings,
            "oldestPriceAt": min(observed).isoformat() if observed else None,
        }


@dataclass
class Result:
    request: Request
    allocation: dict[str, int]
    min_specs: MinSpecs
    plans: list[Plan]
    notes: list[str] = field(default_factory=list)
    candidates: int = 0
    builds: list[Build] = field(default_factory=list, repr=False)

    def as_dict(self, catalog: Catalog) -> dict:
        return {
            "allocation": self.allocation,
            "minSpecs": {
                "ramGb": self.min_specs.ram_gb,
                "ssdGb": self.min_specs.ssd_gb,
                "gpuReference": self.min_specs.gpu_reference,
                "gpuVramGb": self.min_specs.gpu_vram_gb,
                "notes": list(self.min_specs.notes),
            },
            "plans": [p.as_dict(catalog, self.allocation) for p in self.plans],
            "notes": self.notes,
            "candidates": self.candidates,
        }


# --- performance & popularity ---------------------------------------------


def tier(norm: float) -> int:
    """1–5 performance grade on the 0–100 normalised scale."""
    return max(1, min(5, math.ceil(norm / 20)))


def balance_factor(catalog: Catalog, cpu: Part, gpu: Part | None) -> float:
    """Bottleneck penalty: 10% per grade beyond one grade of CPU/GPU difference."""
    if gpu is None:
        return 1.0
    diff = abs(tier(catalog.norm(cpu)) - tier(catalog.norm(gpu)))
    return 0.9 ** max(0, diff - 1)


def performance(catalog: Catalog, req: Request, cpu: Part, gpu: Part | None) -> float:
    wc, wg = perf_weights(req)
    return wc * catalog.norm(cpu) + wg * catalog.norm(gpu)


def build_popularity(catalog: Catalog, parts: dict[str, Part | None]) -> float:
    present = {c: w for c, w in PART_POPULARITY_WEIGHTS.items() if parts.get(c) is not None}
    total = sum(present.values())
    return sum(w * catalog.popularity(parts[c]) for c, w in present.items()) / total


def _assemble(catalog: Catalog, req: Request, parts: dict[str, Part | None]) -> Build:
    cpu, gpu = parts["cpu"], parts.get("gpu")
    return Build(
        parts=parts,
        total=sum(p.price for p in parts.values() if p) + req.assembly_fee,
        performance=performance(catalog, req, cpu, gpu),
        balance=balance_factor(catalog, cpu, gpu),
        popularity=build_popularity(catalog, parts),
        checks=compat.check(parts),
    )


# --- candidate pools -------------------------------------------------------


def base_pools(catalog: Catalog, req: Request, specs: MinSpecs) -> dict[str, list[Part]]:
    """Usable parts meeting the request's hard conditions, before budget ranges."""
    excluded = {b.lower() for b in req.exclude_brands}
    excluded_ids = set(req.exclude_parts)

    def ok(p: Part) -> bool:
        return (p.brand or "").lower() not in excluded and p.id not in excluded_ids

    pools = {c: [p for p in catalog.usable(c) if ok(p)] for c in CATEGORIES}
    if not req.needs_gpu:
        pools["cpu"] = [p for p in pools["cpu"] if p.spec("igpu") is True]
        pools["gpu"] = []
    else:
        pools["gpu"] = [
            p for p in pools["gpu"]
            if p.benchmark >= specs.gpu_benchmark and p.spec("vram", 0) >= specs.gpu_vram_gb
        ]
    pools["ram"] = [p for p in pools["ram"] if p.spec("capacity") >= specs.ram_gb]
    pools["ssd"] = [p for p in pools["ssd"] if p.spec("capacity") >= specs.ssd_gb]
    if req.white:
        pools["case"] = [p for p in pools["case"] if p.spec("color") == "white"]
    if req.wifi:
        pools["board"] = [p for p in pools["board"] if p.spec("wifi")]
    pools["cooler"] = [p for p in pools["cooler"] if not compat.LIQUID.search(p.name)]
    return pools


def ranged(pool: list[Part], target: int, tolerance: float) -> list[Part]:
    lo, hi = target * (1 - tolerance), target * (1 + tolerance)
    return [p for p in pool if lo <= p.price <= hi]


REDUCE_KEYS = {
    # CPU/GPU: one entry per chip. A pricier chip that is not faster is kept:
    # it can be what brings the total into the ±5% band.
    "cpu": lambda p: (p.benchmark, p.spec("socket"), p.spec("watts"), p.spec("igpu")),
    "gpu": lambda p: (p.benchmark, p.spec("vram")),
    "board": lambda p: (p.spec("socket"), board_chipset(p), p.spec("form"), p.spec("ddr"),
                        p.spec("slots"), p.spec("maxRam"), p.spec("m2"), p.spec("wifi")),
    "ram": lambda p: (p.spec("ddr"), p.spec("capacity"), p.spec("sticks")),
    "ssd": lambda p: (p.spec("capacity"), bool(p.spec("m2"))),
    "psu": lambda p: (p.spec("capacity"), tuple(sorted(p.spec("connectors") or []))),
    "case": lambda p: (tuple(p.spec("forms") or []), p.spec("gpuLength"), p.spec("coolerHeight")),
    "cooler": lambda p: (tuple(p.spec("sockets") or []), p.spec("height"), p.spec("coolingWatts")),
}


def reduce(catalog: Catalog, category: str, parts: list[Part]) -> list[Part]:
    """Per group of equivalent specs keep the cheapest and the most popular part."""
    groups: dict = {}
    for p in parts:
        groups.setdefault(REDUCE_KEYS[category](p), []).append(p)
    keep: dict[str, Part] = {}
    for group in groups.values():
        cheapest = min(group, key=lambda p: p.price)
        popular = max(group, key=lambda p: (catalog.popularity(p), -p.price))
        keep[cheapest.id] = cheapest
        keep[popular.id] = popular
    return sorted(keep.values(), key=lambda p: p.price)


# --- search ----------------------------------------------------------------


class _Search:
    """Remaining parts for each CPU×GPU pair, in two modes.

    ``cheap`` takes the cheapest compatible part of each kind; ``popular`` the
    most popular (ties → cheaper). The remaining parts split into independent
    sub-problems, each memoised on the only specs that affect it: PSU (CPU/GPU
    power), board list (CPU platform), RAM+SSD (board memory/M.2), case+cooler
    (GPU length, board form, CPU socket and power).
    """

    MODES = ("cheap", "popular")

    def __init__(self, catalog: Catalog, req: Request, pools: dict[str, list[Part]]):
        self.catalog, self.req = catalog, req
        pop = catalog.popularity
        self.ordered = {
            "cheap": pools,
            "popular": {c: sorted(ps, key=lambda p: (-pop(p), p.price)) for c, ps in pools.items()},
        }
        self.pools = pools
        self._memo: dict[str, dict] = {}

    def _cached(self, table: str, key, compute):
        memo = self._memo.setdefault(table, {})
        if key not in memo:
            memo[key] = compute()
        return memo[key]

    def _utility(self, mode: str, parts: dict[str, Part]) -> tuple:
        """Lower is better: cost for cheap mode, (−popularity, cost) for popular mode."""
        cost = sum(p.price for p in parts.values())
        if mode == "cheap":
            return (cost,)
        pop = sum(PART_POPULARITY_WEIGHTS[c] * self.catalog.popularity(p) for c, p in parts.items())
        return (-round(pop, 6), cost)

    def _psu(self, mode: str, cpu: Part, gpu: Part | None) -> Part | None:
        key = (mode, compat.cpu_power(cpu), gpu.spec("watts") if gpu else 0,
               gpu.spec("connector") if gpu else None, gpu.spec("minPsu") if gpu else None)
        return self._cached("psu", key, lambda: next(
            (p for p in self.ordered[mode]["psu"] if compat.passes({"cpu": cpu, "gpu": gpu, "psu": p})), None))

    def _boards(self, cpu: Part) -> list[Part]:
        key = (cpu.spec("socket"), cpu_generation(cpu), compat.cpu_power(cpu))
        return self._cached("boards", key, lambda: [
            b for b in self.pools["board"] if compat.passes({"cpu": cpu, "board": b})])

    def _extras(self, mode: str, board: Part) -> tuple[Part, Part] | None:
        key = (mode, board.spec("ddr"), board.spec("slots"), board.spec("maxRam"), board.spec("m2"))
        order = self.ordered[mode]

        def compute():
            ram = next((r for r in order["ram"] if compat.passes({"board": board, "ram": r}, "ram")), None)
            ssd = next((s for s in order["ssd"] if compat.passes({"board": board, "ssd": s}, "ssd")), None)
            return (ram, ssd) if ram and ssd else None

        return self._cached("extras", key, compute)

    def _coolers(self, mode: str, cpu: Part) -> list[Part]:
        key = (mode, cpu.spec("socket"), cpu.spec("tdp"), cpu.spec("watts"))
        return self._cached("coolers", key, lambda: [
            c for c in self.ordered[mode]["cooler"] if compat.passes({"cpu": cpu, "cooler": c})])

    def _case_cooler(self, mode: str, cpu: Part, gpu: Part | None, board: Part) -> tuple[Part, Part] | None:
        coolers = self._coolers(mode, cpu)
        key = (mode, gpu.spec("length") if gpu else None, board.spec("form"), cpu.spec("socket"),
               cpu.spec("tdp"), cpu.spec("watts"))

        def compute():
            if not coolers:
                return None
            best, best_u = None, None
            cheapest_cooler = min(c.price for c in coolers)
            for case in self.pools["case"]:
                if mode == "cheap" and best_u is not None and case.price + cheapest_cooler >= best_u[0]:
                    break
                if not compat.passes({"gpu": gpu, "board": board, "case": case}, "case"):
                    continue
                cooler = next((c for c in coolers
                               if compat.passes({"cpu": cpu, "case": case, "cooler": c}, "cooler")), None)
                if cooler is None:
                    continue
                u = self._utility(mode, {"case": case, "cooler": cooler})
                if best_u is None or u < best_u:
                    best, best_u = (case, cooler), u
            return best

        return self._cached("case", key, compute)

    @staticmethod
    def _rest_key(cpu: Part, gpu: Part | None) -> tuple:
        g = (gpu.spec("watts"), gpu.spec("length"), gpu.spec("connector"), gpu.spec("minPsu")) if gpu else None
        return (cpu.spec("socket"), cpu_generation(cpu), cpu.spec("watts"), cpu.spec("tdp"), cpu.spec("igpu"), g)

    def rest(self, mode: str, cpu: Part, gpu: Part | None) -> dict[str, Part] | None:
        return self._cached("rest", (mode, self._rest_key(cpu, gpu)), lambda: self._find_rest(mode, cpu, gpu))

    def _find_rest(self, mode: str, cpu: Part, gpu: Part | None) -> dict[str, Part] | None:
        psu = self._psu(mode, cpu, gpu)
        if psu is None:
            return None
        best, best_u = None, None
        for board in self._boards(cpu):
            if mode == "cheap" and best_u is not None and board.price + psu.price >= best_u[0]:
                break
            extras = self._extras(mode, board)
            case_cooler = self._case_cooler(mode, cpu, gpu, board) if extras else None
            if not case_cooler:
                continue
            (ram, ssd), (case, cooler) = extras, case_cooler
            rest = {"board": board, "ram": ram, "ssd": ssd, "psu": psu, "case": case, "cooler": cooler}
            u = self._utility(mode, rest)
            if best_u is None or u < best_u:
                best, best_u = rest, u
        return best

    def _upgrade(self, cpu: Part, gpu: Part | None, cheap: dict[str, Part], popular: dict[str, Part],
                 cap: float) -> dict[str, Part]:
        """Start from the cheapest rest and swap in popular parts while the total stays under ``cap``.

        Swaps go in order of popularity gained per won, so a popular PSU that
        fits is taken even when the all-popular set would overshoot.
        """
        pop = self.catalog.popularity
        rest = dict(cheap)
        total = sum(p.price for p in rest.values()) + cpu.price + (gpu.price if gpu else 0) + self.req.assembly_fee

        def gain(c: str) -> float:
            delta_pop = PART_POPULARITY_WEIGHTS[c] * (pop(popular[c]) - pop(cheap[c]))
            return delta_pop / max(popular[c].price - cheap[c].price, 1)

        for c in sorted((c for c in rest if pop(popular[c]) > pop(cheap[c])), key=gain, reverse=True):
            new_total = total - rest[c].price + popular[c].price
            trial = {**rest, c: popular[c]}
            if new_total <= cap and compat.passes({"cpu": cpu, "gpu": gpu, **trial}):
                rest, total = trial, new_total
        return rest

    def builds(self, cap: float = math.inf) -> list[Build]:
        out = []
        gpus: list[Part | None] = self.pools["gpu"] if self.req.needs_gpu else [None]
        for cpu in self.pools["cpu"]:
            for gpu in gpus:
                if not compat.passes({"cpu": cpu, "gpu": gpu}):
                    continue
                cheap, popular = self.rest("cheap", cpu, gpu), self.rest("popular", cpu, gpu)
                variants = [cheap, popular]
                if cheap and popular and cheap != popular:
                    variants.append(self._upgrade(cpu, gpu, cheap, popular, cap))
                seen = []
                for rest in variants:
                    if rest is None or rest in seen:
                        continue
                    seen.append(rest)
                    out.append(_assemble(self.catalog, self.req, {"cpu": cpu, "gpu": gpu, **rest}))
        return out


# Parts that decide the platform. Memory type (DDR4/DDR5) and socket split the market;
# a fixed budget share can leave one memory type entirely outside its price range
# (2026: 32GB DDR5 costs far more than 7% of a gaming budget), which would drop
# every DDR5-only platform before scoring. Each platform keeps its cheapest and
# most popular part regardless of the range; the ±5% total band still applies.
PLATFORM_KEYS = {
    "ram": lambda p: p.spec("ddr"),
    "board": lambda p: (p.spec("socket"), p.spec("ddr")),
}


def platform_anchors(catalog: Catalog, category: str, pool: list[Part], budget: int) -> list[Part]:
    groups: dict = {}
    for p in pool:
        if p.price <= budget:
            groups.setdefault(PLATFORM_KEYS[category](p), []).append(p)
    out = []
    for group in groups.values():
        out.append(min(group, key=lambda p: p.price))
        out.append(max(group, key=lambda p: (catalog.popularity(p), -p.price)))
    return out


def _search(catalog: Catalog, req: Request, specs: MinSpecs, alloc: dict[str, int], tolerance: float | None,
            notes: list[str]) -> list[Build]:
    """Builds with each category inside its allocation ± tolerance (None = no range)."""
    base = base_pools(catalog, req, specs)
    pools = {}
    for c in CATEGORIES:
        if c == "gpu" and not req.needs_gpu:
            pools[c] = []
            continue
        candidates = base[c] if tolerance is None else ranged(base[c], alloc[c], tolerance)
        if not candidates and base[c]:
            # Nothing inside the range: fall back to the full pool under the budget cap.
            candidates = [p for p in base[c] if p.price <= req.parts_budget]
            notes.append(f"{CATEGORY_LABELS[c]}: 배분 예산 범위 안 제품이 없어 범위를 넓힘")
        if c in PLATFORM_KEYS and tolerance is not None:
            ids = {p.id for p in candidates}
            candidates = candidates + [p for p in platform_anchors(catalog, c, base[c], req.parts_budget) if p.id not in ids]
        pools[c] = reduce(catalog, c, candidates)
    return _Search(catalog, req, pools).builds(cap=req.budget * (1 + BUDGET_BAND))


def _rank_text(catalog: Catalog, part: Part) -> str:
    rank = catalog.rank(part)
    return f" · 다나와 인기 {rank}위" if rank else ""


def _explain(catalog: Catalog, req: Request, specs: MinSpecs, alloc: dict[str, int], build: Build) -> dict[str, str]:
    p = build.parts
    rt = lambda c: _rank_text(catalog, p[c])  # noqa: E731
    share = lambda c: f"{alloc[c] / req.parts_budget * 100:.0f}%"  # noqa: E731
    reasons = {}
    cpu = p["cpu"]
    reasons["cpu"] = f"CPU 배분 {share('cpu')}({alloc['cpu']:,}원) 기준. 성능 지수 {catalog.norm(cpu):.0f}/100{rt('cpu')}"
    if p.get("gpu"):
        gpu = p["gpu"]
        floor = f", 최소 기준 {specs.gpu_reference}급 충족" if specs.gpu_reference else ""
        reasons["gpu"] = (f"GPU 배분 {share('gpu')}({alloc['gpu']:,}원) 기준. "
                          f"성능 지수 {catalog.norm(gpu):.0f}/100, VRAM {gpu.spec('vram')}GB{floor}{rt('gpu')}")
    b = p["board"]
    reasons["board"] = f"{board_chipset(b) or ''} {b.spec('socket')}·{b.spec('form')}·DDR{b.spec('ddr')} 호환{rt('board')}".strip()
    r = p["ram"]
    reasons["ram"] = f"DDR{r.spec('ddr')} {r.spec('capacity')}GB (최소 {specs.ram_gb}GB 기준){rt('ram')}"
    s = p["ssd"]
    reasons["ssd"] = f"{s.spec('capacity')}GB {'NVMe M.2' if s.spec('m2') else 'SATA'} (최소 {specs.ssd_gb}GB 기준){rt('ssd')}"
    ps = p["psu"]
    need = compat.required_psu_watts(cpu, p.get("gpu"))
    reasons["psu"] = f"{ps.spec('capacity')}W — 필요 용량 {need}W 이상{rt('psu')}"
    k = p["case"]
    reasons["case"] = f"GPU {k.spec('gpuLength')}mm·쿨러 {k.spec('coolerHeight')}mm까지 장착 가능{rt('case')}"
    co = p["cooler"]
    reasons["cooler"] = f"냉각 {co.spec('coolingWatts')}W, 높이 {co.spec('height')}mm로 케이스에 장착 가능{rt('cooler')}"
    return reasons


def _pick_plans(builds: list[Build], notes: list[str]) -> dict[str, Build]:
    """Pick the three plans so their order is fixed for the customer.

    - 성능 우선형: the strongest and most expensive (faster than balanced, not cheaper).
    - 가성비형: the cheapest (cheaper than balanced, not faster than 성능 우선형).
    - 균형형: the best balanced score that still leaves room for both. Balanced
      candidates are tried in score order; the first that admits a performance and a
      value plan wins. If none does, the top balanced build is kept with whatever fits.
    Each plan takes its own best by score among the CPU·GPU pairs that keep the order.
    """
    if not builds:
        return {}
    scorer = Scorer.over(builds)
    balanced, performance, value = PLAN_TYPES
    by = {t.key: sorted(builds, key=lambda b, t=t: (-scorer.score(b, t), b.total)) for t in PLAN_TYPES}

    def strong_for(base: Build) -> Build | None:
        return next((b for b in by[performance.key]
                     if b.key != base.key and b.performance > base.performance and b.total >= base.total), None)

    def cheap_for(base: Build, strong: Build | None) -> Build | None:
        return next((b for b in by[value.key]
                     if b.key not in {base.key, strong.key if strong else None} and b.total < base.total
                     and (strong is None or b.performance <= strong.performance)), None)

    chosen = None
    seen: set = set()
    for base in by[balanced.key]:
        if base.key in seen:
            continue
        seen.add(base.key)
        strong = strong_for(base)
        cheap = cheap_for(base, strong)
        if chosen is None:
            chosen = (base, strong, cheap)
        if strong and cheap:
            chosen = (base, strong, cheap)
            break
    base, strong, cheap = chosen
    picks = {balanced.key: base}
    if strong:
        picks[performance.key] = strong
    else:
        notes.append(f"{performance.label}: 균형안보다 성능이 높고 가격이 같거나 높은 조합이 없어 생략")
    if cheap:
        picks[value.key] = cheap
    else:
        notes.append(f"{value.label}: 균형안보다 저렴한 조합이 없어 생략")
    return picks


def recommend(catalog: Catalog, req: Request) -> Result:
    specs = min_specs(req, catalog)
    alloc = allocation(req)
    lo, hi = req.budget * (1 - BUDGET_BAND), req.budget * (1 + BUDGET_BAND)
    # Every allocation range up to BASE_TOLERANCE is searched, so a popular part
    # priced above the narrow range still competes. Wider ranges are tried only
    # while the band cannot yet give three plans in order (see _pick_plans).
    pooled: dict[tuple, Build] = {}
    notes: list[str] = []
    widest: float | None = 0.0
    last_builds: list[Build] = []
    for tolerance in TOLERANCES:
        attempt_notes: list[str] = []
        last_builds = _search(catalog, req, specs, alloc, tolerance, attempt_notes)
        for b in last_builds:
            if lo <= b.total <= hi:
                pooled.setdefault(tuple(p.id if p else None for p in b.parts.values()), b)
        notes = list(dict.fromkeys(notes + attempt_notes))
        widest = tolerance
        enough = len(_pick_plans(list(pooled.values()), [])) == len(PLAN_TYPES)  # three plans in price/performance order
        if enough and (tolerance is None or tolerance >= BASE_TOLERANCE):
            break
    builds = list(pooled.values())
    if builds:
        if widest is None:
            notes.append("배분 비율 범위 안 조합이 부족해 비율을 벗어난 조합까지 포함함")
        elif widest > BASE_TOLERANCE:
            notes.append(f"배분 비율 ±{BASE_TOLERANCE * 100:.0f}% 안 조합이 부족해 ±{widest * 100:.0f}%까지 넓혀 찾음")
    else:
        # Nothing inside ±5%: step the lower bound down so the offer stays near the budget.
        builds, notes = [], ["조건과 예산에 맞는 호환 조합을 찾지 못함"]
        unrestricted = _search(catalog, req, specs, alloc, None, [])
        if unrestricted:
            cheapest = min(unrestricted, key=lambda b: b.total)
            if cheapest.total > hi:
                notes.append(f"이 조건(최소 사양 포함)으로 가능한 최저 견적은 {cheapest.total:,}원")
        for floor in (0.85, 0.70, 0.0):
            near = [b for b in last_builds if req.budget * floor <= b.total <= hi]
            if near:
                builds = near
                notes = [f"예산 ±5% 안 조합이 없어 예산의 {floor * 100:.0f}% 이상 조합을 제시함" if floor
                         else "예산 ±5% 안 조합이 없어 더 저렴한 조합을 제시함"]
                break

    picks = _pick_plans(builds, notes)
    plans: list[Plan] = []
    for plan_type in PLAN_TYPES:
        if pick := picks.get(plan_type.key):
            warnings = [c.detail for c in pick.checks if c.status == "warn"]
            plans.append(Plan(len(plans) + 1, plan_type, pick, _explain(catalog, req, specs, alloc, pick), warnings))
    return Result(req, alloc, specs, plans, notes, len(builds), builds)


def evaluate(catalog: Catalog, req: Request, part_ids: dict[str, str | None]) -> dict:
    """Recalculate a quote after a manual change (plan scenario step 4)."""
    parts: dict[str, Part | None] = {}
    missing = []
    for c in CATEGORIES:
        pid = part_ids.get(c)
        if pid is None and c == "gpu" and not req.needs_gpu:
            parts[c] = None
            continue
        part = catalog.by_id.get(pid) if pid else None
        if part is None or part.category != c:
            missing.append(CATEGORY_LABELS[c])
        parts[c] = part
    if missing:
        return {"ok": False, "error": f"부품 누락 또는 잘못된 부품: {', '.join(missing)}"}
    build = _assemble(catalog, req, parts)
    return {
        "ok": all(c.status != "fail" for c in build.checks),
        "total": build.total,
        "budgetDelta": build.total - req.budget,
        "withinBand": abs(build.total - req.budget) <= req.budget * BUDGET_BAND,
        "performance": round(build.performance, 1),
        "popularity": round(build.popularity, 3),
        "checks": [c.as_dict() for c in build.checks],
    }


def alternatives(catalog: Catalog, req: Request, part_ids: dict[str, str | None], category: str,
                 limit: int = 20) -> list[dict]:
    """Compatible replacements for one category: popular first, then nearest price."""
    current = {c: catalog.by_id.get(pid) if pid else None for c, pid in part_ids.items()}
    for c in CATEGORIES:
        current.setdefault(c, None)
    now = current.get(category)
    out = []
    for p in catalog.usable(category):
        if now and p.id == now.id:
            continue
        trial = {**current, category: p}
        if not compat.passes({k: v for k, v in trial.items() if v is not None or k == "gpu"}, category):
            continue
        out.append({
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "priceDelta": p.price - (now.price if now else 0),
            "benchmark": round(catalog.norm(p), 1) if category in ("cpu", "gpu") else None,
            "popularityRank": catalog.rank(p),
        })
    out.sort(key=lambda x: (x["popularityRank"] or math.inf, abs(x["priceDelta"]), x["price"]))
    return out[:limit]
