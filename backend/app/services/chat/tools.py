"""Deterministic tools the chat agent uses. Every number in an answer comes from here, never from the LLM.

They read the same reference data as the report pipeline (Supabase snapshot or JSON fallback), so the chat and the
PDF report can never disagree about an ingredient.
"""
from __future__ import annotations

import difflib
import re
from datetime import datetime
from typing import Any

from app.services.clinical_rule_service import evaluate_safety_rules, match_condition_codes
from app.services.personalization_service import energy_plan, months_for, region_scope
from app.services.recipe_generation_service import blocked_ingredient_ids
from app.services.reference_import.catalog import CONDITIONS
from app.services.report_data_service import load_ingredient_index, reference_metadata, slugify

NUTRIENT_LABELS = {
    "calories": ("Năng lượng", "kcal"), "protein": ("Protein", "g"), "carbohydrate": ("Carbohydrate", "g"),
    "fat": ("Chất béo", "g"), "fiber": ("Chất xơ", "g"), "sugar": ("Đường tổng", "g"), "sodium": ("Natri", "mg"),
}
# words that never name an ingredient on their own (avoid "của" / "và" style false matches)
STOPWORDS = {"cua", "va", "hay", "voi", "cho", "toi", "minh", "co", "khong", "duoc", "la", "gi", "nao", "the", "nhu",
             "nen", "an", "uong", "bao", "nhieu", "trong", "mot", "ly", "qua", "trai", "rau", "hat", "cu", "sinh", "to",
             "tat", "ca", "cac", "nhung", "theo", "mua", "danh", "sach", "toan", "bo", "moi", "thu", "loai", "ban", "lap", "giup", "cung", "deu"}
REGION_LABELS = {"north": "miền Bắc", "central": "miền Trung", "south": "miền Nam"}


def _canonical() -> dict[str, dict[str, Any]]:
    # the item registered under its own id is the one the report pipeline resolves (Supabase before fallback)
    return {key: item for key, item in load_ingredient_index().items() if key == item["ingredient_id"]}


def find_ingredients(message: str, limit: int = 12) -> tuple[list[dict[str, Any]], list[str]]:
    """Ingredients named in a message: full names first ("sữa đậu nành"), then families ("chuối" -> chuối tây,
    chuối tiêu). Returns (items, unmatched_terms) where unmatched_terms are close-but-unknown words worth asking about."""
    text = f"-{slugify(message)}-"
    items = _canonical()
    names: list[tuple[str, str]] = []  # (slug, ingredient_id), longest first so "sua-dau-nanh" beats "sua"
    for ingredient_id, item in items.items():
        for name in {item["name"], *item.get("aliases", [])}:
            slug = slugify(str(name))
            if slug and not slug.startswith("ing-"):
                names.append((slug, ingredient_id))
    names.sort(key=lambda pair: -len(pair[0]))
    positions: dict[str, int] = {}  # ingredient_id -> where the user mentioned it, to answer in their order
    consumed = text
    for slug, ingredient_id in names:
        at = consumed.find(f"-{slug}-")
        if at >= 0 and ingredient_id not in positions:
            positions[ingredient_id] = at
            consumed = consumed.replace(f"-{slug}-", "-" + "#" * len(slug) + "-")
    # families: a bare word that starts several ingredient names ("chuoi" -> "chuoi-tay", "chuoi-tieu").
    # Accents decide between words that collide without them (dứa / dưa / đũa): when the user typed accents,
    # names whose first word matches exactly win over accent-free matches.
    typed = {slugify(word): word for word in re.findall(r"\w+", message.lower())}
    for token in [t for t in consumed.strip("-").split("-") if t and "#" not in t and t not in STOPWORDS and len(t) >= 2]:
        at = consumed.find(f"-{token}-")
        family = [(ingredient_id, items[ingredient_id]["name"].lower().split()[0]) for slug, ingredient_id in names
                  if slug.startswith(f"{token}-")]
        user_word = typed.get(token, "")
        exact = [ingredient_id for ingredient_id, first in family if first == user_word]
        has_accents = slugify(user_word) != user_word
        chosen = exact if has_accents else (exact or [ingredient_id for ingredient_id, _ in family])
        for ingredient_id in dict.fromkeys(chosen):
            if ingredient_id not in positions:
                positions[ingredient_id] = at
    found = sorted(positions, key=lambda ingredient_id: positions[ingredient_id])[:limit]
    tokens = [t for t in consumed.strip("-").split("-") if t and "#" not in t and t not in STOPWORDS and len(t) >= 3]
    vocabulary = sorted({token for slug, _ in names for token in slug.split("-")})
    unmatched = [t for t in tokens if difflib.get_close_matches(t, vocabulary, n=1, cutoff=0.8) and t not in vocabulary]
    return [items[ingredient_id] for ingredient_id in found], unmatched


