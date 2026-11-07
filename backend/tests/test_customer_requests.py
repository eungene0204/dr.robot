"""Customer phrasing found by the quote-eval scenarios (.claude/skills/quote-eval)."""

import pytest

from pcquote.catalog import Catalog
from pcquote.consult import customer_preferences, detect_profile, explicit_budget
from pcquote.engine.recommend import recommend
from pcquote.engine.requirements import Request
from pcquote.screen import to_request

from conftest import NOW, part, sample_parts


@pytest.mark.parametrize("text, budget", [
    ("백오십만원으로 게임용", 1_500_000), ("2백만원 QHD 게임", 2_000_000), ("1.5백만원 FHD", 1_500_000),
    ("이백오십만 원", 2_500_000), ("1천5백만원", 15_000_000), ("200만원대", 2_000_000), ("1,800,000원", 1_800_000),
    ("150만원, 모니터 이원화", 1_500_000),  # a bare Korean numeral before 원 is a word, not an amount
])
def test_budget_in_korean_numerals(text, budget):
    assert explicit_budget(text) == budget


@pytest.mark.parametrize("text, profile", [
    ("9800X3D로 350만원 4K 게이밍", "gaming"), ("7800x3d 게임용", "gaming"), ("블렌더 3D 렌더링", "editing"),
    ("캐드(CAD) 도면 작업", "editing"), ("AutoCAD 작업용", "editing"), ("스테이블 디퓨전 이미지 생성", "ai"),
])
def test_profile_ignores_x3d_model_names(text, profile):
    assert detect_profile(text) == profile


CATALOG_RECORDS = [{"category": "cpu", "name": "AMD 라이젠7 9800X3D", "benchmarkName": "AMD Ryzen 7 9800X3D"},
                   {"category": "gpu", "name": "RTX 5070 12GB", "benchmarkName": "NVIDIA GeForce RTX 5070"}]


def test_preferences_parsed_from_request_text():
    p = customer_preferences("9800X3D랑 RTX 5070, 램 64GB, SSD는 2TB 이상, VRAM 16GB", CATALOG_RECORDS)
    assert p["cpu_models"] == ("9800x3d",) and p["gpu_models"] == ("5070",)
    assert (p["min_ram_gb"], p["min_ssd_gb"], p["min_vram_gb"]) == (64, 2000, 16)
    assert customer_preferences("딥러닝용, VRAM 16GB 이상", [])["min_ram_gb"] == 0  # VRAM is not system memory
    assert customer_preferences("인텔 CPU, 라데온 그래픽카드", [])["cpu_brand"] == "intel"
    assert customer_preferences("인텔 CPU, 라데온 그래픽카드", [])["gpu_brand"] == "amd"
    assert customer_preferences("램 32GB\n추가 요청: 램 64GB로", [])["min_ram_gb"] == 64  # last mention wins


def test_to_request_carries_preferences():
    req = to_request({"profile": "gaming", "budget": 2_000_000, "text": "인텔 CPU로 200만원, 램 64GB"}, {}, {})
    assert req.cpu_brand == "intel" and req.min_ram_gb == 64


def with_parts(*extra):
    return Catalog(sample_parts() + list(extra), now=NOW)


def test_gpu_builds_never_use_an_unrated_psu():
    bulk = part("p-bulk", "psu", "600W 벌크", 10_000, capacity=900, connectors=["8pin", "12v2x6"])
    result = recommend(with_parts(bulk), Request(budget=2_000_000, uses=("gaming",), resolution="QHD"))
    assert result.plans and all(p.build.parts["psu"].id != "p-bulk" for p in result.plans)
    office = recommend(with_parts(bulk), Request(budget=900_000, uses=("office",)))
    assert any(p.build.parts["psu"].id == "p-bulk" for p in office.plans)  # office builds have no GPU load


def test_fhd_gaming_below_the_rtx4060_floor_falls_back_to_entry_gpus():
    entry = [part("g-5050", "gpu", "RTX 5050 8GB", 250_000, 60, "NVIDIA GeForce RTX 5050",
                  watts=130, length=230, vram=8, connector="8pin", minPsu=550),
             part("g-3050", "gpu", "RTX 3050 6GB", 180_000, 40, "NVIDIA GeForce RTX 3050",
                  watts=70, length=200, vram=6, connector="8pin", minPsu=300)]
    result = recommend(with_parts(*entry), Request(budget=900_000, uses=("gaming",), resolution="FHD"))
    assert result.plans and result.relaxed[-1] == "그래픽카드 기준 RTX 4060급 → RTX 5050급"
    assert all(p.build.total <= 900_000 for p in result.plans)


def test_low_budget_office_lowers_memory_and_ssd_below_the_normal_floor():
    small = [part("r-8", "ram", "DDR5-5600 8GB", 30_000, ddr=5, capacity=8, sticks=1),
             part("s-256", "ssd", "NVMe 256GB", 35_000, capacity=256, m2=1, interface="nvme")]
    result = recommend(with_parts(*small), Request(budget=620_000, uses=("office",)))
    assert result.plans and result.relaxed == ("메모리 16GB → 8GB", "SSD 500GB → 256GB")


def test_cpu_brand_and_model_preferences_are_hard_while_a_build_fits(catalog):
    intel = recommend(catalog, Request(budget=2_000_000, uses=("gaming",), resolution="QHD", cpu_brand="intel"))
    assert intel.plans and all(p.build.parts["cpu"].brand == "Intel" for p in intel.plans)
    x3d = recommend(catalog, Request(budget=3_500_000, uses=("gaming",), resolution="4K", cpu_models=("9800x3d",)))
    assert x3d.plans and all(p.build.parts["cpu"].id == "c-9800x3d" for p in x3d.plans)
    ram = recommend(catalog, Request(budget=2_500_000, uses=("gaming",), resolution="QHD", min_ram_gb=64))
    assert ram.plans and all(p.build.parts["ram"].spec("capacity") >= 64 for p in ram.plans)


def test_unservable_preference_is_dropped_with_a_note(catalog):
    result = recommend(catalog, Request(budget=2_000_000, uses=("gaming",), resolution="QHD", gpu_brand="amd"))
    assert result.plans and result.dropped == "요청하신 조건(라데온 그래픽카드)은 사용 가능한 제품이 없어 반영하지 못했어요"
    assert result.notes[0] == result.dropped
