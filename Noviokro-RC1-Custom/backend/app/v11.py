"""Additive local gateway diagnostics and safe operator-owned route validation."""
import os
from urllib.parse import urlsplit
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
import httpx

router = APIRouter(prefix='/api/v1/v11', tags=['v1.1 Gateway Foundation'])


def require_admin(key):
    expected = os.getenv('NOVIOKRO_ADMIN_KEY', '')
    if not expected or key != expected:
        raise HTTPException(401, 'Unauthorized')


class CheckRequest(BaseModel):
    upstream: str = Field(pattern=r'^[a-z0-9_-]{1,64}$')


def configured_upstream(name):
    value = os.getenv('UPSTREAM_' + name.upper(), '').rstrip('/')
    parsed = urlsplit(value)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise HTTPException(400, 'Upstream must be explicitly configured by operator')
    if parsed.scheme != 'https' and os.getenv('NOVIOKRO_ALLOW_HTTP_STAGING') != '1':
        raise HTTPException(400, 'HTTPS required; local HTTP staging requires explicit opt-in')
    return value


@router.get('/gateway/configuration')
def configuration(x_admin_key: str | None = Header(default=None)):
    require_admin(x_admin_key)
    names = sorted(k[9:].lower() for k in os.environ if k.startswith('UPSTREAM_') and k[9:])
    return {'configured_upstream_names': names, 'health_checks_enabled': os.getenv('NOVIOKRO_ENABLE_STAGING_CHECKS') == '1', 'live_integrations_enabled': False}


@router.post('/gateway/staging-health')
async def staging_health(payload: CheckRequest, x_admin_key: str | None = Header(default=None)):
    require_admin(x_admin_key)
    if os.getenv('NOVIOKRO_ENABLE_STAGING_CHECKS') != '1':
        raise HTTPException(403, 'Staging checks disabled')
    base = configured_upstream(payload.upstream)
    # No user-controlled URL, path, query, redirects or credential forwarding.
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(3.0), follow_redirects=False, trust_env=False) as client:
            result = await client.get(base + '/health', headers={'Accept': 'application/json'})
    except httpx.RequestError:
        raise HTTPException(502, 'Configured staging upstream unavailable')
    return {'upstream': payload.upstream, 'status_code': result.status_code, 'healthy': 200 <= result.status_code < 300}
