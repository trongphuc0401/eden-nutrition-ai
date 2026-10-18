from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from app.services.reference_repository import ReferenceSnapshot, get_snapshot


APP_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
BACKEND_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
NUTRIENT_ALIASES = {
    "calories": ("calories", "energy_kcal", "energy", "kcal"),
    "protein": ("protein", "protein_g"),
    "carbohydrate": ("carbohydrate", "carbohydrate_g", "carb", "carbs", "glucid_g"),
    "fat": ("fat", "fat_g", "lipid_g", "lipid"),
    "fiber": ("fiber", "fiber_g", "dietary_fiber_g"),
    "sugar": ("sugar", "sugar_g", "total_sugar_g", "total_sugars_g"),
    "sodium": ("sodium", "sodium_mg"),
}


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower().replace("đ", "d"))
    ascii_value = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "ingredients", "fruits", "data", "records"):
            if isinstance(payload.get(key), list):
                return [item for item in payload[key] if isinstance(item, dict)]
    return []


def _first_number(record: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    pools = [record]
    for key in ("per_100g", "nutrition_per_100g", "nutrients", "nutrition", "normalized_nutrients"):
        if isinstance(record.get(key), dict):
            pools.append(record[key])
    for pool in pools:
        for key in keys:
            value = pool.get(key)
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                match = re.search(r"-?\d+(?:[.,]\d+)?", value)
                if match:
                    return float(match.group(0).replace(",", "."))
    return None


def _normalise_record(record: dict[str, Any], default_region: str) -> dict[str, Any] | None:
    name = str(record.get("name_vi") or record.get("vietnamese_name") or record.get("ingredient_name") or record.get("title") or record.get("name") or "").strip()
    if not name:
        return None
    ingredient_id = str(record.get("ingredient_id") or record.get("id") or slugify(name))
    per_100g = {key: _first_number(record, aliases) for key, aliases in NUTRIENT_ALIASES.items()}
    source = record.get("source") or record.get("source_url") or record.get("reference")
    source_label = record.get("source_label") or record.get("source_name")
    source_verified = bool(source and source_label)
    known_nutrients = sum(value is not None for value in per_100g.values())
    confidence = "high" if source_verified and known_nutrients == len(per_100g) else (
        "medium" if source_verified and known_nutrients >= 4 else "unknown"
    )
    allergen_groups = list(record.get("allergen_groups") or [])
    if ingredient_id == "sua-dau-nanh" and "soy" not in allergen_groups:
        allergen_groups.append("soy")
    return {
        "ingredient_id": ingredient_id,
        "name": name,
        "aliases": record.get("aliases") or [],
        "source": source,
        "source_label": str(source_label or "Nguồn chưa được xác minh"),
        "source_region": record.get("source_region") or default_region,
        "per_100g": per_100g,
        "nutrition_basis": record.get("nutrition_basis") or "per_100g",
        "density_g_per_ml": record.get("density_g_per_ml"),
        "density_source": record.get("density_source"),
        "source_verified": source_verified,
        "confidence": confidence,
        "allergen_groups": allergen_groups,
    }


def _fallback_records() -> list[dict[str, Any]]:
    fallback_path = APP_DATA_DIR / "report_nutrition_fallback.json"
    return [item for row in _records(_read_json(fallback_path)) if (item := _normalise_record(row, "international")) is not None]


def _index(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for item in candidates:
        keys = {item["ingredient_id"], slugify(item["name"])}
        keys.update(slugify(alias) for alias in item.get("aliases", []))
        for key in keys:
            index.setdefault(key, item)  # earlier sources win: Supabase / Vietnamese rows first.
    return index


def _database_index(snapshot: ReferenceSnapshot) -> dict[str, dict[str, Any]]:
    """Supabase rows first; the international fallback only fills ingredients the workbook lacks (oats, chia...).

    When both describe the same ingredient, Supabase nutrients win but the fallback's sourced ml->g density is kept,
    because the workbook has no density column.
    """
    fallback = {item["ingredient_id"]: item for item in _fallback_records()}
    db_items = []
    for item in snapshot.ingredients:
        if not item["allowed_for_smoothie"]:
            continue
        extra = fallback.get(item["ingredient_id"])
        if extra and extra.get("density_g_per_ml") is not None and item.get("density_g_per_ml") is None:
            item = {**item, "density_g_per_ml": extra["density_g_per_ml"], "density_source": extra.get("density_source")}
        db_items.append(item)
    return _index([*db_items, *fallback.values()])


def reference_metadata() -> dict[str, Any]:
    snapshot = get_snapshot()
    if snapshot is None:
        return {"data_source": "json", "dataset_version": None}
    return {"data_source": snapshot.source, "dataset_version": snapshot.dataset_version}


def load_ingredient_index() -> dict[str, dict[str, Any]]:
    snapshot = get_snapshot()
    if snapshot is not None:
        return _database_index(snapshot)
    candidates: list[dict[str, Any]] = []
    vietnamese_seed = BACKEND_DATA_DIR / "vietnamese_fruits_seed.json"
    if vietnamese_seed.exists():
        candidates.extend(
            item for row in _records(_read_json(vietnamese_seed))
            if (item := _normalise_record(row, "VN")) is not None
        )
    candidates.extend(_fallback_records())
    return _index(candidates)


def resolve_ingredients(ingredient_ids: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    index = load_ingredient_index()
    resolved: list[dict[str, Any]] = []
    unknown: list[str] = []
    for ingredient_id in ingredient_ids:
        item = index.get(ingredient_id) or index.get(slugify(ingredient_id))
        if item is None:
            unknown.append(ingredient_id)
            resolved.append({
                "ingredient_id": ingredient_id,
                "name": ingredient_id.replace("-", " ").title(),
                "aliases": [],
                "source": None,
                "source_label": "Chưa có nguồn dữ liệu",
                "source_region": "unknown",
                "per_100g": {key: None for key in NUTRIENT_ALIASES},
                "nutrition_basis": "unknown",
                "density_g_per_ml": None,
                "density_source": None,
                "source_verified": False,
                "confidence": "unknown",
                "allergen_groups": [],
            })
        else:
            resolved.append(dict(item))
    return resolved, unknown


def load_thresholds() -> list[dict[str, Any]]:
    snapshot = get_snapshot()
    if snapshot is not None:
        return [dict(rule) for rule in snapshot.thresholds]
    return _records(_read_json(APP_DATA_DIR / "report_thresholds.json"))


def condition_keywords() -> dict[str, list[str]]:
    snapshot = get_snapshot()
    return dict(snapshot.condition_keywords) if snapshot is not None else {}


def condition_types() -> dict[str, str]:
    snapshot = get_snapshot()
    return dict(snapshot.condition_types) if snapshot is not None else {}


def load_safety_rules() -> list[dict[str, Any]]:
    snapshot = get_snapshot()
    return [dict(rule) for rule in snapshot.safety_rules] if snapshot is not None else []


def load_profile_rules() -> list[dict[str, Any]] | None:
    """Supabase profile_classification_rules; None when the JSON fallback is active."""
    snapshot = get_snapshot()
    return [dict(rule) for rule in snapshot.profile_rules] if snapshot is not None else None
