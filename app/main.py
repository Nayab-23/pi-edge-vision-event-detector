from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.logging import configure_logging
from app.core.settings import Settings
from app.routes.api import router as api_router
from app.routes.pages import router as page_router
from app.services.runtime import VisionRuntime


def create_app(settings: Settings | None = None, *, start_worker: bool = True) -> FastAPI:
    resolved = settings or Settings.from_env()
    configure_logging(resolved.log_path)
    runtime = VisionRuntime(resolved, start_worker=start_worker)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = resolved
        app.state.runtime = runtime
        runtime.start()
        try:
            yield
        finally:
            runtime.stop()

    app = FastAPI(title="Pi Edge Vision Event Detector", version="0.1.0", lifespan=lifespan)
    project_root = Path(__file__).resolve().parents[1]
    media_root = Path(resolved.media_root).expanduser().resolve()
    media_root.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(project_root / "static")), name="static")
    app.mount("/media", StaticFiles(directory=str(media_root)), name="media")
    app.include_router(api_router)
    app.include_router(page_router)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
