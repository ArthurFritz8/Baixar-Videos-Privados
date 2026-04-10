from src.api.schemas.download_schema import DownloadStatusResponse
from src.infrastructure.persistence.in_memory.download_job_repository import (
    InMemoryDownloadJobRepository,
)
from src.shared.exceptions.errors import DownloadNotFoundError


class GetDownloadStatusUseCase:
    def __init__(
        self,
        download_job_repository: InMemoryDownloadJobRepository,
        public_failure_message: str,
    ) -> None:
        self._download_job_repository = download_job_repository
        self._public_failure_message = public_failure_message

    async def execute(self, download_id: str) -> DownloadStatusResponse:
        job = self._download_job_repository.get(download_id)
        if job is None:
            raise DownloadNotFoundError(
                public_message=self._public_failure_message,
                internal_detail=f"download_id_not_found={download_id}",
            )

        if job.queue_status == "failed":
            return DownloadStatusResponse(
                success=False,
                message=self._public_failure_message,
                provider=job.provider,
                download_id=job.download_id,
                queue_status=job.queue_status,
                artifact_location=job.artifact_location,
                code=job.error_code or "DOWNLOAD_FAILED",
            )

        if job.queue_status == "completed":
            return DownloadStatusResponse(
                success=True,
                message="Download processado com sucesso.",
                provider=job.provider,
                download_id=job.download_id,
                queue_status=job.queue_status,
                artifact_location=job.artifact_location,
            )

        return DownloadStatusResponse(
            success=True,
            message="Download em processamento.",
            provider=job.provider,
            download_id=job.download_id,
            queue_status=job.queue_status,
            artifact_location=job.artifact_location,
        )
