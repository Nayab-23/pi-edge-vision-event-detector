#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.settings import Settings
from app.video.sample_video import ensure_sample_video


def main() -> None:
    settings = Settings.from_env()
    path = ensure_sample_video(
        settings.sample_video_path,
        settings.frame_width,
        settings.frame_height,
        settings.poll_fps,
    )
    print(path)


if __name__ == "__main__":
    main()
