-- public.diamonds (not part of the recommender; shares this database) let anyone with the public key insert rows.
-- The database is near the free-plan 500 MB limit, where it turns read-only, so open inserts put every table at risk.
-- Reads stay public; the table and its data are unchanged.
drop policy if exists "Allow public insert access" on public.diamonds;
