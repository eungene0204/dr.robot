"""Customer phrasing found by the quote-eval scenarios (.claude/skills/quote-eval)."""

import pytest

from pcquote.catalog import Catalog
from pcquote.consult import budget_change, customer_preferences, detect_profile, explicit_budget, parse_requirement
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


@pytest.mark.parametrize("text, options", [
    # (white, wifi, os) — the last mention decides; a refusal in the same clause turns it off.
    ("화이트 말고 블랙으로 180만원", (False, False, False)),
    ("200만원 QHD 게임용 화이트\n추가 요청: 화이트 말고 블랙으로 해주세요", (False, False, False)),
    ("하얀색으로 맞춘 게임용", (True, False, False)), ("흰 케이스로 해주세요", (True, False, False)),
    ("블랙 감성, 무선 마우스는 따로 살게요", (False, False, False)),
    ("와이파이는 필요 없어요 유선 써요", (False, False, False)), ("와이파이 랜카드 포함", (False, True, False)),
    ("윈도우는 집에 있는 거 쓸게요", (False, False, False)), ("윈도우 정품 필요 없어요", (False, False, False)),
    ("150만원 윈도우 포함\n추가 요청: 윈도우는 빼주세요", (False, False, False)),
    ("윈도우도 넣어주세요", (False, False, True)),
    ("흰색 케이스, 무선랜, 윈도우 정품 포함 200만원", (True, True, True)),
])
def test_options_follow_refusals_and_synonyms(text, options):
    r = parse_requirement(text)
    assert (r["white"], r["wifi"], r["os"]) == options


@pytest.mark.parametrize("text, profile, resolution", [
    ("사무용인데 가끔 배그도 해요", "gaming", "QHD"), ("초등학생 줌 수업용 45만원", "office", "FHD"),
    ("엑셀 매크로 컨트롤", "office", "FHD"), ("UHD 모니터로 게임", "gaming", "4K"), ("2160p 게이밍", "gaming", "4K"),
])
def test_profile_and_resolution_phrasings(text, profile, resolution):
    r = parse_requirement(text)
    assert (r["profile"], r["resolution"]) == (profile, resolution)


def test_ssd_size_with_words_between():
    assert customer_preferences("저장공간 넉넉하게 2테라로, 게임용", [])["min_ssd_gb"] == 2000


@pytest.mark.parametrize("text, budget", [
    ("예산 이백 정도로 QHD 게임용", 2_000_000), ("삼백 내외", 3_000_000), ("budget 2,000,000 won", 2_000_000),
    ("천천히 생각해 볼게요", None), ("이원화", None),
])
def test_bare_korean_and_won_budgets(text, budget):
    assert explicit_budget(text) == budget


@pytest.mark.parametrize("text, change", [
    ("예산 10만원만 더 올려줘", 100_000), ("예산을 30만원 줄여주세요", -300_000), ("30만원 추가", 300_000),
    ("모니터 30만원 빼고 170만원", None), ("예산 250만원으로 올려주세요", None), ("예산을 200만원으로 줄여주세요", None),
])
def test_relative_budget_change(text, change):
    assert budget_change(text) == change


@pytest.mark.parametrize("text, resolution, os_, wifi", [
    ("윈도우 넣고 와이파이는 빼줘", "QHD", True, False), ("윈도우 없이 120만원", "QHD", False, False),
    ("운영체제 포함해서", "QHD", True, False), ("300만원 4K 게임용\n추가 요청: 4K 말고 QHD로 해주세요", "QHD", False, False),
    ("풀HD 모니터", "FHD", False, False), ("5K 모니터로 게임", "4K", False, False),
])
def test_refusal_stays_in_its_clause_and_resolution_synonyms(text, resolution, os_, wifi):
    r = parse_requirement(text)
    assert (r["resolution"], r["os"], r["wifi"]) == (resolution, os_, wifi)


