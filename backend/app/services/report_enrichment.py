"""Extra report data for the personalised report view: profile snapshot, scores, allergen check, seasons,
structured prep steps, reference ranges and consistency checks. Everything here is derived from data the
pipeline already has; nothing is invented by the LLM."""
from __future__ import annotations

import re
from typing import Any

# Chính vụ / có quanh năm / trái vụ. Ingredients without a season calendar are left out of the score.
SEASON_POINTS = {"in_season": 100, "year_round": 80, "out_of_season": 20}
NON_SEASONAL_CATEGORIES = {"liquid", "dairy", "seed", "sweetener", "grain", "other", "protein"}

# AMDR share of energy (IOM 2005, also used by WHO): carbs 45-65 %, fat 20-35 %.
ENERGY_SHARE_RANGES = {"carbohydrate": (0.45, 0.65, 4), "fat": (0.20, 0.35, 9)}
ATWATER_TOLERANCE = 0.2

STEP_KINDS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("wash", "Rửa sạch", ("rửa", "ngâm nước muối")),
    ("peel", "Tách vỏ", ("gọt", "bóc", "tách vỏ", "bỏ vỏ", "lột")),
    ("cut", "Cắt nhỏ", ("cắt", "thái", "băm")),
    ("soak", "Ngâm", ("ngâm",)),
    ("weigh", "Cân định lượng", ("cân đúng", "cân định lượng", "cân nguyên liệu", "đong")),
    ("add", "Cho vào máy", ("vào máy", "vào cối")),
    ("blend", "Xay nhuyễn", ("xay",)),
    ("rest", "Để nghỉ", ("để nghỉ", "để lạnh", "ủ lạnh")),
    ("pour", "Rót ra ly", ("rót", "đổ ra", "chia đều", "chia đúng", "chia ra", "chia vào", "dùng ngay")),
)

_DURATION = re.compile(r"(\d+(?:[.,]\d+)?)(?:\s*[–-]\s*(\d+(?:[.,]\d+)?))?\s*(phút|giây)", re.IGNORECASE)


def bmi_category(bmi: float | None, classifications: list[dict[str, Any]] | None = None) -> str | None:
    """DB classification first; otherwise QĐ 2892/QĐ-BYT (Asian cut-offs)."""
    for row in classifications or []:
        if row.get("input_field") == "bmi" and row.get("classification_result"):
            return str(row["classification_result"])
    if not bmi:
        return None
    if bmi >= 30:
        return "Béo phì độ II (ngưỡng châu Á)"
    if bmi >= 25:
        return "Béo phì độ I (ngưỡng châu Á)"
    if bmi >= 23:
        return "Thừa cân (ngưỡng châu Á)"
    if bmi >= 18.5:
        return "Bình thường (ngưỡng châu Á)"
    return "Thiếu cân"


def _terms(value: Any) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]
    if isinstance(value, list):
        return [str(part).strip() for part in value if str(part).strip()]
    return []


