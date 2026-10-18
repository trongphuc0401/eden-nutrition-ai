from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.profile_schema import ProfileInput
from app.schemas.smoothie_schema import SmoothiePlanResponse


class ProfileAnalysisResponse(BaseModel):
    profile: ProfileInput
    bmi: float = Field(ge=0)
    bmi_category: str
    research_scope_match: bool
    constraints: list[str] = Field(default_factory=list)


class KnowledgePreviewItem(BaseModel):
    title: str
    ingredient_name: str | None = None
    category: str | None = None
    source: str | None = None
    retrieval_source: str


class KnowledgeSearchResponse(BaseModel):
    query: str
    retrieval_source: str
    item_count: int = Field(ge=0)
    items: list[KnowledgePreviewItem] = Field(default_factory=list)
    context: list[str] = Field(default_factory=list)


class SmoothieGenerationResponse(BaseModel):
    plan: SmoothiePlanResponse
    profile_analysis: ProfileAnalysisResponse
    retrieval_source: str
    knowledge_item_count: int = Field(ge=0)
    knowledge_titles: list[str] = Field(default_factory=list)
    guardrail_passed: bool = True
    warnings: list[str] = Field(default_factory=list)
    saved_profile_id: str | None = None
    saved_plan_id: str | None = None


class NutritionEstimateResponse(BaseModel):
    calories: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    fiber_g: float = Field(ge=0)
    total_sugar_g: float = Field(ge=0)


class IngredientNutritionBreakdown(BaseModel):
    ingredient_name: str
    amount: str
    estimated_amount_g: float | None = Field(default=None, ge=0)
    source: str
    matched_reference: str | None = None
    nutrition_per_100g: NutritionEstimateResponse | dict
    estimated_nutrition: NutritionEstimateResponse | dict


class ThresholdCheckResponse(BaseModel):
    threshold_code: str
    metric: str
    value: float | None = None
    min_value: float | None = None
    max_value: float | None = None
    passed: bool
    source: str


class SafetyCheckResponse(BaseModel):
    rule_code: str
    condition_key: str
    triggered: bool
    severity: str
    action: str
    warning_message: str
    source: str


class EvaluationReportResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    decision: Literal["pass", "review", "reject"]
    data_coverage: float = Field(ge=0, le=1)
    known_ingredient_count: int = Field(ge=0)
    total_ingredient_count: int = Field(ge=0)
    failed_threshold_count: int = Field(ge=0)
    triggered_safety_count: int = Field(ge=0)
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class SmoothieEvaluationRequest(BaseModel):
    profile: ProfileInput
    plan: SmoothiePlanResponse


class SmoothieEvaluationResponse(BaseModel):
    estimated_nutrition: NutritionEstimateResponse
    ingredient_breakdown: list[IngredientNutritionBreakdown]
    threshold_checks: list[ThresholdCheckResponse]
    safety_checks: list[SafetyCheckResponse]
    evaluation_report: EvaluationReportResponse
    overall_pass: bool


class GenerateAndEvaluateResponse(BaseModel):
    generation: SmoothieGenerationResponse
    evaluation: SmoothieEvaluationResponse


class DemoProfileResponse(BaseModel):
    profile_id: str
    label: str
    description: str
    expected_result: Literal["generate_ok", "review", "reject_out_of_scope"]
    profile: ProfileInput


class FrontendEndpointResponse(BaseModel):
    method: str
    path: str
    purpose: str


class FrontendBootstrapResponse(BaseModel):
    app_name: str
    research_goal: str
    goal_options: list[str]
    gender_options: list[str]
    sample_profiles: list[DemoProfileResponse]
    endpoints: list[FrontendEndpointResponse]
    recommended_flow: list[str]
    notes: list[str]


class CapabilityStatus(BaseModel):
    name: str
    status: str
    ready: bool
    reason: str
    next_action: str | None = None


class SystemStatusResponse(BaseModel):
    app_name: str
    app_env: str
    readiness_status: str
    llm_provider: str
    llm_configured: bool
    openai_configured: bool
    embedding_provider: str
    embedding_configured: bool
    database_reachable: bool
    vector_search_available: bool
    persistence_available: bool
    knowledge_fallback_item_count: int
    vector_embedding_item_count: int
    threshold_rule_count: int
    safety_rule_count: int
    active_threshold_rule_source: str
    active_safety_rule_source: str
    capabilities: list[CapabilityStatus]
