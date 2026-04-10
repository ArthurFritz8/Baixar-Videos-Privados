import asyncio

import pytest
from fastapi.testclient import TestClient

from src.application.use_cases.generate_download_file_token_use_case import (
    GenerateDownloadFileTokenUseCase,
)
from src.application.use_cases.resolve_download_file_use_case import ResolveDownloadFileUseCase
from src.domain.entities.download_job import DownloadJob
from src.infrastructure.persistence.in_memory.download_job_repository import (
    InMemoryDownloadJobRepository,
)
from src.main import create_app
from src.shared.config.settings import Settings
from src.shared.exceptions.errors import DownloadFileTokenInvalidError
from src.shared.security.download_file_token_service import DownloadFileTokenService


def _valid_create_payload(download_id: str) -> dict:
    return {
        "provider": "panda_video",
        "video_reference": "video-security-001",
        "requester_id": "user-security-001",
        "download_id": download_id,
        "authorization": {
            "session_proof": "abcdefgh",
            "entitlement_proof": "ijklmnop",
        },
        "prefer_cached_authorization": True,
    }


def test_api_key_required_when_configured() -> None:
    settings = Settings(
        job_repository_backend="in_memory",
        api_key="secret-key-123",
    )
    with TestClient(create_app(settings)) as client:
        unauthorized = client.post(
            "/api/v1/downloads",
            json=_valid_create_payload("dl-auth-missing-001"),
        )
        assert unauthorized.status_code == 401
        unauthorized_body = unauthorized.json()
        assert unauthorized_body["success"] is False
        assert unauthorized_body["code"] == "API_KEY_INVALID"

        authorized = client.post(
            "/api/v1/downloads",
            json=_valid_create_payload("dl-auth-ok-001"),
            headers={"X-API-Key": "secret-key-123"},
        )
        assert authorized.status_code == 200


def test_healthz_livez_readyz_endpoints_exist() -> None:
    settings = Settings(job_repository_backend="in_memory")
    with TestClient(create_app(settings)) as client:
        assert client.get("/healthz").status_code == 200
        assert client.get("/livez").status_code == 200
        readiness = client.get("/readyz")
        assert readiness.status_code == 200
        body = readiness.json()
        assert body["status"] in ("ok", "degraded")
        assert "repository" in body["checks"]
        assert "queue" in body["checks"]


def test_generate_and_resolve_file_token_success(tmp_path) -> None:
    repository = InMemoryDownloadJobRepository()
    token_service = DownloadFileTokenService(secret="token-secret", ttl_seconds=300)
    generate_use_case = GenerateDownloadFileTokenUseCase(
        download_job_repository=repository,
        token_service=token_service,
        public_failure_message="Nao foi possivel baixar o video.",
    )
    resolve_use_case = ResolveDownloadFileUseCase(
        download_job_repository=repository,
        token_service=token_service,
        public_failure_message="Nao foi possivel baixar o video.",
    )

    artifact_path = tmp_path / "artifact.bin"
    artifact_path.write_bytes(b"ok")

    queued_job = DownloadJob.new(
        download_id="dl-file-token-001",
        provider="panda_video",
        video_reference="video-file-001",
        quality_preference="best",
        requester_id="user-file-001",
        session_proof="abcdefgh",
        entitlement_proof="ijklmnop",
    )
    completed_job = queued_job.to_completed(
        artifact_location=str(artifact_path),
        attempt_count=1,
    )
    repository.create_if_absent(completed_job)

    token_response = asyncio.run(generate_use_case.execute("dl-file-token-001"))
    resolved_path = asyncio.run(
        resolve_use_case.execute("dl-file-token-001", token_response.token)
    )

    assert resolved_path == artifact_path


def test_resolve_file_with_invalid_token_raises_error(tmp_path) -> None:
    repository = InMemoryDownloadJobRepository()
    token_service = DownloadFileTokenService(secret="token-secret", ttl_seconds=300)
    resolve_use_case = ResolveDownloadFileUseCase(
        download_job_repository=repository,
        token_service=token_service,
        public_failure_message="Nao foi possivel baixar o video.",
    )

    artifact_path = tmp_path / "artifact-invalid-token.bin"
    artifact_path.write_bytes(b"ok")

    queued_job = DownloadJob.new(
        download_id="dl-file-token-002",
        provider="panda_video",
        video_reference="video-file-002",
        quality_preference="best",
        requester_id="user-file-002",
        session_proof="abcdefgh",
        entitlement_proof="ijklmnop",
    )
    completed_job = queued_job.to_completed(
        artifact_location=str(artifact_path),
        attempt_count=1,
    )
    repository.create_if_absent(completed_job)

    with pytest.raises(DownloadFileTokenInvalidError) as exc:
        asyncio.run(resolve_use_case.execute("dl-file-token-002", "invalid-token-value"))

    assert exc.value.code == "DOWNLOAD_FILE_TOKEN_INVALID"
