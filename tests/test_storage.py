from pathlib import Path

import pytest

from app.errors import StorageConflict
from app.models import SyllabusExtraction
from app.storage import SQLiteStorage


def test_sqlite_storage_round_trips_structured_result(tmp_path: Path) -> None:
    storage = SQLiteStorage(tmp_path / "temporary.sqlite3")
    result = SyllabusExtraction.model_validate(
        {
            "deadlines": [{"title": "Exam", "due_date": "2026-12-01"}],
            "topics": [{"title": "Methods"}],
            "scores": [{"name": "Exam", "points": 20, "max_points": 100}],
        }
    )

    saved = storage.save(result, "storage-request", record_id="record-1")
    loaded = storage.get(saved.record_id, "storage-request")

    assert loaded is not None
    assert loaded.result == result
    assert storage.check()


def test_sqlite_storage_reports_duplicate_record(tmp_path: Path) -> None:
    storage = SQLiteStorage(tmp_path / "temporary.sqlite3")
    result = SyllabusExtraction()
    storage.save(result, "first", record_id="duplicate")

    with pytest.raises(StorageConflict):
        storage.save(result, "second", record_id="duplicate")
