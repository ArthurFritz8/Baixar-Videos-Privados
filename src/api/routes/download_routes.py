from fastapi import APIRouter

from src.api.controllers.download_controller import DownloadController
from src.api.schemas.download_schema import DownloadRequest, DownloadResponse


def build_download_router(controller: DownloadController) -> APIRouter:
    router = APIRouter(prefix="/downloads", tags=["downloads"])

    @router.post("", response_model=DownloadResponse)
    async def create_download(payload: DownloadRequest) -> DownloadResponse:
        return await controller.create_download(payload)

    return router
