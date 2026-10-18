-- Landing area for workbook imports: raw rows exactly as read, plus every validation problem per cell.
-- Lets the data team see what was rejected and why before anything reaches the reference tables.
CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.raw_rows (
    batch_id UUID NOT NULL REFERENCES public.import_batches(id) ON DELETE CASCADE,
    sheet    VARCHAR(80) NOT NULL,
    row_no   INTEGER NOT NULL,
    payload  JSONB NOT NULL,
    PRIMARY KEY (batch_id, sheet, row_no)
);

CREATE TABLE IF NOT EXISTS staging.row_errors (
    id       BIGSERIAL PRIMARY KEY,
    batch_id UUID NOT NULL REFERENCES public.import_batches(id) ON DELETE CASCADE,
    sheet    VARCHAR(80) NOT NULL,
    row_no   INTEGER,
    col      VARCHAR(80),
    value    TEXT,
    severity VARCHAR(10) NOT NULL CHECK (severity IN ('critical', 'warning', 'info')),
    message  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS row_errors_batch_idx ON staging.row_errors (batch_id, severity, sheet);

ALTER TABLE staging.raw_rows ENABLE ROW LEVEL SECURITY;
ALTER TABLE staging.row_errors ENABLE ROW LEVEL SECURITY;
