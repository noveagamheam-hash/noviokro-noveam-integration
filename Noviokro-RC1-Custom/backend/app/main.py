import os
import time
from urllib.parse import urlsplit
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
import httpx

app = FastAPI(title='Noviokro AI API Manager', version='0.2.0')
ADMIN_KEY = os.getenv('NOVIOKRO_ADMIN_KEY', '')
# Explicit, operator-controlled upstream destinations; no arbitrary user URLs.
UPSTREAMS = {k[9:].lower(): v.rstrip('/') for k, v in os.environ.items() if k.startswith('UPSTREAM_') and k[9:]}
ROUTES: dict[str, dict] = {}

class RouteIn(BaseModel):
    name: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    upstream: str = Field(pattern=r'^[a-z0-9_-]{1,64}$')
    prefix: str = Field(pattern=r'^/[a-zA-Z0-9_/-]*$', max_length=128)

def authorize(key: str | None):
    if not ADMIN_KEY or key != ADMIN_KEY:
        raise HTTPException(401, 'Unauthorized')

@app.get('/health')
def health():
    return {'status':'ok', 'service':'noviokro-ai-api-manager', 'version':'0.2.0'}

@app.get('/api/v1/capabilities')
def capabilities(x_admin_key: str | None = Header(default=None)):
    authorize(x_admin_key)
    return {'gateway':'http-proxy', 'ai':'adapter-planned', 'gui':'static', 'nui':'planned', 'multi_bot':'registry-and-approval-requests'}

@app.get('/api/v1/routes')
def list_routes(x_admin_key: str | None = Header(default=None)):
    authorize(x_admin_key)
    return {'routes':list(ROUTES.values())}

@app.post('/api/v1/routes', status_code=201)
def add_route(data: RouteIn, x_admin_key: str | None = Header(default=None)):
    authorize(x_admin_key)
    if data.upstream not in UPSTREAMS:
        raise HTTPException(400, 'Upstream must be configured by operator')
    if data.prefix in (r['prefix'] for r in ROUTES.values()):
        raise HTTPException(409, 'Prefix already registered')
    if data.name in ROUTES:
        raise HTTPException(409, 'Name already registered')
    route = data.model_dump()
    ROUTES[data.name] = route
    return route

@app.api_route('/gateway/{route_name}/{path:path}', methods=['GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'])
async def proxy(route_name: str, path: str, request: Request, x_admin_key: str | None = Header(default=None)):
    # Local development only: gateway requests require same admin key.
    authorize(x_admin_key)
    route = ROUTES.get(route_name)
    if route is None:
        raise HTTPException(404, 'Route not found')
    base = UPSTREAMS[route['upstream']]
    parsed = urlsplit(base)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(500, 'Invalid operator upstream')
    target = f"{base}/{path}"
    if request.url.query:
        target += '?' + request.url.query
    blocked = {'host','connection','transfer-encoding','content-length','x-admin-key','authorization','cookie','proxy-authorization'}
    headers = {k:v for k,v in request.headers.items() if k.lower() not in blocked}
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False, trust_env=False) as client:
            res = await client.request(request.method, target, headers=headers, content=await request.body())
    except httpx.RequestError:
        raise HTTPException(502, 'Upstream unavailable')
    response_headers = {k:v for k,v in res.headers.items() if k.lower() not in {'connection','transfer-encoding','content-length','set-cookie','location','content-encoding'}}
    return Response(content=res.content, status_code=res.status_code, headers=response_headers)


# Additive multi-bot registry. Development-only in-memory storage.
from uuid import uuid4
from typing import Literal

BOT_TYPES = {'devbot', 'testbot', 'qabot', 'feedback_taker',
             'suggestion_giver', 'callbot', 'securitybot', 'supportbot',
             'debugbot', 'monitoringbot', 'documentationbot', 'learningbot'}
BOTS: dict[str, dict] = {}
BOT_RUNS: dict[str, dict] = {}
FEEDBACK: dict[str, dict] = {}

class BotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    bot_type: str
    approval_mode: Literal['manual', 'review', 'read'] = 'manual'

class RunCreate(BaseModel):
    instruction: str = Field(min_length=1, max_length=4000)

