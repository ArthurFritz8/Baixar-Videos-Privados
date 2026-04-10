from src.api.schemas.download_schema import (
    CreateDownloadResponse,
    DownloadRequest,
    DownloadStatusResponse,
)
from src.application.use_cases.create_download_use_case import CreateDownloadUseCase
from src.application.use_cases.get_download_status_use_case import GetDownloadStatusUseCase


class DownloadController:
    def __init__(
        self,
        create_download_use_case: CreateDownloadUseCase,
        get_download_status_use_case: GetDownloadStatusUseCase,
    ) -> None:
        self._create_download_use_case = create_download_use_case
        self._get_download_status_use_case = get_download_status_use_case

    async def create_download(self, payload: DownloadRequest) -> CreateDownloadResponse:
        return await self._create_download_use_case.execute(payload)

    async def get_download_status(self, download_id: str) -> DownloadStatusResponse:
        return await self._get_download_status_use_case.execute(download_id)
