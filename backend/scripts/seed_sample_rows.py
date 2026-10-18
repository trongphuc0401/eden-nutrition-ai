"""Insert ONE sample row per reference table, taken from the research workbook (not a full import).

  python scripts/seed_sample_rows.py data/workbook/ai_dinh_duong.xlsx          # writes
  python scripts/seed_sample_rows.py data/workbook/ai_dinh_duong.xlsx --dry-run

Idempotent: re-running adds nothing. The sample follows one story so the rows join up:
soy milk (ING_FRUIT_0132) -> soy_allergy -> SAFE_ALLERGY_009, used by REC_EXAMPLE_001 with pomelo.
"""
import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(str(Path(__file__).resolve().parents[1]))

import openpyxl  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402
from app.services.reference_import import catalog  # noqa: E402
from app.services.reference_import.normalizers import normalize_name  # noqa: E402
from app.services.reference_import.pipeline import build_bundle  # noqa: E402

SOY_MILK = "ING_FRUIT_0132"
POMELO = "ING_FRUIT_0001"
RULE = "SAFE_ALLERGY_009"
THRESHOLD = "THR_LIPID_001"
PROFILE_RULE = "PROFILE_BMI_001"
RECIPE = "REC_EXAMPLE_001"
AUTO = "AUTO_SAFE_001"
RUBRIC = "RUBRIC_SAFETY_001"
TEMPLATE = "PROFILE_TEMPLATE_001"
VERSION = "v1.0"
CORE = {"water_g", "energy_kcal", "protein_g", "fat_g", "carbohydrate_g", "fiber_g", "total_sugar_g",
        "sodium_mg", "potassium_mg", "calcium_mg", "iron_mg", "vitamin_c_mg"}
CATEGORY = {"roots_tubers": "vegetable", "dairy": "liquid"}  # public.ingredients allows no roots_tubers/dairy


def pick(rows, key, value):
    return next(r for r in rows if r[key] == value)


