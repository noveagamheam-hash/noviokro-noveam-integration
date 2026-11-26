"""Read-only integration discovery for operator-configured services."""
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit
from uuid import uuid4
import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, String, Text
from .extensions import Base, Session, engine, require_admin
from .catalog import openapi_endpoints

router = APIRouter(prefix="/api/v1/integrations", tags=["v0.4 integrations"])

class Discovery(Base):
    __tablename__ = "noviokro_v04_discoveries"
    id = Column(String(36), primary_key=True)
    project = Column(String(32), nullable=False)
    service = Column(String(64), nullable=False)
    title = Column(String(200), nullable=False)
    spec_version = Column(String(30), nullable=False)
    endpoints_json = Column(Text, nullable=False)
    discovered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

# Explicit operator-owned addresses; no user-supplied URLs or arbitrary targets.
# For Docker, set NOVIOKRO_SERVICE_NOVEAM_BACKEND=http://host.docker.internal:PORT
# and NOVIOKRO_SERVICE_NOVEOMEDIATER_BACKEND=... to trusted staging targets only.
PROJECTS = {"noveam", "noveomediater"}
SERVICE_NAME = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
SAFE_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}
CUSTOM_FORMAT = "noviokro-api/1"


class CustomRoute(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    method: str
    path: str = Field(pattern=r"^/[^/][^?#]*$", max_length=500)
    query: list[str] = Field(default_factory=list)
    summary: str = Field(default="", max_length=300)


class NoveamCatalog(BaseModel):
    format: str
    app: str
    routes: list[CustomRoute] = Field(max_length=2000)


def noveam_endpoints(spec):
    try:
        catalog = NoveamCatalog.model_validate(spec)
    except ValueError as exc:
        raise HTTPException(422, "Invalid NOVEAM route catalog") from exc
    if catalog.format != CUSTOM_FORMAT or catalog.app != "noveam":
        raise HTTPException(422, "Expected a NOVEAM noviokro-api/1 catalog")
    endpoints = []
    route_ids = set()
    for route in catalog.routes:
        method = route.method.lower()
        if method not in SAFE_METHODS or route.id in route_ids:
            raise HTTPException(422, "Invalid method or duplicate route ID in NOVEAM catalog")
        route_ids.add(route.id)
        endpoints.append({**route.model_dump(), "method": method.upper()})
    return endpoints

class DiscoveryRequest(BaseModel):
    project: str = Field(pattern=r"^(noveam|noveomediater)$")
    service: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")


def operator_target(project: str, service: str):
    key = f"NOVIOKRO_SERVICE_{project}_{service}".upper()
    raw = os.getenv(key, "").rstrip("/")
    parsed = urlsplit(raw)
    if not raw or parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise HTTPException(400, "Trusted staging service is not configured")
    # Operator must restrict DNS and network access at deployment time.
    return raw

@router.get("/projects")
def projects(x_admin_key: str | None = Header(None)):
    require_admin(x_admin_key)
    return {"projects": sorted(PROJECTS), "mode": "read-only", "existing_routes_modified": False}

@router.post("/discover", status_code=201)
async def discover(body: DiscoveryRequest, x_admin_key: str | None = Header(None)):
    require_admin(x_admin_key)
    base = operator_target(body.project, body.service)
    custom = body.project == "noveam"
    catalog_path = "/api.json" if custom else "/openapi.json"
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=False, trust_env=False) as client:
            response = await client.get(base + catalog_path, headers={"Accept": "application/json"})
            # Native NOVEAM FastAPI deployments expose OpenAPI rather than the
            # separately hosted frontend's custom catalog. Only a missing custom
            # catalog permits fallback; authorization/outages stay visible.
            if custom and response.status_code == 404:
                catalog_path = "/openapi.json"
                response = await client.get(base + catalog_path, headers={"Accept": "application/json"})
            response.raise_for_status()
            if len(response.content) > 2_000_000:
                raise HTTPException(413, "API catalog too large")
            spec = response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, f"Unable to retrieve valid JSON from {catalog_path}")
    if custom and catalog_path == "/api.json":
        endpoints = noveam_endpoints(spec)
        return save_discovery(body, "NOVEAM", CUSTOM_FORMAT, endpoints)
    if custom:
        try:
            endpoints = openapi_endpoints(spec)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return save_discovery(body, "NOVEAM", spec["openapi"], endpoints)
    if not isinstance(spec, dict) or not isinstance(spec.get("paths"), dict) or not isinstance(spec.get("openapi"), str):
        raise HTTPException(422, "Expected OpenAPI 3 document")
    endpoints = []
    for path, methods in list(spec["paths"].items())[:1000]:
        if not isinstance(path, str) or not path.startswith("/") or not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.lower() in SAFE_METHODS and isinstance(operation, dict):
                endpoints.append({"method": method.upper(), "path": path[:500], "summary": str(operation.get("summary", ""))[:300]})
                if len(endpoints) >= 2000:
                    break
        if len(endpoints) >= 2000:
            break
    return save_discovery(body, str(spec.get("info", {}).get("title", "API")), spec["openapi"], endpoints)


