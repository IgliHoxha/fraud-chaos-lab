"""The three attack vectors the lab can unleash.

Every scenario resolves its size/concurrency/dry-run from the request (falling
back to config), builds a per-unit coroutine, and hands it to the engine. The
scenarios never decide *where* traffic goes on their own - endpoints come from
config, and an unconfigured endpoint keeps the unit in dry-run.
"""

from __future__ import annotations

import asyncio

from app.chaos.engine import run_storm
from app.config import Settings
from app.models import StormRequest, StormResult
from app.providers.client import ProviderClient
from app.synthetic.identity import IdentityFactory


def _resolve(request: StormRequest, settings: Settings) -> tuple[int, int, bool]:
    """Merge a request with server config into (count, concurrency, dry_run)."""
    count = request.count or settings.default_storm_size
    count = min(count, settings.max_storm_size)
    concurrency = request.concurrency or settings.concurrency
    dry_run = settings.effectively_dry_run if request.dry_run is None else request.dry_run
    # A missing target always forces dry-run - you cannot flood nothing.
    dry_run = dry_run or not settings.storm_target_base_url
    return count, concurrency, dry_run


async def _run(
    *,
    scenario: str,
    request: StormRequest,
    settings: Settings,
    build_task,
) -> StormResult:
    count, concurrency, dry_run = _resolve(request, settings)
    identities = IdentityFactory(seed=settings.faker_seed)
    async with ProviderClient(
        dry_run=dry_run, timeout_seconds=settings.request_timeout_seconds
    ) as client:
        make_task = build_task(client, identities)
        result = await run_storm(
            scenario=scenario, count=count, concurrency=concurrency, make_task=make_task
        )
    return result.model_copy(update={"dry_run": dry_run})


async def subscription_churn(request: StormRequest, settings: Settings) -> StormResult:
    """Botnet-style signup/cancel churn across three credit-data providers."""
    provider_1 = settings.endpoint(settings.provider_1_url, "/provider-1/subscriptions")
    provider_2 = settings.endpoint(settings.provider_2_url, "/provider-2/subscriptions")
    provider_3 = settings.endpoint(settings.provider_3_url, "/provider-3/subscriptions")

    def build_task(client: ProviderClient, identities: IdentityFactory):
        async def task(_: int) -> None:
            identity = identities.make().as_dict()
            # Subscribe to every provider concurrently...
            await asyncio.gather(
                client.post_json(provider_1, {"action": "subscribe", "identity": identity}),
                client.post_json(provider_2, {"action": "subscribe", "identity": identity}),
                client.post_json(provider_3, {"action": "subscribe", "identity": identity}),
            )
            # ...then immediately churn to probe consistency limits.
            await asyncio.gather(
                client.post_json(provider_1, {"action": "unsubscribe", "identity": identity}),
                client.post_json(provider_2, {"action": "unsubscribe", "identity": identity}),
                client.post_json(provider_3, {"action": "unsubscribe", "identity": identity}),
            )

        return task

    return await _run(
        scenario="subscription-churn", request=request, settings=settings, build_task=build_task
    )


async def service_1_flood(request: StormRequest, settings: Settings) -> StormResult:
    """Flood upstream service-1 with critical FRAUD_DETECTED events."""
    service_1 = settings.endpoint(settings.service_1_url, "/service-1/events")

    def build_task(client: ProviderClient, identities: IdentityFactory):
        async def task(index: int) -> None:
            identity = identities.make()
            await client.post_json(
                service_1,
                {
                    "type": "FRAUD_DETECTED",
                    "severity": "CRITICAL",
                    "sequence": index,
                    "subject_id": identity.external_id,
                    "subject_name": identity.name,
                },
            )

        return task

    return await _run(
        scenario="service-1-flood", request=request, settings=settings, build_task=build_task
    )


async def service_2_storm(request: StormRequest, settings: Settings) -> StormResult:
    """Simulate a city-wide IoT storm against upstream service-2."""
    service_2 = settings.endpoint(settings.service_2_url, "/service-2/ingest")

    def build_task(client: ProviderClient, identities: IdentityFactory):
        async def task(index: int) -> None:
            await client.post_json(
                service_2,
                {
                    "device_id": f"iot-{index:06d}",
                    "event": "SMOKE_DETECTED",
                    "temperature_c": 300 + (index % 200),
                    "smoke_density": 0.9,
                },
            )

        return task

    return await _run(
        scenario="service-2-storm", request=request, settings=settings, build_task=build_task
    )
