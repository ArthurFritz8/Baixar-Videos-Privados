from pathlib import Path

from src.application.ports.download_job_repository_port import DownloadJobRepositoryPort
from src.shared.exceptions.errors import (
    DownloadFileMissingError,
    DownloadFileNotReadyError,
    DownloadFileTokenInvalidError,
    DownloadNotFoundError,
)
from src.shared.security.download_file_token_service import DownloadFileTokenService


class ResolveDownloadFileUseCase:
    def __init__(
        self,
        download_job_repository: DownloadJobRepositoryPort,
        token_service: DownloadFileTokenService,
        public_failure_message: str,
    ) -> None:
        self._download_job_repository = download_job_repository
        self._token_service = token_service
        self._public_failure_message = public_failure_message

    async def execute(self, download_id: str, token: str) -> Path:
        job = self._download_job_repository.get(download_id)
        if job is None:
            raise DownloadNotFoundError(
                public_message=self._public_failure_message,
                internal_detail=f"download_id_not_found={download_id}",
            )

        if not self._token_service.validate(download_id=download_id, token=token):
            raise DownloadFileTokenInvalidError(
                public_message=self._public_failure_message,
                internal_detail=f"download_file_token_invalid download_id={download_id}",
            )

        if job.queue_status != "completed" or not job.artifact_location:
            raise DownloadFileNotReadyError(
                public_message=self._public_failure_message,
                internal_detail=f"download_file_not_ready status={job.queue_status}",
            )

        local_path = Path(job.artifact_location)
        if not local_path.exists() or not local_path.is_file():
            raise DownloadFileMissingError(
                public_message=self._public_failure_message,
                internal_detail=f"download_file_missing path={local_path}",
            )

        return local_path
