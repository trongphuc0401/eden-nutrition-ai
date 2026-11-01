from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from app.agents.report_state import NutritionReportState
from app.config import settings
from app.schemas.report_schema import NutritionReportDocument
from app.services.clinical_rule_service import (
    bmi_in_scope,
    clinically_blocked_ids,
    evaluate_safety_rules,
    match_condition_codes,
)
from app.services.pdf_report_service import render_report_pdf
from app.services.report_calculation_service import calculate_nutrition
from app.services.personalization_service import describe, energy_plan, personal_thresholds, region_scope
from app.services import report_calculation_service
from app.services.report_data_service import reference_metadata, resolve_ingredients, slugify
from app.services.recipe_generation_service import blocked_ingredient_ids, generate_recipe_proposal
from app.services.recipe_optimizer import optimize_amounts
from app.services import report_enrichment as enrichment

VIETNAM_TZ = timezone(timedelta(hours=7))


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
            **reference_metadata(),
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
    height_cm = float(profile.get("height_cm") or profile.get("heightCm") or 0)
    weight_kg = float(profile.get("weight_kg") or profile.get("weightKg") or 0)
    age = float(profile.get("age") or 0) or None
    height_m = height_cm / 100
    bmi = round(weight_kg / (height_m * height_m), 1) if height_m > 0 else 0
    in_scope, classifications = bmi_in_scope(bmi, age, height_cm, weight_kg)
    if not in_scope:
        errors.append("Phiên bản thử nghiệm chỉ hỗ trợ người trưởng thành thừa cân hoặc béo phì.")
    if unsupported:
        errors.append("Hồ sơ cần chuyên gia y tế đánh giá trực tiếp: " + ", ".join(unsupported))
    condition_codes = match_condition_codes(_profile_terms(profile, ("allergies",)), medical_notes)
    # Fail before generation when a user-selected ingredient is blocked for one of the matched conditions.
    safety = evaluate_safety_rules(condition_codes, state.get("selected_ingredients", []), block_only=True)
    errors.extend(error for error in safety["errors"] if error not in errors)
    needs_review = bool(medical_notes) or restriction_status in {"yes", "unknown"}
    return {
        "profile_analysis": {
            "goal": ", ".join(goals) or "Bổ sung dinh dưỡng cân bằng",
            "conditions": conditions,
            "condition_codes": condition_codes,
            "energy_plan": energy_plan(profile),
            "region_scope": region_scope(profile.get("hometown")),
            "bmi": bmi,
            "classifications": classifications,
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
        rejected_ids=[
            *(request.get("rejectedIngredientIds") or []),
            *sorted(clinically_blocked_ids(analysis.get("condition_codes", []))),
        ],
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
def _calculate(state: NutritionReportState, recipe: dict[str, Any]) -> dict[str, Any]:
    """Pass/fail stays on the research thresholds; the personal energy plan only adds its assumptions."""
    plan = state.get("profile_analysis", {}).get("energy_plan")
    calculation = calculate_nutrition(recipe)
    if plan:
        calculation["assumptions"] = list(dict.fromkeys([*plan["assumptions"], *calculation["assumptions"]]))[:5]
    return calculation


def _optimizer_targets(state: NutritionReportState) -> list[list[dict[str, Any]]]:
    """Threshold sets the adjuster tries: the user's calorie window first, then the plain research rules."""
    research = report_calculation_service.load_thresholds()  # via the module so swapped thresholds are seen
    personal = personal_thresholds(research, state.get("profile_analysis", {}).get("energy_plan"))
    return [personal, research] if personal != research else [research]


def _outside_personal_window(state: NutritionReportState, calculation: dict[str, Any]) -> float:
    plan = state.get("profile_analysis", {}).get("energy_plan")
    calories = calculation["totals"].get("calories")
    if not plan or calories is None:
        return 0.0
    return max(plan["smoothie_kcal_min"] - calories, calories - plan["smoothie_kcal_max"], 0.0)


def calculate_report_nutrition(state: NutritionReportState) -> dict[str, Any]:
    return {"nutrition_calculation": _calculate(state, state["recipe_draft"])}


MAX_ADJUSTMENT_ROUNDS = 2


def _review_thresholds(calculation: dict[str, Any]) -> list[str]:
    return [item["nutrient"] for item in calculation["thresholds"] if item["status"] == "review"]


def _amount_rows(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"ingredient_id": item["ingredient_id"], "name": item["name"], "amount": item["amount"], "unit": item["unit"]}
        for item in recipe["ingredients"]
    ]


def adjust_recipe_amounts(state: NutritionReportState) -> dict[str, Any]:
    """Try to bring failing thresholds into range by re-weighing the chosen ingredients (max 2 rounds)."""
    original_recipe = state["recipe_draft"]
    original_calculation = state["nutrition_calculation"]
    failing = _review_thresholds(original_calculation)
    if not failing:
        return {}
    metadata = dict(state.get("execution_metadata", {}))
    if original_calculation["missing_data"] or any(
        item["status"] == "unknown" for item in original_calculation["thresholds"]
    ):
        metadata["recipe_adjustment"] = {"applied": False, "reason": "missing_data", "rounds": 0}
        return {"execution_metadata": metadata}

    recipe, calculation, rounds, reason = original_recipe, original_calculation, 0, "no_improvement"
    def score(calc: dict[str, Any]) -> tuple[int, float]:
        # research rules first; among equally good recipes, the one closest to the user's calorie window
        return len(_review_thresholds(calc)), _outside_personal_window(state, calc)

    for _ in range(MAX_ADJUSTMENT_ROUNDS):
        best: tuple[dict[str, Any], dict[str, Any]] | None = None
        for targets in _optimizer_targets(state):
            result = optimize_amounts(recipe, targets)
            if result["status"] != "improved":
                reason = result["reason"]
                continue
            candidate = {
                **recipe,
                "ingredients": [
                    {**item, "amount": amount} for item, amount in zip(recipe["ingredients"], result["amounts"])
                ],
            }
            candidate_calculation = _calculate(state, candidate)
            if best is None or score(candidate_calculation) < score(best[1]):
                best = (candidate, candidate_calculation)
        if best is None or len(_review_thresholds(best[1])) >= len(_review_thresholds(calculation)):
            break
        recipe, calculation, rounds = best[0], best[1], rounds + 1
        if not _review_thresholds(calculation):
            break

    if rounds == 0:
        metadata["recipe_adjustment"] = {"applied": False, "reason": reason, "rounds": 0, "failing_thresholds": failing}
        return {"execution_metadata": metadata}
    remaining = _review_thresholds(calculation)
    metadata["recipe_adjustment"] = {
        "applied": True,
        "rounds": rounds,
        "before": _amount_rows(original_recipe),
        "after": _amount_rows(recipe),
        "fixed_thresholds": [name for name in failing if name not in remaining],
        "remaining_thresholds": remaining,
    }
    return {"recipe_draft": recipe, "nutrition_calculation": calculation, "execution_metadata": metadata}


def safety_and_quality_gate(state: NutritionReportState) -> dict[str, Any]:
    calculation = state["nutrition_calculation"]
    decision = "review" if state.get("decision") == "review" or calculation["decision"] == "review" else calculation["decision"]
    warnings = list(state.get("warnings", []))
    safety = evaluate_safety_rules(
        state.get("profile_analysis", {}).get("condition_codes", []),
        state.get("recipe_draft", {}).get("ingredients", []),
        calculation["totals"],
    )
    warnings.extend(safety["warnings"])
    if _profile_terms(state.get("profile", {}), ("allergies",)):
        # Allergen links not confirmed by an expert were inferred from names; say so instead of implying certainty.
        unreviewed = [
            item["name"] for item in state.get("recipe_draft", {}).get("ingredients", [])
            if "unverified_condition_codes" in item
            and (item["unverified_condition_codes"] or not item.get("condition_codes"))
        ]
        if unreviewed:
            warnings.append(
                "Thông tin dị ứng của " + ", ".join(unreviewed)
                + " được suy luận từ tên nguyên liệu, chưa được chuyên gia xác nhận; hãy kiểm tra thành phần thực tế."
            )
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
    if safety["review"]:
        decision = "review"
    errors = list(state.get("errors", []))
    if safety["errors"]:
        decision = "reject"
        errors.extend(error for error in safety["errors"] if error not in errors)
    return {
        "evaluation_result": {
            "decision": decision,
            "thresholds": calculation["thresholds"],
            "data_coverage": calculation["coverage"],
            "safety_rules": safety["triggered"],
        },
        "decision": decision,
        "errors": errors,
        "warnings": list(dict.fromkeys(warnings)),
    }


def _compose(state: NutritionReportState, force_warning: bool) -> dict[str, Any]:
    recipe = state["recipe_draft"]
    calculation = state["nutrition_calculation"]
    warnings = state.get("warnings", [])
    decision = "review" if force_warning else state.get("decision", "pass")
    profile = state.get("profile", {})
    analysis = state.get("profile_analysis", {})
    snapshot = enrichment.profile_snapshot(profile, analysis)
    month = datetime.now(VIETNAM_TZ).month
    ingredients = [
        {
            "ingredient_id": item["ingredient_id"], "name": item["name"], "amount": item["amount"],
            "unit": item["unit"], "source": item.get("source"), "source_label": item.get("source_label"),
            "source_region": item.get("source_region", "unknown"), "source_per_100g": item.get("per_100g", {}),
            "season": enrichment.ingredient_season(item, month),
            "substitution_for": enrichment.substitution_for(item, snapshot["allergies"]),
        }
        for item in recipe["ingredients"][:8]
    ]
    allergy_blocked = blocked_ingredient_ids({"allergies": snapshot["allergies"]}) if snapshot["allergies"] else set()
    allergens = enrichment.allergen_check(snapshot["allergies"], recipe["ingredients"][:8], allergy_blocked)
    data_checks = enrichment.consistency_checks(calculation["totals"])
    if data_checks:
        decision = "review"
        warnings = [*warnings, *data_checks]
    plan = analysis.get("energy_plan")
    scores = {
        "personal_fit": enrichment.personal_fit_score(
            calculation["thresholds"], len(allergens["conflicts"]), calculation["coverage"],
            calculation["totals"].get("calories"), plan,
        ),
        "seasonal": enrichment.seasonal_score(
            [(float(item["amount"]), item["season"]["status"]) for item in ingredients]
        ),
        "season_month": month,
    }
    unique_sources = []
    for item in ingredients:
        source = item.get("source_label") or "Chưa có nguồn"
        if item.get("source"):
            source = f"{source}: {item['source']}"
        if source not in unique_sources:
            unique_sources.append(source)
    adjustment = state.get("execution_metadata", {}).get("recipe_adjustment") or {}
    adjustment_note = ""
    if adjustment.get("applied"):
        fixed = ", ".join(adjustment["fixed_thresholds"])
        adjustment_note = f"Định lượng đã được tự động điều chỉnh (giữ nguyên nguyên liệu) để đạt ngưỡng: {fixed}. "
    plan = state.get("profile_analysis", {}).get("energy_plan")
    plan_note = describe(plan)
    calories = calculation["totals"].get("calories")
    if plan and calories is not None:
        if calories < plan["smoothie_kcal_min"]:
            plan_note += f" Ly này {calories:.0f} kcal, thấp hơn mục tiêu cá nhân."
        elif calories > plan["smoothie_kcal_max"]:
            plan_note += f" Ly này {calories:.0f} kcal, cao hơn mục tiêu cá nhân; có thể giảm định lượng hoặc chia đôi."
        else:
            plan_note += f" Ly này {calories:.0f} kcal, nằm trong mục tiêu cá nhân."
    details = (
        (plan_note + " " if plan_note else "")
        + "Công thức được tính theo mỗi khẩu phần từ định lượng và dữ liệu dinh dưỡng trên 100 g. "
        f"Độ phủ dữ liệu hiện tại là {calculation['coverage'] * 100:.0f}%. "
        + adjustment_note
        + ("Có điểm cần xem lại trong phần ngưỡng và dữ liệu thiếu." if decision == "review" else "Các ngưỡng demo hiện tại đều đạt.")
    )
    # the AI rationale is trimmed first so the calculated facts (and adjustment note) always fit in 650 chars
    ai_summary = recipe.get("ai_summary") or ""
    ai_summary = ai_summary[: max(650 - len(details) - 1, 0)].strip()
    summary = (ai_summary + " " if ai_summary else "") + details
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
        profile_snapshot=snapshot,
        scores=scores,
        allergen_check=allergens,
        steps=enrichment.structured_steps(recipe["steps"]),
        prep_minutes=recipe.get("prep_minutes"),
        serving_ml=enrichment.serving_ml(recipe["ingredients"], recipe["servings"]),
        meal_context="Bữa phụ",
        reference_ranges=enrichment.reference_ranges(calculation["totals"], plan),
        data_checks=data_checks[:5],
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
    output_path = settings.pdf_dir / f"{document.report_id}.pdf"
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
builder.add_node("adjust_recipe_amounts", adjust_recipe_amounts)
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
builder.add_edge("calculate_nutrition", "adjust_recipe_amounts")
builder.add_edge("adjust_recipe_amounts", "safety_and_quality_gate")
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
