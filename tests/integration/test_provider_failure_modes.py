import time

import pytest
from fastapi.testclient import TestClient

from src.main import create_app
from src.shared.config.settings import Settings


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(
        create_app(Settings(job_repository_backend="in_memory", api_key=""))
    ) as test_client:
        yield test_client


def _wait_for_terminal_status(
    client: TestClient,
    download_id: str,
    timeout_seconds: float = 3.0,
) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        response = client.get(f"/api/v1/downloads/{download_id}")
        assert response.status_code == 200
        body = response.json()
        if body["queue_status"] in ("completed", "failed", "canceled"):
            return body
        time.sleep(0.05)
    raise AssertionError("job nao atingiu estado terminal no tempo esperado")


def test_hotmart_timeout_returns_failed_status(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/downloads",
        json={
            "provider": "hotmart",
            "video_reference": "timeout-video-001",
            "requester_id": "user-timeout-001",
            "download_id": "dl-itg-timeout-hotmart-001",
            "authorization": {
                "session_proof": "abcdefgh",
                "entitlement_proof": "ijklmnop",
            },
            "prefer_cached_authorization": True,
        },
    )

    assert create_response.status_code == 200
    terminal_status = _wait_for_terminal_status(client, "dl-itg-timeout-hotmart-001")
    assert terminal_status["queue_status"] == "failed"
    assert terminal_status["code"] == "PROVIDER_TIMEOUT"
    assert terminal_status["message"] == "Nao foi possivel baixar o video."


def test_panda_invalid_contract_returns_failed_status(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/downloads",
        json={
            "provider": "panda_video",
            "video_reference": "invalid_payload-video-001",
            "requester_id": "user-contract-001",
            "download_id": "dl-itg-contract-panda-001",
            "authorization": {
                "session_proof": "abcdefgh",
                "entitlement_proof": "ijklmnop",
            },
            "prefer_cached_authorization": True,
        },
    )

    assert create_response.status_code == 200
    terminal_status = _wait_for_terminal_status(client, "dl-itg-contract-panda-001")
    assert terminal_status["queue_status"] == "failed"
    assert terminal_status["code"] == "PROVIDER_CONTRACT_VIOLATION"
    assert terminal_status["message"] == "Nao foi possivel baixar o video."
