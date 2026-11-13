import asyncio
import pytest
from pcquote.quote_agent import configured_agent_model

@pytest.mark.parametrize('provider,expected', [('exaone', 'k-exaone_v2.5'), ('openrouter', 'existing/model')])
def test_existing_model_without_openai_key(monkeypatch, provider, expected):
    for name in ('OPENAI_API_KEY', 'EXAONE_MODEL', 'OPENROUTER_FALLBACK_MODEL'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('LLM_PROVIDER', provider)
    monkeypatch.setenv(f'{provider.upper()}_API_KEY', 'test-only')
    monkeypatch.setenv('OPENROUTER_MODEL', 'existing/model')
    model, settings, client = configured_agent_model()
    assert model.model == expected
    assert provider in str(client.base_url)
    assert settings.extra_body
    asyncio.run(client.close())


def test_interactive_price_client_still_honors_robots():
    import httpx
    from pcquote.danawa import quote_source_client
    waits = []
    def respond(request):
        return httpx.Response(200, text='User-agent: *\nCrawl-delay: 3' if request.url.path == '/robots.txt' else 'ok')
    client = quote_source_client(client=httpx.Client(transport=httpx.MockTransport(respond)), sleep=waits.append)
    assert client.min_delay == 0.25
    client.text('https://prod.danawa.com/info/?pcode=1')
    client.text('https://prod.danawa.com/info/?pcode=2')
    assert waits and waits[0] > 2.9
    client.http.close()


def test_broadcast_purpose_and_game_search():
    from pcquote.consult import detect_profile
    from pcquote.game_search import game_query
    from pcquote.screen import to_request
    for text in ['유튜브 방송용 견적을 뽑아줘', 'OBS 송출용 PC', '치지직 스트리밍용 견적']:
        assert detect_profile(text) == 'editing'
        assert game_query(text) is None
    assert detect_profile('유튜브 방송 시청용 PC') == 'office'
    req = to_request({'text': '배그 게임 방송용', 'profile': 'editing', 'budget': None}, {'assembly': 0}, {})
    assert req.uses == ('gaming', 'editing')
