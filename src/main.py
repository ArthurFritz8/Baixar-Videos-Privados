import asyncio
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI

from src.api.controllers.download_controller import DownloadController
from src.api.middlewares.api_key_auth import ApiKeyAuthenticator
from src.api.middlewares.error_handlers import register_exception_handlers
from src.api.routes.download_routes import build_download_router
from src.application.ports.download_queue_port import DownloadQueuePort
from src.application.ports.download_job_repository_port import DownloadJobRepositoryPort
from src.application.services.retention_cleanup_service import RetentionCleanupService
from src.application.services.provider_registry import ProviderRegistry
from src.application.use_cases.cancel_download_use_case import CancelDownloadUseCase
from src.application.use_cases.create_download_use_case import CreateDownloadUseCase
from src.application.use_cases.generate_download_file_token_use_case import (
    GenerateDownloadFileTokenUseCase,
)
from src.application.use_cases.get_download_status_use_case import GetDownloadStatusUseCase
from src.application.use_cases.process_download_job_use_case import (
    ProcessDownloadJobUseCase,
)
from src.application.use_cases.resolve_download_file_use_case import (
    ResolveDownloadFileUseCase,
)
from src.infrastructure.cache.memory.authorization_cache import AuthorizationCache
from src.infrastructure.observability.logger import get_logger
from src.infrastructure.observability.metrics_registry import MetricsRegistry
from src.infrastructure.persistence.in_memory.download_job_repository import (
    InMemoryDownloadJobRepository,
)
from src.infrastructure.persistence.sqlite.download_job_repository import (
    SQLiteDownloadJobRepository,
)
from src.infrastructure.providers.hotmart.hotmart_provider import HotmartProvider
from src.infrastructure.providers.panda_video.panda_provider import PandaVideoProvider
from src.infrastructure.providers.platform_links.platform_link_provider import (
    PlatformLinkProvider,
)
from src.infrastructure.queue.in_process.download_queue import InProcessDownloadQueue
from src.infrastructure.queue.in_process.download_worker import InProcessDownloadWorker
from src.infrastructure.storage.local.authorized_artifact_downloader import (
    AuthorizedArtifactDownloader,
)
from src.infrastructure.storage.local.platform_extractor_downloader import (
    PlatformExtractorDownloader,
)
from src.shared.config.settings import Settings, get_settings
from src.shared.security.download_file_token_service import DownloadFileTokenService
from src.shared.security.request_rate_limiter import RequesterRateLimiter

logger = get_logger(__name__)

PLATFORM_PROVIDER_CONFIG: list[tuple[str, str, set[str]]] = [
    ("youtube", "yt", {"youtube.com", "youtu.be"}),
    ("instagram", "ig", {"instagram.com"}),
    ("tiktok", "tk", {"tiktok.com"}),
    ("facebook", "fb", {"facebook.com", "fb.watch"}),
    ("x", "x", {"x.com", "twitter.com"}),
    ("vimeo", "vi", {"vimeo.com", "player.vimeo.com"}),
]


def _build_download_queue(settings: Settings) -> DownloadQueuePort:
    if settings.queue_backend == "redis":
        try:
            from src.infrastructure.queue.redis_optional.redis_download_queue import (
                RedisDownloadQueue,
            )

            logger.info("download_queue_backend backend=redis")
            return RedisDownloadQueue(
                redis_url=settings.redis_url,
                queue_key=settings.redis_queue_key,
            )
        except Exception as exc:
            logger.warning(
                "download_queue_backend_fallback backend=in_process reason=%s",
                exc,
            )

    logger.info("download_queue_backend backend=in_process")
    return InProcessDownloadQueue()


def _build_download_job_repository(settings: Settings) -> DownloadJobRepositoryPort:
    if settings.job_repository_backend == "sqlite":
        logger.info("download_job_repository backend=sqlite path=%s", settings.sqlite_db_path)
        return SQLiteDownloadJobRepository(settings.sqlite_db_path)

    logger.info("download_job_repository backend=in_memory")
    return InMemoryDownloadJobRepository()


