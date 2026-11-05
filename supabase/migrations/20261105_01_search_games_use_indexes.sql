-- search_games: same inputs and outputs, now uses the indexes (was ~13.5 s per call, full table scans).
-- Causes fixed: (1) the shared "candidates" CTE was referenced three times, so Postgres materialized the whole table
-- (embeddings included) before searching; (2) the semantic branch numbered every row by distance before limiting,
-- which rules out the HNSW index. Filters now sit in each branch, and the semantic branch takes the nearest rows with
-- ORDER BY distance LIMIT k, then numbers them. k is capped at 40, the index's default search width (hnsw.ef_search;
-- Supabase does not allow setting it per function), which is what the default match_count of 20 used before.
create or replace function public.search_games(
  query_text text,
  query_embedding extensions.halfvec,
  match_count integer default 20,
  include_dlc boolean default false,
  full_text_weight double precision default 1,
  semantic_weight double precision default 1,
  fuzzy_weight double precision default 0.5,
  rrf_k integer default 50,
  include_explicit boolean default false)
returns table(app_id integer, title text, tags text[], rating text, item_type text, score double precision)
language sql
stable
set search_path to ''
as $function$
  with full_text as (
    select g.app_id,
           row_number() over (order by ts_rank_cd(g.fts, websearch_to_tsquery('english', query_text)) desc) as rank_ix
    from public.games g
    where g.fts @@ websearch_to_tsquery('english', query_text)
      and (include_dlc or g.item_type is null or g.item_type = 'game')
      and (include_explicit or not g.explicit)
    order by rank_ix limit least(match_count, 30) * 2
  ),
  nearest as (
    select g.app_id, g.embedding operator(extensions.<=>) query_embedding as dist
    from public.games g
    where g.embedding is not null
      and (include_dlc or g.item_type is null or g.item_type = 'game')
      and (include_explicit or not g.explicit)
    order by g.embedding operator(extensions.<=>) query_embedding
    limit least(match_count * 2, 40)
  ),
  semantic as (
    select n.app_id, row_number() over (order by n.dist) as rank_ix from nearest n
  ),
  fuzzy as (
    select g.app_id,
           row_number() over (order by extensions.similarity(g.title, query_text) desc) as rank_ix
    from public.games g
    where g.title operator(extensions.%) query_text
      and (include_dlc or g.item_type is null or g.item_type = 'game')
      and (include_explicit or not g.explicit)
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
