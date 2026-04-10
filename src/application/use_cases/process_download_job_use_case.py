import asyncio
from urllib.parse import urlparse

from src.application.ports.provider_port import ProviderDownloadRequest
from src.application.services.provider_registry import ProviderRegistry
from src.infrastructure.persistence.in_memory.download_job_repository import (
    InMemoryDownloadJobRepository,
)
from src.infrastructure.storage.local.authorized_artifact_downloader import (
    AuthorizedArtifactDownloader,
)
from src.shared.exceptions.errors import AppError


class ProcessDownloadJobUseCase:
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        download_job_repository: InMemoryDownloadJobRepository,
        artifact_downloader: AuthorizedArtifactDownloader,
        public_failure_message: str,
        retry_max_attempts: int,
        retry_base_delay_seconds: float,
    ) -> None:
        self._provider_registry = provider_registry
        self._download_job_repository = download_job_repository
        self._artifact_downloader = artifact_downloader
        self._public_failure_message = public_failure_message
        self._retry_max_attempts = retry_max_attempts
        self._retry_base_delay_seconds = retry_base_delay_seconds

    async def execute(self, download_id: str) -> None:
        job = self._download_job_repository.mark_processing(download_id)
        if job is None:
            return
        if job.queue_status in ("completed", "failed", "canceled"):
            return

        provider = self._provider_registry.get(
            provider_name=job.provider,
            public_failure_message=self._public_failure_message,
        )

        attempt = 0
        while True:
            if self._is_canceled(download_id):
                return

            attempt += 1
            try:
                result = await provider.request_download_ticket(
                    ProviderDownloadRequest(
                        provider=job.provider,
                        video_reference=job.video_reference,
                        requester_id=job.requester_id,
                        session_proof=job.session_proof,
                        entitlement_proof=job.entitlement_proof,
                    )
                )

                resolved_artifact_location = result.artifact_location
                if (
                    resolved_artifact_location
                    and self._is_http_url(resolved_artifact_location)
                ):
                    resolved_artifact_location = await self._artifact_downloader.download(
                        source_url=resolved_artifact_location,
                        download_id=download_id,
                    )

                if self._is_canceled(download_id):
                    return

                self._download_job_repository.mark_completed(
                    download_id=download_id,
                    artifact_location=resolved_artifact_location,
                    attempt_count=attempt,
                )
                return
            except AppError as exc:
                if self._is_canceled(download_id):
                    return

                should_retry = exc.code in ("PROVIDER_TIMEOUT", "PROVIDER_UNAVAILABLE")
                if (not should_retry) or (attempt >= self._retry_max_attempts):
                    self._download_job_repository.mark_failed(
                        download_id=download_id,
                        error_code=exc.code,
                        attempt_count=attempt,
                    )
                    return
                await asyncio.sleep(self._retry_base_delay_seconds * (2 ** (attempt - 1)))
            except Exception:
                if self._is_canceled(download_id):
                    return

                self._download_job_repository.mark_failed(
                    download_id=download_id,
                    error_code="DOWNLOAD_FAILED",
                    attempt_count=attempt,
                )
                return

    def _is_canceled(self, download_id: str) -> bool:
        current = self._download_job_repository.get(download_id)
        if current is None:
            return False
        return current.queue_status == "canceled"

    @staticmethod
    def _is_http_url(value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme.lower() in ("http", "https") and bool(parsed.netloc)
