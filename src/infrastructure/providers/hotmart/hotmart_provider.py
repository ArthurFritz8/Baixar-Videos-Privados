from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.application.ports.provider_port import (
    ProviderDownloadRequest,
    ProviderDownloadResult,
    ProviderPort,
)
from src.shared.exceptions.errors import ProviderUnavailableError


class HotmartTicketPayload(BaseModel):
    ticket_id: str = Field(min_length=4)
    status: str
    artifact_location: str | None = None

    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class HotmartProvider(ProviderPort):
    provider_name = "hotmart"

    def __init__(self, public_failure_message: str) -> None:
        self._public_failure_message = public_failure_message

    async def request_download_ticket(
        self, request: ProviderDownloadRequest
    ) -> ProviderDownloadResult:
        if "offline" in request.video_reference.lower():
            raise ProviderUnavailableError(
                public_message=self._public_failure_message,
                internal_detail="hotmart_provider_offline_reference",
            )

        raw_payload = {
            "ticket_id": f"hot-{uuid4().hex[:12]}",
            "status": "accepted",
            "artifact_location": None,
        }
        payload = HotmartTicketPayload.model_validate(raw_payload)
        return ProviderDownloadResult(
            provider=self.provider_name,
            download_id=payload.ticket_id,
            status=payload.status,
            artifact_location=payload.artifact_location,
        )
