-- Step 1 of the games reload (run BEFORE index/load_games.py). Deletes no rows.
-- Half-precision embeddings keep ~111k games under the 500 MB plan limit.
-- The HNSW index is dropped so the bulk upsert doesn't time out; step 2 rebuilds it.
drop index if exists public.games_embedding_hnsw;
alter table public.games alter column embedding type extensions.halfvec(384) using embedding::extensions.halfvec(384);
alter table public.games add column if not exists price_source text;
comment on column public.games.embed_text is 'Unused since the full-catalog reload; left empty for new rows';
comment on column public.games.price_regular is 'Regular USD price: Steam regular price from IsThereAnyDeal when known (rule G24), else older sources';

drop function if exists public.search_games(text, extensions.vector, integer, boolean, double precision, double precision, double precision, integer);
create or replace function public.search_games(query_text text, query_embedding extensions.halfvec, match_count integer default 20,
  include_dlc boolean default false, full_text_weight double precision default 1, semantic_weight double precision default 1,
  fuzzy_weight double precision default 0.5, rrf_k integer default 50)
returns table(app_id integer, title text, tags text[], rating text, item_type text, score double precision)
language sql stable set search_path to ''
as $function$
  with candidates as (
    select g.* from public.games g
    where include_dlc or g.item_type is null or g.item_type = 'game'
  ),
  full_text as (
    select c.app_id,
           row_number() over (order by ts_rank_cd(c.fts, websearch_to_tsquery('english', query_text)) desc) as rank_ix
    from candidates c
    where c.fts @@ websearch_to_tsquery('english', query_text)
    order by rank_ix limit least(match_count, 30) * 2
  ),
  semantic as (
    select c.app_id,
           row_number() over (order by c.embedding operator(extensions.<=>) query_embedding) as rank_ix
    from candidates c
    where c.embedding is not null
    order by rank_ix limit least(match_count, 30) * 2
  ),
  fuzzy as (
    select c.app_id,
           row_number() over (order by extensions.similarity(c.title, query_text) desc) as rank_ix
    from candidates c
    where c.title operator(extensions.%) query_text
    order by rank_ix limit least(match_count, 30)
  ),
  fused as (
    select coalesce(ft.app_id, s.app_id, fz.app_id) as app_id,
           coalesce(1.0 / (rrf_k + ft.rank_ix), 0) * full_text_weight +
           coalesce(1.0 / (rrf_k + s.rank_ix), 0) * semantic_weight +
           coalesce(1.0 / (rrf_k + fz.rank_ix), 0) * fuzzy_weight as score
    from full_text ft
    full outer join semantic s on ft.app_id = s.app_id
    full outer join fuzzy fz on coalesce(ft.app_id, s.app_id) = fz.app_id
  )
  select g.app_id, g.title, g.tags, g.rating, g.item_type, f.score::float
  from fused f join public.games g on g.app_id = f.app_id
  order by f.score desc
  limit match_count;
$function$;