@pytest.mark.parametrize("text, key, value", [
    ("엔비디아 말고 AMD 그래픽카드로", "gpu_brand", "amd"), ("AMD로 맞춰주세요", "cpu_brand", "amd"),
    ("인텔 말고 AMD CPU로", "cpu_brand", "amd"), ("64GB DDR5 램으로", "min_ram_gb", 64), ("램 DDR5 64GB", "min_ram_gb", 64),
])
def test_brand_refusals_and_memory_with_ddr(text, key, value):
    assert customer_preferences(text, [])[key] == value


@pytest.mark.parametrize("text, profile", [
    ("마야 애니메이션", "editing"), ("라이노 그래스호퍼 건축", "editing"), ("레빗 BIM", "editing"), ("클립스튜디오 웹툰", "editing"),
    ("SDXL 로라 학습", "ai"), ("ComfyUI 이미지 생성", "ai"), ("Ollama 70B", "ai"), ("Whisper 음성인식", "ai"),
])
def test_work_tool_names(text, profile):
    assert detect_profile(text) == profile


@pytest.mark.parametrize("text, budget", [
    ("배그컴 170", 1_700_000), ("편집컴 300 정도요", 3_000_000), ("예산 1500000", 1_500_000), ("1,500,000", 1_500_000),
    ("게임용 예산 150에서 200 사이", 2_000_000), ("2백오십 정도 QHD 게임", 2_500_000), ("예산 1억", 100_000_000),
    ("용도는 그대로고 예산만 200으로", 2_000_000), ("예산은 200", 2_000_000),
    # model numbers, resolutions and part sizes are not budgets
    ("RTX 5070으로 바꿔줘", None), ("1440으로 해주세요", None), ("i5 13400F로", None), ("윈도우 11 홈", None),
    ("퓨전360으로", None), ("램 32로", None), ("모니터 27로", None), ("파워 750으로", None), ("165Hz로", None),
])
def test_bare_number_budgets(text, budget):
    assert explicit_budget(text) == budget


@pytest.mark.parametrize("text, profile", [
    ("퓨전360 기계 설계", "editing"), ("카티아 자동차 설계", "editing"), ("RAG 서버", "ai"), ("텐서플로 케라스 공부", "ai"),
    ("YOLO 객체인식 학습", "ai"), ("강화학습 연구", "ai"), ("TTS 음성 합성 모델 학습", "ai"),
    ("매장 키오스크용 PC", "office"), ("CCTV 녹화용 PC", "office"), ("드래그 앤 드롭 사무", "office"),
])
def test_more_work_names(text, profile):
    assert detect_profile(text) == profile


@pytest.mark.parametrize("text, resolution, white", [
    ("모니터는 FHD인데 나중에 QHD로 바꿀 수도 있어요", "QHD", False),
    ("200만원 QHD 게임용 화이트\n추가 요청: 블랙으로 바꿔주세요", "QHD", False),
    ("화이트 앤 블랙 투톤", "QHD", True), ("화이트에 블랙 포인트로", "QHD", True),
])
def test_future_monitor_and_switch_to_black(text, resolution, white):
    r = parse_requirement(text)
    assert (r["resolution"], r["white"]) == (resolution, white)


def test_unknown_gpu_models_intel_arc_and_memory_phrasings():
    catalog = [{"category": "gpu", "name": "RTX 5080", "benchmarkName": "NVIDIA GeForce RTX 5080"}]
    assert customer_preferences("RTX 4090 들어간 800만원", catalog)["gpu_models"] == ("4090",)  # dropped later with a notice
    assert customer_preferences("4070 Ti SUPER로", catalog)["gpu_models"] == ("4070tisuper",)
    arc = customer_preferences("인텔 아크 그래픽카드로", [])
    assert (arc["gpu_brand"], arc["cpu_brand"]) == ("intel", None)
    assert customer_preferences("아크릴 케이스", [])["gpu_brand"] is None
    assert customer_preferences("램 2개 꽂아서 32GB로", [])["min_ram_gb"] == 32
    assert customer_preferences("비디오 메모리 16GB 이상", [])["min_vram_gb"] == 16


