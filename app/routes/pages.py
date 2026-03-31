from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

PROJECT_ROOT = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"page_title": "Edge Vision Dashboard"})


@router.get("/config", response_class=HTMLResponse)
async def config_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="config.html", context={"page_title": "Detector Configuration"})
