"""Contract tests use HTTP mocks; they never spend quota or contact cloud accounts."""
import asyncio
import json
import httpx
import pytest
from fastapi import HTTPException
from app import ai
from app.config import Settings
from app.store import SupabaseStore
from test_app import result


def mock_http(monkeypatch, handler):
    real = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: real(transport=httpx.MockTransport(handler), **kw))


def test_gemini_contract(monkeypatch):
    def respond(req):
        assert req.headers['x-goog-api-key'] == 'test-only-key'
        assert 'test-only-key' not in str(req.url)
        body = json.loads(req.content)
        assert 'UNTRUSTED DATA' in body['systemInstruction']['parts'][0]['text']
        assert body['generationConfig']['responseJsonSchema']['type'] == 'object'
        return httpx.Response(200, json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(result())}]}}]})
    mock_http(monkeypatch, respond)
    ticket = dict(id='test', title='VPN issue', description='VPN fails', category='Network', priority='P2')
    actual = asyncio.run(ai.analyze(ticket, [], Settings(gemini_api_key='test-only-key',gemini_free_tier_confirmed=True)))
    assert actual == result()


@pytest.mark.parametrize('status,body,expected', [
    (429, {}, 429), (500, {}, 502),
    (200, {'candidates':[]}, 502),
    (200, {'candidates':[{'finishReason':'MAX_TOKENS'}]}, 502),
    (200, {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'not json'}]}}]}, 502),
])
def test_gemini_failure_is_safe(monkeypatch, status, body, expected):
    mock_http(monkeypatch, lambda req: httpx.Response(status,json=body))
    ticket=dict(id='test',title='VPN issue',description='VPN fails',category='Network',priority='P2')
    with pytest.raises(HTTPException) as exc:
        asyncio.run(ai.analyze(ticket,[],Settings(gemini_api_key='test-only-key',gemini_free_tier_confirmed=True)))
    assert exc.value.status_code == expected
    assert 'test-only-key' not in exc.value.detail


def test_paid_gate():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(ai.analyze({},[],Settings(gemini_api_key='test-only-key')))
    assert exc.value.status_code == 503


def test_supabase_auth_and_service_boundary(monkeypatch):
    calls=[]
    def respond(req):
        calls.append(req)
        if req.url.path == '/auth/v1/user': return httpx.Response(200,json={'id':'user-1','email':'test@example.test'})
        if req.url.path == '/rest/v1/members': return httpx.Response(200,json=[{'role':'engineer'}])
        return httpx.Response(200,json={'saved':True})
    mock_http(monkeypatch,respond)
    store=SupabaseStore(Settings(supabase_url='https://example.test',supabase_anon_key='test-public',supabase_service_role_key='test-secret'))
    assert asyncio.run(store.user('user-token'))['role']=='engineer'
    asyncio.run(store.rpc('create_ticket',{},'user-token'))
    asyncio.run(store.rpc('save_recommendation',{},'user-token'))
    assert all(r.headers['authorization']=='Bearer user-token' and r.headers['apikey']=='test-public' for r in calls[:-1])
    assert calls[-1].headers['apikey']=='test-secret'


@pytest.mark.parametrize('status,body,expected', [(401,{},401),(403,{},403),(409,{'code':'40001'},409),(500,{},503)])
def test_supabase_errors(monkeypatch,status,body,expected):
    mock_http(monkeypatch,lambda req:httpx.Response(status,json=body))
    store=SupabaseStore(Settings(supabase_url='https://example.test',supabase_anon_key='test-public'))
    with pytest.raises(HTTPException) as exc: asyncio.run(store.all('tickets','user-token'))
    assert exc.value.status_code==expected