def card(ing, names):
    core = [f"{names[n['nutrient_code']]['name_vi']} {n['value_per_100g']:g} {names[n['nutrient_code']]['unit']}"
            for n in ing["nutrients"] if n["nutrient_code"] in CORE and n["value_per_100g"] is not None]
    allergens = ", ".join(catalog.CONDITIONS[c["condition_code"]][1] for c in ing["conditions"])
    return (f"{ing['name_vi']} ({ing['name_en'] or ''}) - nhóm {ing['category']}. Trên 100g: {'; '.join(core)}."
            + (f" Lưu ý dị ứng/bệnh lý: {allergens}." if allergens else "")
            + f" Trạng thái dữ liệu: {ing['data_status']}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("xlsx", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    b = build_bundle(args.xlsx)
    names = {n["code"]: n for n in b.nutrients}
    soy = pick(b.ingredients, "ingredient_code", SOY_MILK)
    rule = pick(b.safety_rules, "rule_code", RULE)
    thr = pick(b.thresholds, "threshold_code", THRESHOLD)
    prof = pick(b.profile_rules, "rule_code", PROFILE_RULE)
    recipe = pick(b.recipes, "recipe_code", RECIPE)
    auto = pick(b.eval_auto, "criterion_code", AUTO)
    rubric = pick(b.eval_rubric, "criterion_code", RUBRIC)
    template = pick(b.eval_templates, "template_code", TEMPLATE)
    condition = pick(b.conditions, "code", "soy_allergy")
    source_codes = {c["source_code"] for c in b.citations
                    if c["entity_code"] in (THRESHOLD, PROFILE_RULE, RULE, SOY_MILK) or c["entity_table"] == "clinical_safety_rules" and c["entity_code"] == RULE}
    sources = [s for s in b.sources if s["source_code"] in source_codes | {soy["primary_source_code"]}]
    citations = [c for c in b.citations if c["entity_code"] in (THRESHOLD, PROFILE_RULE, RULE)]

    ws = next(w for w in openpyxl.load_workbook(args.xlsx, data_only=True).worksheets if w.title == "Data_Ingredients")
    raw = {"ingredient_code": ws.cell(soy["_row"], 1).value, "name_vi": ws.cell(soy["_row"], 2).value}
    raw["nutrients"] = {n["code"]: str(ws.cell(soy["_row"], n["col"] + 1).value) for n in catalog.NUTRIENTS
                        if ws.cell(soy["_row"], n["col"] + 1).value not in (None, "")}
    row_issues = [i for i in b.issues if i.sheet == "Data_Ingredients" and i.row_no == soy["_row"]][:3]

    print(f"Sample story: {soy['name_vi']} ({SOY_MILK}) -> {condition['name_vi']} -> {RULE}; recipe {RECIPE}")
    if args.dry_run:
        print("Dry run: nothing written.")
        return

    with engine.begin() as c:
        one = lambda sql, **p: c.execute(text(sql), p).scalar()  # noqa: E731
        run = lambda sql, **p: c.execute(text(sql), p)           # noqa: E731

        batch = one("SELECT id FROM import_batches WHERE file_checksum = :c AND sheet_name = 'Data_Ingredients (sample)'", c=b.file_checksum)
        if batch is None:
            batch = one("""INSERT INTO import_batches (dataset_version_code, sheet_name, file_checksum, rows_ok, rows_rejected, errors)
                           VALUES (:v, 'Data_Ingredients (sample)', :c, 1, 0, CAST(:e AS jsonb)) RETURNING id""",
                        v=VERSION, c=b.file_checksum,
                        e=json.dumps([{"col": i.col, "severity": i.severity, "message": i.message} for i in row_issues], ensure_ascii=False))

        for s in sources:
            run("""INSERT INTO data_sources (source_code, title, source_type, author_or_org, published_year, url_or_file, locator,
                                              reliability_level, used_for, notes)
                   VALUES (:source_code, :title, COALESCE(:source_type, 'website'), :author_or_org, :year, :url_or_file, :locator,
                           :reliability_level, :used_for, :notes) ON CONFLICT (source_code) DO NOTHING""", **s)

        # nutrients: only the config this layer needs (core flag, ceiling) + the one missing code
        for code, n in names.items():
            if code in CORE:
                run("""INSERT INTO nutrients (nutrient_code, name_vi, name_en, unit, nutrient_group, display_order, sheet_header, is_core, plausible_max_per_100g)
                       VALUES (:code, :name_vi, :name_en, :unit, :group, :display_order, NULL, TRUE, :plausible_max)
                       ON CONFLICT (nutrient_code) DO UPDATE SET is_core = TRUE, plausible_max_per_100g = EXCLUDED.plausible_max_per_100g""", **n)
        existing = {r[0] for r in run("SELECT nutrient_code FROM nutrients")}

        run("""INSERT INTO health_conditions (condition_code, name_vi, name_en, condition_type, keywords_vi)
               VALUES (:c, :n, 'Soy allergy', :t, :k) ON CONFLICT (condition_code) DO NOTHING""",
            c=condition["code"], n=condition["name_vi"], t=condition["condition_type"], k=condition["keywords_vi"])

        ing_id = {}
        for ing in (soy, pick(b.ingredients, "ingredient_code", POMELO)):
            found = one("SELECT id FROM ingredients WHERE ingredient_code = :c", c=ing["ingredient_code"])
            if found is None:
                found = one("""INSERT INTO ingredients (ingredient_code, name_vi, name_en, name_normalized, category, processing_state, origin_country,
                                                         growing_regions, allowed_for_smoothie, data_status, primary_source_code, entry_notes, dataset_version_code)
                               VALUES (:code, :vi, :en, :norm, :cat, COALESCE(:state, 'fresh'), :country, :regions, :allowed, :status, :src, :notes, :v)
                               RETURNING id""",
                            code=ing["ingredient_code"], vi=ing["name_vi"], en=ing["name_en"], norm=normalize_name(ing["name_vi"]),
                            cat=CATEGORY.get(ing["category"], ing["category"]), state=ing["processing_state"], country=ing["origin_country"],
                            regions=ing["growing_regions"], allowed=ing["allowed_for_smoothie"], status=ing["data_status"],
                            src=ing["primary_source_code"], notes=ing["entry_notes"], v=VERSION)
            ing_id[ing["ingredient_code"]] = found

        sid = ing_id[SOY_MILK]
        for n in soy["nutrients"]:
            if n["nutrient_code"] not in existing:
                continue
            value, status = n["value_per_100g"], ("measured" if n["value_per_100g"] is not None else "not_available")
            run("""INSERT INTO ingredient_nutrients (ingredient_id, nutrient_code, value_per_100g, value_status, source_code, import_batch_id, needs_review, review_note)
                   VALUES (:i, :n, :v, :s, :src, :b, :nr, :note) ON CONFLICT (ingredient_id, nutrient_code) DO NOTHING""",
                i=sid, n=n["nutrient_code"], v=value, s=status, src=n["source_code"], b=batch,
                nr=n["value_status"] == "repaired", note="Excel đã đổi số thành ngày; giá trị dựng lại từ ngày/tháng, cần kiểm tra lại" if n["value_status"] == "repaired" else None)
        for s in soy["seasons"]:
            run("""INSERT INTO ingredient_seasons (ingredient_id, region_label, region_scope, months, year_round)
                   VALUES (:i, :l, :sc, :m, :y) ON CONFLICT (ingredient_id, region_label) DO NOTHING""",
                i=sid, l=s["region_label"], sc=s["region_scope"], m=s["months"], y=s["year_round"])
        run("""INSERT INTO ingredient_aliases (ingredient_id, alias, alias_normalized, language_code)
               VALUES (:i, 'Soy milk', :n, 'en') ON CONFLICT DO NOTHING""", i=sid, n=normalize_name("Soy milk"))
        run("""INSERT INTO ingredient_conditions (ingredient_id, condition_code, relation, notes)
               VALUES (:i, 'soy_allergy', 'contains_allergen', 'Tự gán theo từ khoá tên nguyên liệu; chuyên gia cần xác nhận') ON CONFLICT DO NOTHING""", i=sid)

        for ct in citations:
            run("""INSERT INTO source_citations (entity_table, entity_code, source_code) VALUES (:t, :c, :s) ON CONFLICT DO NOTHING""",
                t=ct["entity_table"], c=ct["entity_code"], s=ct["source_code"])

        if not one("SELECT 1 FROM clinical_safety_rules WHERE rule_code = :c", c=RULE):
            run("""INSERT INTO clinical_safety_rules
                     (id, rule_code, condition_key, risk_type, ingredient_or_nutrient, action, severity, threshold_value, unit, warning_message, source, notes,
                      condition_code, target_type, target_text, avoid_or_limit, warning_message_vi, recommended_action, is_active, entry_notes,
                      import_batch_id, dataset_version_code)
                   VALUES (gen_random_uuid(), :code, :cond, :risk, :target, :action, :sev, :thr, :unit, :msg, :src, :notes,
                           :cond2, 'ingredient_group', :target2, :aol, :msg2, :action2, TRUE, :notes2, :b, :v)""",
                code=RULE, cond=rule["condition_code"], risk=rule["risk_type"], target=rule["target_text"], action=rule["action"], sev=rule["severity"],
                thr=rule["threshold_value"], unit=rule["unit"], msg=rule["warning_message_vi"], src="SRC_MDPI_2023_BM", notes=rule["entry_notes"],
                aol=rule["avoid_or_limit"], b=batch, v=VERSION, cond2=rule["condition_code"], target2=rule["target_text"],
                msg2=rule["warning_message_vi"], action2=rule["action"], notes2=rule["entry_notes"])

        if not one("SELECT 1 FROM nutrition_thresholds WHERE threshold_code = :c", c=THRESHOLD):
            run("""INSERT INTO nutrition_thresholds
                     (id, threshold_code, goal, metric, min_value, max_value, unit, meal_context, pass_rule, source, notes, priority,
                      nutrient_code, target_group, sex, age_min, age_max, bmi_group, comparator, pass_rule_text, is_active, import_batch_id,
                      basis, dataset_version_code)
                   VALUES (gen_random_uuid(), :code, :goal, :metric, :lo, :hi, :unit, :ctx, :rule, 'SRC_2892_QD_BYT', :notes, 1,
                           :nut, :grp, :sex, :amin, :amax, :bmi, :cmp, :rule2, TRUE, :b, :basis, :v)""",
                code=THRESHOLD, goal=thr["target_group"], metric=thr["metric_raw"], lo=thr["min_value"], hi=thr["max_value"], unit=thr["unit"] or "%",
                ctx=thr["meal_context"], rule=thr["pass_rule_text"], notes=thr["entry_notes"], nut=thr["nutrient_code"], grp=thr["target_group"],
                sex=thr["sex"], amin=thr["age_min"], amax=thr["age_max"], bmi=thr["bmi_group"], cmp=thr["comparator"], b=batch,
                basis=thr["basis"], v=VERSION, rule2=thr["pass_rule_text"])

        ops = {">=": "gte", "<=": "lte", ">": "gt", "<": "lt"}
        run("""INSERT INTO profile_classification_rules (rule_code, rule_name, target_group, input_field, operator, min_value, max_value, unit, classification_result, priority)
               VALUES (:code, :name, :grp, :field, :op, :lo, :hi, :unit, :res, :pr) ON CONFLICT (rule_code) DO NOTHING""",
            code=prof["rule_code"], name=prof["rule_name"], grp=prof["target_group"], field=prof["input_field"], op=ops.get(prof["operator"], prof["operator"]),
            lo=prof["min_value"], hi=prof["max_value"], unit=prof["unit"], res=prof["classification_result"], pr=prof["priority"])

        rid = one("SELECT id FROM smoothie_recipes WHERE recipe_code = :c", c=RECIPE)
        if rid is None:
            rid = one("""INSERT INTO smoothie_recipes (recipe_code, name_vi, target_goal, total_weight_g, serving_ml, preparation_steps_vi, why_suitable_vi,
                                                       safety_warning_vi, data_quality_status, entry_notes)
                         VALUES (:code, :name, :goal, :w, :ml, :steps, :why, :warn, :st, :notes) RETURNING id""",
                      code=RECIPE, name=recipe["name_vi"], goal=recipe["target_goal"], w=recipe["total_weight_g"], ml=recipe["serving_ml"],
                      steps=recipe["preparation_steps_vi"], why=recipe["why_suitable_vi"], warn=recipe["safety_warning_vi"],
                      st=recipe["data_quality_status"], notes=recipe["entry_notes"])
        for it in recipe["items"]:
            if it["ingredient_code"] in ing_id and it["amount"]:
                run("""INSERT INTO recipe_ingredients (recipe_id, ingredient_id, amount, unit, amount_g, sort_order, raw_text)
                       VALUES (:r, :i, :a, :u, :a, :o, :t) ON CONFLICT DO NOTHING""",
                    r=rid, i=ing_id[it["ingredient_code"]], a=it["amount"], u=it["unit"], o=it["sort_order"] + 1, t=it["raw_text"])

        run("""INSERT INTO eval_auto_criteria (criterion_code, name_vi, metric, check_type, pass_condition, fail_condition, severity, is_required, related_rule_code, implementation_notes)
               VALUES (:code, :name, :metric, :chk, :pc, :fc, :sev, :req, :rel, :notes) ON CONFLICT (criterion_code) DO NOTHING""",
            code=auto["criterion_code"], name=auto["name_vi"], metric=auto["metric"] or "unknown", chk=auto["check_type"] or "unknown",
            pc=auto["pass_condition"], fc=auto["fail_condition"], sev=auto["severity"] or "medium", req=auto["is_required"],
            rel=auto["related_rule_code"], notes=auto["implementation_notes"])

        # sheet says auto_fail_if_below = TRUE; the table stores the score below which the whole recipe fails -> the pass threshold
        run("""INSERT INTO eval_rubric_criteria (criterion_code, name_vi, score_min, score_max, pass_threshold, auto_fail_if_below, low_description_vi, high_description_vi)
               VALUES (:code, :name, :lo, :hi, :thr, :fail, :low, :high) ON CONFLICT (criterion_code) DO NOTHING""",
            code=rubric["criterion_code"], name=rubric["name_vi"], lo=rubric["score_min"], hi=rubric["score_max"], thr=rubric["pass_threshold"],
            fail=rubric["pass_threshold"] if rubric["auto_fail_if_below"] else None, low=rubric["low_desc_vi"], high=rubric["high_desc_vi"])

        run("""INSERT INTO eval_profile_templates (template_code, age_min, age_max, sex, height_cm_min, height_cm_max, weight_kg_min, weight_kg_max, bmi_group,
                                                   activity_level, allergy_scenario, disliked_scenario, preferred_scenario, medical_note_scenario, sample_count, purpose)
               VALUES (:code, :a0, :a1, :sex, :h0, :h1, :w0, :w1, :bmi, :act, :al, :di, :pr, :me, :n, :pu) ON CONFLICT (template_code) DO NOTHING""",
            code=template["template_code"], a0=template["age_min"], a1=template["age_max"], sex=template["sex"], h0=template["height_cm_min"],
            h1=template["height_cm_max"], w0=template["weight_kg_min"], w1=template["weight_kg_max"], bmi=template["bmi_group"], act=template["activity_level"],
            al=template["allergy_scenario"], di=template["disliked_scenario"], pr=template["preferred_scenario"], me=template["medical_note_scenario"],
            n=template["sample_count"] or 1, pu=template["purpose"])

        run("""INSERT INTO nutrition_knowledge (id, title, ingredient_name, category, allowed_for_smoothie, content, source, tags, ingredient_id, dataset_version_code,
                                                chunk_type, entity_table, entity_code, metadata, content_hash)
               VALUES (gen_random_uuid(), :t, :n, :cat, TRUE, :content, :src, CAST('[]' AS json), :i, :v, 'ingredient_card', 'ingredients', :code, CAST(:meta AS jsonb), 'sample')
               ON CONFLICT (entity_table, entity_code, chunk_type) WHERE entity_code IS NOT NULL DO NOTHING""",
            t=f"{soy['name_vi']} - thẻ nguyên liệu", n=soy["name_vi"].lower(), cat=soy["category"], content=card(soy, names), src=soy["primary_source_code"],
            i=sid, v=VERSION, code=SOY_MILK, meta=json.dumps({"conditions": ["soy_allergy"], "sample": True}))

        run("""INSERT INTO staging.raw_rows (batch_id, sheet, row_no, payload) VALUES (:b, 'Data_Ingredients', :r, CAST(:p AS jsonb)) ON CONFLICT DO NOTHING""",
            b=batch, r=soy["_row"], p=json.dumps(raw, ensure_ascii=False))
        if not one("SELECT 1 FROM staging.row_errors WHERE batch_id = :b", b=batch):
            for i in row_issues:
                run("""INSERT INTO staging.row_errors (batch_id, sheet, row_no, col, value, severity, message) VALUES (:b, :s, :r, :c, :v, :sev, :m)""",
                    b=batch, s=i.sheet, r=i.row_no, c=i.col, v=i.value, sev=i.severity, m=i.message)

        run_id = one("SELECT id FROM eval_runs WHERE label = 'SAMPLE - not a real evaluation'")
        if run_id is None:
            run_id = one("""INSERT INTO eval_runs (dataset_version_code, label, model, config) VALUES (:v, 'SAMPLE - not a real evaluation', NULL, CAST(:c AS jsonb)) RETURNING id""",
                         v=VERSION, c=json.dumps({"sample": True}))
            run("""INSERT INTO eval_results (run_id, template_code, criterion_code, passed, score, details)
                   VALUES (:r, :t, :c, NULL, NULL, CAST(:d AS jsonb))""",
                r=run_id, t=TEMPLATE, c=AUTO, d=json.dumps({"sample": True, "note": "placeholder row to show the shape; no recipe was evaluated"}))

    print("Sample rows written.")


if __name__ == "__main__":
    main()
