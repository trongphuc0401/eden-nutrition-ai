from __future__ import annotations

from typing import Any, TypedDict


class NutritionReportState(TypedDict, total=False):
    request: dict[str, Any]
    report_id: str
    thread_id: str
    run_id: str
    profile: dict[str, Any]
    selected_ingredients: list[dict[str, Any]]
    ingredient_data: list[dict[str, Any]]
    profile_analysis: dict[str, Any]
    recipe_draft: dict[str, Any]
    recipe_proposal: dict[str, Any]
    confirmation_required: bool
    nutrition_calculation: dict[str, Any]
    evaluation_result: dict[str, Any]
    decision: str
    report_document: dict[str, Any]
    pdf_metadata: dict[str, Any]
    errors: list[str]
    warnings: list[str]
    retry_count: int
    execution_metadata: dict[str, Any]
