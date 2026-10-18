-- Additive extension of the normalized reference tables that already exist in `public`
-- (ingredients, nutrients, ingredient_nutrients, data_sources, health_conditions, ...).
-- Nothing is dropped or renamed: this only adds the columns/tables the AI layer needs.
-- Idempotent: safe to re-run.

CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------- versions
-- Exactly one version is "current"; the AI layer reads only that one.
ALTER TABLE dataset_versions ADD COLUMN IF NOT EXISTS is_current BOOLEAN NOT NULL DEFAULT FALSE;
CREATE UNIQUE INDEX IF NOT EXISTS dataset_versions_one_current ON dataset_versions (is_current) WHERE is_current;

-- ---------------------------------------------------------------- nutrients
ALTER TABLE nutrients ADD COLUMN IF NOT EXISTS is_core BOOLEAN NOT NULL DEFAULT FALSE;           -- sent to the LLM
ALTER TABLE nutrients ADD COLUMN IF NOT EXISTS plausible_max_per_100g NUMERIC;                     -- import sanity ceiling

-- ---------------------------------------------------------------- ingredients
-- Values rebuilt from corrupted cells (Excel turned "8.3" into a date) are kept but flagged for review.
ALTER TABLE ingredient_nutrients ADD COLUMN IF NOT EXISTS needs_review BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE ingredient_nutrients ADD COLUMN IF NOT EXISTS review_note TEXT;
ALTER TABLE ingredient_seasons ADD COLUMN IF NOT EXISTS region_scope VARCHAR(12) NOT NULL DEFAULT 'all';
ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS dataset_version_code VARCHAR(80) REFERENCES dataset_versions(version_code);
ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ingredient_seasons_scope_valid') THEN
        ALTER TABLE ingredient_seasons ADD CONSTRAINT ingredient_seasons_scope_valid
            CHECK (region_scope IN ('north','central','south','all','province'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ingredients_name_trgm_idx ON ingredients USING gin (name_normalized gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ingredient_aliases_trgm_idx ON ingredient_aliases USING gin (alias_normalized gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ingredient_nutrients_nutrient_idx ON ingredient_nutrients (nutrient_code);
CREATE INDEX IF NOT EXISTS ingredient_seasons_months_idx ON ingredient_seasons USING gin (months);
CREATE INDEX IF NOT EXISTS ingredient_conditions_cond_idx ON ingredient_conditions (condition_code);

-- ---------------------------------------------------------------- conditions
-- keywords_vi maps free-text user notes ("tiểu đường") to condition codes without calling the LLM.
ALTER TABLE health_conditions ADD COLUMN IF NOT EXISTS keywords_vi TEXT[] NOT NULL DEFAULT '{}';

-- ---------------------------------------------------------------- thresholds
-- lipid/protein/carb limits are percent of energy, not grams; make that explicit.
ALTER TABLE nutrition_thresholds ADD COLUMN IF NOT EXISTS basis VARCHAR(16) NOT NULL DEFAULT 'absolute';
ALTER TABLE nutrition_thresholds ADD COLUMN IF NOT EXISTS dataset_version_code VARCHAR(80) REFERENCES dataset_versions(version_code);
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'nutrition_thresholds_basis_valid') THEN
        ALTER TABLE nutrition_thresholds ADD CONSTRAINT nutrition_thresholds_basis_valid
            CHECK (basis IN ('absolute','percent_energy'));
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS nutrition_thresholds_lookup_idx
    ON nutrition_thresholds (target_group, nutrient_code) WHERE is_active;

-- ---------------------------------------------------------------- safety rules
ALTER TABLE clinical_safety_rules ADD COLUMN IF NOT EXISTS dataset_version_code VARCHAR(80) REFERENCES dataset_versions(version_code);
CREATE INDEX IF NOT EXISTS clinical_safety_rules_cond_idx ON clinical_safety_rules (condition_code) WHERE is_active;

-- ---------------------------------------------------------------- recipes
ALTER TABLE recipe_ingredients ADD COLUMN IF NOT EXISTS raw_text TEXT;

-- ---------------------------------------------------------------- knowledge chunks (RAG)
-- nutrition_knowledge becomes the chunk table: one row per ingredient card / safety rule / threshold / recipe.
-- Existing columns and rows are untouched; new columns are nullable or defaulted.
ALTER TABLE nutrition_knowledge ADD COLUMN IF NOT EXISTS chunk_type VARCHAR(24) NOT NULL DEFAULT 'ingredient_card';
ALTER TABLE nutrition_knowledge ADD COLUMN IF NOT EXISTS entity_table VARCHAR(64);
ALTER TABLE nutrition_knowledge ADD COLUMN IF NOT EXISTS entity_code VARCHAR(120);
ALTER TABLE nutrition_knowledge ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE nutrition_knowledge ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);
ALTER TABLE nutrition_knowledge ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(80);
ALTER TABLE nutrition_knowledge ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- unaccent() is only STABLE; this wrapper is IMMUTABLE so it can back generated columns and indexes.
CREATE SCHEMA IF NOT EXISTS ai;
CREATE OR REPLACE FUNCTION ai.f_unaccent(value text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT SET search_path = public, extensions AS
$$ SELECT lower(unaccent('unaccent', value)) $$;

ALTER TABLE nutrition_knowledge
    ADD COLUMN IF NOT EXISTS fts TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple', ai.f_unaccent(content))) STORED;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'nutrition_knowledge_chunk_type_valid') THEN
        ALTER TABLE nutrition_knowledge ADD CONSTRAINT nutrition_knowledge_chunk_type_valid
            CHECK (chunk_type IN ('ingredient_card','safety_rule','threshold','recipe','source'));
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS nutrition_knowledge_entity_key
    ON nutrition_knowledge (entity_table, entity_code, chunk_type) WHERE entity_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS nutrition_knowledge_fts_idx ON nutrition_knowledge USING gin (fts);
CREATE INDEX IF NOT EXISTS nutrition_knowledge_metadata_idx ON nutrition_knowledge USING gin (metadata jsonb_path_ops);
CREATE INDEX IF NOT EXISTS nutrition_knowledge_type_idx ON nutrition_knowledge (chunk_type, dataset_version_code);
CREATE INDEX IF NOT EXISTS nutrition_knowledge_embedding_idx
    ON nutrition_knowledge USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- ---------------------------------------------------------------- evaluation history
-- Lets prompt/model changes be compared run to run.
CREATE TABLE IF NOT EXISTS eval_runs (
    id                   BIGSERIAL PRIMARY KEY,
    dataset_version_code VARCHAR(80) REFERENCES dataset_versions(version_code),
    label                VARCHAR(120),
    model                VARCHAR(80),
    config               JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS eval_results (
    id             BIGSERIAL PRIMARY KEY,
    run_id         BIGINT NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
    template_code  VARCHAR(80) REFERENCES eval_profile_templates(template_code),
    criterion_code VARCHAR(80) NOT NULL,
    passed         BOOLEAN,
    score          NUMERIC(6,2),
    details        JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS eval_results_run_idx ON eval_results (run_id, criterion_code);
-- New tables are closed to the public API (anon/authenticated); the backend role bypasses RLS.
ALTER TABLE eval_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_results ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------- app tables
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS activity_level VARCHAR(16);
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS condition_codes TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS region_scope VARCHAR(12);
ALTER TABLE smoothie_plans ADD COLUMN IF NOT EXISTS dataset_version_code VARCHAR(80);
ALTER TABLE report_jobs ADD COLUMN IF NOT EXISTS dataset_version_code VARCHAR(80);
ALTER TABLE report_jobs ADD COLUMN IF NOT EXISTS knowledge_refs JSONB;
