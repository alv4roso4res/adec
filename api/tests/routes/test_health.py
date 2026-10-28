import httpx
from fastapi.testclient import TestClient


def test_health_returns_200(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_returns_version_from_settings(client, settings):
    response = client.get("/api/health")

    assert response.json() == {"status": "ok", "version": settings.app_version}
    assert response.json()["version"] == "1.2.3-test"


def test_old_routes_are_gone(client):
    assert client.get("/").status_code == 404
    assert client.get("/health").status_code == 404


def test_lifespan_creates_and_closes_github_client(app, settings):
    with TestClient(app):
        http = app.state.http_client
        assert isinstance(http, httpx.AsyncClient)
        assert str(http.base_url) == "https://api.github.com"
        assert http.headers["Authorization"] == f"Bearer {settings.github_token}"
        assert http.headers["Accept"] == "application/vnd.github+json"
        assert "X-GitHub-Api-Version" in http.headers
        assert not http.is_closed

    assert http.is_closed
