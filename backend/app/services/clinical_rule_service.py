"""Profile classification and clinical safety rules from the Supabase reference tables.

- classify_profile mirrors ai.classify_profile (migration 0005) over the cached profile_classification_rules.
- match_condition_codes maps free-text allergies / medical notes to health_conditions codes (whole-word slug match).
- evaluate_safety_rules applies clinical_safety_rules to a recipe: block_recipe -> error, warn_user -> warning,
  suggest_consult -> review. Nutrient-limit rules compare against the per-serving totals of calculate_nutrition.
In JSON fallback mode there are no rules: conditions and rule results are empty and BMI uses the >= 25 cut-off.
"""
from __future__ import annotations

import re
from typing import Any

from app.services.reference_import.catalog import CONDITION_EXCLUDES
from app.services.reference_repository import REPORT_KEY_BY_CODE
from app.services.report_data_service import (
    condition_keywords,
    condition_types,
    load_ingredient_index,
    load_profile_rules,
    load_safety_rules,
    slugify,
)

# classification_result values inside the research scope (overweight / obese adults)
IN_SCOPE_BMI_MARKERS = ("overweight", "obes", "thua-can", "beo-phi")
# nutrient names in a rule's target_text -> report nutrient key
NUTRIENT_TERMS = {
    "sugar": ("sugar", "sugars", "total-sugar", "duong", "duong-tong"),
    "sodium": ("sodium", "natri", "muoi", "salt"),
    "fat": ("fat", "chat-beo", "lipid"),
    "fiber": ("fiber", "chat-xo"),
    "protein": ("protein", "dam"),
    "carbohydrate": ("carbohydrate", "carb", "carbs", "glucid", "tinh-bot"),
    "calories": ("calories", "energy", "kcal", "nang-luong"),
}
UNIT_FACTORS = {"g": 1.0, "mg": 0.001, "mcg": 0.000001, "ug": 0.000001}
NUTRIENT_UNITS = {"sodium": "mg", "calories": "kcal"}  # every other report nutrient is in g


def _contains_words(haystack: str, needle: str) -> bool:
    return bool(needle) and f"-{needle}-" in f"-{haystack}-"


