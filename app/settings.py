from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    llm_model: str
    llm_api_key: str | None
    llm_timeout_s: float
    db_path: Path
    log_file: Path
    app_version: str
    mock_delay_ms: int
    mock_failure_rate: float
    mock_failure_kind: str

    @classmethod
    def from_env(cls) -> "Settings":
        provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()
        if provider not in {"mock", "gemini_compat"}:
            raise ValueError("Invalid LLM_PROVIDER. Allowed values: mock, gemini_compat.")

        key = (
            os.getenv("LLM_API_KEY", "").strip()
            or os.getenv("GEMINI_API_KEY", "").strip()
            or None
        )
        if provider != "mock" and not key:
            raise ValueError(
                "LLM_API_KEY or GEMINI_API_KEY is required when LLM_PROVIDER is not mock."
            )

        try:
            timeout = float(os.getenv("LLM_TIMEOUT_S", "30"))
            delay = int(os.getenv("MOCK_DELAY_MS", "0"))
            failure_rate = float(os.getenv("MOCK_FAILURE_RATE", "0"))
        except ValueError as exc:
            raise ValueError("LLM_TIMEOUT_S, MOCK_DELAY_MS, and MOCK_FAILURE_RATE must be numeric.") from exc

        if timeout <= 0:
            raise ValueError("LLM_TIMEOUT_S must be greater than zero.")
        if delay < 0:
            raise ValueError("MOCK_DELAY_MS cannot be negative.")
        if not 0 <= failure_rate <= 1:
            raise ValueError("MOCK_FAILURE_RATE must be between 0 and 1.")

        failure_kind = os.getenv("MOCK_FAILURE_KIND", "unavailable").strip().lower()
        if failure_kind not in {"timeout", "rate_limit", "unavailable", "invalid_json", "mid_stream"}:
            raise ValueError("Invalid MOCK_FAILURE_KIND.")

        return cls(
            llm_provider=provider,
            llm_model=os.getenv("LLM_MODEL", "mock-syllabus-v1").strip() or "mock-syllabus-v1",
            llm_api_key=key,
            llm_timeout_s=timeout,
            db_path=Path(os.getenv("DB_PATH", "data/smart_syllabus.sqlite3")),
            log_file=Path(os.getenv("LOG_FILE", "logs/app.log")),
            app_version=os.getenv("APP_VERSION", "dev").strip() or "dev",
            mock_delay_ms=delay,
            mock_failure_rate=failure_rate,
            mock_failure_kind=failure_kind,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
