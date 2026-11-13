import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
READINESS = "/api/v2/release-readiness"


@pytest.mark.parametrize("key", [None, "incorrect"])
def test_release_readiness_requires_admin(monkeypatch, key):
    monkeypatch.setenv("NOVIOKRO_ADMIN_KEY", "rc1-test-admin")
    headers = {"x-admin-key": key} if key else {}
    assert client.get(READINESS, headers=headers).status_code == 401


def test_release_readiness_is_a_static_checklist(monkeypatch):
    secret = "rc1-test-admin"
    monkeypatch.setenv("NOVIOKRO_ADMIN_KEY", secret)
    monkeypatch.setenv("NOVIOKRO_V12_ENABLE_PROXY", "1")
    response = client.get(READINESS, headers={"x-admin-key": secret})
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert secret not in response.text
    result = response.json()
    assert result["release"] == "2.0.0-rc.1"
    assert result["production_ready"] is False
    assert result["checks"]["postgresql_persistence"] == "run_in_ci"
    assert result["checks"]["browser_e2e"] == "requires_verification"


def test_release_readiness_coexists_with_legacy_routes():
    paths = app.openapi()["paths"]
    for path, method in [
        ("/health", "get"),
        ("/api/v1/routes", "post"),
        ("/api/v1/bots/{bot_id}/execute", "post"),
        ("/gateway/{route_name}/{path}", "get"),
        ("/api/v1/v19/integration-readiness", "get"),
        (READINESS, "get"),
    ]:
        assert method in paths[path]
