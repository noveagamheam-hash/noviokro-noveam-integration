from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_v10_requires_authentication():
    assert client.get('/api/v1/v10/monitoring/standalone').status_code==401

def test_v10_rejects_unknown_project():
    assert client.get('/api/v1/v10/monitoring/unknown').status_code==400
