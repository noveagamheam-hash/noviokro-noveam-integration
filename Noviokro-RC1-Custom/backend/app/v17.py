"""v1.7 isolated integration readiness checks. No live network calls."""
import importlib.util
import os
from fastapi import APIRouter, Header
from .v12 import admin
router = APIRouter(prefix="/api/v1/v17", tags=["v1.7 integration readiness"])
@router.get("/readiness")
def readiness(x_admin_key: str | None = Header(default=None)):
    admin(x_admin_key)
    return {
        "release": "1.7.0",
        "production_ready": False,
        "checks": {
            "postgres_driver_installed": importlib.util.find_spec("psycopg") is not None,
            "database_configured": os.getenv("NOVIOKRO_V12_DATABASE_URL", "").startswith(("postgresql://", "postgresql+psycopg://")),
            "staging_proxy_enabled": os.getenv("NOVIOKRO_V12_ENABLE_PROXY") == "1",
            "staging_telemetry_enabled": os.getenv("NOVIOKRO_V14_ENABLE_TELEMETRY") == "1",
        },
        "unverified": ["React production build", "Docker runtime", "real PostgreSQL", "browser E2E", "load testing", "security audit"],
    }
