from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

def test_readiness_requires_admin(monkeypatch):
    monkeypatch.setenv("NOVIOKRO_ADMIN_KEY", "test-v17-secret")
    assert client.get("/api/v1/v17/readiness").status_code == 401
    assert client.get("/api/v1/v17/readiness", headers={"x-admin-key":"wrong"}).status_code == 401

def test_readiness_is_conservative(monkeypatch):
    monkeypatch.setenv("NOVIOKRO_ADMIN_KEY", "test-v17-secret")
    monkeypatch.delenv("NOVIOKRO_V12_ENABLE_PROXY", raising=False)
    response = client.get("/api/v1/v17/readiness", headers={"x-admin-key":"test-v17-secret"})
    assert response.status_code == 200
    assert response.json()["production_ready"] is False
    assert response.json()["checks"]["staging_proxy_enabled"] is False
    assert "test-v17-secret" not in response.text

def test_readiness_config_flags(monkeypatch):
    monkeypatch.setenv("NOVIOKRO_ADMIN_KEY", "test-v17-secret")
    monkeypatch.setenv("NOVIOKRO_V12_DATABASE_URL", "postgresql+psycopg://example:secret@localhost/test")
    monkeypatch.setenv("NOVIOKRO_V12_ENABLE_PROXY", "1")
    response = client.get("/api/v1/v17/readiness", headers={"x-admin-key":"test-v17-secret"})
    assert response.json()["checks"]["database_configured"] is True
    assert response.json()["checks"]["staging_proxy_enabled"] is True
    assert "example:secret" not in response.text
