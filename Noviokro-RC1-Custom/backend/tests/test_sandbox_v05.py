import os
os.environ.setdefault('NOVIOKRO_ADMIN_KEY','local-dev-test-secret-123456')
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
headers={'X-Admin-Key':os.environ['NOVIOKRO_ADMIN_KEY']}
def test_requires_auth():
    assert client.get('/api/v1/sandbox/bots').status_code==403
def test_persistent_bot_and_run():
    b=client.post('/api/v1/sandbox/bots',headers=headers,json={'name':'QA sandbox','bot_type':'testbot','enabled':True}).json()
    assert b['id']
    r=client.post(f"/api/v1/sandbox/bots/{b['id']}/run",headers=headers,json={'spec':{'cases':[{'expected_status':200,'actual_status':200},{'expected_status':201,'actual_status':400}]}})
    assert r.status_code==201
    assert r.json()['result']['passed']==1
    assert client.get('/api/v1/sandbox/metrics',headers=headers).json()['runs']>=1
def test_devbot_lint():
    b=client.post('/api/v1/sandbox/bots',headers=headers,json={'name':'Dev sandbox','bot_type':'devbot','enabled':True}).json()
    r=client.post(f"/api/v1/sandbox/bots/{b['id']}/run",headers=headers,json={'spec':{'paths':{'/health':{'get':{'responses':{'200':{}}}}}}})
    assert r.json()['result']['total_warnings']==1
