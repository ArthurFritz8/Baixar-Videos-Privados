from fastapi import Request

from src.shared.exceptions.errors import ApiKeyInvalidError


class ApiKeyAuthenticator:
    def __init__(
        self,
        header_name: str,
        expected_api_key: str,
        public_failure_message: str,
    ) -> None:
        self._header_name = header_name
        self._expected_api_key = expected_api_key
        self._public_failure_message = public_failure_message

    async def __call__(self, request: Request) -> None:
        if not self._expected_api_key:
            return

        provided = request.headers.get(self._header_name)
        if not provided or provided != self._expected_api_key:
            raise ApiKeyInvalidError(
                public_message=self._public_failure_message,
                internal_detail="api_key_invalid_or_missing",
            )
