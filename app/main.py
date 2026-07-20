"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from app import __version__
from app.api import chaos, health

DESCRIPTION = (
    "Fraud Chaos Lab simulates high-velocity, catastrophic fraud scenarios "
    "against your own infrastructure to prove it stays antifragile under load. "
    "It ships in DRY_RUN mode: no real traffic leaves the process until you "
    "configure a target and disable the flag."
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fraud Chaos Lab",
        version=__version__,
        description=DESCRIPTION,
    )
    app.include_router(health.router)
    app.include_router(chaos.router)

    @app.get("/", tags=["ops"], summary="Service banner")
    async def root() -> dict[str, str]:
        return {"service": "fraud-chaos-lab", "version": __version__, "docs": "/docs"}

    return app


app = create_app()
