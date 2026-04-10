from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Literal

QueueStatus = Literal["queued", "processing", "completed", "failed"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DownloadJob:
    download_id: str
    provider: Literal["panda_video", "hotmart"]
    video_reference: str
    requester_id: str
    session_proof: str
    entitlement_proof: str
    queue_status: QueueStatus
    created_at: datetime
    updated_at: datetime
    attempt_count: int = 0
    artifact_location: str | None = None
    error_code: str | None = None

    @classmethod
    def new(
        cls,
        download_id: str,
        provider: Literal["panda_video", "hotmart"],
        video_reference: str,
        requester_id: str,
        session_proof: str,
        entitlement_proof: str,
    ) -> "DownloadJob":
        now = _utc_now()
        return cls(
            download_id=download_id,
            provider=provider,
            video_reference=video_reference,
            requester_id=requester_id,
            session_proof=session_proof,
            entitlement_proof=entitlement_proof,
            queue_status="queued",
            created_at=now,
            updated_at=now,
        )

    def to_processing(self) -> "DownloadJob":
        return replace(self, queue_status="processing", updated_at=_utc_now(), error_code=None)

    def to_completed(
        self,
        artifact_location: str | None,
        attempt_count: int,
    ) -> "DownloadJob":
        return replace(
            self,
            queue_status="completed",
            artifact_location=artifact_location,
            attempt_count=attempt_count,
            error_code=None,
            updated_at=_utc_now(),
        )

    def to_failed(self, error_code: str, attempt_count: int) -> "DownloadJob":
        return replace(
            self,
            queue_status="failed",
            error_code=error_code,
            attempt_count=attempt_count,
            updated_at=_utc_now(),
        )
