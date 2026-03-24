"""Agents router.

Exposes HTTP endpoints that trigger background agent tasks and surface
per-resource agent status. Also provides a dev-only endpoint for
simulating host replies during Agent 3 testing.
"""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent_logs import Agent1Log
from app.models.apartment import Apartment
from app.models.match import Match
from app.models.message import Message
from app.models.preferences import NegotiationPreferences
from app.models.user import User
from app.agents.agent1_image import is_agent1_running, run_agent1, run_agent1_batch
from app.agents.agent2_recommend import run_agent2
from app.agents.agent3_outreach import run_agent3
from app.constants import DEBUG, SMTP_FROM

router = APIRouter(prefix="/agents", tags=["agents"])

# ---------------------------------------------------------------------------
# Rate limiter — reuse the same key function as main.py.
# Agent endpoints call Claude (external API), so abuse is expensive.
# OWASP API4:2023 Unrestricted Resource Consumption.
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# Dev-mode guard dependency.
# OWASP A05:2021 Security Misconfiguration — debug surfaces must not be
# reachable in production.
# ---------------------------------------------------------------------------
async def require_debug() -> None:
    """Raise HTTP 404 when DEBUG env var is not set to 'true'.

    Returns 404 rather than 403 to avoid advertising the endpoint's existence
    to non-development callers (security through obscurity as a secondary
    control, not a primary one).
    """
    if not DEBUG:
        raise HTTPException(status_code=404, detail="Not found")


# ── Shared response model ─────────────────────────────────────────────────────


class AgentResponse(BaseModel):
    message: str


# ── Agent 1 endpoints ─────────────────────────────────────────────────────────


