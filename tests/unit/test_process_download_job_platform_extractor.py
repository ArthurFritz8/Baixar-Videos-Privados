import asyncio

from src.application.ports.provider_port import (
    ProviderDownloadRequest,
    ProviderDownloadResult,
    ProviderPort,
)
from src.application.services.provider_registry import ProviderRegistry
from src.application.use_cases.process_download_job_use_case import ProcessDownloadJobUseCase
from src.domain.entities.download_job import DownloadJob
from src.infrastructure.observability.metrics_registry import MetricsRegistry
from src.infrastructure.persistence.in_memory.download_job_repository import (
    InMemoryDownloadJobRepository,
)


class YoutubeProvider(ProviderPort):
    provider_name = "youtube"

    async def request_download_ticket(
        self, request: ProviderDownloadRequest
    ) -> ProviderDownloadResult:
        return ProviderDownloadResult(
            provider="youtube",
            download_id="yt-ticket-001",
            status="accepted",
            artifact_location="https://www.youtube.com/watch?v=abc123",
        )


class FakeDirectDownloader:
    def __init__(self) -> None:
        self.called = False

    async def download(self, source_url: str, download_id: str) -> str:
        self.called = True
        return "should-not-be-used"


class FakePlatformExtractorDownloader:
    def __init__(self) -> None:
        self.called = False

    def supports(self, source_url: str) -> bool:
        return "youtube.com" in source_url

    async def download(
        self,
        source_url: str,
        download_id: str,
        quality_preference: str,
    ) -> str:
        self.called = True
        return f"downloads/{download_id}.mp4"


async def _run_platform_path() -> tuple[str, bool, bool]:
    repository = InMemoryDownloadJobRepository()
    repository.create_if_absent(
        DownloadJob.new(
            download_id="dl-platform-extractor-001",
            provider="youtube",
            video_reference="https://www.youtube.com/watch?v=abc123",
            quality_preference="best",
            requester_id="user-platform-001",
            session_proof="abcdefgh",
            entitlement_proof="ijklmnop",
        )
    )

    direct_downloader = FakeDirectDownloader()
    extractor_downloader = FakePlatformExtractorDownloader()

    use_case = ProcessDownloadJobUseCase(
        provider_registry=ProviderRegistry(providers=[YoutubeProvider()]),
        download_job_repository=repository,
        artifact_downloader=direct_downloader,
        platform_extractor_downloader=extractor_downloader,
        metrics_registry=MetricsRegistry(enabled=True),
        public_failure_message="Nao foi possivel baixar o video.",
        retry_max_attempts=2,
        retry_base_delay_seconds=0.01,
    )

    await use_case.execute("dl-platform-extractor-001")
    final_job = repository.get("dl-platform-extractor-001")
    if final_job is None:
        raise AssertionError("job nao encontrado")

    return final_job.artifact_location or "", direct_downloader.called, extractor_downloader.called


def test_process_uses_platform_extractor_for_social_links() -> None:
    artifact_location, direct_called, extractor_called = asyncio.run(_run_platform_path())
    assert artifact_location.endswith("dl-platform-extractor-001.mp4")
    assert direct_called is False
    assert extractor_called is True
