import uuid
from datetime import date, datetime

from sqlalchemy import String, Integer, Boolean, Float, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class NeighborInfo(Base):
    __tablename__ = "neighbor_info"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)

    apartments: Mapped[list["Apartment"]] = relationship(
        "Apartment", back_populates="neighborhood", cascade="all, delete-orphan"
    )


class Apartment(Base):
    __tablename__ = "apartments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    streeteasy_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    craigslist_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    bedroom_type: Mapped[str] = mapped_column(String, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    neighbor_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("neighbor_info.id", ondelete="SET NULL"), nullable=True
    )
    move_in_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    lease_length_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    laundry: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    parking: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    pets: Mapped[bool] = mapped_column(Boolean, default=False)
    host_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    host_email: Mapped[str | None] = mapped_column(String, nullable=True)
    amenities: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    images: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    image_labels: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    neighborhood: Mapped["NeighborInfo | None"] = relationship("NeighborInfo", back_populates="apartments")
    matches: Mapped[list["Match"]] = relationship(
        "Match", back_populates="apartment", cascade="all, delete-orphan"
    )
    agent1_logs: Mapped[list["Agent1Log"]] = relationship(
        "Agent1Log", back_populates="apartment", cascade="all, delete-orphan"
    )
    agent3_logs: Mapped[list["Agent3Log"]] = relationship(
        "Agent3Log", back_populates="apartment"
    )
