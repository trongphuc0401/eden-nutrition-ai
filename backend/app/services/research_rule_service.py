import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from time import monotonic

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.clinical_safety_rule import ClinicalSafetyRule
from app.models.nutrition_threshold import NutritionThreshold


@dataclass
class ThresholdRule:
    threshold_code: str
    metric: str
    min_value: float | None
    max_value: float | None
    unit: str
    pass_rule: str
    source: str


@dataclass
class SafetyRule:
    rule_code: str
    condition_key: str
    ingredient_or_nutrient: str
    action: str
    severity: str
    warning_message: str
    source: str


DEFAULT_THRESHOLDS = [
    ThresholdRule("THR_CAL_001", "calories", 110.0, 300.0, "kcal", "between", "fallback_internal_rule"),
    ThresholdRule("THR_PROTEIN_001", "protein_g", 8.0, None, "g", "min_only", "fallback_internal_rule"),
    ThresholdRule("THR_FIBER_001", "fiber_g", 4.0, None, "g", "min_only", "fallback_internal_rule"),
    ThresholdRule("THR_SUGAR_001", "total_sugar_g", None, 25.0, "g", "max_only", "fallback_internal_rule"),
]

DEFAULT_SAFETY_RULES = [
    SafetyRule(
        "SAFE_ALLERGY_MILK",
        "milk_allergy",
        "milk,yogurt,whey",
        "block_recipe",
        "critical",
        "Nguoi dung di ung sua can tranh sua, sua chua va whey.",
        "fallback_internal_rule",
    ),
    SafetyRule(
        "SAFE_MEDICAL_GENERIC",
        "medical_notes_present",
        "clinical_consult",
        "warn_user",
        "high",
        "Nguoi dung co ghi chu suc khoe, can xem xet tu van chuyen gia truoc khi ap dung.",
        "fallback_internal_rule",
    ),
]

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
THRESHOLD_SEED_PATH = DATA_DIR / "nutrition_thresholds_seed.json"
SAFETY_SEED_PATH = DATA_DIR / "clinical_safety_rules_seed.json"
DB_FAILURE_BACKOFF_SECONDS = 30.0


@lru_cache(maxsize=1)
def load_threshold_seed_rules() -> tuple[ThresholdRule, ...]:
    if not THRESHOLD_SEED_PATH.exists():
        return tuple(DEFAULT_THRESHOLDS)
    with THRESHOLD_SEED_PATH.open(encoding="utf-8") as file:
        rows = json.load(file)
    return tuple(
        ThresholdRule(
            threshold_code=row["threshold_code"],
            metric=row["metric"],
            min_value=row.get("min_value"),
            max_value=row.get("max_value"),
            unit=row["unit"],
            pass_rule=row.get("pass_rule", "custom"),
            source=row.get("source", "seed_json"),
        )
        for row in rows
    )


@lru_cache(maxsize=1)
def load_safety_seed_rules() -> tuple[SafetyRule, ...]:
    if not SAFETY_SEED_PATH.exists():
        return tuple(DEFAULT_SAFETY_RULES)
    with SAFETY_SEED_PATH.open(encoding="utf-8") as file:
        rows = json.load(file)
    return tuple(
        SafetyRule(
            rule_code=row["rule_code"],
            condition_key=row["condition_key"],
            ingredient_or_nutrient=row["ingredient_or_nutrient"],
            action=row["action"],
            severity=row["severity"],
            warning_message=row["warning_message"],
            source=row.get("source", "seed_json"),
        )
        for row in rows
    )


class ResearchRuleService:
    _db_unavailable_until = 0.0

    def load_threshold_seed_rules(self) -> list[ThresholdRule]:
        return list(load_threshold_seed_rules())

    def load_safety_seed_rules(self) -> list[SafetyRule]:
        return list(load_safety_seed_rules())

    @classmethod
    def _can_attempt_database(cls) -> bool:
        return monotonic() >= cls._db_unavailable_until

    @classmethod
    def _mark_database_unavailable(cls) -> None:
        cls._db_unavailable_until = monotonic() + DB_FAILURE_BACKOFF_SECONDS

    def load_threshold_rules(self) -> list[ThresholdRule]:
        if not self._can_attempt_database():
            return self.load_threshold_seed_rules()

        try:
            from app.database import SessionLocal

            with SessionLocal() as db:
                rows = list(db.scalars(select(NutritionThreshold)).all())
            if not rows:
                return self.load_threshold_seed_rules()
            return [
                ThresholdRule(
                    threshold_code=row.threshold_code,
                    metric=row.metric,
                    min_value=row.min_value,
                    max_value=row.max_value,
                    unit=row.unit,
                    pass_rule=row.pass_rule or "custom",
                    source=row.source or "database",
                )
                for row in rows
            ]
        except SQLAlchemyError:
            self._mark_database_unavailable()
            return self.load_threshold_seed_rules()

    def load_safety_rules(self) -> list[SafetyRule]:
        if not self._can_attempt_database():
            return self.load_safety_seed_rules()

        try:
            from app.database import SessionLocal

            with SessionLocal() as db:
                rows = list(db.scalars(select(ClinicalSafetyRule)).all())
            if not rows:
                return self.load_safety_seed_rules()
            return [
                SafetyRule(
                    rule_code=row.rule_code,
                    condition_key=row.condition_key,
                    ingredient_or_nutrient=row.ingredient_or_nutrient,
                    action=row.action,
                    severity=row.severity,
                    warning_message=row.warning_message,
                    source=row.source or "database",
                )
                for row in rows
            ]
        except SQLAlchemyError:
            self._mark_database_unavailable()
            return self.load_safety_seed_rules()

    def preview_rules(self) -> dict[str, list[dict]]:
        return {
            "thresholds": [
                {
                    "threshold_code": rule.threshold_code,
                    "metric": rule.metric,
                    "min_value": rule.min_value,
                    "max_value": rule.max_value,
                    "unit": rule.unit,
                    "pass_rule": rule.pass_rule,
                    "source": rule.source,
                }
                for rule in self.load_threshold_rules()
            ],
            "clinical_safety_rules": [
                {
                    "rule_code": rule.rule_code,
                    "condition_key": rule.condition_key,
                    "ingredient_or_nutrient": rule.ingredient_or_nutrient,
                    "action": rule.action,
                    "severity": rule.severity,
                    "warning_message": rule.warning_message,
                    "source": rule.source,
                }
                for rule in self.load_safety_rules()
            ],
        }

    def active_rule_sources(self) -> dict[str, str]:
        thresholds = self.load_threshold_rules()
        safety_rules = self.load_safety_rules()
        return {
            "threshold_source": thresholds[0].source if thresholds else "none",
            "safety_source": safety_rules[0].source if safety_rules else "none",
        }