def profile_snapshot(profile: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    bmi = analysis.get("bmi") or None
    age = profile.get("age")
    return {
        "gender": str(profile.get("gender") or "") or None,
        "age": int(float(age)) if age else None,
        "bmi": bmi,
        "bmi_category": bmi_category(bmi, analysis.get("classifications")),
        "allergies": _terms(profile.get("allergies"))[:8],
        "preferences": _terms(profile.get("preferred_food_types") or profile.get("preferences"))[:8],
        "dislikes": _terms(profile.get("disliked_ingredients") or profile.get("dislikes"))[:8],
    }


def ingredient_season(ingredient: dict[str, Any], month: int) -> dict[str, Any]:
    months = sorted({int(m) for m in ingredient.get("season_months") or [] if 1 <= int(m) <= 12})
    if len(months) == 12:
        status = "year_round"
    elif months:
        status = "in_season" if month in months else "out_of_season"
    elif str(ingredient.get("category") or "") in NON_SEASONAL_CATEGORIES:
        status = "not_seasonal"
    else:
        status = "unknown"
    return {"status": status, "months": months}


def seasonal_score(rows: list[tuple[float, str]]) -> int | None:
    """Weighted by amount; ingredients without a season calendar do not count."""
    scored = [(amount, SEASON_POINTS[status]) for amount, status in rows if status in SEASON_POINTS and amount > 0]
    total = sum(amount for amount, _ in scored)
    if not total:
        return None
    return round(sum(amount * points for amount, points in scored) / total)


def allergen_check(allergies: list[str], ingredients: list[dict[str, Any]], allergy_blocked_ids: set[str]) -> dict[str, Any]:
    """allergy_blocked_ids = ingredients blocked by the allergy list only (dislikes are not allergies)."""
    conflicts = [item["name"] for item in ingredients if item["ingredient_id"] in allergy_blocked_ids]
    return {"checked": allergies[:8], "conflicts": conflicts[:8], "checked_ingredients": len(ingredients)}


def personal_fit_score(
    thresholds: list[dict[str, Any]],
    conflicts: int,
    coverage: float,
    calories: float | None,
    plan: dict[str, Any] | None,
) -> dict[str, Any]:
    breakdown: list[dict[str, Any]] = []
    for item in thresholds:
        if item["status"] == "review":
            breakdown.append({"label": f"{item['nutrient']} ngoài ngưỡng", "points": -15})
        elif item["status"] == "unknown":
            breakdown.append({"label": f"{item['nutrient']} thiếu dữ liệu", "points": -5})
    if conflicts:
        breakdown.append({"label": "Xung đột dị ứng", "points": -40 * conflicts})
    if plan and calories is not None and not plan["smoothie_kcal_min"] <= calories <= plan["smoothie_kcal_max"]:
        breakdown.append({"label": "Năng lượng ngoài mục tiêu cá nhân", "points": -10})
    gap = round((1 - coverage) * 20)
    if gap:
        breakdown.append({"label": "Độ phủ dữ liệu chưa đủ", "points": -gap})
    value = max(0, min(100, 100 + sum(row["points"] for row in breakdown)))
    return {"value": value, "breakdown": breakdown}


def reference_ranges(totals: dict[str, float | None], plan: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Display ranges for nutrients the research thresholds do not bound on both sides."""
    ranges: list[dict[str, Any]] = []
    if plan:
        ranges.append({
            "nutrient": "calories", "unit": "kcal",
            "minimum": plan["smoothie_kcal_min"], "maximum": plan["smoothie_kcal_max"],
            "basis": "Mục tiêu cá nhân: 10–15% năng lượng ngày (Mifflin-St Jeor, TDEE − 500 kcal)",
        })
    calories = totals.get("calories")
    if calories:
        for nutrient, (low, high, kcal_per_g) in ENERGY_SHARE_RANGES.items():
            ranges.append({
                "nutrient": nutrient, "unit": "g",
                "minimum": round(calories * low / kcal_per_g, 1),
                "maximum": round(calories * high / kcal_per_g, 1),
                "basis": f"{low * 100:.0f}–{high * 100:.0f}% năng lượng của ly (AMDR, IOM)",
            })
    return ranges


def consistency_checks(totals: dict[str, float | None]) -> list[str]:
    issues: list[str] = []
    carbs, sugar = totals.get("carbohydrate"), totals.get("sugar")
    if carbs is not None and sugar is not None and sugar > carbs + 0.5:
        issues.append(f"Đường tổng ({sugar:g} g) lớn hơn tinh bột/carb ({carbs:g} g): dữ liệu nguồn cần kiểm tra.")
    protein, fat, calories = totals.get("protein"), totals.get("fat"), totals.get("calories")
    if None not in (protein, carbs, fat) and calories:
        estimated = 4 * protein + 4 * carbs + 9 * fat
        if abs(estimated - calories) / calories > ATWATER_TOLERANCE:
            issues.append(
                f"Năng lượng tính từ đạm/carb/béo ({estimated:.0f} kcal) lệch hơn 20% so với tổng kcal ({calories:.0f})."
            )
    return issues


def _step_minutes(text: str) -> float | None:
    match = _DURATION.search(text)
    if not match:
        return None
    high = float((match.group(2) or match.group(1)).replace(",", "."))
    return round(high / 60, 1) if match.group(3).lower() == "giây" else high


def structured_steps(steps: list[str]) -> list[dict[str, Any]]:
    rows = []
    for text in steps[:6]:
        lower = text.lower()
        # the keyword that appears first decides the step type ("Cân ...; ngâm hạt" is a weighing step)
        hits = [
            (position, candidate, label)
            for candidate, label, words in STEP_KINDS
            for word in words
            if (position := lower.find(word)) >= 0
        ]
        if hits:
            _, kind, title = min(hits)
        else:
            kind, title = "other", text.split(",")[0].split(";")[0].strip()[:40]
        rows.append({"title": title, "detail": text, "minutes": _step_minutes(text), "kind": kind})
    return rows


def serving_ml(ingredients: list[dict[str, Any]], servings: int) -> int | None:
    """Rough blended volume: ml as is, grams of produce ~1 ml/g. Shown with '≈' in the UI."""
    total = sum(float(item["amount"]) for item in ingredients if item.get("amount"))
    if not total:
        return None
    return int(round(total / max(servings, 1) / 10) * 10)


MILK_ALLERGY_TERMS = ("sữa bò", "sua bo", "sữa", "milk", "dairy", "lactose")


def substitution_for(ingredient: dict[str, Any], allergies: list[str]) -> str | None:
    """Tag a plant milk as the stand-in for cow's milk when the profile is allergic to milk."""
    name = str(ingredient.get("name") or "").lower()
    plant_milk = name.startswith("sữa") and "bò" not in name
    milk_allergy = any(term in allergy.lower() for allergy in allergies for term in MILK_ALLERGY_TERMS)
    return "sữa bò" if plant_milk and milk_allergy else None
