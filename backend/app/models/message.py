import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    match_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("matches.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    match: Mapped["Match | None"] = relationship("Match", back_populates="messages")
    agent3_logs: Mapped[list["Agent3Log"]] = relationship(
        "Agent3Log", back_populates="message"
    )
