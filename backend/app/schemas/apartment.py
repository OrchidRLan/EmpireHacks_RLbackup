from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# --- NeighborInfo ---

class NeighborInfoBase(BaseModel):
    name: str
    description: str


class NeighborInfoCreate(NeighborInfoBase):
    pass


class NeighborInfoRead(NeighborInfoBase):
    model_config = ConfigDict(from_attributes=True)

    id: str


class NeighborInfoUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


# --- Apartment ---

class ApartmentBase(BaseModel):
    name: str
    bedroom_type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price: int
    neighbor_id: Optional[str] = None
    move_in_date: Optional[date] = None
    lease_length_months: Optional[int] = None
    laundry: List[str] = []
    parking: List[str] = []
    pets: bool = False
    host_phone: Optional[str] = None
    host_email: Optional[str] = None
    images: List[str] = []
    image_labels: List[str] = []


class ApartmentCreate(ApartmentBase):
    pass


class ApartmentRead(ApartmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class ApartmentUpdate(BaseModel):
    name: Optional[str] = None
    bedroom_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price: Optional[int] = None
    neighbor_id: Optional[str] = None
    move_in_date: Optional[date] = None
    lease_length_months: Optional[int] = None
    laundry: Optional[List[str]] = None
    parking: Optional[List[str]] = None
    pets: Optional[bool] = None
    host_phone: Optional[str] = None
    host_email: Optional[str] = None
    images: Optional[List[str]] = None
    image_labels: Optional[List[str]] = None
