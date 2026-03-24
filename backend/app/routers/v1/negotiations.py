"""
GET  /api/v1/negotiations
POST /api/v1/negotiations
GET  /api/v1/negotiations/:listingId/messages
POST /api/v1/negotiations/:listingId/messages
PUT  /api/v1/negotiations/:listingId/status
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.apartment import Apartment
from app.models.match import Match
from app.models.message import Message
from app.models.user import User
from app.routers.v1.deps import get_current_user

router = APIRouter(prefix="/negotiations", tags=["v1-negotiations"])


# ---------------------------------------------------------------------------
# Status mapping (Match.status ↔ frontend NegotiationStatus)
# ---------------------------------------------------------------------------

_MATCH_TO_NEGO: dict[str, str] = {
    "not_started": "pending",
    "in_progress": "negotiating",
    "completed": "accepted",
}

_NEGO_TO_MATCH: dict[str, str] = {
    "pending": "not_started",
    "negotiating": "in_progress",
    "responded": "in_progress",
    "accepted": "completed",
    "rejected": "completed",
}


# ---------------------------------------------------------------------------
# Out schemas
# ---------------------------------------------------------------------------


class NegotiationOut(BaseModel):
    id: str
    listingId: str
    listingTitle: str
    status: str
    matchScore: float | None
    commuteMinutes: int | None
    createdAt: str


class MessageOut(BaseModel):
    id: str
    role: str  # "agent" | "host" | "user"
    text: str
    timestamp: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=list[NegotiationOut])
async def list_negotiations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[NegotiationOut]:
    matches_result = await db.execute(
        select(Match)
        .options(selectinload(Match.apartment))
        .where(Match.user_id == current_user.id, Match.status != "not_started")
    )
    matches = matches_result.scalars().all()

    return [
        NegotiationOut(
            id=m.id,
            listingId=m.apartment_id,
            listingTitle=m.apartment.name if m.apartment else m.apartment_id,
            status=_MATCH_TO_NEGO.get(m.status, m.status),
            matchScore=m.match_score,
            commuteMinutes=m.commute_minutes,
            createdAt=m.created_at.isoformat(),
        )
        for m in matches
    ]


class StartNegotiationRequest(BaseModel):
    listingId: str


@router.post("", response_model=NegotiationOut, status_code=201)
async def start_negotiation(
    body: StartNegotiationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> NegotiationOut:
    apt = await db.get(Apartment, body.listingId)
    if not apt:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Get or create match
    match = (
        await db.execute(
            select(Match).where(
                Match.user_id == current_user.id,
                Match.apartment_id == body.listingId,
            ).limit(1)
        )
    ).scalar_one_or_none()

    if match is None:
        match = Match(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            apartment_id=body.listingId,
            status="in_progress",
        )
        db.add(match)
    elif match.status == "not_started":
        match.status = "in_progress"

    await db.commit()
    await db.refresh(match)

    # Trigger agent3 in background if host_email is present
    if apt.host_email:
        from app.agents.agent3_outreach import run_agent3
        background_tasks.add_task(run_agent3, match.id)

    return NegotiationOut(
        id=match.id,
        listingId=match.apartment_id,
        listingTitle=apt.name,
        status=_MATCH_TO_NEGO.get(match.status, match.status),
        matchScore=match.match_score,
        commuteMinutes=match.commute_minutes,
        createdAt=match.created_at.isoformat(),
    )


@router.get("/{listing_id}/messages", response_model=list[MessageOut])
async def get_messages(
    listing_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[MessageOut]:
    match = (
        await db.execute(
            select(Match).where(
                Match.user_id == current_user.id,
                Match.apartment_id == listing_id,
            ).limit(1)
        )
    ).scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    messages_result = await db.execute(
        select(Message)
        .where(Message.match_id == match.id)
        .order_by(Message.timestamp.asc())
    )
    msgs = messages_result.scalars().all()

    return [
        MessageOut(
            id=m.id,
            role=m.type,  # "agent" | "host"
            text=m.text,
            timestamp=m.timestamp.isoformat(),
        )
        for m in msgs
    ]


class SendMessageRequest(BaseModel):
    text: str
    role: str = "user"  # "user" | "agent" | "host"


@router.post("/{listing_id}/messages", response_model=MessageOut, status_code=201)
async def send_message(
    listing_id: str,
    body: SendMessageRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> MessageOut:
    match = (
        await db.execute(
            select(Match).where(
                Match.user_id == current_user.id,
                Match.apartment_id == listing_id,
            ).limit(1)
        )
    ).scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    _VALID_ROLES = {"user", "agent", "host"}
    if body.role not in _VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"role must be one of {sorted(_VALID_ROLES)}")

    msg = Message(
        id=str(uuid.uuid4()),
        match_id=match.id,
        type=body.role,
        timestamp=datetime.now(tz=timezone.utc),
        text=body.text,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    return MessageOut(
        id=msg.id,
        role=msg.type,
        text=msg.text,
        timestamp=msg.timestamp.isoformat(),
    )


class UpdateStatusRequest(BaseModel):
    status: str  # "accept" | "reject" | "pause"


class UpdateStatusResponse(BaseModel):
    listingId: str
    status: str


@router.put("/{listing_id}/status", response_model=UpdateStatusResponse)
async def update_negotiation_status(
    listing_id: str,
    body: UpdateStatusRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> UpdateStatusResponse:
    match = (
        await db.execute(
            select(Match).where(
                Match.user_id == current_user.id,
                Match.apartment_id == listing_id,
            ).limit(1)
        )
    ).scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    action_map = {
        "accept": "completed",
        "reject": "completed",
        "pause": "not_started",
    }
    new_status = action_map.get(body.status)
    if not new_status:
        raise HTTPException(status_code=400, detail="status must be accept, reject, or pause")

    match.status = new_status
    await db.commit()

    frontend_status_map = {"accept": "accepted", "reject": "rejected", "pause": "pending"}
    return UpdateStatusResponse(
        listingId=listing_id,
        status=frontend_status_map.get(body.status, body.status),
    )
