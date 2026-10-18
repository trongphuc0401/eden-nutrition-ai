from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from app.agents.report_graph import adjust_recipe_amounts, report_graph
from app.schemas.report_schema import RecipeProposal
from app.services.recipe_optimizer import MAX_AMOUNT, optimize_amounts
from app.services.report_calculation_service import calculate_nutrition
from app.services.report_data_service import resolve_ingredients


# Research-scope rules (Supabase shape): both bases and every comparator the calculator supports.
RESEARCH_THRESHOLDS = [
    {"nutrient": "calories", "label": "Năng lượng", "unit": "kcal", "minimum": 110, "maximum": 300, "comparator": "between"},
    {"nutrient": "fiber", "label": "Chất xơ", "unit": "g", "minimum": 8, "maximum": None, "comparator": "gt"},
    {"nutrient": "sugar", "label": "Đường tổng", "unit": "g", "minimum": None, "maximum": 25, "comparator": "lte"},
    {"nutrient": "fat", "label": "Chất béo", "unit": "%E", "minimum": 6, "maximum": 15,
     "comparator": "between", "basis": "percent_energy"},
]


def recipe(amounts: dict[str, float], servings: int = 1) -> dict:
    resolved, _ = resolve_ingredients(list(amounts))
    return {
        "title": "Test",
        "servings": servings,
        "ingredients": [{**item, "amount": amounts[item["ingredient_id"]], "unit": "g"} for item in resolved],
    }


def statuses(calculation: dict) -> dict[str, str]:
    return {item["nutrient"]: item["status"] for item in calculation["thresholds"]}


class RecipeOptimizerTests(unittest.TestCase):
    def test_low_calorie_low_fiber_recipe_is_adjusted_to_pass(self) -> None:
        draft = recipe({"cam": 40, "yen-mach": 10})
        with patch("app.services.report_calculation_service.load_thresholds", return_value=RESEARCH_THRESHOLDS):
            before = calculate_nutrition(draft)
            self.assertEqual(statuses(before)["Năng lượng"], "review")
            self.assertEqual(statuses(before)["Chất xơ"], "review")
            result = optimize_amounts(draft, RESEARCH_THRESHOLDS)
            self.assertEqual(result["status"], "improved")
            adjusted = {**draft, "ingredients": [
                {**item, "amount": amount} for item, amount in zip(draft["ingredients"], result["amounts"])
            ]}
            after = calculate_nutrition(adjusted)
        self.assertTrue(all(status == "pass" for status in statuses(after).values()), after["thresholds"])

    def test_bounds_are_respected(self) -> None:
        huge = [{"nutrient": "calories", "unit": "kcal", "minimum": 5000, "maximum": None, "comparator": "gte"}]
        result = optimize_amounts(recipe({"cam": 100, "yen-mach": 50}), huge)
        self.assertEqual(result["amounts"], [MAX_AMOUNT["g"], MAX_AMOUNT["g"]])
        tiny = [{"nutrient": "calories", "unit": "kcal", "minimum": None, "maximum": 1, "comparator": "lte"}]
        result = optimize_amounts(recipe({"cam": 100, "yen-mach": 12}), tiny)
        # never below 25 % of the proposal / 5 g: ingredients shrink but are never removed
        self.assertEqual(result["amounts"], [25.0, 5.0])
        self.assertTrue(all(amount > 0 for amount in result["amounts"]))

    def test_missing_data_is_never_adjusted(self) -> None:
        draft = recipe({"cam": 40, "nguyen-lieu-chua-co": 50})
        result = optimize_amounts(draft, RESEARCH_THRESHOLDS)
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "missing_data")
        self.assertEqual(result["amounts"], [40.0, 50.0])


def _proposal(amounts: dict[str, float]):
    def generate(**kwargs):
        proposal = RecipeProposal.model_validate({
            "version": 1,
            "title": "Sinh tố điều chỉnh",
            "ingredients": [
                {"ingredient_id": key, "amount": value, "unit": "g", "reason": "test"} for key, value in amounts.items()
            ],
            "suggested_ingredient_ids": [],
            "steps": ["Rửa nguyên liệu.", "Cân nguyên liệu.", "Xay và dùng ngay."],
            "prep_minutes": 8,
            "rationale": "Test điều chỉnh.",
            "ai_provider": "test",
            "ai_model": "test",
            "prompt_version": "test-v1",
        })
        return proposal, {"mode": "test", "usage": {}, "repairs": 0}
    return generate


