import asyncio
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
        lowered_reference = request.video_reference.lower()
        if "slow" in lowered_reference:
            await asyncio.sleep(0.4)

        if "offline" in lowered_reference:
            raise ProviderUnavailableError(
                public_message=self._public_failure_message,
                internal_detail="hotmart_provider_offline_reference",
            )
        if "timeout" in lowered_reference:
            raise ProviderTimeoutError(
                public_message=self._public_failure_message,
                internal_detail="hotmart_provider_timeout_reference",
            )

        if "invalid_payload" in lowered_reference:
            raw_payload = {
                "status": "accepted",
                "artifact_location": None,
            }
        else:
            raw_payload = {
                "ticket_id": f"hot-{uuid4().hex[:12]}",
                "status": "accepted",
                "artifact_location": None,
            }

        try:
            payload = HotmartTicketPayload.model_validate(raw_payload)
        except ValidationError as exc:
            raise ProviderContractViolationError(
                public_message=self._public_failure_message,
                internal_detail=f"hotmart_invalid_contract={exc.errors()}",
            ) from exc
        return ProviderDownloadResult(
            provider=self.provider_name,
            download_id=payload.ticket_id,
            status=payload.status,
            artifact_location=payload.artifact_location,
        )
