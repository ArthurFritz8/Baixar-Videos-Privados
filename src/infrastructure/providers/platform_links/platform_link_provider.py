from urllib.parse import urlparse
from uuid import uuid4

from src.application.ports.provider_port import (
    ProviderDownloadRequest,
    ProviderDownloadResult,
    ProviderPort,
)
from src.shared.exceptions.errors import SourceNotAllowedError


class PlatformLinkProvider(ProviderPort):
    def __init__(
        self,
        provider_name: str,
        ticket_prefix: str,
        allowed_hosts: set[str],
        public_failure_message: str,
    ) -> None:
        self.provider_name = provider_name
        self._ticket_prefix = ticket_prefix
        self._allowed_hosts = {host.strip().lower() for host in allowed_hosts}
        self._public_failure_message = public_failure_message

    async def request_download_ticket(
        self, request: ProviderDownloadRequest
    ) -> ProviderDownloadResult:
        source_url = request.video_reference.strip()
        parsed = urlparse(source_url)
        scheme = parsed.scheme.lower()
        host = (parsed.hostname or "").lower()

        if scheme not in ("http", "https"):
            raise SourceNotAllowedError(
                public_message=self._public_failure_message,
                internal_detail=(
                    f"platform_provider_invalid_scheme provider={self.provider_name} "
                    f"scheme={scheme}"
                ),
            )

        if not self._is_host_allowed(host):
            raise SourceNotAllowedError(
                public_message=self._public_failure_message,
                internal_detail=(
                    f"platform_provider_host_not_allowed provider={self.provider_name} "
                    f"host={host}"
                ),
            )

        return ProviderDownloadResult(
            provider=self.provider_name,
            download_id=f"{self._ticket_prefix}-{uuid4().hex[:12]}",
            status="accepted",
            artifact_location=source_url,
        )

    def _is_host_allowed(self, host: str) -> bool:
        if not host:
            return False
        for allowed_host in self._allowed_hosts:
            if host == allowed_host or host.endswith(f".{allowed_host}"):
                return True
        return False
