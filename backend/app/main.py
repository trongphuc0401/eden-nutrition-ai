from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import SessionLocal
from app.models.nutrition_knowledge import NutritionKnowledge
from app.schemas.api_schema import (
    CapabilityStatus,
    GenerateAndEvaluateResponse,
    KnowledgeSearchResponse,
    ProfileAnalysisResponse,
    SystemStatusResponse,
    SmoothieEvaluationRequest,
    SmoothieEvaluationResponse,
    SmoothieGenerationResponse,
)
from app.schemas.profile_schema import ProfileInput
from app.schemas.smoothie_schema import SmoothiePlanResponse
from app.services.evaluation_service import EvaluationService
from app.services.nutrition_service import (
    GuardrailViolationError,
    NutritionService,
    PersistenceError,
    ResearchScopeError,
    build_profile_analysis,
    local_seed_item_count,
)
from app.services.research_rule_service import ResearchRuleService


app = FastAPI(title=settings.app_name)
nutrition_service = NutritionService()
evaluation_service = EvaluationService()
research_rule_service = ResearchRuleService()


def _database_status() -> tuple[bool, str]:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return True, "Database connection succeeded."
    except SQLAlchemyError as error:
        return False, f"Database connection failed: {error.__class__.__name__}."


def _vector_embedding_item_count() -> int:
    try:
        with SessionLocal() as db:
            return int(
                db.scalar(
                    select(func.count()).select_from(NutritionKnowledge).where(
                        NutritionKnowledge.embedding.is_not(None)
                    )
                )
                or 0
            )
    except SQLAlchemyError:
        return 0


def _readiness_label(capabilities: list[CapabilityStatus]) -> str:
    if all(item.ready for item in capabilities):
        return "ready"
    if any(item.ready for item in capabilities):
        return "partial"
    return "not_ready"


@app.get("/health")
def health_check() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "openai_configured": bool(settings.openai_api_key),
    }


@app.get("/system-status", response_model=SystemStatusResponse)
def system_status() -> SystemStatusResponse:
    rule_sources = research_rule_service.active_rule_sources()
    threshold_rules = research_rule_service.load_threshold_rules()
    safety_rules = research_rule_service.load_safety_rules()
    fallback_count = local_seed_item_count()
    database_reachable, database_reason = _database_status()
    vector_embedding_count = _vector_embedding_item_count() if database_reachable else 0
    openai_configured = bool(settings.openai_api_key)
    vector_search_available = openai_configured and database_reachable and vector_embedding_count > 0
    persistence_available = database_reachable

    capabilities = [
        CapabilityStatus(
            name="openai_generation",
            status="ready" if openai_configured else "missing_api_key",
            ready=openai_configured,
            reason="OPENAI_API_KEY is configured." if openai_configured else "OPENAI_API_KEY is not configured.",
            next_action=None if openai_configured else "Set OPENAI_API_KEY in backend/.env for live model calls.",
        ),
        CapabilityStatus(
            name="database_persistence",
            status="ready" if database_reachable else "unavailable",
            ready=database_reachable,
            reason=database_reason,
            next_action=None if database_reachable else "Start PostgreSQL and verify DATABASE_URL.",
        ),
        CapabilityStatus(
            name="vector_search",
            status="ready" if vector_search_available else "fallback_only",
            ready=vector_search_available,
            reason=(
                f"{vector_embedding_count} embedded knowledge rows available."
                if vector_search_available
                else "Vector search needs OpenAI API key, reachable database, and embedded knowledge rows."
            ),
            next_action=None
            if vector_search_available
            else "Run fruit import with embeddings after PostgreSQL and OPENAI_API_KEY are available.",
        ),
        CapabilityStatus(
            name="local_knowledge_fallback",
            status="ready" if fallback_count > 0 else "empty",
            ready=fallback_count > 0,
            reason=f"{fallback_count} local seed knowledge rows available.",
            next_action=None if fallback_count > 0 else "Rebuild or restore backend/data/vietnamese_fruits_seed.json.",
        ),
        CapabilityStatus(
            name="research_rules",
            status="ready" if threshold_rules and safety_rules else "incomplete",
            ready=bool(threshold_rules and safety_rules),
            reason=f"{len(threshold_rules)} threshold rules and {len(safety_rules)} safety rules available.",
            next_action=None if threshold_rules and safety_rules else "Import or restore research rule seed files.",
        ),
        CapabilityStatus(
            name="guardrail_and_evaluation",
            status="ready",
            ready=True,
            reason="Profile analysis, blocked ingredient checks, threshold checks, and safety checks are wired.",
            next_action=None,
        ),
    ]

    return SystemStatusResponse(
        app_name=settings.app_name,
        app_env=settings.app_env,
        readiness_status=_readiness_label(capabilities),
        openai_configured=openai_configured,
        database_reachable=database_reachable,
        vector_search_available=vector_search_available,
        persistence_available=persistence_available,
        knowledge_fallback_item_count=fallback_count,
        vector_embedding_item_count=vector_embedding_count,
        threshold_rule_count=len(threshold_rules),
        safety_rule_count=len(safety_rules),
        active_threshold_rule_source=rule_sources["threshold_source"],
        active_safety_rule_source=rule_sources["safety_source"],
        capabilities=capabilities,
    )


