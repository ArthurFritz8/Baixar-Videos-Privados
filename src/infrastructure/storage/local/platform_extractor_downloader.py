import asyncio
from pathlib import Path
from urllib.parse import urlparse

from src.shared.exceptions.errors import SourceDownloadFailedError

SUPPORTED_PLATFORM_HOSTS = {
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "tiktok.com",
    "facebook.com",
    "fb.watch",
    "x.com",
    "twitter.com",
    "vimeo.com",
    "player.vimeo.com",
}


class PlatformExtractorDownloader:
    def __init__(
        self,
        output_dir: str,
        enabled: bool,
        public_failure_message: str,
    ) -> None:
        self._output_dir = Path(output_dir)
        self._enabled = enabled
        self._public_failure_message = public_failure_message

    def supports(self, source_url: str) -> bool:
        parsed = urlparse(source_url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme.lower() not in ("http", "https"):
            return False
        if not host:
            return False

        for supported_host in SUPPORTED_PLATFORM_HOSTS:
            if host == supported_host or host.endswith(f".{supported_host}"):
                return True
        return False

    async def download(self, source_url: str, download_id: str) -> str:
        if not self._enabled:
            raise SourceDownloadFailedError(
                public_message=self._public_failure_message,
                internal_detail="platform_extractor_disabled",
            )

        try:
            import yt_dlp
        except Exception as exc:
            raise SourceDownloadFailedError(
                public_message=self._public_failure_message,
                internal_detail=f"platform_extractor_dependency_missing={exc}",
            ) from exc

        self._output_dir.mkdir(parents=True, exist_ok=True)
        output_template = str(self._output_dir / f"{download_id}.%(ext)s")

        ydl_opts = {
            "outtmpl": output_template,
            "format": "best[ext=mp4]/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "restrictfilenames": True,
            "overwrites": True,
            "nopart": True,
            "cachedir": False,
        }

        def _run_extract() -> None:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(source_url, download=True)

        try:
            await asyncio.to_thread(_run_extract)
        except Exception as exc:
            raise SourceDownloadFailedError(
                public_message=self._public_failure_message,
                internal_detail=f"platform_extractor_error={exc}",
            ) from exc

        candidates = [
            candidate
            for candidate in self._output_dir.glob(f"{download_id}.*")
            if candidate.is_file() and not candidate.name.endswith((".part", ".ytdl"))
        ]
        if not candidates:
            raise SourceDownloadFailedError(
                public_message=self._public_failure_message,
                internal_detail="platform_extractor_no_output",
            )

        candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
        return str(candidates[0])
