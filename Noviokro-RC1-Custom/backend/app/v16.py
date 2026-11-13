"""v1.6 additive staging preflight diagnostics; no live integration."""
import os
from fastapi import APIRouter, Header
from .v12 import admin
router = APIRouter(prefix='/api/v1/v16', tags=['v1.6 staging verification'])
@router.get('/preflight')
def preflight(x_admin_key: str | None = Header(default=None)):
    admin(x_admin_key)
    flags = {
        'proxy_enabled': os.getenv('NOVIOKRO_V12_ENABLE_PROXY') == '1',
        'telemetry_enabled': os.getenv('NOVIOKRO_V14_ENABLE_TELEMETRY') == '1',
        'database_rate_limit_enabled': os.getenv('NOVIOKRO_V14_ENABLE_DB_RATE_LIMIT') == '1',
    }
    return {'release': '1.6.0', 'environment': 'standalone-staging', 'flags': flags,
            'production_ready': False,
            'checks_remaining': ['real PostgreSQL integration', 'Docker startup',
                                 'browser E2E', 'load test', 'security review']}
