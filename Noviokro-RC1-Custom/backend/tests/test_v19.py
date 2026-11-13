"""Isolated integration-readiness and PostgreSQL persistence verification."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from app.main import app

client = TestClient(app)
HEADERS = {"x-admin-key": "v19-test-secret"}

def test_v19_requires_admin(monkeypatch):
    monkeypatch.setenv("NOVIOKRO_ADMIN_KEY", "v19-test-secret")
    assert client.get("/api/v1/v19/integration-readiness").status_code == 401
    assert client.get("/api/v1/v19/integration-readiness", headers={"x-admin-key":"wrong"}).status_code == 401

def test_v19_never_claims_live_production(monkeypatch):
    monkeypatch.setenv("NOVIOKRO_ADMIN_KEY", "v19-test-secret")
    monkeypatch.setenv("NOVIOKRO_V12_ENABLE_PROXY", "1")
    response = client.get("/api/v1/v19/integration-readiness", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["production_ready"] is False
    assert data["live_platforms_connected"] is False
    assert data["checks"]["browser_e2e"] == "not_verified"
    assert "v19-test-secret" not in response.text

def test_v19_existing_route_catalog_sqlite(monkeypatch, tmp_path):
    monkeypatch.setenv("NOVIOKRO_ADMIN_KEY", "v19-test-secret")
    monkeypatch.setenv("NOVIOKRO_V12_DATABASE_URL", f"sqlite:///{tmp_path}/routes.db")
    monkeypatch.setenv("UPSTREAM_V19MOCK", "https://198.51.100.10")
    payload = {"name":"v19route", "upstream":"v19mock", "enabled":False}
    created = client.post("/api/v1/v12/routes", headers=HEADERS, json=payload)
    assert created.status_code == 201, created.text
    rows = client.get("/api/v1/v12/routes", headers=HEADERS)
    assert rows.status_code == 200
    assert payload in rows.json()["routes"]
    assert client.delete("/api/v1/v12/routes/v19route", headers=HEADERS).status_code == 200

def test_v19_postgres_persistence_when_ci_service_present(monkeypatch):
    url = os.getenv("NOVIOKRO_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires isolated PostgreSQL CI service")
    monkeypatch.setenv("NOVIOKRO_ADMIN_KEY", "v19-test-secret")
    monkeypatch.setenv("NOVIOKRO_V12_DATABASE_URL", url)
    monkeypatch.setenv("UPSTREAM_V19PG", "https://198.51.100.11")
    name = "v19_pg_ci"
    with create_engine(url).begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS v12_routes (name VARCHAR(64) PRIMARY KEY, upstream VARCHAR(64) NOT NULL, enabled BOOLEAN NOT NULL DEFAULT FALSE)"))
        conn.execute(text("DELETE FROM v12_routes WHERE name=:name"), {"name":name})
    try:
        response = client.post("/api/v1/v12/routes", headers=HEADERS, json={"name":name,"upstream":"v19pg","enabled":False})
        assert response.status_code == 201, response.text
        with create_engine(url).connect() as conn:
            persisted = conn.execute(text("SELECT upstream FROM v12_routes WHERE name=:name"), {"name":name}).scalar()
        assert persisted == "v19pg"
    finally:
        client.delete(f"/api/v1/v12/routes/{name}", headers=HEADERS)
