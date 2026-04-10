from src.infrastructure.storage.local.platform_extractor_downloader import (
    PlatformExtractorDownloader,
)


def _build_downloader() -> PlatformExtractorDownloader:
    return PlatformExtractorDownloader(
        output_dir="downloads",
        enabled=True,
        public_failure_message="Nao foi possivel baixar o video.",
    )


def test_supports_pandavideo_embed_host() -> None:
    downloader = _build_downloader()

    assert (
        downloader.supports(
            "https://player-vz-f06468fb-5cb.tv.pandavideo.com.br/embed/?v=abc123"
        )
        is True
    )


def test_rejects_non_http_scheme() -> None:
    downloader = _build_downloader()

    assert downloader.supports("file:///tmp/video.mp4") is False
