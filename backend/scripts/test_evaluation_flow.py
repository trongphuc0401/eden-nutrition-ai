from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.schemas.profile_schema import ProfileInput
from app.schemas.smoothie_schema import SmoothieIngredient, SmoothiePlanResponse
from app.services.evaluation_service import EvaluationService


def main() -> None:
    profile = ProfileInput(
        age=29,
        gender="female",
        height_cm=162,
        weight_kg=76,
        goal="overweight_obesity_weight_management",
        allergies=["milk"],
        preferred_food_types=["Vietnamese tropical fruits"],
        disliked_ingredients=["banana"],
        medical_notes="prediabetes",
    )
    plan = SmoothiePlanResponse(
        smoothie_name="Vietnamese Orange Soy Smoothie",
        goal=profile.goal,
        calories=280,
        ingredients=[
            SmoothieIngredient(name="orange", amount="120 g", purpose="fiber"),
            SmoothieIngredient(name="unsweetened soy beverage", amount="200 ml", purpose="protein"),
            SmoothieIngredient(name="spinach", amount="40 g", purpose="micronutrients"),
            SmoothieIngredient(name="chia seeds", amount="1 tsp", purpose="fiber"),
        ],
        reason="Dry-run example",
        safety_warning="Please consult a clinician if you have ongoing medical concerns.",
    )

    result = EvaluationService().evaluate_plan(profile=profile, plan=plan)
    assert len(result["ingredient_breakdown"]) == 4
    assert result["ingredient_breakdown"][0]["source"] == "vietnamese_fruit_seed"
    assert result["ingredient_breakdown"][0]["matched_reference"] == "Cam"
    assert result["ingredient_breakdown"][0]["estimated_amount_g"] == 120.0
    assert result["estimated_nutrition"]["calories"] > 0
    assert len(result["threshold_checks"]) >= 4
    assert result["evaluation_report"]["decision"] in {"pass", "review", "reject"}
    assert result["evaluation_report"]["score"] >= 0
    assert result["evaluation_report"]["data_coverage"] > 0
    print(result)


if __name__ == "__main__":
    main()
