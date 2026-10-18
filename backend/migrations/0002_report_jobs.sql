CREATE TABLE IF NOT EXISTS report_jobs (
    report_id VARCHAR(64) PRIMARY KEY,
    idempotency_key VARCHAR(255),
    status VARCHAR(32) NOT NULL,
    payload JSONB NOT NULL,
    lease_owner VARCHAR(255),
    lease_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS report_jobs_idempotency_key
ON report_jobs (idempotency_key)
WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS report_jobs_status_updated_at
ON report_jobs (status, updated_at);
