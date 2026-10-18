from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SmoothiePlan(Base):
    __tablename__ = "smoothie_plans"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    profile_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    smoothie_name: Mapped[str] = mapped_column(String(255))
    goal: Mapped[str] = mapped_column(String(50))
    calories: Mapped[int | None] = mapped_column(Integer)
    ingredients: Mapped[list[dict]] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text)
    safety_warning: Mapped[str | None] = mapped_column(Text)
    raw_response: Mapped[dict | None] = mapped_column(JSON)
    dataset_version_code: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User | None"] = relationship(back_populates="smoothie_plans")
    profile: Mapped["UserProfile"] = relationship(back_populates="smoothie_plans")
