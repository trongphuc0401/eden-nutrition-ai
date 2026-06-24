import csv
import json
from pathlib import Path
import re
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


BACKEND_DIR = Path(__file__).resolve().parents[1]
RAW_CSV_PATH = BACKEND_DIR / "data" / "fruit_data_raw.csv"
SEED_PATH = BACKEND_DIR / "data" / "vietnamese_fruits_seed.json"


def clean_text(value: str) -> str:
    return value.replace("\n", " ").strip()


def parse_number(value: str) -> float | int | None:
    value = clean_text(value)
    if not value or value == "-":
        return None
    normalized = value.replace(",", ".")
    try:
        number = float(normalized)
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


def parse_months(value: str) -> list[int]:
    return sorted({int(match) for match in re.findall(r"T\s*(\d{1,2})", value) if 1 <= int(match) <= 12})


def make_column_names(header_rows: list[list[str]], width: int) -> list[str]:
    names: list[str] = []
    for index in range(width):
        parts = [clean_text(row[index]) for row in header_rows if index < len(row) and clean_text(row[index])]
        if not parts:
            parts = [f"Column {index + 1}"]
        candidate = " | ".join(parts)
        if candidate in names:
            candidate = f"{candidate} ({index + 1})"
        names.append(candidate)
    return names


def get_value(raw_values: dict[str, str], column_names: list[str], index: int) -> str:
    return raw_values.get(column_names[index], "")


def build_content(record: dict[str, Any]) -> str:
    nutrition = record["nutrition_per_100g"]
    raw_values = record["raw_values"]
    facts = [
        f"Ingredient: {record['ingredient_name']}",
        f"Category: {record['category']}",
        f"Origin country: {record['origin_country']}",
        f"Region: {record['region'] or 'unknown'}",
        f"Season: {record['season'] or 'unknown'}",
        "Key nutrition per 100g:",
        f"- Energy: {nutrition['energy_kcal'] if nutrition['energy_kcal'] is not None else 'unknown'} kcal",
        f"- Protein: {nutrition['protein_g'] if nutrition['protein_g'] is not None else 'unknown'} g",
        f"- Lipid: {nutrition['lipid_g'] if nutrition['lipid_g'] is not None else 'unknown'} g",
        f"- Glucid: {nutrition['glucid_g'] if nutrition['glucid_g'] is not None else 'unknown'} g",
        f"- Fiber: {nutrition['fiber_g'] if nutrition['fiber_g'] is not None else 'unknown'} g",
        f"- Total sugar: {nutrition['total_sugar_g'] if nutrition['total_sugar_g'] is not None else 'unknown'} g",
        f"- Calcium: {nutrition['calcium_mg'] if nutrition['calcium_mg'] is not None else 'unknown'} mg",
        f"- Iron: {nutrition['iron_mg'] if nutrition['iron_mg'] is not None else 'unknown'} mg",
        f"- Potassium: {nutrition['potassium_mg'] if nutrition['potassium_mg'] is not None else 'unknown'} mg",
        f"- Vitamin C: {nutrition['vitamin_c_mg'] if nutrition['vitamin_c_mg'] is not None else 'unknown'} mg",
        "Raw source values:",
    ]
    facts.extend(f"- {key}: {value}" for key, value in raw_values.items() if value)
    return "\n".join(facts)


def convert_csv_to_seed(raw_csv_path: Path = RAW_CSV_PATH, seed_path: Path = SEED_PATH) -> list[dict[str, Any]]:
    with raw_csv_path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file))

    width = max(len(row) for row in rows)
    padded_rows = [row + [""] * (width - len(row)) for row in rows]
    header_rows = padded_rows[:4]
    column_names = make_column_names(header_rows[:3], width)

    records: list[dict[str, Any]] = []
    for source_row_number, row in enumerate(padded_rows[4:], start=5):
        if not any(clean_text(value) for value in row):
            continue
        raw_values = {
            column_names[index]: clean_text(value)
            for index, value in enumerate(row)
        }
        stt = parse_number(get_value(raw_values, column_names, 0))
        title = get_value(raw_values, column_names, 1)
        season = get_value(raw_values, column_names, 2)
        region = get_value(raw_values, column_names, 3)
        allowed_for_smoothie = "khô" not in title.lower()

        record = {
            "source_sheet": "Fruit_Data",
            "source_range": "Fruit_Data!A1:CQ1000",
            "source_row_number": source_row_number,
            "source_column_count": width,
            "raw_headers": header_rows,
            "raw_columns": column_names,
            "raw_values": raw_values,
            "stt": stt,
            "title": title,
            "ingredient_name": title,
            "category": "fruit",
            "origin_country": "Vietnam",
            "region": region,
            "season": season,
            "season_months": parse_months(season),
            "allowed_for_smoothie": allowed_for_smoothie,
            "source": "Google Sheet Fruit_Data - Thành phần dinh dưỡng trên 100g",
            "nutrition_per_100g": {
                "water_g": parse_number(get_value(raw_values, column_names, 4)),
                "energy_kcal": parse_number(get_value(raw_values, column_names, 5)),
                "protein_g": parse_number(get_value(raw_values, column_names, 6)),
                "lipid_g": parse_number(get_value(raw_values, column_names, 7)),
                "glucid_g": parse_number(get_value(raw_values, column_names, 8)),
                "fiber_g": parse_number(get_value(raw_values, column_names, 9)),
                "ash_g": parse_number(get_value(raw_values, column_names, 10)),
                "total_sugar_g": parse_number(get_value(raw_values, column_names, 11)),
                "calcium_mg": parse_number(get_value(raw_values, column_names, 17)),
                "iron_mg": parse_number(get_value(raw_values, column_names, 18)),
                "magnesium_mg": parse_number(get_value(raw_values, column_names, 19)),
                "manganese_mg": parse_number(get_value(raw_values, column_names, 20)),
                "phosphorus_mg": parse_number(get_value(raw_values, column_names, 21)),
                "potassium_mg": parse_number(get_value(raw_values, column_names, 22)),
                "sodium_mg": parse_number(get_value(raw_values, column_names, 23)),
                "zinc_mg": parse_number(get_value(raw_values, column_names, 24)),
                "copper_ug": parse_number(get_value(raw_values, column_names, 25)),
                "selenium_ug": parse_number(get_value(raw_values, column_names, 26)),
                "vitamin_c_mg": parse_number(get_value(raw_values, column_names, 27)),
            },
        }
        record["content"] = build_content(record)
        records.append(record)

    with seed_path.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)
        file.write("\n")

    return records


def main() -> None:
    records = convert_csv_to_seed()
    print(f"Built {len(records)} fruit records.")
    print(f"Seed file: {SEED_PATH}")
    print(f"Columns preserved per record: {records[0]['source_column_count'] if records else 0}")


if __name__ == "__main__":
    main()
