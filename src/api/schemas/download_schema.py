from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProviderName = Literal[
    "panda_video",
    "hotmart",
    "youtube",
    "instagram",
    "tiktok",
    "facebook",
    "x",
    "vimeo",
]


class AuthorizationProof(BaseModel):
    session_proof: str = Field(min_length=8, max_length=2048)
    entitlement_proof: str = Field(min_length=8, max_length=2048)

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )


class DownloadRequest(BaseModel):
    provider: ProviderName
    video_reference: str = Field(min_length=3, max_length=2048)
    requester_id: str = Field(min_length=3, max_length=128)
    download_id: str | None = Field(default=None, min_length=8, max_length=128)
    authorization: AuthorizationProof
    prefer_cached_authorization: bool = True

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )


class CreateDownloadResponse(BaseModel):
    success: bool
    message: str
    status: Literal["accepted"]
    provider: ProviderName
    download_id: str
    queue_status: Literal["queued", "processing", "completed", "failed", "canceled"]
    code: str | None = None

    model_config = ConfigDict(extra="forbid", strict=True)


class DownloadStatusResponse(BaseModel):
    success: bool
    message: str
    provider: ProviderName
    download_id: str
    queue_status: Literal["queued", "processing", "completed", "failed", "canceled"]
    artifact_location: str | None = None
    code: str | None = None

    model_config = ConfigDict(extra="forbid", strict=True)


class CancelDownloadResponse(BaseModel):
    success: bool
    message: str
    provider: ProviderName
    download_id: str
    queue_status: Literal["canceled"]
    code: str | None = None

    model_config = ConfigDict(extra="forbid", strict=True)
