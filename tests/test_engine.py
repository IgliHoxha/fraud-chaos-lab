import pytest

from app.chaos.engine import _percentile, run_storm


@pytest.mark.parametrize(
    ("values", "pct", "expected"),
    [
        ([], 50, 0.0),
        ([1.0], 95, 1.0),
        ([1.0, 2.0, 3.0, 4.0], 50, 2.0),
        ([1.0, 2.0, 3.0, 4.0], 100, 4.0),
    ],
)
def test_percentile(values, pct, expected):
    assert _percentile(sorted(values), pct) == expected


async def test_run_storm_counts_success_and_failure():
    async def make_task(index: int) -> None:
        if index % 5 == 0:
            raise RuntimeError("boom")

    result = await run_storm(scenario="unit", count=20, concurrency=8, make_task=make_task)
    assert result.requested == 20
    assert result.failed == 4  # indices 0,5,10,15
    assert result.succeeded == 16
    assert result.requests_per_second > 0


async def test_run_storm_respects_concurrency_cap():
    import asyncio

    active = 0
    peak = 0

    async def make_task(_: int) -> None:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.005)
        active -= 1

    await run_storm(scenario="unit", count=50, concurrency=5, make_task=make_task)
    assert peak <= 5