def test_missing_gpu_model_is_dropped_with_a_notice(catalog):
    result = recommend(catalog, Request(budget=3_000_000, uses=("gaming",), resolution="QHD", gpu_models=("4090",)))
    assert result.plans and "그래픽카드 4090" in result.dropped and "사용 가능한 제품이 없어" in result.dropped


@pytest.mark.parametrize("text, budget", [
    ("모니터 30만원 포함해서 총 200만원, 게임용 QHD", 1_700_000), ("모니터까지 30만원 포함 200만원", 1_700_000),
    ("키보드 마우스 10만원 합쳐서 150만원", 1_400_000), ("150만원 모니터는 따로 30만원", 1_500_000),
    ("모니터 30만원 빼고 170만원", 1_700_000),
])
def test_peripheral_amounts(text, budget):
    assert explicit_budget(text) == budget


@pytest.mark.parametrize("text, profile", [
    ("웹 개발 공부용 데스크탑", "office"), ("앱 개발용", "office"), ("코딩 학원 수업용", "office"), ("주식 HTS 모니터 4대", "office"),
    ("게임 개발 언리얼", "ai"), ("AI 개발용", "ai"), ("로컬 AI 코딩 어시스턴트", "ai"),
])
def test_web_development_and_coding_need_no_gpu(text, profile):
    assert detect_profile(text) == profile


def test_size_right_after_a_gpu_model_is_vram():
    assert customer_preferences("RTX 5060 16GB로 160만원", [])["min_vram_gb"] == 16
    assert customer_preferences("3060 12GB로", [])["min_vram_gb"] == 12
    p = customer_preferences("RTX 5070 Ti, 램 32GB", [])
    assert (p["min_vram_gb"], p["min_ram_gb"]) == (0, 32)


def test_accounting_program_is_office():
    req = parse_requirement('회계 프로그램용 컴퓨터를 새로 사려는데 85만원 안에서 본체 추천해주세요.')
    assert (req['profile'], req['resolution']) == ('office', 'FHD')


def test_unlimited_budget_reaches_engine_and_can_be_evaluated(catalog):
    from pcquote.engine.recommend import evaluate
    from pcquote.screen import budget_cap
    req = to_request({'profile': 'gaming', 'budget': None, 'resolution': 'QHD',
                      'text': 'QHD 게임용 PC 예산 제한 없음'}, {'assembly': 40000}, {})
    assert req.budget is None
    result = recommend(catalog, req)
    assert result.plans and result.request.budget is None
    assert budget_cap({'budget': None}) is None
    plan = result.plans[0]
    checked = evaluate(catalog, req, {c: p.id if p else None for c, p in plan.build.parts.items()})
    assert checked['ok'] and checked['withinBand'] and checked['budgetDelta'] is None


def test_unlimited_budget_is_not_a_hidden_twenty_million_cap():
    expensive_gpu = part('g-expensive', 'gpu', 'RTX 5090 32GB premium', 25_000_000, 500,
                         'NVIDIA GeForce RTX 5090', watts=575, length=360, vram=32,
                         connector='12v2x6', minPsu=1000)
    result = recommend(with_parts(expensive_gpu), Request(budget=None, uses=('gaming',), resolution='4K', memo='예산 제한 없이 최고 성능'))
    assert result.plans and any(p.build.total > 20_000_000 for p in result.plans)
    assert all(c.status != 'fail' for p in result.plans for c in p.build.checks)
    assert not result.relaxed


@pytest.mark.parametrize('text', [
    '발로란트 게임 연습용이고 FHD 모니터 있습니다. 155만원짜리 본체 찾습니다.',
    '게임용 FHD 모니터 있어요',
    '게임용 FHD 모니터 집에 있습니다',
    '게임용 FHD 모니터는 따로 있어요',
    '4K 말고 FHD 모니터 있습니다',
])
def test_monitor_ownership_keeps_the_requested_resolution(text):
    assert parse_requirement(text)['resolution'] == 'FHD'


