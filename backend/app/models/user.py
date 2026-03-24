import uuid
from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True, unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    objective_preferences: Mapped[list["ObjectivePreferences"]] = relationship(
        "ObjectivePreferences", back_populates="user", cascade="all, delete-orphan"
    )
    subjective_preferences: Mapped[list["SubjectivePreferences"]] = relationship(
        "SubjectivePreferences", back_populates="user", cascade="all, delete-orphan"
    )
    negotiation_preferences: Mapped[list["NegotiationPreferences"]] = relationship(
        "NegotiationPreferences", back_populates="user", cascade="all, delete-orphan"
    )
    notification_preferences: Mapped[list["NotificationPreferences"]] = relationship(
        "NotificationPreferences", back_populates="user", cascade="all, delete-orphan"
    )
    matches: Mapped[list["Match"]] = relationship(
        "Match", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
    agent2_logs: Mapped[list["Agent2Log"]] = relationship(
        "Agent2Log", back_populates="user", cascade="all, delete-orphan"
    )
    agent3_logs: Mapped[list["Agent3Log"]] = relationship(
        "Agent3Log", back_populates="user", cascade="all, delete-orphan"
    )
