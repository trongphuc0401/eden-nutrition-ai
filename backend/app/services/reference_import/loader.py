"""Persist a validated Bundle into the reference tables (public.*). One transaction.

Re-runnable: every table is keyed by its sheet code and upserted, so a second run updates rather than duplicates.
Rows already in the database that are not in the workbook (legacy rules/thresholds the app still reads) are left alone.
The new dataset version only becomes `is_current` as the very last statement.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from sqlalchemy import text

from app.database import engine

from . import catalog
from .normalizers import normalize_name
from .pipeline import Bundle

CATEGORY = {"roots_tubers": "vegetable", "dairy": "liquid"}  # public.ingredients has no roots_tubers/dairy
OPERATORS = {">=": "gte", "<=": "lte", ">": "gt", "<": "lt"}
CITED_TABLES = ["ingredients", "clinical_safety_rules", "nutrition_thresholds", "profile_classification_rules"]


def _canon(sheet: str) -> str:
    return re.sub(r"\s*\(.*$", "", sheet)


def _hash(*parts: Any) -> str:
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def _dedupe(rows: list[dict], key: tuple[str, ...]) -> list[dict]:
    return list({tuple(r[k] for k in key): r for r in rows}.values())


def _ingredient_card(ing: dict, names: dict[str, dict]) -> str:
    core = [f"{names[n['nutrient_code']]['name_vi']} {n['value_per_100g']:g} {names[n['nutrient_code']]['unit']}"
            for n in ing["nutrients"] if names[n["nutrient_code"]]["is_core"] and n["value_per_100g"] is not None]
    seasons = "; ".join(
        f"{s['region_label']}: " + ("quanh năm" if s["year_round"] else "tháng " + ",".join(map(str, s["months"])))
        for s in ing["seasons"])
    allergens = ", ".join(catalog.CONDITIONS[c["condition_code"]][1] for c in ing["conditions"] if c["condition_code"] in catalog.CONDITIONS)
    parts = [f"{ing['name_vi']}" + (f" ({ing['name_en']})" if ing["name_en"] else "") + f" - nhóm {ing['category']}."]
    if core:
        parts.append("Trên 100g: " + "; ".join(core) + ".")
    if seasons:
        parts.append(f"Mùa vụ: {seasons}.")
    if allergens:
        parts.append(f"Lưu ý dị ứng/bệnh lý: {allergens}.")
    parts.append(f"Trạng thái dữ liệu: {ing['data_status']}." + (f" Nguồn: {ing['primary_source_code']}." if ing["primary_source_code"] else ""))
    return " ".join(parts)


def _chunks(b: Bundle) -> list[dict]:
    names = {n["code"]: n for n in b.nutrients}
    cond_names = {c["code"]: c["name_vi"] for c in b.conditions}
    out = []
    for ing in b.ingredients:
        if ing["allowed_for_smoothie"]:
            out.append({"table": "ingredients", "code": ing["ingredient_code"], "type": "ingredient_card", "title": f"{ing['name_vi']} - thẻ nguyên liệu",
                        "ingredient_name": ing["name_vi"].lower(), "category": ing["category"], "content": _ingredient_card(ing, names),
                        "source": ing["primary_source_code"],
                        "meta": {"category": ing["category"], "data_status": ing["data_status"],
                                 "conditions": [c["condition_code"] for c in ing["conditions"]],
                                 "months": sorted({m for s in ing["seasons"] for m in s["months"]})}})
    for r in b.safety_rules:
        out.append({"table": "clinical_safety_rules", "code": r["rule_code"], "type": "safety_rule", "title": f"Quy tắc an toàn {r['rule_code']}",
                    "ingredient_name": None, "category": r["risk_type"], "source": None,
                    "content": f"[{r['severity']}] {cond_names.get(r['condition_code'], r['condition_code'])}: {r['warning_message_vi']} "
                               f"({'tránh' if r['avoid_or_limit'] == 'avoid' else 'hạn chế'}: {r['target_text']}). Hành động: {r['action']}.",
                    "meta": {"condition": r["condition_code"], "severity": r["severity"], "action": r["action"]}})
    for t in b.thresholds:
        bound = " - ".join(f"{x:g}" for x in (t["min_value"], t["max_value"]) if x is not None)
        out.append({"table": "nutrition_thresholds", "code": t["threshold_code"], "type": "threshold", "title": f"Ngưỡng {t['threshold_code']}",
                    "ingredient_name": None, "category": "threshold", "source": None,
                    "content": f"Ngưỡng {t['nutrient_code']} cho nhóm {t['target_group']} (tuổi {t['age_min']}-{t['age_max']}, {t['meal_context']}): "
                               f"{bound} {t['unit'] or ''}" + (" % năng lượng" if t["basis"] == "percent_energy" else ""),
                    "meta": {"target_group": t["target_group"], "nutrient": t["nutrient_code"]}})
    for rec in b.recipes:
        out.append({"table": "smoothie_recipes", "code": rec["recipe_code"], "type": "recipe", "title": rec["name_vi"], "ingredient_name": None,
                    "category": "recipe", "source": None,
                    "content": f"{rec['name_vi']} - mục tiêu {rec['target_goal']}. Nguyên liệu: " + "; ".join(i["raw_text"] for i in rec["items"])
                               + f". {rec['why_suitable_vi'] or ''} {rec['safety_warning_vi'] or ''}".rstrip(),
                    "meta": {"status": rec["data_quality_status"]}})
    return out


def load_bundle(b: Bundle, version: str, embed: bool = False, commit: bool = True) -> dict[str, int]:
    """Load everything. With commit=False the transaction is rolled back at the end (constraint check only)."""
    chunks = _chunks(b)
    stats: dict[str, int] = {}
    conn = engine.connect()
    trans = conn.begin()
    try:
        run = lambda sql, params=None: conn.execute(text(sql), params or {})   # noqa: E731
        one = lambda sql, params=None: conn.execute(text(sql), params or {}).scalar()  # noqa: E731

        # ---- versions and one batch per sheet (carries counts + issues; staging keeps raw rows and per-cell errors)
        for v in b.versions:
            run("""INSERT INTO dataset_versions (version_code, released_on, author_name, change_summary, change_reason, meeting_reference)
                   VALUES (:v, :d, :a, :s, :r, :m) ON CONFLICT (version_code) DO UPDATE SET released_on = EXCLUDED.released_on,
                   author_name = EXCLUDED.author_name, change_summary = EXCLUDED.change_summary,
                   change_reason = EXCLUDED.change_reason, meeting_reference = EXCLUDED.meeting_reference""",
                {"v": v["version"], "d": v["released_on"], "a": v["author"], "s": v["change_summary"] or "", "r": v["reason"], "m": v["meeting_ref"]})
        run("INSERT INTO dataset_versions (version_code, change_summary) VALUES (:v, 'Import from workbook') ON CONFLICT DO NOTHING", {"v": version})

        sheets = sorted({_canon(r["sheet"]) for r in b.raw_rows})
        batch = {}
        for sheet in sheets:
            issues = [i for i in b.issues if _canon(i.sheet) == sheet and i.severity != "info"]
            rows = sum(1 for r in b.raw_rows if _canon(r["sheet"]) == sheet)
            critical = sum(1 for i in issues if i.severity == "critical")
            batch[sheet] = one("""INSERT INTO import_batches (dataset_version_code, sheet_name, file_checksum, rows_ok, rows_rejected, errors)
                                  VALUES (:v, :s, :c, :ok, :rej, CAST(:e AS jsonb)) RETURNING id""",
                               {"v": version, "s": sheet, "c": b.file_checksum, "ok": max(rows - critical, 0), "rej": critical,
                                "e": json.dumps([{"row": i.row_no, "col": i.col, "severity": i.severity, "message": i.message} for i in issues[:200]], ensure_ascii=False)})
            run("DELETE FROM staging.raw_rows WHERE batch_id IN (SELECT id FROM import_batches WHERE sheet_name = :s AND id <> :id)", {"s": sheet, "id": batch[sheet]})
        conn.execute(text("INSERT INTO staging.raw_rows (batch_id, sheet, row_no, payload) VALUES (:b, :s, :r, CAST(:p AS jsonb))"),
                     [{"b": batch[_canon(r["sheet"])], "s": _canon(r["sheet"]), "r": r["row_no"], "p": json.dumps(r["cells"], ensure_ascii=False)} for r in b.raw_rows])
        err_rows = [{"b": batch[_canon(i.sheet)], "s": _canon(i.sheet), "r": i.row_no, "c": i.col, "v": i.value, "sev": i.severity, "m": i.message}
                    for i in b.issues if _canon(i.sheet) in batch]
        if err_rows:
            conn.execute(text("INSERT INTO staging.row_errors (batch_id, sheet, row_no, col, value, severity, message) "
                              "VALUES (:b, :s, :r, :c, :v, :sev, :m)"), err_rows)
        ing_batch = batch["Data_Ingredients"]

        # ---- sources, nutrients, conditions
        conn.execute(text("""INSERT INTO data_sources (source_code, title, source_type, author_or_org, published_year, url_or_file, locator,
                                                       reliability_level, used_for, notes)
                             VALUES (:source_code, :title, COALESCE(:source_type, 'website'), :author_or_org, :year, :url_or_file, :locator,
                                     :reliability_level, :used_for, :notes)
                             ON CONFLICT (source_code) DO UPDATE SET title = EXCLUDED.title, source_type = EXCLUDED.source_type,
                               author_or_org = EXCLUDED.author_or_org, published_year = EXCLUDED.published_year, url_or_file = EXCLUDED.url_or_file,
                               locator = EXCLUDED.locator, reliability_level = EXCLUDED.reliability_level, used_for = EXCLUDED.used_for, notes = EXCLUDED.notes"""),
                     [{**s, "title": s["title"][:500], "locator": (s["locator"] or "")[:255] or None, "author_or_org": (s["author_or_org"] or "")[:255] or None} for s in b.sources])
        # existing nutrient names/order stay as the team set them; the new flags and missing codes are filled in
        conn.execute(text("""INSERT INTO nutrients (nutrient_code, name_vi, name_en, unit, nutrient_group, display_order, sheet_header, is_core, plausible_max_per_100g)
                             VALUES (:code, :name_vi, :name_en, :unit, :group, :display_order, :header, :is_core, :plausible_max)
                             ON CONFLICT (nutrient_code) DO UPDATE SET is_core = EXCLUDED.is_core, plausible_max_per_100g = EXCLUDED.plausible_max_per_100g,
                               sheet_header = COALESCE(nutrients.sheet_header, EXCLUDED.sheet_header)"""),
                     [{**n, "header": n["name_vi"]} for n in b.nutrients])
        conn.execute(text("UPDATE nutrients SET parent_nutrient_code = :p WHERE nutrient_code = :c AND parent_nutrient_code IS NULL"),
                     [{"p": n["parent_code"], "c": n["code"]} for n in b.nutrients if n["parent_code"]])
        conn.execute(text("""INSERT INTO health_conditions (condition_code, name_vi, condition_type, keywords_vi)
                             VALUES (:code, :name_vi, :condition_type, :keywords_vi)
                             ON CONFLICT (condition_code) DO UPDATE SET name_vi = EXCLUDED.name_vi, condition_type = EXCLUDED.condition_type,
                               keywords_vi = EXCLUDED.keywords_vi"""), b.conditions)
        known_nutrients = {r[0] for r in run("SELECT nutrient_code FROM nutrients")}

        # ---- ingredients and everything hanging off them
        # ingredients.name_normalized is UNIQUE; duplicate names in the sheet (e.g. two "Hạt điều") keep the first and get "<name> (<code>)"
        owner = {r[0]: r[1] for r in run("SELECT name_normalized, ingredient_code FROM ingredients")}
        norm_for: dict[str, str] = {}
        for ing in b.ingredients:
            base = normalize_name(ing["name_vi"])[:255]
            taken = owner.get(base)
            if taken and taken != ing["ingredient_code"]:
                norm_for[ing["ingredient_code"]] = f"{base[:230]} ({ing['ingredient_code'].lower()})"
            else:
                norm_for[ing["ingredient_code"]] = base
                owner[base] = ing["ingredient_code"]
        ing_id: dict[str, Any] = {}
        for ing in b.ingredients:
            h = _hash(ing["nutrients"], ing["seasons"], ing["name_vi"], ing["category"], ing["data_status"])
            iid = one("""INSERT INTO ingredients (ingredient_code, name_vi, name_en, name_normalized, category, processing_state, origin_country, growing_regions,
                                                  allowed_for_smoothie, data_status, primary_source_code, entry_notes, dataset_version_code, content_hash)
                         VALUES (:code, :vi, :en, :norm, :cat, COALESCE(:state, 'fresh'), :country, :regions, :allowed, :status, :src, :notes, :v, :h)
                         ON CONFLICT (ingredient_code) DO UPDATE SET name_vi = EXCLUDED.name_vi, name_en = EXCLUDED.name_en,
                           name_normalized = EXCLUDED.name_normalized, category = EXCLUDED.category, processing_state = EXCLUDED.processing_state,
                           origin_country = EXCLUDED.origin_country, growing_regions = EXCLUDED.growing_regions,
                           allowed_for_smoothie = EXCLUDED.allowed_for_smoothie, data_status = EXCLUDED.data_status,
                           primary_source_code = EXCLUDED.primary_source_code, entry_notes = EXCLUDED.entry_notes,
                           dataset_version_code = EXCLUDED.dataset_version_code, content_hash = EXCLUDED.content_hash, updated_at = NOW()
                         RETURNING id""",
                       {"code": ing["ingredient_code"], "vi": ing["name_vi"][:255], "en": (ing["name_en"] or "")[:255] or None, "norm": norm_for[ing["ingredient_code"]],
                        "cat": CATEGORY.get(ing["category"], ing["category"]), "state": ing["processing_state"] if ing["processing_state"] in
                        {"fresh", "dried", "frozen", "powder", "juice", "other"} else None, "country": (ing["origin_country"] or "")[:100] or None,
                        "regions": ing["growing_regions"], "allowed": ing["allowed_for_smoothie"], "status": ing["data_status"],
                        "src": ing["primary_source_code"], "notes": ing["entry_notes"], "v": version, "h": h})
            ing_id[ing["ingredient_code"]] = iid
        ids = list(ing_id.values())
        for table in ("ingredient_nutrients", "ingredient_seasons"):
            run(f"DELETE FROM {table} WHERE ingredient_id = ANY(:ids)", {"ids": ids})
        # only the name-derived links are rebuilt; expert-reviewed ones (verified / rejected) survive re-imports
        run("DELETE FROM ingredient_conditions WHERE ingredient_id = ANY(:ids) AND review_status = 'auto'", {"ids": ids})
        nut_rows, season_rows, cond_rows, alias_rows = [], [], [], []
        for ing in b.ingredients:
            iid = ing_id[ing["ingredient_code"]]
            for n in ing["nutrients"]:
                if n["value_per_100g"] is None or n["nutrient_code"] not in known_nutrients:
                    continue  # absence of a row means "no data"; not_available rows would only add noise
                repaired = n["value_status"] == "repaired"
                nut_rows.append({"i": iid, "n": n["nutrient_code"], "v": n["value_per_100g"], "src": n["source_code"], "b": ing_batch, "nr": repaired,
                                 "note": "Excel đã đổi số thành ngày; giá trị dựng lại từ ngày/tháng, cần kiểm tra lại" if repaired else None})
            merged: dict[str, dict] = {}
            for s in ing["seasons"]:
                cur = merged.setdefault(s["region_label"][:255], {**s, "region_label": s["region_label"][:255], "months": set()})
                cur["months"] |= set(s["months"])
                cur["year_round"] = cur["year_round"] or s["year_round"]
            season_rows += [{"i": iid, "l": s["region_label"], "sc": s["region_scope"], "m": sorted(s["months"]), "y": s["year_round"]} for s in merged.values()]
            cond_rows += [{"i": iid, "c": c["condition_code"], "r": c["relation"]} for c in ing["conditions"]]
            if norm_for[ing["ingredient_code"]] != normalize_name(ing["name_vi"])[:255]:
                alias_rows.append({"i": iid, "a": ing["name_vi"][:255], "n": normalize_name(ing["name_vi"])[:255], "lang": "vi"})
            if ing["name_en"]:
                alias_rows.append({"i": iid, "a": ing["name_en"][:255], "n": normalize_name(ing["name_en"])[:255], "lang": "en"})
        if nut_rows:
            conn.execute(text("""INSERT INTO ingredient_nutrients (ingredient_id, nutrient_code, value_per_100g, value_status, source_code, import_batch_id, needs_review, review_note)
                                 VALUES (:i, :n, :v, 'measured', :src, :b, :nr, :note)"""), nut_rows)
        if season_rows:
            conn.execute(text("INSERT INTO ingredient_seasons (ingredient_id, region_label, region_scope, months, year_round) VALUES (:i, :l, :sc, :m, :y)"),
                         [s for s in season_rows if s["m"] or s["y"]])
        if cond_rows:
            conn.execute(text("""INSERT INTO ingredient_conditions (ingredient_id, condition_code, relation, notes)
                                 VALUES (:i, :c, :r, 'Tự gán theo từ khoá tên nguyên liệu; chuyên gia cần xác nhận') ON CONFLICT DO NOTHING"""), cond_rows)
        if alias_rows:
            conn.execute(text("""INSERT INTO ingredient_aliases (ingredient_id, alias, alias_normalized, language_code)
                                 VALUES (:i, :a, :n, :lang) ON CONFLICT DO NOTHING"""), alias_rows)
        stats.update(ingredients=len(ing_id), ingredient_nutrients=len(nut_rows), ingredient_seasons=len(season_rows), ingredient_conditions=len(cond_rows))

        # ---- citations
        run("DELETE FROM source_citations WHERE entity_table = ANY(:t)", {"t": CITED_TABLES})
        cites = _dedupe([c for c in b.citations if c["entity_table"] in CITED_TABLES], ("entity_table", "entity_code", "source_code"))
        if cites:
            conn.execute(text("INSERT INTO source_citations (entity_table, entity_code, source_code) VALUES (:entity_table, :entity_code, :source_code) ON CONFLICT DO NOTHING"), cites)
        first_source: dict[tuple[str, str], str] = {}
        for c in cites:
            first_source.setdefault((c["entity_table"], c["entity_code"]), c["source_code"])

        # ---- safety rules (legacy NOT NULL columns are filled too: the app still reads them)
        for r in b.safety_rules:
            p = {"code": r["rule_code"], "cond": r["condition_code"], "risk": r["risk_type"], "target": r["target_text"], "tshort": r["target_text"][:255],
                 "action": r["action"], "sev": r["severity"], "thr": r["threshold_value"], "unit": r["unit"], "msg": r["warning_message_vi"],
                 "src": first_source.get(("clinical_safety_rules", r["rule_code"])), "notes": r["entry_notes"], "aol": r["avoid_or_limit"],
                 "b": batch["Data_Clinical_Safety"], "v": version, "tt": r["target_type"]}
            exists = one("SELECT 1 FROM clinical_safety_rules WHERE rule_code = :code", p)
            if exists:
                run("""UPDATE clinical_safety_rules SET condition_key = :cond, risk_type = :risk, ingredient_or_nutrient = :tshort, action = :action, severity = :sev,
                         threshold_value = :thr, unit = :unit, warning_message = :msg, source = :src, notes = :notes, condition_code = :cond2, target_type = :tt,
                         target_text = :target, avoid_or_limit = :aol, warning_message_vi = :msg2, recommended_action = :action2, is_active = TRUE,
                         entry_notes = :notes2, import_batch_id = :b, dataset_version_code = :v WHERE rule_code = :code""",
                    {**p, "cond2": p["cond"], "msg2": p["msg"], "action2": p["action"], "notes2": p["notes"]})
            else:
                run("""INSERT INTO clinical_safety_rules (id, rule_code, condition_key, risk_type, ingredient_or_nutrient, action, severity, threshold_value, unit,
                         warning_message, source, notes, condition_code, target_type, target_text, avoid_or_limit, warning_message_vi, recommended_action,
                         is_active, entry_notes, import_batch_id, dataset_version_code)
                       VALUES (gen_random_uuid(), :code, :cond, :risk, :tshort, :action, :sev, :thr, :unit, :msg, :src, :notes, :cond2, :tt, :target, :aol,
                               :msg2, :action2, TRUE, :notes2, :b, :v)""",
                    {**p, "cond2": p["cond"], "msg2": p["msg"], "action2": p["action"], "notes2": p["notes"]})
        stats["clinical_safety_rules"] = len(b.safety_rules)

        # ---- thresholds
        for t in b.thresholds:
            p = {"code": t["threshold_code"], "goal": t["target_group"], "metric": t["metric_raw"], "lo": t["min_value"], "hi": t["max_value"],
                 "unit": t["unit"] or "%", "ctx": t["meal_context"], "rule": (t["pass_rule_text"] or "")[:255] or None, "rule2": t["pass_rule_text"],
                 "src": first_source.get(("nutrition_thresholds", t["threshold_code"])), "notes": t["entry_notes"], "nut": t["nutrient_code"],
                 "grp": t["target_group"], "sex": t["sex"], "amin": t["age_min"], "amax": t["age_max"], "bmi": t["bmi_group"], "cmp": t["comparator"],
                 "b": batch["Data_Nutrition_Thresholds"], "basis": t["basis"], "v": version}
            if one("SELECT 1 FROM nutrition_thresholds WHERE threshold_code = :code", p):
                run("""UPDATE nutrition_thresholds SET goal = :goal, metric = :metric, min_value = :lo, max_value = :hi, unit = :unit, meal_context = :ctx,
                         pass_rule = :rule, source = :src, notes = :notes, nutrient_code = :nut, target_group = :grp, sex = :sex, age_min = :amin,
                         age_max = :amax, bmi_group = :bmi, comparator = :cmp, pass_rule_text = :rule2, is_active = TRUE, import_batch_id = :b,
                         basis = :basis, dataset_version_code = :v WHERE threshold_code = :code""", p)
            else:
                run("""INSERT INTO nutrition_thresholds (id, threshold_code, goal, metric, min_value, max_value, unit, meal_context, pass_rule, source, notes, priority,
                         nutrient_code, target_group, sex, age_min, age_max, bmi_group, comparator, pass_rule_text, is_active, import_batch_id, basis, dataset_version_code)
                       VALUES (gen_random_uuid(), :code, :goal, :metric, :lo, :hi, :unit, :ctx, :rule, :src, :notes, 1, :nut, :grp, :sex, :amin, :amax, :bmi,
                               :cmp, :rule2, TRUE, :b, :basis, :v)""", p)
        stats["nutrition_thresholds"] = len(b.thresholds)

        # ---- profile rules, recipes, evaluation
        conn.execute(text("""INSERT INTO profile_classification_rules (rule_code, rule_name, target_group, input_field, operator, min_value, max_value, unit,
                               classification_result, priority)
                             VALUES (:rule_code, :rule_name, :target_group, :input_field, :op, :min_value, :max_value, :unit, :classification_result, :priority)
                             ON CONFLICT (rule_code) DO UPDATE SET rule_name = EXCLUDED.rule_name, target_group = EXCLUDED.target_group,
                               input_field = EXCLUDED.input_field, operator = EXCLUDED.operator, min_value = EXCLUDED.min_value, max_value = EXCLUDED.max_value,
                               unit = EXCLUDED.unit, classification_result = EXCLUDED.classification_result, priority = EXCLUDED.priority"""),
                     [{**r, "op": OPERATORS.get(r["operator"], r["operator"])} for r in b.profile_rules])
        for rec in b.recipes:
            rid = one("""INSERT INTO smoothie_recipes (recipe_code, name_vi, target_goal, total_weight_g, serving_ml, preparation_steps_vi, why_suitable_vi,
                                                         safety_warning_vi, data_quality_status, entry_notes)
                         VALUES (:code, :name, :goal, :w, :ml, :steps, :why, :warn, :st, :notes)
                         ON CONFLICT (recipe_code) DO UPDATE SET name_vi = EXCLUDED.name_vi, target_goal = EXCLUDED.target_goal,
                           total_weight_g = EXCLUDED.total_weight_g, serving_ml = EXCLUDED.serving_ml, preparation_steps_vi = EXCLUDED.preparation_steps_vi,
                           why_suitable_vi = EXCLUDED.why_suitable_vi, safety_warning_vi = EXCLUDED.safety_warning_vi,
                           data_quality_status = EXCLUDED.data_quality_status, entry_notes = EXCLUDED.entry_notes RETURNING id""",
                      {"code": rec["recipe_code"], "name": rec["name_vi"], "goal": rec["target_goal"], "w": rec["total_weight_g"], "ml": rec["serving_ml"],
                       "steps": rec["preparation_steps_vi"], "why": rec["why_suitable_vi"], "warn": rec["safety_warning_vi"],
                       "st": rec["data_quality_status"], "notes": rec["entry_notes"]})
            run("DELETE FROM recipe_ingredients WHERE recipe_id = :r", {"r": rid})
            per_ing: dict[Any, dict] = {}
            for it in rec["items"]:
                if it["ingredient_code"] in ing_id and it["amount"]:
                    cur = per_ing.setdefault(ing_id[it["ingredient_code"]], {"amount": 0.0, "unit": it["unit"], "order": it["sort_order"] + 1, "raw": []})
                    cur["amount"] += it["amount"]
                    cur["raw"].append(it["raw_text"])
            for iid, cur in per_ing.items():
                run("""INSERT INTO recipe_ingredients (recipe_id, ingredient_id, amount, unit, amount_g, sort_order, raw_text)
                       VALUES (:r, :i, :a, :u, :a2, :o, :t)""",
                    {"r": rid, "i": iid, "a": cur["amount"], "a2": cur["amount"], "u": cur["unit"], "o": cur["order"], "t": "; ".join(cur["raw"])})
        stats["smoothie_recipes"] = len(b.recipes)

        conn.execute(text("""INSERT INTO eval_auto_criteria (criterion_code, name_vi, metric, check_type, pass_condition, fail_condition, severity, is_required,
                               related_rule_code, implementation_notes)
                             VALUES (:criterion_code, :name_vi, :metric, :check_type, :pass_condition, :fail_condition, :severity, :is_required,
                                     :related_rule_code, :implementation_notes)
                             ON CONFLICT (criterion_code) DO UPDATE SET name_vi = EXCLUDED.name_vi, metric = EXCLUDED.metric, check_type = EXCLUDED.check_type,
                               pass_condition = EXCLUDED.pass_condition, fail_condition = EXCLUDED.fail_condition, severity = EXCLUDED.severity,
                               is_required = EXCLUDED.is_required, related_rule_code = EXCLUDED.related_rule_code,
                               implementation_notes = EXCLUDED.implementation_notes"""),
                     [{**c, "metric": c["metric"] or "unknown", "check_type": c["check_type"] or "unknown", "severity": c["severity"] or "medium"} for c in b.eval_auto])
        if b.eval_rubric:
            # the table stores the score below which the whole recipe fails; the sheet's TRUE/FALSE maps to the pass threshold / NULL
            conn.execute(text("""INSERT INTO eval_rubric_criteria (criterion_code, name_vi, score_min, score_max, pass_threshold, auto_fail_if_below,
                                   low_description_vi, high_description_vi)
                                 VALUES (:criterion_code, :name_vi, :score_min, :score_max, :pass_threshold, :fail, :low_desc_vi, :high_desc_vi)
                                 ON CONFLICT (criterion_code) DO UPDATE SET name_vi = EXCLUDED.name_vi, score_min = EXCLUDED.score_min, score_max = EXCLUDED.score_max,
                                   pass_threshold = EXCLUDED.pass_threshold, auto_fail_if_below = EXCLUDED.auto_fail_if_below,
                                   low_description_vi = EXCLUDED.low_description_vi, high_description_vi = EXCLUDED.high_description_vi"""),
                         [{**c, "fail": c["pass_threshold"] if c["auto_fail_if_below"] else None} for c in b.eval_rubric])
        templates = [t for t in b.eval_templates if t["purpose"]]
        if templates:
            conn.execute(text("""INSERT INTO eval_profile_templates (template_code, age_min, age_max, sex, height_cm_min, height_cm_max, weight_kg_min, weight_kg_max,
                                   bmi_group, activity_level, allergy_scenario, disliked_scenario, preferred_scenario, medical_note_scenario, sample_count, purpose)
                                 VALUES (:template_code, :age_min, :age_max, :sex, :height_cm_min, :height_cm_max, :weight_kg_min, :weight_kg_max, :bmi_group,
                                         :activity_level, :allergy_scenario, :disliked_scenario, :preferred_scenario, :medical_note_scenario, :n, :purpose)
                                 ON CONFLICT (template_code) DO UPDATE SET age_min = EXCLUDED.age_min, age_max = EXCLUDED.age_max, sex = EXCLUDED.sex,
                                   height_cm_min = EXCLUDED.height_cm_min, height_cm_max = EXCLUDED.height_cm_max, weight_kg_min = EXCLUDED.weight_kg_min,
                                   weight_kg_max = EXCLUDED.weight_kg_max, bmi_group = EXCLUDED.bmi_group, activity_level = EXCLUDED.activity_level,
                                   allergy_scenario = EXCLUDED.allergy_scenario, disliked_scenario = EXCLUDED.disliked_scenario,
                                   preferred_scenario = EXCLUDED.preferred_scenario, medical_note_scenario = EXCLUDED.medical_note_scenario,
                                   sample_count = EXCLUDED.sample_count, purpose = EXCLUDED.purpose"""),
                         [{**t, "n": t["sample_count"] or 1} for t in templates])

        # ---- knowledge chunks for the AI (embedding kept when content did not change)
        for ch in chunks:
            digest = _hash(ch["content"], ch["meta"])
            run("""INSERT INTO nutrition_knowledge (id, title, ingredient_name, category, allowed_for_smoothie, content, source, tags, ingredient_id,
                                                      dataset_version_code, chunk_type, entity_table, entity_code, metadata, content_hash)
                   VALUES (gen_random_uuid(), :title, :iname, :cat, TRUE, :content, :src, CAST('[]' AS json), :iid, :v, :type, :tbl, :code, CAST(:meta AS jsonb), :h)
                   ON CONFLICT (entity_table, entity_code, chunk_type) WHERE entity_code IS NOT NULL DO UPDATE SET
                     title = EXCLUDED.title, ingredient_name = EXCLUDED.ingredient_name, category = EXCLUDED.category, content = EXCLUDED.content,
                     source = EXCLUDED.source, ingredient_id = EXCLUDED.ingredient_id, dataset_version_code = EXCLUDED.dataset_version_code,
                     metadata = EXCLUDED.metadata, updated_at = NOW(),
                     embedding = CASE WHEN nutrition_knowledge.content_hash = EXCLUDED.content_hash THEN nutrition_knowledge.embedding END,
                     embedding_model = CASE WHEN nutrition_knowledge.content_hash = EXCLUDED.content_hash THEN nutrition_knowledge.embedding_model END,
                     content_hash = EXCLUDED.content_hash""",
                {"title": ch["title"][:255], "iname": ch["ingredient_name"], "cat": ch["category"], "content": ch["content"], "src": ch["source"],
                 "iid": ing_id.get(ch["code"]) if ch["table"] == "ingredients" else None, "v": version, "type": ch["type"], "tbl": ch["table"],
                 "code": ch["code"], "meta": json.dumps(ch["meta"], ensure_ascii=False), "h": digest})
        stats["knowledge_chunks"] = len(chunks)

        if embed and commit:
            from app.config import settings
            from app.services.vector_service import VectorService

            service = VectorService()
            pending = run("SELECT id, content FROM nutrition_knowledge WHERE embedding IS NULL AND entity_code IS NOT NULL").all()
            for row in pending:
                run("UPDATE nutrition_knowledge SET embedding = CAST(:e AS vector), embedding_model = :m WHERE id = :id",
                    {"e": str(service.create_embedding(row.content)), "m": settings.embedding_model, "id": row.id})
            stats["embedded"] = len(pending)

        # publish last: any failure above rolls back and the previous version stays current
        run("UPDATE dataset_versions SET is_current = FALSE WHERE is_current")
        run("UPDATE dataset_versions SET is_current = TRUE WHERE version_code = :v", {"v": version})
        # sanity queries against the freshly loaded data (visible inside this transaction even when it is rolled back)
        stats["usable_candidates"] = one("SELECT count(*) FROM ai.candidate_ingredients('{}', '{}', NULL, NULL, 0.5, 1000)")
        stats["candidates_without_soy"] = one("SELECT count(*) FROM ai.candidate_ingredients(ARRAY['soy_allergy'], '{}', NULL, NULL, 0.5, 1000)")
        stats["candidates_without_milk"] = one("SELECT count(*) FROM ai.candidate_ingredients(ARRAY['milk_allergy'], '{}', NULL, NULL, 0.5, 1000)")
        stats["recipes_with_energy"] = one("SELECT count(*) FROM ai.v_recipe_nutrition WHERE energy_kcal IS NOT NULL")
        if commit:
            trans.commit()
        else:
            trans.rollback()
    except Exception:
        trans.rollback()
        raise
    finally:
        conn.close()
    return stats
