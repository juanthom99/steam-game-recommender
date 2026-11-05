-- Evaluation results for the team (Layers 2 and 3, diagnosis, value per dollar), loaded by dashboard/load_eval_supabase.py.
-- Long format: one row per (report, section, row, metric). Public read-only, like the eda_* tables.
create table if not exists public.eval_results (
  id bigint generated always as identity primary key,
  report text not null,        -- e.g. 'layer2', 'layer3', 'layer3_prices', 'diagnosis', 'diagnosis_value', 'layer2_run1'
  section text not null,       -- the report heading the table sits under
  row_label text not null,     -- usually the model name
  metric text not null,        -- the column header
  value double precision,      -- numeric value when the cell is a number
  value_text text,             -- the cell as written in the report
  seq integer not null,        -- row order within the section
  loaded_at timestamptz not null default now()
);
create index if not exists eval_results_report_idx on public.eval_results (report, section);
alter table public.eval_results enable row level security;
drop policy if exists "public read eval_results" on public.eval_results;
create policy "public read eval_results" on public.eval_results for select to anon, authenticated using (true);
