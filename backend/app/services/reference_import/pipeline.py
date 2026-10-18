"""Extract -> validate -> normalize the research workbook into table-shaped dicts.

No database access here: `build_bundle()` is what `--dry-run` runs, and `loader.load_bundle()`
persists exactly what it returns.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import openpyxl

from . import catalog
from .normalizers import (
    code_slug, comparator_from_rule, is_missing, normalize_name, normalize_severity, parse_range,
    parse_recipe_items, parse_seasons, parse_threshold_text, source_code, split_regions,
    split_source_refs, strip_accents, text, to_bool, to_int, to_number,
)


@dataclass
class Issue:
    sheet: str
    row_no: int | None
    col: str | None
    value: str | None
    severity: str  # critical | warning | info
    message: str


@dataclass
class Bundle:
    file_checksum: str = ""
    versions: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)
    nutrients: list[dict] = field(default_factory=list)
    ingredients: list[dict] = field(default_factory=list)       # each has aliases/nutrients/seasons/conditions
    conditions: list[dict] = field(default_factory=list)
    safety_rules: list[dict] = field(default_factory=list)
    thresholds: list[dict] = field(default_factory=list)
    profile_rules: list[dict] = field(default_factory=list)
    recipes: list[dict] = field(default_factory=list)
    eval_auto: list[dict] = field(default_factory=list)
    eval_rubric: list[dict] = field(default_factory=list)
    eval_templates: list[dict] = field(default_factory=list)
    raw_rows: list[dict] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    def add(self, sheet, row_no, col, value, severity, message) -> None:
        self.issues.append(Issue(sheet, row_no, col, None if value is None else str(value)[:120], severity, message))


def _find_sheet(wb, prefix: str):
    for ws in wb.worksheets:
        if ws.title.startswith(prefix):
            return ws
    return None


def _rows(b: "Bundle", ws, header_text: str, skip_after: int = 1, width: int | None = None):
    """Yield (row_no, values) for data rows below the header row; every row is also kept in b.raw_rows."""
    header_row = next((r for r in range(1, 15) if str(ws.cell(r, 1).value or "").strip().startswith(header_text)), None)
    if header_row is None:
        return
    for r in range(header_row + 1 + skip_after, ws.max_row + 1):
        first = ws.cell(r, 1).value
        if is_missing(first):
            continue
        values = [ws.cell(r, c).value for c in range(1, (width or ws.max_column) + 1)]
        b.raw_rows.append({
            "sheet": ws.title, "row_no": r,
            "cells": [v.date().isoformat() if hasattr(v, "date") else (None if v is None else str(v)) for v in values],
        })
        yield r, values


def _get(values, i):
    return values[i] if i < len(values) else None


# --------------------------------------------------------------------------- sources
def _sources(wb, b: Bundle) -> set[str]:
    sheet = "Data_Source_Register"
    ws = _find_sheet(wb, sheet)
    known: set[str] = set()
    for row_no, v in _rows(b, ws, "source_id", width=10):
        raw_code = text(v[0])
        code = source_code(raw_code)
        if len(source_code(raw_code + "x")) >= 80 or len(re.sub(r"[^A-Za-z0-9]", "", strip_accents(raw_code))) > 70:
            b.add(sheet, row_no, "source_id", raw_code, "warning", "source_id looks like a title, not a code; truncated to 80 chars")
        if code != raw_code:
            b.add(sheet, row_no, "source_id", raw_code, "info", f"source_id normalized to {code}")
        if code in known:
            b.add(sheet, row_no, "source_id", raw_code, "critical", "duplicate source_id; row skipped")
            continue
        year, _, _ = to_number(v[4])
        if year is not None and not (1900 <= year <= 2100):
            year = None
        if year is None and not is_missing(v[4]):
            b.add(sheet, row_no, "year", v[4], "warning", "year is not a valid year; stored as NULL (row text likely shifted)")
        stype = (text(v[2]) or "").lower()
        stype = stype if stype in {"book", "paper", "guideline", "spreadsheet", "website"} else None
        rel = (text(v[7]) or "needs_review").lower()
        if rel not in {"high", "medium", "low", "needs_review"}:
            b.add(sheet, row_no, "reliability_level", v[7], "warning", "unknown reliability_level; set to needs_review")
            rel = "needs_review"
        author = text(v[3])
        if author in {"Cột"}:
            b.add(sheet, row_no, "author_or_org", author, "warning", "guide-table text spilled into this row; author cleared")
            author = None
        known.add(code)
        b.sources.append({
            "source_code": code, "title": text(v[1]) or code, "source_type": stype, "author_or_org": author,
            "year": int(year) if year else None, "url_or_file": text(v[5]), "locator": text(v[6]),
            "reliability_level": rel,
            "used_for": [s.strip() for s in re.split(r"[,;]", text(v[8]) or "") if s.strip()],
            "notes": text(v[9]),
        })
    return known


def _cite(b: Bundle, sheet: str, row_no: int, col: str, cell: Any, known: set[str], table: str, entity: str) -> list[str]:
    codes, unknown = split_source_refs(cell, known)
    for raw in unknown:
        b.add(sheet, row_no, col, raw, "warning", "source not found in Data_Source_Register")
    for code in codes:
        b.citations.append({"entity_table": table, "entity_code": entity, "source_code": code})
    if not codes and not unknown:
        b.add(sheet, row_no, col, None, "warning", "no source cited")
    return codes


# --------------------------------------------------------------------------- ingredients
def _ingredients(wb, b: Bundle, known: set[str]) -> None:
    sheet = "Data_Ingredients"
    ws = _find_sheet(wb, sheet)
    seen: set[str] = set()
    for row_no, v in _rows(b, ws, "Mã duy nhất", skip_after=0, width=95):
        code = text(v[0])
        if not re.fullmatch(r"ING_[A-Z0-9_]+", code or ""):
            b.add(sheet, row_no, "ingredient_code", code, "critical", "ingredient_code must match ING_<GROUP>_<NNNN>; row skipped")
            continue
        if code in seen:
            b.add(sheet, row_no, "ingredient_code", code, "critical", "duplicate ingredient_code; row skipped")
            continue
        seen.add(code)
        name_vi = text(v[1])
        if not name_vi:
            b.add(sheet, row_no, "name_vi", None, "critical", "missing Vietnamese name; row skipped")
            continue
        raw_cat = (text(v[3]) or "").lower()
        category = catalog.CATEGORY_MAP.get(raw_cat)
        if category is None:
            b.add(sheet, row_no, "category", v[3], "warning", "missing/unknown category; stored as 'other'")
            category = "other"
        status = (text(v[91]) or "").lower()
        if status not in {"verified", "needs_review", "missing_source", "example"}:
            status = "needs_review"
        src_codes = _cite(b, sheet, row_no, "source_code", v[90], known, "ingredients", code)
        if not src_codes and status == "verified":
            status = "missing_source"

        nutrients, coverage_core = [], 0
        for col, nut in catalog.NUTRIENT_BY_COL.items():
            number, nstatus, note = to_number(_get(v, col))
            if nstatus == "invalid":
                b.add(sheet, row_no, nut["code"], _get(v, col), "warning", f"{note}; stored as not_available")
                number, nstatus = None, "not_available"
            if number is not None and number < 0:
                b.add(sheet, row_no, nut["code"], number, "critical", "negative value; stored as not_available")
                number, nstatus = None, "not_available"
            if number is not None and number > nut["plausible_max"]:
                b.add(sheet, row_no, nut["code"], number, "critical",
                      f"{number} {nut['unit']}/100g exceeds plausible max {nut['plausible_max']}; stored as not_available")
                number, nstatus = None, "not_available"
            if nstatus == "repaired":
                b.add(sheet, row_no, nut["code"], _get(v, col), "warning", f"{note}; marked repaired, please verify")
            if number is None and nstatus != "not_available":
                nstatus = "not_available"
            if number is not None and nut["is_core"]:
                coverage_core += 1
            nutrients.append({
                "nutrient_code": nut["code"], "value_per_100g": number, "value_status": nstatus,
                "source_code": src_codes[0] if src_codes else None,
            })

        # Internal consistency: macronutrients should roughly reproduce the stated energy.
        vals = {n["nutrient_code"]: n["value_per_100g"] for n in nutrients}
        if all(vals.get(k) is not None for k in ("energy_kcal", "protein_g", "fat_g", "carb_g")):
            est = 4 * vals["protein_g"] + 9 * vals["fat_g"] + 4 * vals["carb_g"] + 2 * (vals.get("fiber_g") or 0)
            if abs(est - vals["energy_kcal"]) > max(40, 0.5 * vals["energy_kcal"]):
                b.add(sheet, row_no, "energy_kcal", vals["energy_kcal"], "warning",
                      f"energy {vals['energy_kcal']} kcal vs ~{est:.0f} kcal from macros; check carb/fat values")
        if (vals.get("total_sugar_g") or 0) > (vals.get("carb_g") or 1e9):
            b.add(sheet, row_no, "total_sugar_g", vals["total_sugar_g"], "warning", "total sugar exceeds carbohydrate")
        if coverage_core < 5 and (to_bool(v[7], True)):
            b.add(sheet, row_no, "core nutrients", coverage_core, "warning",
                  f"only {coverage_core}/{len(catalog.CORE_CODES)} core nutrients; unusable as a smoothie candidate")

        seasons = parse_seasons(v[6])
        if text(v[6]) and not is_missing(v[6]) and not seasons:
            b.add(sheet, row_no, "season_months", v[6], "warning", "season text could not be parsed")
        b.ingredients.append({
            "ingredient_code": code, "name_vi": name_vi, "name_en": text(v[2]), "category": category,
            "processing_state": (text(v[8]) or "").lower() or None,
            "origin_country": text(v[4]), "growing_regions": split_regions(v[5]),
            "allowed_for_smoothie": bool(to_bool(v[7], True)), "data_status": status,
            "primary_source_code": src_codes[0] if src_codes else None,
            "entry_notes": text(v[92]), "nutrients": nutrients, "seasons": seasons,
            "aliases": [], "conditions": [], "_row": row_no,
        })


def _link_ingredient_conditions(b: Bundle) -> None:
    """Derive allergen links from names (flagged for expert review: keyword heuristic)."""
    patterns = {}
    for code, spec in catalog.CONDITIONS.items():
        if spec[3]:
            patterns[code] = [
                (kw.startswith("="), re.compile(rf"(?<![^\W\d_]){re.escape(kw.lstrip('='))}(?![^\W\d_])"))
                for kw in spec[3]
            ]
    for ing in b.ingredients:
        raw = ((ing["name_vi"] or "") + " " + (ing["name_en"] or "")).lower()
        plain = normalize_name(raw)
        for code, regexes in patterns.items():
            if any(word in plain for word in catalog.CONDITION_EXCLUDES.get(code, [])):
                continue
            if any(r.search(raw if accented else plain) for accented, r in regexes):
                relation = "contains_allergen" if catalog.CONDITIONS[code][0] == "allergy" else "should_limit"
                ing["conditions"].append({"condition_code": code, "relation": relation})
    linked = sum(1 for i in b.ingredients if i["conditions"])
    b.add("Data_Ingredients", None, "ingredient_conditions", linked, "info",
          f"{linked} ingredients auto-linked to conditions by keyword; expert should review")


# --------------------------------------------------------------------------- rules
def _condition_for(label: str, target: str, risk_type: str) -> tuple[str, bool]:
    """Return (canonical_code, label_was_wrong)."""
    slug = re.sub(r"\s+", "", label.lower())
    if slug in catalog.DISEASE_LABELS:
        return catalog.DISEASE_LABELS[slug], False
    if risk_type == "allergy":
        low = target.lower()
        for kw, code in catalog.ALLERGY_TARGET_KEYWORDS:
            if kw in low:
                return code, True
    fallback = re.sub(r"[^a-z0-9]+", "_", strip_accents(label).lower()).strip("_") or "unknown"
    return fallback, False


def _safety(wb, b: Bundle, known: set[str]) -> None:
    sheet = "Data_Clinical_Safety"
    ws = _find_sheet(wb, sheet)
    seen: set[str] = set()
    for row_no, v in _rows(b, ws, "rule_id", width=12):
        code = text(v[0])
        if code in seen:
            b.add(sheet, row_no, "rule_id", code, "critical", "duplicate rule_id; row skipped")
            continue
        seen.add(code)
        risk = (text(v[2]) or "").lower()
        if risk not in {"allergy", "disease", "nutrient_limit", "medication"}:
            b.add(sheet, row_no, "risk_type", v[2], "critical", "unknown risk_type; row skipped")
            continue
        target = text(v[3]) or ""
        label = text(v[1]) or ""
        cond, wrong = _condition_for(label, target, risk)
        if wrong:
            b.add(sheet, row_no, "condition_or_allergy", label, "info", f"label grouped different allergens; mapped to {cond} from target text")
        severity = normalize_severity(v[8])
        action = (text(v[9]) or "").lower()
        if severity is None or action not in {"block_recipe", "warn_user", "suggest_consult"}:
            b.add(sheet, row_no, "severity/action", f"{v[8]}/{v[9]}", "critical", "invalid severity or action; row skipped")
            continue
        avoid = (text(v[4]) or "").lower()
        if avoid not in {"avoid", "limit"}:
            b.add(sheet, row_no, "avoid_or_limit", v[4], "critical", "must be avoid or limit; row skipped")
            continue
        threshold, unit = to_number(v[5])[0], text(v[6])
        notes = text(v[11])
        if threshold is None and not is_missing(v[5]):
            threshold, parsed_unit = parse_threshold_text(v[5])
            unit = unit or parsed_unit
            notes = ((notes + " | ") if notes else "") + f"raw threshold: {text(v[5])}"
        if avoid == "limit" and threshold is None:
            b.add(sheet, row_no, "threshold_value", v[5], "warning", "limit rule without numeric threshold")
        message = text(v[7])
        if not message:
            b.add(sheet, row_no, "warning_message_vi", None, "critical", "missing warning message; row skipped")
            continue
        _cite(b, sheet, row_no, "source_id", v[10], known, "clinical_safety_rules", code)
        if cond not in {c["code"] for c in b.conditions}:
            spec = catalog.CONDITIONS.get(cond)
            b.conditions.append({
                "code": cond, "condition_type": spec[0] if spec else risk if risk in {"allergy", "disease"} else "other",
                "name_vi": spec[1] if spec else label, "keywords_vi": spec[2] if spec else [],
            })
        b.safety_rules.append({
            "rule_code": code, "condition_code": cond, "risk_type": risk, "target_type": "ingredient_group",
            "target_text": target, "avoid_or_limit": avoid, "threshold_value": threshold, "unit": unit,
            "warning_message_vi": message, "severity": severity, "action": action, "entry_notes": notes,
        })


def _thresholds(wb, b: Bundle, known: set[str]) -> None:
    sheet = "Data_Nutrition_Thresholds"
    ws = _find_sheet(wb, sheet)
    nutrient_codes = {n["code"] for n in catalog.NUTRIENTS}
    for row_no, v in _rows(b, ws, "threshold_id", width=14):
        code = text(v[0])
        metric = text(v[6]) or ""
        mapped = catalog.THRESHOLD_METRICS.get(metric)
        if mapped is None or mapped[0] not in nutrient_codes:
            b.add(sheet, row_no, "metric", metric, "critical", "metric has no nutrient mapping; row skipped")
            continue
        nutrient, basis = mapped
        lo, hi = to_number(v[7])[0], to_number(v[8])[0]
        if lo is not None and hi is not None and lo > hi:
            b.add(sheet, row_no, "min/max", f"{lo}>{hi}", "critical", "min_value > max_value; row skipped")
            continue
        unit = text(v[9])
        if basis == "percent_energy":
            if unit != "%":
                b.add(sheet, row_no, "unit", unit, "info", "metric is % of energy; unit set to %")
            unit = "%"
        if metric == "salt_mg":
            b.add(sheet, row_no, "metric", metric, "warning",
                  "salt_mg is mapped to sodium_mg; 600 mg salt != 600 mg sodium - confirm which one the source means")
        rule = text(v[11])
        sex = (text(v[2]) or "all").lower()
        b.thresholds.append({
            "threshold_code": code, "target_group": text(v[1]) or "all", "sex": sex if sex in {"male", "female", "all"} else "all",
            "age_min": to_int(v[3]), "age_max": to_int(v[4]), "bmi_group": text(v[5]), "metric_raw": metric,
            "nutrient_code": nutrient, "basis": basis, "min_value": lo, "max_value": hi,
            "comparator": comparator_from_rule(rule, lo, hi), "unit": unit, "meal_context": text(v[10]),
            "pass_rule_text": rule, "entry_notes": text(v[13]),
        })
        _cite(b, sheet, row_no, "source_id", v[12], known, "nutrition_thresholds", code)


def _profile_rules(wb, b: Bundle, known: set[str]) -> None:
    sheet = "Data_User_Profile_Rules"
    ws = _find_sheet(wb, sheet)
    ops = {">=", "<=", ">", "<", "between", "equals"}
    for priority, (row_no, v) in enumerate(_rows(b, ws, "profile_rule_id", width=11), start=1):
        op = (text(v[4]) or "").lower()
        if op not in ops:
            b.add(sheet, row_no, "operator", v[4], "critical", "unknown operator; row skipped")
            continue
        code = text(v[0])
        b.profile_rules.append({
            "rule_code": code, "rule_name": text(v[1]) or code, "target_group": text(v[2]), "input_field": (text(v[3]) or "").lower(),
            "operator": op, "min_value": to_number(v[5])[0], "max_value": to_number(v[6])[0], "unit": text(v[7]),
            "classification_result": text(v[8]) or "unknown", "priority": priority, "entry_notes": text(v[10]),
        })
        _cite(b, sheet, row_no, "source_id", v[9], known, "profile_classification_rules", code)


# --------------------------------------------------------------------------- recipes & eval
def _recipes(wb, b: Bundle) -> None:
    sheet = "Data_Smoothie_Recipe_Examples"
    ws = _find_sheet(wb, sheet)
    index: dict[str, str] = {}
    for ing in b.ingredients:
        index[normalize_name(ing["name_vi"])] = ing["ingredient_code"]
    for row_no, v in _rows(b, ws, "recipe_id", width=18):
        code = text(v[0])
        items = parse_recipe_items(v[3])
        for it in items:
            it["ingredient_code"] = None
            if it["amount"] is None:
                b.add(sheet, row_no, "ingredient_list", it["raw_text"], "warning", "could not read amount (expected '<name> <number>g|ml')")
                continue
            name = normalize_name(it["name"])
            it["ingredient_code"] = index.get(name) or next((c for n, c in index.items() if name.startswith(n) or n.startswith(name)), None)
            if not it["ingredient_code"]:
                b.add(sheet, row_no, "ingredient_list", it["name"], "warning", "ingredient not found in Data_Ingredients")
            if it["unit"] == "ml":
                b.add(sheet, row_no, "ingredient_list", it["raw_text"], "info", "ml converted to g assuming density 1.0")
        status = (text(v[16]) or "example").lower()
        for col, label in ((6, "energy_kcal"), (7, "protein_g"), (8, "lipid_g"), (9, "glucid_g"), (10, "fiber_g"), (11, "total_sugar_g")):
            if not is_missing(v[col]):
                b.add(sheet, row_no, label, v[col], "info", "typed nutrition totals are ignored; computed from ingredients by ai.v_recipe_nutrition")
        b.recipes.append({
            "recipe_code": code, "name_vi": text(v[1]) or code, "target_goal": text(v[2]),
            "total_weight_g": to_number(v[4])[0], "serving_ml": to_number(v[5])[0],
            "preparation_steps_vi": text(v[12]), "why_suitable_vi": text(v[13]), "safety_warning_vi": text(v[14]),
            "data_quality_status": status if status in {"example", "verified", "needs_review"} else "needs_review",
            "entry_notes": text(v[17]), "items": items,
        })


def _eval(wb, b: Bundle) -> None:
    ws = _find_sheet(wb, "Eval_Automatic_Criteria")
    for row_no, v in _rows(b, ws, "criterion_id", width=10):
        required = to_bool(v[7], None)
        related = code_slug(text(v[8])) if text(v[8]) else None
        crit = code_slug(text(v[0]))
        if crit != text(v[0]):
            b.add("Eval_Automatic_Criteria", row_no, "criterion_id", v[0], "info", f"criterion_id normalized to {crit}")
        b.eval_auto.append({
            "criterion_code": crit, "name_vi": text(v[1]) or text(v[0]), "metric": text(v[2]), "check_type": text(v[3]),
            "pass_condition": text(v[4]), "fail_condition": text(v[5]), "severity": normalize_severity(v[6]),
            "is_required": True if required is None else required, "related_rule_code": related,
            "implementation_notes": text(v[9]),
        })
        if required is None:
            b.add("Eval_Automatic_Criteria", row_no, "required", v[7], "warning", "required is not TRUE/FALSE/1/0; defaulted to TRUE")
    ws = _find_sheet(wb, "Eval_Expert_Rubric")
    for row_no, v in _rows(b, ws, "criterion_id", width=10):
        lo, hi, thr = (to_number(v[i])[0] for i in (2, 3, 4))
        if None in (lo, hi, thr) or not (lo < hi and lo <= thr <= hi):
            b.add("Eval_Expert_Rubric", row_no, "score range", f"{lo},{hi},{thr}", "critical", "invalid score_min/score_max/pass_threshold; row skipped")
            continue
        b.eval_rubric.append({
            "criterion_code": text(v[0]), "name_vi": text(v[1]) or text(v[0]), "score_min": lo, "score_max": hi, "pass_threshold": thr,
            "auto_fail_if_below": bool(to_bool(v[5], False)), "low_desc_vi": text(v[6]), "high_desc_vi": text(v[7]),
            "entry_notes": text(v[9]),
        })
    ws = _find_sheet(wb, "Eval_Synthetic_Profile_Plan")
    for row_no, v in _rows(b, ws, "profile_template_id", width=14):
        a0, a1 = parse_range(v[1])
        h0, h1 = parse_range(v[3])
        w0, w1 = parse_range(v[4])
        purpose = (text(v[12]) or "").lower()
        b.eval_templates.append({
            "template_code": text(v[0]), "age_min": a0 and int(a0), "age_max": a1 and int(a1), "sex": (text(v[2]) or "all").lower(),
            "height_cm_min": h0, "height_cm_max": h1, "weight_kg_min": w0, "weight_kg_max": w1, "bmi_group": text(v[5]),
            "activity_level": text(v[6]), "allergy_scenario": text(v[7]), "disliked_scenario": text(v[8]),
            "preferred_scenario": text(v[9]), "medical_note_scenario": text(v[10]), "sample_count": to_int(v[11]),
            "purpose": purpose if purpose in {"pilot_20", "evaluation_1000", "expert_30"} else None,
            "entry_notes": text(v[13]),
        })
        if purpose not in {"pilot_20", "evaluation_1000", "expert_30"}:
            b.add("Eval_Synthetic_Profile_Plan", row_no, "purpose", v[12], "warning",
                  "purpose is not pilot_20/evaluation_1000/expert_30; stored as NULL")


def _versions(wb, b: Bundle) -> None:
    ws = _find_sheet(wb, "SYS_Change_Log")
    last_minor = -1
    for row_no, v in _rows(b, ws, "Phiên bản", skip_after=0, width=7):
        version = text(v[0])
        if not version:
            b.add("SYS_Change_Log", row_no, "version", None, "info", "row has no version; assigned the next minor version")
            version = f"v1.{last_minor + 1}"
        m = re.fullmatch(r"v1\.(\d+)", version)
        last_minor = int(m.group(1)) if m else last_minor
        released = v[1]
        if hasattr(released, "date"):
            released = released.date()
        elif isinstance(released, (int, float)):
            from datetime import date, timedelta
            released = date(1899, 12, 30) + timedelta(days=int(released))
        else:
            released = None
        b.versions.append({
            "version": version, "released_on": released, "author": text(v[2]), "change_summary": text(v[3]),
            "reason": text(v[4]), "meeting_ref": text(v[6]),
        })


def _validate_references(b: Bundle) -> None:
    first_by_name: dict[str, dict] = {}
    for ing in b.ingredients:
        key = normalize_name(ing["name_vi"])
        if key in first_by_name:
            b.add("Data_Ingredients", ing["_row"], "name_vi", ing["name_vi"], "warning",
                  f"same name as {first_by_name[key]['ingredient_code']} (row {first_by_name[key]['_row']}); "
                  "keep one or rename (e.g. add processing state) - the database stores it as '<name> (<code>)'")
        else:
            first_by_name[key] = ing
    for rule in b.eval_auto:
        ref = rule["related_rule_code"]
        if ref and ref.startswith("SAFE_") and ref not in {r["rule_code"] for r in b.safety_rules}:
            b.add("Eval_Automatic_Criteria", None, "related_rule_code", ref, "warning",
                  f"{rule['criterion_code']} points to rule {ref} which does not exist in Data_Clinical_Safety")
    allergens = {c["code"] for c in b.conditions if c["condition_type"] == "allergy"}
    for code in ("milk_allergy", "soy_allergy"):
        if code not in allergens:
            b.add("Data_Clinical_Safety", None, "condition", code, "warning",
                  f"no safety rule for {code}, but Eval_Automatic_Criteria refers to it")


def build_bundle(xlsx_path: Path) -> Bundle:
    b = Bundle(file_checksum=hashlib.sha256(Path(xlsx_path).read_bytes()).hexdigest())
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    missing = [p for p in ("Data_Source_Register", "Data_Ingredients", "Data_Clinical_Safety", "Data_Nutrition_Thresholds",
                           "Data_User_Profile_Rules", "Data_Smoothie_Recipe_Examples", "Eval_Automatic_Criteria",
                           "Eval_Expert_Rubric", "Eval_Synthetic_Profile_Plan", "SYS_Change_Log") if _find_sheet(wb, p) is None]
    if missing:
        raise SystemExit(f"Workbook is missing tabs: {', '.join(missing)}")
    b.nutrients = [{k: n[k] for k in ("code", "name_vi", "name_en", "unit", "group", "is_core", "plausible_max", "parent_code", "display_order")}
                   for n in catalog.NUTRIENTS]
    _versions(wb, b)
    known = _sources(wb, b)
    _ingredients(wb, b, known)
    _safety(wb, b, known)
    _thresholds(wb, b, known)
    _profile_rules(wb, b, known)
    _recipes(wb, b)
    _eval(wb, b)
    for code, spec in catalog.CONDITIONS.items():  # conditions referenced only by ingredient links / profiles
        if code not in {c["code"] for c in b.conditions}:
            b.conditions.append({"code": code, "condition_type": spec[0], "name_vi": spec[1], "keywords_vi": spec[2]})
    _link_ingredient_conditions(b)
    _validate_references(b)
    return b


def restrict_ingredients(b: Bundle, codes: list[str]) -> Bundle:
    """Keep only the given ingredient codes (a small test import); every other sheet stays complete."""
    wanted = set(codes)
    missing = wanted - {i["ingredient_code"] for i in b.ingredients}
    if missing:
        raise SystemExit(f"Unknown ingredient codes: {', '.join(sorted(missing))}")
    rows = {i["_row"] for i in b.ingredients if i["ingredient_code"] in wanted}
    b.ingredients = [i for i in b.ingredients if i["ingredient_code"] in wanted]
    b.citations = [c for c in b.citations if c["entity_table"] != "ingredients" or c["entity_code"] in wanted]
    b.raw_rows = [r for r in b.raw_rows if r["sheet"] != "Data_Ingredients" or r["row_no"] in rows]
    b.issues = [i for i in b.issues if i.sheet != "Data_Ingredients" or i.row_no is None or i.row_no in rows]
    return b
