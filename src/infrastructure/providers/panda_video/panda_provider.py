from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.application.ports.provider_port import (
    ProviderDownloadRequest,
    ProviderDownloadResult,
    ProviderPort,
)
from src.shared.exceptions.errors import ProviderUnavailableError


class PandaTicketPayload(BaseModel):
    ticket_id: str = Field(min_length=4)
    status: str
    artifact_location: str | None = None

    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class PandaVideoProvider(ProviderPort):
    provider_name = "panda_video"

    def __init__(self, public_failure_message: str) -> None:
        self._public_failure_message = public_failure_message

    async def request_download_ticket(
        self, request: ProviderDownloadRequest
    ) -> ProviderDownloadResult:
        if request.video_reference.lower().startswith("blocked"):
            raise ProviderUnavailableError(
                public_message=self._public_failure_message,
                internal_detail="panda_provider_blocked_reference",
            )

        raw_payload = {
            "ticket_id": f"pan-{uuid4().hex[:12]}",
            "status": "accepted",
            "artifact_location": None,
        }
        payload = PandaTicketPayload.model_validate(raw_payload)
        return ProviderDownloadResult(
            provider=self.provider_name,
            download_id=payload.ticket_id,
            status=payload.status,
            artifact_location=payload.artifact_location,
        )
