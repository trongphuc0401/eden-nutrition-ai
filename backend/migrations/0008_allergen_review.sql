-- Expert review of ingredient -> allergen/condition links.
-- 'auto' links are derived from ingredient names at import and are replaced on every import;
-- 'verified' and 'rejected' are expert decisions and are never overwritten by an import.
ALTER TABLE ingredient_conditions ADD COLUMN IF NOT EXISTS review_status VARCHAR(10) NOT NULL DEFAULT 'auto';
ALTER TABLE ingredient_conditions ADD COLUMN IF NOT EXISTS reviewed_by VARCHAR(255);
ALTER TABLE ingredient_conditions ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ingredient_conditions_review_valid') THEN
        ALTER TABLE ingredient_conditions ADD CONSTRAINT ingredient_conditions_review_valid
            CHECK (review_status IN ('auto', 'verified', 'rejected'));
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS ingredient_conditions_review_idx ON ingredient_conditions (review_status);
