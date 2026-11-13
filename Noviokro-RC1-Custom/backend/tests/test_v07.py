from fastapi.testclient import TestClient
from app.main import app

def test_v07_is_additive():
    paths=app.openapi()['paths']
    assert '/api/v1/v07/bots/briefs' in paths
    assert '/api/v1/v06/qa-runs' in paths
    assert '/api/v1/bots' in paths

def test_v07_requires_token():
    r=TestClient(app).get('/api/v1/v07/bots/catalog')
    assert r.status_code==401

def test_v07_staging_disabled_without_token():
    r=TestClient(app).post('/api/v1/v07/monitoring/staging-check',json={'service':'test','url':'https://example.com/health'})
    assert r.status_code==401
