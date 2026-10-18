-- Conversation memory for the nutrition chat agent (/v1/chat).
CREATE TABLE IF NOT EXISTS chat_threads (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id   VARCHAR(255) NOT NULL,
    title      VARCHAR(160) NOT NULL DEFAULT 'Cuộc trò chuyện mới',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS chat_threads_owner_idx ON chat_threads (owner_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS chat_messages (
    id         BIGSERIAL PRIMARY KEY,
    thread_id  UUID NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
    role       VARCHAR(10) NOT NULL CHECK (role IN ('user', 'assistant')),
    content    TEXT NOT NULL,
    intent     VARCHAR(32),
    -- ingredient ids discussed, cards, suggested actions, tool trace and dataset version (for follow-ups and audit)
    metadata   JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS chat_messages_thread_idx ON chat_messages (thread_id, id);

-- Closed to the public API like every other table; the backend role bypasses RLS.
ALTER TABLE chat_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
