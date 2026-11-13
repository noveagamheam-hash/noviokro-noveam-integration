"""v1.8 isolated, authenticated production-readiness security inventory.
No live external checks or credentials returned.
"""
import os
from fastapi import APIRouter, Header
from .v12 import admin

router = APIRouter(prefix="/api/v1/v18", tags=["v1.8 security readiness"])

@router.get("/security-readiness")
def security_readiness(x_admin_key: str | None = Header(default=None)):
    admin(x_admin_key)
    flags = {
        "proxy_enabled": os.getenv("NOVIOKRO_V12_ENABLE_PROXY") == "1",
        "telemetry_enabled": os.getenv("NOVIOKRO_V14_ENABLE_TELEMETRY") == "1",
        "http_staging_opt_in": os.getenv("NOVIOKRO_ALLOW_HTTP_STAGING") == "1",
        "loopback_staging_opt_in": os.getenv("NOVIOKRO_ALLOW_LOOPBACK_STAGING") == "1",
        "postgresql_url_configured": os.getenv("NOVIOKRO_V12_DATABASE_URL", "").startswith(("postgresql://", "postgresql+")),
    }
    return {
        "release": "1.8.0",
        "production_ready": False,
        "configuration": flags,
        "verification": {
            "react_build": "not_verified",
            "docker_startup": "not_verified",
            "postgresql_live": "not_verified",
            "browser_e2e": "not_verified",
            "load_test": "not_verified",
            "external_security_audit": "not_verified",
        },
        "known_risks": [
            "Shared administrator key is not user-scoped RBAC",
            "Staging proxy is not a production-hardened gateway",
            "In-memory fallback rate limiting is not distributed",
            "Live infrastructure checks must run in isolated authorized staging",
        ],
    }
