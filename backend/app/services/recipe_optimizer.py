"""Deterministic gram/ml adjustment that pulls a recipe towards the active nutrition thresholds.

The ingredient set is fixed (the user picked it); only amounts move, inside the same bounds that
recipe_generation_service.validate_proposal enforces. Nothing is adjusted when any value needed by a
threshold is unknown: missing data must stay visible as missing, never be optimised around.
"""
from __future__ import annotations

from typing import Any

from app.services.report_calculation_service import KCAL_PER_G, _threshold_value, _within
from app.services.report_data_service import load_thresholds


MAX_AMOUNT = {"g": 400.0, "ml": 600.0}
MIN_AMOUNT = 5.0
# An ingredient may shrink to a quarter of the proposed amount at most, so "keep the ingredient"
# means something more than a 5 g token amount of a fruit the user chose.
MIN_SHARE_OF_ORIGINAL = 0.25
STEPS = (50.0, 20.0, 10.0, 5.0, 2.0, 1.0)
MAX_PASSES = 200


def amount_bounds(ingredient: dict[str, Any], original: float) -> tuple[float, float]:
    maximum = MAX_AMOUNT[ingredient["unit"]]
    minimum = min(original, max(MIN_AMOUNT, original * MIN_SHARE_OF_ORIGINAL))
    return minimum, max(maximum, minimum)


def _factor_per_unit(ingredient: dict[str, Any]) -> float | None:
    """Multiplier from one unit of amount to the per_100g values (mirrors calculate_nutrition)."""
    unit = ingredient.get("unit")
    if unit == "g":
        return 0.01
    if unit == "ml":
        if ingredient.get("nutrition_basis") == "per_100ml":
            return 0.01
        if ingredient.get("density_g_per_ml") is not None and ingredient.get("density_source"):
            return float(ingredient["density_g_per_ml"]) / 100.0
    return None


def _required_nutrients(thresholds: list[dict[str, Any]]) -> set[str]:
    required: set[str] = set()
    for rule in thresholds:
        required.add(rule["nutrient"])
        if rule.get("basis") == "percent_energy":
            required.add("calories")
    return required


def _violation(value: float | None, rule: dict[str, Any]) -> float:
    """0 when the rule passes, otherwise a normalised distance to the nearest bound (> 0)."""
    minimum, maximum, comparator = rule.get("minimum"), rule.get("maximum"), rule.get("comparator")
    if value is None:
        return float("inf")
    if _within(value, minimum, maximum, comparator):
        return 0.0
    if comparator in ("lt", "lte"):
        bound = maximum
    elif comparator in ("gt", "gte"):
        bound = minimum
    else:
        bound = minimum if minimum is not None and value < minimum else maximum
    # strict comparators fail exactly on the bound; keep a small positive distance there
    return max(abs(value - float(bound)) / max(abs(float(bound)), 1.0), 1e-6)


class _Evaluator:
    def __init__(self, ingredients: list[dict[str, Any]], servings: int, thresholds: list[dict[str, Any]]):
        self.thresholds = thresholds
        self.servings = max(int(servings), 1)
        nutrients = _required_nutrients(thresholds)
        self.nutrients = sorted(nutrients)
        self.rows: list[dict[str, float]] = []
        for ingredient in ingredients:
            factor = _factor_per_unit(ingredient)
            per_100g = ingredient.get("per_100g") or {}
            if factor is None or any(per_100g.get(key) is None for key in nutrients):
                raise ValueError(f"missing data for {ingredient.get('ingredient_id')}")
            self.rows.append({key: float(per_100g[key]) * factor for key in nutrients})

    def totals(self, amounts: list[float]) -> dict[str, float | None]:
        totals: dict[str, float | None] = {}
        for key in self.nutrients:
            recipe_total = round(sum(row[key] * amount for row, amount in zip(self.rows, amounts)), 2)
            totals[key] = round(recipe_total / self.servings, 2)
        return totals

    def violations(self, amounts: list[float]) -> list[float]:
        totals = self.totals(amounts)
        return [
            _violation(_threshold_value(totals, rule["nutrient"], rule.get("basis", "absolute")), rule)
            for rule in self.thresholds
        ]

    def score(self, amounts: list[float]) -> tuple[int, float]:
        violations = self.violations(amounts)
        return sum(1 for item in violations if item > 0), round(sum(violations), 9)


def optimize_amounts(recipe: dict[str, Any], thresholds: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Bounded coordinate search over ingredient amounts.

    Returns {"status": "improved" | "unchanged" | "skipped", "amounts": [...], "reason": ...}.
    "amounts" follows recipe["ingredients"] order and equals the input when nothing improved.
    """
    rules = [rule for rule in (thresholds if thresholds is not None else load_thresholds()) if rule.get("nutrient")]
    ingredients = recipe.get("ingredients", [])
    original = [float(item["amount"]) for item in ingredients]
    if not ingredients or not rules:
        return {"status": "skipped", "amounts": original, "reason": "nothing_to_adjust"}
    if any(item.get("unit") not in MAX_AMOUNT for item in ingredients):
        return {"status": "skipped", "amounts": original, "reason": "unsupported_unit"}
    if any(rule.get("basis") == "percent_energy" and rule["nutrient"] not in KCAL_PER_G for rule in rules):
        return {"status": "skipped", "amounts": original, "reason": "unsupported_threshold"}
    try:
        evaluator = _Evaluator(ingredients, int(recipe.get("servings", 1)), rules)
    except ValueError:
        return {"status": "skipped", "amounts": original, "reason": "missing_data"}

    bounds = [amount_bounds(item, amount) for item, amount in zip(ingredients, original)]
    # Start from the proposal, clamped into bounds (a proposal is already validated, so normally a no-op).
    amounts = [min(max(amount, low), high) for amount, (low, high) in zip(original, bounds)]
    best = evaluator.score(amounts)
    passes = 0
    for step in STEPS:
        improved = True
        while improved and best[0] > 0 and passes < MAX_PASSES:
            improved = False
            passes += 1
            for index, (low, high) in enumerate(bounds):
                for direction in (1.0, -1.0):
                    candidate = list(amounts)
                    candidate[index] = round(min(max(amounts[index] + direction * step, low), high), 1)
                    if candidate[index] == amounts[index]:
                        continue
                    score = evaluator.score(candidate)
                    if score < best:
                        amounts, best = candidate, score
                        improved = True

    start = evaluator.score(original)
    if best >= start:
        return {"status": "unchanged", "amounts": original, "reason": "no_improvement"}
    return {"status": "improved", "amounts": amounts, "reason": None, "violations": best[0]}
