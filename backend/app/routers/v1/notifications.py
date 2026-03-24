"""GET /api/v1/notifications, PUT /api/v1/notifications/:id/read,
PUT /api/v1/notifications/read-all

Bridges the existing Notification model to the frontend notification shape.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.routers.v1.deps import get_current_user

router = APIRouter(prefix="/notifications", tags=["v1-notifications"])


# ---------------------------------------------------------------------------
# Out schemas
# ---------------------------------------------------------------------------


class NotificationOut(BaseModel):
    id: str
    type: str
    title: str
    message: str
    timestamp: str
    read: bool
    listingId: str | None


class PaginatedNotifications(BaseModel):
    items: list[NotificationOut]
    total: int
    page: int
    pageSize: int


class ReadResponse(BaseModel):
    id: str
    read: bool


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------


def _notif_to_out(n: Notification) -> NotificationOut:
    # The Notification model stores content as a plain string and type as a
    # category string.  We derive title as the first sentence of content and
    # use the full content as the message body.
    content = n.content or ""
    parts = content.split(". ", 1)
    title = parts[0] if parts else content
    message = content

    listing_id = n.match.apartment_id if n.match else None

    return NotificationOut(
        id=n.id,
        type=n.type,
        title=title[:120],
        message=message,
        timestamp=n.timestamp.isoformat(),
        read=n.read,
        listingId=listing_id,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedNotifications)
async def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
) -> PaginatedNotifications:
    uid = current_user.id
    offset = (page - 1) * pageSize

    total_result = await db.execute(
        select(func.count(Notification.id)).where(Notification.user_id == uid)
    )
    total = total_result.scalar_one()

    paged_result = await db.execute(
        select(Notification)
        .options(selectinload(Notification.match))
        .where(Notification.user_id == uid)
        .order_by(Notification.timestamp.desc())
        .offset(offset)
        .limit(pageSize)
    )
    items = [_notif_to_out(n) for n in paged_result.scalars().all()]

    return PaginatedNotifications(items=items, total=total, page=page, pageSize=pageSize)


@router.put("/read-all", response_model=dict)
async def mark_all_read(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.read == False,  # noqa: E712
        )
    )
    unread = result.scalars().all()
    for n in unread:
        n.read = True
    await db.commit()
    return {"updated": len(unread)}


@router.put("/{notification_id}/read", response_model=ReadResponse)
async def mark_read(
    notification_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ReadResponse:
    notif = await db.get(Notification, notification_id)
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.read = True
    await db.commit()
    return ReadResponse(id=notif.id, read=True)
