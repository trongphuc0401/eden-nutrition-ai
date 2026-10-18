"""Read-only checks against the real Supabase reference tables.

Opt-in so CI never depends on the shared database:  RUN_SUPABASE_TESTS=1 python -m pytest tests/test_reference_supabase.py
"""
from __future__ import annotations

import os

import pytest

from app.config import settings
from app.services import reference_repository
from app.services.recipe_generation_service import blocked_ingredient_ids
from app.services.report_data_service import load_ingredient_index, load_thresholds

pytestmark = pytest.mark.skipif(os.getenv("RUN_SUPABASE_TESTS") != "1", reason="set RUN_SUPABASE_TESTS=1 to hit Supabase")


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setattr(settings, "reference_data_source", "db")
    reference_repository.clear_cache()
    snapshot = reference_repository.get_snapshot()
    assert snapshot is not None
    return snapshot


def test_snapshot_reads_current_version_and_core_nutrients(live) -> None:
    assert live.dataset_version
    by_code = {item["ingredient_code"]: item for item in live.ingredients}
    pomelo = by_code["ING_FRUIT_0001"]
    assert pomelo["ingredient_id"] == "buoi"
    assert pomelo["per_100g"]["calories"] == 30.0
    assert set(pomelo["per_100g"]) == set(reference_repository.NUTRIENT_CODES)


def test_soy_milk_carries_allergen_and_review_flags(live) -> None:
    soy = next(item for item in live.ingredients if item["ingredient_code"] == "ING_FRUIT_0132")
    assert "soy_allergy" in soy["condition_codes"] and "soy" in soy["allergen_groups"]
    assert soy["needs_review_nutrients"]  # values rebuilt from Excel dates are flagged
    assert soy["source_verified"] is False  # data_status needs_review -> report stays in review
    assert "sua-dau-nanh" in blocked_ingredient_ids({"allergies": ["đậu nành"]})


def test_thresholds_come_from_new_columns_only(live) -> None:
    rules = load_thresholds()
    assert rules and all(rule["code"] for rule in rules)  # legacy rows without nutrient_code are skipped
    fat = next(rule for rule in rules if rule["nutrient"] == "fat")
    assert fat["basis"] == "percent_energy" and fat["unit"] == "%"


def test_index_merges_database_and_fallback(live) -> None:
    index = load_ingredient_index()
    assert index["buoi"]["source_label"] != "Nguồn chưa được xác minh"
    assert "yen-mach" in index
