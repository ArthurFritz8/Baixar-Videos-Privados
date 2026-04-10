from fastapi import FastAPI

from src.api.controllers.download_controller import DownloadController
from src.api.middlewares.error_handlers import register_exception_handlers
from src.api.routes.download_routes import build_download_router
from src.application.services.provider_registry import ProviderRegistry
from src.application.use_cases.create_download_use_case import CreateDownloadUseCase
from src.infrastructure.cache.memory.authorization_cache import AuthorizationCache
from src.infrastructure.providers.hotmart.hotmart_provider import HotmartProvider
from src.infrastructure.providers.panda_video.panda_provider import PandaVideoProvider
from src.shared.config.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    app = FastAPI(title=resolved_settings.app_name)
    register_exception_handlers(app, resolved_settings)

    authorization_cache = AuthorizationCache(
        ttl_seconds=resolved_settings.authorization_cache_ttl_seconds,
        max_size=resolved_settings.authorization_cache_max_size,
    )
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
    use_case = CreateDownloadUseCase(
        provider_registry=provider_registry,
        authorization_cache=authorization_cache,
        public_failure_message=resolved_settings.public_download_failure_message,
    )
    controller = DownloadController(use_case=use_case)
    app.include_router(
        build_download_router(controller),
        prefix=resolved_settings.api_prefix,
    )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