def save_discovery(body, title, version, endpoints):
    import json
    ident = str(uuid4())
    with Session.begin() as db:
        db.add(Discovery(id=ident, project=body.project, service=body.service,
                         title=title[:200], spec_version=version[:30], endpoints_json=json.dumps(endpoints)))
    return {"id": ident, "project": body.project, "service": body.service, "endpoint_count": len(endpoints), "mode": "read-only"}

@router.get("/discoveries")
def discoveries(project: str | None = None, x_admin_key: str | None = Header(None)):
    require_admin(x_admin_key)
    if project is not None and project not in PROJECTS:
        raise HTTPException(422, "Unknown project")
    import json
    with Session() as db:
        query = db.query(Discovery)
        if project:
            query = query.filter(Discovery.project == project)
        rows = query.order_by(Discovery.discovered_at.desc()).limit(100).all()
        return [{"id": x.id, "project": x.project, "service": x.service, "title": x.title,
                 "spec_version": x.spec_version, "endpoints": json.loads(x.endpoints_json),
                 "discovered_at": x.discovered_at.isoformat() if x.discovered_at else None} for x in rows]

@router.get("/health/{project}/{service}")
async def service_health(project: str, service: str, x_admin_key: str | None = Header(None)):
    require_admin(x_admin_key)
    if project not in PROJECTS or not SERVICE_NAME.fullmatch(service):
        raise HTTPException(422, "Unknown project or invalid service")
    base = operator_target(project, service)
    probe_path = "/api.json" if project == "noveam" else "/health"
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=False, trust_env=False) as client:
            response = await client.get(base + probe_path)
            if project == "noveam" and response.status_code == 404:
                probe_path = "/openapi.json"
                response = await client.get(base + probe_path)
        return {"project": project, "service": service, "upstream_status": response.status_code,
                "reachable": True, "available": response.is_success, "probe_path": probe_path}
    except httpx.RequestError:
        return {"project": project, "service": service, "reachable": False}


@router.get("/noveam/professional/categories")
async def noveam_professional_categories(x_admin_key: str | None = Header(None)):
    require_admin(x_admin_key)
    base = operator_target("noveam", "backend")
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False, trust_env=False) as client:
            response = await client.get(
                base + "/api/professional/categories",
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "Unable to retrieve NOVEAM professional categories") from exc


def initialize_v04():
    Base.metadata.create_all(engine, tables=[Discovery.__table__])

@router.get('/noveam/routing')
def noveam_routing_status(x_admin_key: str | None = Header(None)):
    require_admin(x_admin_key)
    from .noveam_gateway_contract import backend_origin
    try:
        backend = backend_origin(os.getenv('NOVIOKRO_SERVICE_NOVEAM_BACKEND', ''))
    except ValueError:
        backend = None
    return {'enabled': os.getenv('NOVIOKRO_NOVEAM_GATEWAY_ENABLED') == '1',
            'backend': backend, 'http_prefix': '/noveam/api',
            'user_auth': 'forwarded to NOVEAM', 'websocket_proxy': False}
