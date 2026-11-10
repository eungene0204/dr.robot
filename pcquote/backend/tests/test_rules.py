import pytest

from conftest import part
from pcquote.engine import compatibility as compat
from pcquote.engine.chipset import board_chipset, chipset_support, cpu_generation
from pcquote.engine.requirements import Request, allocation, allocation_shares, min_specs, perf_weights


@pytest.mark.parametrize("name,expected", [
    ("MSI PRO B650M-A WIFI", "B650"),
    ("ASRock B760M Pro RS D5 에즈윈", "B760"),
    ("GIGABYTE H610M K D4 제이씨현", "H610"),
    ("MSI MAG Z890 토마호크 WIFI", "Z890"),
    ("ASUS ROG STRIX X870E-E GAMING WIFI", "X870"),
    ("이름에 칩셋 없음", None),
])
def test_board_chipset(name, expected):
    assert board_chipset(part("b", "board", name, 1)) == expected


@pytest.mark.parametrize("name,bench_name,expected", [
    ("인텔 코어i5-14세대 14400F (랩터레이크 리프레시)", None, "intel-14"),
    ("인텔 코어i7-12세대 12700K (엘더레이크)", None, "intel-12"),
    ("인텔 코어 울트라7 시리즈2 270K Plus (애로우레이크 리프레시)", None, "intel-ultra-200-plus"),
    ("인텔 코어 울트라5 시리즈2 245KF (애로우레이크)", None, "intel-ultra-200"),
    ("AMD 라이젠7-6세대 9800X3D (그래니트 릿지)", None, "amd-9000"),
    ("AMD 라이젠5-5세대 8600G (피닉스)", None, "amd-8000"),
    ("AMD 라이젠5-4세대 5600 (버미어)", None, "amd-5000"),
    ("AMD 라이젠5-2세대 3400G (피카소) (멀티팩 정품)", None, "amd-zen+"),
    ("AMD 라이젠3-2세대 3200G (피카소)", "AMD Ryzen 3 3200G", "amd-zen+"),
    ("AMD 라이젠5-3세대 3600 (마티스)", None, "amd-3000"),
    ("이름 불명 CPU", "AMD Ryzen 5 7500F", "amd-7000"),
    ("인텔 제온 E5-1607", None, None),
])
def test_cpu_generation(name, bench_name, expected):
    cpu = part("c", "cpu", name, 1, bench_name=bench_name or "")
    assert cpu_generation(cpu) == expected


@pytest.mark.parametrize("cpu_name,board_name,socket,status", [
    ("인텔 코어i5-13세대 13400", "GIGABYTE B760M DS3H", "LGA1700", "ok"),
    ("인텔 코어i5-14세대 14400F", "GIGABYTE B760M DS3H", "LGA1700", "warn"),
    ("인텔 코어i5-14세대 14400F", "ASUS PRIME H610M-K D4", "LGA1700", "warn"),
    ("인텔 코어i5-12세대 12400F", "ASUS PRIME H610M-K D4", "LGA1700", "ok"),
    ("인텔 코어 울트라5 시리즈2 245KF", "GIGABYTE B860M DS3H", "LGA1851", "ok"),
    ("인텔 코어 울트라5 시리즈2 250K Plus", "GIGABYTE B860M DS3H", "LGA1851", "warn"),
    ("AMD 라이젠7-6세대 9800X3D", "MSI PRO B650M-A WIFI", "AM5", "warn"),
    ("AMD 라이젠7-6세대 9800X3D", "ASRock B850M Pro RS", "AM5", "ok"),
    ("AMD 라이젠5-5세대 7500F", "MSI PRO B650M-A WIFI", "AM5", "ok"),
    ("AMD 라이젠5-4세대 5600", "ASRock A320M-HDV", "AM4", "fail"),
    ("AMD 라이젠5-2세대 3400G (피카소)", "ASRock A520M-HVS", "AM4", "fail"),
    ("AMD 라이젠5-3세대 3600 (마티스)", "ASRock A520M-HVS", "AM4", "ok"),
    ("인텔 코어i5-10세대 10400", "ASUS PRIME H510M-E", "LGA1200", "fail"),
])
def test_chipset_support(cpu_name, board_name, socket, status):
    cpu = part("c", "cpu", cpu_name, 1)
    board = part("b", "board", board_name, 1, socket=socket)
    assert chipset_support(cpu, board)[0] == status


def test_psu_rule_uses_max_cpu_power_with_30_percent_headroom(catalog):
    cpu, gpu = catalog.by_id["c-14400f"], catalog.by_id["g-5060ti"]
    assert compat.required_psu_watts(cpu, gpu) == int((148 + 180) * 1.3 + 0.999)  # 427W
    weak = part("p", "psu", "400W", 1, capacity=400, connectors=["8pin"])
    checks = {c.label: c for c in compat.check({"cpu": cpu, "gpu": gpu, "psu": weak})}
    assert checks["파워 용량"].status == "fail"


