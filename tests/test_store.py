from __future__ import annotations

from app.services.store import EventStore


def test_event_store_records_config_and_events(tmp_path) -> None:
    store = EventStore(str(tmp_path / "vision.db"))
    store.initialize()
    defaults = {"detection": {"sensitivity": 0.5}, "storage": {"retention_days": 7}}
    store.ensure_default_config(defaults, "2026-03-30T00:00:00+00:00")

    config = store.get_config(defaults)
    assert config["detection"]["sensitivity"] == 0.5

    store.add_event(
        created_at="2026-03-30T00:00:01+00:00",
        event_label="motion",
        motion_ratio=0.12,
        source_mode="sample_video",
        source_label="Synthetic Demo Video",
        snapshot_path="snapshots/example.jpg",
        clip_path="clips/example.avi",
        metadata={"frame_count": 10},
    )

    events = store.list_events(limit=5)
    assert len(events) == 1
    assert events[0]["event_label"] == "motion"
    assert store.get_stats()["total_events"] == 1
