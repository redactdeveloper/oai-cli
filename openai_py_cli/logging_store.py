"""SQLite-backed request log store."""

from __future__ import annotations

import csv
import json
import sqlite3
import uuid
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RequestLog:
    id: str
    created_at: str
    command: str
    model: str
    input_text: str
    output_text: str
    status: str
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None
    request_json: str | None = None
    response_json: str | None = None
    error: str | None = None


class LoggingStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY,
                    created_at TEXT,
                    command TEXT,
                    model TEXT,
                    input_text TEXT,
                    output_text TEXT,
                    status TEXT,
                    latency_ms INTEGER,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    total_tokens INTEGER,
                    estimated_cost_usd REAL,
                    request_json TEXT,
                    response_json TEXT,
                    error TEXT
                )
                """
            )

    def insert(
        self,
        *,
        command: str,
        model: str,
        input_text: str,
        output_text: str,
        status: str,
        latency_ms: int | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
        estimated_cost_usd: float | None = None,
        request_json: dict[str, Any] | None = None,
        response_json: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> RequestLog:
        row = RequestLog(
            id=uuid.uuid4().hex[:12],
            created_at=datetime.now(timezone.utc).isoformat(),
            command=command,
            model=model,
            input_text=input_text,
            output_text=output_text,
            status=status,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
            request_json=json.dumps(request_json, ensure_ascii=False) if request_json else None,
            response_json=json.dumps(response_json, ensure_ascii=False) if response_json else None,
            error=error,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO requests VALUES (
                    :id, :created_at, :command, :model, :input_text, :output_text, :status,
                    :latency_ms, :input_tokens, :output_tokens, :total_tokens,
                    :estimated_cost_usd, :request_json, :response_json, :error
                )
                """,
                asdict(row),
            )
        return row

    def list(self, limit: int = 50) -> list[RequestLog]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM requests ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_log(row) for row in rows]

    def show(self, log_id: str) -> RequestLog | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM requests WHERE id = ?", (log_id,)).fetchone()
        return self._row_to_log(row) if row else None

    def delete(self, log_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM requests WHERE id = ?", (log_id,))
        return cursor.rowcount > 0

    def clear(self) -> int:
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
            conn.execute("DELETE FROM requests")
        return int(count)

    def export(self, fmt: str) -> str:
        rows = [asdict(row) for row in self.list(limit=10_000)]
        if fmt == "json":
            return json.dumps(rows, indent=2, ensure_ascii=False)
        if fmt == "jsonl":
            return "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
        if fmt == "csv":
            return _to_csv(rows)
        raise ValueError(f"Unsupported export format: {fmt}")

    @staticmethod
    def _row_to_log(row: sqlite3.Row) -> RequestLog:
        return RequestLog(**dict(row))


def _to_csv(rows: Iterable[dict[str, Any]]) -> str:
    rows = list(rows)
    if not rows:
        return ""
    from io import StringIO

    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()
