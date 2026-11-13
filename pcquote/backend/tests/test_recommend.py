from pcquote.engine.recommend import Scorer, alternatives, evaluate, recommend
from pcquote.engine.requirements import CHEAP_GAP, POOL_FLOOR, STRONG_GAP, Request


def _ids(plan):
    return {c: (p.id if p else None) for c, p in plan.build.parts.items()}


def test_three_distinct_plans_under_budget_ceiling(catalog):
    req = Request(budget=1_800_000, uses=("gaming",))
    result = recommend(catalog, req)
    assert [p.type.key for p in result.plans] == ["balanced", "performance", "value"]
    assert len({p.build.key for p in result.plans}) == 3
    for plan in result.plans:
        assert plan.build.total <= req.budget
        assert all(c.status != "fail" for c in plan.build.checks)


def test_each_plan_is_best_by_its_own_score_among_builds_that_keep_the_order(catalog):
    result = recommend(catalog, Request(budget=1_800_000))
    scorer = Scorer.over(result.builds)
    plans = {p.type.key: p for p in result.plans}
    base = plans["balanced"].build
    if "performance" in plans:
        strong = plans["performance"]
        allowed = [b for b in result.builds if b.performance > base.performance and b.total >= base.total * STRONG_GAP]
        assert scorer.score(strong.build, strong.type) == max(scorer.score(b, strong.type) for b in allowed)
    if "value" in plans:
        cheap = plans["value"]
        cap = plans["performance"].build.performance if "performance" in plans else float("inf")
        allowed = [b for b in result.builds if b.total <= base.total * CHEAP_GAP and b.performance <= cap]
        assert scorer.score(cheap.build, cheap.type) == max(scorer.score(b, cheap.type) for b in allowed)


def test_intel_is_recommended_when_it_scores_best(catalog):
    # 245KF has the best CPU benchmark per won in the fixture; nothing restricts vendors.
    result = recommend(catalog, Request(budget=1_500_000))
    vendors = {p.build.parts["cpu"].brand for p in result.plans}
    assert "Intel" in vendors


def test_bios_update_condition_is_reported(catalog):
    result = recommend(catalog, Request(budget=1_500_000))
    for plan in result.plans:
        warn = [c for c in plan.build.checks if c.status == "warn"]
        assert plan.warnings == [c.detail for c in warn]


def test_qhd_minimum_gpu_is_respected(catalog):
    result = recommend(catalog, Request(budget=2_000_000, resolution="QHD"))
    assert result.plans
    for plan in result.plans:
        assert plan.build.parts["gpu"].benchmark >= 100  # RTX 5060 Ti reference
        assert plan.build.parts["ram"].spec("capacity") >= 32


def test_office_uses_integrated_graphics(catalog):
    result = recommend(catalog, Request(budget=750_000, uses=("office",)))
    assert result.plans
    for plan in result.plans:
        assert plan.build.parts["gpu"] is None
        assert plan.build.parts["cpu"].spec("igpu") is True


def test_white_case_and_brand_exclusion(catalog):
    result = recommend(catalog, Request(budget=1_500_000, white=True, exclude_brands=("Intel",)))
    assert result.plans
    for plan in result.plans:
        assert plan.build.parts["case"].spec("color") == "white"
        assert plan.build.parts["cpu"].brand != "Intel"


def test_impossible_budget_reports_instead_of_breaking_rules(catalog):
    # 4K needs an RTX 5070 Ti-class card that cannot fit in this budget.
    result = recommend(catalog, Request(budget=900_000, resolution="4K"))
    assert result.plans == []
    # Staff need the smallest feasible budget to continue the consultation.
    assert any("가능한 최저 견적" in n for n in result.notes)


def test_every_plan_explains_each_part(catalog):
    result = recommend(catalog, Request(budget=1_500_000))
    for plan in result.plans:
        assert set(plan.reasons) == {"cpu", "gpu", "board", "ram", "ssd", "psu", "case", "cooler"}


def test_evaluate_after_swap_recomputes_total_and_compatibility(catalog):
    req = Request(budget=1_500_000)
    plan = recommend(catalog, req).plans[0]
    ids = _ids(plan)
    same = evaluate(catalog, req, ids)
    assert same["ok"] and same["total"] == plan.build.total
    # Swapping in a DDR4 board breaks the memory rule and must be reported.
    ids["board"] = "b-h610"
    broken = evaluate(catalog, req, ids)
    assert not broken["ok"]
    assert any(c["label"] == "메모리 규격" and c["status"] == "fail" for c in broken["checks"])


def test_alternatives_are_compatible_and_exclude_current(catalog):
    req = Request(budget=1_500_000)
    plan = recommend(catalog, req).plans[0]
    ids = _ids(plan)
    alts = alternatives(catalog, req, ids, "ssd")
    assert alts and all(a["id"] != ids["ssd"] for a in alts)
    for alt in alts:
        assert evaluate(catalog, req, {**ids, "ssd": alt["id"]})["ok"]
    # The DDR4 H610 board is never offered next to DDR5 memory.
    assert "b-h610" not in {a["id"] for a in alternatives(catalog, req, ids, "board")}


