"""Energy plan, climate zone, liquid units and allergen-review warnings."""
from __future__ import annotations

from unittest.mock import patch

from app.schemas.report_schema import RecipeProposal
from app.services.frontend_service import build_ingredient_catalog
from app.services.personalization_service import energy_plan, months_for, personal_thresholds, region_scope
from app.services.recipe_generation_service import validate_proposal
from app.services.report_calculation_service import default_amount
from test_reference_repository import SNAPSHOT, db_snapshot, graph_run  # noqa: F401  (fixture re-export)

PROFILE = {"age": 32, "gender": "Nữ", "height_cm": 165, "weight_kg": 75, "allergies": [], "disliked_ingredients": []}
CALORIES = {"code": "THR_ENG_001", "nutrient": "calories", "label": "Năng lượng", "unit": "kcal",
            "minimum": 110.0, "maximum": 300.0, "comparator": "between", "basis": "absolute"}


def test_energy_plan_mifflin_st_jeor_with_weight_loss_deficit() -> None:
    plan = energy_plan({**PROFILE, "activity_level": "light"})
    assert plan["bmr_kcal"] == 1460  # 10*75 + 6.25*165 - 5*32 - 161
    assert plan["daily_target_kcal"] == 1508  # 1460 * 1.375 - 500
    assert (plan["smoothie_kcal_min"], plan["smoothie_kcal_max"]) == (151, 226)
    assert plan["assumptions"] == []


def test_missing_activity_is_an_explicit_assumption_and_floor_applies() -> None:
    plan = energy_plan({**PROFILE, "age": 70, "height_cm": 150, "weight_kg": 60, "activity_level": "sedentary"})
    assert plan["daily_target_kcal"] == 1200  # never below the 1200 kcal floor for women
    assert "vận động" in energy_plan(PROFILE)["assumptions"][0]
    assert energy_plan({"age": 0}) is None


def test_personal_window_only_narrows_the_research_rule() -> None:
    plan = energy_plan(PROFILE)
    narrowed = personal_thresholds([CALORIES], plan)[0]
    assert (narrowed["minimum"], narrowed["maximum"]) == (151.0, 226.0)
    wide = {**plan, "smoothie_kcal_min": 50, "smoothie_kcal_max": 900}
    clipped = personal_thresholds([CALORIES], wide)[0]
    assert (clipped["minimum"], clipped["maximum"]) == (110.0, 300.0)
    assert personal_thresholds([CALORIES], None) == [CALORIES]


def test_region_scope_and_zone_specific_season() -> None:
    assert region_scope("TP. Hồ Chí Minh") == "south"
    assert region_scope("Hà Nội") == "north"
    assert region_scope("Nghệ An") == "central"
    assert region_scope("Paris") is None
    item = {"season_months": [1, 2, 3, 10, 11, 12], "season_by_scope": {"north": [10, 11, 12], "south": [1, 2, 3]}}
    assert months_for(item, "south") == [1, 2, 3]
    assert months_for(item, "central") == [1, 2, 3, 10, 11, 12]


def test_catalog_seasonality_follows_hometown(db_snapshot) -> None:  # noqa: F811
    zoned = {**SNAPSHOT.ingredients[0], "season_by_scope": {"south": [10]}}
    snapshot = type(SNAPSHOT)(SNAPSHOT.source, SNAPSHOT.dataset_version, [zoned, *SNAPSHOT.ingredients[1:]],
                              SNAPSHOT.thresholds, SNAPSHOT.condition_keywords)
    db_snapshot.return_value = snapshot
    south = {row["id"]: row["seasonal"] for row in build_ingredient_catalog(10, "TP. Hồ Chí Minh")}
    north = {row["id"]: row["seasonal"] for row in build_ingredient_catalog(10, "Hà Nội")}
    assert south["oi"] == "in" and north["oi"] == "out"


def test_liquid_without_sourced_density_is_weighed_in_grams() -> None:
    assert default_amount({"ingredient_id": "sua-dau-nanh", "name": "Sữa đậu nành"}, 2) == (200.0, "g")
    sourced = {"ingredient_id": "sua-dau-nanh", "name": "Sữa đậu nành", "density_g_per_ml": 1.03, "density_source": "lab"}
    assert default_amount(sourced, 2) == (200.0, "ml")
    proposal = RecipeProposal.model_validate({
        "title": "Test", "steps": ["Một", "Hai", "Ba"], "prep_minutes": 5, "rationale": "x",
        "ingredients": [{"ingredient_id": "sua-dau-nanh", "amount": 200, "unit": "ml", "reason": "nền"}],
        "ai_provider": "t", "ai_model": "t", "prompt_version": "t",
    })
    assert any("mật độ" in error for error in validate_proposal(proposal, PROFILE, {"sua-dau-nanh"}, False))


def test_report_flags_inferred_allergen_data_and_states_energy_target(db_snapshot) -> None:  # noqa: F811
    result = graph_run(["oi", "kiwi"], allergies=["đậu nành"])
    assert any("chưa được chuyên gia xác nhận" in warning for warning in result["warnings"])
    assert "kcal/ngày" in result["report_document"]["summary"]
    assert result["profile_analysis"]["energy_plan"]["smoothie_kcal_min"] == 151


def test_milk_rule_text_does_not_match_plant_milk() -> None:
    from app.services.clinical_rule_service import _ingredient_matches

    rule = {"condition_code": "milk_allergy", "target_text": "milk,yogurt,whey,sữa bò,sữa chua,phô mai"}
    soy = {"ingredient_id": "sua-dau-nanh", "name": "Sữa đậu nành", "aliases": ["Soy milk"], "condition_codes": ["soy_allergy"]}
    yogurt = {"ingredient_id": "sua-chua", "name": "Sữa chua", "aliases": [], "condition_codes": []}
    assert not _ingredient_matches(rule, soy)
    assert _ingredient_matches(rule, yogurt)
