from __future__ import annotations

import base64
import hmac
from datetime import UTC, datetime, timedelta
from hashlib import sha256


class DownloadFileTokenService:
    def __init__(self, secret: str, ttl_seconds: int) -> None:
        self._secret = secret.encode("utf-8")
        self._ttl_seconds = ttl_seconds

    def generate(self, download_id: str) -> tuple[str, datetime]:
        expires_at = datetime.now(UTC) + timedelta(seconds=self._ttl_seconds)
        payload = f"{download_id}:{int(expires_at.timestamp())}"
        signature = self._sign(payload)
        raw = f"{payload}:{signature}".encode("utf-8")
        token = base64.urlsafe_b64encode(raw).decode("utf-8")
        return token, expires_at

    def validate(self, download_id: str, token: str) -> bool:
        try:
            decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
            parts = decoded.split(":")
            if len(parts) != 3:
                return False

            token_download_id, expires_ts_str, signature = parts
            if token_download_id != download_id:
                return False

            payload = f"{token_download_id}:{expires_ts_str}"
            expected_signature = self._sign(payload)
            if not hmac.compare_digest(signature, expected_signature):
                return False

            expires_at = datetime.fromtimestamp(int(expires_ts_str), UTC)
            return expires_at >= datetime.now(UTC)
        except Exception:
            return False

    def _sign(self, payload: str) -> str:
        return hmac.new(self._secret, payload.encode("utf-8"), sha256).hexdigest()
