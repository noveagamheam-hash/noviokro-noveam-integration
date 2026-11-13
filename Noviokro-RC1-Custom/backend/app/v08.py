"""Additive v0.8: independent identity/RBAC, QA reports, press evidence, optional local AI."""
import os, json, time, hmac, hashlib, secrets, base64
from datetime import datetime, timezone
from uuid import uuid4
from urllib.parse import urlsplit
import httpx
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, UniqueConstraint
from .sandbox_bots import Base, engine, Session
from .v06 import Record

router = APIRouter(prefix='/api/v1/v08', tags=['v0.8 standalone features'])
PROJECTS={'standalone','noveam','noveomediater'}
PERMISSIONS={'viewer':{'read'},'tester':{'read','qa'},'editor':{'read','qa','draft'},'manager':{'read','qa','draft','review'},'admin':{'read','qa','draft','review','manage'}}

class Principal(Base):
    __tablename__='noviokro_v08_principals'
    id=Column(String(36),primary_key=True)
    username=Column(String(100),nullable=False,unique=True)
    password_hash=Column(Text,nullable=False)
    created_at=Column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Membership(Base):
    __tablename__='noviokro_v08_memberships'
    id=Column(String(36),primary_key=True)
    principal_id=Column(String(36),nullable=False)
    project=Column(String(30),nullable=False)
    role=Column(String(30),nullable=False)
    __table_args__=(UniqueConstraint('principal_id','project',name='uq_v08_member_project'),)
class Evidence(Base):
    __tablename__='noviokro_v08_press_evidence'
    id=Column(String(36),primary_key=True)
    project=Column(String(30),nullable=False)
    headline=Column(String(250),nullable=False)
    source_url=Column(Text,nullable=False)
    status=Column(String(30),nullable=False,default='unverified')
    notes=Column(Text,nullable=False,default='')
    created_at=Column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

def initialize_v08(): Base.metadata.create_all(engine)

def _secret():
    s=os.getenv('NOVIOKRO_V08_TOKEN_SECRET','')
    if len(s)<32: raise HTTPException(503,'Configure NOVIOKRO_V08_TOKEN_SECRET (32+ chars)')
    return s.encode()
def _hash(password,salt=None):
    salt=salt or secrets.token_bytes(16)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,310000)
    return salt.hex()+':'+digest.hex()
def _verify(password,stored):
    try:
        salt,expected=stored.split(':',1)
        return hmac.compare_digest(_hash(password,bytes.fromhex(salt)),stored)
    except (ValueError,TypeError): return False

def _encode(data): return base64.urlsafe_b64encode(json.dumps(data,separators=(',',':')).encode()).rstrip(b'=').decode()
def _decode(s): return json.loads(base64.urlsafe_b64decode(s+'='*((-len(s))%4)))
def _sign(principal):
    payload=_encode({'sub':principal.id,'exp':int(time.time())+1800,'aud':'noviokro-v08'})
    sig=hmac.new(_secret(),payload.encode(),hashlib.sha256).hexdigest()
    return payload+'.'+sig

def authz(authorization,project,permission):
    if project not in PROJECTS: raise HTTPException(400,'Unknown project')
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401,'Bearer token required')
    try:
        payload,signature=authorization[7:].split('.',1)
        expected=hmac.new(_secret(),payload.encode(),hashlib.sha256).hexdigest()
        data=_decode(payload)
        if not hmac.compare_digest(signature,expected) or data.get('aud')!='noviokro-v08' or data.get('exp',0)<=time.time(): raise ValueError()
    except (ValueError,TypeError,KeyError,OverflowError): raise HTTPException(401,'Invalid or expired token')
    with Session() as db:
        member=db.query(Membership).filter_by(principal_id=data['sub'],project=project).first()
        if not member or permission not in PERMISSIONS.get(member.role,set()): raise HTTPException(403,'Insufficient project permission')
        return data['sub']

class Bootstrap(BaseModel):
    username:str=Field(min_length=3,max_length=100,pattern=r'^[a-zA-Z0-9_.-]+$')
    password:str=Field(min_length=12,max_length=256)
@router.post('/identity/bootstrap',status_code=201)
def bootstrap(body:Bootstrap,x_admin_key:str|None=Header(None)):
    key=os.getenv('NOVIOKRO_ADMIN_KEY','')
    if len(key)<16 or not x_admin_key or not hmac.compare_digest(x_admin_key,key): raise HTTPException(403,'Bootstrap key required')
    with Session.begin() as db:
        if db.query(Principal).first(): raise HTTPException(409,'Already bootstrapped')
        ident=str(uuid4());db.add(Principal(id=ident,username=body.username,password_hash=_hash(body.password)))
        db.add(Membership(id=str(uuid4()),principal_id=ident,project='standalone',role='admin'))
    return {'id':ident,'project':'standalone','role':'admin'}
@router.post('/identity/login')
def login(body:Bootstrap):
    with Session() as db:
        principal=db.query(Principal).filter_by(username=body.username).first()
        # Always run password KDF to reduce account enumeration timing.
        good=_verify(body.password,principal.password_hash if principal else _hash('invalid-placeholder'))
        if not principal or not good: raise HTTPException(401,'Invalid credentials')
        return {'access_token':_sign(principal),'token_type':'bearer','expires_in':1800}
