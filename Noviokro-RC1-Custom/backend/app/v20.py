"""Admin-only release checklist for the standalone release candidate."""

from fastapi import APIRouter, Depends, Header, Response

from .v12 import admin

router = APIRouter(prefix="/api/v2", tags=["Release readiness"])


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    admin(x_admin_key)


@router.get("/release-readiness", dependencies=[Depends(require_admin)])
def release_readiness(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {
        "release": "2.0.0-rc.1",
        "production_ready": False,
        "checks": {
            "backend_regression": "run_in_ci",
            "react_build": "run_in_ci",
            "docker_compose_config": "run_in_ci",
            "postgresql_persistence": "run_in_ci",
            "docker_runtime": "requires_verification",
            "browser_e2e": "requires_verification",
            "load_test": "requires_verification",
            "independent_security_review": "requires_verification",
        },
    }
