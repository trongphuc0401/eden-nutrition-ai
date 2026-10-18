"""Read the research reference data (ingredients, nutrients, seasons, allergens, thresholds, clinical safety rules,
profile classification rules) from Supabase.

The report pipeline asks for one immutable snapshot of the *current* dataset version. The snapshot is cached for
`reference_cache_seconds`; when the database is unreachable or holds too little data the caller gets `None` and
falls back to the bundled JSON seeds, so the API never goes down because of the reference tables.

REFERENCE_DATA_SOURCE: auto (default: DB when it qualifies, else JSON) | db (always DB) | json (never DB).
"""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings

logger = logging.getLogger(__name__)

# report nutrient key -> DB nutrient code
NUTRIENT_CODES = {
    "calories": "energy_kcal",
    "protein": "protein_g",
    "carbohydrate": "carbohydrate_g",
    "fat": "fat_g",
    "fiber": "fiber_g",
    "sugar": "total_sugar_g",
    "sodium": "sodium_mg",
}
REPORT_KEY_BY_CODE = {code: key for key, code in NUTRIENT_CODES.items()}
THRESHOLD_LABELS = {
    "calories": "Năng lượng", "protein": "Protein", "carbohydrate": "Carbohydrate", "fat": "Chất béo",
    "fiber": "Chất xơ", "sugar": "Đường tổng", "sodium": "Natri",
}
# condition codes -> allergen groups the report pipeline already understands
ALLERGEN_GROUPS = {"soy_allergy": "soy", "milk_allergy": "milk", "peanut_allergy": "peanut", "tree_nut_allergy": "tree_nuts"}
FAILURE_BACKOFF_SECONDS = 60.0


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower().replace("đ", "d"))
    ascii_value = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")


@dataclass(frozen=True)
class ReferenceSnapshot:
    source: str
    dataset_version: str | None
    ingredients: list[dict[str, Any]]
    thresholds: list[dict[str, Any]]
    condition_keywords: dict[str, list[str]] = field(default_factory=dict)
    condition_types: dict[str, str] = field(default_factory=dict)
    safety_rules: list[dict[str, Any]] = field(default_factory=list)
    profile_rules: list[dict[str, Any]] = field(default_factory=list)


_cache: tuple[float, ReferenceSnapshot | None] | None = None
_failed_until = 0.0
_lock = Lock()


def clear_cache() -> None:
    global _cache, _failed_until
    with _lock:
        _cache = None
        _failed_until = 0.0


def get_snapshot() -> ReferenceSnapshot | None:
    """Current DB snapshot, or None when the JSON fallback should be used."""
    global _cache, _failed_until
    mode = settings.reference_data_source.strip().lower()
    if mode == "json":
        return None
    now = monotonic()
    with _lock:
        if _cache and now - _cache[0] < settings.reference_cache_seconds:
            return _cache[1]
        if mode == "auto" and now < _failed_until:
            return None
        try:
            snapshot = _load_from_database()
        except SQLAlchemyError as error:
            if mode == "db":
                raise
            logger.warning("Reference data unavailable, using JSON fallback: %s", type(error).__name__)
            _failed_until = now + FAILURE_BACKOFF_SECONDS
            return None
        if mode == "auto" and not _qualifies(snapshot):
            logger.info("Reference data in DB is too sparse (%s usable ingredients); using JSON fallback",
                        sum(1 for item in snapshot.ingredients if item["usable"]))
            snapshot = None
        _cache = (now, snapshot)
        return snapshot


def _qualifies(snapshot: ReferenceSnapshot) -> bool:
    usable = sum(1 for item in snapshot.ingredients if item["usable"])
    return usable >= settings.reference_min_db_ingredients and bool(snapshot.thresholds)


