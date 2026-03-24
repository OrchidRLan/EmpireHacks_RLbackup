"""GET /api/v1/preferences, PUT /api/v1/preferences/{housing,negotiation,notifications}"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.preferences import (
    NegotiationPreferences,
    NotificationPreferences,
    ObjectivePreferences,
)
from app.models.user import User
from app.routers.v1.deps import get_current_user

router = APIRouter(prefix="/preferences", tags=["v1-preferences"])


# ---------------------------------------------------------------------------
# Out schemas (camelCase for frontend)
# ---------------------------------------------------------------------------


class HousingOut(BaseModel):
    bedroomType: Optional[str] = None
    selectedAreas: list[str] = []
    minBudget: Optional[int] = None
    maxBudget: Optional[int] = None
    moveInDate: Optional[str] = None
    leaseLengthMonths: Optional[int] = None
    laundry: list[str] = []
    parking: list[str] = []
    pets: bool = False
    workLatitude: Optional[float] = None
    workLongitude: Optional[float] = None
    commuteMethod: Optional[str] = None
    maxCommuteMinutes: Optional[int] = None


class NegotiationOut(BaseModel):
    enableAutomation: bool = False
    negotiableItems: list[str] = []
    goals: list[str] = []
    maxRent: Optional[int] = None
    maxDeposit: Optional[int] = None
    latestMoveInDate: Optional[str] = None
    minLeaseMonths: Optional[int] = None
    maxLeaseMonths: Optional[int] = None
    negotiationStyle: Optional[str] = None


class NotificationsOut(BaseModel):
    enableNotifications: bool = True
    autoScheduling: bool = False
    notificationTypes: list[str] = []
    frequency: str = "realtime"


class PreferencesOut(BaseModel):
    housing: HousingOut
    negotiation: NegotiationOut
    notifications: NotificationsOut


# ---------------------------------------------------------------------------
# In schemas (camelCase → snake_case)
# ---------------------------------------------------------------------------


class HousingPatch(BaseModel):
    bedroomType: Optional[str] = None
    selectedAreas: Optional[list[str]] = None
    minBudget: Optional[int] = None
    maxBudget: Optional[int] = None
    moveInDate: Optional[str] = None
    leaseLengthMonths: Optional[int] = None
    laundry: Optional[list[str]] = None
    parking: Optional[list[str]] = None
    pets: Optional[bool] = None
    workLatitude: Optional[float] = None
    workLongitude: Optional[float] = None
    commuteMethod: Optional[str] = None
    maxCommuteMinutes: Optional[int] = None


class NegotiationPatch(BaseModel):
    enableAutomation: Optional[bool] = None
    negotiableItems: Optional[list[str]] = None
    goals: Optional[list[str]] = None
    maxRent: Optional[int] = None
    maxDeposit: Optional[int] = None
    latestMoveInDate: Optional[str] = None
    minLeaseMonths: Optional[int] = None
    maxLeaseMonths: Optional[int] = None
    negotiationStyle: Optional[str] = None


class NotificationsPatch(BaseModel):
    enableNotifications: Optional[bool] = None
    autoScheduling: Optional[bool] = None
    notificationTypes: Optional[list[str]] = None
    frequency: Optional[str] = None


# ---------------------------------------------------------------------------
# Converters
# ---------------------------------------------------------------------------


def _obj_prefs_to_out(obj: ObjectivePreferences | None) -> HousingOut:
    if obj is None:
        return HousingOut()
    return HousingOut(
        bedroomType=obj.bedroom_type,
        selectedAreas=obj.selected_areas or [],
        minBudget=obj.min_budget,
        maxBudget=obj.max_budget,
        moveInDate=obj.move_in_date.isoformat() if obj.move_in_date else None,
        leaseLengthMonths=obj.lease_length_months,
        laundry=obj.laundry or [],
        parking=obj.parking or [],
        pets=obj.pets,
        workLatitude=obj.work_latitude,
        workLongitude=obj.work_longitude,
        commuteMethod=obj.commute_method,
        maxCommuteMinutes=obj.max_commute_minutes,
    )


def _nego_prefs_to_out(obj: NegotiationPreferences | None) -> NegotiationOut:
    if obj is None:
        return NegotiationOut()
    return NegotiationOut(
        enableAutomation=obj.enable_automation,
        negotiableItems=obj.negotiable_items or [],
        goals=obj.goals or [],
        maxRent=obj.max_rent,
        maxDeposit=obj.max_deposit,
        latestMoveInDate=obj.latest_move_in_date.isoformat() if obj.latest_move_in_date else None,
        minLeaseMonths=obj.min_lease_months,
        maxLeaseMonths=obj.max_lease_months,
        negotiationStyle=obj.negotiation_style,
    )


def _notif_prefs_to_out(obj: NotificationPreferences | None) -> NotificationsOut:
    if obj is None:
        return NotificationsOut()
    return NotificationsOut(
        enableNotifications=obj.enable_notifications,
        autoScheduling=obj.auto_scheduling,
        notificationTypes=obj.notification_types or [],
        frequency=obj.frequency,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=PreferencesOut)
async def get_preferences(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> PreferencesOut:
    uid = current_user.id

    obj_pref = (
        await db.execute(
            select(ObjectivePreferences).where(ObjectivePreferences.user_id == uid).limit(1)
        )
    ).scalar_one_or_none()

    nego_pref = (
        await db.execute(
            select(NegotiationPreferences).where(NegotiationPreferences.user_id == uid).limit(1)
        )
    ).scalar_one_or_none()

    notif_pref = (
        await db.execute(
            select(NotificationPreferences).where(NotificationPreferences.user_id == uid).limit(1)
        )
    ).scalar_one_or_none()

    return PreferencesOut(
        housing=_obj_prefs_to_out(obj_pref),
        negotiation=_nego_prefs_to_out(nego_pref),
        notifications=_notif_prefs_to_out(notif_pref),
    )


@router.put("/housing", response_model=HousingOut)
async def update_housing(
    body: HousingPatch,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> HousingOut:
    uid = current_user.id
    obj_pref = (
        await db.execute(
            select(ObjectivePreferences).where(ObjectivePreferences.user_id == uid).limit(1)
        )
    ).scalar_one_or_none()

    if obj_pref is None:
        # Need at least minimal required fields to create a new record
        obj_pref = ObjectivePreferences(
            id=str(uuid.uuid4()),
            user_id=uid,
            bedroom_type=body.bedroomType or "1BR",
            min_budget=body.minBudget or 0,
            max_budget=body.maxBudget or 9999,
            move_in_date=date.fromisoformat(body.moveInDate) if body.moveInDate else date.today(),
        )
        db.add(obj_pref)

    patch = body.model_dump(exclude_none=True)
    mapping: dict[str, str] = {
        "bedroomType": "bedroom_type",
        "selectedAreas": "selected_areas",
        "minBudget": "min_budget",
        "maxBudget": "max_budget",
        "moveInDate": "move_in_date",
        "leaseLengthMonths": "lease_length_months",
        "laundry": "laundry",
        "parking": "parking",
        "pets": "pets",
        "workLatitude": "work_latitude",
        "workLongitude": "work_longitude",
        "commuteMethod": "commute_method",
        "maxCommuteMinutes": "max_commute_minutes",
    }
    for camel, snake in mapping.items():
        if camel in patch:
            val = patch[camel]
            if camel == "moveInDate" and isinstance(val, str):
                val = date.fromisoformat(val)
            setattr(obj_pref, snake, val)

    await db.commit()
    await db.refresh(obj_pref)
    return _obj_prefs_to_out(obj_pref)


@router.put("/negotiation", response_model=NegotiationOut)
async def update_negotiation(
    body: NegotiationPatch,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> NegotiationOut:
    uid = current_user.id
    nego_pref = (
        await db.execute(
            select(NegotiationPreferences).where(NegotiationPreferences.user_id == uid).limit(1)
        )
    ).scalar_one_or_none()

    if nego_pref is None:
        nego_pref = NegotiationPreferences(id=str(uuid.uuid4()), user_id=uid)
        db.add(nego_pref)

    patch = body.model_dump(exclude_none=True)
    mapping: dict[str, str] = {
        "enableAutomation": "enable_automation",
        "negotiableItems": "negotiable_items",
        "goals": "goals",
        "maxRent": "max_rent",
        "maxDeposit": "max_deposit",
        "latestMoveInDate": "latest_move_in_date",
        "minLeaseMonths": "min_lease_months",
        "maxLeaseMonths": "max_lease_months",
        "negotiationStyle": "negotiation_style",
    }
    for camel, snake in mapping.items():
        if camel in patch:
            val = patch[camel]
            if camel == "latestMoveInDate" and isinstance(val, str):
                val = date.fromisoformat(val)
            setattr(nego_pref, snake, val)

    await db.commit()
    await db.refresh(nego_pref)
    return _nego_prefs_to_out(nego_pref)


@router.put("/notifications", response_model=NotificationsOut)
async def update_notifications(
    body: NotificationsPatch,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> NotificationsOut:
    uid = current_user.id
    notif_pref = (
        await db.execute(
            select(NotificationPreferences).where(NotificationPreferences.user_id == uid).limit(1)
        )
    ).scalar_one_or_none()

    if notif_pref is None:
        notif_pref = NotificationPreferences(id=str(uuid.uuid4()), user_id=uid)
        db.add(notif_pref)

    patch = body.model_dump(exclude_none=True)
    mapping: dict[str, str] = {
        "enableNotifications": "enable_notifications",
        "autoScheduling": "auto_scheduling",
        "notificationTypes": "notification_types",
        "frequency": "frequency",
    }
    for camel, snake in mapping.items():
        if camel in patch:
            setattr(notif_pref, snake, patch[camel])

    await db.commit()
    await db.refresh(notif_pref)
    return _notif_prefs_to_out(notif_pref)
