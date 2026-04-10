from hashlib import sha256

from src.domain.value_objects.authorization_context import AuthorizationContext
from src.shared.exceptions.errors import AuthorizationDeniedError


class AuthorizationPolicy:
    @staticmethod
    def build_cache_key(context: AuthorizationContext) -> str:
        payload = "|".join(
            [
                context.provider,
                context.video_reference,
                context.requester_id,
                context.session_proof,
                context.entitlement_proof,
            ]
        )
        return f"auth:{sha256(payload.encode('utf-8')).hexdigest()}"

    @staticmethod
    def enforce_combined_proof(
        context: AuthorizationContext,
        public_failure_message: str,
    ) -> None:
        if context.session_proof == context.entitlement_proof:
            raise AuthorizationDeniedError(
                public_message=public_failure_message,
                internal_detail="session_proof_equals_entitlement_proof",
            )
        if len(context.session_proof) < 8 or len(context.entitlement_proof) < 8:
            raise AuthorizationDeniedError(
                public_message=public_failure_message,
                internal_detail="authorization_proof_too_short",
            )
        if not context.requester_id.strip():
            raise AuthorizationDeniedError(
                public_message=public_failure_message,
                internal_detail="missing_requester_id",
            )
