import uuid
from datetime import datetime

from sqlalchemy import UniqueConstraint, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Match(Base):
    __tablename__ = "matches"

    __table_args__ = (
        UniqueConstraint("user_id", "apartment_id", name="uq_match_user_apartment"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    apartment_id: Mapped[str] = mapped_column(String, ForeignKey("apartments.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String, default="not_started")
    commute_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_reasoning: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="matches")
    apartment: Mapped["Apartment"] = relationship("Apartment", back_populates="matches")
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="match", cascade="all, delete-orphan"
    )


