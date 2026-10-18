-- Close every public table to the Supabase REST API (anon/authenticated).
-- No policies are created, so those roles see nothing; the backend connects as `postgres`
-- (BYPASSRLS) and is unaffected. New tables must enable RLS themselves.
DO $$
DECLARE t record;
BEGIN
    FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
        EXECUTE 'ALTER TABLE public.' || quote_ident(t.tablename) || ' ENABLE ROW LEVEL SECURITY';
    END LOOP;
END $$;
