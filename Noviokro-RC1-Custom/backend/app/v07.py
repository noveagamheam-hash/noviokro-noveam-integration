"""Additive v0.7: isolated marketing bots, role records, staging checks, QA dashboards."""
import os, json, hmac, ipaddress, socket, time
from datetime import datetime, timezone
from urllib.parse import urlsplit
from uuid import uuid4
import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime
from .sandbox_bots import Base, engine, Session
from .v06 import require, Record, QARequest, run_isolated, save

router=APIRouter(prefix='/api/v1/v07',tags=['v0.7 standalone AI-bot extensions'])
class RoleAssignment(Base):
    __tablename__='noviokro_v07_role_assignments'
    id=Column(String(36),primary_key=True)
    principal=Column(String(100),nullable=False)
    project=Column(String(30),nullable=False)
    role=Column(String(30),nullable=False)
    created_at=Column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class MarketingRecord(Base):
    __tablename__='noviokro_v07_marketing_records'
    id=Column(String(36),primary_key=True)
    project=Column(String(30),nullable=False)
    bot=Column(String(40),nullable=False)
    payload_json=Column(Text,nullable=False)
    created_at=Column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
def initialize_v07(): Base.metadata.create_all(engine)
PROJECTS=('standalone','noveam','noveomediater')
BOTS=('digital-marketing','digital-branding','public-relations','press-coverage','feedback','suggestions','devbot','testbot','qabot')
class RoleInput(BaseModel):
    principal:str=Field(min_length=1,max_length=100,pattern=r'^[a-zA-Z0-9_.@-]+$')
    project:str=Field(pattern='^(standalone|noveam|noveomediater)$')
    role:str=Field(pattern='^(viewer|editor|tester|manager|admin)$')
@router.post('/roles',status_code=201)
def add_role(body:RoleInput,authorization:str|None=Header(None)):
    require(authorization,'admin')
    ident=str(uuid4())
    with Session.begin() as db: db.add(RoleAssignment(id=ident,**body.model_dump()))
    return {'id':ident,**body.model_dump()}
@router.get('/roles')
def roles(authorization:str|None=Header(None)):
    require(authorization,'read')
    with Session() as db: return [{'id':r.id,'principal':r.principal,'project':r.project,'role':r.role} for r in db.query(RoleAssignment).limit(200)]
@router.get('/bots/catalog')
def catalog(authorization:str|None=Header(None)):
    require(authorization,'read')
    return {'bots':BOTS,'projects':PROJECTS,'execution':'review-only; no external publication or model inference'}
class MarketingInput(BaseModel):
    project:str=Field(pattern='^(standalone|noveam|noveomediater)$')
    bot:str=Field(pattern='^(digital-marketing|digital-branding|public-relations|press-coverage|feedback|suggestions)$')
    topic:str=Field(min_length=3,max_length=250)
    audience:str=Field(min_length=2,max_length=150)
    objective:str=Field(min_length=3,max_length=250)
    source_urls:list[str]=Field(default_factory=list,max_length=10)
@router.post('/bots/briefs',status_code=201)
def draft_brief(body:MarketingInput,authorization:str|None=Header(None)):
    require(authorization,'execute')
    # Original deterministic brief generator: drafts only; never invents press coverage or metrics.
    result={'project':body.project,'bot':body.bot,'status':'draft_needs_human_review',
      'brief':{'topic':body.topic,'audience':body.audience,'objective':body.objective,
        'steps':['Verify factual claims and permissions','Research audience and relevant channels','Prepare a draft and review tone','Check citations, rights and compliance','Obtain human approval before publication'],
        'measurement':['Reach','Engagement','Qualified inquiries','Verified coverage links'],
        'source_urls':body.source_urls},
      'limitations':'No AI inference, web research, outreach, publication or claimed press coverage performed.'}
    ident=str(uuid4())
    with Session.begin() as db: db.add(MarketingRecord(id=ident,project=body.project,bot=body.bot,payload_json=json.dumps(result)))
    return {'id':ident,**result}
@router.get('/bots/briefs')
def briefs(authorization:str|None=Header(None)):
    require(authorization,'read')
    with Session() as db: return [{'id':r.id,**json.loads(r.payload_json)} for r in db.query(MarketingRecord).order_by(MarketingRecord.created_at.desc()).limit(100)]
@router.post('/qa-runs',status_code=201)
def qa(body:QARequest,authorization:str|None=Header(None)):
    actor=require(authorization,'execute')
    return save('v07_qa',actor,run_isolated('qa',body.model_dump()))
@router.get('/monitoring/summary')
def summary(authorization:str|None=Header(None)):
    require(authorization,'read')
    with Session() as db:
        rows=db.query(Record).order_by(Record.created_at.desc()).limit(100).all()
        return {'total_records':len(rows),'qa_runs':sum(r.kind in ('qa','v07_qa') for r in rows),'monitoring_snapshots':sum(r.kind in ('monitor','staging_health') for r in rows),'source':'stored local results; not live traffic'}
class StagingCheck(BaseModel):
    service:str=Field(min_length=1,max_length=100)
    url:str=Field(max_length=500)
def _approved_url(url):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or parsed.port not in (None,443):
        raise HTTPException(400,'HTTPS on port 443 only')
    allowed=[x.strip().lower() for x in os.getenv('NOVIOKRO_STAGING_HOSTS','').split(',') if x.strip()]
    if parsed.hostname.lower() not in allowed: raise HTTPException(403,'Host not explicitly allowlisted')
    # No outbound requests to private, loopback, reserved or link-local addresses.
    try: resolved=socket.getaddrinfo(parsed.hostname,443,type=socket.SOCK_STREAM)
    except OSError: raise HTTPException(502,'DNS lookup failed')
    addresses={item[4][0] for item in resolved}
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise HTTPException(403,'Non-public upstream address blocked')
    return parsed.hostname,addresses
@router.post('/monitoring/staging-check',status_code=201)
async def staging_check(body:StagingCheck,authorization:str|None=Header(None)):
    actor=require(authorization,'execute')
    if os.getenv('NOVIOKRO_ENABLE_STAGING_CHECKS','false').lower()!='true': raise HTTPException(403,'Staging checks disabled')
    host,ips=_approved_url(body.url)
    # DNS rebinding defense: connect directly to validated address, preserve TLS SNI/Host.
    # Until a pinned-DNS transport is implemented, refuse outbound checks rather than trusting a second resolution.
    raise HTTPException(501,'Safe DNS-pinned staging transport not yet implemented; no request sent')
