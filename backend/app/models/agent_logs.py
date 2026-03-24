import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Agent1Log(Base):
    __tablename__ = "agent1_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    apartment_id: Mapped[str] = mapped_column(
        String, ForeignKey("apartments.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)

    apartment: Mapped["Apartment"] = relationship("Apartment", back_populates="agent1_logs")


class Agent2Log(Base):
    __tablename__ = "agent2_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="agent2_logs")


class Agent3Log(Base):
    __tablename__ = "agent3_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    apartment_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("apartments.id", ondelete="SET NULL"), nullable=True
    )
    message_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="agent3_logs")
    apartment: Mapped["Apartment | None"] = relationship("Apartment", back_populates="agent3_logs")
    message: Mapped["Message | None"] = relationship("Message", back_populates="agent3_logs")
