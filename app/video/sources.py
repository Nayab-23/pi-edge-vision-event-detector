from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import cv2

from app.core.settings import Settings
from app.video.base import FramePacket, SourceInfo
from app.video.probe import probe_video_hardware
from app.video.sample_video import ensure_sample_video


class Picamera2Source:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.info = SourceInfo(mode="pi_camera", label="Raspberry Pi Camera")
        self._camera = None
        self._frame_index = 0
        self._frame_interval = 1.0 / max(1, settings.poll_fps)
        self._last_frame_at = 0.0

    def open(self) -> None:
        from picamera2 import Picamera2  # type: ignore

        self._camera = Picamera2()
        config = self._camera.create_video_configuration(
            main={"size": (self.settings.frame_width, self.settings.frame_height), "format": "RGB888"}
        )
        self._camera.configure(config)
        self._camera.start()
        self.info.details = {"resolution": [self.settings.frame_width, self.settings.frame_height]}

    def read(self) -> FramePacket | None:
        if self._camera is None:
            return None
        now = time.time()
        wait = self._frame_interval - (now - self._last_frame_at)
        if wait > 0:
            time.sleep(wait)
        rgb = self._camera.capture_array()
        frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        self._frame_index += 1
        self._last_frame_at = time.time()
        return FramePacket(frame=frame, frame_index=self._frame_index, timestamp=self._last_frame_at, source_mode="pi_camera")

    def close(self) -> None:
        if self._camera is not None:
            self._camera.stop()
            self._camera.close()
            self._camera = None


class OpenCVCameraSource:
    def __init__(self, settings: Settings, device_path: str, label: str) -> None:
        self.settings = settings
        self.device_path = device_path
        self.info = SourceInfo(mode="usb_camera", label=label, details={"device_path": device_path})
        self._capture = None
        self._frame_index = 0

    def open(self) -> None:
        self._capture = cv2.VideoCapture(self.device_path)
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings.frame_width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings.frame_height)
        self._capture.set(cv2.CAP_PROP_FPS, self.settings.poll_fps)
        if not self._capture.isOpened():
            raise RuntimeError(f"Unable to open camera device {self.device_path}")

    def read(self) -> FramePacket | None:
        if self._capture is None:
            return None
        ok, frame = self._capture.read()
        if not ok or frame is None:
            return None
        self._frame_index += 1
        return FramePacket(frame=frame, frame_index=self._frame_index, timestamp=time.time(), source_mode="usb_camera")

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None


class SampleVideoSource:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.info = SourceInfo(mode="sample_video", label="Synthetic Demo Video")
        self._capture = None
        self._frame_index = 0
        self._sample_path = ensure_sample_video(
            settings.sample_video_path,
            settings.frame_width,
            settings.frame_height,
            settings.poll_fps,
        )
        self.info.details = {"sample_path": str(self._sample_path)}

    def open(self) -> None:
        self._capture = cv2.VideoCapture(str(self._sample_path))
        if not self._capture.isOpened():
            raise RuntimeError(f"Unable to open sample video {self._sample_path}")

    def read(self) -> FramePacket | None:
        if self._capture is None:
            return None

        ok, frame = self._capture.read()
        if not ok or frame is None:
            self._capture.release()
            self._capture = cv2.VideoCapture(str(self._sample_path))
            ok, frame = self._capture.read()
            if not ok or frame is None:
                return None

        self._frame_index += 1
        return FramePacket(frame=frame, frame_index=self._frame_index, timestamp=time.time(), source_mode="sample_video")

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None


@dataclass(slots=True)
class SelectedSource:
    source: object
    info: SourceInfo
    hardware: dict[str, object]


def select_source(settings: Settings) -> SelectedSource:
    hardware = probe_video_hardware()
    pi_camera = hardware["pi_camera"]
    if bool(pi_camera.get("available")):
        source = Picamera2Source(settings)
        return SelectedSource(source=source, info=source.info, hardware=hardware)

    for candidate in hardware["usb_candidates"]:
        source = OpenCVCameraSource(settings, device_path=candidate["path"], label=candidate["name"])
        try:
            source.open()
        except Exception:
            source.close()
            continue
        source.close()
        return SelectedSource(source=source, info=source.info, hardware=hardware)

    source = SampleVideoSource(settings)
    return SelectedSource(source=source, info=source.info, hardware=hardware)
