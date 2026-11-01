"""Clinical safety rules and profile classification from Supabase, applied by the /v1/reports graph."""
from __future__ import annotations

import uuid
from dataclasses import replace
from unittest.mock import patch

import pytest

from app.agents.report_graph import analyze_profile, report_graph
from app.config import settings
from app.services import reference_repository
from app.services.clinical_rule_service import classify_profile, evaluate_safety_rules, match_condition_codes
from app.services.reference_repository import ReferenceSnapshot
from tests.test_reference_repository import FULL, item

SUGAR_FREE = {**FULL, "sugar": 0.2}
KIDNEY_BLOCK = "Người bị sỏi thận cần tránh rau bina và củ dền vì giàu oxalat."
SUGAR_WARN = "Người gan nhiễm mỡ nên giữ đường dưới 2,5 g mỗi khẩu phần."
KIDNEY_CONSULT = "Người bị sỏi thận nên hỏi ý kiến bác sĩ về lượng nước và kali."


def rule(code: str, condition: str, action: str, message: str, **extra) -> dict:
    return {"rule_code": code, "condition_code": condition, "target_type": "ingredient_group", "nutrient_code": None,
            "target_text": None, "avoid_or_limit": "avoid", "threshold_value": None, "unit": None,
            "warning_message_vi": message, "severity": "high", "recommended_action": action, **extra}


SNAPSHOT = ReferenceSnapshot(
    source="supabase",
    dataset_version="v-test",
    ingredients=[
        item("Ổi", "ING_FRUIT_0010", {**SUGAR_FREE, "fiber": 5.4}),
        item("Thanh long", "ING_FRUIT_0011", SUGAR_FREE),
        item("Táo", "ING_FRUIT_0012", SUGAR_FREE),
        item("Rau bina", "ING_VEG_0001", SUGAR_FREE, category="vegetable", conditions=["kidney_stones"]),
        item("Củ dền", "ING_VEG_0002", SUGAR_FREE, category="vegetable"),
        item("Xoài", "ING_FRUIT_0013", {**FULL, "sugar": 14.0}),
    ],
    thresholds=[
        {"code": "THR_ENG_001", "nutrient": "calories", "label": "Năng lượng", "unit": "kcal", "minimum": 50.0,
         "maximum": 400.0, "comparator": "between", "basis": "absolute", "source": None},
    ],
    condition_keywords={"kidney_stones": ["soi than", "Sỏi thận"], "nafld": ["gan nhiem mo", "Gan nhiễm mỡ"],
                        "kiwi_allergy": ["kiwi", "Dị ứng kiwi"], "sesame_allergy": ["me", "vung", "Dị ứng mè"]},
    condition_types={"kidney_stones": "disease", "nafld": "disease", "kiwi_allergy": "allergy",
                     "sesame_allergy": "allergy"},
    safety_rules=[
        rule("SAFE_KIDNEY_001", "kidney_stones", "block_recipe", KIDNEY_BLOCK, target_text="rau bina, củ dền"),
        rule("SAFE_KIDNEY_002", "kidney_stones", "suggest_consult", KIDNEY_CONSULT),
        rule("SAFE_NAFLD_001", "nafld", "warn_user", SUGAR_WARN, target_type="nutrient", target_text="Đường tổng",
             avoid_or_limit="limit", threshold_value=2.5, unit="g"),
    ],
    profile_rules=[
        {"rule_code": "PROFILE_BMI_001", "input_field": "bmi", "operator": "between", "min_value": 23.0,
         "max_value": 24.9, "classification_result": "overweight", "target_group": "adult", "priority": 1},
        {"rule_code": "PROFILE_BMI_002", "input_field": "bmi", "operator": "lt", "min_value": None,
         "max_value": 18.5, "classification_result": "underweight", "target_group": "adult", "priority": 2},
        {"rule_code": "PROFILE_AGE_001", "input_field": "age", "operator": "gte", "min_value": 18.0,
         "max_value": None, "classification_result": "adult", "target_group": "adult", "priority": 3},
    ],
)


@pytest.fixture
def db_snapshot(monkeypatch):
    monkeypatch.setattr(settings, "reference_data_source", "db")
    reference_repository.clear_cache()
    with patch.object(reference_repository, "_load_from_database", return_value=SNAPSHOT) as loader:
        yield loader


def profile(*, weight_kg: float = 75, medical_notes: str = "", allergies: list[str] | None = None) -> dict:
    return {"age": 32, "gender": "Nữ", "height_cm": 165, "weight_kg": weight_kg,
            "goal": "overweight_obesity_weight_management", "allergies": allergies or [],
            "disliked_ingredients": [], "medical_notes": medical_notes,
            "health_restriction_status": "yes" if medical_notes else "no"}


def graph_run(ingredients: list[str], **profile_args) -> dict:
    token = uuid.uuid4().hex[:10]
    payload = {"profile": profile(**profile_args), "ingredientIds": ingredients, "servings": 1, "prompt": "",
               "locale": "vi-VN", "allowSuggestions": False}
    initial = {"request": payload, "report_id": f"test_{token}", "thread_id": f"t_{token}", "run_id": f"r_{token}",
               "errors": [], "warnings": [], "retry_count": 0, "execution_metadata": {}}
    with patch.object(settings, "report_recipe_mode", "mock"):
        return report_graph.invoke(initial, {"configurable": {"thread_id": initial["thread_id"]}})


