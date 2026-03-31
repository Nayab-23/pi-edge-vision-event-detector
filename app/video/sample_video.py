from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def ensure_sample_video(path: str, width: int, height: int, fps: int) -> Path:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return target

    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(str(target), fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Unable to create sample video at {target}")

    total_frames = fps * 18
    for index in range(total_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = (18, 24, 28)

        # Simulated hallway / room lines.
        cv2.rectangle(frame, (30, 40), (width - 30, height - 40), (42, 52, 60), 2)
        cv2.putText(frame, "Pi Edge Vision Demo", (26, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (120, 220, 210), 2)

        # Motion event 1: moving package-sized box.
        if fps * 2 <= index <= fps * 6:
            x = 40 + (index - fps * 2) * 8
            cv2.rectangle(frame, (x, 150), (x + 70, 220), (50, 160, 240), -1)

        # Motion event 2: simple person-like silhouette.
        if fps * 9 <= index <= fps * 14:
            x = width - 120 - (index - fps * 9) * 6
            cv2.circle(frame, (x + 30, 110), 18, (220, 220, 220), -1)
            cv2.rectangle(frame, (x + 16, 128), (x + 44, 212), (220, 220, 220), -1)
            cv2.line(frame, (x + 18, 212), (x, 252), (220, 220, 220), 8)
            cv2.line(frame, (x + 42, 212), (x + 60, 252), (220, 220, 220), 8)
            cv2.line(frame, (x + 16, 148), (x - 6, 192), (220, 220, 220), 8)
            cv2.line(frame, (x + 44, 148), (x + 66, 190), (220, 220, 220), 8)

        noise = np.random.default_rng(seed=index).integers(0, 6, size=frame.shape, dtype=np.uint8)
        frame = cv2.add(frame, noise)
        writer.write(frame)

    writer.release()
    return target
