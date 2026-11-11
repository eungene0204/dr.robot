from copy import deepcopy
from datetime import date

import pytest

from pcquote.knowledge import GameGraph, graph
from pcquote.engine.recommend import recommend
from pcquote.engine.requirements import Request, min_specs
from pcquote import llm

TODAY = date(2026, 11, 11)


def test_graph_has_source_backed_official_profiles_and_measurements():
    g = graph()
    assert len(g.games()) == 28
    assert sum(n['kind'] == 'requirement' for n in g.nodes.values()) == 57
    assert sum(n['kind'] == 'measurement' for n in g.nodes.values()) == 20
    assert all(g.related(n, 'SUPPORTED_BY') for n in g.nodes.values() if n['kind'] in ('requirement','measurement'))


@pytest.mark.parametrize('text', ['오버워치용 견적','오버 워치 2용','OW2 PC','Overwatch 2','롤용','CS2용','사펑 본체'])
def test_known_aliases(text):
    assert len(graph().match(text)) == 1


@pytest.mark.parametrize('text', ['스크롤 작업용', '컨트롤 프로그램', '롤러코스터 개발', 'unknown title', 'apexify'])
def test_aliases_do_not_match_embedded_words(text):
    assert not graph().match(text)


def test_overwatch_candidates_are_derived_from_measurement_edges():
    r = graph().resolve('오버워치용', today=TODAY)
    assert r['gpuModels'] == ['4060', '5060'] and r['restrictGpu']
    assert not r['fpsGuaranteed']
    assert r['games'][0]['measurements'][0]['platform']['cpu'] == 'AMD Ryzen 7 9800X3D'
    assert r['games'][0]['measurements'][0]['context']['frame_generation'] is None
    assert graph().resolve('오버워치 200fps', today=TODAY)['gpuModels'] == ['5060']


@pytest.mark.parametrize('text,res', [
    ('오버워치 240fps','FHD'),('오버워치','QHD'),('오버워치','4K'),
    ('오버워치 낮음 144fps','FHD'),('오버워치 네이티브','FHD'),('오버워치 144프레임 방어','FHD'),
    ('사펑 RT 켜고','FHD'),('오버워치 높음','FHD'),('오버워치 DLSS','FHD'),
])
def test_scope_gaps_never_reuse_incompatible_fps(text,res):
    r = graph().resolve(text,res,today=TODAY)
    assert not r['restrictGpu'] and not r['fpsGuaranteed']
    assert r['games'][0]['status'] == 'coverage_gap'


def test_multi_game_requires_shared_measured_candidates():
    assert graph().resolve('오버워치와 사펑 90fps',today=TODAY)['gpuModels'] == ['5060']
    assert not graph().resolve('오버워치와 배그',today=TODAY)['restrictGpu']


def test_official_requirements_are_not_benchmarks():
    r=graph().resolve('발로란트',today=TODAY)
    assert r['games'][0]['officialProfiles']
    assert not r['games'][0]['measurements'] and not r['restrictGpu']
    assert r['targetFps'] is None


def test_expired_or_unreviewed_evidence_is_not_used():
    assert not graph().resolve('오버워치',today=date(2027,2,12))['restrictGpu']
    d=deepcopy(graph().data)
    for n in d['nodes']:
        if n['kind']=='source': n['reviewed']=False
    r=GameGraph(d).resolve('오버워치',today=TODAY)
    assert not r['restrictGpu'] and r['ramGb']==0


def test_validator_rejects_missing_provenance_and_bad_edges():
    d=deepcopy(graph().data)
    d['edges']=[e for e in d['edges'] if e['relation']!='SUPPORTED_BY']
    with pytest.raises(ValueError,match='without source'):GameGraph(d)
    d=deepcopy(graph().data);d['edges'][0]['to']='game:overwatch'
    with pytest.raises(ValueError,match='relation types'):GameGraph(d)


def test_real_recommendation_uses_graph_not_generic_gpu_ranking(catalog):
    req=Request(budget=3_000_000,memo='오버워치용 견적',resolution='FHD')
    result=recommend(catalog,req)
    assert result.plans
    assert result.min_specs.game_gpu_models == ('4060','5060')
    assert all(p.build.parts['gpu'].id=='g-4060' and p.build.total<=req.budget for p in result.plans)
    assert result.as_dict(catalog)['gameEvidence']['selectionApplied']
    assert all(c.status!='fail' for p in result.plans for c in p.build.checks)


