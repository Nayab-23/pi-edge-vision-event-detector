from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.settings import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        host="127.0.0.1",
        port=8080,
        db_path=str(tmp_path / "vision.db"),
        log_path=str(tmp_path / "logs" / "app.log"),
        media_root=str(tmp_path / "media"),
        sample_video_path=str(tmp_path / "sample" / "demo_input.avi"),
        poll_fps=10,
        frame_width=320,
        frame_height=240,
        cooldown_seconds=1,
        pre_event_seconds=1,
        post_event_seconds=1,
        min_motion_area_ratio=0.01,
        sensitivity=0.6,
        advanced_detection_enabled=False,
        retention_days=7,
        max_event_count=20,
    )
