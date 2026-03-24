import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.match import Match
from app.models.user import User
from app.schemas.match import MatchCreate, MatchRead, MatchUpdate
from app.schemas.matching import RunFilterResponse, SwipeRequest, SwipeResponse
from app.services.matching import run_objective_filter, process_swipe

router = APIRouter(tags=["matches"])


@router.get("/matches", response_model=List[MatchRead])
async def list_matches(skip: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=500), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Match).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/matches/{match_id}", response_model=MatchRead)
async def get_match(match_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Match, match_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Match not found")
    return obj


@router.post("/matches", response_model=MatchRead, status_code=201)
async def create_match(body: MatchCreate, db: AsyncSession = Depends(get_db)):
    obj = Match(id=str(uuid.uuid4()), **body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/matches/{match_id}", response_model=MatchRead)
async def update_match(match_id: str, body: MatchUpdate, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Match, match_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Match not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/matches/{match_id}", status_code=204)
async def delete_match(match_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Match, match_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Match not found")
    await db.delete(obj)
    await db.commit()


@router.get("/users/{user_id}/matches", response_model=List[MatchRead])
async def get_user_matches(user_id: str, skip: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=500), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Match).where(Match.user_id == user_id).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.post("/users/{user_id}/run-filter", response_model=RunFilterResponse, tags=["matches"])
async def run_filter(user_id: str, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        count = await run_objective_filter(user_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RunFilterResponse(matches_created=count)


@router.post("/users/{user_id}/swipe", response_model=SwipeResponse, tags=["matches"])
async def swipe(user_id: str, body: SwipeRequest, db: AsyncSession = Depends(get_db)):
    try:
        count = await process_swipe(user_id, body.apartment_id, body.action, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SwipeResponse(matches_rescored=count)


@router.get("/users/{user_id}/matches/relevant", response_model=List[MatchRead], tags=["matches"])
async def get_relevant_matches(
    user_id: str,
    min_score: float = 0.8,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Match)
        .where(
            Match.user_id == user_id,
            Match.match_score >= min_score,
        )
        .order_by(Match.match_score.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
