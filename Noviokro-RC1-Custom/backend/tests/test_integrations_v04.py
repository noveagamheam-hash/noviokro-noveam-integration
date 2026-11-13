import os
import httpx
os.environ["NOVIOKRO_ADMIN_KEY"] = "local-test-secret"
os.environ.setdefault("DATABASE_URL", "sqlite:///./noviokro-test-v04.db")
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
H = {"X-Admin-Key": "local-test-secret"}

def test_project_access():
    assert client.get("/api/v1/integrations/projects").status_code == 401
    response = client.get("/api/v1/integrations/projects", headers=H)
    assert response.status_code == 200
    assert response.json()["projects"] == ["noveam", "noveomediater"]

def test_unconfigured_service_cannot_discover():
    response = client.post("/api/v1/integrations/discover", headers=H,
                           json={"project": "noveam", "service": "unconfigured"})
    assert response.status_code == 400

def test_invalid_project_rejected():
    response = client.post("/api/v1/integrations/discover", headers=H,
                           json={"project": "unknown", "service": "backend"})
    assert response.status_code == 422

def test_catalog_requires_admin():
    assert client.get("/api/v1/integrations/discoveries").status_code == 401
    assert client.get("/api/v1/integrations/discoveries", headers=H).status_code == 200

def test_existing_endpoints_preserved():
    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/bots", headers=H).status_code == 200


def test_noveam_discovers_custom_catalog(monkeypatch):
    monkeypatch.setenv("NOVIOKRO_SERVICE_NOVEAM_CUSTOMTEST", "https://noveam.example")
    route = {
        "id": "professional-subcategories",
        "method": "GET",
        "path": "/api/professional/subcategories",
        "query": ["category_id"],
        "summary": "List subcategories",
    }

    def catalog_response(request):
        assert str(request.url) == "https://noveam.example/api.json"
        return httpx.Response(200, json={
            "format": "noviokro-api/1", "app": "noveam", "routes": [route],
        })

    async_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: async_client(
        transport=httpx.MockTransport(catalog_response), **kwargs,
    ))
    health = client.get("/api/v1/integrations/health/noveam/customtest", headers=H)
    assert health.json()["upstream_status"] == 200
    discovery = client.post("/api/v1/integrations/discover", headers=H,
                            json={"project": "noveam", "service": "customtest"})
    assert discovery.status_code == 201, discovery.text
    result = discovery.json()
    assert result["endpoint_count"] == 1
    rows = client.get("/api/v1/integrations/discoveries?project=noveam", headers=H).json()
    saved = next(row for row in rows if row["id"] == result["id"])
    assert saved["spec_version"] == "noviokro-api/1"
    assert saved["endpoints"] == [route]
