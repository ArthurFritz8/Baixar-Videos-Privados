import time

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def _wait_for_terminal_status(
    client: TestClient,
    download_id: str,
    timeout_seconds: float = 2.0,
) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        response = client.get(f"/api/v1/downloads/{download_id}")
        assert response.status_code == 200
        body = response.json()
        if body["queue_status"] in ("completed", "failed"):
            return body
        time.sleep(0.05)
    raise AssertionError("job nao atingiu status terminal no tempo esperado")


def test_download_rejects_equal_proofs_with_generic_message(client: TestClient) -> None:
    response = client.post(
        "/api/v1/downloads",
        json={
            "provider": "panda_video",
            "video_reference": "video-001",
            "requester_id": "user-001",
            "authorization": {
                "session_proof": "abcdefgh",
                "entitlement_proof": "abcdefgh",
            },
            "prefer_cached_authorization": True,
        },
    )

    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Nao foi possivel baixar o video."
    assert body["code"] == "AUTHORIZATION_DENIED"


def test_download_provider_failure_is_visible_in_status_with_generic_message(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/v1/downloads",
        json={
            "provider": "hotmart",
            "video_reference": "offline-course-video",
            "requester_id": "user-002",
            "download_id": "dl-fail-hotmart-001",
            "authorization": {
                "session_proof": "abcdefgh",
                "entitlement_proof": "ijklmnop",
            },
            "prefer_cached_authorization": True,
        },
    )

    assert create_response.status_code == 200
    create_body = create_response.json()
    assert create_body["success"] is True
    assert create_body["download_id"] == "dl-fail-hotmart-001"

    status_body = _wait_for_terminal_status(client, "dl-fail-hotmart-001")
    assert status_body["success"] is False
    assert status_body["queue_status"] == "failed"
    assert status_body["message"] == "Nao foi possivel baixar o video."
    assert status_body["code"] == "PROVIDER_UNAVAILABLE"


def test_download_success_with_valid_proofs(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/downloads",
        json={
            "provider": "panda_video",
            "video_reference": "video-003",
            "requester_id": "user-003",
            "download_id": "dl-ok-panda-001",
            "authorization": {
                "session_proof": "abcdefgh",
                "entitlement_proof": "ijklmnop",
            },
            "prefer_cached_authorization": True,
        },
    )

    assert create_response.status_code == 200
    create_body = create_response.json()
    assert create_body["success"] is True
    assert create_body["status"] == "accepted"
    assert create_body["provider"] == "panda_video"
    assert create_body["download_id"] == "dl-ok-panda-001"

    status_body = _wait_for_terminal_status(client, "dl-ok-panda-001")
    assert status_body["success"] is True
    assert status_body["queue_status"] == "completed"


def test_download_idempotency_reuses_existing_job(client: TestClient) -> None:
    payload = {
        "provider": "panda_video",
        "video_reference": "video-777",
        "requester_id": "user-777",
        "download_id": "dl-idempotent-777",
        "authorization": {
            "session_proof": "abcdefgh",
            "entitlement_proof": "ijklmnop",
        },
        "prefer_cached_authorization": True,
    }

    first = client.post("/api/v1/downloads", json=payload)
    second = client.post("/api/v1/downloads", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    assert first_body["download_id"] == "dl-idempotent-777"
    assert second_body["download_id"] == "dl-idempotent-777"
    assert second_body["message"] == "Requisicao ja registrada para este download_id."
