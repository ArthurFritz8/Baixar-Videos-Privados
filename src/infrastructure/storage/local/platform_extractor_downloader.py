import asyncio
import os
import re
import shutil
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.shared.exceptions.errors import SourceDownloadFailedError

SUPPORTED_PLATFORM_HOSTS = {
    "pandavideo.com.br",
    "tv.pandavideo.com.br",
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
        concurrent_fragment_downloads: int = 8,
    ) -> None:
        self._output_dir = Path(output_dir)
        self._enabled = enabled
        self._concurrent_fragment_downloads = max(1, concurrent_fragment_downloads)
        self._public_failure_message = public_failure_message

    def supports(self, source_url: str) -> bool:
        if not self._enabled:
            return False

        parsed = urlparse(source_url)
        host = (parsed.hostname or "").lower()
        path = (parsed.path or "").lower()
        query = (parsed.query or "").lower()
        normalized_url = source_url.lower()
        if parsed.scheme.lower() not in ("http", "https"):
            return False
        if not host:
            return False

        for supported_host in SUPPORTED_PLATFORM_HOSTS:
            if host == supported_host or host.endswith(f".{supported_host}"):
                return True

        # Para hosts nao catalogados, tenta extractor em URLs tipicas de player/stream.
        if (
            ".m3u8" in normalized_url
            or ".mpd" in normalized_url
            or "manifest" in normalized_url
            or "playlist" in normalized_url
            or path.endswith(".html")
            or "/player" in path
            or "/embed" in path
            or "m3u8" in query
        ):
            return True

        return False

    async def download(
        self,
        source_url: str,
        download_id: str,
        quality_preference: str,
    ) -> str:
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
        resolved_source_url = self._resolve_source_url(source_url)
        output_template = str(self._output_dir / f"{download_id}.%(ext)s")
        ffmpeg_location = self._resolve_ffmpeg_location()

        ydl_opts = {
            "outtmpl": output_template,
            "format": self._resolve_format(quality_preference),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "restrictfilenames": True,
            "overwrites": True,
            "nopart": True,
            "cachedir": False,
            "concurrent_fragment_downloads": self._concurrent_fragment_downloads,
            "extractor_retries": 3,
            "geo_bypass": True,
            "legacyserverconnect": True
        }
        if ffmpeg_location:
            ydl_opts["ffmpeg_location"] = ffmpeg_location

        def _run_extract() -> None:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(resolved_source_url, download=True)

        try:
            await asyncio.to_thread(_run_extract)
        except Exception as exc:
            normalized_error_detail = self._normalize_extractor_error_detail(str(exc))
            raise SourceDownloadFailedError(
                public_message=self._public_failure_message,
                internal_detail=(
                    "platform_extractor_error="
                    f"{normalized_error_detail} source_url={resolved_source_url}"
                ),
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

    @staticmethod
    def _resolve_source_url(source_url: str) -> str:
        normalized_source_url = source_url.replace("&amp;", "&")
        parsed = urlparse(normalized_source_url)
        host = (parsed.hostname or "").lower()

        if "pandavideo.com.br" not in host:
            return normalized_source_url

        if parsed.path.rstrip("/").endswith("/embed"):
            video_id = parse_qs(parsed.query).get("v", [""])[0].strip()
            if video_id:
                return f"{parsed.scheme}://{parsed.netloc}/{video_id}/playlist.m3u8"

        return normalized_source_url

    @staticmethod
    def _resolve_format(quality_preference: str) -> str:
        normalized = (quality_preference or "best").lower()
        if normalized == "high":
            return "best[height<=1080][vcodec!=none][acodec!=none]/best[height<=1080]/best"
        if normalized == "medium":
            return "best[height<=720][vcodec!=none][acodec!=none]/best[height<=720]/best"
        if normalized == "low":
            return "best[height<=480][vcodec!=none][acodec!=none]/best[height<=480]/best"
        if normalized == "audio":
            return "bestaudio/best"
        return "best[vcodec!=none][acodec!=none]/best"

    @staticmethod
    def _strip_ansi(value: str) -> str:
        return re.sub(r"\x1b\[[0-9;]*m", "", value or "").strip()

    @classmethod
    def _normalize_extractor_error_detail(cls, value: str) -> str:
        clean_value = cls._strip_ansi(value)
        lowered = clean_value.lower()

        if "cloudflare anti-bot challenge" in lowered:
            return "source_protected_by_cloudflare_antibot_challenge"

        return clean_value

    @staticmethod
    def _resolve_ffmpeg_location() -> str | None:
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            return str(Path(ffmpeg_path).resolve().parent)

        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            winget_packages_dir = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
            if winget_packages_dir.exists():
                for candidate in winget_packages_dir.glob(
                    "Gyan.FFmpeg_*/*/bin/ffmpeg.exe"
                ):
                    return str(candidate.parent)

        return None
