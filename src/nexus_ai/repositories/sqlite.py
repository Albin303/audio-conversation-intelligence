from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from src.nexus_ai.core.paths import SQLITE_DB_PATH, ensure_runtime_dirs


_DB_LOCK = threading.Lock()


def connect(db_path: Path = SQLITE_DB_PATH) -> sqlite3.Connection:
    ensure_runtime_dirs()
    connection = sqlite3.connect(db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        connection.execute("PRAGMA journal_mode = WAL")
    except sqlite3.OperationalError:
        connection.execute("PRAGMA journal_mode = DELETE")
    return connection


def init_sqlite(db_path: Path = SQLITE_DB_PATH) -> None:
    with _DB_LOCK, connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                source_name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                transcript TEXT NOT NULL,
                language TEXT,
                duration_s REAL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_conversations_created_at
                ON conversations(created_at);

            CREATE TABLE IF NOT EXISTS follow_up_alerts (
                id TEXT PRIMARY KEY,
                follow_up_required INTEGER NOT NULL,
                customer_name TEXT NOT NULL DEFAULT '',
                company_name TEXT NOT NULL DEFAULT '',
                action_needed TEXT NOT NULL,
                priority TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                source_text TEXT NOT NULL DEFAULT '',
                created_date TEXT NOT NULL,
                status TEXT NOT NULL,
                source_name TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_follow_up_alerts_status
                ON follow_up_alerts(status);

            CREATE INDEX IF NOT EXISTS idx_follow_up_alerts_priority
                ON follow_up_alerts(priority);

            CREATE TABLE IF NOT EXISTS processing_jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                filename TEXT NOT NULL DEFAULT '',
                storage_path TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT 'audio',
                payload_json TEXT,
                progress_stage TEXT NOT NULL DEFAULT 'Queued',
                progress_percent INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                result_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_processing_jobs_status
                ON processing_jobs(status);
            """
        )
        _ensure_column(connection, "processing_jobs", "progress_stage", "TEXT NOT NULL DEFAULT 'Queued'")
        _ensure_column(connection, "processing_jobs", "progress_percent", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(connection, "processing_jobs", "payload_json", "TEXT")


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


class ConversationRepository:
    def __init__(self, db_path: Path = SQLITE_DB_PATH) -> None:
        self.db_path = db_path

    def create(
        self,
        *,
        conversation_id: str,
        source_name: str,
        source_type: str,
        transcript: str,
        created_at: str,
        language: str | None = None,
        duration_s: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with _DB_LOCK, connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO conversations (
                    id, source_name, source_type, transcript, language,
                    duration_s, metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    source_name,
                    source_type,
                    transcript,
                    language,
                    duration_s,
                    json.dumps(metadata or {}, ensure_ascii=True),
                    created_at,
                ),
            )


class FollowUpAlertRepository:
    def __init__(self, db_path: Path = SQLITE_DB_PATH) -> None:
        self.db_path = db_path

    def list(
        self,
        *,
        priority: str | None = None,
        status: str | None = None,
        customer_name: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM follow_up_alerts WHERE 1=1"
        params: list[Any] = []
        if priority:
            sql += " AND priority = ?"
            params.append(priority)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if customer_name:
            sql += " AND lower(customer_name) LIKE ?"
            params.append(f"%{customer_name.lower()}%")
        sql += " ORDER BY CASE status WHEN 'Pending' THEN 0 ELSE 1 END, created_date DESC"

        with connect(self.db_path) as connection:
            rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def save_many(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        with _DB_LOCK, connect(self.db_path) as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO follow_up_alerts (
                    id, follow_up_required, customer_name, company_name,
                    action_needed, priority, reason, source_text,
                    created_date, status, source_name, source_type
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row["id"],
                        1 if row.get("follow_up_required") else 0,
                        row.get("customer_name", ""),
                        row.get("company_name", ""),
                        row.get("action_needed", ""),
                        row.get("priority", "Low"),
                        row.get("reason", ""),
                        row.get("source_text", ""),
                        row.get("created_date", ""),
                        row.get("status", "Pending"),
                        row.get("source_name", ""),
                        row.get("source_type", ""),
                    )
                    for row in rows
                ],
            )

    def update_status(self, alert_id: str, status: str) -> dict[str, Any] | None:
        with _DB_LOCK, connect(self.db_path) as connection:
            connection.execute(
                "UPDATE follow_up_alerts SET status = ? WHERE id = ?",
                (status, alert_id),
            )
            row = connection.execute(
                "SELECT * FROM follow_up_alerts WHERE id = ?",
                (alert_id,),
            ).fetchone()
        return dict(row) if row else None


class JobRepository:
    def __init__(self, db_path: Path = SQLITE_DB_PATH) -> None:
        self.db_path = db_path

    def create(
        self,
        *,
        job_id: str,
        status: str,
        filename: str,
        storage_path: str,
        created_at: str,
        source_type: str = "audio",
        payload: dict[str, Any] | None = None,
    ) -> None:
        with _DB_LOCK, connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO processing_jobs (
                    id, status, filename, storage_path, source_type, payload_json,
                    progress_stage, progress_percent, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    status,
                    filename,
                    storage_path,
                    source_type,
                    json.dumps(payload, ensure_ascii=True) if payload is not None else None,
                    "Queued",
                    0,
                    created_at,
                    created_at,
                ),
            )

    def update(
        self,
        job_id: str,
        *,
        status: str,
        updated_at: str,
        error: str | None = None,
        result: dict[str, Any] | None = None,
        completed_at: str | None = None,
        progress_stage: str | None = None,
        progress_percent: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        with _DB_LOCK, connect(self.db_path) as connection:
            connection.execute(
                """
                UPDATE processing_jobs
                SET status = ?,
                    error = ?,
                    payload_json = COALESCE(?, payload_json),
                    result_json = ?,
                    progress_stage = COALESCE(?, progress_stage),
                    progress_percent = COALESCE(?, progress_percent),
                    updated_at = ?,
                    completed_at = COALESCE(?, completed_at)
                WHERE id = ?
                """,
                (
                    status,
                    error,
                    json.dumps(payload, ensure_ascii=True) if payload is not None else None,
                    json.dumps(result, ensure_ascii=True) if result is not None else None,
                    progress_stage,
                    progress_percent,
                    updated_at,
                    completed_at,
                    job_id,
                ),
            )

    def get(self, job_id: str) -> dict[str, Any] | None:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM processing_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        if not row:
            return None
        payload = dict(row)
        payload_json = payload.pop("payload_json", None)
        result_json = payload.pop("result_json", None)
        payload["payload"] = json.loads(payload_json) if payload_json else None
        payload["result"] = json.loads(result_json) if result_json else None
        return payload

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT * FROM processing_jobs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        jobs: list[dict[str, Any]] = []
        for row in rows:
            payload = dict(row)
            payload_json = payload.pop("payload_json", None)
            result_json = payload.pop("result_json", None)
            payload["payload"] = json.loads(payload_json) if payload_json else None
            payload["result"] = json.loads(result_json) if result_json else None
            jobs.append(payload)
        return jobs

    def claim_next(
        self,
        *,
        statuses: tuple[str, ...],
        source_types: tuple[str, ...],
        claimed_status: str,
        updated_at: str,
        progress_stage: str | None = None,
        progress_percent: int | None = None,
    ) -> dict[str, Any] | None:
        if not statuses or not source_types:
            return None

        status_placeholders = ", ".join("?" for _ in statuses)
        source_placeholders = ", ".join("?" for _ in source_types)
        select_params: list[Any] = [*statuses, *source_types]

        with _DB_LOCK, connect(self.db_path) as connection:
            row = connection.execute(
                f"""
                SELECT id
                FROM processing_jobs
                WHERE status IN ({status_placeholders})
                  AND source_type IN ({source_placeholders})
                ORDER BY created_at ASC
                LIMIT 1
                """,
                select_params,
            ).fetchone()
            if not row:
                return None

            connection.execute(
                """
                UPDATE processing_jobs
                SET status = ?,
                    progress_stage = COALESCE(?, progress_stage),
                    progress_percent = COALESCE(?, progress_percent),
                    updated_at = ?
                WHERE id = ?
                """,
                (claimed_status, progress_stage, progress_percent, updated_at, row["id"]),
            )

        return self.get(row["id"])
