import os
os.environ['NOVIOKRO_ADMIN_KEY'] = 'local-test-secret'
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
HEADERS = {'X-Admin-Key': 'local-test-secret'}

def test_authorization():
    assert client.get('/api/v1/bots').status_code == 401

def test_bot_lifecycle():
    r = client.post('/api/v1/bots', headers=HEADERS, json={'name':'Development Bot','bot_type':'devbot'})
    assert r.status_code == 201
    bot = r.json()
    assert bot['enabled'] is False
    run = client.post(f"/api/v1/bots/{bot['id']}/execute", headers=HEADERS, json={'instruction':'Review API routes'})
    assert run.status_code == 202
    assert run.json()['status'] == 'pending_approval'
    assert client.get(f"/api/v1/bot-runs/{run.json()['id']}", headers=HEADERS).status_code == 200

def test_feedback():
    r = client.post('/api/v1/feedback', headers=HEADERS, json={'message':'Add export','category':'suggestion'})
    assert r.status_code == 201
    assert r.json()['status'] == 'new'
