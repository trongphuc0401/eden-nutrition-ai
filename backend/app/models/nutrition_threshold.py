from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NutritionThreshold(Base):
    __tablename__ = "nutrition_thresholds"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    threshold_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    goal: Mapped[str] = mapped_column(String(100), index=True)
    metric: Mapped[str] = mapped_column(String(100), index=True)
    min_value: Mapped[float | None] = mapped_column(Float)
    max_value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(50))
    meal_context: Mapped[str | None] = mapped_column(String(100))
    pass_rule: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