class Grant(BaseModel):
    principal_id:str=Field(min_length=36,max_length=36)
    project:str=Field(pattern='^(standalone|noveam|noveomediater)$')
    role:str=Field(pattern='^(viewer|tester|editor|manager|admin)$')
@router.post('/identity/memberships',status_code=201)
def grant(body:Grant,authorization:str|None=Header(None)):
    authz(authorization,'standalone','manage')
    with Session.begin() as db:
        if not db.get(Principal,body.principal_id): raise HTTPException(404,'Principal not found')
        m=db.query(Membership).filter_by(principal_id=body.principal_id,project=body.project).first()
        if m: m.role=body.role
        else: db.add(Membership(id=str(uuid4()),**body.model_dump()))
    return {'status':'saved',**body.model_dump()}
@router.get('/identity/me/{project}')
def me(project:str,authorization:str|None=Header(None)):
    ident=authz(authorization,project,'read')
    with Session() as db:
        m=db.query(Membership).filter_by(principal_id=ident,project=project).first()
        return {'principal_id':ident,'project':project,'role':m.role,'permissions':sorted(PERMISSIONS[m.role])}

class EvidenceInput(BaseModel):
    project:str=Field(pattern='^(standalone|noveam|noveomediater)$')
    headline:str=Field(min_length=3,max_length=250)
    source_url:str=Field(max_length=1000)
    notes:str=Field(default='',max_length=2000)
@router.post('/press/evidence',status_code=201)
def add_evidence(body:EvidenceInput,authorization:str|None=Header(None)):
    authz(authorization,body.project,'draft')
    u=urlsplit(body.source_url)
    if u.scheme!='https' or not u.hostname or u.username or u.password: raise HTTPException(400,'Public HTTPS URL required')
    ident=str(uuid4())
    with Session.begin() as db: db.add(Evidence(id=ident,project=body.project,headline=body.headline,source_url=body.source_url,notes=body.notes,status='unverified'))
    return {'id':ident,'status':'unverified','note':'Submitted link is not independently verified; no press coverage claimed'}
@router.get('/press/evidence/{project}')
def list_evidence(project:str,authorization:str|None=Header(None)):
    authz(authorization,project,'read')
    with Session() as db:
        rows=db.query(Evidence).filter_by(project=project).limit(100).all()
        return [{'id':r.id,'headline':r.headline,'source_url':r.source_url,'status':r.status,'notes':r.notes} for r in rows]
class EvidenceReview(BaseModel):
    project:str=Field(pattern='^(standalone|noveam|noveomediater)$')
    status:str=Field(pattern='^(verified_by_reviewer|rejected)$')
@router.post('/press/evidence/{evidence_id}/review')
def review_evidence(evidence_id:str,body:EvidenceReview,authorization:str|None=Header(None)):
    authz(authorization,body.project,'review')
    with Session.begin() as db:
        r=db.get(Evidence,evidence_id)
        if not r or r.project!=body.project: raise HTTPException(404,'Evidence not found')
        r.status=body.status
    return {'id':evidence_id,'status':body.status,'verification':'manual reviewer assertion; no automated source validation'}
@router.get('/qa/report/{project}')
def qa_report(project:str,authorization:str|None=Header(None)):
    authz(authorization,project,'read')
    # Legacy QA records are not project-scoped; do not leak them across projects.
    if project!='standalone': return {'project':project,'runs':[],'note':'No project-scoped QA runs yet'}
    with Session() as db:
        rows=db.query(Record).filter(Record.kind.in_(['qa','v07_qa'])).order_by(Record.created_at.desc()).limit(30).all()
        return {'project':project,'runs':[{'id':r.id,'result':json.loads(r.result_json)} for r in rows]}
class AIRequest(BaseModel):
    project:str=Field(pattern='^(standalone|noveam|noveomediater)$')
    bot:str=Field(pattern='^(digital-marketing|digital-branding|public-relations|press-coverage|devbot|testbot)$')
    prompt:str=Field(min_length=3,max_length=2000)
@router.post('/ai/local-draft')
async def local_draft(body:AIRequest,authorization:str|None=Header(None)):
    authz(authorization,body.project,'draft')
    if os.getenv('NOVIOKRO_V08_ENABLE_LOCAL_AI','false').lower()!='true': raise HTTPException(403,'Local AI disabled')
    # No user-controlled URLs. Fixed local service only; no redirects or outbound publication.
    model=os.getenv('NOVIOKRO_V08_OLLAMA_MODEL','').strip()
    if not model: raise HTTPException(503,'Configure local model name')
    try:
        async with httpx.AsyncClient(timeout=30,follow_redirects=False,trust_env=False) as client:
            response=await client.post('http://127.0.0.1:11434/api/generate',json={'model':model,'prompt':f'Provide a draft for human review. Never invent facts or press coverage. Bot: {body.bot}. Task: {body.prompt}','stream':False})
            response.raise_for_status()
            answer=response.json().get('response','')
    except (httpx.HTTPError,ValueError): raise HTTPException(502,'Local model unavailable')
    return {'project':body.project,'bot':body.bot,'draft':answer[:12000],'status':'needs_human_review','source':'operator-configured local Ollama; not fact-checked'}
