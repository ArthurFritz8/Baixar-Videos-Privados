import asyncio

import pytest

from src.application.use_cases.cancel_download_use_case import CancelDownloadUseCase
from src.domain.entities.download_job import DownloadJob
from src.infrastructure.persistence.in_memory.download_job_repository import (
    InMemoryDownloadJobRepository,
)
from src.shared.exceptions.errors import (
    DownloadNotFoundError,
)


def test_cancel_queued_download_succeeds() -> None:
    repository = InMemoryDownloadJobRepository()
    use_case = CancelDownloadUseCase(
        download_job_repository=repository,
        public_failure_message="Nao foi possivel baixar o video.",
    )

    repository.create_if_absent(
        DownloadJob.new(
            download_id="dl-cancel-queued-001",
            provider="panda_video",
            video_reference="video-queued-001",
            requester_id="user-queued",
            session_proof="abcdefgh",
            entitlement_proof="ijklmnop",
        )
    )

    result = asyncio.run(use_case.execute("dl-cancel-queued-001"))
    assert result.success is True
    assert result.queue_status == "canceled"
    assert result.code == "CANCELED_BY_USER"


def test_cancel_processing_download_succeeds_with_cooperative_mode() -> None:
    repository = InMemoryDownloadJobRepository()
    use_case = CancelDownloadUseCase(
        download_job_repository=repository,
        public_failure_message="Nao foi possivel baixar o video.",
    )

    repository.create_if_absent(
        DownloadJob.new(
            download_id="dl-cancel-processing-001",
            provider="hotmart",
            video_reference="video-processing-001",
            requester_id="user-processing",
            session_proof="abcdefgh",
            entitlement_proof="ijklmnop",
        )
    )
    repository.mark_processing("dl-cancel-processing-001")

    result = asyncio.run(use_case.execute("dl-cancel-processing-001"))
    assert result.success is True
    assert result.queue_status == "canceled"
    assert result.code == "CANCELED_BY_USER"
    assert "processamento" in result.message.lower()


def test_cancel_unknown_download_raises_not_found() -> None:
    repository = InMemoryDownloadJobRepository()
    use_case = CancelDownloadUseCase(
        download_job_repository=repository,
        public_failure_message="Nao foi possivel baixar o video.",
    )

    with pytest.raises(DownloadNotFoundError) as exc:
        asyncio.run(use_case.execute("dl-missing-001"))

    assert exc.value.code == "DOWNLOAD_NOT_FOUND"
