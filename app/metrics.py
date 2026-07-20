"""Prometheus instrumentation for the chaos engine."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUESTS = Counter(
    "chaos_requests_total",
    "Synthetic requests fired by the chaos engine.",
    ["scenario", "outcome"],
)

STORM_DURATION = Histogram(
    "chaos_storm_duration_seconds",
    "Wall-clock duration of a completed storm.",
    ["scenario"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)

REQUEST_LATENCY = Histogram(
    "chaos_request_latency_seconds",
    "Per-request latency of synthetic traffic.",
    ["scenario"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5),
)


def render() -> tuple[bytes, str]:
    """Return the current metrics payload and its content type."""
    return generate_latest(), CONTENT_TYPE_LATEST
