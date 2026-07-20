"""Request and response schemas exposed by the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StormRequest(BaseModel):
    """Parameters controlling a single chaos storm.

    All fields are optional; omitted values fall back to server configuration.
    """

    count: int | None = Field(
        default=None,
        ge=1,
        description="Number of synthetic events to generate. Defaults to DEFAULT_STORM_SIZE.",
    )
    concurrency: int | None = Field(
        default=None,
        ge=1,
        description="Max in-flight requests. Defaults to CONCURRENCY.",
    )
    dry_run: bool | None = Field(
        default=None,
        description="Override the server DRY_RUN flag for this storm only.",
    )


class StormResult(BaseModel):
    """Outcome summary for a completed storm."""

    scenario: str
    dry_run: bool
    requested: int
    succeeded: int
    failed: int
    duration_seconds: float
    requests_per_second: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_max_ms: float
