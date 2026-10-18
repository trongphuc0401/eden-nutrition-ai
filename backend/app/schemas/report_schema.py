from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.profile_schema import ProfileInput


ReportDecision = Literal["pass", "review", "reject"]
ReportStatus = Literal[
    "queued", "running", "awaiting_confirmation", "review", "rejected", "failed", "cancelled", "completed"
]


class RecipeIngredientProposal(BaseModel):
    ingredient_id: str = Field(min_length=1, max_length=120)
    amount: float = Field(gt=0, le=1000)
    unit: Literal["g", "ml"]
    reason: str = Field(min_length=1, max_length=220)


class RecipeProposal(BaseModel):
    version: int = Field(default=1, ge=1)
    title: str = Field(min_length=1, max_length=90)
    ingredients: list[RecipeIngredientProposal] = Field(min_length=1, max_length=8)
    suggested_ingredient_ids: list[str] = Field(default_factory=list, max_length=4)
    omitted_selected: list[dict[str, str]] = Field(default_factory=list, max_length=8)
    steps: list[str] = Field(min_length=3, max_length=6)
    prep_minutes: int = Field(ge=1, le=60)
    rationale: str = Field(min_length=1, max_length=500)
    clarification_needed: list[str] = Field(default_factory=list, max_length=5)
    unable_reason: str | None = Field(default=None, max_length=300)
    ai_provider: str
    ai_model: str
    prompt_version: str
    repair_count: int = Field(default=0, ge=0, le=2)


class ReportConfirmationRequest(BaseModel):
    proposal_version: int = Field(ge=1)
    accepted_ingredient_ids: list[str] = Field(default_factory=list, max_length=4)


class ReportRequest(BaseModel):
    profile: ProfileInput
    ingredientIds: list[str] = Field(min_length=1, max_length=8)
    servings: int = Field(default=1, ge=1, le=4)
    prompt: str = Field(default="", max_length=500)
    locale: str = Field(default="vi-VN", pattern=r"^vi(?:-|$)")
    allowSuggestions: bool = True
    confirmedIngredientIds: list[str] = Field(default_factory=list, max_length=4)
    rejectedIngredientIds: list[str] = Field(default_factory=list, max_length=4)

    model_config = {"populate_by_name": True}


class ReportIngredient(BaseModel):
    ingredient_id: str
    name: str
    amount: float
    unit: Literal["g", "ml"]
    source: str | None = None
    source_label: str | None = None
    source_region: Literal["VN", "international", "internal", "unknown"] = "unknown"
    source_per_100g: dict[str, float | None] = Field(default_factory=dict)


class NutritionTotals(BaseModel):
    calories: float | None = None
    protein: float | None = None
    carbohydrate: float | None = None
    fat: float | None = None
    fiber: float | None = None
    sugar: float | None = None
    sodium: float | None = None


class IngredientNutrition(BaseModel):
    ingredient_id: str
    name: str
    amount_g: float | None = None
    amount: float | None = None
    unit: Literal["g", "ml"] = "g"
    nutrition: NutritionTotals
    source_label: str
    confidence: Literal["high", "medium", "low", "unknown"] = "unknown"


class ThresholdResult(BaseModel):
    nutrient: str
    value: float | None
    unit: str
    minimum: float | None = None
    maximum: float | None = None
    status: Literal["pass", "review", "unknown"]
    message: str


class NutritionReportDocument(BaseModel):
    report_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    locale: str = "vi-VN"
    title: str
    goal: str
    servings: int
    ingredients: list[ReportIngredient] = Field(max_length=8)
    preparation_steps: list[str] = Field(max_length=6)
    usage: str = Field(max_length=380)
    substitutions: str = Field(default="", max_length=300)
    warning: str = Field(default="", max_length=800)
    summary: str = Field(max_length=650)
    totals: NutritionTotals
    recipe_totals: NutritionTotals | None = None
    ingredient_nutrition: list[IngredientNutrition] = Field(max_length=8)
    thresholds: list[ThresholdResult] = Field(default_factory=list, max_length=8)
    sources: list[str] = Field(default_factory=list, max_length=6)
    assumptions: list[str] = Field(default_factory=list, max_length=5)
    missing_data: list[str] = Field(default_factory=list, max_length=5)
    data_coverage: float = Field(ge=0, le=1)
    decision: ReportDecision
    quality_label: str = "Bản thử nghiệm nội bộ – chưa được chuyên gia dinh dưỡng thẩm định."
    ai_metadata: dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = "Thông tin chỉ nhằm mục đích tham khảo, không thay thế chẩn đoán hoặc tư vấn y khoa."


class PdfArtifact(BaseModel):
    path: str
    page_count: int = 2
    sha256: str
    size_bytes: int


class ReportCreatedResponse(BaseModel):
    report_id: str
    thread_id: str
    run_id: str
    status: ReportStatus


class ReportStatusResponse(ReportCreatedResponse):
    current_node: str | None = None
    summary: str | None = None
    warning: str | None = None
    error: str | None = None
    decision: ReportDecision | None = None
    report: NutritionReportDocument | None = None
    pdf_url: str | None = None
    proposal: RecipeProposal | None = None
    confirmation_required: bool = False
    quality_metadata: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class ReportEvent(BaseModel):
    sequence: int
    node: str
    status: str
    message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = Field(default_factory=dict)
