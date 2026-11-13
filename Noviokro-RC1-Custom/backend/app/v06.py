"""v0.6 isolated offline QA and monitoring. No arbitrary code or outbound traffic."""
import os, hmac, hashlib, base64, json, time, multiprocessing
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime
from .sandbox_bots import Base, engine, Session

router = APIRouter(prefix='/api/v1/v06', tags=['v0.6 isolated security, QA and monitoring'])

class Record(Base):
    __tablename__ = 'noviokro_v06_records'
    id=Column(String(36),primary_key=True)
    kind=Column(String(30),nullable=False)
    actor=Column(String(30),nullable=False)
    result_json=Column(Text,nullable=False)
    created_at=Column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

def initialize_v06(): Base.metadata.create_all(engine)

def _secret():
    s=os.getenv('NOVIOKRO_V06_TOKEN_SECRET','')
    if len(s)<32: raise HTTPException(503,'Set NOVIOKRO_V06_TOKEN_SECRET to at least 32 characters')
    return s.encode()

def _encode(data): return base64.urlsafe_b64encode(json.dumps(data,separators=(',',':')).encode()).rstrip(b'=').decode()
def _decode(data): return json.loads(base64.urlsafe_b64decode(data+'='*((-len(data))%4)))

def _token(scopes):
    payload=_encode({'scopes':scopes,'exp':int(time.time())+3600,'aud':'noviokro-v06','sub':'local-operator'})
    sig=base64.urlsafe_b64encode(hmac.new(_secret(),payload.encode(),hashlib.sha256).digest()).rstrip(b'=').decode()
    return payload+'.'+sig

def require(auth,scope):
    if not auth or not auth.startswith('Bearer '): raise HTTPException(401,'Bearer token required')
    try:
        value=auth[7:]; payload,sig=value.split('.',1)
        correct=base64.urlsafe_b64encode(hmac.new(_secret(),payload.encode(),hashlib.sha256).digest()).rstrip(b'=').decode()
        data=_decode(payload)
        if not hmac.compare_digest(sig,correct) or data.get('aud')!='noviokro-v06' or int(data.get('exp',0))<=time.time() or scope not in data.get('scopes',[]):
            raise ValueError()
    except (ValueError,TypeError,KeyError,OverflowError): raise HTTPException(403,'Invalid or insufficient token')
    return data['sub']

class Login(BaseModel):
    requested_role: str = Field(pattern='^(viewer|tester|admin)$')

@router.post('/local-token')
def local_token(body:Login,x_admin_key:str|None=Header(None)):
    # Bootstrap endpoint is for localhost-only Docker bindings. No browser key storage.
    key=os.getenv('NOVIOKRO_ADMIN_KEY','')
    if len(key)<16 or not x_admin_key or not hmac.compare_digest(key,x_admin_key): raise HTTPException(403,'Admin bootstrap key required')
    scopes={'viewer':['read'],'tester':['read','execute'],'admin':['read','execute','admin']}[body.requested_role]
    return {'access_token':_token(scopes),'token_type':'bearer','expires_in':3600,'scopes':scopes}

class QACase(BaseModel):
    name:str=Field(min_length=1,max_length=100)
    expected_status:int=Field(ge=100,le=599)
    actual_status:int=Field(ge=100,le=599)
    max_latency_ms:float=Field(ge=0,le=120000)
    actual_latency_ms:float=Field(ge=0,le=120000)
class QARequest(BaseModel):
    cases:list[QACase]=Field(min_length=1,max_length=100)

class HealthSnapshot(BaseModel):
    service:str=Field(min_length=1,max_length=100)
    status_code:int=Field(ge=100,le=599)
    latency_ms:float=Field(ge=0,le=120000)
    error_rate:float=Field(ge=0,le=1)

# Worker evaluates only validated JSON; no user-supplied scripts or network destinations.
def _worker(kind, payload, queue):
    try:
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_CPU,(2,3))
            resource.setrlimit(resource.RLIMIT_AS,(192*1024*1024,192*1024*1024))
        except (ImportError,ValueError,OSError): pass
        if kind=='qa':
            rows=[{'name':x['name'],'passed':x['expected_status']==x['actual_status'] and x['actual_latency_ms']<=x['max_latency_ms']} for x in payload['cases']]
            result={'total':len(rows),'passed':sum(x['passed'] for x in rows),'cases':rows,'mode':'offline_qa'}
        else:
            healthy=200<=payload['status_code']<400 and payload['error_rate']<0.05 and payload['latency_ms']<2000
            result={'service':payload['service'],'healthy':healthy,'status_code':payload['status_code'],'latency_ms':payload['latency_ms'],'error_rate':payload['error_rate'],'mode':'submitted_snapshot_only'}
        queue.put(result)
    except Exception as e: queue.put({'error':type(e).__name__})

def run_isolated(kind,payload):
    ctx=multiprocessing.get_context('spawn')
    q=ctx.Queue(maxsize=1); proc=ctx.Process(target=_worker,args=(kind,payload,q),daemon=True)
    proc.start(); proc.join(timeout=5)
    if proc.is_alive(): proc.terminate(); proc.join(); raise HTTPException(504,'Worker timed out')
    if proc.exitcode!=0: raise HTTPException(500,'Worker failed')
    try: result=q.get(timeout=1)
    except Exception: raise HTTPException(500,'Worker produced no result')
    if 'error' in result: raise HTTPException(500,'Worker evaluation failed')
    return result

def save(kind,actor,result):
    ident=str(uuid4())
    with Session.begin() as db: db.add(Record(id=ident,kind=kind,actor=actor,result_json=json.dumps(result)))
    return {'id':ident,'result':result}

@router.post('/qa-runs',status_code=201)
def qa_run(body:QARequest,authorization:str|None=Header(None)):
    actor=require(authorization,'execute')
    return save('qa',actor,run_isolated('qa',body.model_dump()))

@router.post('/monitoring/snapshots',status_code=201)
def snapshot(body:HealthSnapshot,authorization:str|None=Header(None)):
    actor=require(authorization,'execute')
    return save('monitor',actor,run_isolated('monitor',body.model_dump()))

@router.get('/records')
def records(authorization:str|None=Header(None)):
    require(authorization,'read')
    with Session() as db:
        rows=db.query(Record).order_by(Record.created_at.desc()).limit(100).all()
        return [{'id':r.id,'kind':r.kind,'actor':r.actor,'result':json.loads(r.result_json)} for r in rows]
