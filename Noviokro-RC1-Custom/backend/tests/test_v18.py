from fastapi.testclient import TestClient
from app.main import app
from app.v12 import upstream_url
from fastapi import HTTPException
import pytest

client = TestClient(app)
URL = "/api/v1/v18/security-readiness"

def test_security_readiness_requires_admin(monkeypatch):
    monkeypatch.setenv("NOVIOKRO_ADMIN_KEY", "test-v18-key")
    assert client.get(URL).status_code == 401
    assert client.get(URL, headers={"x-admin-key": "wrong"}).status_code == 401

def test_security_readiness_never_claims_production(monkeypatch):
    monkeypatch.setenv("NOVIOKRO_ADMIN_KEY", "test-v18-key")
    monkeypatch.setenv("NOVIOKRO_V12_ENABLE_PROXY", "1")
    monkeypatch.setenv("NOVIOKRO_V12_DATABASE_URL", "postgresql+psycopg://operator:secret@db/app")
    r = client.get(URL, headers={"x-admin-key": "test-v18-key"})
    assert r.status_code == 200
    assert r.json()["production_ready"] is False
    assert r.json()["configuration"]["postgresql_url_configured"] is True
    assert "secret" not in r.text and "test-v18-key" not in r.text

def test_security_readiness_flags_are_boolean(monkeypatch):
    monkeypatch.setenv("NOVIOKRO_ADMIN_KEY", "test-v18-key")
    r = client.get(URL, headers={"x-admin-key": "test-v18-key"})
    assert all(type(value) is bool for value in r.json()["configuration"].values())

def test_upstream_rejects_credentials(monkeypatch):
    monkeypatch.setenv("UPSTREAM_EVIL", "https://user:password@example.org")
    with pytest.raises(HTTPException) as exc:
        upstream_url("evil")
    assert exc.value.status_code == 400

def test_upstream_rejects_unsafe_scheme(monkeypatch):
    monkeypatch.setenv("UPSTREAM_EVIL", "file:///etc/passwd")
    with pytest.raises(HTTPException) as exc:
        upstream_url("evil")
    assert exc.value.status_code == 400
