from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorizationContext:
    provider: str
    video_reference: str
    requester_id: str
    session_proof: str
    entitlement_proof: str
