from app.models import ProviderRequest, ProviderResponse
from app.providers.base import Provider, ProviderError


class GeminiCompatibleProvider(Provider):
    def generate(self, request: ProviderRequest) -> ProviderResponse:
        raise ProviderError("not_implemented")
