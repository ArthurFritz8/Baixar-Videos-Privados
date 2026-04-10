from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AuthorizationProof(BaseModel):
    session_proof: str = Field(min_length=8, max_length=2048)
    entitlement_proof: str = Field(min_length=8, max_length=2048)

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )


class DownloadRequest(BaseModel):
    provider: Literal["panda_video", "hotmart"]
    video_reference: str = Field(min_length=3, max_length=256)
    requester_id: str = Field(min_length=3, max_length=128)
    authorization: AuthorizationProof
    prefer_cached_authorization: bool = True

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )


class DownloadResponse(BaseModel):
    success: bool
    message: str
    status: Literal["accepted", "failed"]
    code: str | None = None
    provider: str | None = None
    download_id: str | None = None
    artifact_location: str | None = None

    model_config = ConfigDict(extra="forbid", strict=True)
