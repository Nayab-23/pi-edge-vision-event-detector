from __future__ import annotations

import glob
import os
import subprocess
from pathlib import Path


def _run(command: list[str]) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=4,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, "", str(exc)
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _pi_camera_probe() -> dict[str, object]:
    tool = shutil_which("rpicam-hello")
    if not tool:
        return {"available": False, "details": "rpicam-hello not installed"}

    code, stdout, stderr = _run([tool, "--list-cameras"])
    output = stdout or stderr
    available = code == 0 and "No cameras available!" not in output and bool(output.strip())
    return {"available": available, "details": output or "Camera probe returned no output", "tool": tool}


def _video_device_inventory() -> list[dict[str, str]]:
    devices: list[dict[str, str]] = []
    for dev_path in sorted(glob.glob("/dev/video*")):
        name_path = Path("/sys/class/video4linux") / Path(dev_path).name / "name"
        driver_name = name_path.read_text(encoding="utf-8").strip() if name_path.exists() else "unknown"
        devices.append({"path": dev_path, "name": driver_name})
    return devices


def _usb_camera_candidates(devices: list[dict[str, str]]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for device in devices:
        name = device["name"].lower()
        if any(token in name for token in ("usb", "uvc", "webcam", "camera")):
            candidates.append(device)
    return candidates


def probe_video_hardware() -> dict[str, object]:
    devices = _video_device_inventory()
    usb_candidates = _usb_camera_candidates(devices)
    return {
        "pi_camera": _pi_camera_probe(),
        "video_devices": devices,
        "usb_candidates": usb_candidates,
    }


def shutil_which(command: str) -> str | None:
    for directory in os.getenv("PATH", "").split(os.pathsep):
        candidate = Path(directory) / command
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None
