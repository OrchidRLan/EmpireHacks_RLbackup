import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.apartment import NeighborInfo
from app.schemas.apartment import NeighborInfoCreate, NeighborInfoRead, NeighborInfoUpdate

router = APIRouter(prefix="/neighborhoods", tags=["neighborhoods"])


@router.get("/", response_model=List[NeighborInfoRead])
async def list_neighborhoods(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NeighborInfo).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{neighborhood_id}", response_model=NeighborInfoRead)
async def get_neighborhood(neighborhood_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(NeighborInfo, neighborhood_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Neighborhood not found")
    return obj


@router.post("/", response_model=NeighborInfoRead, status_code=201)
async def create_neighborhood(body: NeighborInfoCreate, db: AsyncSession = Depends(get_db)):
    obj = NeighborInfo(id=str(uuid.uuid4()), **body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/{neighborhood_id}", response_model=NeighborInfoRead)
async def update_neighborhood(neighborhood_id: str, body: NeighborInfoUpdate, db: AsyncSession = Depends(get_db)):
    obj = await db.get(NeighborInfo, neighborhood_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Neighborhood not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{neighborhood_id}", status_code=204)
async def delete_neighborhood(neighborhood_id: str, db: AsyncSession = Depends(get_db)):
    obj = await db.get(NeighborInfo, neighborhood_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Neighborhood not found")
    await db.delete(obj)
    await db.commit()
