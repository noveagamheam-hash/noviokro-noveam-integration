"""Opt-in staging telemetry and database-backed per-route minute limits.
No request bodies, credentials, query strings or upstream hostnames are stored.
"""
import os
import re
import time
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from .v12 import admin

router = APIRouter(prefix='/api/v1/v14', tags=['v1.4 staging telemetry'])
ROUTE_RE = re.compile(r'^/api/v1/v12/proxy/([a-z0-9_-]{1,64})(?:/|$)')

def engine():
    url = os.getenv('NOVIOKRO_V14_DATABASE_URL') or os.getenv('NOVIOKRO_V13_DATABASE_URL') or os.getenv('NOVIOKRO_V12_DATABASE_URL', 'sqlite:///./noviokro_v14_local.db')
    db = create_engine(url, pool_pre_ping=True)
    with db.begin() as conn:
        conn.execute(text('CREATE TABLE IF NOT EXISTS v14_traffic (id VARCHAR(48) PRIMARY KEY, project VARCHAR(40) NOT NULL, route VARCHAR(64) NOT NULL, status_code INTEGER NOT NULL, latency_ms FLOAT NOT NULL, recorded_at VARCHAR(40) NOT NULL)'))
        conn.execute(text('CREATE TABLE IF NOT EXISTS v14_limits (route VARCHAR(64) NOT NULL, bucket BIGINT NOT NULL, count INTEGER NOT NULL, PRIMARY KEY(route,bucket))'))
    return db

def limit_request(db, route, limit):
    """Atomic conditional increment, shared across workers using the same DB."""
    bucket = int(time.time() // 60)
    with db.begin() as conn:
        conn.execute(text('INSERT INTO v14_limits (route,bucket,count) VALUES (:route,:bucket,0) ON CONFLICT (route,bucket) DO NOTHING'), {'route':route,'bucket':bucket})
        changed = conn.execute(text('UPDATE v14_limits SET count=count+1 WHERE route=:route AND bucket=:bucket AND count < :limit'), {'route':route,'bucket':bucket,'limit':limit})
        return changed.rowcount == 1

async def telemetry_middleware(request: Request, call_next):
    match = ROUTE_RE.match(request.url.path)
    if not match or os.getenv('NOVIOKRO_V14_ENABLE_TELEMETRY') != '1':
        return await call_next(request)
    route = match.group(1)
    start = time.perf_counter()
    db = engine()
    status = 500
    try:
        if os.getenv('NOVIOKRO_V14_ENABLE_DB_RATE_LIMIT') == '1':
            # Fail closed on malformed configuration.
            try:
                limit = int(os.getenv('NOVIOKRO_V14_RPM', '30'))
            except ValueError:
                return JSONResponse({'detail':'Invalid rate-limit configuration'}, status_code=503)
            if not 1 <= limit <= 10000:
                return JSONResponse({'detail':'Invalid rate-limit configuration'}, status_code=503)
            # Only authorized calls consume capacity; legacy handler still verifies auth.
            from .v12 import admin
            try:
                admin(request.headers.get('x-admin-key'))
            except HTTPException:
                return await call_next(request)
            if not limit_request(db, route, limit):
                status = 429
                return JSONResponse({'detail':'Staging database rate limit exceeded'}, status_code=429, headers={'Retry-After':'60'})
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        # Telemetry failures must not leak credentials or request data. They are not silently ignored.
        with db.begin() as conn:
            conn.execute(text('INSERT INTO v14_traffic (id,project,route,status_code,latency_ms,recorded_at) VALUES (:id,:project,:route,:status_code,:latency_ms,:recorded_at)'), {
                'id':uuid4().hex, 'project':'standalone', 'route':route, 'status_code':status,
                'latency_ms':round((time.perf_counter()-start)*1000,3),
                'recorded_at':datetime.now(timezone.utc).isoformat()})

@router.get('/traffic/{project}')
def traffic(project: str, x_admin_key: str | None = Header(default=None)):
    admin(x_admin_key)
    if project != 'standalone':
        raise HTTPException(404, 'Only standalone staging telemetry is supported')
    with engine().connect() as conn:
        rows = conn.execute(text('SELECT route,status_code,latency_ms,recorded_at FROM v14_traffic WHERE project=:project ORDER BY recorded_at DESC LIMIT 100'), {'project':project}).mappings().all()
    items = [dict(row) for row in rows]
    return {'project':project, 'sample_count':len(items), 'error_count':sum(x['status_code']>=500 for x in items), 'observations':items, 'note':'Last 100 staging proxy requests only; enabled by operator.'}
