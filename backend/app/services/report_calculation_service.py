from __future__ import annotations

from typing import Any

from app.services.report_data_service import load_thresholds


NUTRIENTS = ("calories", "protein", "carbohydrate", "fat", "fiber", "sugar", "sodium")
KCAL_PER_G = {"protein": 4, "carbohydrate": 4, "fat": 9}


def _threshold_value(totals: dict[str, float | None], key: str, basis: str) -> float | None:
    """Per-serving value a threshold is checked against; percent_energy = share of the serving's kcal."""
    value = totals.get(key)
    if basis != "percent_energy":
        return value
    calories = totals.get("calories")
    if value is None or not calories or key not in KCAL_PER_G:
        return None
    return round(value * KCAL_PER_G[key] / calories * 100, 1)


def _within(value: float, minimum: float | None, maximum: float | None, comparator: str | None) -> bool:
    if comparator == "gt":
        return minimum is None or value > minimum
    if comparator == "gte":
        return minimum is None or value >= minimum
    if comparator == "lt":
        return maximum is None or value < maximum
    if comparator == "lte":
        return maximum is None or value <= maximum
    return (minimum is None or value >= minimum) and (maximum is None or value <= maximum)


def ml_supported(ingredient: dict[str, Any]) -> bool:
    """ml can only be converted when the data is per 100 ml or a sourced density exists."""
    return ingredient.get("nutrition_basis") == "per_100ml" or (
        ingredient.get("density_g_per_ml") is not None and bool(ingredient.get("density_source"))
    )


def _is_liquid_base(ingredient: dict[str, Any]) -> bool:
    name = str(ingredient.get("name") or "").lower()
    return ingredient["ingredient_id"] == "sua-dau-nanh" or ingredient.get("category") in {"liquid", "dairy"} or name.startswith(("sữa", "nước"))


def default_amount(ingredient: dict[str, Any], count: int) -> tuple[float, str]:
    ingredient_id = ingredient["ingredient_id"]
    if _is_liquid_base(ingredient):
        # Without a sourced density, weigh the liquid instead of guessing ml -> g.
        return 200.0, "ml" if ml_supported(ingredient) else "g"
    if ingredient_id == "hat-chia":
        return 12.0, "g"
    if ingredient_id == "yen-mach":
        return 25.0, "g"
    return (120.0 if count <= 4 else 80.0), "g"


def build_recipe(ingredients: list[dict[str, Any]], servings: int, goal: str) -> dict[str, Any]:
    recipe_ingredients = []
    for ingredient in ingredients:
        amount, unit = default_amount(ingredient, len(ingredients))
        recipe_ingredients.append({**ingredient, "amount": amount * servings, "unit": unit})
    names = [item["name"] for item in ingredients]
    title = "Sinh tố " + " – ".join(names[:2])
    steps = [
        "Rửa sạch nguyên liệu tươi, để ráo và loại bỏ phần không ăn được.",
        "Cân đúng định lượng trong bảng; ngâm hạt hoặc yến mạch 10 phút nếu có.",
        "Cho nguyên liệu lỏng vào máy trước, sau đó thêm nguyên liệu còn lại.",
        "Xay 45–60 giây đến khi mịn; không thêm đường nếu chưa được chỉ định.",
        "Chia đúng số khẩu phần và dùng ngay sau khi chế biến.",
    ]
    return {
        "title": title[:90],
        "goal": goal[:180] or "Bổ sung dinh dưỡng cân bằng",
        "servings": servings,
        "ingredients": recipe_ingredients,
        "steps": steps[:6],
        "usage": "Dùng như bữa phụ, ưu tiên uống ngay sau khi xay. Không tự thay thế bữa chính hoặc phác đồ điều trị.",
        "substitutions": "Chỉ thay nguyên liệu bằng lựa chọn có dữ liệu dinh dưỡng và không xung đột dị ứng; tính lại report sau khi thay.",
    }


