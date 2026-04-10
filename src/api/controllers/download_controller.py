from pathlib import Path

from src.api.schemas.download_schema import (
    CancelDownloadResponse,
    CreateDownloadResponse,
    DownloadFileTokenResponse,
    DownloadRequest,
    DownloadStatusResponse,
)
from src.application.use_cases.cancel_download_use_case import CancelDownloadUseCase
from src.application.use_cases.create_download_use_case import CreateDownloadUseCase
from src.application.use_cases.generate_download_file_token_use_case import (
    GenerateDownloadFileTokenUseCase,
)
from src.application.use_cases.get_download_status_use_case import GetDownloadStatusUseCase
from src.application.use_cases.resolve_download_file_use_case import (
    ResolveDownloadFileUseCase,
)


class DownloadController:
    def __init__(
        self,
        create_download_use_case: CreateDownloadUseCase,
        get_download_status_use_case: GetDownloadStatusUseCase,
        cancel_download_use_case: CancelDownloadUseCase,
        generate_download_file_token_use_case: GenerateDownloadFileTokenUseCase,
        resolve_download_file_use_case: ResolveDownloadFileUseCase,
    ) -> None:
        self._create_download_use_case = create_download_use_case
        self._get_download_status_use_case = get_download_status_use_case
        self._cancel_download_use_case = cancel_download_use_case
        self._generate_download_file_token_use_case = generate_download_file_token_use_case
        self._resolve_download_file_use_case = resolve_download_file_use_case

    async def create_download(self, payload: DownloadRequest) -> CreateDownloadResponse:
        return await self._create_download_use_case.execute(payload)

    async def get_download_status(self, download_id: str) -> DownloadStatusResponse:
        return await self._get_download_status_use_case.execute(download_id)

    async def cancel_download(self, download_id: str) -> CancelDownloadResponse:
        return await self._cancel_download_use_case.execute(download_id)

    async def generate_download_file_token(
        self,
        download_id: str,
    ) -> DownloadFileTokenResponse:
        return await self._generate_download_file_token_use_case.execute(download_id)

    async def resolve_download_file(self, download_id: str, token: str) -> Path:
        return await self._resolve_download_file_use_case.execute(download_id, token)
