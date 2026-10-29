from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .settings import settings


def _paths() -> tuple[Path, Path]:
    root = Path(settings.storage_dir).resolve()
    files = root / "files"
    root.mkdir(parents=True, exist_ok=True)
    files.mkdir(parents=True, exist_ok=True)
    return root / "buildsight.sqlite3", files


def initialize_storage() -> None:
    database, _ = _paths()
    with sqlite3.connect(database) as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS records (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL, created_at TEXT NOT NULL,
            result_json TEXT NOT NULL, image_path TEXT)""")


def save_record(kind: str, result: dict, image: bytes | None = None, mime_type: str | None = None) -> str:
    database, files = _paths()
    record_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    image_path = None
    if image:
        suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(mime_type or "", ".bin")
        image_path = str((files / f"{record_id}{suffix}").resolve())
        Path(image_path).write_bytes(image)
    try:
        with sqlite3.connect(database) as connection:
            connection.execute("INSERT INTO records VALUES (?, ?, ?, ?, ?)",
                               (record_id, kind, created_at, json.dumps(result), image_path))
    except Exception:
        if image_path:
            Path(image_path).unlink(missing_ok=True)
        raise
    return record_id


def get_record(record_id: str) -> dict | None:
    database, _ = _paths()
    with sqlite3.connect(database) as connection:
        row = connection.execute("SELECT id, kind, created_at, result_json, image_path FROM records WHERE id = ?",
                                 (record_id,)).fetchone()
    if not row:
        return None
    return {"id": row[0], "kind": row[1], "created_at": row[2], "result": json.loads(row[3]),
            "image_available": bool(row[4] and Path(row[4]).is_file())}


def list_records(limit: int = 20) -> list[dict]:
    database, _ = _paths()
    with sqlite3.connect(database) as connection:
        rows = connection.execute("SELECT id, kind, created_at, result_json, image_path FROM records "
                                  "ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [{"id": row[0], "kind": row[1], "created_at": row[2], "result": json.loads(row[3]),
             "image_available": bool(row[4] and Path(row[4]).is_file())} for row in rows]