def test_resolution_refusals_and_owned_options_are_independent():
    r = parse_requirement('FHD 말고 4K로 게임, 윈도우는 집에 있습니다')
    assert r['resolution'] == '4K' and not r['os']


@pytest.mark.parametrize('text,budget', [
    ('QHD 게임용 총 290만원에 모니터 40만원 포함해서 견적 부탁합니다.', 2500000),
    ('모니터 40만원 포함 총 290만원 QHD 게임용', 2500000),
    ('총 290만원, 키보드 마우스 10만원 합쳐서 게임용', 2800000),
    ('총 300만원, 모니터 40만원 포함, 키보드 10만원 포함', 2500000),
    ('모니터 40만원 포함, 총 300만원, 키보드 10만원 포함', 2500000),
    ('총 290만원, 모니터는 따로 40만원', 2900000),
    ('본체 250만원, 모니터는 별도 40만원', 2500000),
    ('모니터 40만원 빼고 본체 250만원', 2500000),
])
def test_peripheral_inclusions_do_not_depend_on_amount_order(text, budget):
    assert explicit_budget(text) == budget


def test_unspecified_overwatch_quote_does_not_recommend_a_flagship(catalog):
    req = Request(budget=None, uses=('gaming',), resolution='QHD', memo='오버워치용 견적')
    result = recommend(catalog, req)
    assert result.plans
    selected = [(p.type.key, p.build.parts['gpu'].name, p.build.total) for p in result.plans]
    assert all(p.build.parts['gpu'].id != 'g-5090' for p in result.plans), selected


@pytest.mark.parametrize('memo', ['오버워치용 견적', '게임용 견적', '롤 FHD 게임용', '게임 예산 제한 없음', '최고 성능은 필요 없고 적당한 게임용'])
def test_default_no_budget_keeps_a_suitable_gpu_even_if_flagship_is_popular(memo):
    from dataclasses import replace
    parts = [replace(p, popularity_rank=1, popularity_observed_at=NOW) if p.id == 'g-5090' else p for p in sample_parts()]
    result = recommend(Catalog(parts, now=NOW), Request(budget=None, uses=('gaming',), resolution='QHD', memo=memo))
    assert len(result.plans) == 3
    assert all(p.build.parts['gpu'].id in {'g-5060ti','g-5070'} for p in result.plans)
    assert result.request.budget is None
    assert all(c.status != 'fail' for p in result.plans for c in p.build.checks)


@pytest.mark.parametrize('kwargs', [
    {'memo':'예산 제한 없이 최고 성능'},
    {'gpu_models':('5090',), 'memo':'오버워치용 5090 지정'},
    {'uses':('ai',),'min_vram_gb':32,'memo':'로컬 AI VRAM 32GB 이상'},
])
def test_real_high_end_requests_are_not_blocked_by_default_adequacy(catalog, kwargs):
    fields = {'budget':None,'uses':('gaming',),'resolution':'QHD',**kwargs}
    result = recommend(catalog, Request(**fields))
    assert result.plans
    assert any(p.build.parts['gpu'].id=='g-5090' for p in result.plans)
    assert all(c.status!='fail' for p in result.plans for c in p.build.checks)


@pytest.mark.parametrize('text',['오버워치용 견적','Overwatch 2 게임 PC'])
def test_overwatch_name_is_a_known_game_without_guessing(text):
    assert detect_profile(text)=='gaming'


def test_price_refresh_failure_does_not_promote_a_flagship(catalog):
    req = Request(budget=None, uses=('gaming',), resolution='QHD', memo='오버워치용 견적',
                  exclude_parts=('g-4060','g-5060ti','g-5070','g-5070ti'))
    result = recommend(catalog, req)
    assert not result.plans, '적정 후보의 가격 확인이 실패하면 5090으로 자동 승급하면 안 된다'
