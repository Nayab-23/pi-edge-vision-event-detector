from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.core.settings import Settings
from app.services.detector import DetectionResult


@dataclass(slots=True)
class RecordedEvent:
    created_at: str
    event_label: str
    motion_ratio: float
    snapshot_path: str
    clip_path: str
    metadata: dict[str, Any]


@dataclass(slots=True)
class _ActiveRecording:
    created_at: str
    event_label: str
    motion_ratio: float
    snapshot_path: Path
    clip_path: Path
    end_timestamp: float
    frames: list[np.ndarray]
    metadata: dict[str, Any]


class EventRecorder:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.media_root = Path(settings.media_root).expanduser().resolve()
        self.media_root.mkdir(parents=True, exist_ok=True)
        self._buffer: deque[tuple[float, np.ndarray]] = deque(maxlen=max(1, int(settings.pre_event_seconds * settings.poll_fps)))
        self._active: _ActiveRecording | None = None
        self._last_event_timestamp = 0.0

    def process(
        self,
        frame: np.ndarray,
        *,
        timestamp: float,
        detection: DetectionResult,
        annotated_frame: np.ndarray,
        source_mode: str,
    ) -> RecordedEvent | None:
        self._buffer.append((timestamp, frame.copy()))

        if self._active is not None:
            self._active.frames.append(frame.copy())
            if detection.triggered:
                self._active.end_timestamp = max(self._active.end_timestamp, timestamp + self.settings.post_event_seconds)
                self._active.metadata["extended"] = True
            if timestamp >= self._active.end_timestamp:
                completed = self._finalize(source_mode)
                self._last_event_timestamp = timestamp
                return completed

        if detection.triggered and timestamp - self._last_event_timestamp >= self.settings.cooldown_seconds and self._active is None:
            self._active = self._start_recording(timestamp, detection, annotated_frame)
            self._active.frames.extend(frame_copy for _, frame_copy in self._buffer)
        return None

    def flush(self, source_mode: str) -> RecordedEvent | None:
        if self._active is None:
            return None
        return self._finalize(source_mode)

    def _start_recording(self, timestamp: float, detection: DetectionResult, annotated_frame: np.ndarray) -> _ActiveRecording:
        created_at = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        folder = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y/%m/%d")
        base_name = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%H%M%S")

        snapshot_dir = self.media_root / "snapshots" / folder
        clip_dir = self.media_root / "clips" / folder
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        clip_dir.mkdir(parents=True, exist_ok=True)

        snapshot_path = snapshot_dir / f"{base_name}_{detection.event_label}.jpg"
        clip_path = clip_dir / f"{base_name}_{detection.event_label}.avi"
        cv2.imwrite(str(snapshot_path), annotated_frame)

        return _ActiveRecording(
            created_at=created_at,
            event_label=detection.event_label,
            motion_ratio=detection.motion_ratio,
            snapshot_path=snapshot_path,
            clip_path=clip_path,
            end_timestamp=timestamp + self.settings.post_event_seconds,
            frames=[],
            metadata={
                "contour_count": detection.contour_count,
                "bounding_boxes": detection.bounding_boxes,
                "person_boxes": detection.person_boxes,
                "detector": detection.metadata,
            },
        )

    def _finalize(self, source_mode: str) -> RecordedEvent:
        if self._active is None:
            raise RuntimeError("No active recording to finalize")
        active = self._active
        self._active = None

        if active.frames:
            height, width = active.frames[0].shape[:2]
            writer = cv2.VideoWriter(
                str(active.clip_path),
                cv2.VideoWriter_fourcc(*"MJPG"),
                self.settings.poll_fps,
                (width, height),
            )
            for frame in active.frames:
                writer.write(frame)
            writer.release()

        return RecordedEvent(
            created_at=active.created_at,
            event_label=active.event_label,
            motion_ratio=active.motion_ratio,
            snapshot_path=str(active.snapshot_path),
            clip_path=str(active.clip_path),
            metadata={**active.metadata, "source_mode": source_mode, "frame_count": len(active.frames)},
        )
