"""Adapters for the Next.js workspace contract."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any

from app.schemas.profile_schema import ProfileInput
from app.services.evaluation_service import EvaluationService
from app.services.nutrition_service import NutritionService, build_profile_analysis


def ingredient_id(name: str) -> str:
    normalized = unicodedata.normalize("NFD", name.lower()).replace("đ", "d")
    ascii_name = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")


def _seasonal(season_months: list[int], month: int) -> str:
    return "unknown" if not season_months else ("in" if month in season_months else "out")


def build_ingredient_catalog(month: int | None = None, hometown: str | None = None) -> list[dict[str, Any]]:
    from app.services.nutrition_service import load_local_seed
    from app.services.personalization_service import months_for, region_scope
    from app.services.reference_repository import get_snapshot

    active_month = month or datetime.now().month
    catalog: list[dict[str, Any]] = []
    snapshot = get_snapshot()
    if snapshot is not None:
        # Same IDs the report pipeline resolves, so every selectable item has nutrition data behind it.
        scope = region_scope(hometown)
        for item in snapshot.ingredients:
            if not item["usable"]:
                continue
            catalog.append({
                "id": item["ingredient_id"], "name": item["name"], "kind": "fruit" if item["category"] == "fruit" else "support",
                "seasonal": _seasonal(months_for(item, scope), active_month), "region": item["region"] or "Chưa có dữ liệu vùng",
                "season_months": months_for(item, scope), "source": item["source_label"],
            })
        return sorted(catalog, key=lambda item: (item["seasonal"] != "in", item["kind"] != "fruit", item["name"]))
    for item in load_local_seed():
        if not item.get("allowed_for_smoothie", True):
            continue
        season_months = item.get("season_months") or []
        seasonal = _seasonal(season_months, active_month)
        name = str(item.get("ingredient_name") or item.get("title") or "")
        if name:
            catalog.append({"id": ingredient_id(name), "name": name, "kind": "fruit", "seasonal": seasonal, "region": item.get("region") or "Chưa có dữ liệu vùng", "season_months": season_months, "source": item.get("source") or "Chưa có nguồn"})
    return sorted(catalog, key=lambda item: (item["seasonal"] != "in", item["name"]))


def build_allergen_options() -> list[dict[str, str]]:
    """Allergy conditions for the profile form: Supabase health_conditions, else the importer's seed catalog.

    The label is the condition name without "Dị ứng", which still matches the condition keywords that
    clinical_rule_service.match_condition_codes checks the profile's allergy list against.
    """
    from app.services.reference_import.catalog import CONDITIONS
    from app.services.reference_repository import get_snapshot

    snapshot = get_snapshot()
    if snapshot is not None and snapshot.condition_types:
        names = {code: words[-1] for code, words in snapshot.condition_keywords.items() if words}  # name_vi is last
        pairs = [(code, names.get(code) or code) for code, kind in snapshot.condition_types.items() if kind == "allergy"]
    else:
        pairs = [(code, entry[1]) for code, entry in CONDITIONS.items() if entry[0] == "allergy"]
    return sorted(({"code": code, "label": _allergen_label(name)} for code, name in pairs), key=lambda item: ingredient_id(item["label"]))


def _allergen_label(name: str) -> str:
    label = re.sub(r"^\s*dị ứng\s+", "", name, flags=re.IGNORECASE).strip()
    return label[:1].upper() + label[1:]


def create_frontend_report(profile: ProfileInput, prompt: str = "") -> dict[str, Any]:
    """Create a UI-ready report from the existing generation/evaluation pipeline."""
    generation = NutritionService().generate_smoothie(profile=profile, persist_result=False)
    evaluation = EvaluationService().evaluate_plan(profile=profile, plan=generation.plan)
    nutrition = evaluation["estimated_nutrition"]
    plan = generation.plan
    return {
        "id": f"preview-{datetime.now().timestamp():.0f}", "name": plan.smoothie_name,
        "createdAt": datetime.now().isoformat(), "saved": False,
        "decision": "pass" if evaluation["evaluation_report"]["decision"] == "pass" else "review", "version": 1,
        "ingredients": [{"name": item.name, "amount": item.amount, "purpose": item.purpose, "used": True} for item in plan.ingredients],
        "nutrition": {"calories": nutrition.get("calories"), "protein": nutrition.get("protein_g"), "carbs": None, "fat": None, "fiber": nutrition.get("fiber_g"), "sugar": nutrition.get("total_sugar_g")},
        "tools": ["Máy xay sinh tố", "Ly định lượng", "Dao và thớt"],
        "steps": ["Rửa sạch và sơ chế nguyên liệu theo định lượng.", "Cho nguyên liệu cùng chất lỏng vào máy xay.", "Xay đến khi mịn, sau đó điều chỉnh bằng nước hoặc đá nếu cần.", "Dùng ngay sau khi xay."],
        "reason": plan.reason, "warning": plan.safety_warning,
        "sources": [*generation.knowledge_titles, *generation.warnings] or ["Dữ liệu dinh dưỡng nội bộ"],
        "prompt": prompt, "profile_analysis": build_profile_analysis(profile).model_dump(),
    }
