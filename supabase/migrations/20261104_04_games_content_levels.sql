-- Rule G25 content levels on public.games; search_games hides explicit games unless include_explicit = true.
-- Applied 2026-11-04. Values are filled by index/update_content_levels.py (updates only, no deletes).
alter table public.games add column if not exists explicit boolean not null default false;
alter table public.games add column if not exists content_level text not null default 'none'
  check (content_level in ('explicit', 'sexual_themes', 'mature', 'none'));
alter table public.games add column if not exists explicit_reason text not null default '';
create index if not exists games_explicit_idx on public.games (explicit);
-- search_games: same body as 20261104_01, plus "and (include_explicit or not g.explicit)" in candidates and a new
-- last parameter include_explicit boolean default false.
