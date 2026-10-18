"""Import the "Timeline - AI Dinh Duong" workbook (.xlsx export) into the reference tables.

  --dry-run   validate and report only; no database access
  --check-db  run the full load inside a transaction and ROLL IT BACK (finds constraint errors, writes nothing)
  --apply     load for real, then publish the dataset version (needs no critical issues unless --allow-critical)

  python scripts/import_research_workbook.py data/workbook/ai_dinh_duong.xlsx --dry-run --issues-csv issues.csv
  python scripts/import_research_workbook.py data/workbook/ai_dinh_duong.xlsx --check-db
  python scripts/import_research_workbook.py data/workbook/ai_dinh_duong.xlsx --apply --version v1.0 --embed
"""

import argparse
import collections
import csv
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.reference_import.pipeline import build_bundle, restrict_ingredients  # noqa: E402

# A small, smoothie-relevant test set: rows whose energy matches their macros and have >= 5 of 7 core nutrients,
# including allergen carriers (milk, soy, sesame, peanut, latex-fruit) so allergy blocking can be tried.
SAMPLE_CODES = [
    "ING_FRUIT_0001", "ING_FRUIT_0002", "ING_FRUIT_0003", "ING_FRUIT_0006", "ING_FRUIT_0009", "ING_FRUIT_0011",
    "ING_FRUIT_0015", "ING_FRUIT_0016", "ING_FRUIT_0017", "ING_FRUIT_0022", "ING_FRUIT_0023", "ING_FRUIT_0024",
    "ING_FRUIT_0026", "ING_FRUIT_0035", "ING_FRUIT_0038", "ING_FRUIT_0039", "ING_FRUIT_0045", "ING_FRUIT_0052",
    "ING_FRUIT_0055", "ING_FRUIT_0067", "ING_FRUIT_0054", "ING_FRUIT_0056", "ING_FRUIT_0062", "ING_FRUIT_0064",
    "ING_FRUIT_0090", "ING_FRUIT_0091", "ING_FRUIT_0096", "ING_FRUIT_0100", "ING_FRUIT_0101", "ING_FRUIT_0103",
    "ING_FRUIT_0132",
]


def print_report(bundle, issues_csv: Path | None) -> None:
    tables = {
        "sources": bundle.sources, "nutrients": bundle.nutrients, "ingredients": bundle.ingredients,
        "conditions": bundle.conditions, "safety_rules": bundle.safety_rules, "thresholds": bundle.thresholds,
        "profile_rules": bundle.profile_rules, "recipes": bundle.recipes, "eval_auto": bundle.eval_auto,
        "eval_rubric": bundle.eval_rubric, "eval_templates": bundle.eval_templates, "versions": bundle.versions,
        "citations": bundle.citations,
    }
    print("Rows ready to load:")
    for name, rows in tables.items():
        print(f"  {name:15} {len(rows)}")
    usable = sum(1 for i in bundle.ingredients if i["allowed_for_smoothie"])
    print(f"  ingredients allowed for smoothie: {usable}")

    by_sev = collections.Counter(i.severity for i in bundle.issues)
    print(f"\nIssues: critical={by_sev['critical']} warning={by_sev['warning']} info={by_sev['info']}")
    grouped = collections.Counter((i.sheet, i.severity, i.message.split(";")[0][:70]) for i in bundle.issues if i.severity != "info")
    for (sheet, sev, msg), count in sorted(grouped.items(), key=lambda kv: (kv[0][1] != "critical", -kv[1]))[:40]:
        print(f"  [{sev:8}] {sheet}: {msg} x{count}")
    if issues_csv:
        with issues_csv.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["sheet", "row", "column", "value", "severity", "message"])
            for i in bundle.issues:
                writer.writerow([i.sheet, i.row_no, i.col, i.value, i.severity, i.message])
        print(f"\nFull issue list written to {issues_csv}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("xlsx", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="validate and report only; no database access")
    mode.add_argument("--check-db", action="store_true", help="full load in a transaction that is rolled back")
    mode.add_argument("--apply", action="store_true", help="load for real and publish the version")
    parser.add_argument("--version", help="dataset version to publish (default: latest in SYS_Change_Log)")
    parser.add_argument("--embed", action="store_true", help="create embeddings for new/changed knowledge chunks (only with --apply)")
    parser.add_argument("--issues-csv", type=Path, help="write every issue to this CSV for the data team")
    parser.add_argument("--sample", action="store_true", help=f"load only the {len(SAMPLE_CODES)}-ingredient test set (other sheets complete)")
    parser.add_argument("--allow-critical", action="store_true", help="load even when critical issues exist (those rows are already skipped)")
    args = parser.parse_args()

    bundle = build_bundle(args.xlsx)
    if args.sample:
        bundle = restrict_ingredients(bundle, SAMPLE_CODES)
    print_report(bundle, args.issues_csv)
    if args.dry_run:
        print("\nDry run: nothing was written.")
        return

    critical = sum(1 for i in bundle.issues if i.severity == "critical")
    if args.apply and critical and not args.allow_critical:
        raise SystemExit(f"\n{critical} critical issues; fix the sheet or re-run with --allow-critical (affected cells/rows are skipped).")
    from app.services.reference_import.loader import load_bundle

    version = args.version or (bundle.versions[-1]["version"] if bundle.versions else "v1.0")
    stats = load_bundle(bundle, version=version, embed=args.embed, commit=args.apply)
    print(f"\n{'Loaded' if args.apply else 'Checked (rolled back, nothing written)'} dataset {version}: {stats}")


if __name__ == "__main__":
    main()
