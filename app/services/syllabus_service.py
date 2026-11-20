from app.ai.orchestration import AIOrchestrator
from app.models import ParseRequest, ParseResponse, ProviderRequest
from app.storage import SQLiteStorage
from app.telemetry import log_event


class SyllabusService:
    def __init__(self, orchestrator: AIOrchestrator, storage: SQLiteStorage, model: str) -> None:
        self.orchestrator = orchestrator
        self.storage = storage
        self.model = model

    def parse(self, request: ParseRequest, request_id: str) -> ParseResponse:
        log_event(request_id, "service", "Starting syllabus extraction")
        result = self.orchestrator.extract(
            ProviderRequest(
                request_id=request_id,
                source_text=request.source_text,
                case_id=request.case_id,
                model=self.model,
            )
        )
        record = self.storage.save(result, request_id)
        log_event(request_id, "service", "Syllabus extraction completed")
        return ParseResponse(record_id=record.record_id, result=record.result)
