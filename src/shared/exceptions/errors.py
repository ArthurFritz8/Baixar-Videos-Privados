from dataclasses import dataclass


@dataclass
class AppError(Exception):
    code: str
    public_message: str
    status_code: int
    internal_detail: str | None = None


class DownloadFailureError(AppError):
    def __init__(self, public_message: str, internal_detail: str | None = None) -> None:
        super().__init__(
            code="DOWNLOAD_FAILED",
            public_message=public_message,
            status_code=400,
            internal_detail=internal_detail,
        )


class AuthorizationDeniedError(AppError):
    def __init__(self, public_message: str, internal_detail: str | None = None) -> None:
        super().__init__(
            code="AUTHORIZATION_DENIED",
            public_message=public_message,
            status_code=403,
            internal_detail=internal_detail,
        )


class ProviderUnavailableError(AppError):
    def __init__(self, public_message: str, internal_detail: str | None = None) -> None:
        super().__init__(
            code="PROVIDER_UNAVAILABLE",
            public_message=public_message,
            status_code=502,
            internal_detail=internal_detail,
        )


class ProviderTimeoutError(AppError):
    def __init__(self, public_message: str, internal_detail: str | None = None) -> None:
        super().__init__(
            code="PROVIDER_TIMEOUT",
            public_message=public_message,
            status_code=504,
            internal_detail=internal_detail,
        )


class ProviderContractViolationError(AppError):
    def __init__(self, public_message: str, internal_detail: str | None = None) -> None:
        super().__init__(
            code="PROVIDER_CONTRACT_VIOLATION",
            public_message=public_message,
            status_code=502,
            internal_detail=internal_detail,
        )


class ProviderNotSupportedError(AppError):
    def __init__(self, public_message: str, internal_detail: str | None = None) -> None:
        super().__init__(
            code="PROVIDER_NOT_SUPPORTED",
            public_message=public_message,
            status_code=400,
            internal_detail=internal_detail,
        )


class DownloadNotFoundError(AppError):
    def __init__(self, public_message: str, internal_detail: str | None = None) -> None:
        super().__init__(
            code="DOWNLOAD_NOT_FOUND",
            public_message=public_message,
            status_code=404,
            internal_detail=internal_detail,
        )


class DownloadCancellationNotAllowedError(AppError):
    def __init__(self, public_message: str, internal_detail: str | None = None) -> None:
        super().__init__(
            code="DOWNLOAD_CANCELLATION_NOT_ALLOWED",
            public_message=public_message,
            status_code=409,
            internal_detail=internal_detail,
        )
