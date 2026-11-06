from pcquote.engine.recommend import Scorer, alternatives, evaluate, recommend
from pcquote.engine.requirements import BUDGET_BAND, Request


def _ids(plan):
    return {c: (p.id if p else None) for c, p in plan.build.parts.items()}


def test_three_distinct_plans_inside_budget_band(catalog):
    req = Request(budget=1_800_000, uses=("gaming",))
    result = recommend(catalog, req)
    assert [p.type.key for p in result.plans] == ["balanced", "performance", "value"]
    assert len({p.build.key for p in result.plans}) == 3
    for plan in result.plans:
        assert abs(plan.build.total - req.budget) <= req.budget * BUDGET_BAND
        assert all(c.status != "fail" for c in plan.build.checks)


def test_each_plan_is_best_by_its_own_score_among_builds_that_keep_the_order(catalog):
    result = recommend(catalog, Request(budget=1_800_000))
    scorer = Scorer.over(result.builds)
    plans = {p.type.key: p for p in result.plans}
    base = plans["balanced"].build
    if "performance" in plans:
        strong = plans["performance"]
        allowed = [b for b in result.builds if b.performance > base.performance and b.total >= base.total]
        assert scorer.score(strong.build, strong.type) == max(scorer.score(b, strong.type) for b in allowed)
    if "value" in plans:
        cheap = plans["value"]
        cap = plans["performance"].build.performance if "performance" in plans else float("inf")
        allowed = [b for b in result.builds if b.total < base.total and b.performance <= cap]
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
    assert all(p.build.total >= 2_200_000 * 0.7 for p in result.plans)
    assert result.notes