def test_gpu_minimum_psu_also_applies(catalog):
    cpu, gpu = catalog.by_id["c-7500f"], catalog.by_id["g-5070ti"]
    psu = part("p", "psu", "700W", 1, capacity=700, connectors=["8pin", "12v2x6"])
    # (88+300)*1.3 = 505W, but the card's 750W minimum governs.
    assert not compat.passes({"cpu": cpu, "gpu": gpu, "psu": psu})


def test_unknown_gpu_power_connector_fails(catalog):
    gpu = part("g", "gpu", "connector unknown", 1, watts=200, length=250, vram=8)
    checks = compat.check({"gpu": gpu, "psu": catalog.by_id["p-850"]})
    assert checks[0].status == "fail"


def test_liquid_cooler_is_not_auto_recommended(catalog):
    parts = {"cooler": catalog.by_id["f-aio"], "case": catalog.by_id["k-black"]}
    assert not compat.passes(parts)


def test_integrated_graphics_required_without_gpu(catalog):
    assert not compat.passes({"cpu": catalog.by_id["c-7500f"], "gpu": None})
    assert compat.passes({"cpu": catalog.by_id["c-9600x"], "gpu": None})


def test_gaming_allocation_matches_plan_ratios():
    req = Request(budget=1_500_000, uses=("gaming",))
    shares = allocation_shares(req)
    assert shares["gpu"] == pytest.approx(0.42, abs=0.001)
    assert shares["cpu"] == pytest.approx(0.18, abs=0.001)
    assert shares["psu"] + shares["case"] + shares["cooler"] == pytest.approx(0.16, abs=0.001)
    assert sum(allocation(req).values()) <= req.budget


def test_multi_use_averages_ratios_and_weights():
    req = Request(budget=1_500_000, uses=("gaming", "editing"))
    assert allocation_shares(req)["gpu"] == pytest.approx((0.42 + 0.30) / 2, abs=0.001)
    assert perf_weights(req) == pytest.approx((0.375, 0.625))


def test_office_has_no_gpu_budget():
    req = Request(budget=700_000, uses=("office",))
    assert allocation(req)["gpu"] == 0
    assert not req.needs_gpu


def test_assembly_fee_is_taken_out_of_parts_budget():
    req = Request(budget=1_500_000, assembly_fee=50_000)
    assert sum(allocation(req).values()) <= 1_450_000


def test_min_specs_by_resolution(catalog):
    fhd = min_specs(Request(budget=1_500_000, resolution="FHD"), catalog)
    qhd = min_specs(Request(budget=1_500_000, resolution="QHD"), catalog)
    assert fhd.gpu_reference == "RTX 4060" and fhd.gpu_benchmark == 74
    assert qhd.gpu_reference == "RTX 5060 Ti" and qhd.ram_gb == 32


def test_request_validation():
    with pytest.raises(ValueError):
        Request(budget=100_000)
    with pytest.raises(ValueError):
        Request(budget=1_000_000, uses=("mining",))


@pytest.mark.parametrize("board_name,cpu_watts,status", [
    ("ASUS PRIME H610M-K D4", 148, "ok"),     # i5-14400F class
    ("ASUS PRIME H610M-K D4", 253, "fail"),   # i7-13700KF on an entry board
    ("ASRock A620M-HDV/M.2", 162, "fail"),
    ("GIGABYTE B760M DS3H", 253, "ok"),
])
def test_entry_chipset_power_limit(board_name, cpu_watts, status):
    cpu = part("c", "cpu", "cpu", 1, socket="LGA1700", watts=cpu_watts, tdp=65)
    board = part("b", "board", board_name, 1, socket="LGA1700")
    checks = {c.label: c for c in compat.check({"cpu": cpu, "board": board})}
    assert checks["전원부 등급"].status == status


def test_only_nvme_ssd_is_usable():
    # Store policy (2026-11-06, carried over from buildmate): SATA or unconfirmed interfaces are not recommended.
    from conftest import part
    assert part("s-n", "ssd", "NVMe", 1, capacity=500, m2=1, interface="nvme").usable
    assert not part("s-s", "ssd", "SATA", 1, capacity=500, m2=1, interface="sata").usable
    assert not part("s-u", "ssd", "미확인", 1, capacity=500, m2=1).usable


def test_seed_classifies_ssd_interface():
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location("seed", pathlib.Path(__file__).parents[1] / "scripts/seed_from_buildmate.py")
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)
    assert seed.ssd_interface({"name": "삼성 990 PRO M.2 NVMe (1TB)", "capacity": 1000}) == "nvme"
    assert seed.ssd_interface({"name": "타무즈 GKM330 M.2 SATA (512GB)", "capacity": 512}) == "sata"
    assert seed.ssd_interface({"name": "WD Blue M.2 (1TB)", "capacity": 1000}) is None
    assert seed.ssd_interface({"name": "NVMe 외장 인클로저 USB", "capacity": 0}) is None
    assert seed.ssd_interface({"name": "인텔 Optane Memory NVMe 16GB", "capacity": 16}) is None
    assert seed.ssd_interface({"name": "인텔 D7 U.2 NVMe", "capacity": 3840}) is None
