from __future__ import annotations

import numpy as np

from app.services.detector import MotionDetector


def test_motion_detector_triggers_on_large_change(settings) -> None:
    detector = MotionDetector(settings)
    base = np.zeros((settings.frame_height, settings.frame_width, 3), dtype=np.uint8)
    moving = base.copy()
    moving[60:180, 90:220] = 255

    first = detector.process(base, 1.0)
    second = detector.process(moving, 2.0)

    assert first.triggered is False
    assert second.triggered is True
    assert second.motion_ratio > settings.min_motion_area_ratio