def test_plan_shows_fewer_options_instead_of_duplicates(catalog):
    result = recommend(catalog, Request(budget=1_500_000))
    assert len({p.build.key for p in result.plans}) == len(result.plans)
    if len(result.plans) < 3:
        assert any("생략" in n for n in result.notes)


def test_fallback_stays_near_budget(catalog):
    # No fixture build reaches 2.2M; the offer must not drop to a 1M build.
    result = recommend(catalog, Request(budget=2_200_000))
    assert result.plans
    assert all(2_200_000 * POOL_FLOOR <= p.build.total <= 2_200_000 for p in result.plans)
    assert result.notes


def test_plans_never_exceed_budget_and_are_priced_apart(catalog):
    for budget in (1_500_000, 1_800_000):
        result = recommend(catalog, Request(budget=budget, uses=("gaming",)))
        totals = {p.type.key: p.build.total for p in result.plans}
        assert all(t <= budget for t in totals.values())
        if len(totals) == 3:
            assert totals["performance"] >= totals["balanced"] * STRONG_GAP
            assert totals["value"] <= totals["balanced"] * CHEAP_GAP


def test_budget_below_minimum_lowers_specs_step_by_step(catalog):
    # Gaming QHD needs 32GB in the fixture's cheapest build above 1.2M; 16GB fits.
    result = recommend(catalog, Request(budget=1_200_000, uses=("gaming",), resolution="QHD"))
    assert result.plans and result.relaxed == ("메모리 32GB → 16GB",)
    assert all(p.build.total <= 1_200_000 for p in result.plans)
    assert result.min_specs.ram_gb == 16 and result.min_specs.ssd_gb == 1000  # stops at the first step that fits
    assert any("최소 사양을 낮춤" in n for n in result.notes)


def test_gpu_reference_drops_one_resolution_last(catalog):
    result = recommend(catalog, Request(budget=1_100_000, uses=("gaming",), resolution="QHD"))
    assert result.plans and result.relaxed[-1] == "그래픽카드 기준 RTX 5060 Ti급 → RTX 4060급"
    assert result.min_specs.gpu_reference == "RTX 4060"


def test_specs_stay_when_the_budget_fits_them(catalog):
    result = recommend(catalog, Request(budget=1_500_000, uses=("gaming",), resolution="QHD"))
    assert result.plans and result.relaxed == ()
    assert result.min_specs.ram_gb == 32


def test_minimum_price_note_kept_when_even_lower_specs_do_not_fit(catalog):
    result = recommend(catalog, Request(budget=1_000_000, uses=("gaming",), resolution="QHD"))
    assert not result.plans and result.relaxed == ()
    assert any("최저 견적" in n for n in result.notes)


def test_case_cooler_search_reuses_height_checks_across_gpu_lengths(catalog, monkeypatch):
    """GPU variants must not rescan the same cooler fit for every case."""
    from dataclasses import replace
    from pcquote.engine.recommend import _Search
    from pcquote.engine import compatibility

    pools = {c: catalog.usable(c) for c in catalog.by_category}
    search = _Search(catalog, Request(budget=1_800_000), pools)
    cpu, board, gpu = pools['cpu'][0], pools['board'][0], pools['gpu'][0]
    calls = 0
    original = compatibility.passes
    def counted(parts, only_with=None):
        nonlocal calls
        if only_with == 'cooler' and 'case' in parts:
            calls += 1
        return original(parts, only_with)
    monkeypatch.setattr(compatibility, 'passes', counted)
    for length in range(100, 120):
        variant = replace(gpu, specs={**gpu.specs, 'length': length})
        assert search._case_cooler('popular', cpu, variant, board)
    assert calls <= len(pools['case']) * len(pools['cooler']), f'redundant cooler scans: {calls}'


def test_case_cooler_factoring_matches_exhaustive_selection(catalog):
    from dataclasses import replace
    from pcquote.engine.recommend import _Search
    from pcquote.engine import compatibility
    pools = {c: sorted(catalog.usable(c), key=lambda p: p.price) for c in catalog.by_category}
    search = _Search(catalog, Request(budget=1_800_000), pools)
    for mode in search.MODES:
        for cpu in pools['cpu']:
            for board in pools['board']:
                for length in (100, 280, 330, 500):
                    gpu = replace(pools['gpu'][0], specs={**pools['gpu'][0].specs, 'length': length})
                    options = []
                    for case in pools['case']:
                        if not compatibility.passes({'gpu': gpu, 'board': board, 'case': case}, 'case'):
                            continue
                        cooler = next((c for c in search._coolers(mode, cpu) if compatibility.passes(
                            {'cpu': cpu, 'case': case, 'cooler': c}, 'cooler')), None)
                        if cooler:
                            options.append((case, cooler))
                    expected = min(options, key=lambda pair: search._utility(mode, dict(zip(('case', 'cooler'), pair))), default=None)
                    assert search._case_cooler(mode, cpu, gpu, board) == expected
