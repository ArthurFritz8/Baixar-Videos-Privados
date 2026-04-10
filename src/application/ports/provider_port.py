from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderDownloadRequest:
    provider: str
    video_reference: str
    quality_preference: str
    requester_id: str
    session_proof: str
    entitlement_proof: str


@dataclass(frozen=True)
class ProviderDownloadResult:
    provider: str
    download_id: str
    status: str
    artifact_location: str | None = None


class ProviderPort(ABC):
    provider_name: str

    @abstractmethod
    async def request_download_ticket(
        self, request: ProviderDownloadRequest
    ) -> ProviderDownloadResult:
        raise NotImplementedError
