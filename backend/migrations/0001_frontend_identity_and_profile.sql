-- Fresh Citrus frontend identity/profile extension.
-- Apply once with PostgreSQL after taking a database backup.
-- The statements are idempotent so this migration is safe to re-run.

ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS users_google_sub_key ON users (google_sub) WHERE google_sub IS NOT NULL;

ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS hometown_code VARCHAR(32);
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS hometown_name VARCHAR(255);
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS preferences TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS completion_status VARCHAR(20) NOT NULL DEFAULT 'draft';
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;
