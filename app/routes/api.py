from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.services.runtime import VisionRuntime

router = APIRouter(prefix="/api", tags=["api"])


class DetectionPatch(BaseModel):
    cooldown_seconds: float | None = Field(default=None, ge=0)
    pre_event_seconds: float | None = Field(default=None, ge=0)
    post_event_seconds: float | None = Field(default=None, ge=0)
    min_motion_area_ratio: float | None = Field(default=None, ge=0.001, le=0.5)
    sensitivity: float | None = Field(default=None, ge=0.1, le=1.0)
    advanced_detection_enabled: bool | None = None


class StoragePatch(BaseModel):
    retention_days: int | None = Field(default=None, ge=1, le=90)
    max_event_count: int | None = Field(default=None, ge=10, le=5000)


class ConfigPatch(BaseModel):
    detection: DetectionPatch | None = None
    storage: StoragePatch | None = None


def _runtime(request: Request) -> VisionRuntime:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Runtime not initialized")
    return runtime


@router.get("/summary")
async def summary(request: Request) -> dict[str, Any]:
    return _runtime(request).get_summary()


@router.get("/status")
async def status(request: Request) -> dict[str, Any]:
    return _runtime(request).get_status()


@router.get("/events")
async def events(request: Request, limit: int = Query(default=30, ge=1, le=200)) -> dict[str, Any]:
    return {"events": _runtime(request)._serialize_events(_runtime(request).store.list_events(limit=limit))}


@router.get("/stats")
async def stats(request: Request) -> dict[str, Any]:
    return _runtime(request).store.get_stats()


@router.get("/config")
async def config(request: Request) -> dict[str, Any]:
    return _runtime(request).get_config()


@router.put("/config")
async def update_config(request: Request, payload: ConfigPatch) -> dict[str, Any]:
    patch = payload.model_dump(exclude_none=True)
    return _runtime(request).update_config(patch)


@router.get("/logs")
async def logs(request: Request, limit: int = Query(default=20, ge=1, le=200)) -> dict[str, Any]:
    return {"logs": _runtime(request).store.list_run_logs(limit=limit)}