def classify_profile(age: float | None, height_cm: float | None, weight_kg: float | None,
                     rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts: dict[str, float] = {}
    if age:
        facts["age"] = float(age)
    if height_cm and weight_kg:
        facts["bmi"] = round(float(weight_kg) / ((float(height_cm) / 100) ** 2), 2)
    matches = []
    for rule in sorted(rules, key=lambda row: (row.get("priority") or 1, row["rule_code"])):
        value = facts.get(rule["input_field"])
        if value is None:
            continue
        low, high = rule.get("min_value"), rule.get("max_value")
        upper = high if high is not None else low
        hit = {
            "between": low is not None and high is not None and low <= value <= high,
            "gte": low is not None and value >= low,
            "gt": low is not None and value > low,
            "lte": upper is not None and value <= upper,
            "lt": upper is not None and value < upper,
            "equals": low is not None and value == low,
        }.get(rule["operator"], False)
        if hit:
            matches.append({"input_field": rule["input_field"], "classification_result": rule["classification_result"],
                            "rule_code": rule["rule_code"]})
    return matches


def bmi_in_scope(bmi: float, age: float | None, height_cm: float | None,
                 weight_kg: float | None) -> tuple[bool, list[dict[str, Any]]]:
    """Research scope: the DB classification decides (QĐ 2892/BYT: BMI 23-24.9 = overweight). Without a DB
    snapshot, or when no BMI rule covers the value, the original BMI >= 25 cut-off applies."""
    rules = load_profile_rules()
    classifications = classify_profile(age, height_cm, weight_kg, rules) if rules else []
    bmi_classes = [slugify(row["classification_result"]) for row in classifications if row["input_field"] == "bmi"]
    if bmi_classes:
        return any(marker in result for result in bmi_classes for marker in IN_SCOPE_BMI_MARKERS), classifications
    return bmi >= 25, classifications


def match_condition_codes(allergies: list[str], medical_notes: str) -> list[str]:
    """health_conditions codes for a profile. Allergy conditions match the allergy list on any keyword, but the
    free-text notes only on their full name ("dị ứng kiwi"): short allergen keywords are too ambiguous in prose."""
    keywords = condition_keywords()
    types = condition_types()
    allergy_terms = [slugify(str(term)) for term in allergies if str(term).strip()]
    notes = slugify(medical_notes or "")
    matched: list[str] = []
    for code, words in keywords.items():
        slugs = [slug for word in words if (slug := slugify(str(word)))]
        if not slugs:
            continue
        if types.get(code) == "allergy":
            hit = any(_contains_words(term, word) for term in allergy_terms for word in slugs)
            hit = hit or _contains_words(notes, slugs[-1])  # name_vi is appended last by the repository
        else:
            hit = any(_contains_words(text, word) for text in [notes, *allergy_terms] for word in slugs)
        if hit:
            matched.append(code)
    return matched


def _target_terms(target_text: str | None) -> list[str]:
    return [slug for part in re.split(r"[,;/\n]", target_text or "") if (slug := slugify(part))]


def _rule_nutrient(rule: dict[str, Any]) -> str | None:
    if rule.get("nutrient_code") in REPORT_KEY_BY_CODE:
        return REPORT_KEY_BY_CODE[rule["nutrient_code"]]
    if rule.get("target_type") != "nutrient" and rule.get("threshold_value") is None:
        return None
    target = slugify(rule.get("target_text") or "")
    for key, terms in NUTRIENT_TERMS.items():
        if any(_contains_words(target, term) for term in terms):
            return key
    return None


def _ingredient_matches(rule: dict[str, Any], ingredient: dict[str, Any]) -> bool:
    # condition_codes hold the ingredient_conditions links with relation contains_allergen / should_avoid
    if rule.get("condition_code") in ingredient.get("condition_codes", []):
        return True
    names = {slugify(ingredient.get("name") or ""), ingredient.get("ingredient_id") or ""}
    names.update(slugify(str(alias)) for alias in ingredient.get("aliases", []))
    names.discard("")
    # free-text matching would read "sữa" in "Sữa đậu nành" as dairy: plant milks etc. are excluded per condition
    excluded = [slugify(word) for word in CONDITION_EXCLUDES.get(rule.get("condition_code") or "", [])]
    if any(_contains_words(name, word) for name in names for word in excluded):
        return False
    return any(
        _contains_words(name, term) or (len(name) >= 4 and _contains_words(term, name))
        for term in _target_terms(rule.get("target_text")) for name in names
    )


def _in_rule_unit(value: float, nutrient: str, unit: str | None) -> float:
    rule_unit = (unit or "").strip().lower()
    base_unit = NUTRIENT_UNITS.get(nutrient, "g")
    if rule_unit in UNIT_FACTORS and base_unit in UNIT_FACTORS:
        return value * UNIT_FACTORS[base_unit] / UNIT_FACTORS[rule_unit]
    return value


def evaluate_safety_rules(condition_codes: list[str], ingredients: list[dict[str, Any]],
                          totals: dict[str, Any] | None = None, *, block_only: bool = False) -> dict[str, Any]:
    """Apply the active clinical_safety_rules of the matched conditions to a recipe.

    block_only checks just the block_recipe ingredient rules (used on the selected ingredients, before generation)."""
    result: dict[str, Any] = {"errors": [], "warnings": [], "review": False, "triggered": []}
    if not condition_codes:
        return result
    for rule in load_safety_rules():
        if rule.get("condition_code") not in condition_codes:
            continue
        action = (rule.get("recommended_action") or "warn_user").lower()
        if block_only and action != "block_recipe":
            continue
        message = rule.get("warning_message_vi") or f"Quy tắc an toàn {rule['rule_code']} được áp dụng."
        nutrient = _rule_nutrient(rule)
        hits: list[str] = []
        if nutrient is not None:
            if totals is None:
                continue
            value, limit = totals.get(nutrient), rule.get("threshold_value")
            if value is None or limit is None:
                result["warnings"].append(f"{message} (Chưa đủ dữ liệu để kiểm tra quy tắc {rule['rule_code']}.)")
                result["review"] = True
                result["triggered"].append({"rule_code": rule["rule_code"], "action": "review", "ingredients": []})
                continue
            per_serving = _in_rule_unit(float(value), nutrient, rule.get("unit"))
            if per_serving < limit:
                continue
            unit = rule.get("unit") or NUTRIENT_UNITS.get(nutrient, "g")
            detail = f"{message} (Mỗi khẩu phần: {round(per_serving, 2):g} {unit}; ngưỡng < {limit:g} {unit}.)"
        else:
            hits = sorted({item["name"] for item in ingredients if _ingredient_matches(rule, item)})
            has_target = bool(_target_terms(rule.get("target_text")))
            if not hits and (action == "block_recipe" or (action == "warn_user" and has_target)):
                continue
            detail = f"{message} ({', '.join(hits)})" if hits else message
        result["triggered"].append({"rule_code": rule["rule_code"], "action": action, "ingredients": hits})
        if action == "block_recipe":
            result["errors"].append(detail)
        else:
            result["warnings"].append(detail)
            result["review"] = result["review"] or action == "suggest_consult"
    result["errors"] = list(dict.fromkeys(result["errors"]))
    result["warnings"] = list(dict.fromkeys(result["warnings"]))
    return result


def clinically_blocked_ids(condition_codes: list[str]) -> set[str]:
    """Catalog ingredients a block_recipe rule forbids for these conditions, kept out of AI suggestions."""
    if not condition_codes or not load_safety_rules():
        return set()
    return {
        item["ingredient_id"] for item in load_ingredient_index().values()
        if evaluate_safety_rules(condition_codes, [item], block_only=True)["errors"]
    }
