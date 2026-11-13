from datetime import date

import httpx
import pytest

from pcquote.game_search import SteamGames, game_query, game_answer


def test_known_game_short_korean_name_needs_no_network():
    def forbidden(request):
        raise AssertionError('Known games must stay local')
    lookup = SteamGames(client=httpx.Client(transport=httpx.MockTransport(forbidden)))
    result = lookup.lookup('사이버 펑크 견적은?')
    assert result['status'] == 'found' and result['method'] == 'local'
    assert result['evidence']['games'][0]['name'] == 'Cyberpunk 2077'
    answer = game_answer(result)
    assert answer['references'] and answer['sources'] == ['game']
    assert '제품 모델명' not in answer['text']


@pytest.mark.parametrize('text,expected', [
    ('Hades II 견적은?', 'Hades II'), ('하데스 2 게임용 PC 견적 짜줘', '하데스 2'),
    ('Hades II 게임 권장 사양은?', 'Hades II'), ('Hades II 돌아가?', 'Hades II'),
    ('Hades II QHD 200만원 견적', 'Hades II'),
    ('Hades II 견적\n추가 요청: 예산 50만원 더', 'Hades II'),
    ('조용한 사무용 PC', None), ('RTX 5060 Ti 견적은?', None), ('게임 200만원 견적', None),
    ('150만원 견적은?', None), ('이 견적으로 배그 되나?', None),
])
def test_extract_only_title_not_customer_context(text, expected):
    assert game_query(text) == expected


def steam_mock(request):
    if request.url.path == '/api/storesearch/':
        return httpx.Response(200, json={'items': [{'id': 1145350, 'name': 'Hades II'}]})
    return httpx.Response(200, json={'1145350': {'success': True, 'data': {
        'name': 'Hades II', 'type': 'game', 'platforms': {'windows': True},
        'publishers': ['Supergiant Games'], 'pc_requirements': {
            'minimum': '<ul><li><strong>Processor:</strong> Dual Core</li><li><strong>Memory:</strong> 8 GB RAM</li><li><strong>Storage:</strong> 10 GB available space</li></ul>',
            'recommended': '<ul><li><strong>Processor:</strong> Quad Core</li><li><strong>Memory:</strong> 32 GB RAM</li><li><strong>Storage:</strong> 20 GB available space</li></ul>'}}}})


def test_online_exact_game_has_official_requirements_and_expiring_cache():
    requests = []
    def handler(request):
        requests.append(request)
        return steam_mock(request)
    clock = [100.0]
    lookup = SteamGames(client=httpx.Client(transport=httpx.MockTransport(handler)), clock=lambda: clock[0])
    result = lookup.lookup('Hades II QHD 200만원 견적은?')
    assert result['status'] == 'found' and result['method'] == 'steam'
    evidence = result['evidence']
    assert evidence['ramGb'] == 32 and evidence['storageGb'] == 20
    assert not evidence['restrictGpu'] and not evidence['fpsGuaranteed']
    assert evidence['games'][0]['sources'][0]['url'] == 'https://store.steampowered.com/app/1145350/'
    assert len(evidence['games'][0]['officialProfiles']) == 2
    assert '200' not in str(requests[0].url) and requests[0].url.params['term'] == 'Hades II'
    assert lookup.lookup('Hades II 견적은?')['status'] == 'found'
    assert len(requests) == 2
    result['evidence']['ramGb'] = 999
    assert lookup.lookup('Hades II 견적')['evidence']['ramGb'] == 32
    clock[0] += 3601
    lookup.lookup('Hades II 견적')
    assert len(requests) == 4


@pytest.mark.parametrize('failure', ['ambiguous', 'not_found', 'timeout', 'no_requirements', 'dlc', 'invalid'])
def test_unconfirmed_search_is_not_a_catalog_error_or_fabricated_specs(failure):
    def handler(request):
        if failure == 'timeout':
            raise httpx.ReadTimeout('timeout')
        if failure == 'invalid':
            return httpx.Response(200, text='not json')
        if request.url.path == '/api/storesearch/':
            items = [] if failure == 'not_found' else [{'id': 1, 'name': 'Hades II'}, {'id': 2, 'name': 'Hades II'}] if failure == 'ambiguous' else [{'id': 1145350, 'name': 'Hades II'}]
            return httpx.Response(200, json={'items': items})
        data = steam_mock(request).json()
        data['1145350']['data']['pc_requirements'] = {}
        if failure == 'dlc':
            data['1145350']['data']['type'] = 'dlc'
        return httpx.Response(200, json=data)
    result = SteamGames(client=httpx.Client(transport=httpx.MockTransport(handler))).lookup('Hades II 견적')
    assert result['status'] != 'found'
    assert not result.get('evidence')
    assert '제품 모델명' not in game_answer(result)['text']


def test_official_capacity_floors_survive_customer_preference_fallback_and_budget_relaxation(catalog):
    from pcquote.engine.requirements import Request, min_specs, relaxed_specs
    lookup = SteamGames(client=httpx.Client(transport=httpx.MockTransport(steam_mock)))
    evidence = lookup.lookup('Hades II 견적')['evidence']
    evidence.update(ramGb=64, storageGb=2000)
    req = Request(budget=1_000_000, uses=('gaming',), resolution='FHD', memo='Hades II 견적',
                  game_evidence=evidence, gpu_models=('5090',))
    fallback = req.without_preferences()
    specs = min_specs(fallback, catalog)
    assert specs.ram_gb == 64 and specs.ssd_gb == 2000
    assert all(s.ram_gb >= 64 and s.ssd_gb >= 2000 for s, _ in relaxed_specs(fallback, specs, catalog))
