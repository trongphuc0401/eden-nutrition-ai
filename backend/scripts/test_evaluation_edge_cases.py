from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.schemas.profile_schema import ProfileInput
from app.schemas.smoothie_schema import SmoothieIngredient, SmoothiePlanResponse
from app.services.evaluation_service import EvaluationService


def make_profile(**overrides) -> ProfileInput:
    data = {
        "age": 32,
        "gender": "female",
        "height_cm": 162,
        "weight_kg": 76,
        "goal": "overweight_obesity_weight_management",
        "allergies": [],
        "preferred_food_types": ["Vietnamese tropical fruits"],
        "disliked_ingredients": [],
        "medical_notes": "",
    }
    data.update(overrides)
    return ProfileInput(**data)


def make_plan(name: str, ingredients: list[SmoothieIngredient]) -> SmoothiePlanResponse:
    return SmoothiePlanResponse(
        smoothie_name=name,
        goal="overweight_obesity_weight_management",
        calories=220,
        ingredients=ingredients,
        reason="Evaluation edge-case test recipe.",
        safety_warning="Review allergies and medical notes before use.",
    )


def assert_report(result: dict, decision: str, overall_pass: bool) -> None:
    report = result["evaluation_report"]
    assert report["decision"] == decision
    assert result["overall_pass"] is overall_pass
    assert 0 <= report["score"] <= 100
    assert isinstance(report["issues"], list)
    assert isinstance(report["recommendations"], list)


def main() -> None:
    service = EvaluationService()

    pass_result = service.evaluate_plan(
        profile=make_profile(),
        plan=make_plan(
            "Passable Orange Soy Smoothie",
            [
                SmoothieIngredient(name="orange", amount="150 g", purpose="fiber and vitamin C"),
                SmoothieIngredient(name="unsweetened soy beverage", amount="200 ml", purpose="protein"),
                SmoothieIngredient(name="chia seeds", amount="1 tbsp", purpose="fiber"),
            ],
        ),
    )
    assert_report(pass_result, decision="pass", overall_pass=True)

    review_result = service.evaluate_plan(
        profile=make_profile(),
        plan=make_plan(
            "Unknown Ingredient Smoothie",
            [
                SmoothieIngredient(name="orange", amount="150 g", purpose="fiber and vitamin C"),
                SmoothieIngredient(name="unsweetened soy beverage", amount="200 ml", purpose="protein"),
                SmoothieIngredient(name="mystery powder", amount="one scoop", purpose="unknown supplement"),
            ],
        ),
    )
    assert_report(review_result, decision="review", overall_pass=False)
    assert review_result["evaluation_report"]["data_coverage"] < 1

    allergy_reject_result = service.evaluate_plan(
        profile=make_profile(allergies=["soy"]),
        plan=make_plan(
            "Soy Allergy Conflict Smoothie",
            [
                SmoothieIngredient(name="orange", amount="150 g", purpose="fiber and vitamin C"),
                SmoothieIngredient(name="unsweetened soy beverage", amount="200 ml", purpose="protein"),
                SmoothieIngredient(name="chia seeds", amount="1 tbsp", purpose="fiber"),
            ],
        ),
    )
    assert_report(allergy_reject_result, decision="reject", overall_pass=False)
    assert any(
        item["rule_code"] == "SAFE_ALLERGY_SOY" and item["triggered"]
        for item in allergy_reject_result["safety_checks"]
    )

    threshold_reject_result = service.evaluate_plan(
        profile=make_profile(),
        plan=make_plan(
            "Too Small Lemon Smoothie",
            [
                SmoothieIngredient(name="lemon", amount="10 g", purpose="flavor"),
            ],
        ),
    )
    assert_report(threshold_reject_result, decision="reject", overall_pass=False)
    assert threshold_reject_result["evaluation_report"]["failed_threshold_count"] > 0

    print(
        {
            "pass": pass_result["evaluation_report"],
            "review": review_result["evaluation_report"],
            "allergy_reject": allergy_reject_result["evaluation_report"],
            "threshold_reject": threshold_reject_result["evaluation_report"],
        }
    )


if __name__ == "__main__":
    main()
