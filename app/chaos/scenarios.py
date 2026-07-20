"""The three attack vectors the lab can unleash.

Every scenario resolves its size/concurrency/dry-run from the request (falling
back to config), builds a per-unit coroutine, and hands it to the engine. The
scenarios never decide *where* traffic goes on their own — endpoints come from
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
    # A missing target always forces dry-run — you cannot flood nothing.
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
    dnb = settings.endpoint(settings.dnb_url, "/dnb/subscriptions")
    valitive = settings.endpoint(settings.valitive_url, "/valitive/subscriptions")
    creditsafe = settings.endpoint(settings.creditsafe_url, "/creditsafe/subscriptions")

    def build_task(client: ProviderClient, identities: IdentityFactory):
        async def task(_: int) -> None:
            identity = identities.make().as_dict()
            # Subscribe to every provider concurrently...
            await asyncio.gather(
                client.post_json(dnb, {"action": "subscribe", "identity": identity}),
                client.post_json(valitive, {"action": "subscribe", "identity": identity}),
                client.post_json(creditsafe, {"action": "subscribe", "identity": identity}),
            )
            # ...then immediately churn to probe consistency limits.
            await asyncio.gather(
                client.post_json(dnb, {"action": "unsubscribe", "identity": identity}),
                client.post_json(valitive, {"action": "unsubscribe", "identity": identity}),
                client.post_json(creditsafe, {"action": "unsubscribe", "identity": identity}),
            )

        return task

    return await _run(
        scenario="subscription-churn", request=request, settings=settings, build_task=build_task
    )


async def crm_flood(request: StormRequest, settings: Settings) -> StormResult:
    """Flood the internal CRM with critical FRAUD_DETECTED events."""
    crm = settings.endpoint(settings.crm_url, "/crm/events")

    def build_task(client: ProviderClient, identities: IdentityFactory):
        async def task(index: int) -> None:
            identity = identities.make()
            await client.post_json(
                crm,
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
        scenario="crm-flood", request=request, settings=settings, build_task=build_task
    )


async def alarm_storm(request: StormRequest, settings: Settings) -> StormResult:
    """Simulate a city-wide IoT alarm storm against the alarm gateway."""
    gateway = settings.endpoint(settings.alarm_gateway_url, "/alarms/ingest")

    def build_task(client: ProviderClient, identities: IdentityFactory):
        async def task(index: int) -> None:
            await client.post_json(
                gateway,
                {
                    "device_id": f"iot-{index:06d}",
                    "event": "SMOKE_DETECTED",
                    "temperature_c": 300 + (index % 200),
                    "smoke_density": 0.9,
                },
            )

        return task

    return await _run(
        scenario="alarm-storm", request=request, settings=settings, build_task=build_task
    )