def _load_from_database() -> ReferenceSnapshot:
    from app.database import engine

    with engine.connect() as conn:
        # the dataset version is only a label: the one written by the latest workbook import (no version table)
        version = conn.execute(text("""
            SELECT dataset_version_code FROM import_batches
             WHERE dataset_version_code IS NOT NULL ORDER BY imported_at DESC LIMIT 1""")).scalar()
        rows = conn.execute(text("""
            SELECT i.id, i.ingredient_code, i.name_vi, i.name_en, i.category, i.processing_state, i.allowed_for_smoothie,
                   i.data_status, i.growing_regions, i.primary_source_code,
                   s.title AS source_title, s.url_or_file AS source_url, s.reliability_level
              FROM ingredients i
              LEFT JOIN data_sources s ON s.source_code = i.primary_source_code
             ORDER BY i.ingredient_code""")).mappings().all()
        nutrients = conn.execute(text("""
            SELECT ingredient_id, nutrient_code, value_per_100g, needs_review
              FROM ingredient_nutrients
             WHERE nutrient_code = ANY(:codes) AND value_per_100g IS NOT NULL"""),
            {"codes": list(NUTRIENT_CODES.values())}).mappings().all()
        seasons = conn.execute(text(
            "SELECT ingredient_id, region_label, region_scope, months, year_round FROM ingredient_seasons")).mappings().all()
        # expert-rejected links are ignored; 'auto' links still block (safety first) but are reported as unverified
        conditions = conn.execute(text("""
            SELECT ingredient_id, condition_code, review_status FROM ingredient_conditions
             WHERE relation IN ('contains_allergen', 'should_avoid') AND review_status <> 'rejected'""")).mappings().all()
        aliases = conn.execute(text("SELECT ingredient_id, alias FROM ingredient_aliases")).mappings().all()
        keywords = conn.execute(text("""
            SELECT condition_code, keywords_vi, name_vi, condition_type FROM health_conditions WHERE is_active""")).mappings().all()
        # Rows seeded before the workbook columns existed only fill the original text fields.
        safety_rules = conn.execute(text("""
            SELECT rule_code, COALESCE(condition_code, condition_key) AS condition_code, target_type, nutrient_code,
                   COALESCE(target_text, ingredient_or_nutrient) AS target_text, avoid_or_limit, threshold_value, unit,
                   COALESCE(warning_message_vi, warning_message) AS warning_message_vi, severity,
                   COALESCE(recommended_action, action) AS recommended_action
              FROM clinical_safety_rules
             WHERE is_active AND (CAST(:v AS text) IS NULL OR dataset_version_code IS NULL OR dataset_version_code = :v)
             ORDER BY rule_code"""), {"v": version}).mappings().all()
        profile_rules = conn.execute(text("""
            SELECT rule_code, input_field, operator, min_value, max_value, classification_result, target_group, priority
              FROM profile_classification_rules
             WHERE is_active
             ORDER BY priority, rule_code""")).mappings().all()
        thresholds = conn.execute(text("""
            SELECT t.threshold_code, t.nutrient_code, t.min_value, t.max_value, t.unit, t.comparator, t.basis, t.meal_context,
                   t.target_group, t.source, t.priority
              FROM nutrition_thresholds t
             WHERE t.is_active AND t.nutrient_code = ANY(:codes)
               AND (CAST(:v AS text) IS NULL OR t.dataset_version_code IS NULL OR t.dataset_version_code = :v)
             ORDER BY t.priority, t.threshold_code"""),
            {"codes": list(NUTRIENT_CODES.values()), "v": version}).mappings().all()

    per_ingredient: dict[Any, dict[str, Any]] = {}
    for row in nutrients:
        bucket = per_ingredient.setdefault(row["ingredient_id"], {"values": {}, "review": []})
        key = REPORT_KEY_BY_CODE[row["nutrient_code"]]
        bucket["values"][key] = float(row["value_per_100g"])
        if row["needs_review"]:
            bucket["review"].append(key)
    months_by: dict[Any, set[int]] = {}
    scope_months_by: dict[Any, dict[str, set[int]]] = {}
    regions_by: dict[Any, list[str]] = {}
    for row in seasons:
        months = set(range(1, 13)) if row["year_round"] else set(row["months"] or [])
        months_by.setdefault(row["ingredient_id"], set()).update(months)
        scope = row.get("region_scope") or "all"
        if scope in ("north", "central", "south"):
            scope_months_by.setdefault(row["ingredient_id"], {}).setdefault(scope, set()).update(months)
        regions_by.setdefault(row["ingredient_id"], []).append(row["region_label"])
    conditions_by: dict[Any, list[str]] = {}
    unverified_by: dict[Any, list[str]] = {}
    for row in conditions:
        conditions_by.setdefault(row["ingredient_id"], []).append(row["condition_code"])
        if row["review_status"] != "verified":
            unverified_by.setdefault(row["ingredient_id"], []).append(row["condition_code"])
    aliases_by: dict[Any, list[str]] = {}
    for row in aliases:
        aliases_by.setdefault(row["ingredient_id"], []).append(row["alias"])

    items: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    for row in rows:
        data = per_ingredient.get(row["id"], {"values": {}, "review": []})
        per_100g = {key: data["values"].get(key) for key in NUTRIENT_CODES}
        known = sum(value is not None for value in per_100g.values())
        ingredient_id = slugify(row["name_vi"])
        if ingredient_id in used_ids:  # two rows with the same Vietnamese name
            ingredient_id = f"{ingredient_id}-{row['ingredient_code'].lower().replace('_', '-')}"
        used_ids.add(ingredient_id)
        verified = row["data_status"] == "verified" and bool(row["primary_source_code"])
        if verified and known == len(per_100g) and not data["review"]:
            confidence = "high"
        elif known >= 4:
            confidence = "medium" if verified else "low"
        else:
            confidence = "unknown"
        condition_codes = sorted(set(conditions_by.get(row["id"], [])))
        regions = list(dict.fromkeys([*regions_by.get(row["id"], []), *(row["growing_regions"] or [])]))
        items.append({
            "ingredient_id": ingredient_id,
            "ingredient_code": row["ingredient_code"],
            "name": row["name_vi"],
            "aliases": [row["ingredient_code"], *([row["name_en"]] if row["name_en"] else []), *aliases_by.get(row["id"], [])],
            "category": row["category"],
            "source": row["source_url"],
            "source_label": row["source_title"] or "Nguồn chưa được xác minh",
            "source_code": row["primary_source_code"],
            "source_region": "VN",
            "per_100g": per_100g,
            "nutrition_basis": "per_100g",
            "density_g_per_ml": None,
            "density_source": None,
            "source_verified": verified,
            "confidence": confidence,
            "data_status": row["data_status"],
            "needs_review_nutrients": data["review"],
            "allergen_groups": sorted({ALLERGEN_GROUPS.get(code, code) for code in condition_codes} | set(condition_codes)),
            "condition_codes": condition_codes,
            "unverified_condition_codes": sorted(set(unverified_by.get(row["id"], []))),
            "season_months": sorted(months_by.get(row["id"], set())),
            # months per climate zone (north / central / south) when the sheet says where the season applies
            "season_by_scope": {scope: sorted(months) for scope, months in scope_months_by.get(row["id"], {}).items()},
            "region": ", ".join(regions[:3]) if regions else None,
            "allowed_for_smoothie": bool(row["allowed_for_smoothie"]),
            "usable": bool(row["allowed_for_smoothie"]) and known >= 4,
        })

    report_thresholds = []
    seen_keys: set[tuple[str, str]] = set()
    for row in thresholds:
        key = REPORT_KEY_BY_CODE[row["nutrient_code"]]
        basis = row["basis"] or "absolute"
        if (key, basis) in seen_keys:  # one rule per nutrient and basis, highest priority wins
            continue
        seen_keys.add((key, basis))
        percent = basis == "percent_energy"
        report_thresholds.append({
            "code": row["threshold_code"],
            "nutrient": key,
            "label": THRESHOLD_LABELS[key] + (" (% năng lượng)" if percent else ""),
            "unit": "%" if percent else (row["unit"] or ""),
            "minimum": float(row["min_value"]) if row["min_value"] is not None else None,
            "maximum": float(row["max_value"]) if row["max_value"] is not None else None,
            "comparator": row["comparator"] or "between",
            "basis": basis,
            "source": row["source"],
        })

    return ReferenceSnapshot(
        source="supabase",
        dataset_version=version,
        ingredients=items,
        thresholds=report_thresholds,
        condition_keywords={row["condition_code"]: [*(row["keywords_vi"] or []), row["name_vi"]] for row in keywords},
        condition_types={row["condition_code"]: row["condition_type"] for row in keywords},
        safety_rules=[
            {**row, "threshold_value": float(row["threshold_value"]) if row["threshold_value"] is not None else None}
            for row in map(dict, safety_rules)
        ],
        profile_rules=[
            {**row, **{key: float(row[key]) if row[key] is not None else None for key in ("min_value", "max_value")}}
            for row in map(dict, profile_rules)
        ],
    )
