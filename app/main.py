import logging
from pathlib import Path
from time import perf_counter
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from app.errors import AppError, StorageConflict
from app.models import ErrorResponse, HealthResponse, ParseResponse
from app.settings import Settings, get_settings
from app.storage import SQLiteStorage
from app.telemetry import configure_logging, log_event

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(
    settings: Settings | None = None,
    storage: SQLiteStorage | None = None,
) -> FastAPI:
    config = settings or get_settings()
    configure_logging(config.log_file)
    record_store = storage or SQLiteStorage(config.db_path)
    started_at = perf_counter()
    application = FastAPI(title="Smart Syllabus", version=config.app_version)
    application.state.settings = config
    application.state.storage = record_store

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @application.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid4()))
        log_event(request_id, "controller", f"Request failed: {exc.kind}")
        body = ErrorResponse(
            error={
                "kind": exc.kind,
                "message": exc.message,
                "retryable": exc.retryable,
                "request_id": request_id,
            }
        )
        return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json"))

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid4()))
        log_event(request_id, "controller", "Request validation failed")
        body = ErrorResponse(
            error={
                "kind": "validation_error",
                "message": "Request validation failed.",
                "retryable": False,
                "request_id": request_id,
            }
        )
        return JSONResponse(status_code=400, content=body.model_dump(mode="json"))

    @application.exception_handler(StorageConflict)
    async def handle_storage_conflict(request: Request, exc: StorageConflict) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid4()))
        body = ErrorResponse(
            error={
                "kind": "conflict",
                "message": "A record with this identifier already exists.",
                "retryable": False,
                "request_id": request_id,
            }
        )
        return JSONResponse(status_code=409, content=body.model_dump(mode="json"))

    @application.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid4()))
        status_code = exc.status_code if exc.status_code in {404, 409} else 400
        kind = "not_found" if status_code == 404 else "conflict" if status_code == 409 else "bad_request"
        message = "Resource not found." if status_code == 404 else "Request could not be completed."
        body = ErrorResponse(
            error={
                "kind": kind,
                "message": message,
                "retryable": False,
                "request_id": request_id,
            }
        )
        return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid4()))
        logging.getLogger("smart_syllabus").error(
            "Unhandled request failure",
            extra={"request_id": request_id, "layer": "controller"},
        )
        body = ErrorResponse(
            error={
                "kind": "internal_error",
                "message": "The request could not be completed.",
                "retryable": False,
                "request_id": request_id,
            }
        )
        return JSONResponse(status_code=503, content=body.model_dump(mode="json"))

    @application.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @application.get("/api/health", response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse:
        request_id = request.state.request_id
        log_event(request_id, "controller", "Health check requested")
        if not request.app.state.storage.check():
            raise AppError("unavailable", "Storage is unavailable.", 503, True)
        log_event(request_id, "storage", "Storage health check passed")
        return HealthResponse(
            status="ok",
            version=config.app_version,
            provider=config.llm_provider,
            model=config.llm_model,
            mode="mock" if config.llm_provider == "mock" else "live",
            storage="ok",
            additional_component="not_loaded",
            uptime_s=round(perf_counter() - started_at, 2),
        )

    @application.get("/api/v1/syllabi/{record_id}", response_model=ParseResponse)
    async def get_syllabus(record_id: UUID, request: Request) -> ParseResponse:
        request_id = request.state.request_id
        log_event(request_id, "controller", "Syllabus record requested")
        record = request.app.state.storage.get(str(record_id), request_id)
        if record is None:
            raise AppError("not_found", "Syllabus record not found.", 404)
        return ParseResponse(record_id=record.record_id, result=record.result)

    return application


app = create_app()
