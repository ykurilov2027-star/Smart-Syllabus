import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import ParseRequest
from app.services.syllabus_service import SyllabusService
from app.settings import Settings
from app.storage import SQLiteStorage


def make_settings(
    tmp_path: Path,
    *,
    failure_rate: float = 0,
    failure_kind: str = "unavailable",
) -> Settings:
    return Settings(
        llm_provider="mock",
        llm_model="test-mock",
        llm_api_key=None,
        llm_timeout_s=1,
        db_path=tmp_path / "records.sqlite3",
        log_file=tmp_path / "app.log",
        app_version="test",
        mock_delay_ms=0,
        mock_failure_rate=failure_rate,
        mock_failure_kind=failure_kind,
    )


def test_api_parse_uses_mock_and_correlates_layer_logs(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    application = create_app(settings, SQLiteStorage(settings.db_path))

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/syllabi/parse",
            json={"source_text": "Final essay due 2026-12-10", "case_id": "intro-course"},
        )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"record_id", "result"}
    assert body["result"]["deadlines"][0]["due_date"] == "2026-12-10"
    assert body["result"]["topics"][0]["title"] == "Research methods"
    assert body["result"]["scores"][0]["points"] == 30

    request_id = response.headers["X-Request-ID"]
    log_lines = settings.log_file.read_text(encoding="utf-8").splitlines()
    request_lines = [line for line in log_lines if f"request_id={request_id}" in line]
    layers = {re.search(r"layer=(\w+)", line).group(1) for line in request_lines}
    assert {"controller", "service", "orchestration", "gateway", "provider", "storage"} <= layers
    assert all(re.search(r"request_id=([0-9a-f-]+)", line).group(1) == request_id for line in request_lines)


def test_application_service_runs_without_http(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    application = create_app(settings, SQLiteStorage(settings.db_path))
    service = application.state.service

    assert isinstance(service, SyllabusService)
    response = service.parse(
        ParseRequest(source_text="Project demo", case_id="project-course"),
        request_id="direct-service-request",
    )

    assert response.result.deadlines[0].title == "Project demonstration"
    stored = application.state.storage.get(response.record_id, "direct-service-request")
    assert stored is not None
    assert stored.result.scores[0].max_points == 100


@pytest.mark.parametrize(
    ("failure_kind", "status_code", "error_kind"),
    [
        ("timeout", 504, "timeout"),
        ("rate_limit", 429, "rate_limit"),
        ("unavailable", 503, "unavailable"),
        ("invalid_json", 422, "invalid_output"),
        ("mid_stream", 422, "invalid_output"),
    ],
)
def test_mock_failures_use_unified_error_contract(
    tmp_path: Path,
    failure_kind: str,
    status_code: int,
    error_kind: str,
) -> None:
    settings = make_settings(tmp_path, failure_rate=1, failure_kind=failure_kind)
    application = create_app(settings, SQLiteStorage(settings.db_path))

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/syllabi/parse",
            json={"source_text": "A course syllabus"},
        )

    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"kind", "message", "retryable", "request_id"}
    assert body["error"]["kind"] == error_kind
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]


def test_health_reports_mock_without_calling_model(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, failure_rate=1, failure_kind="unavailable")
    application = create_app(settings, SQLiteStorage(settings.db_path))

    with TestClient(application) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["provider"] == "mock"
    assert response.json()["storage"] == "ok"
    assert response.json()["additional_component"] == "not_loaded"
    assert "llm_api_key" not in response.text.lower()


def test_settings_require_key_for_non_mock_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini_compat")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="LLM_API_KEY or GEMINI_API_KEY is required"):
        Settings.from_env()


def test_settings_accept_gemini_compatibility_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini_compat")
    monkeypatch.setenv("LLM_API_KEY", " ")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-logged")

    assert Settings.from_env().llm_api_key == "test-key-not-logged"
