"""Additive v0.3 endpoints. Original v0.2 endpoints remain unchanged."""
import os
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import httpx

router = APIRouter(prefix="/api/v1/next", tags=["v0.3 additive features"])
Base = declarative_base()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./noviokro-dev.db")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
Session = sessionmaker(bind=engine)

class Audit(Base):
    __tablename__ = "noviokro_v03_audit"
    id = Column(String(36), primary_key=True)
    event = Column(String(100), nullable=False)
    detail = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Approval(Base):
    __tablename__ = "noviokro_v03_approvals"
    id = Column(String(36), primary_key=True)
    bot_id = Column(String(36), nullable=False)
    instruction = Column(Text, nullable=False)
    state = Column(String(32), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ModelConfig(Base):
    __tablename__ = "noviokro_v03_models"
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    provider = Column(String(32), nullable=False)
    model = Column(String(128), nullable=False)

# No automatic schema changes to any existing table. New tables only.
def initialize_v03():
    Base.metadata.create_all(engine)

def require_admin(key):
    configured = os.getenv("NOVIOKRO_ADMIN_KEY", "")
    if not configured or key != configured:
        raise HTTPException(401, "Unauthorized")

class ApprovalRequest(BaseModel):
    bot_id: str = Field(min_length=1, max_length=36)
    instruction: str = Field(min_length=1, max_length=4000)

class ModelRegistration(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    provider: str = Field(pattern="^ollama$")
    model: str = Field(pattern=r"^[a-zA-Z0-9_.:/-]{1,128}$")

class Prompt(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)

@router.get("/health")
def health():
    return {"version":"0.3.0", "status":"ok", "execution":"approval-only"}

@router.post("/approvals", status_code=201)
def request_approval(body: ApprovalRequest, x_admin_key: str | None = Header(None)):
    require_admin(x_admin_key)
    from .main import BOTS
    if body.bot_id not in BOTS:
        raise HTTPException(404, "Bot not found")
    ident = str(uuid4())
    with Session.begin() as db:
        db.add(Approval(id=ident, bot_id=body.bot_id, instruction=body.instruction, state="pending"))
        db.add(Audit(id=str(uuid4()), event="approval_requested", detail=ident))
    return {"id":ident,"state":"pending","bot_id":body.bot_id}

@router.get("/approvals")
def list_approvals(x_admin_key: str | None = Header(None)):
    require_admin(x_admin_key)
    with Session() as db:
        return [{"id":a.id,"bot_id":a.bot_id,"state":a.state,"instruction":a.instruction} for a in db.query(Approval).order_by(Approval.created_at.desc()).limit(100)]

@router.post("/approvals/{approval_id}/{decision}")
def decide(approval_id: str, decision: str, x_admin_key: str | None = Header(None)):
    require_admin(x_admin_key)
    if decision not in ("approve", "reject"):
        raise HTTPException(422,"Expected approve or reject")
    with Session.begin() as db:
        record = db.get(Approval, approval_id)
        if not record: raise HTTPException(404,"Not found")
        if record.state != "pending": raise HTTPException(409,"Already decided")
        record.state = "approved" if decision == "approve" else "rejected"
        db.add(Audit(id=str(uuid4()), event="approval_"+decision, detail=approval_id))
        state = record.state
    # Approval NEVER invokes a tool or model automatically.
    return {"id":approval_id,"state":state,"executed":False}

@router.post("/models", status_code=201)
def register_model(body: ModelRegistration, x_admin_key: str | None = Header(None)):
    require_admin(x_admin_key)
    ident = str(uuid4())
    with Session.begin() as db:
        db.add(ModelConfig(id=ident, **body.model_dump()))
        db.add(Audit(id=str(uuid4()),event="model_registered",detail=ident))
    return {"id":ident,**body.model_dump()}

@router.get("/models")
def list_models(x_admin_key: str | None = Header(None)):
    require_admin(x_admin_key)
    with Session() as db:
        return [{"id":m.id,"name":m.name,"provider":m.provider,"model":m.model} for m in db.query(ModelConfig).all()]

@router.post("/models/{model_id}/generate")
async def generate(model_id: str, body: Prompt, x_admin_key: str | None = Header(None)):
    require_admin(x_admin_key)
    if os.getenv("NOVIOKRO_ENABLE_LOCAL_AI") != "true":
        raise HTTPException(403,"Local inference disabled by default")
    with Session() as db:
        config = db.get(ModelConfig, model_id)
        if not config: raise HTTPException(404,"Model not found")
        model_name = config.model
    # Fixed local endpoint: no user-supplied network destinations.
    try:
        async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
            response = await client.post("http://ollama:11434/api/generate", json={"model":model_name,"prompt":body.prompt,"stream":False})
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502,"Local model service unavailable")
    return {"model":model_name,"response":str(data.get("response", ""))[:30000]}

@router.get("/audit")
def audit(x_admin_key: str | None = Header(None)):
    require_admin(x_admin_key)
    with Session() as db:
        return [{"event":a.event,"detail":a.detail,"created_at":a.created_at.isoformat() if a.created_at else None} for a in db.query(Audit).order_by(Audit.created_at.desc()).limit(100)]
