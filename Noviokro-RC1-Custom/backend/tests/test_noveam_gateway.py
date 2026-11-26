"""Framework regressions for the NOVEAM user gateway; no real upstream or DB."""
import httpx
import pytest
from fastapi.testclient import TestClient
from app.noveam_gateway import create_noveam_gateway

@pytest.fixture
def gateway(monkeypatch):
    monkeypatch.setenv('NOVIOKRO_NOVEAM_GATEWAY_ENABLED', '1')
    monkeypatch.setenv('NOVIOKRO_SERVICE_NOVEAM_BACKEND', 'http://127.0.0.1:8000')
    return TestClient(create_noveam_gateway())

@pytest.mark.parametrize('method', ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def test_forwards_user_calls_without_manager_secret(gateway, monkeypatch, method):
    calls = []
    def upstream(request):
        calls.append(request)
        assert request.method == method
        assert str(request.url) == 'http://127.0.0.1:8000/api/users/me?view=a%2Bb'
        assert request.headers['authorization'] == 'Bearer synthetic-user'
        assert 'x-admin-key' not in request.headers
        assert 'cookie' not in request.headers
        assert 'x-forwarded-for' not in request.headers
        assert request.content == b'{"test":true}'
        return httpx.Response(428, json={'detail': {'code': 'ONBOARDING_REQUIRED'}}, headers={'Set-Cookie':'private=secret'})
    native = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: native(transport=httpx.MockTransport(upstream), **kw))
    response = gateway.request(method, '/api/users/me?view=a%2Bb', content=b'{"test":true}', headers={
        'Authorization':'Bearer synthetic-user', 'X-Admin-Key':'synthetic-admin', 'Cookie':'private=value',
        'X-Forwarded-For':'untrusted', 'Content-Type':'application/json'})
    assert len(calls) == 1
    assert response.status_code == 428
    assert response.json()['detail']['code'] == 'ONBOARDING_REQUIRED'
    assert 'set-cookie' not in response.headers
    assert response.headers['cache-control'] == 'no-store'


def test_disabled_gateway_and_scoped_preflight(gateway, monkeypatch):
    monkeypatch.setenv('NOVIOKRO_NOVEAM_GATEWAY_ENABLED', '0')
    assert gateway.get('/api/users/me').status_code == 503
    allowed = gateway.options('/api/users/me', headers={'Origin':'http://127.0.0.1:5500',
        'Access-Control-Request-Method':'PATCH', 'Access-Control-Request-Headers':'authorization,content-type'})
    assert allowed.status_code == 200
    assert allowed.headers['access-control-allow-origin'] == 'http://127.0.0.1:5500'
    denied = gateway.options('/api/users/me', headers={'Origin':'https://untrusted.example',
        'Access-Control-Request-Method':'POST'})
    assert denied.status_code == 400
