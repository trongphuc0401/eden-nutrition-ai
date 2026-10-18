-- Fresh Citrus research-workbook schema.
-- Structure only: this migration never imports, converts, or deletes workbook data.
-- PostgreSQL comments are intentionally Vietnamese so operators can understand fields in pgAdmin.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS data_sources (
    source_code VARCHAR(80) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    source_type VARCHAR(30) NOT NULL,
    author_or_org VARCHAR(255),
    published_year SMALLINT,
    url_or_file TEXT,
    locator VARCHAR(255),
    reliability_level VARCHAR(20) NOT NULL DEFAULT 'needs_review',
    used_for TEXT[] NOT NULL DEFAULT '{}',
    notes TEXT,
    CONSTRAINT data_sources_code_format CHECK (source_code ~ '^[A-Z0-9_]+$'),
    CONSTRAINT data_sources_type_valid CHECK (source_type IN ('book', 'paper', 'guideline', 'spreadsheet', 'website')),
    CONSTRAINT data_sources_reliability_valid CHECK (reliability_level IN ('high', 'medium', 'low', 'needs_review'))
);

CREATE TABLE IF NOT EXISTS dataset_versions (
    version_code VARCHAR(80) PRIMARY KEY,
    released_on DATE,
    author_name VARCHAR(255),
    change_summary TEXT NOT NULL,
    change_reason TEXT,
    meeting_reference VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS import_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_version_code VARCHAR(80) REFERENCES dataset_versions(version_code),
    sheet_name VARCHAR(255) NOT NULL,
    file_checksum VARCHAR(128) NOT NULL,
    rows_ok INTEGER NOT NULL DEFAULT 0 CHECK (rows_ok >= 0),
    rows_rejected INTEGER NOT NULL DEFAULT 0 CHECK (rows_rejected >= 0),
    errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS nutrients (
    nutrient_code VARCHAR(80) PRIMARY KEY,
    name_vi VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    unit VARCHAR(20) NOT NULL,
    nutrient_group VARCHAR(30) NOT NULL,
    parent_nutrient_code VARCHAR(80) REFERENCES nutrients(nutrient_code),
    display_order SMALLINT NOT NULL DEFAULT 0,
    sheet_header VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT nutrients_group_valid CHECK (nutrient_group IN ('macro', 'sugar', 'mineral', 'vitamin', 'carotenoid', 'isoflavone', 'fatty_acid', 'amino_acid', 'sterol', 'other'))
);

CREATE TABLE IF NOT EXISTS ingredients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ingredient_code VARCHAR(80) NOT NULL UNIQUE,
    name_vi VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    name_normalized VARCHAR(255) NOT NULL,
    category VARCHAR(30) NOT NULL,
    processing_state VARCHAR(30) NOT NULL DEFAULT 'fresh',
    origin_country VARCHAR(100),
    growing_regions TEXT[] NOT NULL DEFAULT '{}',
    allowed_for_smoothie BOOLEAN NOT NULL DEFAULT TRUE,
    data_status VARCHAR(20) NOT NULL DEFAULT 'needs_review',
    primary_source_code VARCHAR(80) REFERENCES data_sources(source_code),
    entry_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ingredients_code_format CHECK (ingredient_code ~ '^[A-Z0-9_]+$'),
    CONSTRAINT ingredients_category_valid CHECK (category IN ('fruit', 'vegetable', 'protein', 'liquid', 'seed', 'sweetener', 'other')),
    CONSTRAINT ingredients_processing_valid CHECK (processing_state IN ('fresh', 'dried', 'frozen', 'powder', 'juice', 'other')),
    CONSTRAINT ingredients_status_valid CHECK (data_status IN ('verified', 'needs_review', 'missing_source', 'example'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ingredients_name_normalized_key ON ingredients(name_normalized);

CREATE TABLE IF NOT EXISTS ingredient_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ingredient_id UUID NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    alias VARCHAR(255) NOT NULL,
    alias_normalized VARCHAR(255) NOT NULL,
    language_code VARCHAR(10) NOT NULL DEFAULT 'vi',
    UNIQUE (ingredient_id, alias_normalized, language_code)
);

CREATE TABLE IF NOT EXISTS ingredient_nutrients (
    ingredient_id UUID NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    nutrient_code VARCHAR(80) NOT NULL REFERENCES nutrients(nutrient_code),
    value_per_100g NUMERIC(12, 4),
    value_status VARCHAR(20) NOT NULL DEFAULT 'not_available',
    source_code VARCHAR(80) REFERENCES data_sources(source_code),
    import_batch_id UUID REFERENCES import_batches(id),
    PRIMARY KEY (ingredient_id, nutrient_code),
    CONSTRAINT ingredient_nutrients_value_status_valid CHECK (value_status IN ('measured', 'not_available', 'trace')),
    CONSTRAINT ingredient_nutrients_value_matches_status CHECK (
        (value_status = 'measured' AND value_per_100g IS NOT NULL) OR
        (value_status IN ('not_available', 'trace') AND value_per_100g IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS ingredient_seasons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ingredient_id UUID NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    region_label VARCHAR(255) NOT NULL,
    months SMALLINT[] NOT NULL DEFAULT '{}',
    year_round BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT ingredient_seasons_months_valid CHECK (months <@ ARRAY[1,2,3,4,5,6,7,8,9,10,11,12]::SMALLINT[]),
    CONSTRAINT ingredient_seasons_months_or_year_round CHECK (year_round OR cardinality(months) > 0),
    UNIQUE (ingredient_id, region_label)
);

CREATE TABLE IF NOT EXISTS health_conditions (
    condition_code VARCHAR(80) PRIMARY KEY,
    name_vi VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    condition_type VARCHAR(20) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT health_conditions_type_valid CHECK (condition_type IN ('allergy', 'disease', 'medication', 'other'))
);

CREATE TABLE IF NOT EXISTS ingredient_conditions (
    ingredient_id UUID NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    condition_code VARCHAR(80) NOT NULL REFERENCES health_conditions(condition_code),
    relation VARCHAR(30) NOT NULL,
    notes TEXT,
    PRIMARY KEY (ingredient_id, condition_code, relation),
    CONSTRAINT ingredient_conditions_relation_valid CHECK (relation IN ('contains_allergen', 'should_limit', 'should_avoid'))
);

CREATE TABLE IF NOT EXISTS profile_classification_rules (
    rule_code VARCHAR(80) PRIMARY KEY,
    rule_name VARCHAR(255) NOT NULL,
    target_group VARCHAR(100),
    input_field VARCHAR(50) NOT NULL,
    operator VARCHAR(20) NOT NULL,
    min_value NUMERIC(12, 4),
    max_value NUMERIC(12, 4),
    unit VARCHAR(20),
    classification_result VARCHAR(100) NOT NULL,
    priority SMALLINT NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT profile_rules_input_valid CHECK (input_field IN ('age', 'bmi', 'activity_level', 'sex')),
    CONSTRAINT profile_rules_operator_valid CHECK (operator IN ('between', 'gte', 'gt', 'lte', 'lt', 'equals')),
    CONSTRAINT profile_rules_range_valid CHECK (min_value IS NULL OR max_value IS NULL OR min_value <= max_value)
);

CREATE TABLE IF NOT EXISTS smoothie_recipes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_code VARCHAR(80) NOT NULL UNIQUE,
    name_vi VARCHAR(255) NOT NULL,
    target_goal VARCHAR(100),
    total_weight_g NUMERIC(10, 2),
    serving_ml NUMERIC(10, 2),
    preparation_steps_vi TEXT,
    why_suitable_vi TEXT,
    safety_warning_vi TEXT,
    data_quality_status VARCHAR(20) NOT NULL DEFAULT 'needs_review',
    entry_notes TEXT,
    CONSTRAINT smoothie_recipes_status_valid CHECK (data_quality_status IN ('verified', 'needs_review', 'example'))
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    recipe_id UUID NOT NULL REFERENCES smoothie_recipes(id) ON DELETE CASCADE,
    ingredient_id UUID NOT NULL REFERENCES ingredients(id),
    amount NUMERIC(10, 2) NOT NULL CHECK (amount > 0),
    unit VARCHAR(10) NOT NULL,
    amount_g NUMERIC(10, 2),
    sort_order SMALLINT NOT NULL DEFAULT 1,
    PRIMARY KEY (recipe_id, ingredient_id),
    CONSTRAINT recipe_ingredients_unit_valid CHECK (unit IN ('g', 'ml'))
);

CREATE TABLE IF NOT EXISTS eval_auto_criteria (
    criterion_code VARCHAR(80) PRIMARY KEY,
    name_vi VARCHAR(255) NOT NULL,
    metric VARCHAR(100) NOT NULL,
    check_type VARCHAR(50) NOT NULL,
    pass_condition TEXT,
    fail_condition TEXT,
    severity VARCHAR(20) NOT NULL DEFAULT 'medium',
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    related_rule_code VARCHAR(100),
    implementation_notes TEXT,
    CONSTRAINT eval_auto_criteria_severity_valid CHECK (severity IN ('low', 'medium', 'high', 'critical'))
);

CREATE TABLE IF NOT EXISTS eval_rubric_criteria (
    criterion_code VARCHAR(80) PRIMARY KEY,
    name_vi VARCHAR(255) NOT NULL,
    score_min NUMERIC(6, 2) NOT NULL DEFAULT 0,
    score_max NUMERIC(6, 2) NOT NULL DEFAULT 5,
    pass_threshold NUMERIC(6, 2),
    auto_fail_if_below NUMERIC(6, 2),
    low_description_vi TEXT,
    high_description_vi TEXT,
    CONSTRAINT eval_rubric_score_range_valid CHECK (score_min <= score_max),
    CONSTRAINT eval_rubric_pass_threshold_valid CHECK (pass_threshold IS NULL OR pass_threshold BETWEEN score_min AND score_max)
);

CREATE TABLE IF NOT EXISTS eval_profile_templates (
    template_code VARCHAR(80) PRIMARY KEY,
    age_min SMALLINT,
    age_max SMALLINT,
    sex VARCHAR(10),
    height_cm_min NUMERIC(6, 2),
    height_cm_max NUMERIC(6, 2),
    weight_kg_min NUMERIC(6, 2),
    weight_kg_max NUMERIC(6, 2),
    bmi_group VARCHAR(50),
    activity_level VARCHAR(50),
    allergy_scenario TEXT,
    disliked_scenario TEXT,
    preferred_scenario TEXT,
    medical_note_scenario TEXT,
    sample_count INTEGER NOT NULL DEFAULT 1 CHECK (sample_count > 0),
    purpose VARCHAR(50) NOT NULL,
    CONSTRAINT eval_templates_age_range_valid CHECK (age_min IS NULL OR age_max IS NULL OR age_min <= age_max)
);

CREATE TABLE IF NOT EXISTS source_citations (
    entity_table VARCHAR(80) NOT NULL,
    entity_code VARCHAR(100) NOT NULL,
    source_code VARCHAR(80) NOT NULL REFERENCES data_sources(source_code),
    locator VARCHAR(255),
    notes TEXT,
    PRIMARY KEY (entity_table, entity_code, source_code),
    CONSTRAINT source_citations_table_valid CHECK (entity_table IN ('ingredients', 'ingredient_nutrients', 'nutrition_thresholds', 'clinical_safety_rules', 'smoothie_recipes', 'eval_auto_criteria', 'eval_rubric_criteria', 'profile_classification_rules'))
);

-- Add canonical fields without touching existing rows or legacy fields.
ALTER TABLE nutrition_thresholds ADD COLUMN IF NOT EXISTS nutrient_code VARCHAR(80) REFERENCES nutrients(nutrient_code);
ALTER TABLE nutrition_thresholds ADD COLUMN IF NOT EXISTS target_group VARCHAR(100);
ALTER TABLE nutrition_thresholds ADD COLUMN IF NOT EXISTS sex VARCHAR(10);
ALTER TABLE nutrition_thresholds ADD COLUMN IF NOT EXISTS age_min SMALLINT;
ALTER TABLE nutrition_thresholds ADD COLUMN IF NOT EXISTS age_max SMALLINT;
ALTER TABLE nutrition_thresholds ADD COLUMN IF NOT EXISTS bmi_group VARCHAR(50);
ALTER TABLE nutrition_thresholds ADD COLUMN IF NOT EXISTS comparator VARCHAR(20);
ALTER TABLE nutrition_thresholds ADD COLUMN IF NOT EXISTS pass_rule_text TEXT;
ALTER TABLE nutrition_thresholds ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE nutrition_thresholds ADD COLUMN IF NOT EXISTS import_batch_id UUID REFERENCES import_batches(id);
DO $$
BEGIN
    ALTER TABLE nutrition_thresholds ADD CONSTRAINT nutrition_thresholds_range_valid CHECK (min_value IS NULL OR max_value IS NULL OR min_value <= max_value) NOT VALID;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$
BEGIN
    ALTER TABLE nutrition_thresholds ADD CONSTRAINT nutrition_thresholds_comparator_valid CHECK (comparator IS NULL OR comparator IN ('between', 'gte', 'gt', 'lte', 'lt'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE clinical_safety_rules ADD COLUMN IF NOT EXISTS condition_code VARCHAR(80) REFERENCES health_conditions(condition_code);
ALTER TABLE clinical_safety_rules ADD COLUMN IF NOT EXISTS target_type VARCHAR(30);
ALTER TABLE clinical_safety_rules ADD COLUMN IF NOT EXISTS ingredient_id UUID REFERENCES ingredients(id);
ALTER TABLE clinical_safety_rules ADD COLUMN IF NOT EXISTS nutrient_code VARCHAR(80) REFERENCES nutrients(nutrient_code);
ALTER TABLE clinical_safety_rules ADD COLUMN IF NOT EXISTS target_text TEXT;
ALTER TABLE clinical_safety_rules ADD COLUMN IF NOT EXISTS avoid_or_limit VARCHAR(20);
ALTER TABLE clinical_safety_rules ADD COLUMN IF NOT EXISTS warning_message_vi TEXT;
ALTER TABLE clinical_safety_rules ADD COLUMN IF NOT EXISTS recommended_action VARCHAR(20);
ALTER TABLE clinical_safety_rules ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE clinical_safety_rules ADD COLUMN IF NOT EXISTS entry_notes TEXT;
ALTER TABLE clinical_safety_rules ADD COLUMN IF NOT EXISTS import_batch_id UUID REFERENCES import_batches(id);
DO $$
BEGIN
    ALTER TABLE clinical_safety_rules ADD CONSTRAINT clinical_safety_rules_target_valid CHECK (target_type IS NULL OR target_type IN ('ingredient', 'ingredient_group', 'nutrient'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$
BEGIN
    ALTER TABLE clinical_safety_rules ADD CONSTRAINT clinical_safety_rules_recommended_action_valid CHECK (recommended_action IS NULL OR recommended_action IN ('block_recipe', 'warn_user', 'suggest_consult'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS activity_level VARCHAR(50);
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS allergy_condition_codes TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE nutrition_knowledge ADD COLUMN IF NOT EXISTS ingredient_id UUID REFERENCES ingredients(id);
ALTER TABLE nutrition_knowledge ADD COLUMN IF NOT EXISTS dataset_version_code VARCHAR(80) REFERENCES dataset_versions(version_code);
ALTER TABLE smoothie_plans ADD COLUMN IF NOT EXISTS dataset_version_code VARCHAR(80) REFERENCES dataset_versions(version_code);
ALTER TABLE report_jobs ADD COLUMN IF NOT EXISTS dataset_version_code VARCHAR(80) REFERENCES dataset_versions(version_code);

-- SQLAlchemy creates the legacy tables before this migration on a fresh install.
-- Add the reference constraints separately so they exist whether a column was new or pre-created.
DO $$
BEGIN
    ALTER TABLE nutrition_thresholds ADD CONSTRAINT nutrition_thresholds_nutrient_code_fkey
        FOREIGN KEY (nutrient_code) REFERENCES nutrients(nutrient_code);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$
BEGIN
    ALTER TABLE nutrition_thresholds ADD CONSTRAINT nutrition_thresholds_import_batch_id_fkey
        FOREIGN KEY (import_batch_id) REFERENCES import_batches(id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$
BEGIN
    ALTER TABLE clinical_safety_rules ADD CONSTRAINT clinical_safety_rules_condition_code_fkey
        FOREIGN KEY (condition_code) REFERENCES health_conditions(condition_code);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$
BEGIN
    ALTER TABLE clinical_safety_rules ADD CONSTRAINT clinical_safety_rules_ingredient_id_fkey
        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$
BEGIN
    ALTER TABLE clinical_safety_rules ADD CONSTRAINT clinical_safety_rules_nutrient_code_fkey
        FOREIGN KEY (nutrient_code) REFERENCES nutrients(nutrient_code);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$
BEGIN
    ALTER TABLE clinical_safety_rules ADD CONSTRAINT clinical_safety_rules_import_batch_id_fkey
        FOREIGN KEY (import_batch_id) REFERENCES import_batches(id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$
BEGIN
    ALTER TABLE nutrition_knowledge ADD CONSTRAINT nutrition_knowledge_ingredient_id_fkey
        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$
BEGIN
    ALTER TABLE nutrition_knowledge ADD CONSTRAINT nutrition_knowledge_dataset_version_code_fkey
        FOREIGN KEY (dataset_version_code) REFERENCES dataset_versions(version_code);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$
BEGIN
    ALTER TABLE smoothie_plans ADD CONSTRAINT smoothie_plans_dataset_version_code_fkey
        FOREIGN KEY (dataset_version_code) REFERENCES dataset_versions(version_code);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$
BEGIN
    ALTER TABLE report_jobs ADD CONSTRAINT report_jobs_dataset_version_code_fkey
        FOREIGN KEY (dataset_version_code) REFERENCES dataset_versions(version_code);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS ingredient_nutrients_nutrient_code_idx ON ingredient_nutrients(nutrient_code);
CREATE INDEX IF NOT EXISTS ingredients_primary_source_code_idx ON ingredients(primary_source_code);
CREATE INDEX IF NOT EXISTS clinical_safety_rules_condition_code_idx ON clinical_safety_rules(condition_code);
CREATE INDEX IF NOT EXISTS nutrition_thresholds_nutrient_code_idx ON nutrition_thresholds(nutrient_code);

COMMENT ON TABLE ingredients IS 'Danh mục nguyên liệu chuẩn; mỗi nguyên liệu chỉ có một mã ING_...';
COMMENT ON COLUMN ingredients.ingredient_code IS 'Mã nguyên liệu duy nhất, ví dụ ING_FRUIT_0001.';
COMMENT ON COLUMN ingredients.name_vi IS 'Tên hiển thị tiếng Việt để nhập và tra cứu.';
COMMENT ON COLUMN ingredients.name_normalized IS 'Tên không dấu, chữ thường; dùng để đối chiếu và chống trùng.';
COMMENT ON COLUMN ingredients.data_status IS 'verified: đã xác minh; needs_review: chờ rà soát; missing_source: thiếu nguồn; example: dữ liệu minh hoạ.';
COMMENT ON TABLE nutrients IS 'Danh mục chỉ số dinh dưỡng chuẩn dùng chung cho nguyên liệu, ngưỡng và đánh giá.';
COMMENT ON COLUMN nutrients.sheet_header IS 'Tên cột gốc trong workbook, chỉ dùng để đối chiếu khi nhập sau này.';
COMMENT ON TABLE ingredient_nutrients IS 'Một giá trị dinh dưỡng trên 100g cho một nguyên liệu; không dùng số 0 để biểu thị thiếu dữ liệu.';
COMMENT ON COLUMN ingredient_nutrients.value_status IS 'measured: có số; not_available: không có số liệu; trace: chỉ có vết, không có số định lượng.';
COMMENT ON TABLE data_sources IS 'Danh mục nguồn tham chiếu chuẩn; nhập nguồn trước các bảng dữ liệu khác.';
COMMENT ON TABLE source_citations IS 'Liên kết nguồn đến bản ghi. entity_table/entity_code được kiểm tra bởi quy trình nhập sau này.';
COMMENT ON TABLE health_conditions IS 'Danh mục dị ứng, bệnh lý và thuốc chuẩn hoá.';
COMMENT ON TABLE ingredient_conditions IS 'Quan hệ nguyên liệu với dị ứng/bệnh lý, phục vụ chặn hoặc cảnh báo không cần suy luận AI.';
COMMENT ON TABLE nutrition_thresholds IS 'Ngưỡng dinh dưỡng. Cột metric và pass_rule cũ được giữ để tương thích; dùng nutrient_code, comparator, pass_rule_text cho dữ liệu mới.';
COMMENT ON TABLE clinical_safety_rules IS 'Quy tắc an toàn lâm sàng. Cột condition_key, ingredient_or_nutrient và action cũ được giữ để tương thích; dùng các cột *_code, target_* và recommended_action cho dữ liệu mới.';
COMMENT ON TABLE import_batches IS 'Nhật ký lô nhập trong tương lai; bảng này rỗng ở giai đoạn tạo schema.';
