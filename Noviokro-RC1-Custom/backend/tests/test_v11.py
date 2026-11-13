import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
H = {'X-Admin-Key': 'local-test-secret'}

def test_gateway_diagnostics_require_auth():
    assert client.get('/api/v1/v11/gateway/configuration').status_code == 401
    assert client.post('/api/v1/v11/gateway/staging-health', json={'upstream': 'demo'}).status_code == 401

def test_gateway_checks_disabled_by_default(monkeypatch):
    monkeypatch.delenv('NOVIOKRO_ENABLE_STAGING_CHECKS', raising=False)
    assert client.post('/api/v1/v11/gateway/staging-health', headers=H, json={'upstream': 'demo'}).status_code == 403

def test_unconfigured_target_rejected(monkeypatch):
    monkeypatch.setenv('NOVIOKRO_ENABLE_STAGING_CHECKS', '1')
    monkeypatch.delenv('UPSTREAM_DEMO', raising=False)
    assert client.post('/api/v1/v11/gateway/staging-health', headers=H, json={'upstream': 'demo'}).status_code == 400

def test_http_requires_explicit_opt_in(monkeypatch):
    monkeypatch.setenv('NOVIOKRO_ENABLE_STAGING_CHECKS', '1')
    monkeypatch.setenv('UPSTREAM_DEMO', 'http://localhost:9999')
    monkeypatch.delenv('NOVIOKRO_ALLOW_HTTP_STAGING', raising=False)
    assert client.post('/api/v1/v11/gateway/staging-health', headers=H, json={'upstream': 'demo'}).status_code == 400

def test_openapi_operation_ids_unique():
    operations=[]
    for path, methods in client.get('/openapi.json').json()['paths'].items():
        for method, spec in methods.items():
            if method in {'get','post','put','patch','delete','head','options'}:
                operations.append(spec['operationId'])
    assert len(operations) == len(set(operations))

def test_gateway_proxy_auth_and_missing_route():
    assert client.get('/gateway/missing/example').status_code == 401
    assert client.get('/gateway/missing/example', headers=H).status_code == 404

def test_health_does_not_require_admin():
    assert client.get('/health').status_code == 200
