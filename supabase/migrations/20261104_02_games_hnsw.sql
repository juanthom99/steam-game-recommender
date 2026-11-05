-- Step 2 of the games reload (run AFTER index/load_games.py): rebuild the vector index once, on the full table.
-- Free-tier memory: 128MB with parallel workers failed ("could not resize shared memory segment"); this setting worked
-- (about 10 minutes for ~120k rows). The SQL editor may time out first; the build keeps running server-side.
set local statement_timeout = '30min';
set local max_parallel_maintenance_workers = 0;
set local maintenance_work_mem = '48MB';
create index if not exists games_embedding_hnsw on public.games using hnsw (embedding extensions.halfvec_cosine_ops);
analyze public.games;
