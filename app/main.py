from __future__ import annotations

from fastapi import FastAPI

from app.core.logging import configure_logging
from app.core.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings.from_env()
    configure_logging(resolved.log_path)
    app = FastAPI(title="Pi Edge Vision Event Detector", version="0.1.0")
    app.state.settings = resolved

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
