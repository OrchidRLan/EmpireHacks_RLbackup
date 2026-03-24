import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.preferences import (
    NegotiationPreferences,
    NotificationPreferences,
    ObjectivePreferences,
    SubjectivePreferences,
)
from app.schemas.preferences import (
    NegotiationPreferencesCreate,
    NegotiationPreferencesRead,
    NegotiationPreferencesUpdate,
    NotificationPreferencesCreate,
    NotificationPreferencesRead,
    NotificationPreferencesUpdate,
    ObjectivePreferencesCreate,
    ObjectivePreferencesRead,
    ObjectivePreferencesUpdate,
    SubjectivePreferencesCreate,
    SubjectivePreferencesRead,
    SubjectivePreferencesUpdate,
)

router = APIRouter(tags=["preferences"])


# --- Objective Preferences ---

@router.get("/users/{user_id}/objective-preferences", response_model=List[ObjectivePreferencesRead])
async def list_objective_preferences(user_id: str, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ObjectivePreferences).where(ObjectivePreferences.user_id == user_id).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get("/users/{user_id}/objective-preferences/{pref_id}", response_model=ObjectivePreferencesRead)
async def get_objective_preferences(user_id: str, pref_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(ObjectivePreferences, pref_id)
    if not obj or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="Objective preferences not found")
    return obj


@router.post("/users/{user_id}/objective-preferences", response_model=ObjectivePreferencesRead, status_code=201)
async def create_objective_preferences(user_id: str, body: ObjectivePreferencesCreate, db: AsyncSession = Depends(get_db)):
    obj = ObjectivePreferences(id=str(uuid.uuid4()), **{**body.model_dump(), "user_id": user_id})
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/users/{user_id}/objective-preferences/{pref_id}", response_model=ObjectivePreferencesRead)
async def update_objective_preferences(
    user_id: str, pref_id: str, body: ObjectivePreferencesUpdate, db: AsyncSession = Depends(get_db)
):
    obj = await db.get(ObjectivePreferences, pref_id)
    if not obj or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="Objective preferences not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/users/{user_id}/objective-preferences/{pref_id}", status_code=204)
async def delete_objective_preferences(user_id: str, pref_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(ObjectivePreferences, pref_id)
    if not obj or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="Objective preferences not found")
    await db.delete(obj)
    await db.commit()


# --- Subjective Preferences ---

@router.get("/users/{user_id}/subjective-preferences", response_model=List[SubjectivePreferencesRead])
async def list_subjective_preferences(user_id: str, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SubjectivePreferences).where(SubjectivePreferences.user_id == user_id).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get("/users/{user_id}/subjective-preferences/{pref_id}", response_model=SubjectivePreferencesRead)
async def get_subjective_preferences(user_id: str, pref_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(SubjectivePreferences, pref_id)
    if not obj or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="Subjective preferences not found")
    return obj


@router.post("/users/{user_id}/subjective-preferences", response_model=SubjectivePreferencesRead, status_code=201)
async def create_subjective_preferences(user_id: str, body: SubjectivePreferencesCreate, db: AsyncSession = Depends(get_db)):
    obj = SubjectivePreferences(id=str(uuid.uuid4()), **{**body.model_dump(), "user_id": user_id})
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/users/{user_id}/subjective-preferences/{pref_id}", response_model=SubjectivePreferencesRead)
async def update_subjective_preferences(
    user_id: str, pref_id: str, body: SubjectivePreferencesUpdate, db: AsyncSession = Depends(get_db)
):
    obj = await db.get(SubjectivePreferences, pref_id)
    if not obj or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="Subjective preferences not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/users/{user_id}/subjective-preferences/{pref_id}", status_code=204)
async def delete_subjective_preferences(user_id: str, pref_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(SubjectivePreferences, pref_id)
    if not obj or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="Subjective preferences not found")
    await db.delete(obj)
    await db.commit()


# --- Negotiation Preferences ---

@router.get("/users/{user_id}/negotiation-preferences", response_model=List[NegotiationPreferencesRead])
async def list_negotiation_preferences(user_id: str, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NegotiationPreferences).where(NegotiationPreferences.user_id == user_id).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get("/users/{user_id}/negotiation-preferences/{pref_id}", response_model=NegotiationPreferencesRead)
async def get_negotiation_preferences(user_id: str, pref_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(NegotiationPreferences, pref_id)
    if not obj or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="Negotiation preferences not found")
    return obj


@router.post("/users/{user_id}/negotiation-preferences", response_model=NegotiationPreferencesRead, status_code=201)
async def create_negotiation_preferences(user_id: str, body: NegotiationPreferencesCreate, db: AsyncSession = Depends(get_db)):
    obj = NegotiationPreferences(id=str(uuid.uuid4()), **{**body.model_dump(), "user_id": user_id})
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/users/{user_id}/negotiation-preferences/{pref_id}", response_model=NegotiationPreferencesRead)
async def update_negotiation_preferences(
    user_id: str, pref_id: str, body: NegotiationPreferencesUpdate, db: AsyncSession = Depends(get_db)
):
    obj = await db.get(NegotiationPreferences, pref_id)
    if not obj or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="Negotiation preferences not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/users/{user_id}/negotiation-preferences/{pref_id}", status_code=204)
async def delete_negotiation_preferences(user_id: str, pref_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(NegotiationPreferences, pref_id)
    if not obj or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="Negotiation preferences not found")
    await db.delete(obj)
    await db.commit()


# --- Notification Preferences ---

@router.get("/users/{user_id}/notification-preferences", response_model=List[NotificationPreferencesRead])
async def list_notification_preferences(user_id: str, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NotificationPreferences).where(NotificationPreferences.user_id == user_id).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get("/users/{user_id}/notification-preferences/{pref_id}", response_model=NotificationPreferencesRead)
async def get_notification_preferences(user_id: str, pref_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(NotificationPreferences, pref_id)
    if not obj or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="Notification preferences not found")
    return obj


@router.post("/users/{user_id}/notification-preferences", response_model=NotificationPreferencesRead, status_code=201)
async def create_notification_preferences(user_id: str, body: NotificationPreferencesCreate, db: AsyncSession = Depends(get_db)):
    obj = NotificationPreferences(id=str(uuid.uuid4()), **{**body.model_dump(), "user_id": user_id})
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/users/{user_id}/notification-preferences/{pref_id}", response_model=NotificationPreferencesRead)
async def update_notification_preferences(
    user_id: str, pref_id: str, body: NotificationPreferencesUpdate, db: AsyncSession = Depends(get_db)
):
    obj = await db.get(NotificationPreferences, pref_id)
    if not obj or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="Notification preferences not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/users/{user_id}/notification-preferences/{pref_id}", status_code=204)
async def delete_notification_preferences(user_id: str, pref_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(NotificationPreferences, pref_id)
    if not obj or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="Notification preferences not found")
    await db.delete(obj)
    await db.commit()
