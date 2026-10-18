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
from app.models.nutrition_knowledge import NutritionKnowledge
from app.services.vector_service import VectorService, ensure_pgvector_extension


DEFAULT_SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "vietnamese_fruits_seed.json"


def load_seed(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def import_seed(seed_path: Path, dry_run: bool, embed: bool) -> None:
    items = load_seed(seed_path)
    print(f"Loaded {len(items)} fruit records from {seed_path}.")

    if dry_run:
        smoothie_allowed = sum(1 for item in items if item["allowed_for_smoothie"])
        print(f"Dry run only. {smoothie_allowed}/{len(items)} records are allowed for smoothies.")
        print(f"Columns preserved per record: {items[0]['source_column_count'] if items else 0}")
        print("First record preview:")
        print(items[0]["content"])
        return

    vector_service = VectorService() if embed else None
    with SessionLocal() as db:
        ensure_pgvector_extension(db)
        inserted_or_updated = 0

        for item in items:
            existing = db.scalar(
                select(NutritionKnowledge).where(
                    NutritionKnowledge.ingredient_name == item["ingredient_name"],
                    NutritionKnowledge.source == item["source"],
                )
            )
            knowledge = existing or NutritionKnowledge()
            knowledge.title = item["title"]
            knowledge.ingredient_name = item["ingredient_name"]
            knowledge.category = item["category"]
            knowledge.origin_country = item["origin_country"]
            knowledge.region = item["region"] or None
            knowledge.season_months = item["season_months"]
            knowledge.allowed_for_smoothie = item["allowed_for_smoothie"]
            knowledge.content = item["content"]
            knowledge.source = item["source"]
            knowledge.tags = {
                "labels": [
                    "Vietnamese fruit",
                    "fruit data",
                    "smoothie ingredient",
                    f"stt:{item['stt']}",
                ],
                "source_sheet": item["source_sheet"],
                "source_range": item["source_range"],
                "source_row_number": item["source_row_number"],
                "source_column_count": item["source_column_count"],
                "raw_headers": item["raw_headers"],
                "raw_columns": item["raw_columns"],
                "raw_values": item["raw_values"],
                "nutrition_per_100g": item["nutrition_per_100g"],
            }
            db.add(knowledge)
            db.flush()

            if vector_service:
                knowledge.embedding = vector_service.create_embedding(knowledge.content)

            inserted_or_updated += 1

        db.commit()

    print(f"Imported {inserted_or_updated} fruit records into nutrition_knowledge.")
    if not embed:
        print("Embeddings were not created. Re-run with --embed after setting an embeddings provider key.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Vietnamese fruit data into nutrition_knowledge.")
    parser.add_argument("--seed-path", type=Path, default=DEFAULT_SEED_PATH)
    parser.add_argument("--dry-run", action="store_true", help="Load and preview the seed file without DB writes.")
    parser.add_argument("--embed", action="store_true", help="Create embeddings during import using the configured embeddings provider.")
    args = parser.parse_args()

    import_seed(seed_path=args.seed_path, dry_run=args.dry_run, embed=args.embed)


if __name__ == "__main__":
    main()
