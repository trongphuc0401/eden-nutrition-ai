import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.schemas.profile_schema import ProfileInput
from app.schemas.smoothie_schema import SmoothiePlanResponse
from app.services.guardrail_service import expand_blocked_terms, normalize_text
from app.services.research_rule_service import ResearchRuleService


@dataclass
class NutrientEstimate:
    calories: float = 0.0
    protein_g: float = 0.0
    fiber_g: float = 0.0
    total_sugar_g: float = 0.0


FALLBACK_INGREDIENT_NUTRITION = {
    "unsweetened soy beverage": {"calories": 66.0, "protein_g": 6.0, "fiber_g": 1.0, "total_sugar_g": 1.0},
    "nuoc dau nanh khong duong": {"calories": 33.0, "protein_g": 3.0, "fiber_g": 0.5, "total_sugar_g": 0.8},
    "sua dau nanh khong duong": {"calories": 33.0, "protein_g": 3.0, "fiber_g": 0.5, "total_sugar_g": 0.8},
    "spinach": {"calories": 9.0, "protein_g": 1.2, "fiber_g": 0.9, "total_sugar_g": 0.1},
    "rau bina": {"calories": 9.0, "protein_g": 1.2, "fiber_g": 0.9, "total_sugar_g": 0.1},
    "chia seeds": {"calories": 25.0, "protein_g": 1.0, "fiber_g": 2.0, "total_sugar_g": 0.0},
    "hat chia": {"calories": 25.0, "protein_g": 1.0, "fiber_g": 2.0, "total_sugar_g": 0.0},
    "guava": {"calories": 82.0, "protein_g": 3.0, "fiber_g": 6.0, "total_sugar_g": 9.0},
    "oi": {"calories": 68.0, "protein_g": 2.6, "fiber_g": 5.4, "total_sugar_g": 8.9},
    "nuoc loc lanh": {"calories": 0.0, "protein_g": 0.0, "fiber_g": 0.0, "total_sugar_g": 0.0},
    "nuoc loc": {"calories": 0.0, "protein_g": 0.0, "fiber_g": 0.0, "total_sugar_g": 0.0},
    "bot protein thuc vat": {"calories": 380.0, "protein_g": 75.0, "fiber_g": 5.0, "total_sugar_g": 2.0},
}

INGREDIENT_ALIASES = {
    "orange": ["cam"],
    "guava": ["oi", "ổi"],
    "oi": ["guava", "ổi"],
    "pomelo": ["buoi", "bưởi", "buoi da xanh"],
    "buoi": ["pomelo", "bưởi", "buoi da xanh"],
    "lemon": ["chanh"],
    "lime": ["chanh"],
    "grapefruit": ["buoi"],
    "strawberry": ["dau tay"],
    "banana": ["chuoi tay", "chuoi tieu"],
    "watermelon": ["dua hau"],
    "cantaloupe": ["dua hong"],
    "melon": ["dua le", "dua bo"],
    "pineapple": ["dua ta", "dua tay", "thom", "khom"],
    "papaya": ["du du chin"],
    "pear": ["le"],
    "pomegranate": ["luu"],
    "soursop": ["mang cau xiem"],
    "persimmon": ["hong do", "hong ngam"],
    "apricot": ["mo"],
    "jackfruit": ["mit dai", "mit mat", "mit kho"],
    "plum": ["man"],
}

AMOUNT_UNIT_TO_GRAMS = {
    "g": 1.0,
    "gram": 1.0,
    "grams": 1.0,
    "gr": 1.0,
    "kg": 1000.0,
    "ml": 1.0,
    "l": 1000.0,
    "tsp": 5.0,
    "tbsp": 15.0,
    "teaspoon": 5.0,
    "tablespoon": 15.0,
    "cup": 240.0,
}

SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "vietnamese_fruits_seed.json"


@lru_cache(maxsize=1)
def load_fruit_seed_index() -> dict[str, dict]:
    if not SEED_PATH.exists():
        return {}

    with SEED_PATH.open(encoding="utf-8") as file:
        rows = json.load(file)

    index: dict[str, dict] = {}
    for row in rows:
        names = {
            normalize_text(str(row.get("ingredient_name") or "")),
            normalize_text(str(row.get("title") or "")),
        }
        for canonical_name, alias_group in INGREDIENT_ALIASES.items():
            for alias in alias_group:
                alias_normalized = normalize_text(alias)
                if alias_normalized in names:
                    names.add(normalize_text(canonical_name))
                    names.update(normalize_text(item) for item in alias_group)
        nutrition = row.get("nutrition_per_100g") or {}
        normalized_nutrition = {
            "calories": float(nutrition.get("energy_kcal") or 0.0),
            "protein_g": float(nutrition.get("protein_g") or 0.0),
            "fiber_g": float(nutrition.get("fiber_g") or 0.0),
            "total_sugar_g": float(nutrition.get("total_sugar_g") or 0.0),
        }
        for name in names:
            if name:
                index[name] = {
                    "title": str(row.get("title") or row.get("ingredient_name") or ""),
                    "nutrition_per_100g": normalized_nutrition,
                }
    return index


