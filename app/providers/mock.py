import json
import random
import time
from pathlib import Path

from app.models import ProviderRequest, ProviderResponse, SyllabusExtraction
from app.providers.base import Provider, ProviderError
from app.settings import Settings
from app.telemetry import log_event


class MockProvider(Provider):
    def __init__(self, settings: Settings, cases_path: Path | None = None) -> None:
        self.settings = settings
        path = cases_path or Path(__file__).resolve().parents[2] / "eval" / "cases.json"
        with path.open(encoding="utf-8") as cases_file:
            cases = json.load(cases_file)
        self.cases = {
            case["case_id"]: SyllabusExtraction.model_validate(case["expected"])
            for case in cases
        }

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        log_event(request.request_id, "provider", "Mock provider invoked")
        delay_s = self.settings.mock_delay_ms / 1000
        if delay_s > self.settings.llm_timeout_s:
            time.sleep(self.settings.llm_timeout_s)
            raise ProviderError("timeout")
        if delay_s:
            time.sleep(delay_s)

        if random.random() < self.settings.mock_failure_rate:
            failure_kind = self.settings.mock_failure_kind
            if failure_kind in {"timeout", "rate_limit", "unavailable"}:
                raise ProviderError(failure_kind)
            malformed = "not-json" if failure_kind == "invalid_json" else '{"deadlines":['
            return ProviderResponse(output_json=malformed, model=request.model)

        if request.case_id is None:
            result = SyllabusExtraction()
        else:
            result = self.cases.get(request.case_id)
            if result is None:
                raise ProviderError("invalid_request")
        return ProviderResponse(output_json=result.model_dump_json(), model=request.model)
