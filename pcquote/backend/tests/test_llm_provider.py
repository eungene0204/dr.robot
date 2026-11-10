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
        timeout = request.extensions['timeout']
        assert timeout == {'connect': 5, 'read': 60, 'write': 5, 'pool': 5}
        assert llm.REQUIREMENTS_TIMEOUT_MS >= sum(timeout.values()) * llm.REQUIREMENTS_ATTEMPTS * 1000 + 10000
        body = json.loads(request.content)
        assert body['model'] == 'k-exaone_v2.5'
        assert body['reasoning_effort'] == 'low'
        assert body['max_tokens'] >= 4096
        assert not {'models', 'route', 'reasoning', 'response_format'} & body.keys()
        assert 'JSON' in body['messages'][0]['content']
        assert 'questions는 항상 빈 배열' in body['messages'][0]['content']
        assert 'maxItems' in body['messages'][0]['content']
        return httpx.Response(200, json={'choices': [{'message': {'content': '\n\n```json\n'+json.dumps(VALUE)+'\n```'}}]})
    complete = llm.configured_llm(client=httpx.Client(transport=httpx.MockTransport(respond)))
    result = llm.interpret('최신 AAA 타이틀용 150만원 QHD 와이파이', complete)
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
    result = llm.interpret('최신 AAA 타이틀용 150만원 QHD', complete)
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
    assert llm.interpret('최신 AAA 타이틀용 150만원', complete)['method'] == 'openrouter'


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


@pytest.mark.parametrize('complete', [None, lambda **kwargs: (_ for _ in ()).throw(TimeoutError('timeout'))])
def test_unknown_purpose_never_defaults_to_gaming(complete):
    result = llm.interpret('LaTeX로 논문을 작성할 본체 150만원', complete)
    assert result.get('needsPurpose') is True
    assert result['profile'] is None
    assert result['budget'] == 1500000
    assert result['questions'] == [llm.USE_QUESTION]


def test_quote_audit_stops_for_unresolved_purpose_and_preserves_context():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / '.claude/skills/quote-eval/run_eval.py'
    spec = importlib.util.spec_from_file_location('quote_eval_regression', path)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    class NoCatalog:
        def get(self):
            raise AssertionError('Unresolved purpose must not reach the recommendation engine')
    case = {'id':'E002','group':'LLM 용도 보완','turns':['LaTeX로 논문을 작성할 본체 150만원'],
            'expect':{'profile':'office','budget':1500000,'resolution':'FHD','clarificationOnFallback':True}}
    result = audit.run_case(case, NoCatalog(), lambda text: llm.interpret(text, None))
    assert result['needsPurpose'] is True and result['plans'] == []
    assert audit.status(result) == 'PASS'
    resumed = audit.screen_requirement([*case['turns'], '사무용이에요'], lambda text: llm.interpret(text, None))
    assert resumed['profile'] == 'office' and resumed['budget'] == 1500000


def test_model_detected_office_uses_office_default_but_keeps_explicit_resolution():
    complete = lambda **kwargs: {**VALUE, 'profile':'office', 'resolution':'FHD'}
    result = llm.interpret('LaTeX로 논문을 작성할 본체 150만원', complete)
    assert result['profile'] == 'office' and result['resolution'] == 'FHD'
    explicit = llm.interpret('LaTeX로 논문을 작성할 본체 150만원 QHD 모니터 사용', complete)
    assert explicit['profile'] == 'office' and explicit['resolution'] == 'QHD'


@pytest.mark.parametrize('text', [
    '게임용 QHD 본체 150만원', '사무용 본체 100만원 화이트 와이파이',
    '게임 QHD 본체 예산 제한 없이', '배그 게임 QHD 본체, 예산은 제한 없이 성능 우선', '총 290만원에 모니터 40만원 포함 게임용',
    '게임용 150만원\n추가 요청: 예산 10만원만 더 올려줘',
])
def test_clear_requirements_skip_model(text):
    calls = []
    def complete(**kwargs):
        calls.append(kwargs)
        return VALUE
    result = llm.interpret(text, complete)
    assert calls == []
    assert result['method'] == 'local'
    assert not result.get('fallback')


@pytest.mark.parametrize('text', ['LaTeX로 논문 작성할 본체 150만원', '사무용 PC 견적'])
def test_ambiguous_requirements_still_use_model(text):
    calls = []
    def complete(**kwargs):
        calls.append(kwargs)
        return {**VALUE, 'profile':'office', 'resolution':'FHD'}
    complete.provider = 'exaone'
    result = llm.interpret(text, complete)
    assert len(calls) == 1 and result['method'] == 'exaone'
