from __future__ import annotations

import logging
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2

from app.core.settings import Settings
from app.services.detector import DetectionResult, MotionDetector
from app.services.recorder import EventRecorder, RecordedEvent
from app.services.retention import RetentionManager
from app.services.store import EventStore
from app.video.sample_video import ensure_sample_video
from app.video.sources import SampleVideoSource, SelectedSource, select_source


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class VisionRuntime:
    def __init__(self, settings: Settings, *, start_worker: bool = True) -> None:
        self.settings = settings
        self.store = EventStore(settings.db_path)
        self.detector = MotionDetector(settings)
        self.recorder = EventRecorder(settings)
        self.retention = RetentionManager(settings, self.store)
        self.logger = logging.getLogger("pi_edge_vision.runtime")
        self.start_worker = start_worker

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._selected: SelectedSource | None = None
        self._source = None
        self._frame_count = 0
        self._event_count = 0
        self._last_detection: DetectionResult | None = None
        self._last_event: dict[str, Any] | None = None
        self._last_preview_at = 0.0
        self._last_retention_at = 0.0
        self._latest_frame_path = Path(settings.media_root).expanduser().resolve() / "live" / "latest.jpg"
        self._latest_frame_path.parent.mkdir(parents=True, exist_ok=True)
        self._hardware_check: dict[str, Any] | None = None
        self._startup_message = "initializing"

    @property
    def default_config(self) -> dict[str, Any]:
        return {
            "video": {
                "frame_width": self.settings.frame_width,
                "frame_height": self.settings.frame_height,
                "poll_fps": self.settings.poll_fps,
                "sample_video_path": self.settings.sample_video_path,
            },
            "detection": {
                "cooldown_seconds": self.settings.cooldown_seconds,
                "pre_event_seconds": self.settings.pre_event_seconds,
                "post_event_seconds": self.settings.post_event_seconds,
                "min_motion_area_ratio": self.settings.min_motion_area_ratio,
                "sensitivity": self.settings.sensitivity,
                "advanced_detection_enabled": self.settings.advanced_detection_enabled,
            },
            "storage": {
                "retention_days": self.settings.retention_days,
                "max_event_count": self.settings.max_event_count,
                "media_root": self.settings.media_root,
            },
        }

    def start(self) -> None:
        self.store.initialize()
        self.store.ensure_default_config(self.default_config, updated_at=_iso_now())
        self._selected = select_source(self.settings)
        self._source = self._selected.source
        self._source.open()
        self._hardware_check = self._selected.hardware
        self._startup_message = f"source={self._selected.info.mode}"
        self.store.write_run_log(_iso_now(), "info", "Startup hardware check complete", self._hardware_check)
        self.logger.info("Selected source mode=%s label=%s", self._selected.info.mode, self._selected.info.label)

        if not self.start_worker:
            self.collect_once()
            return

        self._thread = threading.Thread(target=self._run_loop, name="vision-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        if self._source is not None:
            try:
                final_event = self.recorder.flush(self.active_source_mode)
                if final_event:
                    self._persist_event(final_event)
            except Exception:
                self.logger.exception("Failed to flush active recording")
            self._source.close()

    @property
    def active_source_mode(self) -> str:
        return self._selected.info.mode if self._selected is not None else "unknown"

    def get_config(self) -> dict[str, Any]:
        return self.store.get_config(self.default_config)

    def update_config(self, patch: dict[str, Any]) -> dict[str, Any]:
        updated = self.store.update_config(patch, self.default_config, _iso_now())
        self._apply_config(updated)
        self.store.write_run_log(_iso_now(), "info", "Runtime config updated", {"patch": patch})
        return updated

    def get_status(self) -> dict[str, Any]:
        stats = self.store.get_stats()
        with self._lock:
            return {
                "status": "running" if self._thread and self._thread.is_alive() else "ready",
                "startup_message": self._startup_message,
                "source": asdict(self._selected.info) if self._selected else None,
                "frame_count": self._frame_count,
                "event_count": stats["total_events"],
                "last_detection": asdict(self._last_detection) if self._last_detection else None,
                "last_event": self._last_event,
                "preview_url": "/media/live/latest.jpg" if self._latest_frame_path.exists() else None,
                "hardware_check": self._hardware_check,
            }

    def get_summary(self) -> dict[str, Any]:
        return {
            "status": self.get_status(),
            "stats": self.store.get_stats(),
            "recent_events": self._serialize_events(self.store.list_events(limit=12)),
            "run_logs": self.store.list_run_logs(limit=12),
            "config": self.get_config(),
        }

    def collect_once(self) -> None:
        if self._source is None:
            raise RuntimeError("No active source")

        config = self.get_config()
        self._apply_config(config)
        packet = self._source.read()
        if packet is None:
            raise RuntimeError("Source did not produce a frame")

        result = self.detector.process(packet.frame, packet.timestamp)
        annotated = self.detector.annotate(packet.frame, result)
        recorded = self.recorder.process(
            packet.frame,
            timestamp=packet.timestamp,
            detection=result,
            annotated_frame=annotated,
            source_mode=packet.source_mode,
        )
        self._maybe_write_preview(annotated, packet.timestamp)
        if recorded:
            self._persist_event(recorded)
        if packet.timestamp - self._last_retention_at >= 60:
            retention = self.retention.prune(
                retention_days=int(config["storage"]["retention_days"]),
                max_event_count=int(config["storage"]["max_event_count"]),
            )
            self._last_retention_at = packet.timestamp
            if retention["deleted_events"]:
                self.store.write_run_log(_iso_now(), "info", "Retention pruned media", retention)

        with self._lock:
            self._frame_count += 1
            self._last_detection = result

    def _run_loop(self) -> None:
        target_interval = 1.0 / max(1, self.settings.poll_fps)
        consecutive_failures = 0

        while not self._stop_event.is_set():
            started = time.monotonic()
            try:
                self.collect_once()
                consecutive_failures = 0
            except Exception as exc:
                consecutive_failures += 1
                self.logger.warning("Frame loop failure (%s): %s", consecutive_failures, exc)
                if consecutive_failures >= 5:
                    self._switch_to_sample_fallback(reason=str(exc))
                    consecutive_failures = 0
            elapsed = time.monotonic() - started
            wait = target_interval - elapsed
            if wait > 0:
                self._stop_event.wait(wait)

    def _apply_config(self, config: dict[str, Any]) -> None:
        self.detector.update_config(config["detection"])
        self.recorder.update_config(config["detection"])

    def _switch_to_sample_fallback(self, reason: str) -> None:
        self.logger.warning("Switching to sample fallback: %s", reason)
        self.store.write_run_log(_iso_now(), "warning", "Switching to sample fallback", {"reason": reason})
        if self._source is not None:
            self._source.close()
        ensure_sample_video(self.settings.sample_video_path, self.settings.frame_width, self.settings.frame_height, self.settings.poll_fps)
        self._source = SampleVideoSource(self.settings)
        self._source.open()
        self._selected = SelectedSource(source=self._source, info=self._source.info, hardware=self._hardware_check or {})

    def _maybe_write_preview(self, frame, timestamp: float) -> None:
        if timestamp - self._last_preview_at >= 0.5:
            cv2.imwrite(str(self._latest_frame_path), frame)
            self._last_preview_at = timestamp

    def _persist_event(self, recorded: RecordedEvent) -> None:
        event_id = self.store.add_event(
            created_at=recorded.created_at,
            event_label=recorded.event_label,
            motion_ratio=recorded.motion_ratio,
            source_mode=self.active_source_mode,
            source_label=self._selected.info.label if self._selected else "unknown",
            snapshot_path=recorded.snapshot_path,
            clip_path=recorded.clip_path,
            metadata=recorded.metadata,
        )
        self.logger.info("Recorded event id=%s label=%s", event_id, recorded.event_label)
        with self._lock:
            self._event_count += 1
            self._last_event = {
                "id": event_id,
                "created_at": recorded.created_at,
                "event_label": recorded.event_label,
                "motion_ratio": recorded.motion_ratio,
                "snapshot_url": f"/media/{recorded.snapshot_path}",
                "clip_url": f"/media/{recorded.clip_path}",
            }

    def _serialize_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        serialized = []
        for event in events:
            serialized.append(
                {
                    **event,
                    "snapshot_url": f"/media/{event['snapshot_path']}" if event.get("snapshot_path") else None,
                    "clip_url": f"/media/{event['clip_path']}" if event.get("clip_path") else None,
                }
            )
        return serialized
