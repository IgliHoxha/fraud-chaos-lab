"""The /chaos routes — one per attack vector."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.chaos import scenarios
from app.config import Settings, get_settings
from app.models import StormRequest, StormResult

router = APIRouter(prefix="/chaos", tags=["chaos"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.post("/subscription-churn", response_model=StormResult, summary="Subscription churn storm")
async def subscription_churn(
    settings: SettingsDep,
    request: StormRequest | None = None,
) -> StormResult:
    return await scenarios.subscription_churn(request or StormRequest(), settings)


@router.post("/service-1-flood", response_model=StormResult, summary="Service-1 fraud flood")
async def service_1_flood(
    settings: SettingsDep,
    request: StormRequest | None = None,
) -> StormResult:
    return await scenarios.service_1_flood(request or StormRequest(), settings)


@router.post("/service-2-storm", response_model=StormResult, summary="Service-2 IoT storm")
async def service_2_storm(
    settings: SettingsDep,
    request: StormRequest | None = None,
) -> StormResult:
    return await scenarios.service_2_storm(request or StormRequest(), settings)
