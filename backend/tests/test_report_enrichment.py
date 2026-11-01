from __future__ import annotations

import unittest

from app.schemas.report_schema import NutritionReportDocument
from app.services import report_enrichment as enrichment


class SeasonTests(unittest.TestCase):
    def test_season_status(self) -> None:
        self.assertEqual(enrichment.ingredient_season({"season_months": [6, 7, 8, 9]}, 9)["status"], "in_season")
        self.assertEqual(enrichment.ingredient_season({"season_months": [1, 2, 3]}, 9)["status"], "out_of_season")
        self.assertEqual(enrichment.ingredient_season({"season_months": list(range(1, 13))}, 9)["status"], "year_round")
        self.assertEqual(enrichment.ingredient_season({"category": "seed"}, 9)["status"], "not_seasonal")
        self.assertEqual(enrichment.ingredient_season({"category": "fruit"}, 9)["status"], "unknown")

    def test_seasonal_score_is_weighted_and_skips_non_seasonal(self) -> None:
        rows = [(120, "in_season"), (100, "in_season"), (30, "out_of_season"), (20, "not_seasonal")]
        self.assertEqual(enrichment.seasonal_score(rows), round((220 * 100 + 30 * 20) / 250))
        self.assertIsNone(enrichment.seasonal_score([(20, "not_seasonal"), (5, "unknown")]))


class ScoreTests(unittest.TestCase):
    def test_personal_fit_deductions(self) -> None:
        thresholds = [
            {"nutrient": "Đường tổng", "status": "review"},
            {"nutrient": "Natri", "status": "unknown"},
            {"nutrient": "Protein", "status": "pass"},
        ]
        plan = {"smoothie_kcal_min": 150, "smoothie_kcal_max": 250}
        score = enrichment.personal_fit_score(thresholds, conflicts=0, coverage=1.0, calories=295, plan=plan)
        self.assertEqual(score["value"], 100 - 15 - 5 - 10)
        self.assertEqual(len(score["breakdown"]), 3)

    def test_allergen_conflict_costs_40_points(self) -> None:
        score = enrichment.personal_fit_score([], conflicts=1, coverage=1.0, calories=None, plan=None)
        self.assertEqual(score["value"], 60)

    def test_allergen_check_only_counts_allergy_blocks(self) -> None:
        ingredients = [
            {"ingredient_id": "sua-bo", "name": "Sữa bò"},
            {"ingredient_id": "oi", "name": "Ổi"},
        ]
        result = enrichment.allergen_check(["sữa bò"], ingredients, {"sua-bo"})
        self.assertEqual(result["conflicts"], ["Sữa bò"])
        self.assertEqual(result["checked_ingredients"], 2)


class ConsistencyTests(unittest.TestCase):
    def test_sugar_above_carbs_is_flagged(self) -> None:
        issues = enrichment.consistency_checks(
            {"calories": 295, "protein": 10.4, "carbohydrate": 17.5, "fat": 6, "sugar": 30}
        )
        self.assertEqual(len(issues), 2)  # sugar > carbs, and macros give ~165 kcal not 295

    def test_consistent_totals_pass(self) -> None:
        self.assertEqual(
            enrichment.consistency_checks({"calories": 300, "protein": 10, "carbohydrate": 52, "fat": 6.5, "sugar": 24}),
            [],
        )

    def test_reference_ranges_follow_energy_share(self) -> None:
        ranges = {row["nutrient"]: row for row in enrichment.reference_ranges({"calories": 300}, None)}
        self.assertEqual((ranges["carbohydrate"]["minimum"], ranges["carbohydrate"]["maximum"]), (33.8, 48.8))
        self.assertEqual((ranges["fat"]["minimum"], ranges["fat"]["maximum"]), (6.7, 11.7))


class StepAndProfileTests(unittest.TestCase):
    def test_steps_get_kind_and_minutes(self) -> None:
        steps = enrichment.structured_steps([
            "Rửa sạch nguyên liệu tươi, để ráo.",
            "Cân đúng định lượng; ngâm hạt chia 10 phút.",
            "Xay 45–60 giây đến khi mịn.",
            "Chia đúng số khẩu phần và dùng ngay.",
        ])
        self.assertEqual([row["kind"] for row in steps], ["wash", "weigh", "blend", "pour"])
        self.assertEqual(steps[1]["minutes"], 10)
        self.assertEqual(steps[2]["minutes"], 1.0)
        self.assertIsNone(steps[0]["minutes"])

    def test_bmi_category_uses_asian_cutoffs(self) -> None:
        self.assertEqual(enrichment.bmi_category(35), "Béo phì độ II (ngưỡng châu Á)")
        self.assertEqual(enrichment.bmi_category(24), "Thừa cân (ngưỡng châu Á)")
        self.assertEqual(
            enrichment.bmi_category(35, [{"input_field": "bmi", "classification_result": "Béo phì"}]), "Béo phì"
        )

    def test_plant_milk_tagged_as_cow_milk_substitute(self) -> None:
        self.assertEqual(enrichment.substitution_for({"name": "Sữa yến mạch"}, ["sữa bò"]), "sữa bò")
        self.assertIsNone(enrichment.substitution_for({"name": "Sữa yến mạch"}, ["đậu phộng"]))
        self.assertIsNone(enrichment.substitution_for({"name": "Ổi"}, ["sữa bò"]))

    def test_serving_volume(self) -> None:
        ingredients = [{"amount": 120}, {"amount": 100}, {"amount": 150}]
        self.assertEqual(enrichment.serving_ml(ingredients, 1), 370)
        self.assertEqual(enrichment.serving_ml(ingredients, 2), 180)


class BackwardCompatibilityTests(unittest.TestCase):
    def test_old_report_without_new_fields_still_parses(self) -> None:
        document = NutritionReportDocument.model_validate({
            "report_id": "old", "title": "Sinh tố", "goal": "x", "servings": 1, "ingredients": [],
            "preparation_steps": [], "usage": "", "summary": "", "totals": {}, "ingredient_nutrition": [],
            "data_coverage": 1, "decision": "pass",
        })
        self.assertIsNone(document.scores)
        self.assertEqual(document.steps, [])


if __name__ == "__main__":
    unittest.main()
