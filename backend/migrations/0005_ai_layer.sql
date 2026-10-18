-- AI-facing layer over the reference tables: flat views and retrieval functions (schema `ai`).
-- Holds no data of its own. Depends on 0003_research_workbook_schema and 0004. Idempotent (CREATE OR REPLACE).

-- One row per ingredient with core nutrients pivoted wide + how many core nutrients are filled in.
CREATE OR REPLACE VIEW ai.v_ingredient_core AS
SELECT i.id, i.ingredient_code, i.name_vi, i.name_en, i.name_normalized, i.category,
       i.processing_state, i.allowed_for_smoothie, i.data_status, i.primary_source_code,
       max(n.value_per_100g) FILTER (WHERE n.nutrient_code = 'energy_kcal')   AS energy_kcal,
       max(n.value_per_100g) FILTER (WHERE n.nutrient_code = 'protein_g')     AS protein_g,
       max(n.value_per_100g) FILTER (WHERE n.nutrient_code = 'fat_g')         AS fat_g,
       max(n.value_per_100g) FILTER (WHERE n.nutrient_code = 'carbohydrate_g')        AS carb_g,
       max(n.value_per_100g) FILTER (WHERE n.nutrient_code = 'fiber_g')       AS fiber_g,
       max(n.value_per_100g) FILTER (WHERE n.nutrient_code = 'total_sugar_g') AS total_sugar_g,
       max(n.value_per_100g) FILTER (WHERE n.nutrient_code = 'sodium_mg')     AS sodium_mg,
       max(n.value_per_100g) FILTER (WHERE n.nutrient_code = 'vitamin_c_mg')  AS vitamin_c_mg,
       (count(*) FILTER (WHERE c.is_core AND n.value_per_100g IS NOT NULL))::numeric
         / NULLIF((SELECT count(*) FROM nutrients WHERE is_core), 0)           AS core_coverage
  FROM ingredients i
  LEFT JOIN ingredient_nutrients n ON n.ingredient_id = i.id
  LEFT JOIN nutrients c ON c.nutrient_code = n.nutrient_code
 GROUP BY i.id;

-- Recipe totals are always computed from ingredient data, never typed by hand.
CREATE OR REPLACE VIEW ai.v_recipe_nutrition AS
SELECT r.recipe_code, r.name_vi,
       (SELECT sum(x.amount_g) FROM recipe_ingredients x WHERE x.recipe_id = r.id)              AS total_g,
       sum(ri.amount_g / 100 * n.value_per_100g) FILTER (WHERE n.nutrient_code = 'energy_kcal')   AS energy_kcal,
       sum(ri.amount_g / 100 * n.value_per_100g) FILTER (WHERE n.nutrient_code = 'protein_g')     AS protein_g,
       sum(ri.amount_g / 100 * n.value_per_100g) FILTER (WHERE n.nutrient_code = 'fat_g')         AS fat_g,
       sum(ri.amount_g / 100 * n.value_per_100g) FILTER (WHERE n.nutrient_code = 'carbohydrate_g')        AS carb_g,
       sum(ri.amount_g / 100 * n.value_per_100g) FILTER (WHERE n.nutrient_code = 'fiber_g')       AS fiber_g,
       sum(ri.amount_g / 100 * n.value_per_100g) FILTER (WHERE n.nutrient_code = 'total_sugar_g') AS total_sugar_g,
       (SELECT count(*) FROM recipe_ingredients x WHERE x.recipe_id = r.id AND x.amount_g IS NULL) AS ingredients_without_grams
  FROM smoothie_recipes r
  JOIN recipe_ingredients ri ON ri.recipe_id = r.id
  LEFT JOIN ingredient_nutrients n ON n.ingredient_id = ri.ingredient_id
 GROUP BY r.id, r.recipe_code, r.name_vi;

-- Ingredients the LLM may choose from: no allergen/avoid link for the user's conditions, not disliked,
-- enough nutrient data; in-season ones ranked first.
CREATE OR REPLACE FUNCTION ai.candidate_ingredients(
    p_condition_codes text[]  DEFAULT '{}',
    p_disliked        text[]  DEFAULT '{}',
    p_month           int     DEFAULT NULL,
    p_region_scope    text    DEFAULT NULL,
    p_min_coverage    numeric DEFAULT 0.5,
    p_limit           int     DEFAULT 40)
RETURNS TABLE (ingredient_code text, name_vi text, category text, in_season boolean, core_coverage numeric)
LANGUAGE sql STABLE AS $$
    SELECT v.ingredient_code::text, v.name_vi::text, v.category::text,
           COALESCE(s.in_season, FALSE), v.core_coverage
      FROM ai.v_ingredient_core v
      LEFT JOIN LATERAL (
            SELECT bool_or(se.year_round OR p_month = ANY (se.months)) AS in_season
              FROM ingredient_seasons se
             WHERE se.ingredient_id = v.id
               AND (p_region_scope IS NULL OR se.region_scope IN ('all', p_region_scope))
      ) s ON TRUE
     WHERE v.allowed_for_smoothie
       AND COALESCE(v.core_coverage, 0) >= p_min_coverage
       AND NOT EXISTS (SELECT 1 FROM ingredient_conditions ic
                        WHERE ic.ingredient_id = v.id
                          AND ic.condition_code = ANY (p_condition_codes)
                          AND ic.relation IN ('contains_allergen', 'should_avoid'))
       AND NOT EXISTS (SELECT 1 FROM unnest(p_disliked) d
                        WHERE v.name_normalized = ai.f_unaccent(d)
                           OR EXISTS (SELECT 1 FROM ingredient_aliases a
                                       WHERE a.ingredient_id = v.id AND a.alias_normalized = ai.f_unaccent(d)))
     ORDER BY COALESCE(s.in_season, FALSE) DESC, v.core_coverage DESC NULLS LAST, v.ingredient_code
     LIMIT p_limit
