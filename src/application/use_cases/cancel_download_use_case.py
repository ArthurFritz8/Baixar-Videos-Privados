from src.api.schemas.download_schema import CancelDownloadResponse
from src.application.ports.download_job_repository_port import DownloadJobRepositoryPort
from src.infrastructure.observability.metrics_registry import MetricsRegistry
from src.shared.exceptions.errors import (
    DownloadCancellationNotAllowedError,
    DownloadNotFoundError,
)


class CancelDownloadUseCase:
    def __init__(
        self,
        download_job_repository: DownloadJobRepositoryPort,
        metrics_registry: MetricsRegistry,
        public_failure_message: str,
    ) -> None:
        self._download_job_repository = download_job_repository
        self._metrics_registry = metrics_registry
        self._public_failure_message = public_failure_message

    async def execute(self, download_id: str) -> CancelDownloadResponse:
        job = self._download_job_repository.get(download_id)
        if job is None:
            raise DownloadNotFoundError(
                public_message=self._public_failure_message,
                internal_detail=f"download_id_not_found={download_id}",
            )

        if job.queue_status in ("queued", "processing"):
            canceled_job = self._download_job_repository.mark_canceled(
                download_id=download_id,
                error_code="CANCELED_BY_USER",
            )
            if canceled_job is None:
                raise DownloadNotFoundError(
                    public_message=self._public_failure_message,
                    internal_detail=f"download_id_not_found={download_id}",
                )
            self._metrics_registry.inc_counter("jobs_canceled_total")
            return CancelDownloadResponse(
                success=True,
                message=(
                    "Cancelamento solicitado e aplicado ao job em processamento."
                    if job.queue_status == "processing"
                    else "Download cancelado."
                ),
                provider=canceled_job.provider,
                download_id=canceled_job.download_id,
                queue_status="canceled",
                code=canceled_job.error_code,
            )

        if job.queue_status == "canceled":
            return CancelDownloadResponse(
                success=True,
                message="Download ja estava cancelado.",
                provider=job.provider,
                download_id=job.download_id,
                queue_status="canceled",
                code=job.error_code,
            )

        raise DownloadCancellationNotAllowedError(
            public_message=self._public_failure_message,
            internal_detail=(
                "cancellation_not_allowed_for_status="
                f"{job.queue_status}"
            ),
        )