def test_unavailable_measured_gpu_does_not_promote_flagship(catalog):
    result=recommend(catalog,Request(budget=None,memo='오버워치 200fps',resolution='FHD'))
    assert not result.plans  # fixture has 4060 and 5090, but no measured 5060.


def test_explicit_gpu_and_maximum_request_remain_customer_choices(catalog):
    for req in [Request(budget=None,memo='오버워치 RTX 5090',gpu_models=('5090',)),
                Request(budget=None,memo='오버워치 최고 성능')]:
        r=recommend(catalog,req)
        assert r.plans and not r.min_specs.game_gpu_models
        assert not r.as_dict(catalog)['gameEvidence']['selectionApplied']


@pytest.mark.parametrize('text', ['발로란트용 견적','오버워치용 견적','CS2용 PC','사펑 본체'])
def test_known_games_skip_the_model_even_without_budget(text):
    def forbidden(**kwargs):raise AssertionError('No model call for known game')
    r=llm.interpret(text,forbidden)
    assert r['profile']=='gaming' and r['method']=='local' and not r.get('needsPurpose')


def test_hardware_alternatives_preserve_vram_variants():
    g=graph()
    pubg=g.nodes['game:pubg:recommended']
    cyberpunk=g.nodes['game:cyberpunk_2077:minimum']
    p=next(h for h in g.related(pubg,'REQUIRES_GPU') if '1060' in h['label'])
    c=next(h for h in g.related(cyberpunk,'REQUIRES_GPU') if '1060' in h['label'])
    assert p['vram_gb']==3 and c['vram_gb']==6 and p['id']!=c['id']
    assert all(e['operator']=='any' for e in g.data['edges'] if e['relation'].startswith('REQUIRES_'))


def test_explicit_vram_and_gpu_brand_are_not_dropped_by_measurement_coverage(catalog):
    req=Request(budget=None,memo='오버워치 VRAM 16GB 이상',min_vram_gb=16)
    result=recommend(catalog,req)
    assert result.plans and result.dropped is None
    assert all(p.build.parts['gpu'].spec('vram')>=16 for p in result.plans)
    assert not result.min_specs.game_gpu_models
    amd=min_specs(Request(budget=None,memo='오버워치 라데온',gpu_brand='amd'),catalog)
    assert not amd.game_gpu_models


EXPANSION_IDS = (
    'dota_2', 'rust', 'gta_v_enhanced', 'red_dead_redemption_2', 'elden_ring',
    'baldurs_gate_3', 'black_myth_wukong', 'monster_hunter_wilds', 'helldivers_2', 'palworld',
    'destiny_2', 'warframe', 'rainbow_six_siege_x', 'dead_by_daylight', 'path_of_exile_2',
    'diablo_iv', 'genshin_impact', 'minecraft_java', 'lost_ark', 'maplestory',
)


@pytest.mark.parametrize('identifier', EXPANSION_IDS)
def test_added_game_is_source_backed_locally_interpreted_and_recommendable(identifier,catalog):
    game=graph().nodes['game:'+identifier]
    def forbidden(**kwargs):raise AssertionError('Known game must not call the model')
    reading=llm.interpret(game['name']+' PC 견적',forbidden)
    assert reading['profile']=='gaming' and reading['method']=='local'
    r=graph().resolve(game['name'],'FHD',today=TODAY)
    assert len(r['games'])==1 and r['games'][0]['officialProfiles'] and r['games'][0]['sources']
    result=recommend(catalog,Request(budget=2_000_000,memo=game['name']+' PC 견적',resolution='FHD'))
    assert result.plans
    assert all(p.build.total<=2_000_000 for p in result.plans)
    assert all(c.status!='fail' for p in result.plans for c in p.build.checks)


