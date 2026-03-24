import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.message import Message
from app.schemas.message import MessageCreate, MessageRead, MessageUpdate

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("/", response_model=List[MessageRead])
async def list_messages(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Message).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{message_id}", response_model=MessageRead)
async def get_message(message_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Message, message_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Message not found")
    return obj


@router.post("/", response_model=MessageRead, status_code=201)
async def create_message(body: MessageCreate, db: AsyncSession = Depends(get_db)):
    obj = Message(id=str(uuid.uuid4()), **body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/{message_id}", response_model=MessageRead)
async def update_message(message_id: str, body: MessageUpdate, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Message, message_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Message not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{message_id}", status_code=204)
async def delete_message(message_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Message, message_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Message not found")
    await db.delete(obj)
    await db.commit()
