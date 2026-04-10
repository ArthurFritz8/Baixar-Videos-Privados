from src.application.ports.provider_port import ProviderPort
from src.shared.exceptions.errors import ProviderNotSupportedError


class ProviderRegistry:
    def __init__(self, providers: list[ProviderPort]) -> None:
        self._providers = {provider.provider_name: provider for provider in providers}

    def get(self, provider_name: str, public_failure_message: str) -> ProviderPort:
        provider = self._providers.get(provider_name)
        if provider is None:
            raise ProviderNotSupportedError(
                public_message=public_failure_message,
                internal_detail=f"unsupported_provider={provider_name}",
            )
        return provider
