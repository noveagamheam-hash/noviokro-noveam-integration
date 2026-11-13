"""v1.2 opt-in, staging-only, persistent route catalog and guarded proxy.
Legacy routes remain unchanged. This is not a production gateway.
"""
import hmac
import ipaddress
import os
import socket
import threading
import time
from collections import defaultdict, deque
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

router = APIRouter(prefix='/api/v1/v12', tags=['v1.2 staging gateway'])
_lock = threading.Lock()
_hits = defaultdict(deque)


def admin(key):
    expected = os.getenv('NOVIOKRO_ADMIN_KEY', '')
    if not expected or not key or not hmac.compare_digest(key, expected):
        raise HTTPException(401, 'Unauthorized')


def db():
    url = os.getenv('NOVIOKRO_V12_DATABASE_URL', 'sqlite:///./noviokro_v12_local.db')
    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE IF NOT EXISTS v12_routes (name VARCHAR(64) PRIMARY KEY, upstream VARCHAR(64) NOT NULL, enabled BOOLEAN NOT NULL DEFAULT FALSE)'))
    return engine


class Route(BaseModel):
    name: str = Field(pattern=r'^[a-z0-9_-]{1,64}$')
    upstream: str = Field(pattern=r'^[a-z0-9_-]{1,64}$')
    enabled: bool = False


def upstream_url(name):
    url = os.getenv('UPSTREAM_' + name.upper(), '')
    parsed = urlsplit(url)
    if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        raise HTTPException(400, 'Invalid operator-configured upstream')
    if parsed.scheme == 'http' and os.getenv('NOVIOKRO_ALLOW_HTTP_STAGING') != '1':
        raise HTTPException(400, 'HTTPS required')
    # Public IP only, except explicit loopback staging opt-in.
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80), type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(400, 'Upstream DNS unavailable')
    ips = {ipaddress.ip_address(entry[4][0]) for entry in addresses}
    if not ips or any(not ip.is_global for ip in ips):
        if not (os.getenv('NOVIOKRO_ALLOW_LOOPBACK_STAGING') == '1' and all(ip.is_loopback for ip in ips)):
            raise HTTPException(403, 'Private or non-public upstream blocked')
    return url.rstrip('/'), parsed.hostname, ips


@router.get('/routes')
def list_routes(x_admin_key: str | None = Header(default=None)):
    admin(x_admin_key)
    with db().connect() as conn:
        rows = conn.execute(text('SELECT name, upstream, enabled FROM v12_routes ORDER BY name')).mappings().all()
    return {'routes': [{**dict(r), 'enabled': bool(r['enabled'])} for r in rows]}


@router.post('/routes', status_code=201)
def create_route(payload: Route, x_admin_key: str | None = Header(default=None)):
    admin(x_admin_key)
    if not os.getenv('UPSTREAM_' + payload.upstream.upper()):
        raise HTTPException(400, 'Upstream not configured')
    engine = db()
    with engine.begin() as conn:
        if conn.execute(text('SELECT name FROM v12_routes WHERE name=:name'), {'name': payload.name}).first():
            raise HTTPException(409, 'Route already exists')
        conn.execute(text('INSERT INTO v12_routes (name, upstream, enabled) VALUES (:name, :upstream, :enabled)'), payload.model_dump())
    return payload.model_dump()


@router.delete('/routes/{name}')
def delete_route(name: str, x_admin_key: str | None = Header(default=None)):
    admin(x_admin_key)
    with db().begin() as conn:
        result = conn.execute(text('DELETE FROM v12_routes WHERE name=:name'), {'name': name})
    if not result.rowcount:
        raise HTTPException(404, 'Route not found')
    return {'deleted': name}


@router.api_route('/proxy/{name}/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
async def staging_proxy(name: str, path: str, request: Request, x_admin_key: str | None = Header(default=None)):
    admin(x_admin_key)
    if os.getenv('NOVIOKRO_V12_ENABLE_PROXY') != '1':
        raise HTTPException(403, 'v1.2 staging proxy disabled')
    with db().connect() as conn:
        route = conn.execute(text('SELECT upstream, enabled FROM v12_routes WHERE name=:name'), {'name': name}).mappings().first()
    if not route or not route['enabled']:
        raise HTTPException(404, 'Enabled route not found')
    if any(segment in ('.', '..') for segment in path.split('/')) or '\\' in path or '%' in path:
        raise HTTPException(400, 'Invalid path')
    now = time.monotonic()
    with _lock:
        q = _hits[name]
        while q and now - q[0] >= 60:
            q.popleft()
        limit = max(1, min(int(os.getenv('NOVIOKRO_V12_RPM', '30')), 10000))
        if len(q) >= limit:
            raise HTTPException(429, 'Staging rate limit exceeded')
        q.append(now)
    base, hostname, ips = upstream_url(route['upstream'])
    # DNS rebinding risk: fail closed for domain names until pinned transport is available.
    if not _is_ip(hostname) or not all(ipaddress.ip_address(hostname) == ip for ip in ips):
        raise HTTPException(403, 'Staging proxy requires an operator-configured IP literal to prevent DNS rebinding')
    blocked = {'host', 'authorization', 'cookie', 'x-admin-key', 'connection', 'content-length', 'transfer-encoding', 'proxy-authorization', 'forwarded', 'x-forwarded-for', 'x-forwarded-host', 'x-forwarded-proto'}
    headers = {k: v for k, v in request.headers.items() if k.lower() not in blocked}
    target = f'{base}/{path}'
    if request.url.query:
        target += '?' + request.url.query
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0), follow_redirects=False, trust_env=False) as client:
            result = await client.request(request.method, target, headers=headers, content=await request.body())
    except httpx.RequestError:
        raise HTTPException(502, 'Staging upstream unavailable')
    response_headers = {k: v for k, v in result.headers.items() if k.lower() not in {'connection', 'content-length', 'content-encoding', 'transfer-encoding', 'set-cookie', 'location'}}
    return Response(result.content, status_code=result.status_code, headers=response_headers)


def _is_ip(host):
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False
