from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.controllers.download_controller import DownloadController
from src.api.middlewares.error_handlers import register_exception_handlers
from src.api.routes.download_routes import build_download_router
from src.application.services.provider_registry import ProviderRegistry
from src.application.use_cases.create_download_use_case import CreateDownloadUseCase
from src.application.use_cases.get_download_status_use_case import GetDownloadStatusUseCase
from src.application.use_cases.process_download_job_use_case import (
    ProcessDownloadJobUseCase,
)
from src.infrastructure.cache.memory.authorization_cache import AuthorizationCache
from src.infrastructure.persistence.in_memory.download_job_repository import (
    InMemoryDownloadJobRepository,
)
from src.infrastructure.providers.hotmart.hotmart_provider import HotmartProvider
from src.infrastructure.providers.panda_video.panda_provider import PandaVideoProvider
from src.infrastructure.queue.in_process.download_queue import InProcessDownloadQueue
from src.infrastructure.queue.in_process.download_worker import InProcessDownloadWorker
from src.shared.config.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    authorization_cache = AuthorizationCache(
        ttl_seconds=resolved_settings.authorization_cache_ttl_seconds,
        max_size=resolved_settings.authorization_cache_max_size,
    )
    download_job_repository = InMemoryDownloadJobRepository()
    download_queue = InProcessDownloadQueue()
    provider_registry = ProviderRegistry(
        providers=[
            PandaVideoProvider(
                public_failure_message=resolved_settings.public_download_failure_message
            ),
            HotmartProvider(
                public_failure_message=resolved_settings.public_download_failure_message
            ),
        ]
    )

    process_download_job_use_case = ProcessDownloadJobUseCase(
        provider_registry=provider_registry,
        download_job_repository=download_job_repository,
        public_failure_message=resolved_settings.public_download_failure_message,
        retry_max_attempts=resolved_settings.provider_retry_max_attempts,
        retry_base_delay_seconds=resolved_settings.provider_retry_base_delay_seconds,
    )
    download_worker = InProcessDownloadWorker(
        download_queue=download_queue,
        process_download_job_use_case=process_download_job_use_case,
        worker_concurrency=resolved_settings.download_worker_concurrency,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await download_worker.start()
        try:
            yield
        finally:
            await download_worker.stop()

    app = FastAPI(title=resolved_settings.app_name, lifespan=lifespan)
    register_exception_handlers(app, resolved_settings)

    create_download_use_case = CreateDownloadUseCase(
        authorization_cache=authorization_cache,
        download_job_repository=download_job_repository,
        download_queue=download_queue,
        public_failure_message=resolved_settings.public_download_failure_message,
    )
    get_download_status_use_case = GetDownloadStatusUseCase(
        download_job_repository=download_job_repository,
        public_failure_message=resolved_settings.public_download_failure_message,
    )
    controller = DownloadController(
        create_download_use_case=create_download_use_case,
        get_download_status_use_case=get_download_status_use_case,
    )
    app.include_router(
        build_download_router(controller),
        prefix=resolved_settings.api_prefix,
    )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
