from __future__ import annotations

from app.video.sources import select_source


def test_select_source_falls_back_to_sample_video(settings, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.video.sources.probe_video_hardware",
        lambda: {"pi_camera": {"available": False}, "video_devices": [], "usb_candidates": []},
    )

    selected = select_source(settings)
    assert selected.info.mode == "sample_video"
    assert "sample_path" in selected.info.details