$$;

-- Compact JSON "ingredient cards" for the prompt (core nutrients only, NULLs dropped).
CREATE OR REPLACE FUNCTION ai.ingredient_cards(p_codes text[])
RETURNS TABLE (ingredient_code text, card jsonb)
LANGUAGE sql STABLE AS $$
    SELECT i.ingredient_code::text,
           jsonb_strip_nulls(jsonb_build_object(
               'name', i.name_vi, 'name_en', i.name_en, 'category', i.category,
               'per_100g', (SELECT jsonb_object_agg(n.nutrient_code, n.value_per_100g)
                              FROM ingredient_nutrients n
                              JOIN nutrients c ON c.nutrient_code = n.nutrient_code AND c.is_core
                             WHERE n.ingredient_id = i.id AND n.value_per_100g IS NOT NULL),
               'allergen_for', (SELECT jsonb_agg(ic.condition_code) FROM ingredient_conditions ic
                                 WHERE ic.ingredient_id = i.id AND ic.relation = 'contains_allergen'),
               'source', i.primary_source_code, 'data_status', i.data_status))
      FROM ingredients i
     WHERE i.ingredient_code = ANY (p_codes)
$$;

-- Hybrid search over nutrition_knowledge: vector rank + full-text rank fused with Reciprocal Rank Fusion.
-- Searches every chunk; the importer replaces chunks in place, so there is no version filter.
CREATE OR REPLACE FUNCTION ai.match_chunks(
    p_query_embedding vector(1536),
    p_query_text      text,
    p_chunk_types     text[] DEFAULT NULL,
    p_k               int    DEFAULT 8)
RETURNS TABLE (chunk_id uuid, entity_code text, chunk_type text, content text, metadata jsonb, score double precision)
LANGUAGE sql STABLE AS $$
    WITH base AS (
        SELECT k.* FROM nutrition_knowledge k
         WHERE (p_chunk_types IS NULL OR k.chunk_type = ANY (p_chunk_types))
    ),
    vec AS (
        SELECT id, row_number() OVER (ORDER BY embedding <=> p_query_embedding) AS r
          FROM base WHERE p_query_embedding IS NOT NULL AND embedding IS NOT NULL
         ORDER BY embedding <=> p_query_embedding LIMIT 50
    ),
    txt AS (
        SELECT id, row_number() OVER (ORDER BY ts_rank_cd(fts, q) DESC) AS r
          FROM base, plainto_tsquery('simple', ai.f_unaccent(COALESCE(p_query_text, ''))) q
         WHERE fts @@ q ORDER BY ts_rank_cd(fts, q) DESC LIMIT 50
    )
    SELECT b.id, b.entity_code::text, b.chunk_type::text, b.content, b.metadata,
           COALESCE(1.0 / (60 + v.r), 0) + COALESCE(1.0 / (60 + t.r), 0)
      FROM base b
      LEFT JOIN vec v ON v.id = b.id
      LEFT JOIN txt t ON t.id = b.id
     WHERE v.id IS NOT NULL OR t.id IS NOT NULL
     ORDER BY 6 DESC
     LIMIT p_k
$$;

-- Map age/BMI to classifications using profile_classification_rules.
CREATE OR REPLACE FUNCTION ai.classify_profile(p_age numeric, p_height_cm numeric, p_weight_kg numeric)
RETURNS TABLE (input_field text, classification_result text, rule_code text)
LANGUAGE sql STABLE AS $$
    WITH facts AS (
        SELECT 'age'::text AS f, p_age AS v
        UNION ALL
        SELECT 'bmi', round(p_weight_kg / ((p_height_cm / 100.0) ^ 2), 2)
    )
    SELECT r.input_field::text, r.classification_result::text, r.rule_code::text
      FROM profile_classification_rules r
      JOIN facts ON facts.f = r.input_field
     WHERE r.is_active
       AND CASE r.operator
               WHEN 'between' THEN facts.v BETWEEN r.min_value AND r.max_value
               WHEN 'gte'     THEN facts.v >= r.min_value
               WHEN 'gt'      THEN facts.v >  r.min_value
               WHEN 'lte'     THEN facts.v <= COALESCE(r.max_value, r.min_value)
               WHEN 'lt'      THEN facts.v <  COALESCE(r.max_value, r.min_value)
               WHEN 'equals'  THEN facts.v =  r.min_value
           END
     ORDER BY r.priority
$$;
