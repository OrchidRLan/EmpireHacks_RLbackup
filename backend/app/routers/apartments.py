import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.apartment import Apartment
from app.schemas.apartment import ApartmentCreate, ApartmentRead, ApartmentUpdate

router = APIRouter(prefix="/apartments", tags=["apartments"])


@router.get("/", response_model=List[ApartmentRead])
async def list_apartments(
    skip: int = 0,
    limit: int = 100,
    bedroom_type: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    neighbor_id: Optional[str] = None,
    pets: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Apartment)
    if bedroom_type is not None:
        stmt = stmt.where(Apartment.bedroom_type == bedroom_type)
    if min_price is not None:
        stmt = stmt.where(Apartment.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Apartment.price <= max_price)
    if neighbor_id is not None:
        stmt = stmt.where(Apartment.neighbor_id == neighbor_id)
    if pets is not None:
        stmt = stmt.where(Apartment.pets == pets)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{apartment_id}", response_model=ApartmentRead)
async def get_apartment(apartment_id: str, db: AsyncSession = Depends(get_db)):
    apt = await db.get(Apartment, apartment_id)
    if not apt:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return apt


@router.post("/", response_model=ApartmentRead, status_code=201)
async def create_apartment(body: ApartmentCreate, db: AsyncSession = Depends(get_db)):
    apt = Apartment(id=str(uuid.uuid4()), **body.model_dump())
    db.add(apt)
    await db.commit()
    await db.refresh(apt)
    return apt


@router.patch("/{apartment_id}", response_model=ApartmentRead)
async def update_apartment(apartment_id: str, body: ApartmentUpdate, db: AsyncSession = Depends(get_db)):
    apt = await db.get(Apartment, apartment_id)
    if not apt:
        raise HTTPException(status_code=404, detail="Apartment not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(apt, field, value)
    await db.commit()
    await db.refresh(apt)
    return apt


@router.delete("/{apartment_id}", status_code=204)
async def delete_apartment(apartment_id: str, db: AsyncSession = Depends(get_db)):
    apt = await db.get(Apartment, apartment_id)
    if not apt:
        raise HTTPException(status_code=404, detail="Apartment not found")
    await db.delete(apt)
    await db.commit()
