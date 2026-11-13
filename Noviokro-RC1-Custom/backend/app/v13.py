"""Additive local monitoring and audit API. Does not intercept legacy gateway traffic."""
import json
import os
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from .v12 import admin

router = APIRouter(prefix='/api/v1/v13', tags=['v1.3 monitoring and audit'])


def engine():
    url = os.getenv('NOVIOKRO_V13_DATABASE_URL') or os.getenv('NOVIOKRO_V12_DATABASE_URL', 'sqlite:///./noviokro_v13_local.db')
    db = create_engine(url, pool_pre_ping=True)
    with db.begin() as conn:
        conn.execute(text('CREATE TABLE IF NOT EXISTS v13_observations (id VARCHAR(48) PRIMARY KEY, project VARCHAR(40) NOT NULL, route VARCHAR(64) NOT NULL, status_code INTEGER NOT NULL, latency_ms FLOAT NOT NULL, recorded_at VARCHAR(40) NOT NULL)'))
        conn.execute(text('CREATE TABLE IF NOT EXISTS v13_audit (id VARCHAR(48) PRIMARY KEY, action VARCHAR(64) NOT NULL, project VARCHAR(40) NOT NULL, details TEXT NOT NULL, recorded_at VARCHAR(40) NOT NULL)'))
    return db


class Observation(BaseModel):
    project: str = Field(pattern=r'^[a-z0-9_-]{1,40}$')
    route: str = Field(pattern=r'^[a-z0-9_-]{1,64}$')
    status_code: int = Field(ge=100, le=599)
    latency_ms: float = Field(ge=0, le=600000, allow_inf_nan=False)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def record_audit(conn, action, project, details):
    from uuid import uuid4
    conn.execute(text('INSERT INTO v13_audit (id,action,project,details,recorded_at) VALUES (:id,:action,:project,:details,:recorded_at)'), dict(id=uuid4().hex, action=action, project=project, details=json.dumps(details, sort_keys=True), recorded_at=stamp()))


@router.post('/observations', status_code=201)
def submit_observation(payload: Observation, x_admin_key: str | None = Header(default=None)):
    """Accept operator-submitted staging snapshots; does not probe live services."""
    from uuid import uuid4
    admin(x_admin_key)
    entry = dict(id=uuid4().hex, **payload.model_dump(), recorded_at=stamp())
    with engine().begin() as conn:
        conn.execute(text('INSERT INTO v13_observations (id,project,route,status_code,latency_ms,recorded_at) VALUES (:id,:project,:route,:status_code,:latency_ms,:recorded_at)'), entry)
        record_audit(conn, 'observation.created', payload.project, {'observation_id': entry['id'], 'route': payload.route})
    return entry


@router.get('/monitoring/{project}')
def monitoring(project: str, limit: int = Query(default=100, ge=1, le=500), x_admin_key: str | None = Header(default=None)):
    admin(x_admin_key)
    with engine().connect() as conn:
        rows = conn.execute(text('SELECT id,project,route,status_code,latency_ms,recorded_at FROM v13_observations WHERE project=:project ORDER BY recorded_at DESC,id DESC LIMIT :limit'), {'project':project, 'limit':limit}).mappings().all()
    observations = [dict(row) for row in rows]
    total = len(observations)
    return {'project':project, 'sample_count':total, 'error_count':sum(row['status_code']>=500 for row in observations), 'average_latency_ms':round(sum(row['latency_ms'] for row in observations)/total,2) if total else None, 'observations':observations, 'note':'Operator-submitted snapshots only; no live traffic capture. Metrics cover the returned sample.'}


@router.get('/audit/{project}')
def audit(project: str, limit: int = Query(default=100, ge=1, le=500), x_admin_key: str | None = Header(default=None)):
    admin(x_admin_key)
    with engine().connect() as conn:
        rows = conn.execute(text('SELECT id,action,project,details,recorded_at FROM v13_audit WHERE project=:project ORDER BY recorded_at DESC,id DESC LIMIT :limit'), {'project':project,'limit':limit}).mappings().all()
    return {'events':[{**dict(row), 'details':json.loads(row['details'])} for row in rows]}
