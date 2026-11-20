from app.gateways.llm_gateway import LLMGateway
from app.models import ProviderRequest, SyllabusExtraction
from app.telemetry import log_event


class AIOrchestrator:
    """PR15 extension point for prompts, context assembly, and model policies."""

    def __init__(self, gateway: LLMGateway) -> None:
        self.gateway = gateway

    def extract(self, request: ProviderRequest) -> SyllabusExtraction:
        log_event(request.request_id, "orchestration", "Running PR14 placeholder orchestration")
        return self.gateway.extract(request)
