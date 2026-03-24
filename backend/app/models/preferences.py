import uuid
from datetime import date

from sqlalchemy import String, Integer, Boolean, Float, Date, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ObjectivePreferences(Base):
    __tablename__ = "objective_preferences"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bedroom_type: Mapped[str] = mapped_column(String, nullable=False)
    selected_areas: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    min_budget: Mapped[int] = mapped_column(Integer, nullable=False)
    max_budget: Mapped[int] = mapped_column(Integer, nullable=False)
    move_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    move_out_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    lease_length_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    laundry: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    parking: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    pets: Mapped[bool] = mapped_column(Boolean, default=False)
    work_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    work_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    commute_method: Mapped[str | None] = mapped_column(String, nullable=True)
    max_commute_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="objective_preferences")


class SubjectivePreferences(Base):
    __tablename__ = "subjective_preferences"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    priority_focus: Mapped[str | None] = mapped_column(String, nullable=True)
    image_labels: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    neighborhood_labels: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    user: Mapped["User"] = relationship("User", back_populates="subjective_preferences")


class NegotiationPreferences(Base):
    __tablename__ = "negotiation_preferences"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    enable_automation: Mapped[bool] = mapped_column(Boolean, default=False)
    negotiable_items: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    goals: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    max_rent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_deposit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latest_move_in_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    min_lease_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_lease_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    negotiation_style: Mapped[str | None] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="negotiation_preferences")


class NotificationPreferences(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    enable_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_scheduling: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_types: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    frequency: Mapped[str] = mapped_column(String, default="realtime")

    user: Mapped["User"] = relationship("User", back_populates="notification_preferences")
