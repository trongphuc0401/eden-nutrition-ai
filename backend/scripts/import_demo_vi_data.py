import argparse
import json
from pathlib import Path
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text

from app.database import Base, SessionLocal, engine
from app.models import ClinicalSafetyRule, NutritionKnowledge, NutritionThreshold  # noqa: F401
from app.models.clinical_safety_rule import ClinicalSafetyRule
from app.models.nutrition_threshold import NutritionThreshold
from app.services.vector_service import VectorService, ensure_pgvector_extension


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
KNOWLEDGE_PATH = DATA_DIR / "demo_knowledge_vi_seed.json"
THRESHOLD_PATH = DATA_DIR / "nutrition_thresholds_seed.json"
SAFETY_PATH = DATA_DIR / "clinical_safety_rules_seed.json"


def load_json(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def import_thresholds(rows: list[dict[str, Any]]) -> int:
    with SessionLocal() as db:
        count = 0
        for row in rows:
            record = db.scalar(
                select(NutritionThreshold).where(
                    NutritionThreshold.threshold_code == row["threshold_code"]
                )
            ) or NutritionThreshold()
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
    return count


def import_safety_rules(rows: list[dict[str, Any]]) -> int:
    with SessionLocal() as db:
        count = 0
        for row in rows:
            record = db.scalar(
                select(ClinicalSafetyRule).where(ClinicalSafetyRule.rule_code == row["rule_code"])
            ) or ClinicalSafetyRule()
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
    return count


def import_knowledge(rows: list[dict[str, Any]], embed: bool) -> tuple[int, int]:
    vector_service = VectorService() if embed else None
    embedded_count = 0

    with SessionLocal() as db:
        ensure_pgvector_extension(db)
        count = 0
        for row in rows:
            record = db.scalar(
                select(NutritionKnowledge).where(
                    NutritionKnowledge.ingredient_name == row["ingredient_name"],
                    NutritionKnowledge.source == row["source"],
                )
            ) or NutritionKnowledge()
            record.title = row["title"]
            record.ingredient_name = row["ingredient_name"]
            record.category = row["category"]
            record.origin_country = row.get("origin_country") or None
            record.region = row.get("region") or None
            record.season_months = row.get("season_months") or []
            record.allowed_for_smoothie = bool(row.get("allowed_for_smoothie", True))
            record.content = row["content"]
            record.source = row["source"]
            record.tags = {
                "labels": ["demo_vi", "frontend_ready", "rag_sample"],
                "knowledge_id": row["knowledge_id"],
                "ingredient_name_en": row.get("ingredient_name_en"),
                "nutrition_per_100g": row.get("nutrition_per_100g") or {},
                "data_quality_status": row.get("data_quality_status", "demo_only"),
                "notes": row.get("notes"),
            }
            db.add(record)
            db.flush()

            if vector_service:
                record.embedding = vector_service.create_embedding(row["content"])
                embedded_count += 1

            count += 1
        db.commit()

    return count, embedded_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Vietnamese demo data into PostgreSQL and pgvector.")
    parser.add_argument("--dry-run", action="store_true", help="Preview counts without writing to the database.")
    parser.add_argument("--skip-embeddings", action="store_true", help="Import knowledge without creating pgvector embeddings.")
    args = parser.parse_args()

    threshold_rows = load_json(THRESHOLD_PATH)
    safety_rows = load_json(SAFETY_PATH)
    knowledge_rows = load_json(KNOWLEDGE_PATH)

    print(
        {
            "threshold_rules": len(threshold_rows),
            "safety_rules": len(safety_rows),
            "knowledge_items": len(knowledge_rows),
            "embed": not args.skip_embeddings,
            "language": "vi",
        }
    )

    if args.dry_run:
        return

    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    print({"imported_threshold_rules": import_thresholds(threshold_rows)})
    print({"imported_safety_rules": import_safety_rules(safety_rows)})
    knowledge_count, embedded_count = import_knowledge(
        knowledge_rows,
        embed=not args.skip_embeddings,
    )
    print({"imported_knowledge_items": knowledge_count, "embedded_knowledge_items": embedded_count})


if __name__ == "__main__":
    main()
