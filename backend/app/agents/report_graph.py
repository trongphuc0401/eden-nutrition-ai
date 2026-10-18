from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from app.agents.report_state import NutritionReportState
from app.schemas.report_schema import NutritionReportDocument
from app.services.pdf_report_service import render_report_pdf
from app.services.report_calculation_service import calculate_nutrition
from app.services.report_data_service import resolve_ingredients, slugify
from app.services.recipe_generation_service import blocked_ingredient_ids, generate_recipe_proposal


REPO_ROOT = Path(__file__).resolve().parents[3]


def _profile_terms(profile: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    terms: list[str] = []
    for key in keys:
        value = profile.get(key)
        if isinstance(value, str):
            terms.extend(part.strip() for part in value.replace(";", ",").split(",") if part.strip())
        elif isinstance(value, list):
            terms.extend(str(part).strip() for part in value if str(part).strip())
    return terms


def validate_request(state: NutritionReportState) -> dict[str, Any]:
    request = state.get("request", {})
    ingredient_ids = request.get("ingredientIds") or request.get("ingredient_ids") or []
    profile = request.get("profile") or {}
    errors: list[str] = []
    warnings: list[str] = []
    if not ingredient_ids:
        errors.append("Cần chọn ít nhất một nguyên liệu.")
    if len(ingredient_ids) > 8:
        errors.append("Report chỉ hỗ trợ tối đa 8 nguyên liệu.")
    resolved, unknown = resolve_ingredients(list(dict.fromkeys(ingredient_ids))[:8])
    blocked_ids = blocked_ingredient_ids(profile)
    conflicts = [item["name"] for item in resolved if item["ingredient_id"] in blocked_ids]
    if conflicts:
        errors.append("Xung đột dị ứng: " + ", ".join(sorted(set(conflicts))))
    if unknown:
        warnings.append("Chưa có dữ liệu dinh dưỡng cho: " + ", ".join(unknown))
    return {
        "profile": profile,
        "selected_ingredients": resolved,
        "errors": errors,
        "warnings": warnings,
        "retry_count": 0,
        "decision": "reject" if errors else "review" if unknown else "pass",
        "execution_metadata": {
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "locale": request.get("locale", "vi-VN"),
        },
    }


def analyze_profile(state: NutritionReportState) -> dict[str, Any]:
    profile = state.get("profile", {})
    goals = _profile_terms(profile, ("goals", "goal", "nutritionGoal", "nutrition_goal"))
    goals = ["Quản lý cân nặng" if goal == "overweight_obesity_weight_management" else goal for goal in goals]
    medical_notes = str(profile.get("medical_notes") or profile.get("medicalNotes") or "").strip()
    restriction_status = str(profile.get("health_restriction_status") or "unknown")
    conditions = [medical_notes] if medical_notes else []
    high_risk_terms = ("suy thận", "lọc máu", "mang thai nguy cơ cao", "dị ứng phản vệ")
    unsupported = [term for term in conditions if any(flag in term.lower() for flag in high_risk_terms)]
    errors = list(state.get("errors", []))
    height_m = float(profile.get("height_cm") or profile.get("heightCm") or 0) / 100
    weight_kg = float(profile.get("weight_kg") or profile.get("weightKg") or 0)
    bmi = round(weight_kg / (height_m * height_m), 1) if height_m > 0 else 0
    if bmi < 25:
        errors.append("Phiên bản thử nghiệm chỉ hỗ trợ người trưởng thành có BMI từ 25 trở lên.")
    if unsupported:
        errors.append("Hồ sơ cần chuyên gia y tế đánh giá trực tiếp: " + ", ".join(unsupported))
    needs_review = bool(medical_notes) or restriction_status in {"yes", "unknown"}
    return {
        "profile_analysis": {
            "goal": ", ".join(goals) or "Bổ sung dinh dưỡng cân bằng",
            "conditions": conditions,
            "bmi": bmi,
            "health_restriction_status": restriction_status,
            "requires_clinical_review": bool(unsupported),
        },
        "errors": errors,
        "decision": "reject" if errors else "review" if needs_review else state.get("decision", "pass"),
    }


def retrieve_ingredient_data(state: NutritionReportState) -> dict[str, Any]:
    return {"ingredient_data": state.get("selected_ingredients", [])}


def generate_recipe(state: NutritionReportState) -> dict[str, Any]:
    request = state["request"]
    analysis = state.get("profile_analysis", {})
    goal = str(analysis.get("goal") or "Bổ sung dinh dưỡng cân bằng")
    proposal, metadata = generate_recipe_proposal(
        profile=state.get("profile", {}),
        selected=state.get("ingredient_data", []),
        servings=int(request.get("servings", 1)),
        user_prompt=str(request.get("prompt") or ""),
        allow_suggestions=bool(request.get("allowSuggestions", True)),
        rejected_ids=list(request.get("rejectedIngredientIds") or []),
    )
    proposal_payload = proposal.model_dump(mode="json")
    if proposal.unable_reason:
        return {
            "recipe_proposal": proposal_payload,
            "errors": [*state.get("errors", []), proposal.unable_reason],
            "decision": "reject",
            "confirmation_required": False,
        }
    suggested_ids = set(proposal.suggested_ingredient_ids)
    confirmation_required = bool(suggested_ids)
    resolved, unknown = resolve_ingredients([item.ingredient_id for item in proposal.ingredients])
    resolved_by_id = {item["ingredient_id"]: item for item in resolved}
    ingredients = [
        {
            **resolved_by_id[item.ingredient_id],
            "amount": item.amount,
            "unit": item.unit,
            "purpose": item.reason,
            "ai_suggested": item.ingredient_id in suggested_ids,
        }
        for item in proposal.ingredients
    ]
    recipe = {
        "title": proposal.title,
        "goal": goal,
        "servings": int(request.get("servings", 1)),
        "ingredients": ingredients,
        "steps": proposal.steps,
        "usage": "Dùng như bữa phụ. Không tự thay thế bữa chính hoặc phác đồ điều trị.",
        "substitutions": "Mọi thay đổi nguyên liệu cần được xác nhận và tính lại report.",
        "ai_summary": proposal.rationale,
        "prep_minutes": proposal.prep_minutes,
    }
    execution_metadata = dict(state.get("execution_metadata", {}))
    execution_metadata.update(
        {
            "ai_provider": proposal.ai_provider,
            "ai_model": proposal.ai_model,
            "prompt_version": proposal.prompt_version,
            "repair_count": proposal.repair_count,
            "model_usage": metadata.get("usage", {}),
        }
    )
    warnings = list(state.get("warnings", []))
    if unknown:
        warnings.append("Đề xuất chứa nguyên liệu thiếu dữ liệu: " + ", ".join(unknown))
    return {
        "recipe_proposal": proposal_payload,
        "recipe_draft": recipe,
        "confirmation_required": confirmation_required,
        "execution_metadata": execution_metadata,
        "warnings": warnings,
    }
def calculate_report_nutrition(state: NutritionReportState) -> dict[str, Any]:
    return {"nutrition_calculation": calculate_nutrition(state["recipe_draft"])}


def safety_and_quality_gate(state: NutritionReportState) -> dict[str, Any]:
    calculation = state["nutrition_calculation"]
    decision = "review" if state.get("decision") == "review" or calculation["decision"] == "review" else calculation["decision"]
    warnings = list(state.get("warnings", []))
    unverified_sources = [
        item["name"] for item in state.get("recipe_draft", {}).get("ingredients", [])
        if not item.get("source_verified")
    ]
    if unverified_sources:
        decision = "review"
        warnings.append("Nguồn dữ liệu chưa được xác minh cho: " + ", ".join(unverified_sources))
    if calculation["missing_data"]:
        warnings.extend(calculation["missing_data"])
    if decision == "review":
        warnings.append("Một hoặc nhiều ngưỡng demo chưa đạt; report cần được xem xét trước khi sử dụng.")
    return {
        "evaluation_result": {
            "decision": decision,
            "thresholds": calculation["thresholds"],
            "data_coverage": calculation["coverage"],
        },
        "decision": decision,
        "warnings": list(dict.fromkeys(warnings)),
    }


def _compose(state: NutritionReportState, force_warning: bool) -> dict[str, Any]:
    recipe = state["recipe_draft"]
    calculation = state["nutrition_calculation"]
    warnings = state.get("warnings", [])
    decision = "review" if force_warning else state.get("decision", "pass")
    ingredients = [
        {
            "ingredient_id": item["ingredient_id"], "name": item["name"], "amount": item["amount"],
            "unit": item["unit"], "source": item.get("source"), "source_label": item.get("source_label"),
            "source_region": item.get("source_region", "unknown"), "source_per_100g": item.get("per_100g", {}),
        }
        for item in recipe["ingredients"][:8]
    ]
    unique_sources = []
    for item in ingredients:
        source = item.get("source_label") or "Chưa có nguồn"
        if item.get("source"):
            source = f"{source}: {item['source']}"
        if source not in unique_sources:
            unique_sources.append(source)
    summary = (
        (recipe.get("ai_summary") + " " if recipe.get("ai_summary") else "")
        + "Công thức được tính theo mỗi khẩu phần từ định lượng và dữ liệu dinh dưỡng trên 100 g. "
        f"Độ phủ dữ liệu hiện tại là {calculation['coverage'] * 100:.0f}%. "
        + ("Có điểm cần xem lại trong phần ngưỡng và dữ liệu thiếu." if decision == "review" else "Các ngưỡng demo hiện tại đều đạt.")
    )
    document = NutritionReportDocument(
        report_id=state["report_id"],
        locale=state["request"].get("locale", "vi-VN"),
        title=recipe["title"],
        goal=recipe["goal"],
        servings=recipe["servings"],
        ingredients=ingredients,
        preparation_steps=recipe["steps"][:6],
        usage=recipe["usage"],
        substitutions=recipe["substitutions"],
        warning=" ".join(warnings) if warnings else "Không phát hiện xung đột dị ứng từ hồ sơ đã nhập.",
        summary=summary[:650],
        totals=calculation["totals"],
        recipe_totals=calculation["recipe_totals"],
        ingredient_nutrition=calculation["ingredients"][:8],
        thresholds=calculation["thresholds"][:8],
        sources=unique_sources[:6],
        assumptions=calculation["assumptions"][:5],
        missing_data=calculation["missing_data"][:5],
        data_coverage=calculation["coverage"],
        decision=decision,
        ai_metadata={
            key: state.get("execution_metadata", {}).get(key)
            for key in ("ai_provider", "ai_model", "prompt_version", "repair_count")
        },
    )
    return {"report_document": document.model_dump(mode="json"), "decision": decision}


def compose_report(state: NutritionReportState) -> dict[str, Any]:
    return _compose(state, False)


def compose_report_with_warning(state: NutritionReportState) -> dict[str, Any]:
    return _compose(state, True)


def render_pdf(state: NutritionReportState) -> dict[str, Any]:
    document = NutritionReportDocument.model_validate(state["report_document"])
    output_path = REPO_ROOT / "output" / "pdf" / f"{document.report_id}.pdf"
    artifact = render_report_pdf(document, output_path)
    return {"pdf_metadata": artifact.model_dump()}


def finalize(state: NutritionReportState) -> dict[str, Any]:
    metadata = dict(state.get("execution_metadata", {}))
    metadata["completed_at"] = datetime.now(timezone.utc).isoformat()
    return {"execution_metadata": metadata}


def finalize_error(state: NutritionReportState) -> dict[str, Any]:
    metadata = dict(state.get("execution_metadata", {}))
    metadata["rejected_at"] = datetime.now(timezone.utc).isoformat()
    return {"decision": "reject", "pdf_metadata": {}, "execution_metadata": metadata}


def finalize_waiting(state: NutritionReportState) -> dict[str, Any]:
    metadata = dict(state.get("execution_metadata", {}))
    metadata["awaiting_confirmation_at"] = datetime.now(timezone.utc).isoformat()
    return {"confirmation_required": True, "pdf_metadata": {}, "execution_metadata": metadata}


def _continue_or_reject(state: NutritionReportState) -> str:
    return "reject" if state.get("decision") == "reject" else "continue"


def _decision(state: NutritionReportState) -> str:
    return state.get("decision", "review")


def _after_recipe(state: NutritionReportState) -> str:
    if state.get("decision") == "reject":
        return "reject"
    if state.get("confirmation_required"):
        return "confirm"
    return "continue"


builder = StateGraph(NutritionReportState)
builder.add_node("validate_request", validate_request)
builder.add_node("analyze_profile", analyze_profile)
builder.add_node("retrieve_ingredient_data", retrieve_ingredient_data, retry_policy=RetryPolicy(max_attempts=3))
builder.add_node("generate_recipe", generate_recipe, retry_policy=RetryPolicy(max_attempts=2))
builder.add_node("calculate_nutrition", calculate_report_nutrition)
builder.add_node("safety_and_quality_gate", safety_and_quality_gate)
builder.add_node("compose_report", compose_report)
builder.add_node("compose_report_with_warning", compose_report_with_warning)
builder.add_node("render_pdf", render_pdf)
builder.add_node("finalize", finalize)
builder.add_node("finalize_error", finalize_error)
builder.add_node("finalize_waiting", finalize_waiting)

builder.add_edge(START, "validate_request")
builder.add_conditional_edges("validate_request", _continue_or_reject, {"continue": "analyze_profile", "reject": "finalize_error"})
builder.add_conditional_edges("analyze_profile", _continue_or_reject, {"continue": "retrieve_ingredient_data", "reject": "finalize_error"})
builder.add_edge("retrieve_ingredient_data", "generate_recipe")
builder.add_conditional_edges(
    "generate_recipe",
    _after_recipe,
    {"continue": "calculate_nutrition", "confirm": "finalize_waiting", "reject": "finalize_error"},
)
builder.add_edge("calculate_nutrition", "safety_and_quality_gate")
builder.add_conditional_edges(
    "safety_and_quality_gate", _decision,
    {"pass": "compose_report", "review": "compose_report_with_warning", "reject": "finalize_error"},
)
builder.add_edge("compose_report", "render_pdf")
builder.add_edge("compose_report_with_warning", "render_pdf")
builder.add_edge("render_pdf", "finalize")
builder.add_edge("finalize", END)
builder.add_edge("finalize_error", END)
builder.add_edge("finalize_waiting", END)

report_graph = builder.compile()
