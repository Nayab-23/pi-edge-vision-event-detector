from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_api_summary_and_config(settings) -> None:
    app = create_app(settings=settings, start_worker=False)
    with TestClient(app) as client:
        summary = client.get("/api/summary")
        assert summary.status_code == 200
        payload = summary.json()
        assert payload["status"]["source"]["mode"] == "sample_video"

        config = client.put(
            "/api/config",
            json={"detection": {"sensitivity": 0.72}, "storage": {"retention_days": 10}},
        )
        assert config.status_code == 200
        assert config.json()["detection"]["sensitivity"] == 0.72
        assert config.json()["storage"]["retention_days"] == 10
