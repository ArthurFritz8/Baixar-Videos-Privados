from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.application.ports.provider_port import (
    ProviderDownloadRequest,
    ProviderDownloadResult,
    ProviderPort,
)
from src.shared.exceptions.errors import (
    ProviderContractViolationError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


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
        lowered_reference = request.video_reference.lower()
        if lowered_reference.startswith("blocked"):
            raise ProviderUnavailableError(
                public_message=self._public_failure_message,
                internal_detail="panda_provider_blocked_reference",
            )
        if "timeout" in lowered_reference:
            raise ProviderTimeoutError(
                public_message=self._public_failure_message,
                internal_detail="panda_provider_timeout_reference",
            )

        if "invalid_payload" in lowered_reference:
            raw_payload = {
                "status": "accepted",
                "artifact_location": None,
            }
        else:
            raw_payload = {
                "ticket_id": f"pan-{uuid4().hex[:12]}",
                "status": "accepted",
                "artifact_location": None,
            }

        try:
            payload = PandaTicketPayload.model_validate(raw_payload)
        except ValidationError as exc:
            raise ProviderContractViolationError(
                public_message=self._public_failure_message,
                internal_detail=f"panda_invalid_contract={exc.errors()}",
            ) from exc
        return ProviderDownloadResult(
            provider=self.provider_name,
            download_id=payload.ticket_id,
            status=payload.status,
            artifact_location=payload.artifact_location,
        )