def _build_provider_registry(settings: Settings) -> ProviderRegistry:
    providers = [
        PandaVideoProvider(public_failure_message=settings.public_download_failure_message),
        HotmartProvider(public_failure_message=settings.public_download_failure_message),
    ]
    for provider_name, ticket_prefix, allowed_hosts in PLATFORM_PROVIDER_CONFIG:
        providers.append(
            PlatformLinkProvider(
                provider_name=provider_name,
                ticket_prefix=ticket_prefix,
                allowed_hosts=allowed_hosts,
                public_failure_message=settings.public_download_failure_message,
            )
        )
    return ProviderRegistry(providers=providers)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    allowed_source_hosts = {
        host.strip().lower()
        for host in resolved_settings.allowed_source_hosts.split(",")
        if host.strip()
    }

    authorization_cache = AuthorizationCache(
        ttl_seconds=resolved_settings.authorization_cache_ttl_seconds,
        max_size=resolved_settings.authorization_cache_max_size,
    )
    metrics_registry = MetricsRegistry(enabled=resolved_settings.metrics_enabled)
    download_job_repository = _build_download_job_repository(resolved_settings)
    download_queue = _build_download_queue(resolved_settings)
    provider_registry = _build_provider_registry(resolved_settings)
    requester_rate_limiter = RequesterRateLimiter(
        enabled=resolved_settings.requester_rate_limit_enabled,
        max_requests=resolved_settings.requester_rate_limit_max_requests,
        window_seconds=resolved_settings.requester_rate_limit_window_seconds,
        public_failure_message=resolved_settings.public_download_failure_message,
    )
    token_service = DownloadFileTokenService(
        secret=resolved_settings.download_file_token_secret,
        ttl_seconds=resolved_settings.download_file_token_ttl_seconds,
    )
    api_key_authenticator = ApiKeyAuthenticator(
        header_name=resolved_settings.api_key_header_name,
        expected_api_key=resolved_settings.api_key,
        public_failure_message=resolved_settings.public_download_failure_message,
    )
    artifact_downloader = AuthorizedArtifactDownloader(
        output_dir=resolved_settings.download_output_dir,
        http_timeout_seconds=resolved_settings.download_http_timeout_seconds,
        allowed_source_hosts=allowed_source_hosts,
        public_failure_message=resolved_settings.public_download_failure_message,
    )
    platform_extractor_downloader = PlatformExtractorDownloader(
        output_dir=resolved_settings.download_output_dir,
        enabled=resolved_settings.enable_platform_extractor,
        public_failure_message=resolved_settings.public_download_failure_message,
    )

    process_download_job_use_case = ProcessDownloadJobUseCase(
        provider_registry=provider_registry,
        download_job_repository=download_job_repository,
        artifact_downloader=artifact_downloader,
        platform_extractor_downloader=platform_extractor_downloader,
        metrics_registry=metrics_registry,
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
        cleanup_task = None
        cleanup_service = RetentionCleanupService(
            download_job_repository=download_job_repository,
            terminal_job_retention_hours=resolved_settings.terminal_job_retention_hours,
        )

        if resolved_settings.retention_cleanup_enabled:
            async def _cleanup_loop() -> None:
                while True:
                    await cleanup_service.run_once()
                    await asyncio.sleep(resolved_settings.retention_cleanup_interval_seconds)

            cleanup_task = asyncio.create_task(_cleanup_loop())

        await download_worker.start()
        try:
            yield
        finally:
            if cleanup_task is not None:
                cleanup_task.cancel()
                await asyncio.gather(cleanup_task, return_exceptions=True)
            await download_worker.stop()
            await download_queue.close()
            close = getattr(download_job_repository, "close", None)
            if callable(close):
                close()

    app = FastAPI(title=resolved_settings.app_name, lifespan=lifespan)
    register_exception_handlers(app, resolved_settings)

    @app.middleware("http")
    async def telemetry_middleware(request, call_next):
        correlation_id = request.headers.get("X-Correlation-Id", str(uuid4()))
        start = perf_counter()
        response = await call_next(request)
        duration_ms = (perf_counter() - start) * 1000.0
        metrics_registry.inc_counter("http_requests_total")
        metrics_registry.inc_counter(f"http_status_{response.status_code}_total")
        metrics_registry.set_gauge("http_last_request_duration_ms", duration_ms)
        response.headers["X-Correlation-Id"] = correlation_id
        logger.info(
            "http_request method=%s path=%s status=%s duration_ms=%.2f correlation_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            correlation_id,
        )
        return response

    create_download_use_case = CreateDownloadUseCase(
        authorization_cache=authorization_cache,
        download_job_repository=download_job_repository,
        download_queue=download_queue,
        requester_rate_limiter=requester_rate_limiter,
        default_quality_preference=resolved_settings.download_quality_default,
        metrics_registry=metrics_registry,
        public_failure_message=resolved_settings.public_download_failure_message,
    )
    get_download_status_use_case = GetDownloadStatusUseCase(
        download_job_repository=download_job_repository,
        public_failure_message=resolved_settings.public_download_failure_message,
    )
    cancel_download_use_case = CancelDownloadUseCase(
        download_job_repository=download_job_repository,
        metrics_registry=metrics_registry,
        public_failure_message=resolved_settings.public_download_failure_message,
    )
    generate_download_file_token_use_case = GenerateDownloadFileTokenUseCase(
        download_job_repository=download_job_repository,
        token_service=token_service,
        public_failure_message=resolved_settings.public_download_failure_message,
    )
    resolve_download_file_use_case = ResolveDownloadFileUseCase(
        download_job_repository=download_job_repository,
        token_service=token_service,
        public_failure_message=resolved_settings.public_download_failure_message,
    )
    controller = DownloadController(
        create_download_use_case=create_download_use_case,
        get_download_status_use_case=get_download_status_use_case,
        cancel_download_use_case=cancel_download_use_case,
        generate_download_file_token_use_case=generate_download_file_token_use_case,
        resolve_download_file_use_case=resolve_download_file_use_case,
    )
    app.include_router(
        build_download_router(controller, require_api_key=api_key_authenticator),
        prefix=resolved_settings.api_prefix,
    )

    @app.get("/healthz", tags=["health"])
    @app.get("/health", tags=["health"], include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/livez", tags=["health"])
    @app.get("/liveness", tags=["health"], include_in_schema=False)
    async def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["health"])
    @app.get("/readiness", tags=["health"], include_in_schema=False)
    async def readiness() -> dict[str, object]:
        checks = {
            "repository": download_job_repository.ping(),
            "queue": True,
        }
        status = "ok" if all(checks.values()) else "degraded"
        return {"status": status, "checks": checks}

    @app.get("/metrics", tags=["observability"])
    async def metrics() -> dict[str, object]:
        by_status = download_job_repository.count_by_status()
        for status, count in by_status.items():
            metrics_registry.set_gauge(f"jobs_{status}", float(count))
        snapshot = metrics_registry.snapshot()
        snapshot["jobs_by_status"] = by_status
        return snapshot

    return app


app = create_app()
