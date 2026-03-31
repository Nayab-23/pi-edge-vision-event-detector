from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from app.core.settings import Settings


@dataclass(slots=True)
class DetectionResult:
    timestamp: float
    motion_ratio: float
    triggered: bool
    event_label: str
    contour_count: int
    bounding_boxes: list[tuple[int, int, int, int]] = field(default_factory=list)
    person_boxes: list[tuple[int, int, int, int]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class MotionDetector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._background: np.ndarray | None = None
        self._hog = None
        self._advanced_counter = 0

        if settings.advanced_detection_enabled:
            self._hog = cv2.HOGDescriptor()
            self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def process(self, frame: np.ndarray, timestamp: float) -> DetectionResult:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self._background is None:
            self._background = gray.astype("float")
            return DetectionResult(
                timestamp=timestamp,
                motion_ratio=0.0,
                triggered=False,
                event_label="idle",
                contour_count=0,
            )

        cv2.accumulateWeighted(gray, self._background, 0.08)
        delta = cv2.absdiff(gray, cv2.convertScaleAbs(self._background))
        threshold_value = int(max(12, 48 - self.settings.sensitivity * 32))
        thresh = cv2.threshold(delta, threshold_value, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        frame_area = float(frame.shape[0] * frame.shape[1])
        motion_boxes: list[tuple[int, int, int, int]] = []
        motion_area = 0.0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < frame_area * 0.0025:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            motion_boxes.append((x, y, w, h))
            motion_area += area

        motion_ratio = motion_area / frame_area if frame_area else 0.0
        person_boxes = self._detect_people(frame) if motion_boxes else []

        triggered = motion_ratio >= self.settings.min_motion_area_ratio
        label = "motion"
        if person_boxes:
            triggered = True
            label = "person_motion"
        elif not triggered:
            label = "idle"

        return DetectionResult(
            timestamp=timestamp,
            motion_ratio=round(motion_ratio, 5),
            triggered=triggered,
            event_label=label,
            contour_count=len(motion_boxes),
            bounding_boxes=motion_boxes,
            person_boxes=person_boxes,
            metadata={
                "pixel_threshold": threshold_value,
                "advanced_detection_enabled": self._hog is not None,
            },
        )

    def annotate(self, frame: np.ndarray, result: DetectionResult) -> np.ndarray:
        annotated = frame.copy()
        for x, y, w, h in result.bounding_boxes:
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (255, 198, 74), 2)
        for x, y, w, h in result.person_boxes:
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (82, 232, 124), 2)

        cv2.putText(
            annotated,
            f"{result.event_label} motion={result.motion_ratio:.4f}",
            (16, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (245, 245, 245),
            2,
        )
        return annotated

    def _detect_people(self, frame: np.ndarray) -> list[tuple[int, int, int, int]]:
        if self._hog is None:
            return []

        self._advanced_counter += 1
        if self._advanced_counter % 3 != 0:
            return []

        resized = cv2.resize(frame, (frame.shape[1] // 2, frame.shape[0] // 2))
        rects, _ = self._hog.detectMultiScale(
            resized,
            winStride=(8, 8),
            padding=(8, 8),
            scale=1.05,
        )
        people: list[tuple[int, int, int, int]] = []
        for x, y, w, h in rects:
            people.append((x * 2, y * 2, w * 2, h * 2))
        return people
