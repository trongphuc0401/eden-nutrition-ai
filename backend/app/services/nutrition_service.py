import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.agents.nutrition_graph import run_nutrition_graph
from app.models.profile import UserProfile
from app.models.smoothie_plan import SmoothiePlan
from app.schemas.api_schema import (
    KnowledgePreviewItem,
    KnowledgeSearchResponse,
    ProfileAnalysisResponse,
    SmoothieGenerationResponse,
)
from app.schemas.profile_schema import ProfileInput
from app.services.guardrail_service import (
    expand_blocked_terms,
    filter_knowledge_context,
    normalize_text,
    validate_smoothie_plan,
)
from app.services.vector_service import build_profile_search_query, format_knowledge_context


class GuardrailViolationError(ValueError):
    pass


class PersistenceError(ValueError):
    pass


class ResearchScopeError(ValueError):
    pass


@dataclass
class KnowledgeSelection:
    source: str
    items: list[KnowledgePreviewItem]
    context: list[str]


def build_profile_analysis(profile: ProfileInput) -> ProfileAnalysisResponse:
    bmi = round(profile.weight_kg / ((profile.height_cm / 100) ** 2), 2)
    if bmi >= 30:
        bmi_category = "obesity"
    elif bmi >= 25:
        bmi_category = "overweight"
    else:
        bmi_category = "outside_research_scope"

    constraints: list[str] = []
    constraints.extend(f"allergy:{item}" for item in profile.allergies if item)
    constraints.extend(f"dislike:{item}" for item in profile.disliked_ingredients if item)
    constraints.extend(f"preference:{item}" for item in profile.preferred_food_types if item)
    if profile.medical_notes:
        constraints.append("medical_notes_present")

    return ProfileAnalysisResponse(
        profile=profile,
        bmi=bmi,
        bmi_category=bmi_category,
        research_scope_match=bmi >= 25,
        constraints=constraints,
    )


def _seed_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "vietnamese_fruits_seed.json"


@lru_cache(maxsize=1)
def load_local_seed() -> list[dict[str, Any]]:
    path = _seed_path()
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def local_seed_search(profile: ProfileInput, limit: int = 5) -> KnowledgeSelection:
    seed = load_local_seed()
    blocked = set(expand_blocked_terms([*profile.allergies, *profile.disliked_ingredients]))
    query_tokens = [
        token for token in normalize_text(build_profile_search_query(profile)).split() if len(token) > 3
    ]
    scored_rows: list[tuple[int, dict[str, Any]]] = []

    for item in seed:
        if not item.get("allowed_for_smoothie", False):
            continue

        ingredient_name = normalize_text(str(item.get("ingredient_name") or ""))
        if any(term in ingredient_name for term in blocked):
            continue

        haystack = normalize_text(
            " ".join(
                [
                    str(item.get("title") or ""),
                    str(item.get("ingredient_name") or ""),
                    str(item.get("content") or ""),
                    str(item.get("origin_country") or ""),
                    str(item.get("region") or ""),
                ]
            )
        )
        score = 0
        if "vietnam" in normalize_text(str(item.get("origin_country", ""))):
            score += 5
        if item.get("allowed_for_smoothie"):
            score += 3
        for token in query_tokens:
            if token in haystack:
                score += 1
        scored_rows.append((score, item))

    scored_rows.sort(key=lambda row: row[0], reverse=True)
    selected = [row for _, row in scored_rows[:limit]]
    previews = [
        KnowledgePreviewItem(
            title=item["title"],
            ingredient_name=item.get("ingredient_name"),
            category=item.get("category"),
            source=item.get("source"),
            retrieval_source="local_seed",
        )
        for item in selected
    ]
    context = [item["content"] for item in selected]
    return KnowledgeSelection(source="local_seed", items=previews, context=context)


def local_seed_item_count() -> int:
    return len(load_local_seed())


def vector_db_search(profile: ProfileInput, limit: int = 5) -> KnowledgeSelection:
    from app.database import SessionLocal
    from app.services.vector_service import VectorService

    vector_service = VectorService()
    with SessionLocal() as db:
        knowledge_items = vector_service.search_knowledge(
            db=db,
            profile=profile,
            limit=limit,
            require_vietnamese_fruits=True,
        )

    previews = [
        KnowledgePreviewItem(
            title=item.title,
            ingredient_name=item.ingredient_name,
            category=item.category,
            source=item.source,
            retrieval_source="vector_db",
        )
        for item in knowledge_items
    ]
    context = format_knowledge_context(knowledge_items)
    return KnowledgeSelection(source="vector_db", items=previews, context=context)


