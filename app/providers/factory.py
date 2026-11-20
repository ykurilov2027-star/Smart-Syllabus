from app.providers.base import Provider
from app.providers.gemini_compat import GeminiCompatibleProvider
from app.providers.mock import MockProvider
from app.settings import Settings


def create_provider(settings: Settings) -> Provider:
    if settings.llm_provider == "mock":
        return MockProvider(settings)
    if settings.llm_provider == "gemini_compat":
        return GeminiCompatibleProvider()
    raise ValueError("Unsupported LLM provider configuration.")
