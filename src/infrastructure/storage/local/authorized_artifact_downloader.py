from pathlib import Path
from urllib.parse import urlparse

import httpx

from src.shared.exceptions.errors import SourceDownloadFailedError, SourceNotAllowedError


class AuthorizedArtifactDownloader:
    def __init__(
        self,
        output_dir: str,
        http_timeout_seconds: float,
        allowed_source_hosts: set[str],
        public_failure_message: str,
    ) -> None:
        self._output_dir = Path(output_dir)
        self._http_timeout_seconds = http_timeout_seconds
        self._allowed_source_hosts = {host.strip().lower() for host in allowed_source_hosts}
        self._public_failure_message = public_failure_message

    async def download(self, source_url: str, download_id: str) -> str:
        parsed = urlparse(source_url)
        scheme = parsed.scheme.lower()
        host = (parsed.hostname or "").lower()

        if scheme not in ("http", "https"):
            raise SourceNotAllowedError(
                public_message=self._public_failure_message,
                internal_detail=f"source_scheme_not_allowed={scheme}",
            )

        if self._allowed_source_hosts and host not in self._allowed_source_hosts:
            raise SourceNotAllowedError(
                public_message=self._public_failure_message,
                internal_detail=f"source_host_not_allowed={host}",
            )

        suffix = Path(parsed.path).suffix
        if not suffix:
            suffix = ".bin"

        self._output_dir.mkdir(parents=True, exist_ok=True)
        local_path = self._output_dir / f"{download_id}{suffix}"

        timeout = httpx.Timeout(self._http_timeout_seconds)
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                async with client.stream("GET", source_url) as response:
                    response.raise_for_status()
                    content_type = (response.headers.get("content-type") or "").lower()
                    if content_type.startswith("text/html"):
                        raise SourceDownloadFailedError(
                            public_message=self._public_failure_message,
                            internal_detail=(
                                "source_download_unexpected_html "
                                f"content_type={content_type or 'missing'}"
                            ),
                        )
                    with local_path.open("wb") as output:
                        async for chunk in response.aiter_bytes():
                            output.write(chunk)
        except httpx.HTTPError as exc:
            raise SourceDownloadFailedError(
                public_message=self._public_failure_message,
                internal_detail=f"source_download_http_error={exc}",
            ) from exc
        except OSError as exc:
            raise SourceDownloadFailedError(
                public_message=self._public_failure_message,
                internal_detail=f"source_download_io_error={exc}",
            ) from exc

        return str(local_path)
