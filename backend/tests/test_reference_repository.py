"""Reference data from Supabase: snapshot mapping, JSON fallback, allergy blocking and DB-driven thresholds."""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.exc import OperationalError

from app.agents.report_graph import report_graph
from app.config import settings
from app.services import reference_repository
from app.services.frontend_service import build_ingredient_catalog
from app.services.recipe_generation_service import blocked_ingredient_ids
from app.services.reference_repository import ReferenceSnapshot
from app.services.report_calculation_service import calculate_nutrition
from app.services.report_data_service import load_ingredient_index, load_thresholds, reference_metadata


def item(name: str, code: str, per_100g: dict, *, category="fruit", conditions=(), months=(), verified=False) -> dict:
    nutrients = {key: per_100g.get(key) for key in reference_repository.NUTRIENT_CODES}
    known = sum(v is not None for v in nutrients.values())
    return {
        "ingredient_id": reference_repository.slugify(name), "ingredient_code": code, "name": name, "aliases": [code],
        "category": category, "source": "https://example.org/fruit-data", "source_label": "Fruit_Data",
        "source_code": "SRC_FRUIT_DATA_001", "source_region": "VN", "per_100g": nutrients, "nutrition_basis": "per_100g",
        "density_g_per_ml": None, "density_source": None, "source_verified": verified,
        "confidence": "medium" if verified else "low", "data_status": "verified" if verified else "needs_review",
        "needs_review_nutrients": [],
        "allergen_groups": sorted({reference_repository.ALLERGEN_GROUPS.get(c, c) for c in conditions} | set(conditions)),
        "condition_codes": list(conditions), "unverified_condition_codes": list(conditions),
        "season_months": list(months), "season_by_scope": {}, "region": "Miền Bắc",
        "allowed_for_smoothie": True, "usable": known >= 4,
    }


FULL = {"calories": 50, "protein": 1.0, "carbohydrate": 11.0, "fat": 0.5, "fiber": 3.0, "sugar": 7.0, "sodium": 2.0}
SNAPSHOT = ReferenceSnapshot(
    source="supabase",
    dataset_version="v-test",
    ingredients=[
        item("Ổi", "ING_FRUIT_0010", {**FULL, "fiber": 5.4}, months=[1, 2, 3]),
        item("Sữa đậu nành", "ING_FRUIT_0132", {"calories": 28, "protein": 3.1, "carbohydrate": 0.4, "fat": 1.6, "fiber": 0.1},
             category="seed", conditions=["soy_allergy"]),
        item("Kiwi", "ING_FRUIT_0152", FULL, conditions=["kiwi_allergy", "latex_fruit_syndrome"], months=[6]),
        item("Chôm chôm", "ING_FRUIT_0020", {"calories": 72}),  # too little data: not offered
    ],
    thresholds=[
        {"code": "THR_ENG_001", "nutrient": "calories", "label": "Năng lượng", "unit": "kcal", "minimum": 110.0,
         "maximum": 300.0, "comparator": "between", "basis": "absolute", "source": "SRC_NIN_2019_DDLS"},
        {"code": "THR_PROTEIN_001", "nutrient": "protein", "label": "Protein (% năng lượng)", "unit": "%", "minimum": 11.0,
         "maximum": 21.0, "comparator": "between", "basis": "percent_energy", "source": None},
        {"code": "THR_FIBER_001", "nutrient": "fiber", "label": "Chất xơ", "unit": "g", "minimum": 8.0, "maximum": None,
         "comparator": "gt", "basis": "absolute", "source": None},
    ],
    condition_keywords={"soy_allergy": ["dau nanh", "soy", "Dị ứng đậu nành"], "kiwi_allergy": ["kiwi"]},
)


@pytest.fixture
def db_snapshot(monkeypatch):
    monkeypatch.setattr(settings, "reference_data_source", "db")
    reference_repository.clear_cache()
    with patch.object(reference_repository, "_load_from_database", return_value=SNAPSHOT) as loader:
        yield loader


def test_index_uses_supabase_rows_and_keeps_international_fallback(db_snapshot) -> None:
    index = load_ingredient_index()
    assert index["oi"]["per_100g"]["fiber"] == 5.4
    assert index["sua-dau-nanh"]["ingredient_code"] == "ING_FRUIT_0132"
    assert index["ing-fruit-0010"]["ingredient_id"] == "oi"  # sheet code works as an alias
    assert "yen-mach" in index  # not in the workbook -> USDA fallback still available
    assert reference_metadata() == {"data_source": "supabase", "dataset_version": "v-test"}


def test_snapshot_is_cached(db_snapshot) -> None:
    load_ingredient_index()
    load_thresholds()
    build_ingredient_catalog(1)
    assert db_snapshot.call_count == 1


