"""GET /api/v1/tours

Tours are not yet tracked in a dedicated table.  We derive scheduled tours
from completed / in-progress matches by scanning agent3_logs for result JSON
that contains scheduling signals, and fall back to an empty list cleanly.

WARNING: The current implementation uses fragile keyword matching ("tour",
"schedule", "showing") against Agent3Log.result JSON text. `scheduledAt` is
the log timestamp, NOT the actual tour date. This is a temporary heuristic
for the hackathon demo.

TODO: Create a dedicated Tour table with columns: id, user_id, apartment_id,
scheduled_at, status, address, notes, created_at. Replace this heuristic with
proper CRUD operations once the Tour model is in place.
"""
from __future__ import annotations

import json
from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.agent_logs import Agent3Log
from app.models.match import Match
from app.models.user import User
from app.routers.v1.deps import get_current_user

router = APIRouter(prefix="/tours", tags=["v1-tours"])


# ---------------------------------------------------------------------------
# Out schema
# ---------------------------------------------------------------------------


class TourOut(BaseModel):
    id: str
    listingId: str
    listingTitle: str
    scheduledAt: Optional[str]
    status: str  # "scheduled" | "completed" | "cancelled"
    address: Optional[str]
    notes: Optional[str]


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.get("", response_model=list[TourOut])
async def list_tours(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[TourOut]:
    uid = current_user.id

    # Look for agent3 logs that mention tour scheduling
    a3_result = await db.execute(
        select(Agent3Log)
        .options(selectinload(Agent3Log.apartment))
        .where(Agent3Log.user_id == uid)
        .order_by(Agent3Log.timestamp.desc())
    )
    a3_logs = a3_result.scalars().all()

    tours: list[TourOut] = []
    seen_apt_ids: set[str] = set()

    for log in a3_logs:
        if not log.result:
            continue
        try:
            data = json.loads(log.result)
        except (ValueError, TypeError):
            continue

        # Check if this log entry is about scheduling a tour
        contact_channel = str(data.get("contact_channel", "")).lower()
        status_val = str(data.get("status", "")).lower()
        msg_text = str(data.get("message", "")).lower()
        is_tour = (
            "tour" in contact_channel
            or "tour" in status_val
            or "tour" in msg_text
            or "schedule" in msg_text
            or "showing" in msg_text
        )
        if not is_tour:
            continue

        apt_id = log.apartment_id
        if not apt_id or apt_id in seen_apt_ids:
            continue
        seen_apt_ids.add(apt_id)

        apt = log.apartment
        listing_title = apt.name if apt else apt_id
        address = apt.name if apt else None

        # Try to extract scheduled time from the message
        scheduled_at: str | None = None
        ai_msg = data.get("message", "")
        if ai_msg:
            # Very naive extraction — just store the log timestamp as proxy
            scheduled_at = log.timestamp.isoformat()

        tours.append(
            TourOut(
                id=log.id,
                listingId=apt_id,
                listingTitle=listing_title,
                scheduledAt=scheduled_at,
                status="scheduled",
                address=address,
                notes=data.get("ai_reasoning") or data.get("message"),
            )
        )

    # Also check in-progress matches where automation produced tour-related messages
    # by looking at match status. If nothing was found via logs, return empty list.
    return tours