class FeedbackCreate(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    category: Literal['feedback', 'suggestion', 'issue'] = 'feedback'

@app.get('/api/v1/bot-types')
def bot_types(x_admin_key: str | None = Header(default=None)):
    authorize(x_admin_key)
    return sorted(BOT_TYPES)

@app.post('/api/v1/bots', status_code=201)
def create_bot(bot: BotCreate, x_admin_key: str | None = Header(default=None)):
    authorize(x_admin_key)
    if bot.bot_type not in BOT_TYPES:
        raise HTTPException(422, 'Unknown bot type')
    identifier = str(uuid4())
    BOTS[identifier] = {'id': identifier, **bot.model_dump(), 'enabled': False}
    return BOTS[identifier]

@app.get('/api/v1/bots')
def list_bots(x_admin_key: str | None = Header(default=None)):
    authorize(x_admin_key)
    return list(BOTS.values())

@app.post('/api/v1/bots/{bot_id}/execute', status_code=202)
def request_bot_run(bot_id: str, payload: RunCreate, x_admin_key: str | None = Header(default=None)):
    authorize(x_admin_key)
    if bot_id not in BOTS:
        raise HTTPException(404, 'Bot not found')
    identifier = str(uuid4())
    BOT_RUNS[identifier] = {'id': identifier, 'bot_id': bot_id,
                            'instruction': payload.instruction,
                            'status': 'pending_approval'}
    return BOT_RUNS[identifier]

@app.get('/api/v1/bot-runs/{run_id}')
def get_bot_run(run_id: str, x_admin_key: str | None = Header(default=None)):
    authorize(x_admin_key)
    if run_id not in BOT_RUNS:
        raise HTTPException(404, 'Run not found')
    return BOT_RUNS[run_id]

@app.post('/api/v1/feedback', status_code=201)
def submit_feedback(payload: FeedbackCreate, x_admin_key: str | None = Header(default=None)):
    authorize(x_admin_key)
    identifier = str(uuid4())
    FEEDBACK[identifier] = {'id': identifier, **payload.model_dump(), 'status': 'new'}
    return FEEDBACK[identifier]

@app.get('/api/v1/feedback')
def list_feedback(x_admin_key: str | None = Header(default=None)):
    authorize(x_admin_key)
    return list(FEEDBACK.values())

# v0.3 additive extension; all v0.2 routes retained.
from .extensions import router as v03_router, initialize_v03
initialize_v03()
app.include_router(v03_router)

# v0.4 independent read-only project integration routes.
from .integrations import router as v04_router, initialize_v04
initialize_v04()
app.include_router(v04_router)

# v0.5 standalone additive sandbox endpoints.
from .sandbox_bots import router as v05_router, initialize_v05
initialize_v05()
app.include_router(v05_router)

# v0.6 additive isolated endpoints; previous routes unchanged.
from .v06 import router as v06_router, initialize_v06
initialize_v06()
app.include_router(v06_router)

# v0.7 additive extensions; earlier routes unchanged.
from .v07 import router as v07_router, initialize_v07
initialize_v07()
app.include_router(v07_router)

# v0.8 independent identity, QA report, press evidence and opt-in local AI.
from .v08 import router as v08_router, initialize_v08
initialize_v08()
app.include_router(v08_router)

# v1.0 additive read-only management summary; existing routes unchanged.
from .v10 import router as v10_router
app.include_router(v10_router)

# v1.1 additive gateway diagnostics; existing gateway behavior unchanged.
from .v11 import router as v11_router
app.include_router(v11_router)

# OpenAPI-only fix for FastAPI's multi-method route ID collision.
# Runtime proxy methods and behavior remain unchanged.
from fastapi.openapi.utils import get_openapi

def _v11_openapi():
    if app.openapi_schema is None:
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='Duplicate Operation ID .*proxy_.*')
            schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        path = schema.get('paths', {}).get('/gateway/{route_name}/{path}', {})
        for method, operation in path.items():
            if isinstance(operation, dict) and 'operationId' in operation:
                operation['operationId'] = 'proxy_gateway_' + method
        for method, operation in schema.get('paths', {}).get('/api/v1/v12/proxy/{name}/{path}', {}).items():
            if isinstance(operation, dict) and 'operationId' in operation:
                operation['operationId'] = 'v12_staging_proxy_' + method
        app.openapi_schema = schema
    return app.openapi_schema

app.openapi = _v11_openapi

# v1.2 additive isolated staging gateway; existing routes are untouched.
from .v12 import router as v12_router
app.include_router(v12_router)

# Additive v1.3 monitoring; legacy API endpoints remain unchanged.
from .v13 import router as v13_router
app.include_router(v13_router)

# v1.4 additions: isolated staging instrumentation; existing routes unchanged.
from .v14 import router as v14_router, telemetry_middleware
app.include_router(v14_router)
app.middleware('http')(telemetry_middleware)

# v1.5 isolated read-only staging diagnostics.
from .v15 import router as v15_router
app.include_router(v15_router)

# v1.6 additive authenticated preflight; no modifications to legacy routes.
from .v16 import router as v16_router
app.include_router(v16_router)

from .v17 import router as v17_router
app.include_router(v17_router)

# v1.8 additive read-only security readiness inventory.
from .v18 import router as v18_router
app.include_router(v18_router)

from .v19 import router as v19_router
app.include_router(v19_router)

from .v20 import router as v20_router
app.include_router(v20_router)

# Dedicated NOVEAM user traffic; separate from manager administrative proxies.
from .noveam_gateway import create_noveam_gateway
app.mount("/noveam", create_noveam_gateway())