class NutritionService:
    def preview_knowledge(
        self,
        profile: ProfileInput,
        limit: int = 5,
    ) -> KnowledgeSearchResponse:
        selection = self._select_knowledge(profile, limit=limit)
        filtered_context = filter_knowledge_context(selection.context, profile)
        filtered_items = selection.items[: len(filtered_context)]
        return KnowledgeSearchResponse(
            query=build_profile_search_query(profile),
            retrieval_source=selection.source,
            item_count=len(filtered_context),
            items=filtered_items,
            context=filtered_context,
        )

    def generate_smoothie(
        self,
        profile: ProfileInput,
        use_rag: bool = True,
        knowledge_limit: int = 5,
        persist_result: bool = False,
    ) -> SmoothieGenerationResponse:
        profile_analysis = build_profile_analysis(profile)
        if not profile_analysis.research_scope_match:
            raise ResearchScopeError(
                "This smoothie generation flow is scoped to Vietnamese adults with overweight or obesity "
                "(BMI >= 25). Use /profiles/analyze to review the profile classification."
            )

        if use_rag:
            selection = self._select_knowledge(profile, limit=knowledge_limit)
        else:
            selection = KnowledgeSelection(source="disabled", items=[], context=[])

        filtered_context = filter_knowledge_context(selection.context, profile)
        filtered_items = selection.items[: len(filtered_context)]
        plan = run_nutrition_graph(profile, knowledge_context=filtered_context)
        violations = validate_smoothie_plan(plan, profile)
        if violations:
            raise GuardrailViolationError(" ".join(violations))

        warnings: list[str] = []
        if not filtered_context:
            warnings.append(
                "No grounded knowledge context was available. The formula may rely on generic nutrition behavior."
            )
        if use_rag and selection.source != "vector_db":
            warnings.append(
                "Vector retrieval was unavailable, so the system used local seed knowledge fallback."
            )

        saved_profile_id: str | None = None
        saved_plan_id: str | None = None
        if persist_result:
            try:
                saved_profile_id, saved_plan_id = self._persist_generation(profile, plan)
            except SQLAlchemyError as error:
                raise PersistenceError(
                    "Failed to persist profile and smoothie plan. Check DATABASE_URL and database availability."
                ) from error

        return SmoothieGenerationResponse(
            plan=plan,
            profile_analysis=profile_analysis,
            retrieval_source=selection.source,
            knowledge_item_count=len(filtered_context),
            knowledge_titles=[item.title for item in filtered_items],
            guardrail_passed=True,
            warnings=warnings,
            saved_profile_id=saved_profile_id,
            saved_plan_id=saved_plan_id,
        )

    def _select_knowledge(
        self,
        profile: ProfileInput,
        limit: int = 5,
    ) -> KnowledgeSelection:
        try:
            return vector_db_search(profile, limit=limit)
        except (ValueError, SQLAlchemyError):
            return local_seed_search(profile, limit=limit)

    def _persist_generation(
        self,
        profile: ProfileInput,
        plan,
    ) -> tuple[str, str]:
        from app.database import SessionLocal

        with SessionLocal() as db:
            profile_row = self._create_profile_row(db, profile)
            plan_row = self._create_plan_row(db, profile_row, plan)
            db.commit()
            db.refresh(profile_row)
            db.refresh(plan_row)
            return str(profile_row.id), str(plan_row.id)

    def _create_profile_row(
        self,
        db: Session,
        profile: ProfileInput,
    ) -> UserProfile:
        profile_row = UserProfile(
            user_id=None,
            age=profile.age,
            gender=profile.gender,
            height_cm=profile.height_cm,
            weight_kg=profile.weight_kg,
            goal=profile.goal,
            allergies=profile.allergies,
            disliked_ingredients=profile.disliked_ingredients,
            medical_notes=profile.medical_notes or None,
        )
        db.add(profile_row)
        db.flush()
        return profile_row

    def _create_plan_row(
        self,
        db: Session,
        profile_row: UserProfile,
        plan,
    ) -> SmoothiePlan:
        plan_row = SmoothiePlan(
            user_id=None,
            profile_id=profile_row.id,
            smoothie_name=plan.smoothie_name,
            goal=plan.goal,
            calories=plan.calories,
            ingredients=[item.model_dump() for item in plan.ingredients],
            reason=plan.reason,
            safety_warning=plan.safety_warning,
            raw_response=plan.model_dump(),
        )
        db.add(plan_row)
        db.flush()
        return plan_row
