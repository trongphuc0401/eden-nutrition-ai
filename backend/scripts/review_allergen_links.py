"""Expert review of ingredient -> allergen/condition links (ingredient_conditions).

  python scripts/review_allergen_links.py export allergen_links.csv
      -> one row per link; fill the `decision` column with verified / rejected (or add new rows with decision=add)
  python scripts/review_allergen_links.py apply allergen_links.csv --reviewer "BS. Tran" --dry-run
  python scripts/review_allergen_links.py apply allergen_links.csv --reviewer "BS. Tran"

Decisions are stored in review_status and survive later workbook imports; 'rejected' links stop blocking recipes.
"""
import argparse
import csv
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402
from app.services.reference_repository import clear_cache  # noqa: E402

COLUMNS = ["ingredient_code", "name_vi", "condition_code", "condition_name", "relation", "review_status", "reviewed_by", "decision", "note"]
DECISIONS = {"verified", "rejected", "add"}


def export(path: Path) -> None:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT i.ingredient_code, i.name_vi, c.condition_code, h.name_vi AS condition_name, c.relation,
                   c.review_status, c.reviewed_by
              FROM ingredient_conditions c
              JOIN ingredients i ON i.id = c.ingredient_id
              JOIN health_conditions h ON h.condition_code = c.condition_code
             ORDER BY c.review_status, h.condition_code, i.ingredient_code""")).mappings().all()
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "decision": "", "note": ""})
    print(f"Exported {len(rows)} links to {path} ({sum(r['review_status'] == 'auto' for r in rows)} still unreviewed).")


def apply(path: Path, reviewer: str, dry_run: bool) -> None:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if (r.get("decision") or "").strip()]
    bad = [r for r in rows if r["decision"].strip().lower() not in DECISIONS]
    if bad:
        raise SystemExit(f"Unknown decision in {len(bad)} rows (allowed: {', '.join(sorted(DECISIONS))}).")
    counts = {"verified": 0, "rejected": 0, "add": 0, "missing": 0}
    with engine.begin() as conn:
        for r in rows:
            decision = r["decision"].strip().lower()
            ingredient_id = conn.execute(text("SELECT id FROM ingredients WHERE ingredient_code = :c"), {"c": r["ingredient_code"].strip()}).scalar()
            known_condition = conn.execute(text("SELECT 1 FROM health_conditions WHERE condition_code = :c"), {"c": r["condition_code"].strip()}).scalar()
            if ingredient_id is None or not known_condition:
                counts["missing"] += 1
                print(f"  skip: unknown ingredient/condition {r['ingredient_code']} / {r['condition_code']}")
                continue
            params = {"i": ingredient_id, "c": r["condition_code"].strip(), "r": (r.get("relation") or "contains_allergen").strip(),
                      "s": "verified" if decision == "add" else decision, "by": reviewer, "n": (r.get("note") or "").strip() or None}
            conn.execute(text("""
                INSERT INTO ingredient_conditions (ingredient_id, condition_code, relation, notes, review_status, reviewed_by, reviewed_at)
                VALUES (:i, :c, :r, :n, :s, :by, NOW())
                ON CONFLICT (ingredient_id, condition_code, relation) DO UPDATE SET review_status = EXCLUDED.review_status,
                  reviewed_by = EXCLUDED.reviewed_by, reviewed_at = NOW(), notes = COALESCE(EXCLUDED.notes, ingredient_conditions.notes)"""), params)
            counts[decision] += 1
        if dry_run:
            conn.rollback()
    clear_cache()
    print(f"{'Dry run - would apply' if dry_run else 'Applied'}: {counts}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    exp = sub.add_parser("export")
    exp.add_argument("csv", type=Path)
    app = sub.add_parser("apply")
    app.add_argument("csv", type=Path)
    app.add_argument("--reviewer", required=True)
    app.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.command == "export":
        export(args.csv)
    else:
        apply(args.csv, args.reviewer, args.dry_run)


if __name__ == "__main__":
    main()
