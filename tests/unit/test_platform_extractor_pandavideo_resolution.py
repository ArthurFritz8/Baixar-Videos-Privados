from src.infrastructure.storage.local.platform_extractor_downloader import (
    PlatformExtractorDownloader,
)


def test_resolve_source_url_converts_pandavideo_embed_to_playlist() -> None:
    source_url = (
        "https://player-vz-f06468fb-5cb.tv.pandavideo.com.br/embed/"
        "?v=c28fc38d-d885-4127-9f67-238442b34bf4&amp;color=ff4376"
    )

    resolved = PlatformExtractorDownloader._resolve_source_url(source_url)

    assert (
        resolved
        == "https://player-vz-f06468fb-5cb.tv.pandavideo.com.br/"
        "c28fc38d-d885-4127-9f67-238442b34bf4/playlist.m3u8"
    )


def test_resolve_source_url_keeps_non_embed_links() -> None:
    source_url = "https://www.youtube.com/watch?v=28eCx9mZ72I"

    resolved = PlatformExtractorDownloader._resolve_source_url(source_url)

    assert resolved == source_url
