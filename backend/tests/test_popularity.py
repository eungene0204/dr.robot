from dataclasses import replace

import pytest

from conftest import NOW, part, sample_parts
from pcquote.catalog import Catalog
from pcquote.engine.recommend import PLAN_TYPES, recommend
from pcquote.engine.requirements import Request


def test_rank_to_score():
    c = Catalog([part("a", "ssd", "a", 1, rank=1), part("b", "ssd", "b", 1, rank=30),
                 part("c", "ssd", "c", 1), part("d", "ssd", "d", 1, rank=1, rank_age_days=30)], now=NOW)
    assert c.popularity(c.by_id["a"]) == 1.0
    assert c.popularity(c.by_id["b"]) == pytest.approx(1 / 30)
    assert c.popularity(c.by_id["c"]) == 0.0
    assert c.popularity(c.by_id["d"]) == 0.0  # stale rank is ignored


def test_popularity_has_the_largest_weight_in_every_plan():
    for t in PLAN_TYPES:
        assert t.popularity_weight > t.performance_weight
        assert t.popularity_weight > t.value_weight
        assert t.popularity_weight + t.performance_weight + t.value_weight == pytest.approx(1.0)


def _with(parts, **ranks):
    return [replace(p, popularity_rank=ranks[p.id], popularity_observed_at=NOW) if p.id in ranks else p
            for p in parts]


def test_popular_psu_beats_cheaper_unranked_one():
    parts = sample_parts() + [part("p-pop", "psu", "인기 850W 골드", 140_000, rank=1,
                                   capacity=850, connectors=["8pin", "12v2x6"])]
    result = recommend(Catalog(parts, now=NOW), Request(budget=1_800_000))
    assert result.plans
    assert all(p.build.parts["psu"].id == "p-pop" for p in result.plans)


def test_popular_cpu_wins_over_faster_unranked_cpus():
    # 7500F (66) is the slowest CPU in its band but ranked 1st; the 1순위 plan
    # should take it over the faster, unranked 14400F (77) and 13400 (73).
    parts = _with(sample_parts(), **{"c-7500f": 1})
    result = recommend(Catalog(parts, now=NOW), Request(budget=1_800_000))
    assert result.plans[0].type.key == "balanced"
    assert result.plans[0].build.parts["cpu"].id == "c-7500f"


def test_popularity_never_breaks_hard_rules():
    # The most popular board is DDR4; it must not be paired with DDR5 memory.
    parts = _with(sample_parts(), **{"b-h610": 1})
    result = recommend(Catalog(parts, now=NOW), Request(budget=1_800_000))
    for plan in result.plans:
        assert all(c.status != "fail" for c in plan.build.checks)


def test_reason_mentions_rank():
    parts = _with(sample_parts(), **{"g-5070": 2})
    result = recommend(Catalog(parts, now=NOW), Request(budget=1_500_000))
    gpu_plans = [p for p in result.plans if p.build.parts["gpu"].id == "g-5070"]
    assert gpu_plans and "인기 2위" in gpu_plans[0].reasons["gpu"]


def test_popular_part_upgrades_fit_inside_budget():
    # For 7500F + 5070 Ti the all-popular rest (PSU + case) overshoots +5%, but
    # the popular PSU alone fits: that partial upgrade must be a candidate.
    parts = sample_parts() + [
        part("p-pop", "psu", "인기 850W 골드", 150_000, rank=1, capacity=850, connectors=["8pin", "12v2x6"]),
        part("k-pop", "case", "인기 케이스", 140_000, rank=1, forms=["ATX", "mATX"], gpuLength=380,
             coolerHeight=165, color="black"),
    ]
    result = recommend(Catalog(parts, now=NOW), Request(budget=1_800_000))
    pair = [b for b in result.builds if b.key == ("c-7500f", "g-5070ti")]
    assert all(b.total <= 1_890_000 for b in pair)
    assert any(b.parts["psu"].id == "p-pop" for b in pair)


def _expensive_ddr5_market():
    """2026 prices: 32GB DDR5 far above the RAM share of the budget, DDR4 within it."""
    parts = [p for p in sample_parts() if p.category != "ram"]
    return parts + [
        part("r5-32", "ram", "DDR5-5600 32GB (16Gx2)", 600_000, rank=1, ddr=5, capacity=32, sticks=2),
        part("r5-32-pop", "ram", "인기 DDR5-5600 32GB (16Gx2)", 750_000, rank=2, ddr=5, capacity=32, sticks=2),
        part("r4-32", "ram", "DDR4-3200 32GB (16Gx2)", 200_000, ddr=4, capacity=32, sticks=2),
    ]


def test_ddr5_platforms_stay_candidates_when_ddr5_ram_exceeds_the_ram_share():
    # RAM share of 2,500,000 is ~171,500: the DDR4 kit is inside ±50%, every 32GB DDR5 kit is
    # beyond ±100%, so the search stops early with DDR4 builds only (the 2026 market).
    # DDR5-only platforms (AM5, LGA1851) must still be searched, not dropped before scoring.
    parts = _with(_expensive_ddr5_market(), **{"c-9800x3d": 1, "b-b850": 1})
    result = recommend(Catalog(parts, now=NOW), Request(budget=2_500_000, resolution="QHD"))
    sockets = {b.parts["cpu"].spec("socket") for b in result.builds}
    assert {"AM5", "LGA1851"} <= sockets
    # Each memory type keeps its cheapest and its most popular kit in the search pool.
    from pcquote.engine.recommend import platform_anchors

    catalog = Catalog(parts, now=NOW)
    anchors = {p.id for p in platform_anchors(catalog, "ram", catalog.usable("ram"), 2_500_000)}
    assert anchors == {"r5-32", "r4-32"}  # r5-32 is both the cheapest and the top-ranked DDR5 kit


@pytest.mark.parametrize("budget, resolution", [(1_200_000, "FHD"), (1_500_000, "QHD"), (1_800_000, "QHD"),
                                                (2_500_000, "QHD"), (3_300_000, "4K")])
def test_plans_are_ordered_enhanced_most_expensive_and_strongest_saving_cheapest(budget, resolution):
    parts = _with(sample_parts(), **{"c-7500f": 1, "b-b650": 1, "g-5060ti": 1})
    result = recommend(Catalog(parts, now=NOW), Request(budget=budget, resolution=resolution))
    plans = {p.type.key: p.build for p in result.plans}
    base = plans["balanced"]
    if "performance" in plans:
        strong = plans["performance"]
        assert strong.total >= base.total and strong.performance > base.performance
        assert strong.performance >= max(b.performance for b in plans.values())
        assert strong.total >= max(b.total for b in plans.values())
    if "value" in plans:
        assert plans["value"].total < base.total
