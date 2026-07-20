"""The concurrency engine that drives every scenario.

A scenario hands the engine a coroutine factory; the engine runs ``count`` of
them under a semaphore-bounded fan-out, times each one, and rolls the outcomes
up into a :class:`~app.models.StormResult`.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

from app import metrics
from app.models import StormResult

# A unit of work: given its index, do one synthetic operation (which may itself
# fan out to several upstream calls). Raising signals a failed unit.
TaskFactory = Callable[[int], Awaitable[None]]


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Nearest-rank percentile over an already-sorted list (empty -> 0.0)."""
    if not sorted_values:
        return 0.0
    rank = max(1, round(pct / 100.0 * len(sorted_values)))
    return sorted_values[min(rank, len(sorted_values)) - 1]


async def run_storm(
    *,
    scenario: str,
    count: int,
    concurrency: int,
    make_task: TaskFactory,
) -> StormResult:
    """Run ``count`` units of ``make_task`` with at most ``concurrency`` in flight."""
    semaphore = asyncio.Semaphore(concurrency)
    latencies: list[float] = []
    succeeded = 0
    failed = 0

    async def guarded(index: int) -> None:
        nonlocal succeeded, failed
        async with semaphore:
            started = time.perf_counter()
            try:
                await make_task(index)
                outcome = "success"
                succeeded += 1
            except Exception:  # noqa: BLE001 - a failed unit is an expected outcome here
                outcome = "failure"
                failed += 1
            elapsed = time.perf_counter() - started
            latencies.append(elapsed)
            metrics.REQUESTS.labels(scenario=scenario, outcome=outcome).inc()
            metrics.REQUEST_LATENCY.labels(scenario=scenario).observe(elapsed)

    wall_start = time.perf_counter()
    await asyncio.gather(*(guarded(i) for i in range(count)))
    duration = time.perf_counter() - wall_start
    metrics.STORM_DURATION.labels(scenario=scenario).observe(duration)

    latencies.sort()
    rps = count / duration if duration > 0 else float(count)
    return StormResult(
        scenario=scenario,
        dry_run=False,  # overwritten by the caller, which knows the effective mode
        requested=count,
        succeeded=succeeded,
        failed=failed,
        duration_seconds=round(duration, 4),
        requests_per_second=round(rps, 2),
        latency_p50_ms=round(_percentile(latencies, 50) * 1000, 3),
        latency_p95_ms=round(_percentile(latencies, 95) * 1000, 3),
        latency_max_ms=round((latencies[-1] if latencies else 0.0) * 1000, 3),
    )
