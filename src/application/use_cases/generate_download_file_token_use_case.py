from src.api.schemas.download_schema import DownloadFileTokenResponse
from src.application.ports.download_job_repository_port import DownloadJobRepositoryPort
from src.shared.exceptions.errors import DownloadFileNotReadyError, DownloadNotFoundError
from src.shared.security.download_file_token_service import DownloadFileTokenService


class GenerateDownloadFileTokenUseCase:
    def __init__(
        self,
        download_job_repository: DownloadJobRepositoryPort,
        token_service: DownloadFileTokenService,
        public_failure_message: str,
    ) -> None:
        self._download_job_repository = download_job_repository
        self._token_service = token_service
        self._public_failure_message = public_failure_message

    async def execute(self, download_id: str) -> DownloadFileTokenResponse:
        job = self._download_job_repository.get(download_id)
        if job is None:
            raise DownloadNotFoundError(
                public_message=self._public_failure_message,
                internal_detail=f"download_id_not_found={download_id}",
            )

        if job.queue_status != "completed" or not job.artifact_location:
            raise DownloadFileNotReadyError(
                public_message=self._public_failure_message,
                internal_detail=f"download_file_not_ready status={job.queue_status}",
            )

        token, expires_at = self._token_service.generate(download_id)
        return DownloadFileTokenResponse(
            success=True,
            message="Token de arquivo gerado com sucesso.",
            download_id=download_id,
            token=token,
            expires_at=expires_at.isoformat(),
        )
