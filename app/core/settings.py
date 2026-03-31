from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw is not None else default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw is not None else default


@dataclass(slots=True)
class Settings:
    host: str = "0.0.0.0"
    port: int = 8080
    db_path: str = "./data/vision.db"
    log_path: str = "./data/logs/app.log"
    media_root: str = "./data/media"
    sample_video_path: str = "./data/sample/demo_input.avi"
    poll_fps: int = 10
    frame_width: int = 640
    frame_height: int = 360
    cooldown_seconds: float = 8.0
    pre_event_seconds: float = 2.0
    post_event_seconds: float = 4.0
    min_motion_area_ratio: float = 0.015
    sensitivity: float = 0.55
    advanced_detection_enabled: bool = False
    retention_days: int = 7
    max_event_count: int = 250

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            host=os.getenv("PIVED_HOST", "0.0.0.0"),
            port=_env_int("PIVED_PORT", 8080),
            db_path=os.getenv("PIVED_DB_PATH", "./data/vision.db"),
            log_path=os.getenv("PIVED_LOG_PATH", "./data/logs/app.log"),
            media_root=os.getenv("PIVED_MEDIA_ROOT", "./data/media"),
            sample_video_path=os.getenv("PIVED_SAMPLE_VIDEO", "./data/sample/demo_input.avi"),
            poll_fps=_env_int("PIVED_POLL_FPS", 10),
            frame_width=_env_int("PIVED_FRAME_WIDTH", 640),
            frame_height=_env_int("PIVED_FRAME_HEIGHT", 360),
            cooldown_seconds=_env_float("PIVED_COOLDOWN_SECONDS", 8.0),
            pre_event_seconds=_env_float("PIVED_PRE_EVENT_SECONDS", 2.0),
            post_event_seconds=_env_float("PIVED_POST_EVENT_SECONDS", 4.0),
            min_motion_area_ratio=_env_float("PIVED_MIN_MOTION_AREA_RATIO", 0.015),
            sensitivity=_env_float("PIVED_SENSITIVITY", 0.55),
            advanced_detection_enabled=_env_bool("PIVED_ADVANCED_DETECTION", False),
            retention_days=_env_int("PIVED_RETENTION_DAYS", 7),
            max_event_count=_env_int("PIVED_MAX_EVENT_COUNT", 250),
        )

    @property
    def project_root(self) -> Path:
        return Path(self.db_path).expanduser().resolve().parent.parent