def test_official_resolution_profiles_and_special_contexts_are_preserved(catalog):
    r=graph().resolve('로아','4K',today=TODAY)
    assert r['games'][0]['officialProfileApplied']=='game:lost_ark:recommended_uhd'
    assert r['ramGb']==32
    assert graph().resolve('로아','FHD',today=TODAY)['games'][0]['officialProfileApplied']=='game:lost_ark:recommended'
    assert min_specs(Request(budget=None,memo='팰월드'),catalog).ram_gb==32
    wilds=graph().nodes['game:monster_hunter_wilds:recommended']
    assert wilds['target_fps']==60 and wilds['frame_generation'] is True
    assert not graph().resolve('몬헌 와일즈 60fps',today=TODAY)['restrictGpu']
    assert graph().resolve('헬다이버즈2',today=TODAY)['storageGb']==135
    # Korean source refresh rate is not transformed into an FPS claim.
    assert all(p['target_fps'] is None for p in r['games'][0]['officialProfiles'])


@pytest.mark.parametrize('text',['마인크래프트 베드락','Minecraft Bedrock','GTA V Legacy','GTA5 레거시','메이플스토리 월드'])
def test_other_editions_do_not_use_default_edition_facts(text):
    assert not graph().match(text)


def test_unknown_upscaled_and_reduced_quality_records_are_visible_but_not_selected():
    for text in ['발더스3','팔월드','디아4','오공','몬헌 와일즈']:
        r=graph().resolve(text,today=TODAY)
        assert r['games'][0]['measurements']
        assert not r['games'][0]['applicableMeasurementIds'] and not r['restrictGpu']
    fhd=graph().resolve('헬다이버즈2','FHD',today=TODAY)
    qhd=graph().resolve('헬다이버즈2','QHD',today=TODAY)
    assert fhd['gpuModels']==['4060','4060ti'] and qhd['gpuModels']==['4060ti']
    assert all(m['context']['resolution']==[2560,1440] for m in qhd['games'][0]['measurements']
               if m['id'] in qhd['games'][0]['applicableMeasurementIds'])
    assert not fhd['fpsGuaranteed'] and not qhd['fpsGuaranteed']


@pytest.mark.parametrize('field,value',[
    ('resolution',[2560,1440]),('upscaling',True),('upscaling',None),('frame_generation',True),
    ('ray_tracing',True),('path_tracing',True),('selection_eligible',False),('quality_degraded',True),
])
def test_measurement_context_is_checked_before_gpu_candidates(field,value):
    data=deepcopy(graph().data)
    for node in data['nodes']:
        if node['kind']=='measurement':node['context'][field]=value
    assert not GameGraph(data).resolve('오버워치','FHD',today=TODAY)['restrictGpu']


def test_every_canonical_title_is_locally_read_as_gaming_without_substring_collisions():
    def forbidden(**kwargs):raise AssertionError('Known title should not call model')
    for game in graph().games():
        reading=llm.interpret(game['name']+' PC 견적',forbidden)
        assert reading['profile']=='gaming',game['name']


def test_candidate_filter_uses_measured_vram_variant_instead_of_fixed_8gb(catalog,monkeypatch):
    data=deepcopy(graph().data)
    original=next(n for n in data['nodes'] if n['kind']=='measurement' and n['context']['game']=='overwatch-2')
    measurement={**deepcopy(original),'id':'fixture-measurement','vram_gb':16}
    gpu={'id':'fixture-gpu','kind':'hardware','category':'gpu','label':'RTX 5060 Ti 16GB',
         'model':'5060ti','vram_gb':16,'brand':'nvidia'}
    data['nodes'].extend([measurement,gpu])
    data['edges'].extend([
        {'from':'game:overwatch','relation':'HAS_MEASUREMENT','to':measurement['id']},
        {'from':measurement['id'],'relation':'TESTED_GPU','to':gpu['id']},
        *[{**edge,'from':measurement['id']} for edge in data['edges']
          if edge['from']==original['id'] and edge['relation'] in ('TESTED_CPU','SUPPORTED_BY')],
    ])
    fixture=GameGraph(data)
    monkeypatch.setattr('pcquote.engine.requirements.graph',lambda:fixture)
    result=recommend(catalog,Request(budget=None,memo='오버워치 VRAM 16GB',min_vram_gb=16))
    assert result.plans and result.dropped is None
    assert result.min_specs.game_gpu_variants==( ('5060ti',16), )
    assert all(p.build.parts['gpu'].id=='g-5060ti' for p in result.plans)


def test_measurement_hardware_vram_mismatch_is_rejected():
    data=deepcopy(graph().data)
    next(n for n in data['nodes'] if n['kind']=='measurement')['vram_gb']=64
    with pytest.raises(ValueError,match='VRAM'):GameGraph(data)
