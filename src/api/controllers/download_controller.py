from src.api.schemas.download_schema import DownloadRequest, DownloadResponse
from src.application.use_cases.create_download_use_case import CreateDownloadUseCase


class DownloadController:
    def __init__(self, use_case: CreateDownloadUseCase) -> None:
        self._use_case = use_case

    async def create_download(self, payload: DownloadRequest) -> DownloadResponse:
        return await self._use_case.execute(payload)
