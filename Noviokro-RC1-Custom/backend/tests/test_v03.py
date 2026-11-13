import os
os.environ['NOVIOKRO_ADMIN_KEY']='local-test-secret'
os.environ['DATABASE_URL']='sqlite://'
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
H={'X-Admin-Key':'local-test-secret'}
def test_v03_requires_auth():
    assert client.get('/api/v1/next/models').status_code==401

def test_model_registration_and_disabled_inference():
    r=client.post('/api/v1/next/models',headers=H,json={'name':'Local','provider':'ollama','model':'gemma3'})
    assert r.status_code==201
    ident=r.json()['id']
    assert client.post(f'/api/v1/next/models/{ident}/generate',headers=H,json={'prompt':'hello'}).status_code==403

def test_approval_never_executes():
    bot=client.post('/api/v1/bots',headers=H,json={'name':'Dev','bot_type':'devbot'}).json()
    r=client.post('/api/v1/next/approvals',headers=H,json={'bot_id':bot['id'],'instruction':'review code'})
    assert r.status_code==201
    decision=client.post('/api/v1/next/approvals/'+r.json()['id']+'/approve',headers=H)
    assert decision.json()['executed'] is False
