"""GET /api/health, exercised through the real app."""

from pathlib import Path

from fastapi.testclient import TestClient

from steady.main import app as module_app
from tests.conftest import TEST_VERSION, ClientFactory


def test_reports_ok_with_version_and_time(make_client: ClientFactory, static_dir: Path):
    response = make_client(static_dir).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "steady",
        "version": TEST_VERSION,
        "time": "2026-11-17T10:00:00Z",
    }


def test_works_without_a_built_interface(make_client: ClientFactory):
    assert make_client(None).get("/api/health").status_code == 200


def test_every_response_carries_a_request_id(make_client: ClientFactory):
    client = make_client(None)
    assert len(client.get("/api/health").headers["x-request-id"]) == 32
    sent = "0123456789abcdef0123456789abcdef"
    assert client.get("/api/health", headers={"X-Request-ID": sent}).headers["x-request-id"] == sent


def test_unknown_api_address_is_a_json_404_for_any_method(
    make_client: ClientFactory, static_dir: Path
):
    client = make_client(static_dir)
    for response in (client.get("/api/nope"), client.post("/api/nope"), client.get("/api/")):
        assert response.status_code == 404
        assert response.json() == {"detail": "Not found"}


def test_health_only_answers_get(make_client: ClientFactory):
    response = make_client(None).post("/api/health")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}


def test_the_schema_and_docs_are_published_under_api(make_client: ClientFactory):
    client = make_client(None)
    schema = client.get("/api/openapi.json").json()
    assert list(schema["paths"]) == ["/api/health"]
    assert client.get("/api/docs").status_code == 200


def test_the_module_level_app_is_built_from_the_environment():
    assert TestClient(module_app).get("/api/health").json()["service"] == "steady"