def _run(ingredients: dict[str, float], thresholds: list[dict]) -> dict:
    token = uuid.uuid4().hex[:10]
    payload = {
        "profile": {
            "age": 32, "gender": "Nữ", "height_cm": 165, "weight_kg": 75,
            "goal": "overweight_obesity_weight_management", "allergies": [],
            "medical_notes": "", "health_restriction_status": "no",
        },
        "ingredientIds": list(ingredients),
        "servings": 1,
        "locale": "vi-VN",
    }
    initial = {
        "request": payload, "report_id": f"test_{token}", "thread_id": f"thread_{token}", "run_id": f"run_{token}",
        "errors": [], "warnings": [], "retry_count": 0, "execution_metadata": {},
    }
    with (
        patch("app.agents.report_graph.generate_recipe_proposal", side_effect=_proposal(ingredients)),
        patch("app.services.report_calculation_service.load_thresholds", return_value=thresholds),
        patch("app.services.recipe_optimizer.load_thresholds", return_value=thresholds),
    ):
        return report_graph.invoke(initial)


class AdjustmentNodeTests(unittest.TestCase):
    def test_graph_adjusts_failing_recipe_and_records_it(self) -> None:
        result = _run({"cam": 40, "yen-mach": 10}, RESEARCH_THRESHOLDS)
        adjustment = result["execution_metadata"]["recipe_adjustment"]
        self.assertTrue(adjustment["applied"])
        self.assertLessEqual(adjustment["rounds"], 2)
        self.assertEqual([row["amount"] for row in adjustment["before"]], [40, 10])
        self.assertIn("Năng lượng", adjustment["fixed_thresholds"])
        self.assertIn("Chất xơ", adjustment["fixed_thresholds"])
        self.assertEqual(adjustment["remaining_thresholds"], [])
        document = result["report_document"]
        self.assertEqual([item["ingredient_id"] for item in document["ingredients"]], ["cam", "yen-mach"])
        self.assertEqual(
            [item["amount"] for item in document["ingredients"]], [row["amount"] for row in adjustment["after"]]
        )
        self.assertTrue(all(0 < item["amount"] <= 400 for item in document["ingredients"]))
        self.assertTrue(all(item["status"] == "pass" for item in document["thresholds"]))
        self.assertIn("tự động điều chỉnh", document["summary"])

    def test_impossible_targets_keep_original_amounts_and_review(self) -> None:
        impossible = [
            {"nutrient": "calories", "label": "Năng lượng", "unit": "kcal", "minimum": 5000, "maximum": None, "comparator": "gte"},
            {"nutrient": "sugar", "label": "Đường tổng", "unit": "g", "minimum": None, "maximum": 0, "comparator": "lt"},
        ]
        result = _run({"cam": 40, "yen-mach": 10}, impossible)
        adjustment = result["execution_metadata"]["recipe_adjustment"]
        self.assertFalse(adjustment["applied"])
        self.assertEqual(result["decision"], "review")
        self.assertEqual([item["amount"] for item in result["report_document"]["ingredients"]], [40, 10])
        self.assertNotIn("tự động điều chỉnh", result["report_document"]["summary"])

    def test_unknown_values_are_not_adjusted(self) -> None:
        result = _run({"cam": 40, "nguyen-lieu-chua-co": 50}, RESEARCH_THRESHOLDS)
        self.assertFalse(result["execution_metadata"].get("recipe_adjustment", {}).get("applied"))
        self.assertEqual(result["decision"], "review")
        self.assertIsNone(result["report_document"]["totals"]["calories"])
        self.assertEqual([item["amount"] for item in result["report_document"]["ingredients"]], [40, 50])

    def test_partially_missing_data_skips_adjustment(self) -> None:
        # calories are known (and failing) but sugar is unknown for one ingredient: no adjustment at all
        draft = recipe({"cam": 40, "yen-mach": 10})
        draft["ingredients"][1] = {
            **draft["ingredients"][1], "per_100g": {**draft["ingredients"][1]["per_100g"], "sugar": None},
        }
        with patch("app.services.report_calculation_service.load_thresholds", return_value=RESEARCH_THRESHOLDS):
            calculation = calculate_nutrition(draft)
            self.assertIn("review", statuses(calculation).values())
            update = adjust_recipe_amounts({"recipe_draft": draft, "nutrition_calculation": calculation})
        self.assertEqual(
            update["execution_metadata"]["recipe_adjustment"], {"applied": False, "reason": "missing_data", "rounds": 0}
        )
        self.assertNotIn("recipe_draft", update)
        self.assertNotIn("nutrition_calculation", update)


if __name__ == "__main__":
    unittest.main()
