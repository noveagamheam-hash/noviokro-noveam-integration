from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

def test_v15_status_is_admin_only(monkeypatch):
    monkeypatch.setenv('NOVIOKRO_ADMIN_KEY','test-v15-secret')
    assert client.get('/api/v1/v15/status').status_code == 401
    r=client.get('/api/v1/v15/status',headers={'x-admin-key':'test-v15-secret'})
    assert r.status_code == 200
    assert r.json()['production_ready'] is False
    assert 'test-v15-secret' not in str(r.json())

def test_v15_summary_disabled(monkeypatch):
    monkeypatch.setenv('NOVIOKRO_ADMIN_KEY','test-v15-secret')
    monkeypatch.delenv('NOVIOKRO_V14_ENABLE_TELEMETRY',raising=False)
    assert client.get('/api/v1/v15/traffic-summary').status_code == 401
    data=client.get('/api/v1/v15/traffic-summary',headers={'x-admin-key':'test-v15-secret'}).json()
    assert data == {'project':'standalone','enabled':False,'routes':[]}

def test_v15_summary_with_record(monkeypatch,tmp_path):
    monkeypatch.setenv('NOVIOKRO_ADMIN_KEY','test-v15-secret')
    monkeypatch.setenv('NOVIOKRO_V14_ENABLE_TELEMETRY','1')
    monkeypatch.setenv('NOVIOKRO_V14_DATABASE_URL',f'sqlite:///{tmp_path}/v15.db')
    from app.v14 import engine
    from sqlalchemy import text
    with engine().begin() as conn:
        conn.execute(text("INSERT INTO v14_traffic(id,project,route,status_code,latency_ms,recorded_at) VALUES ('test','standalone','sample',503,25.5,'2026-01-01')"))
    data=client.get('/api/v1/v15/traffic-summary',headers={'x-admin-key':'test-v15-secret'}).json()
    assert data['routes']==[{'route':'sample','requests':1,'server_errors':1,'rate_limited':0,'avg_latency_ms':25.5}]
