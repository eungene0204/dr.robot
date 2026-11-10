import json
import httpx
import pytest
from pcquote import llm

VALUE = dict(profile='gaming', budget=1500000, resolution='QHD', white=False, wifi=True, os=False, questions=[])


def test_exaone_request(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'exaone')
    monkeypatch.setenv('EXAONE_API_KEY', 'test-key')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'must-not-use')
    def respond(request):
        assert str(request.url) == llm.EXAONE_URL
        assert request.headers['authorization'] == 'Bearer test-key'
        body = json.loads(request.content)
        assert body['model'] == 'k-exaone_v2.5'
        assert body['reasoning_effort'] == 'low'
        assert body['max_tokens'] >= 4096
        assert not {'models', 'route', 'reasoning', 'response_format'} & body.keys()
        assert 'JSON' in body['messages'][0]['content']
        return httpx.Response(200, json={'choices': [{'message': {'content': '\n\n```json\n'+json.dumps(VALUE)+'\n```'}}]})
    complete = llm.configured_llm(client=httpx.Client(transport=httpx.MockTransport(respond)))
    result = llm.interpret('게임용 150만원 QHD 와이파이', complete)
    assert result['method'] == 'exaone'
    assert result['budget'] == 1500000
    assert result['wifi'] is True


@pytest.mark.parametrize('response', [httpx.Response(429), httpx.Response(200, json={'choices':[{'message':{'content':'not json'}}]})])
def test_failure_stays_on_exaone(response):
    urls = []
    def respond(request):
        urls.append(str(request.url))
        return response
    complete = llm.create_llm('test-key', 'k-exaone_v2.5', fallback='other', provider='exaone',
                              client=httpx.Client(transport=httpx.MockTransport(respond)))
    result = llm.interpret('게임용 150만원 QHD', complete)
    assert result['method'] == 'local'
    assert result['budget'] == 1500000
    assert urls == [llm.EXAONE_URL, llm.EXAONE_URL]


def test_missing_exaone_key_does_not_use_openrouter(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'exaone')
    monkeypatch.delenv('EXAONE_API_KEY', raising=False)
    monkeypatch.setenv('OPENROUTER_API_KEY', 'legacy-key')
    monkeypatch.setenv('OPENROUTER_MODEL', 'legacy-model')
    assert llm.configured_llm() is None


def test_legacy_openrouter():
    def respond(request):
        assert str(request.url) == llm.OPENROUTER_URL
        body = json.loads(request.content)
        assert body['response_format']['type'] == 'json_schema'
        assert body['reasoning'] == {'enabled': False}
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(VALUE)}}]})
    complete = llm.create_llm('test-key', 'legacy-model', client=httpx.Client(transport=httpx.MockTransport(respond)))
    assert llm.interpret('게임용 150만원', complete)['method'] == 'openrouter'


def test_exaone_answer_system_keeps_json_instruction_last():
    from pcquote.service import utcnow
    def respond(request):
        messages = json.loads(request.content)['messages']
        assert sum(m['role'] == 'system' for m in messages) == 1
        assert messages[0]['content'].index('출력 형식:') > messages[0]['content'].index('평문으로 쓴다')
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({'answer': '메모리는 실행 중인 프로그램의 데이터를 보관합니다.', 'sources': ['general']})}}]})
    complete = llm.create_llm('test-key', 'k-exaone_v2.5', provider='exaone', client=httpx.Client(transport=httpx.MockTransport(respond)))
    result = llm.answer('메모리 역할?', complete=complete, catalog=[], policy={}, quote=None, history=[], now=utcnow())
    assert result['method'] == 'llm'
