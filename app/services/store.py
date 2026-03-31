from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class EventStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path).expanduser()
        self._lock = Lock()

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            event_label TEXT NOT NULL,
            motion_ratio REAL NOT NULL,
            source_mode TEXT NOT NULL,
            source_label TEXT NOT NULL,
            snapshot_path TEXT,
            clip_path TEXT,
            metadata_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS configs (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        );
        """
        with self._lock, self._connect() as connection:
            connection.executescript(schema)
            connection.commit()

    def ensure_default_config(self, default_config: dict[str, Any], updated_at: str) -> None:
        with self._lock, self._connect() as connection:
            exists = connection.execute("SELECT 1 FROM configs WHERE key = 'runtime'").fetchone()
            if not exists:
                connection.execute(
                    "INSERT INTO configs (key, value_json, updated_at) VALUES (?, ?, ?)",
                    ("runtime", json.dumps(default_config), updated_at),
                )
                connection.commit()

    def get_config(self, default_config: dict[str, Any]) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT value_json FROM configs WHERE key = 'runtime'").fetchone()
        if not row:
            return default_config
        return _deep_merge(default_config, json.loads(row["value_json"]))

    def update_config(self, patch: dict[str, Any], default_config: dict[str, Any], updated_at: str) -> dict[str, Any]:
        merged = _deep_merge(self.get_config(default_config), patch)
        with self._lock, self._connect() as connection:
            connection.execute(
                "REPLACE INTO configs (key, value_json, updated_at) VALUES (?, ?, ?)",
                ("runtime", json.dumps(merged), updated_at),
            )
            connection.commit()
        return merged

    def add_event(
        self,
        *,
        created_at: str,
        event_label: str,
        motion_ratio: float,
        source_mode: str,
        source_label: str,
        snapshot_path: str | None,
        clip_path: str | None,
        metadata: dict[str, Any],
    ) -> int:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO events
                (created_at, event_label, motion_ratio, source_mode, source_label, snapshot_path, clip_path, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    event_label,
                    motion_ratio,
                    source_mode,
                    source_label,
                    snapshot_path,
                    clip_path,
                    json.dumps(metadata),
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def list_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, created_at, event_label, motion_ratio, source_mode, source_label, snapshot_path, clip_path, metadata_json
                FROM events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "event_label": row["event_label"],
                "motion_ratio": row["motion_ratio"],
                "source_mode": row["source_mode"],
                "source_label": row["source_label"],
                "snapshot_path": row["snapshot_path"],
                "clip_path": row["clip_path"],
                "metadata": json.loads(row["metadata_json"]),
            }
            for row in rows
        ]

    def get_stats(self) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            total = connection.execute("SELECT COUNT(*) AS count FROM events").fetchone()["count"]
            last = connection.execute("SELECT created_at FROM events ORDER BY id DESC LIMIT 1").fetchone()
            label_rows = connection.execute(
                "SELECT event_label, COUNT(*) AS count FROM events GROUP BY event_label ORDER BY count DESC"
            ).fetchall()
        return {
            "total_events": total,
            "last_event_at": last["created_at"] if last else None,
            "by_label": {row["event_label"]: row["count"] for row in label_rows},
        }

    def write_run_log(self, created_at: str, level: str, message: str, metadata: dict[str, Any] | None = None) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO runs (created_at, level, message, metadata_json) VALUES (?, ?, ?, ?)",
                (created_at, level, message, json.dumps(metadata or {})),
            )
            connection.commit()

    def list_run_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT created_at, level, message, metadata_json FROM runs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "created_at": row["created_at"],
                "level": row["level"],
                "message": row["message"],
                "metadata": json.loads(row["metadata_json"]),
            }
            for row in rows
        ]

    def stale_media(self, retention_days: int, max_event_count: int) -> list[dict[str, Any]]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
        with self._lock, self._connect() as connection:
            old_rows = connection.execute(
                """
                SELECT id, snapshot_path, clip_path
                FROM events
                WHERE created_at < ?
                ORDER BY id ASC
                """,
                (cutoff,),
            ).fetchall()

            overflow_rows = connection.execute(
                """
                SELECT id, snapshot_path, clip_path
                FROM events
                WHERE id NOT IN (
                    SELECT id FROM events ORDER BY id DESC LIMIT ?
                )
                ORDER BY id ASC
                """,
                (max_event_count,),
            ).fetchall()

        seen: dict[int, dict[str, Any]] = {}
        for row in list(old_rows) + list(overflow_rows):
            seen[row["id"]] = {"id": row["id"], "snapshot_path": row["snapshot_path"], "clip_path": row["clip_path"]}
        return list(seen.values())

    def delete_events(self, event_ids: list[int]) -> None:
        if not event_ids:
            return
        placeholders = ",".join("?" for _ in event_ids)
        with self._lock, self._connect() as connection:
            connection.execute(f"DELETE FROM events WHERE id IN ({placeholders})", tuple(event_ids))
            connection.commit()
