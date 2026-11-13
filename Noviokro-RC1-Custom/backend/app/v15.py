"""Read-only staging diagnostics, no live project integration or secret exposure."""
import os
from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import text
from .v12 import admin
from .v14 import engine

router = APIRouter(prefix='/api/v1/v15', tags=['v1.5 staging diagnostics'])

@router.get('/status')
def staging_status(x_admin_key: str | None = Header(default=None)):
    admin(x_admin_key)
    return {
        'release': '1.5.0',
        'scope': 'standalone-staging',
        'telemetry_enabled': os.getenv('NOVIOKRO_V14_ENABLE_TELEMETRY') == '1',
        'db_rate_limit_enabled': os.getenv('NOVIOKRO_V14_ENABLE_DB_RATE_LIMIT') == '1',
        'proxy_enabled': os.getenv('NOVIOKRO_V12_ENABLE_PROXY') == '1',
        'production_ready': False,
        'external_integrations': 'not configured by this release',
    }

@router.get('/traffic-summary')
def traffic_summary(x_admin_key: str | None = Header(default=None)):
    admin(x_admin_key)
    if os.getenv('NOVIOKRO_V14_ENABLE_TELEMETRY') != '1':
        return {'project':'standalone','enabled':False,'routes':[]}
    with engine().connect() as conn:
        rows = conn.execute(text('''SELECT route, COUNT(*) AS requests,
            SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) AS server_errors,
            SUM(CASE WHEN status_code = 429 THEN 1 ELSE 0 END) AS rate_limited,
            AVG(latency_ms) AS avg_latency_ms
            FROM v14_traffic WHERE project = :project GROUP BY route ORDER BY route LIMIT 100'''), {'project':'standalone'}).mappings().all()
    return {'project':'standalone','enabled':True,'routes':[
        {'route':r['route'],'requests':int(r['requests']), 'server_errors':int(r['server_errors']),
         'rate_limited':int(r['rate_limited']), 'avg_latency_ms':round(float(r['avg_latency_ms']),2)} for r in rows]}
