-- Add report_id to chat_threads so reports generated within a chat session are linked.
ALTER TABLE chat_threads ADD COLUMN IF NOT EXISTS report_id VARCHAR(64);