def calculate_nutrition(recipe: dict[str, Any], rules: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    servings = max(int(recipe.get("servings", 1)), 1)
    recipe_sums = {key: 0.0 for key in NUTRIENTS}
    missing_by_nutrient = {key: False for key in NUTRIENTS}
    ingredient_rows: list[dict[str, Any]] = []
    known_cells = 0
    all_cells = max(len(recipe["ingredients"]) * len(NUTRIENTS), 1)
    missing: list[str] = []
    assumptions: list[str] = []
    for ingredient in recipe["ingredients"]:
        amount = float(ingredient["amount"])
        unit = ingredient["unit"]
        amount_g: float | None = amount if unit == "g" else None
        if unit == "ml":
            if ingredient.get("nutrition_basis") == "per_100ml":
                factor = amount / 100.0
            elif ingredient.get("density_g_per_ml") is not None and ingredient.get("density_source"):
                amount_g = amount * float(ingredient["density_g_per_ml"])
                factor = amount_g / 100.0
                assumptions.append(
                    f"Quy đổi {ingredient['name']} theo mật độ có nguồn {ingredient['density_source']}."
                )
            else:
                factor = None
                missing.append(f"Thiếu dữ liệu quy đổi ml sang g có nguồn cho {ingredient['name']}")
        else:
            factor = amount / 100.0
        values: dict[str, float | None] = {}
        for nutrient in NUTRIENTS:
            source_value = ingredient["per_100g"].get(nutrient)
            if source_value is None or factor is None:
                values[nutrient] = None
                missing_by_nutrient[nutrient] = True
            else:
                values[nutrient] = float(source_value) * factor / servings
                recipe_sums[nutrient] += float(source_value) * factor
                known_cells += 1
        if any(value is None for value in values.values()):
            missing.append(f"Thiếu một phần dữ liệu cho {ingredient['name']}")
        ingredient_rows.append({
            "ingredient_id": ingredient["ingredient_id"],
            "name": ingredient["name"],
            "amount_g": round(amount_g / servings, 1) if amount_g is not None else None,
            "amount": round(amount / servings, 1),
            "unit": unit,
            "nutrition": {key: round(value, 2) if value is not None else None for key, value in values.items()},
            "source_label": ingredient["source_label"],
            "confidence": ingredient.get("confidence", "unknown"),
        })
    recipe_totals = {
        key: None if missing_by_nutrient[key] else round(value, 2)
        for key, value in recipe_sums.items()
    }
    rounded_totals = {
        key: None if value is None else round(value / servings, 2)
        for key, value in recipe_totals.items()
    }
    thresholds = []
    needs_review = bool(missing)
    for rule in (load_thresholds() if rules is None else rules):
        key = rule["nutrient"]
        value = _threshold_value(rounded_totals, key, rule.get("basis", "absolute"))
        minimum = rule.get("minimum")
        maximum = rule.get("maximum")
        passed = value is not None and _within(value, minimum, maximum, rule.get("comparator"))
        status = "pass" if passed else ("unknown" if value is None else "review")
        if status != "pass":
            needs_review = True
        unit = rule["unit"]
        low = minimum if minimum is not None and rule.get("comparator") not in ("lte", "lt") else None
        high = maximum if maximum is not None and rule.get("comparator") not in ("gte", "gt") else None
        if low is not None and high is not None:
            expected = f"nên từ {low:g} đến {high:g} {unit}"
        elif low is not None:
            expected = f"nên {'trên' if rule.get('comparator') == 'gt' else 'ít nhất'} {low:g} {unit}"
        elif high is not None:
            expected = f"nên {'dưới' if rule.get('comparator') == 'lt' else 'không quá'} {high:g} {unit}"
        else:
            expected = ""
        thresholds.append({
            "nutrient": rule.get("label", key),
            "value": value,
            "unit": rule["unit"],
            "minimum": minimum,
            "maximum": maximum,
            "status": status,
            # plain words for the report reader; the rule code stays in the reference data
            "message": "Đạt mức khuyến nghị" if passed
            else "Chưa có số liệu để đánh giá" if value is None
            else f"Nên xem lại: {expected}".rstrip(": "),
        })
    return {
        "totals": rounded_totals,
        "recipe_totals": recipe_totals,
        "ingredients": ingredient_rows,
        "thresholds": thresholds,
        "coverage": round(known_cells / all_cells, 3),
        "missing_data": list(dict.fromkeys(missing))[:5],
        "assumptions": list(dict.fromkeys(assumptions))[:5],
        "decision": "review" if needs_review else "pass",
    }
