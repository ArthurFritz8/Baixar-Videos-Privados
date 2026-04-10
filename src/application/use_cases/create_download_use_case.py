from src.api.schemas.download_schema import DownloadRequest, DownloadResponse
from src.application.ports.provider_port import ProviderDownloadRequest
from src.application.services.provider_registry import ProviderRegistry
from src.domain.policies.authorization_policy import AuthorizationPolicy
from src.domain.value_objects.authorization_context import AuthorizationContext
from src.infrastructure.cache.memory.authorization_cache import AuthorizationCache
from src.shared.exceptions.errors import AppError, DownloadFailureError


class CreateDownloadUseCase:
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        authorization_cache: AuthorizationCache,
        public_failure_message: str,
    ) -> None:
        self._provider_registry = provider_registry
        self._authorization_cache = authorization_cache
        self._public_failure_message = public_failure_message

    async def execute(self, request: DownloadRequest) -> DownloadResponse:
        try:
            authorization_context = AuthorizationContext(
                provider=request.provider,
                video_reference=request.video_reference,
                requester_id=request.requester_id,
                session_proof=request.authorization.session_proof,
                entitlement_proof=request.authorization.entitlement_proof,
            )

            cache_key = AuthorizationPolicy.build_cache_key(authorization_context)
            cache_hit = (
                self._authorization_cache.get(cache_key)
                if request.prefer_cached_authorization
                else None
            )
            if cache_hit is not True:
                AuthorizationPolicy.enforce_combined_proof(
                    authorization_context,
                    public_failure_message=self._public_failure_message,
                )
                self._authorization_cache.set(cache_key, True)

            provider = self._provider_registry.get(
                provider_name=request.provider,
                public_failure_message=self._public_failure_message,
            )
            provider_result = await provider.request_download_ticket(
                ProviderDownloadRequest(
                    provider=request.provider,
                    video_reference=request.video_reference,
                    requester_id=request.requester_id,
                    session_proof=request.authorization.session_proof,
                    entitlement_proof=request.authorization.entitlement_proof,
                )
            )

            return DownloadResponse(
                success=True,
                message="Download autorizado e em processamento.",
                status="accepted",
                provider=provider_result.provider,
                download_id=provider_result.download_id,
                artifact_location=provider_result.artifact_location,
            )
        except AppError:
            raise
        except Exception as exc:
            raise DownloadFailureError(
                public_message=self._public_failure_message,
                internal_detail=f"unhandled_download_error={exc}",
            ) from exc
