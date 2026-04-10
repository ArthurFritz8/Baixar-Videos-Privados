from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.infrastructure.observability.logger import get_logger
from src.shared.config.settings import Settings, get_settings
from src.shared.exceptions.errors import AppError

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI, settings: Settings | None = None) -> None:
    resolved_settings = settings or get_settings()

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        if exc.internal_detail:
            logger.warning(
                "application_error code=%s detail=%s", exc.code, exc.internal_detail
            )
        else:
            logger.warning("application_error code=%s", exc.code)

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.public_message,
                "code": exc.code,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        logger.info("request_validation_error count=%s", len(exc.errors()))
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": resolved_settings.public_download_failure_message,
                "code": "REQUEST_VALIDATION_ERROR",
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unexpected_error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": resolved_settings.public_download_failure_message,
                "code": "UNEXPECTED_ERROR",
            },
        )