def test_allergy_text_is_mapped_through_health_conditions(db_snapshot) -> None:
    blocked = blocked_ingredient_ids({"allergies": ["Đậu nành"]})
    assert "sua-dau-nanh" in blocked and "oi" not in blocked
    assert "kiwi" in blocked_ingredient_ids({"allergies": ["kiwi"]})
    assert "oi" in blocked_ingredient_ids({"disliked_ingredients": ["ổi"]})


def test_db_thresholds_support_percent_energy_and_strict_comparators(db_snapshot) -> None:
    index = load_ingredient_index()
    recipe = {"servings": 1, "ingredients": [{**index["oi"], "amount": 300.0, "unit": "g"}]}
    by_label = {row["nutrient"]: row for row in calculate_nutrition(recipe)["thresholds"]}
    assert by_label["Năng lượng"]["value"] == 150.0 and by_label["Năng lượng"]["status"] == "pass"
    assert by_label["Năng lượng"]["message"] == "Đạt mức khuyến nghị"
    # 3 g protein * 4 kcal / 150 kcal = 8 % of energy -> below 11 %
    assert by_label["Protein (% năng lượng)"]["value"] == 8.0
    assert by_label["Protein (% năng lượng)"]["status"] == "review"
    assert by_label["Chất xơ"]["status"] == "pass"  # 16.2 g > 8 g


def test_catalog_lists_only_ingredients_with_nutrition_data(db_snapshot) -> None:
    catalog = build_ingredient_catalog(month=1)
    ids = [row["id"] for row in catalog]
    assert "chom-chom" not in ids
    assert ids[0] == "oi" and catalog[0]["seasonal"] == "in"
    assert {row["kind"] for row in catalog} == {"fruit", "support"}


def test_auto_mode_falls_back_to_json_when_db_is_sparse(monkeypatch) -> None:
    monkeypatch.setattr(settings, "reference_data_source", "auto")
    sparse = ReferenceSnapshot("supabase", "v-test", SNAPSHOT.ingredients[:2], SNAPSHOT.thresholds)
    with patch.object(reference_repository, "_load_from_database", return_value=sparse):
        assert reference_repository.get_snapshot() is None
        assert reference_metadata()["data_source"] == "json"
        assert "hat-chia" in load_ingredient_index()  # JSON seed path


def test_auto_mode_survives_database_outage(monkeypatch) -> None:
    monkeypatch.setattr(settings, "reference_data_source", "auto")
    error = OperationalError("SELECT 1", {}, Exception("down"))
    with patch.object(reference_repository, "_load_from_database", side_effect=error) as loader:
        assert reference_repository.get_snapshot() is None
        assert reference_repository.get_snapshot() is None
        assert loader.call_count == 1  # backoff: a dead database is not hit on every request
        assert load_thresholds()  # JSON thresholds still served


def graph_run(ingredients: list[str], allergies: list[str] | None = None) -> dict:
    token = uuid.uuid4().hex[:10]
    payload = {
        "profile": {"age": 32, "gender": "Nữ", "height_cm": 165, "weight_kg": 75,
                    "goal": "overweight_obesity_weight_management", "allergies": allergies or [],
                    "disliked_ingredients": [], "medical_notes": "", "health_restriction_status": "no"},
        "ingredientIds": ingredients, "servings": 1, "prompt": "", "locale": "vi-VN",
    }
    initial = {"request": payload, "report_id": f"test_{token}", "thread_id": f"t_{token}", "run_id": f"r_{token}",
               "errors": [], "warnings": [], "retry_count": 0, "execution_metadata": {}}
    with patch.object(settings, "report_recipe_mode", "mock"):
        return report_graph.invoke(initial, {"configurable": {"thread_id": initial["thread_id"]}})


def test_report_graph_runs_on_database_snapshot(db_snapshot) -> None:
    result = graph_run(["oi", "kiwi"])
    assert result["execution_metadata"]["data_source"] == "supabase"
    assert result["execution_metadata"]["dataset_version"] == "v-test"
    # mock amounts 120 g each = 120 kcal; failing thresholds may then be re-weighed by the adjuster
    before = result["execution_metadata"].get("recipe_adjustment", {}).get("before")
    assert before is None or [row["amount"] for row in before] == [120.0, 120.0]
    assert result["nutrition_calculation"]["totals"]["calories"] is not None
    labels = {row["nutrient"] for row in result["report_document"]["thresholds"]}
    assert "Protein (% năng lượng)" in labels


def test_report_graph_rejects_allergen_from_database(db_snapshot) -> None:
    result = graph_run(["oi", "sua-dau-nanh"], allergies=["đậu nành"])
    assert result["decision"] == "reject"
    assert any("Sữa đậu nành" in error for error in result["errors"])
