from fastapi import APIRouter

from src.api.controllers.download_controller import DownloadController
from src.api.schemas.download_schema import (
    CancelDownloadResponse,
    CreateDownloadResponse,
    DownloadRequest,
    DownloadStatusResponse,
)


def build_download_router(controller: DownloadController) -> APIRouter:
    router = APIRouter(prefix="/downloads", tags=["downloads"])

    @router.post("", response_model=CreateDownloadResponse)
    async def create_download(payload: DownloadRequest) -> CreateDownloadResponse:
        return await controller.create_download(payload)

    @router.get("/{download_id}", response_model=DownloadStatusResponse)
    async def get_download_status(download_id: str) -> DownloadStatusResponse:
        return await controller.get_download_status(download_id)

    @router.post("/{download_id}/cancel", response_model=CancelDownloadResponse)
    async def cancel_download(download_id: str) -> CancelDownloadResponse:
        return await controller.cancel_download(download_id)

    return router
