"""GET /api/v1/agent/status, POST /api/v1/agent/start, POST /api/v1/agent/stop,
GET /api/v1/agent/logs

Derives agent status from active matches and agent logs.
Maps Agent1Log / Agent2Log / Agent3Log to the frontend AgentLog format.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent_logs import Agent1Log, Agent2Log, Agent3Log
from app.models.match import Match
from app.models.user import User
from app.routers.v1.deps import get_current_user
from app.routers.v1.tours import list_tours

router = APIRouter(prefix="/agent", tags=["v1-agent"])


# ---------------------------------------------------------------------------
# Out schemas
# ---------------------------------------------------------------------------


class AgentStatusOut(BaseModel):
    isRunning: bool
    currentAction: str
    phase: str
    matchesFound: int
    negotiationsActive: int
    toursScheduled: int


class AgentLogOut(BaseModel):
    id: str
    timestamp: str
    level: str
    message: str
    phase: str


class PaginatedLogs(BaseModel):
    items: list[AgentLogOut]
    total: int
    page: int
    pageSize: int


class AgentControlResponse(BaseModel):
    isRunning: bool
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# In-process toggle — state is lost on server restart. This is intentional for
# the hackathon demo; a production version would persist to the database.
_agent_running: dict[str, bool] = {}


def _is_running(user_id: str) -> bool:
    return _agent_running.get(user_id, True)


def _set_running(user_id: str, value: bool) -> None:
    _agent_running[user_id] = value


def _infer_level_from_result(result: str | None) -> str:
    """Guess log level from a JSON result string."""
    if not result:
        return "info"
    try:
        data = json.loads(result)
        status = str(data.get("status", "")).lower()
        if status in ("error", "failed", "failure"):
            return "error"
        if status in ("warning", "warn", "skipped"):
            return "warning"
        if status in ("success", "ok", "done", "completed"):
            return "success"
    except (ValueError, TypeError):
        pass
    return "info"


def _infer_message_from_result(result: str | None, fallback: str) -> str:
    if not result:
        return fallback
    try:
        data = json.loads(result)
        # Prefer explicit message field, then description, then reasoning
        for key in ("message", "description", "ai_reasoning", "reasoning_description"):
            if data.get(key):
                return str(data[key])[:300]
    except (ValueError, TypeError):
        pass
    return fallback


def _agent1_log_to_out(log: Agent1Log) -> AgentLogOut:
    msg = _infer_message_from_result(
        log.result,
        f"Image analysis for apartment {log.apartment_id}",
    )
    level = _infer_level_from_result(log.result)
    return AgentLogOut(
        id=log.id,
        timestamp=log.timestamp.isoformat(),
        level=level,
        message=msg,
        phase="search",
    )


def _agent2_log_to_out(log: Agent2Log) -> AgentLogOut:
    msg = _infer_message_from_result(
        log.result,
        f"Match ranking for user {log.user_id}",
    )
    level = _infer_level_from_result(log.result)
    return AgentLogOut(
        id=log.id,
        timestamp=log.timestamp.isoformat(),
        level=level,
        message=msg,
        phase="rank",
    )


def _agent3_log_to_out(log: Agent3Log) -> AgentLogOut:
    msg = _infer_message_from_result(
        log.result,
        f"Outreach for apartment {log.apartment_id or 'unknown'}",
    )
    level = _infer_level_from_result(log.result)
    return AgentLogOut(
        id=log.id,
        timestamp=log.timestamp.isoformat(),
        level=level,
        message=msg,
        phase="negotiate",
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/status", response_model=AgentStatusOut)
async def get_agent_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> AgentStatusOut:
    uid = current_user.id
    running = _is_running(uid)

    # Count matches per status
    matches_result = await db.execute(
        select(Match).where(Match.user_id == uid)
    )
    matches = matches_result.scalars().all()

    matches_found = len(matches)
    negotiations_active = sum(1 for m in matches if m.status == "in_progress")
    # Derive tours count from agent3 logs (same heuristic as the /tours endpoint)
    tours = await list_tours(current_user=current_user, db=db)
    tours_scheduled = len(tours)

    if running:
        if negotiations_active > 0:
            phase = "negotiate"
            action = f"Managing {negotiations_active} active negotiation(s)..."
        elif matches_found > 0:
            phase = "rank"
            action = f"Ranked {matches_found} match(es) for your preferences"
        else:
            phase = "search"
            action = "Scanning new listings..."
    else:
        phase = "idle"
        action = "Agent paused"

    return AgentStatusOut(
        isRunning=running,
        currentAction=action,
        phase=phase,
        matchesFound=matches_found,
        negotiationsActive=negotiations_active,
        toursScheduled=tours_scheduled,
    )


@router.post("/start", response_model=AgentControlResponse)
async def start_agent(
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentControlResponse:
    _set_running(current_user.id, True)
    return AgentControlResponse(isRunning=True, message="Agent started")


@router.post("/stop", response_model=AgentControlResponse)
async def stop_agent(
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentControlResponse:
    _set_running(current_user.id, False)
    return AgentControlResponse(isRunning=False, message="Agent stopped")


@router.get("/logs", response_model=PaginatedLogs)
async def get_agent_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
    phase: Optional[str] = Query(default=None),
    level: Optional[str] = Query(default=None),
    since: Optional[str] = Query(default=None),
) -> PaginatedLogs:
    uid = current_user.id

    # Parse `since` datetime if provided
    since_dt: datetime | None = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
        except ValueError:
            since_dt = None

    # Fetch all three log tables for this user
    a2_result = await db.execute(
        select(Agent2Log).where(Agent2Log.user_id == uid).order_by(Agent2Log.timestamp.desc())
    )
    a3_result = await db.execute(
        select(Agent3Log).where(Agent3Log.user_id == uid).order_by(Agent3Log.timestamp.desc())
    )

    # Agent1 logs are per-apartment; gather from user's matched apartments
    matches_result = await db.execute(select(Match).where(Match.user_id == uid))
    matched_apt_ids = [m.apartment_id for m in matches_result.scalars().all()]

    a1_logs_out: list[AgentLogOut] = []
    if matched_apt_ids:
        a1_result = await db.execute(
            select(Agent1Log)
            .where(Agent1Log.apartment_id.in_(matched_apt_ids))
            .order_by(Agent1Log.timestamp.desc())
        )
        a1_logs_out = [_agent1_log_to_out(l) for l in a1_result.scalars().all()]

    a2_logs_out = [_agent2_log_to_out(l) for l in a2_result.scalars().all()]
    a3_logs_out = [_agent3_log_to_out(l) for l in a3_result.scalars().all()]

    all_logs: list[AgentLogOut] = a1_logs_out + a2_logs_out + a3_logs_out
    # Sort by timestamp descending
    all_logs.sort(key=lambda x: x.timestamp, reverse=True)

    # Apply filters
    if since_dt:
        all_logs = [l for l in all_logs if datetime.fromisoformat(l.timestamp) >= since_dt]
    if phase:
        all_logs = [l for l in all_logs if l.phase == phase]
    if level:
        all_logs = [l for l in all_logs if l.level == level]

    total = len(all_logs)
    offset = (page - 1) * pageSize
    page_items = all_logs[offset : offset + pageSize]

    return PaginatedLogs(items=page_items, total=total, page=page, pageSize=pageSize)
