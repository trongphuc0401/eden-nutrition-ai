from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ClinicalSafetyRule(Base):
    __tablename__ = "clinical_safety_rules"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rule_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    condition_key: Mapped[str] = mapped_column(String(100), index=True)
    risk_type: Mapped[str] = mapped_column(String(50), index=True)
    ingredient_or_nutrient: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(50))
    threshold_value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(50))
    warning_message: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    # Canonical workbook fields. The original text fields remain for existing callers.
    condition_code: Mapped[str | None] = mapped_column(String(80), index=True)
    target_type: Mapped[str | None] = mapped_column(String(30))
    ingredient_id: Mapped[UUID | None] = mapped_column()
    nutrient_code: Mapped[str | None] = mapped_column(String(80))
    target_text: Mapped[str | None] = mapped_column(Text)
    avoid_or_limit: Mapped[str | None] = mapped_column(String(20))
    warning_message_vi: Mapped[str | None] = mapped_column(Text)
    recommended_action: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    entry_notes: Mapped[str | None] = mapped_column(Text)
    import_batch_id: Mapped[UUID | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
