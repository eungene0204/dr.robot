"""In-memory part model used by the recommendation engine.

The engine never reads the database directly: the API loads parts once and
passes a ``Catalog`` in, so engine tests run without PostgreSQL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

CATEGORIES = ("cpu", "board", "ram", "gpu", "ssd", "psu", "case", "cooler")
CATEGORY_LABELS = {
    "cpu": "CPU",
    "board": "메인보드",
    "ram": "메모리",
    "gpu": "그래픽카드",
    "ssd": "SSD",
    "psu": "파워",
    "case": "케이스",
    "cooler": "CPU 쿨러",
}

# Specs without which a part cannot pass the compatibility rules.
REQUIRED_SPECS: dict[str, tuple[str, ...]] = {
    "cpu": ("socket", "watts"),
    "board": ("socket", "ddr", "form", "slots", "m2"),
    "ram": ("ddr", "capacity", "sticks"),
    "gpu": ("watts", "length", "vram"),
    "ssd": ("capacity",),
    "psu": ("capacity",),
    "case": ("forms", "gpuLength", "coolerHeight"),
    "cooler": ("sockets", "height", "coolingWatts"),
}


@dataclass(frozen=True)
class Part:
    id: str
    category: str
    name: str
    price: int
    brand: str | None = None
    in_stock: bool = True
    specs: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)
    benchmark: float | None = None
    benchmark_name: str | None = None
    source_url: str | None = None
    price_observed_at: datetime | None = None
    # Danawa "인기상품순" rank within the category (1 = most popular).
    popularity_rank: int | None = None
    popularity_observed_at: datetime | None = None
    # False when the store data policy rejects the part for a reason other than price age
    # (missing fact, SATA drive, unmeasured benchmark…). Stale prices are refreshed instead.
    quotable: bool = True

    def spec(self, key: str, default: Any = None) -> Any:
        value = self.specs.get(key)
        return default if value is None else value

    def missing_specs(self) -> list[str]:
        return [k for k in REQUIRED_SPECS.get(self.category, ()) if self.specs.get(k) in (None, [], "")]

    @property
    def usable(self) -> bool:
        if not self.quotable or not self.in_stock or self.price <= 0 or self.missing_specs():
            return False
        if self.category in ("cpu", "gpu") and not self.benchmark:
            return False
        # Store policy: only drives confirmed as NVMe fill the storage slot (SATA stays in the catalog).
        if self.category == "ssd" and self.specs.get("interface") != "nvme":
            return False
        return True


POPULARITY_DEPTH = 30  # Danawa lists ranks 1–30 per category
POPULARITY_MAX_AGE = timedelta(days=14)


class Catalog:
    """Parts grouped by category with benchmark normalisation (best part = 100)."""

    def __init__(self, parts: list[Part], now: datetime | None = None):
        self.now = now or datetime.now(timezone.utc)
        self.parts = parts
        self.by_id = {p.id: p for p in parts}
        self.by_category: dict[str, list[Part]] = {c: [] for c in CATEGORIES}
        for p in parts:
            if p.category in self.by_category:
                self.by_category[p.category].append(p)
        self.max_benchmark = {
            c: max((p.benchmark for p in self.by_category[c] if p.usable and p.benchmark), default=1.0)
            for c in ("cpu", "gpu")
        }

    def usable(self, category: str) -> list[Part]:
        return [p for p in self.by_category[category] if p.usable]

    def norm(self, part: Part | None) -> float:
        """Benchmark on a 0-100 scale relative to the best usable part of its category."""
        if part is None or not part.benchmark:
            return 0.0
        return 100.0 * part.benchmark / self.max_benchmark[part.category]

    def benchmark_of(self, category: str, model: str) -> float | None:
        """Benchmark of a reference chip (e.g. 'RTX 4060'), matched on benchmark name."""
        key = model.lower()
        scores = [
            p.benchmark
            for p in self.by_category[category]
            if p.benchmark and p.benchmark_name and p.benchmark_name.lower().endswith(key)
        ]
        return max(scores) if scores else None

    def rank(self, part: Part | None) -> int | None:
        """Popularity rank if it is fresh enough to trust, else None."""
        if part is None or not part.popularity_rank or part.popularity_observed_at is None:
            return None
        if self.now - part.popularity_observed_at > POPULARITY_MAX_AGE:
            return None
        return part.popularity_rank

    def popularity(self, part: Part | None) -> float:
        """1.0 for rank 1 down to 1/30 for rank 30; 0 when unranked or stale."""
        rank = self.rank(part)
        if rank is None or rank > POPULARITY_DEPTH:
            return 0.0
        return (POPULARITY_DEPTH + 1 - rank) / POPULARITY_DEPTH