class EvaluationService:
    def __init__(self) -> None:
        self.rule_service = ResearchRuleService()

    def evaluate_plan(
        self,
        profile: ProfileInput,
        plan: SmoothiePlanResponse,
    ) -> dict:
        estimate, ingredient_breakdown = self.estimate_plan_nutrition(plan)
        threshold_checks = self.evaluate_thresholds(estimate)
        safety_checks = self.evaluate_safety(profile, plan)
        evaluation_report = self.build_evaluation_report(
            ingredient_breakdown=ingredient_breakdown,
            threshold_checks=threshold_checks,
            safety_checks=safety_checks,
        )

        return {
            "estimated_nutrition": {
                key: round(value, 2)
                for key, value in estimate.__dict__.items()
            },
            "ingredient_breakdown": ingredient_breakdown,
            "threshold_checks": threshold_checks,
            "safety_checks": safety_checks,
            "evaluation_report": evaluation_report,
            "overall_pass": evaluation_report["decision"] == "pass",
        }

    def estimate_plan_nutrition(self, plan: SmoothiePlanResponse) -> tuple[NutrientEstimate, list[dict]]:
        total = NutrientEstimate()
        breakdown: list[dict] = []
        for ingredient in plan.ingredients:
            amount_grams = self.parse_amount_to_grams(ingredient.amount)
            nutrition_per_100g, source, matched_reference = self.lookup_ingredient_nutrition(ingredient.name)
            scaled_nutrition = self.scale_nutrition_for_amount(nutrition_per_100g, amount_grams)
            total.calories += scaled_nutrition.get("calories", 0.0)
            total.protein_g += scaled_nutrition.get("protein_g", 0.0)
            total.fiber_g += scaled_nutrition.get("fiber_g", 0.0)
            total.total_sugar_g += scaled_nutrition.get("total_sugar_g", 0.0)
            breakdown.append(
                {
                    "ingredient_name": ingredient.name,
                    "amount": ingredient.amount,
                    "estimated_amount_g": amount_grams,
                    "source": source,
                    "matched_reference": matched_reference,
                    "nutrition_per_100g": nutrition_per_100g,
                    "estimated_nutrition": scaled_nutrition,
                }
            )
        return total, breakdown

    def evaluate_thresholds(self, estimate: NutrientEstimate) -> list[dict]:
        rules = self.rule_service.load_threshold_rules()
        checks: list[dict] = []
        for rule in rules:
            value = getattr(estimate, rule.metric, None)
            passed = True
            if value is None:
                passed = False
            elif rule.min_value is not None and value < rule.min_value:
                passed = False
            elif rule.max_value is not None and value > rule.max_value:
                passed = False
            checks.append(
                {
                    "threshold_code": rule.threshold_code,
                    "metric": rule.metric,
                    "value": value,
                    "min_value": rule.min_value,
                    "max_value": rule.max_value,
                    "passed": passed,
                    "source": rule.source,
                }
            )
        return checks

    def build_evaluation_report(
        self,
        ingredient_breakdown: list[dict],
        threshold_checks: list[dict],
        safety_checks: list[dict],
    ) -> dict:
        issues: list[str] = []
        recommendations: list[str] = []
        failed_thresholds = [item for item in threshold_checks if not item["passed"]]
        triggered_safety = [item for item in safety_checks if item["triggered"]]
        critical_safety = [item for item in triggered_safety if item["severity"] == "critical"]
        high_safety = [item for item in triggered_safety if item["severity"] == "high"]
        unknown_ingredients = [
            item["ingredient_name"]
            for item in ingredient_breakdown
            if item["source"] == "unknown"
        ]
        unparsed_amounts = [
            item["ingredient_name"]
            for item in ingredient_breakdown
            if item["estimated_amount_g"] is None
        ]

        for item in failed_thresholds:
            issues.append(
                f"{item['metric']}={item['value']} outside rule {item['threshold_code']}."
            )
            recommendations.append(
                f"Adjust ingredients to satisfy {item['metric']} threshold {item['threshold_code']}."
            )

        for item in critical_safety:
            issues.append(f"Critical safety rule triggered: {item['rule_code']}.")
            recommendations.append(item["warning_message"])

        for item in high_safety:
            issues.append(f"High-priority safety note triggered: {item['rule_code']}.")
            recommendations.append(item["warning_message"])

        if unknown_ingredients:
            issues.append(
                "Nutrition data missing for: " + ", ".join(sorted(set(unknown_ingredients))) + "."
            )
            recommendations.append(
                "Add these ingredients to the nutrition data source before using the estimate as final."
            )

        if unparsed_amounts:
            issues.append(
                "Ingredient amount could not be parsed for: " + ", ".join(sorted(set(unparsed_amounts))) + "."
            )
            recommendations.append("Use explicit amounts such as 120 g, 200 ml, 1 tsp, or 1 tbsp.")

        score = 100
        score -= 15 * len(failed_thresholds)
        score -= 40 * len(critical_safety)
        score -= 10 * len(high_safety)
        score -= 5 * len(set(unknown_ingredients))
        score -= 5 * len(set(unparsed_amounts))
        score = max(0, min(100, score))

        if critical_safety or failed_thresholds:
            decision = "reject"
        elif high_safety or unknown_ingredients or unparsed_amounts:
            decision = "review"
        else:
            decision = "pass"

        known_ingredient_count = len(
            [item for item in ingredient_breakdown if item["source"] != "unknown"]
        )
        total_ingredient_count = len(ingredient_breakdown)
        data_coverage = 1.0
        if total_ingredient_count:
            data_coverage = round(known_ingredient_count / total_ingredient_count, 2)

        if not recommendations:
            recommendations.append("Recipe passes current automated nutrition and safety checks.")

        return {
            "score": score,
            "decision": decision,
            "data_coverage": data_coverage,
            "known_ingredient_count": known_ingredient_count,
            "total_ingredient_count": total_ingredient_count,
            "failed_threshold_count": len(failed_thresholds),
            "triggered_safety_count": len(triggered_safety),
            "issues": issues,
            "recommendations": recommendations,
        }

    def evaluate_safety(self, profile: ProfileInput, plan: SmoothiePlanResponse) -> list[dict]:
        rules = self.rule_service.load_safety_rules()
        normalized_ingredients = [normalize_text(item.name) for item in plan.ingredients]
        blocked_terms = set(expand_blocked_terms([*profile.allergies, *profile.disliked_ingredients]))
        checks: list[dict] = []

        for rule in rules:
            triggered = False
            if rule.condition_key == "medical_notes_present":
                triggered = bool(profile.medical_notes)
            else:
                rule_terms = [normalize_text(term) for term in rule.ingredient_or_nutrient.split(",")]
                triggered = any(term in ingredient for term in rule_terms for ingredient in normalized_ingredients)
                if rule.condition_key.endswith("_allergy"):
                    triggered = triggered and any(rule.condition_key.split("_allergy")[0] in term for term in blocked_terms)

            checks.append(
                {
                    "rule_code": rule.rule_code,
                    "condition_key": rule.condition_key,
                    "triggered": triggered,
                    "severity": rule.severity,
                    "action": rule.action,
                    "warning_message": rule.warning_message,
                    "source": rule.source,
                }
            )
        return checks

    def lookup_ingredient_nutrition(self, ingredient_name: str) -> tuple[dict[str, float], str, str | None]:
        normalized_name = normalize_text(ingredient_name)
        seed_index = load_fruit_seed_index()

        if normalized_name in seed_index:
            matched = seed_index[normalized_name]
            return matched["nutrition_per_100g"], "vietnamese_fruit_seed", matched["title"]

        for key, value in seed_index.items():
            if key and (key in normalized_name or normalized_name in key):
                return value["nutrition_per_100g"], "vietnamese_fruit_seed", value["title"]

        for key, value in FALLBACK_INGREDIENT_NUTRITION.items():
            if normalize_text(key) in normalized_name or normalized_name in normalize_text(key):
                return value, "fallback_internal_lookup", key
        return {}, "unknown", None

    def parse_amount_to_grams(self, amount_text: str) -> float | None:
        normalized = normalize_text(amount_text)
        match = re.search(r"(\d+(?:\.\d+)?)", normalized)
        if not match:
            return None

        value = float(match.group(1))
        for unit, multiplier in AMOUNT_UNIT_TO_GRAMS.items():
            if unit in normalized.split() or unit in normalized:
                return round(value * multiplier, 2)
        return round(value, 2)

    def scale_nutrition_for_amount(
        self,
        nutrition_per_100g: dict[str, float],
        amount_grams: float | None,
    ) -> dict[str, float]:
        if not nutrition_per_100g:
            return {}

        if amount_grams is None:
            return nutrition_per_100g

        factor = amount_grams / 100.0
        return {
            metric: round(value * factor, 2)
            for metric, value in nutrition_per_100g.items()
        }