@router.post(
    "/apartments/{apartment_id}/analyze-images",
    status_code=202,
    response_model=AgentResponse,
)
@limiter.limit("10/minute")
async def trigger_image_analysis(
    request: Request,
    apartment_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Enqueue Agent 1 image analysis for a single apartment.

    Returns 202 immediately; analysis runs asynchronously.
    """
    apt = await db.get(Apartment, apartment_id)
    if not apt:
        raise HTTPException(status_code=404, detail="Apartment not found")
    if not apt.images:
        raise HTTPException(status_code=400, detail="Apartment has no images to analyze")
    background_tasks.add_task(run_agent1, apartment_id)
    return AgentResponse(message=f"Image analysis started for apartment {apartment_id}")


@router.post(
    "/apartments/analyze-all",
    status_code=202,
    response_model=AgentResponse,
)
@limiter.limit("10/minute")
async def trigger_image_analysis_batch(
    request: Request,
    background_tasks: BackgroundTasks,
) -> AgentResponse:
    """Manually trigger the Agent 1 batch job (normally runs every 2 hours).

    Analyzes all apartments whose image_labels are empty or null.
    """
    background_tasks.add_task(run_agent1_batch)
    return AgentResponse(message="Batch image analysis started for all unanalyzed apartments")


# ── Agent 2 endpoints ─────────────────────────────────────────────────────────


@router.post(
    "/users/{user_id}/rank-matches",
    status_code=202,
    response_model=AgentResponse,
)
@limiter.limit("10/minute")
async def trigger_recommendation(
    request: Request,
    user_id: str,
    background_tasks: BackgroundTasks,
    top_n: int = 20,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Enqueue Agent 2 match ranking for a user.

    Requires at least one existing Match row; run the filter endpoint first.
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    match_check = (
        await db.execute(select(Match).where(Match.user_id == user_id).limit(1))
    ).scalar_one_or_none()
    if not match_check:
        raise HTTPException(
            status_code=400,
            detail="User has no matches. Run /run-filter first.",
        )
    background_tasks.add_task(run_agent2, user_id, top_n)
    return AgentResponse(message=f"Match ranking started for user {user_id}")


# ── Agent 3 endpoints ─────────────────────────────────────────────────────────


@router.post(
    "/matches/{match_id}/contact",
    status_code=202,
    response_model=AgentResponse,
)
@limiter.limit("10/minute")
async def trigger_outreach(
    request: Request,
    match_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Enqueue Agent 3 autonomous negotiation for a single match.

    Validates that automation is enabled, the apartment has a host email,
    and the match has not already been completed.
    """
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    nego = (
        await db.execute(
            select(NegotiationPreferences)
            .where(NegotiationPreferences.user_id == match.user_id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if not nego or not nego.enable_automation:
        raise HTTPException(status_code=400, detail="Automation disabled for this user")

    apt = await db.get(Apartment, match.apartment_id)
    if not apt or not apt.host_email:
        raise HTTPException(status_code=400, detail="Apartment has no host email")

    if match.status == "completed":
        raise HTTPException(
            status_code=409, detail="Outreach already completed for this match"
        )

    background_tasks.add_task(run_agent3, match_id)
    return AgentResponse(message=f"Outreach started for match {match_id}")


@router.post("/users/{user_id}/contact-relevant", status_code=202)
@limiter.limit("10/minute")
async def trigger_outreach_relevant(
    request: Request,
    user_id: str,
    background_tasks: BackgroundTasks,
    min_score: float = 0.8,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger Agent 3 on all matches with score >= min_score for a user.

    Skips matches already marked as completed. Returns the count enqueued.
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(Match).where(
            Match.user_id == user_id,
            Match.match_score >= min_score,
            Match.status != "completed",
        )
    )
    relevant_matches = result.scalars().all()

    if not relevant_matches:
        raise HTTPException(
            status_code=404,
            detail=f"No relevant matches found with score >= {min_score}",
        )

    for match in relevant_matches:
        background_tasks.add_task(run_agent3, match.id)

    return {
        "message": f"Outreach started for {len(relevant_matches)} relevant matches",
        "count": len(relevant_matches),
    }


# ── Status endpoints ──────────────────────────────────────────────────────────


@router.get("/apartments/{apartment_id}/status")
async def get_apartment_agent_status(
    apartment_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return current Agent 1 state for an apartment (labels + last log entry)."""
    apt = await db.get(Apartment, apartment_id)
    if not apt:
        raise HTTPException(status_code=404, detail="Apartment not found")

    last_log: Agent1Log | None = (
        await db.execute(
            select(Agent1Log)
            .where(Agent1Log.apartment_id == apartment_id)
            .order_by(Agent1Log.timestamp.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return {
        "apartment_id": apartment_id,
        "is_running": is_agent1_running(apartment_id),
        "image_labels": apt.image_labels or [],
        "last_agent1_log": {
            "id": last_log.id,
            "timestamp": last_log.timestamp.isoformat(),
            "result": json.loads(last_log.result) if last_log.result else None,
        }
        if last_log
        else None,
    }


@router.get("/users/{user_id}/match-status")
async def get_user_match_status(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return all matches for a user, sorted by score descending."""
    result = await db.execute(select(Match).where(Match.user_id == user_id))
    matches = result.scalars().all()

    return {
        "user_id": user_id,
        "total_matches": len(matches),
        "matches": [
            {
                "match_id": m.id,
                "apartment_id": m.apartment_id,
                "status": m.status,
                "match_score": m.match_score,
                "match_reasoning": m.match_reasoning,
            }
            for m in sorted(matches, key=lambda x: x.match_score or 0, reverse=True)
        ],
    }


# ── Dev endpoint: simulate host reply ────────────────────────────────────────


class HostReplyRequest(BaseModel):
    # Reject blank text so the dev simulation endpoint cannot insert empty
    # host-reply rows that would confuse the negotiation loop.
    text: str = Field(..., min_length=1, max_length=10_000)


@router.post("/dev/matches/{match_id}/simulate-host-reply", status_code=201)
async def simulate_host_reply(
    match_id: str,
    body: HostReplyRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_debug),
) -> dict:
    """DEV ONLY: Insert a Message(type='host') row and send a visible SMTP email.

    Writes to both the messages table (so Agent 3's poll loop picks it up) and
    sends via SMTP (so the reply is visible in the Mailpit UI alongside the
    agent's outbound emails). Mailpit and the DB are always kept in sync.
    """
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    apt = await db.get(Apartment, match.apartment_id)
    if not apt:
        raise HTTPException(status_code=404, detail="Apartment not found")

    msg = Message(
        id=str(uuid.uuid4()),
        match_id=match_id,
        type="host",
        timestamp=datetime.utcnow(),
        text=body.text,
    )
    db.add(msg)
    await db.commit()

    subject = f"Re: Apartment Inquiry: {apt.name}"
    try:
        import asyncio

        await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: _send_host_reply(
                to=SMTP_FROM,
                from_addr=apt.host_email or "host@rento.local",
                subject=subject,
                body=body.text,
            ),
        )
    except Exception:
        # SMTP failure is non-fatal: the DB row is committed and the agent
        # will still process the reply. Log but don't roll back.
        pass

    return {"message": "Host reply simulated", "message_id": msg.id}


@router.post("/dev/matches/{match_id}/inject-email-reply", status_code=201)
async def inject_email_reply(
    match_id: str,
    body: HostReplyRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_debug),
) -> dict:
    """DEV ONLY: Send a real SMTP email AND insert a Message(type='host') row.

    Keeps Mailpit and the DB in sync: the reply appears in the Mailpit UI
    (via SMTP) and Agent 3's poll loop picks it up (via the messages table).
    """
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    apt = await db.get(Apartment, match.apartment_id)
    if not apt:
        raise HTTPException(status_code=404, detail="Apartment not found")

    subject = f"Re: Apartment Inquiry: {apt.name}"
    from_addr = apt.host_email or "host@rento.local"

    try:
        import asyncio

        await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: _send_host_reply(
                to=SMTP_FROM,
                from_addr=from_addr,
                subject=subject,
                body=body.text,
            ),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"SMTP send failed: {exc}") from exc

    msg = Message(
        id=str(uuid.uuid4()),
        match_id=match_id,
        type="host",
        timestamp=datetime.utcnow(),
        text=body.text,
    )
    db.add(msg)
    await db.commit()

    return {
        "message": "Host reply injected",
        "message_id": msg.id,
        "subject": subject,
        "to": SMTP_FROM,
        "from": from_addr,
    }


def _send_host_reply(to: str, from_addr: str, subject: str, body: str) -> None:
    """Send an email impersonating the host. Used only by the dev injection endpoints."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    from app.constants import SMTP_HOST, SMTP_PORT

    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.sendmail(from_addr, to, msg.as_string())
