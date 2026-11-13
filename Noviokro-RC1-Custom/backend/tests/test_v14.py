from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_telemetry_opt_in_and_auth(monkeypatch, tmp_path):
    monkeypatch.setenv('NOVIOKRO_ADMIN_KEY', 'local-secret')
    monkeypatch.setenv('NOVIOKRO_V14_DATABASE_URL', f'sqlite:///{tmp_path}/v14.db')
    monkeypatch.setenv('NOVIOKRO_V14_ENABLE_TELEMETRY', '1')
    monkeypatch.delenv('NOVIOKRO_V14_ENABLE_DB_RATE_LIMIT', raising=False)
    assert client.get('/api/v1/v14/traffic/standalone').status_code == 401
    # Existing proxy is disabled, but its response must be recorded without request contents.
    r = client.get('/api/v1/v12/proxy/demo/hello?secret=do-not-store', headers={'x-admin-key':'local-secret'})
    assert r.status_code == 403
    data = client.get('/api/v1/v14/traffic/standalone', headers={'x-admin-key':'local-secret'}).json()
    assert data['sample_count'] == 1
    assert data['observations'][0]['status_code'] == 403
    assert 'do-not-store' not in str(data)
    assert client.get('/api/v1/v14/traffic/noveam', headers={'x-admin-key':'local-secret'}).status_code == 404

def test_persistent_rate_limit(monkeypatch, tmp_path):
    monkeypatch.setenv('NOVIOKRO_ADMIN_KEY', 'local-secret')
    monkeypatch.setenv('NOVIOKRO_V14_DATABASE_URL', f'sqlite:///{tmp_path}/v14.db')
    monkeypatch.setenv('NOVIOKRO_V14_ENABLE_TELEMETRY', '1')
    monkeypatch.setenv('NOVIOKRO_V14_ENABLE_DB_RATE_LIMIT', '1')
    monkeypatch.setenv('NOVIOKRO_V14_RPM', '1')
    headers={'x-admin-key':'local-secret'}
    assert client.get('/api/v1/v12/proxy/example/ok',headers=headers).status_code == 403
    second = client.get('/api/v1/v12/proxy/example/ok',headers=headers)
    assert second.status_code == 429
    assert second.headers['retry-after'] == '60'
    assert client.get('/api/v1/v12/proxy/example/ok').status_code == 401
    assert client.get('/api/v1/v14/traffic/standalone',headers=headers).json()['sample_count'] == 3
