from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_monitoring_requires_admin(monkeypatch):
    monkeypatch.setenv('NOVIOKRO_ADMIN_KEY','test-key')
    assert client.get('/api/v1/v13/monitoring/standalone').status_code == 401
    assert client.post('/api/v1/v13/observations',json={'project':'standalone','route':'demo','status_code':200,'latency_ms':5}).status_code == 401


def test_monitoring_persistence_and_audit(monkeypatch,tmp_path):
    monkeypatch.setenv('NOVIOKRO_ADMIN_KEY','test-key')
    monkeypatch.setenv('NOVIOKRO_V13_DATABASE_URL',f'sqlite:///{tmp_path}/v13.db')
    h={'x-admin-key':'test-key'}
    for status,latency in [(200,10),(503,30)]:
        r=client.post('/api/v1/v13/observations',headers=h,json={'project':'standalone','route':'demo','status_code':status,'latency_ms':latency})
        assert r.status_code == 201, r.text
    data=client.get('/api/v1/v13/monitoring/standalone',headers=h).json()
    assert data['sample_count']==2 and data['error_count']==1 and data['average_latency_ms']==20
    assert len(client.get('/api/v1/v13/audit/standalone',headers=h).json()['events'])==2
    assert client.get('/api/v1/v13/monitoring/noveam',headers=h).json()['sample_count']==0


def test_observation_validation(monkeypatch,tmp_path):
    monkeypatch.setenv('NOVIOKRO_ADMIN_KEY','test-key')
    monkeypatch.setenv('NOVIOKRO_V13_DATABASE_URL',f'sqlite:///{tmp_path}/v13.db')
    r=client.post('/api/v1/v13/observations',headers={'x-admin-key':'test-key'},json={'project':'standalone','route':'bad route','status_code':999,'latency_ms':-5})
    assert r.status_code==422
