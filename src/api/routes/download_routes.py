from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from src.api.controllers.download_controller import DownloadController
from src.api.schemas.download_schema import (
    CancelDownloadResponse,
    CreateDownloadResponse,
    DownloadFileTokenResponse,
    DownloadRequest,
    DownloadStatusResponse,
)


def build_download_router(
    controller: DownloadController,
    require_api_key: Callable[..., Awaitable[None]],
) -> APIRouter:
    router = APIRouter(prefix="/downloads", tags=["downloads"])

    @router.post("", response_model=CreateDownloadResponse)
    async def create_download(
        payload: DownloadRequest,
        _auth: None = Depends(require_api_key),
    ) -> CreateDownloadResponse:
        return await controller.create_download(payload)

    @router.get("/{download_id}", response_model=DownloadStatusResponse)
    async def get_download_status(
        download_id: str,
        _auth: None = Depends(require_api_key),
    ) -> DownloadStatusResponse:
        return await controller.get_download_status(download_id)

    @router.post("/{download_id}/cancel", response_model=CancelDownloadResponse)
    async def cancel_download(
        download_id: str,
        _auth: None = Depends(require_api_key),
    ) -> CancelDownloadResponse:
        return await controller.cancel_download(download_id)

    @router.post("/{download_id}/file-token", response_model=DownloadFileTokenResponse)
    async def generate_file_token(
        download_id: str,
        _auth: None = Depends(require_api_key),
    ) -> DownloadFileTokenResponse:
        return await controller.generate_download_file_token(download_id)

    @router.get("/{download_id}/file")
    async def download_file(
        download_id: str,
        token: str = Query(min_length=16),
        _auth: None = Depends(require_api_key),
    ) -> FileResponse:
        local_path = await controller.resolve_download_file(download_id, token)
        return FileResponse(path=local_path)

    return router