def test_classify_profile_mirrors_sql_operators() -> None:
    rows = classify_profile(32, 165, 65, SNAPSHOT.profile_rules)  # BMI 23.88
    assert [(row["input_field"], row["classification_result"]) for row in rows] == [("bmi", "overweight"), ("age", "adult")]
    assert classify_profile(32, 165, 48, SNAPSHOT.profile_rules)[0]["classification_result"] == "underweight"


def test_bmi_24_is_overweight_from_database_rules(db_snapshot) -> None:
    state = {"profile": profile(weight_kg=65), "errors": [], "decision": "pass"}  # BMI 23.9
    result = analyze_profile(state)
    assert result["errors"] == [] and result["decision"] == "pass"
    assert result["profile_analysis"]["classifications"][0]["rule_code"] == "PROFILE_BMI_001"


def test_database_classification_outside_scope_is_rejected(db_snapshot) -> None:
    result = analyze_profile({"profile": profile(weight_kg=48), "errors": []})  # underweight
    assert result["decision"] == "reject"


def test_bmi_without_matching_db_rule_falls_back_to_25_cutoff(db_snapshot) -> None:
    assert analyze_profile({"profile": profile(weight_kg=80), "errors": []})["errors"] == []  # BMI 29.4
    assert analyze_profile({"profile": profile(weight_kg=55), "errors": []})["decision"] == "reject"  # BMI 20.2


def test_json_fallback_keeps_bmi_25_rule_and_has_no_clinical_rules() -> None:
    assert analyze_profile({"profile": profile(weight_kg=65), "errors": []})["decision"] == "reject"
    result = analyze_profile({"profile": profile(weight_kg=75, medical_notes="sỏi thận"), "errors": []})
    assert result["profile_analysis"]["condition_codes"] == []
    assert evaluate_safety_rules(["kidney_stones"], [{"name": "Rau bina", "condition_codes": ["kidney_stones"]}]) == {
        "errors": [], "warnings": [], "review": False, "triggered": []}


def test_medical_notes_and_allergies_map_to_condition_codes(db_snapshot) -> None:
    assert match_condition_codes([], "Tôi bị sỏi thận 2 năm, gan nhiễm mỡ nhẹ") == ["kidney_stones", "nafld"]
    assert match_condition_codes(["kiwi"], "") == ["kiwi_allergy"]
    # short allergen keywords ("mè" -> "me") only count in the allergy list, not inside free-text notes
    assert match_condition_codes([], "mẹ tôi bị tiểu đường") == []
    assert match_condition_codes([], "bị dị ứng mè") == ["sesame_allergy"]


def test_kidney_stone_note_blocks_linked_ingredient_before_generation(db_snapshot) -> None:
    result = graph_run(["oi", "rau-bina"], medical_notes="sỏi thận")
    assert result["decision"] == "reject"
    assert result["errors"] == [f"{KIDNEY_BLOCK} (Rau bina)"]
    assert "report_document" not in result


def test_block_rule_matches_target_text_without_ingredient_link(db_snapshot) -> None:
    result = graph_run(["oi", "cu-den"], medical_notes="Sỏi thận")
    assert result["decision"] == "reject"
    assert any("Củ dền" in error for error in result["errors"])


def test_kidney_stone_consult_rule_turns_report_into_review(db_snapshot) -> None:
    result = graph_run(["oi", "thanh-long"], medical_notes="sỏi thận")
    assert result["decision"] == "review"
    assert KIDNEY_CONSULT in result["warnings"]
    assert KIDNEY_BLOCK not in " ".join(result["warnings"])  # no blocked ingredient in the recipe
    assert {row["rule_code"] for row in result["evaluation_result"]["safety_rules"]} == {"SAFE_KIDNEY_002"}


def test_nutrient_limit_warns_instead_of_blocking(db_snapshot) -> None:
    warned = graph_run(["oi", "xoai"], medical_notes="gan nhiễm mỡ")
    assert warned["decision"] == "review" and "report_document" in warned
    assert any(text.startswith(SUGAR_WARN) and "ngưỡng < 2.5 g" in text for text in warned["warnings"])
    clean = graph_run(["oi", "thanh-long"], medical_notes="gan nhiễm mỡ")  # 0.48 g sugar per serving
    assert not any(SUGAR_WARN in text for text in clean["warnings"])


def test_nutrient_limit_with_block_action_rejects_after_calculation(db_snapshot, monkeypatch) -> None:
    blocking = replace(SNAPSHOT, safety_rules=[{**SNAPSHOT.safety_rules[2], "recommended_action": "block_recipe"}])
    db_snapshot.return_value = blocking
    reference_repository.clear_cache()
    result = graph_run(["oi", "xoai"], medical_notes="gan nhiễm mỡ")
    assert result["decision"] == "reject"
    assert any(error.startswith(SUGAR_WARN) for error in result["errors"])


def test_allergen_options_come_from_health_conditions_and_match_back(db_snapshot) -> None:
    from app.services.frontend_service import build_allergen_options

    options = build_allergen_options()
    assert options == [{"code": "kiwi_allergy", "label": "Kiwi"}, {"code": "sesame_allergy", "label": "Mè"}]
    # A label the profile form saves must resolve to its own condition in the safety rules.
    for option in options:
        assert match_condition_codes([option["label"]], "") == [option["code"]]


def test_allergen_endpoint_falls_back_to_seed_catalog() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    items = TestClient(app).get("/v1/reference/allergens").json()["items"]
    labels = {item["label"] for item in items}
    assert {"Đậu nành", "Sữa bò", "Kiwi"} <= labels
    assert all(not item["label"].lower().startswith("dị ứng") for item in items)
