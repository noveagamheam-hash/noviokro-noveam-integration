import httpx
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
HEADERS = {'x-admin-key': 'v16-test-secret'}

def test_preflight_auth_and_safe_response(monkeypatch):
    monkeypatch.setenv('NOVIOKRO_ADMIN_KEY', 'v16-test-secret')
    assert client.get('/api/v1/v16/preflight').status_code == 401
    r = client.get('/api/v1/v16/preflight', headers=HEADERS)
    assert r.status_code == 200
    assert r.json()['production_ready'] is False
    assert 'v16-test-secret' not in r.text

def test_preflight_flags(monkeypatch):
    monkeypatch.setenv('NOVIOKRO_ADMIN_KEY', 'v16-test-secret')
    monkeypatch.setenv('NOVIOKRO_V12_ENABLE_PROXY', '1')
    monkeypatch.setenv('NOVIOKRO_V14_ENABLE_TELEMETRY', '1')
    r = client.get('/api/v1/v16/preflight', headers=HEADERS)
    assert r.json()['flags']['proxy_enabled'] is True
    assert r.json()['flags']['telemetry_enabled'] is True

def test_staging_proxy_forwards_without_admin_secret(monkeypatch, tmp_path):
    from app import v12
    monkeypatch.setenv('NOVIOKRO_ADMIN_KEY', 'v16-test-secret')
    monkeypatch.setenv('NOVIOKRO_V12_DATABASE_URL', f'sqlite:///{tmp_path}/v16.db')
    monkeypatch.setenv('NOVIOKRO_V12_ENABLE_PROXY', '1')
    monkeypatch.setenv('NOVIOKRO_ALLOW_HTTP_STAGING', '1')
    monkeypatch.setenv('NOVIOKRO_ALLOW_LOOPBACK_STAGING', '1')
    monkeypatch.setenv('UPSTREAM_V16LOCAL', 'http://127.0.0.1:9898')
    created = client.post('/api/v1/v12/routes', headers=HEADERS,
                          json={'name':'v16sample','upstream':'v16local','enabled':True})
    assert created.status_code == 201, created.text
    seen = {}
    def handler(request):
        seen['method'] = request.method
        seen['url'] = str(request.url)
        seen['headers'] = dict(request.headers)
        seen['body'] = request.content
        return httpx.Response(201, json={'ok':True})
    real_client = httpx.AsyncClient
    def fake_client(*args, **kwargs):
        kwargs['transport'] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)
    monkeypatch.setattr(v12.httpx, 'AsyncClient', fake_client)
    response = client.post('/api/v1/v12/proxy/v16sample/echo?mode=test',
                           headers={**HEADERS,'X-Custom-Test':'present'},content=b'hello')
    assert response.status_code == 201, response.text
    assert seen['method'] == 'POST'
    assert seen['url'] == 'http://127.0.0.1:9898/echo?mode=test'
    assert seen['body'] == b'hello'
    assert seen['headers']['x-custom-test'] == 'present'
    assert 'x-admin-key' not in seen['headers']
    assert client.get('/api/v1/v12/proxy/v16sample/echo').status_code == 401

def test_proxy_fails_closed_when_disabled(monkeypatch):
    monkeypatch.setenv('NOVIOKRO_ADMIN_KEY', 'v16-test-secret')
    monkeypatch.delenv('NOVIOKRO_V12_ENABLE_PROXY', raising=False)
    assert client.get('/api/v1/v12/proxy/anything/echo', headers=HEADERS).status_code == 403
