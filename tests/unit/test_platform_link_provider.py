import asyncio

import pytest

from src.application.ports.provider_port import ProviderDownloadRequest
from src.infrastructure.providers.platform_links.platform_link_provider import (
    PlatformLinkProvider,
)
from src.shared.exceptions.errors import SourceNotAllowedError


def test_platform_provider_accepts_valid_youtube_host() -> None:
    provider = PlatformLinkProvider(
        provider_name="youtube",
        ticket_prefix="yt",
        allowed_hosts={"youtube.com", "youtu.be"},
        public_failure_message="Nao foi possivel baixar o video.",
    )

    result = asyncio.run(
        provider.request_download_ticket(
            ProviderDownloadRequest(
                provider="youtube",
                video_reference="https://www.youtube.com/watch?v=abc123",
                quality_preference="best",
                requester_id="user-yt-001",
                session_proof="abcdefgh",
                entitlement_proof="ijklmnop",
            )
        )
    )

    assert result.provider == "youtube"
    assert result.artifact_location == "https://www.youtube.com/watch?v=abc123"


def test_platform_provider_rejects_invalid_host() -> None:
    provider = PlatformLinkProvider(
        provider_name="youtube",
        ticket_prefix="yt",
        allowed_hosts={"youtube.com", "youtu.be"},
        public_failure_message="Nao foi possivel baixar o video.",
    )

    with pytest.raises(SourceNotAllowedError) as exc:
        asyncio.run(
            provider.request_download_ticket(
                ProviderDownloadRequest(
                    provider="youtube",
                    video_reference="https://example.com/watch?v=abc123",
                    quality_preference="best",
                    requester_id="user-yt-002",
                    session_proof="abcdefgh",
                    entitlement_proof="ijklmnop",
                )
            )
        )

    assert exc.value.code == "SOURCE_NOT_ALLOWED"
