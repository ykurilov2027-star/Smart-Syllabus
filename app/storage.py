import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.errors import StorageConflict
from app.models import StoredRecord, SyllabusExtraction
from app.telemetry import log_event


class SQLiteStorage:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS syllabus_records (
                    record_id TEXT PRIMARY KEY,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    def check(self) -> bool:
        with self._connect() as connection:
            connection.execute("SELECT 1").fetchone()
        return True

    def save(
        self,
        result: SyllabusExtraction,
        request_id: str,
        record_id: str | None = None,
    ) -> StoredRecord:
        record_id = record_id or str(uuid4())
        created_at = datetime.now(timezone.utc)
        log_event(request_id, "storage", "Saving structured result")
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO syllabus_records (record_id, result_json, created_at) VALUES (?, ?, ?)",
                    (record_id, result.model_dump_json(), created_at.isoformat()),
                )
        except sqlite3.IntegrityError as exc:
            raise StorageConflict from exc
        return StoredRecord(record_id=record_id, result=result, created_at=created_at)

    def get(self, record_id: str, request_id: str) -> StoredRecord | None:
        log_event(request_id, "storage", "Reading structured result")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT record_id, result_json, created_at FROM syllabus_records WHERE record_id = ?",
                (record_id,),
            ).fetchone()
        if row is None:
            return None
        return StoredRecord(
            record_id=row["record_id"],
            result=SyllabusExtraction.model_validate(json.loads(row["result_json"])),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
