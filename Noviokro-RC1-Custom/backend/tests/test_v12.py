from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_v12_denies_without_admin(monkeypatch):
    monkeypatch.setenv('NOVIOKRO_ADMIN_KEY', 'local-secret')
    assert client.get('/api/v1/v12/routes').status_code == 401


def test_v12_persistent_catalog_and_disabled_proxy(monkeypatch, tmp_path):
    monkeypatch.setenv('NOVIOKRO_ADMIN_KEY', 'local-secret')
    monkeypatch.setenv('NOVIOKRO_V12_DATABASE_URL', f'sqlite:///{tmp_path}/catalog.db')
    monkeypatch.setenv('UPSTREAM_DEMO', 'https://example.com')
    key = {'x-admin-key': 'local-secret'}
    assert client.post('/api/v1/v12/routes', json={'name':'demo','upstream':'demo'}, headers=key).status_code == 201
    assert client.post('/api/v1/v12/routes', json={'name':'demo','upstream':'demo'}, headers=key).status_code == 409
    assert client.get('/api/v1/v12/routes', headers=key).json()['routes'][0]['enabled'] is False
    assert client.get('/api/v1/v12/proxy/demo/test', headers=key).status_code == 403
    assert client.delete('/api/v1/v12/routes/demo', headers=key).status_code == 200


def test_v12_rejects_unknown_upstream(monkeypatch, tmp_path):
    monkeypatch.setenv('NOVIOKRO_ADMIN_KEY', 'local-secret')
    monkeypatch.setenv('NOVIOKRO_V12_DATABASE_URL', f'sqlite:///{tmp_path}/catalog.db')
    assert client.post('/api/v1/v12/routes', json={'name':'nope','upstream':'missing'}, headers={'x-admin-key':'local-secret'}).status_code == 400
