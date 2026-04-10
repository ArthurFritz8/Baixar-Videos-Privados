from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_download_rejects_equal_proofs_with_generic_message() -> None:
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


def test_download_provider_failure_returns_generic_message() -> None:
    response = client.post(
        "/api/v1/downloads",
        json={
            "provider": "hotmart",
            "video_reference": "offline-course-video",
            "requester_id": "user-002",
            "authorization": {
                "session_proof": "abcdefgh",
                "entitlement_proof": "ijklmnop",
            },
            "prefer_cached_authorization": True,
        },
    )

    assert response.status_code == 502
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Nao foi possivel baixar o video."
    assert body["code"] == "PROVIDER_UNAVAILABLE"


def test_download_success_with_valid_proofs() -> None:
    response = client.post(
        "/api/v1/downloads",
        json={
            "provider": "panda_video",
            "video_reference": "video-003",
            "requester_id": "user-003",
            "authorization": {
                "session_proof": "abcdefgh",
                "entitlement_proof": "ijklmnop",
            },
            "prefer_cached_authorization": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["status"] == "accepted"
    assert body["provider"] == "panda_video"
