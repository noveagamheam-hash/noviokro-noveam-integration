import os
os.environ.setdefault('NOVIOKRO_ADMIN_KEY','test-admin-key-long-enough-123456')
os.environ.setdefault('NOVIOKRO_V08_TOKEN_SECRET','test-v08-token-signing-secret-more-than-32-chars')
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_v08_rejects_missing_token():
    assert client.get('/api/v1/v08/identity/me/standalone').status_code==401

def test_v08_local_ai_disabled():
    # Denied without valid auth; cannot run inference without permissions.
    assert client.post('/api/v1/v08/ai/local-draft',json={'project':'standalone','bot':'devbot','prompt':'Explain this API'}).status_code==401

def test_v08_press_requires_token():
    assert client.post('/api/v1/v08/press/evidence',json={'project':'standalone','headline':'Example headline','source_url':'https://example.org/story'}).status_code==401

def test_v08_project_validation():
    assert client.get('/api/v1/v08/qa/report/unknown').status_code==400
