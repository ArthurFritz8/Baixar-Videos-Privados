import asyncio

from src.application.ports.provider_port import (
    ProviderDownloadRequest,
    ProviderDownloadResult,
    ProviderPort,
)
from src.application.services.provider_registry import ProviderRegistry
from src.application.use_cases.process_download_job_use_case import ProcessDownloadJobUseCase
from src.domain.entities.download_job import DownloadJob
from src.infrastructure.persistence.in_memory.download_job_repository import (
    InMemoryDownloadJobRepository,
)
from src.infrastructure.storage.local.authorized_artifact_downloader import (
    AuthorizedArtifactDownloader,
)


class SlowSuccessProvider(ProviderPort):
    provider_name = "panda_video"

    async def request_download_ticket(
        self, request: ProviderDownloadRequest
    ) -> ProviderDownloadResult:
        await asyncio.sleep(0.2)
        return ProviderDownloadResult(
            provider=request.provider,
            download_id="provider-ticket-001",
            status="accepted",
            artifact_location="memory://artifact",
        )


class NoopArtifactDownloader(AuthorizedArtifactDownloader):
    def __init__(self) -> None:
        super().__init__(
            output_dir="downloads-test",
            http_timeout_seconds=1,
            allowed_source_hosts=set(),
            public_failure_message="Nao foi possivel baixar o video.",
        )

    async def download(self, source_url: str, download_id: str) -> str:
        return source_url


class NoopPlatformExtractorDownloader:
    def supports(self, source_url: str) -> bool:
        return False

    async def download(self, source_url: str, download_id: str) -> str:
        raise AssertionError("platform extractor nao deveria ser chamado")


async def _run_process_with_cancellation() -> str:
    repository = InMemoryDownloadJobRepository()
    repository.create_if_absent(
        DownloadJob.new(
            download_id="dl-coop-cancel-001",
            provider="panda_video",
            video_reference="video-coop-cancel-001",
            requester_id="user-coop-cancel-001",
            session_proof="abcdefgh",
            entitlement_proof="ijklmnop",
        )
    )

    use_case = ProcessDownloadJobUseCase(
        provider_registry=ProviderRegistry(providers=[SlowSuccessProvider()]),
        download_job_repository=repository,
        artifact_downloader=NoopArtifactDownloader(),
        platform_extractor_downloader=NoopPlatformExtractorDownloader(),
        public_failure_message="Nao foi possivel baixar o video.",
        retry_max_attempts=3,
        retry_base_delay_seconds=0.05,
    )

    task = asyncio.create_task(use_case.execute("dl-coop-cancel-001"))
    await asyncio.sleep(0.05)
    repository.mark_canceled("dl-coop-cancel-001", error_code="CANCELED_BY_USER")
    await task

    final_job = repository.get("dl-coop-cancel-001")
    if final_job is None:
        raise AssertionError("job nao encontrado apos processamento")
    return final_job.queue_status


def test_processing_does_not_override_canceled_state() -> None:
    final_status = asyncio.run(_run_process_with_cancellation())
    assert final_status == "canceled"
