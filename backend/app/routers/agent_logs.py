import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent_logs import Agent1Log, Agent2Log, Agent3Log
from app.schemas.agent_logs import (
    Agent1LogCreate,
    Agent1LogRead,
    Agent1LogUpdate,
    Agent2LogCreate,
    Agent2LogRead,
    Agent2LogUpdate,
    Agent3LogCreate,
    Agent3LogRead,
    Agent3LogUpdate,
)

router = APIRouter(prefix="/agent-logs", tags=["agent-logs"])


# --- Agent1 ---

@router.get("/agent1", response_model=List[Agent1LogRead])
async def list_agent1_logs(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent1Log).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/agent1/{log_id}", response_model=Agent1LogRead)
async def get_agent1_log(log_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Agent1Log, log_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Agent1 log not found")
    return obj


@router.post("/agent1", response_model=Agent1LogRead, status_code=201)
async def create_agent1_log(body: Agent1LogCreate, db: AsyncSession = Depends(get_db)):
    obj = Agent1Log(id=str(uuid.uuid4()), **body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/agent1/{log_id}", response_model=Agent1LogRead)
async def update_agent1_log(log_id: str, body: Agent1LogUpdate, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Agent1Log, log_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Agent1 log not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/agent1/{log_id}", status_code=204)
async def delete_agent1_log(log_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Agent1Log, log_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Agent1 log not found")
    await db.delete(obj)
    await db.commit()


# --- Agent2 ---

@router.get("/agent2", response_model=List[Agent2LogRead])
async def list_agent2_logs(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent2Log).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/agent2/{log_id}", response_model=Agent2LogRead)
async def get_agent2_log(log_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Agent2Log, log_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Agent2 log not found")
    return obj


@router.post("/agent2", response_model=Agent2LogRead, status_code=201)
async def create_agent2_log(body: Agent2LogCreate, db: AsyncSession = Depends(get_db)):
    obj = Agent2Log(id=str(uuid.uuid4()), **body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/agent2/{log_id}", response_model=Agent2LogRead)
async def update_agent2_log(log_id: str, body: Agent2LogUpdate, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Agent2Log, log_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Agent2 log not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/agent2/{log_id}", status_code=204)
async def delete_agent2_log(log_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Agent2Log, log_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Agent2 log not found")
    await db.delete(obj)
    await db.commit()


# --- Agent3 ---

@router.get("/agent3", response_model=List[Agent3LogRead])
async def list_agent3_logs(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent3Log).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/agent3/{log_id}", response_model=Agent3LogRead)
async def get_agent3_log(log_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Agent3Log, log_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Agent3 log not found")
    return obj


@router.post("/agent3", response_model=Agent3LogRead, status_code=201)
async def create_agent3_log(body: Agent3LogCreate, db: AsyncSession = Depends(get_db)):
    obj = Agent3Log(id=str(uuid.uuid4()), **body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/agent3/{log_id}", response_model=Agent3LogRead)
async def update_agent3_log(log_id: str, body: Agent3LogUpdate, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Agent3Log, log_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Agent3 log not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/agent3/{log_id}", status_code=204)
async def delete_agent3_log(log_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Agent3Log, log_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Agent3 log not found")
    await db.delete(obj)
    await db.commit()