@app.post("/profiles/analyze", response_model=ProfileAnalysisResponse)
def analyze_profile(profile: ProfileInput) -> ProfileAnalysisResponse:
    return build_profile_analysis(profile)


@app.post("/knowledge/search-preview", response_model=KnowledgeSearchResponse)
def knowledge_search_preview(
    profile: ProfileInput,
    limit: int = Query(default=5, ge=1, le=10),
) -> KnowledgeSearchResponse:
    return nutrition_service.preview_knowledge(profile=profile, limit=limit)


@app.post("/smoothies/generate", response_model=SmoothieGenerationResponse)
def generate_smoothie(
    profile: ProfileInput,
    use_rag: bool = Query(default=True),
    knowledge_limit: int = Query(default=5, ge=1, le=10),
    persist_result: bool = Query(default=False),
) -> SmoothieGenerationResponse:
    try:
        return nutrition_service.generate_smoothie(
            profile=profile,
            use_rag=use_rag,
            knowledge_limit=knowledge_limit,
            persist_result=persist_result,
        )
    except GuardrailViolationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ResearchScopeError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except PersistenceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/smoothies/evaluate", response_model=SmoothieEvaluationResponse)
def evaluate_smoothie(request: SmoothieEvaluationRequest) -> SmoothieEvaluationResponse:
    return SmoothieEvaluationResponse(
        **evaluation_service.evaluate_plan(profile=request.profile, plan=request.plan)
    )


@app.post("/smoothies/generate-and-evaluate", response_model=GenerateAndEvaluateResponse)
def generate_and_evaluate_smoothie(
    profile: ProfileInput,
    use_rag: bool = Query(default=True),
    knowledge_limit: int = Query(default=5, ge=1, le=10),
    persist_result: bool = Query(default=False),
) -> GenerateAndEvaluateResponse:
    try:
        generation = nutrition_service.generate_smoothie(
            profile=profile,
            use_rag=use_rag,
            knowledge_limit=knowledge_limit,
            persist_result=persist_result,
        )
    except GuardrailViolationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ResearchScopeError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except PersistenceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    evaluation = SmoothieEvaluationResponse(
        **evaluation_service.evaluate_plan(profile=profile, plan=generation.plan)
    )
    return GenerateAndEvaluateResponse(
        generation=generation,
        evaluation=evaluation,
    )


@app.get("/research-rules/preview")
def preview_research_rules() -> dict[str, list[dict]]:
    return research_rule_service.preview_rules()
