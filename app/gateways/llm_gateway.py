import json

from pydantic import ValidationError

from app.errors import AppError
from app.models import ProviderRequest, SyllabusExtraction
from app.providers.base import Provider, ProviderError
from app.telemetry import log_event


class LLMGateway:
    def __init__(self, provider: Provider) -> None:
        self.provider = provider

    def extract(self, request: ProviderRequest) -> SyllabusExtraction:
        log_event(request.request_id, "gateway", "Sending structured request to provider")
        try:
            response = self.provider.generate(request)
        except ProviderError as exc:
            errors = {
                "timeout": ("timeout", "The model provider timed out.", 504, True),
                "rate_limit": ("rate_limit", "The model provider rate limit was reached.", 429, True),
                "unavailable": ("unavailable", "The model provider is unavailable.", 503, True),
                "not_implemented": (
                    "not_implemented",
                    "This model provider is not implemented in PR14.",
                    503,
                    False,
                ),
                "invalid_request": ("validation_error", "The requested example was not found.", 400, False),
            }
            kind, message, status, retryable = errors.get(
                exc.kind,
                ("unavailable", "The model provider is unavailable.", 503, True),
            )
            raise AppError(kind, message, status, retryable) from exc

        try:
            result = SyllabusExtraction.model_validate(json.loads(response.output_json))
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise AppError(
                "invalid_output",
                "The model provider returned output that does not match the required schema.",
                422,
            ) from exc
        log_event(request.request_id, "gateway", "Provider output validated")
        return result
