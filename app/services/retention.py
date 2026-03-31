from __future__ import annotations

from pathlib import Path

from app.core.settings import Settings
from app.services.store import EventStore


class RetentionManager:
    def __init__(self, settings: Settings, store: EventStore) -> None:
        self.settings = settings
        self.store = store
        self.media_root = Path(settings.media_root).expanduser().resolve()

    def prune(self, retention_days: int, max_event_count: int) -> dict[str, int]:
        stale = self.store.stale_media(retention_days, max_event_count)
        deleted_files = 0
        deleted_events = 0
        for row in stale:
            for path_key in ("snapshot_path", "clip_path"):
                path = row.get(path_key)
                if not path:
                    continue
                candidate = self.media_root / path
                if candidate.exists():
                    candidate.unlink(missing_ok=True)
                    deleted_files += 1
            deleted_events += 1

        self.store.delete_events([row["id"] for row in stale])
        return {"deleted_events": deleted_events, "deleted_files": deleted_files}
