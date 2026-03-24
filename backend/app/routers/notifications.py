import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationRead, NotificationUpdate

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=List[NotificationRead])
async def list_notifications(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/notifications/{notification_id}", response_model=NotificationRead)
async def get_notification(notification_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Notification, notification_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Notification not found")
    return obj


@router.post("/notifications", response_model=NotificationRead, status_code=201)
async def create_notification(body: NotificationCreate, db: AsyncSession = Depends(get_db)):
    obj = Notification(id=str(uuid.uuid4()), **body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/notifications/{notification_id}", response_model=NotificationRead)
async def update_notification(notification_id: str, body: NotificationUpdate, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Notification, notification_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Notification not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/notifications/{notification_id}", status_code=204)
async def delete_notification(notification_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Notification, notification_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.delete(obj)
    await db.commit()


@router.get("/users/{user_id}/notifications", response_model=List[NotificationRead])
async def get_user_notifications(user_id: str, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Notification).where(Notification.user_id == user_id).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.patch("/notifications/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(notification_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Notification, notification_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Notification not found")
    obj.read = True
    await db.commit()
    await db.refresh(obj)
    return obj
