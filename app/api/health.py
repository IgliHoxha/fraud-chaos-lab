"""Liveness, readiness and metrics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Response

from app import metrics
from app.config import get_settings

router = APIRouter(tags=["ops"])


@router.get("/healthz", summary="Liveness probe")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz", summary="Readiness probe")
async def readyz() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": "ready",
        "dry_run": settings.effectively_dry_run,
        "target": settings.storm_target_base_url or None,
    }


@router.get("/metrics", summary="Prometheus metrics", include_in_schema=False)
async def prometheus_metrics() -> Response:
    settings = get_settings()
    if not settings.metrics_enabled:
        return Response(status_code=404)
    payload, content_type = metrics.render()
    return Response(content=payload, media_type=content_type)
