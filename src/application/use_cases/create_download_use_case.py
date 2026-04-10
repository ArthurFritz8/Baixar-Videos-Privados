from hashlib import sha256

from src.application.ports.download_queue_port import DownloadQueuePort
from src.application.ports.download_job_repository_port import DownloadJobRepositoryPort
from src.api.schemas.download_schema import CreateDownloadResponse, DownloadRequest
from src.domain.policies.authorization_policy import AuthorizationPolicy
from src.domain.entities.download_job import DownloadJob
from src.domain.value_objects.authorization_context import AuthorizationContext
from src.infrastructure.cache.memory.authorization_cache import AuthorizationCache
from src.infrastructure.observability.metrics_registry import MetricsRegistry
from src.shared.security.request_rate_limiter import RequesterRateLimiter
from src.shared.exceptions.errors import AppError, DownloadFailureError


class CreateDownloadUseCase:
    def __init__(
        self,
        authorization_cache: AuthorizationCache,
        download_job_repository: DownloadJobRepositoryPort,
        download_queue: DownloadQueuePort,
        requester_rate_limiter: RequesterRateLimiter,
        default_quality_preference: str,
        metrics_registry: MetricsRegistry,
        public_failure_message: str,
    ) -> None:
        self._authorization_cache = authorization_cache
        self._download_job_repository = download_job_repository
        self._download_queue = download_queue
        self._requester_rate_limiter = requester_rate_limiter
        self._default_quality_preference = default_quality_preference
        self._metrics_registry = metrics_registry
        self._public_failure_message = public_failure_message

    async def execute(self, request: DownloadRequest) -> CreateDownloadResponse:
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

            self._requester_rate_limiter.consume(request.requester_id)

            quality_preference = request.quality_preference or self._default_quality_preference

            resolved_download_id = request.download_id or self._generate_download_id(request)
            job = DownloadJob.new(
                download_id=resolved_download_id,
                provider=request.provider,
                video_reference=request.video_reference,
                quality_preference=quality_preference,
                requester_id=request.requester_id,
                session_proof=request.authorization.session_proof,
                entitlement_proof=request.authorization.entitlement_proof,
            )
            saved_job, created = self._download_job_repository.create_if_absent(job)
            if created:
                await self._download_queue.enqueue(saved_job.download_id)
                self._metrics_registry.inc_counter("jobs_created_total")

            return CreateDownloadResponse(
                success=True,
                message=(
                    "Download autorizado e enfileirado."
                    if created
                    else "Requisicao ja registrada para este download_id."
                ),
                status="accepted",
                provider=saved_job.provider,
                download_id=saved_job.download_id,
                queue_status=saved_job.queue_status,
            )
        except AppError:
            raise
        except Exception as exc:
            raise DownloadFailureError(
                public_message=self._public_failure_message,
                internal_detail=f"enqueue_download_error={exc}",
            ) from exc

    @staticmethod
    def _generate_download_id(request: DownloadRequest) -> str:
        fingerprint = "|".join(
            [
                request.provider,
                request.video_reference,
                request.quality_preference,
                request.requester_id,
            ]
        )
        return f"dl-{sha256(fingerprint.encode('utf-8')).hexdigest()[:20]}"