def suggestions_for(term: str, limit: int = 3) -> list[str]:
    names = {item["name"]: slugify(item["name"]) for item in _canonical().values()}
    close = difflib.get_close_matches(slugify(term), list(names.values()), n=limit, cutoff=0.6)
    return [name for name, slug in names.items() if slug in close]


def seasonal_ingredients(month: int | None = None, hometown: str | None = None) -> list[dict[str, Any]]:
    m = month or datetime.now().month
    scope = region_scope(hometown)
    items = _canonical()
    in_season: list[dict[str, Any]] = []
    for item in items.values():
        months = months_for(item, scope)
        if months and m in months:
            in_season.append(item)
    return sorted(in_season, key=lambda it: (it.get("category") != "fruit", it["name"]))


def catalog_ingredients() -> list[dict[str, Any]]:
    items = _canonical()
    return sorted(items.values(), key=lambda it: (it.get("category") != "fruit", it["name"]))


def ingredient_facts(item: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, Any]:
    scope = region_scope((profile or {}).get("hometown"))
    months = months_for(item, scope)
    month = datetime.now().month
    per_100g = {key: item["per_100g"].get(key) for key in NUTRIENT_LABELS}
    return {
        "ingredient_id": item["ingredient_id"],
        "name": item["name"],
        "category": item.get("category", "fruit"),
        "per_100g": per_100g,
        "missing": [NUTRIENT_LABELS[key][0] for key, value in per_100g.items() if value is None],
        "needs_review": [NUTRIENT_LABELS[key][0] for key in item.get("needs_review_nutrients", []) if key in NUTRIENT_LABELS],
        "season_months": months,
        "in_season_now": (month in months) if months else None,
        "region": REGION_LABELS.get(scope or "", None),
        "allergens": [CONDITIONS[code][1] for code in item.get("condition_codes", []) if code in CONDITIONS],
        "source": item.get("source_label") or "Chưa có nguồn",
        "source_verified": bool(item.get("source_verified")),
        "confidence": item.get("confidence", "unknown"),
    }


def profile_check(items: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
    """What the user's profile says about these ingredients: allergy / dislike blocks and clinical warnings."""
    blocked = blocked_ingredient_ids(profile)
    dislikes = {slugify(str(term)) for term in [*profile.get("disliked_ingredients", []), *profile.get("dislikes", [])]}
    blocked_items = []
    for item in items:
        if item["ingredient_id"] not in blocked:
            continue
        name = slugify(item["name"])
        disliked = any(name == term or name.startswith(f"{term}-") for term in dislikes if term)
        blocked_items.append({"ingredient_id": item["ingredient_id"], "name": item["name"],
                              "reason": "không thích" if disliked else "dị ứng"})
    codes = match_condition_codes(list(profile.get("allergies", [])), str(profile.get("medical_notes") or ""))
    safety = evaluate_safety_rules(codes, items)
    return {
        "blocked": blocked_items,
        "condition_codes": codes,
        "rule_errors": safety["errors"],
        "rule_warnings": safety["warnings"],
        "energy_plan": energy_plan(profile),
    }


def catalog_ids(month: int | None = None, hometown: str | None = None) -> set[str]:
    """IDs the frontend can show in its picker (a report action may only use these)."""
    from app.services.frontend_service import build_ingredient_catalog

    return {row["id"] for row in build_ingredient_catalog(month, hometown)}


def data_context() -> dict[str, Any]:
    return reference_metadata()
