"""v0.5 standalone sandbox workflows. No code execution, network calls or file writes."""
import os, hmac, json
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

router = APIRouter(prefix='/api/v1/sandbox', tags=['v0.5 isolated bot sandbox'])
Base = declarative_base()
url = os.getenv('DATABASE_URL', 'sqlite:///./noviokro-dev.db')
engine = create_engine(url, pool_pre_ping=True, connect_args={'check_same_thread':False} if url.startswith('sqlite') else {})
Session = sessionmaker(bind=engine)

class Config(Base):
    __tablename__ = 'noviokro_v05_bot_configs'
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    bot_type = Column(String(30), nullable=False)
    enabled = Column(String(5), nullable=False, default='false')
    config_json = Column(Text, nullable=False, default='{}')

class Run(Base):
    __tablename__ = 'noviokro_v05_sandbox_runs'
    id = Column(String(36), primary_key=True)
    bot_id = Column(String(36), nullable=False)
    bot_type = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False)
    result_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda:datetime.now(timezone.utc))

class Event(Base):
    __tablename__ = 'noviokro_v05_audit'
    id = Column(String(36), primary_key=True)
    action = Column(String(60), nullable=False)
    target = Column(String(36), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda:datetime.now(timezone.utc))

def initialize_v05():
    Base.metadata.create_all(engine)

def check_key(key, permission='viewer'):
    admin = os.getenv('NOVIOKRO_ADMIN_KEY','')
    viewer = os.getenv('NOVIOKRO_VIEWER_KEY','')
    if not admin or len(admin) < 16:
        raise HTTPException(503,'Configure a strong NOVIOKRO_ADMIN_KEY (at least 16 characters)')
    if key and hmac.compare_digest(key,admin): return
    if permission == 'viewer' and viewer and len(viewer)>=16 and key and hmac.compare_digest(key,viewer): return
    raise HTTPException(403,'Insufficient permission')

class BotConfigIn(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    bot_type: str = Field(pattern='^(devbot|testbot)$')
    enabled: bool = False
    config: dict = Field(default_factory=dict)

class RunIn(BaseModel):
    # Pure-data workflows, no shell commands or external URLs.
    spec: dict = Field(default_factory=dict)

@router.post('/bots',status_code=201)
def create_bot(body:BotConfigIn,x_admin_key:str|None=Header(None)):
    check_key(x_admin_key,'admin')
    if len(json.dumps(body.config))>8000: raise HTTPException(422,'Configuration too large')
    ident=str(uuid4())
    with Session.begin() as db:
        db.add(Config(id=ident,name=body.name,bot_type=body.bot_type,enabled=str(body.enabled).lower(),config_json=json.dumps(body.config)))
        db.add(Event(id=str(uuid4()),action='bot_created',target=ident))
    return {'id':ident,**body.model_dump()}

@router.get('/bots')
def list_bots(x_admin_key:str|None=Header(None)):
    check_key(x_admin_key)
    with Session() as db:
        return [{'id':b.id,'name':b.name,'bot_type':b.bot_type,'enabled':b.enabled=='true','config':json.loads(b.config_json)} for b in db.query(Config).order_by(Config.name).limit(100)]

@router.patch('/bots/{bot_id}')
def update_bot(bot_id:str,body:BotConfigIn,x_admin_key:str|None=Header(None)):
    check_key(x_admin_key,'admin')
    if len(json.dumps(body.config))>8000: raise HTTPException(422,'Configuration too large')
    with Session.begin() as db:
        b=db.get(Config,bot_id)
        if b is None: raise HTTPException(404,'Bot not found')
        b.name=body.name;b.bot_type=body.bot_type;b.enabled=str(body.enabled).lower();b.config_json=json.dumps(body.config)
        db.add(Event(id=str(uuid4()),action='bot_updated',target=bot_id))
    return {'id':bot_id,**body.model_dump()}

def evaluate(bot_type,spec):
    if bot_type=='testbot':
        cases=spec.get('cases',[])
        if not isinstance(cases,list) or len(cases)>50: raise HTTPException(422,'Expected at most 50 test cases')
        output=[]
        for case in cases:
            if not isinstance(case,dict): raise HTTPException(422,'Invalid test case')
            # Only evaluate provided data. Never fetch URLs or execute arbitrary code.
            actual=case.get('actual_status');expected=case.get('expected_status')
            passed=isinstance(actual,int) and isinstance(expected,int) and actual==expected
            output.append({'name':str(case.get('name','unnamed'))[:100],'passed':passed,'expected_status':expected,'actual_status':actual})
        return {'passed':sum(x['passed'] for x in output),'total':len(output),'cases':output,'mode':'offline_fixture'}
    paths=spec.get('paths',{})
    if not isinstance(paths,dict) or len(paths)>100: raise HTTPException(422,'Expected OpenAPI paths object (max 100)')
    warnings=[]
    for path,methods in paths.items():
        if not isinstance(methods,dict): continue
        for method,op in methods.items():
            if method.lower() not in {'get','post','put','patch','delete'} or not isinstance(op,dict):continue
            if not op.get('operationId'): warnings.append({'path':str(path)[:120],'method':method,'issue':'missing operationId'})
            if not op.get('responses'): warnings.append({'path':str(path)[:120],'method':method,'issue':'missing responses'})
    return {'warnings':warnings[:200],'total_warnings':len(warnings),'mode':'offline_openapi_lint'}

@router.post('/bots/{bot_id}/run',status_code=201)
def run_bot(bot_id:str,body:RunIn,x_admin_key:str|None=Header(None)):
    check_key(x_admin_key,'admin')
    if len(json.dumps(body.spec))>100000:raise HTTPException(422,'Fixture too large')
    with Session.begin() as db:
        bot=db.get(Config,bot_id)
        if bot is None:raise HTTPException(404,'Bot not found')
        if bot.enabled!='true':raise HTTPException(409,'Bot disabled')
        result=evaluate(bot.bot_type,body.spec)
        ident=str(uuid4())
        db.add(Run(id=ident,bot_id=bot_id,bot_type=bot.bot_type,status='completed',result_json=json.dumps(result)))
        db.add(Event(id=str(uuid4()),action='sandbox_run',target=ident))
    return {'id':ident,'bot_id':bot_id,'status':'completed','result':result}

@router.get('/runs')
def list_runs(x_admin_key:str|None=Header(None)):
    check_key(x_admin_key)
    with Session() as db:
        return [{'id':r.id,'bot_id':r.bot_id,'bot_type':r.bot_type,'status':r.status,'result':json.loads(r.result_json)} for r in db.query(Run).order_by(Run.created_at.desc()).limit(100)]

@router.get('/metrics')
def metrics(x_admin_key:str|None=Header(None)):
    check_key(x_admin_key)
    with Session() as db:
        return {'bots':db.query(Config).count(),'runs':db.query(Run).count(),'audit_events':db.query(Event).count(),'scope':'sandbox_only'}
