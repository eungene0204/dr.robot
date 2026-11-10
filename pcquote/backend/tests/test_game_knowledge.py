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
    assert len(g.games()) == 8
    assert sum(n['kind'] == 'requirement' for n in g.nodes.values()) == 17
    assert sum(n['kind'] == 'measurement' for n in g.nodes.values()) == 4
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
