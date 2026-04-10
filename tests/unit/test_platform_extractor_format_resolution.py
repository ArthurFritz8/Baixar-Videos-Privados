from src.infrastructure.storage.local.platform_extractor_downloader import (
    PlatformExtractorDownloader,
)


def test_format_resolution_avoids_merge_for_video_profiles() -> None:
    assert "+" not in PlatformExtractorDownloader._resolve_format("best")
    assert "+" not in PlatformExtractorDownloader._resolve_format("high")
    assert "+" not in PlatformExtractorDownloader._resolve_format("medium")
    assert "+" not in PlatformExtractorDownloader._resolve_format("low")


def test_format_resolution_audio_profile_keeps_audio_selector() -> None:
    assert PlatformExtractorDownloader._resolve_format("audio") == "bestaudio/best"
