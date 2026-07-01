import argparse
import json
from pathlib import Path
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import SessionLocal
from app.models.clinical_safety_rule import ClinicalSafetyRule
from app.models.nutrition_threshold import NutritionThreshold


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_THRESHOLD_PATH = DATA_DIR / "nutrition_thresholds_seed.json"
DEFAULT_SAFETY_PATH = DATA_DIR / "clinical_safety_rules_seed.json"


def load_json(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def import_thresholds(path: Path, dry_run: bool) -> int:
    rows = load_json(path)
    if dry_run:
        print(f"[dry-run] Loaded {len(rows)} threshold rules from {path}")
        return len(rows)

    with SessionLocal() as db:
        count = 0
        for row in rows:
            existing = db.scalar(
                select(NutritionThreshold).where(
                    NutritionThreshold.threshold_code == row["threshold_code"]
                )
            )
            record = existing or NutritionThreshold()
            record.threshold_code = row["threshold_code"]
            record.goal = row["goal"]
            record.metric = row["metric"]
            record.min_value = row["min_value"]
            record.max_value = row["max_value"]
            record.unit = row["unit"]
            record.meal_context = row.get("meal_context")
            record.pass_rule = row.get("pass_rule")
            record.source = row.get("source")
            record.notes = row.get("notes")
            record.priority = row.get("priority", 1)
            db.add(record)
            count += 1
        db.commit()
    print(f"Imported {count} threshold rules.")
    return count


def import_safety_rules(path: Path, dry_run: bool) -> int:
    rows = load_json(path)
    if dry_run:
        print(f"[dry-run] Loaded {len(rows)} safety rules from {path}")
        return len(rows)

    with SessionLocal() as db:
        count = 0
        for row in rows:
            existing = db.scalar(
                select(ClinicalSafetyRule).where(
                    ClinicalSafetyRule.rule_code == row["rule_code"]
                )
            )
            record = existing or ClinicalSafetyRule()
            record.rule_code = row["rule_code"]
            record.condition_key = row["condition_key"]
            record.risk_type = row["risk_type"]
            record.ingredient_or_nutrient = row["ingredient_or_nutrient"]
            record.action = row["action"]
            record.severity = row["severity"]
            record.threshold_value = row.get("threshold_value")
            record.unit = row.get("unit")
            record.warning_message = row["warning_message"]
            record.source = row.get("source")
            record.notes = row.get("notes")
            db.add(record)
            count += 1
        db.commit()
    print(f"Imported {count} clinical safety rules.")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Import fallback research rules into the database.")
    parser.add_argument("--threshold-path", type=Path, default=DEFAULT_THRESHOLD_PATH)
    parser.add_argument("--safety-path", type=Path, default=DEFAULT_SAFETY_PATH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    import_thresholds(args.threshold_path, dry_run=args.dry_run)
    import_safety_rules(args.safety_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
