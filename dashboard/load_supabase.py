"""Load the D2 summary tables into Supabase (public.eda_* tables; read-only to the public via RLS).

Inputs: eda/d2_tables/*.parquet + facts.json (from eda/d2_figures.py), clean/cleaning_report.md, data_clean/games.parquet,
data_clean/splits/manifest.json. Uses SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY from .env (never printed).
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python dashboard/load_supabase.py
"""
import json
import math
from pathlib import Path

import pandas as pd
from supabase import create_client

ROOT = Path(__file__).resolve().parent.parent
D = Path("C:/Users/juant/data_clean")
T = ROOT / "eda" / "d2_tables"
env = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))
sb = create_client(env["SUPABASE_URL"].strip(), env["SUPABASE_SERVICE_ROLE_KEY"].strip())


def put(table, df):
    recs = json.loads(df.to_json(orient="records"))
    sb.table(table).delete().neq(df.columns[0], "__none__" if df[df.columns[0]].dtype == object else -10**9).execute()
    for k in range(0, len(recs), 500):
        sb.table(table).upsert(recs[k:k + 500]).execute()
    print(f"{table}: {len(recs)} rows", flush=True)


facts = json.load(open(T / "facts.json"))
# catalog facts for the Sources tab (counts from clean/cleaning_report.md rule F5 and the cleaned catalog)
_fr = pd.read_parquet("C:/Users/juant/data_raw/fronkon/games.parquet", columns=["appID"])
_g = pd.read_parquet(D / "games.parquet", columns=["catalog_source", "recommendable"])
facts.update({"fronkon_games": int(len(_fr)), "fronkon_added_to_catalog": int((_g.catalog_source == "fronkon").sum()),
              "catalog_apps": int(len(_g)), "catalog_recommendable": int(_g.recommendable.sum())})

# ---- per-source summary
mc = pd.read_parquet(D / "interactions_mcauley.parquet", columns=["user_key", "app_id", "played", "history_ok"])
mc = mc[mc.played & mc.history_ok]
kg = pd.read_parquet(D / "interactions_kaggle.parquet", columns=["user_key", "app_id", "played", "history_ok", "bulk_user"])
kg = kg[kg.played & kg.history_ok & ~kg.bulk_user.fillna(False)]
libs = [json.loads(l) for l in Path("C:/Users/juant/data_raw/steam_reviews/libraries.jsonl").open(encoding="utf-8")]
fr = pd.DataFrame([(r["uid"], a) for r in libs if r["public"] for a, pt, _, _ in r["games"] if pt > 0], columns=["user_key", "app_id"])
src = pd.DataFrame([
    {"source": "McAuley 2017", "players": mc.user_key.nunique(), "played_rows": len(mc), "games": mc.app_id.nunique(),
     "years": "crawled 2017", "role": "Primary training and evaluation: full libraries, like a live user"},
    {"source": "Steam 2026", "players": fr.user_key.nunique(), "played_rows": len(fr), "games": fr.app_id.nunique(),
     "years": "collected Oct 2026", "role": "Modern full libraries; its own test slice; label re-test"},
    {"source": "Kaggle (to 2023)", "players": kg.user_key.nunique(), "played_rows": len(kg), "games": kg.app_id.nunique(),
     "years": "reviews to Oct 2023", "role": "Extra training rows; label validation; reviewed games only"}])
src["median_hours"] = src.source.map(lambda s: facts.get(f"median_hours_{s}"))
src["median_library"] = src.source.map(lambda s: facts.get(f"median_library_{s}"))
del mc, kg
put("eda_sources", src)

# ---- figure tables
for name in ("playtime_hist", "library_hist", "popularity_curve", "label_curve", "release_year"):
    put(f"eda_{name}", pd.read_parquet(T / f"{name}.parquet"))

# ---- cleaning rules (parsed from the cleaning report table)
rules = []
for line in (ROOT / "clean" / "cleaning_report.md").read_text(encoding="utf-8").splitlines():
    c = [x.strip() for x in line.strip().strip("|").split("|")]
    if len(c) == 6 and c[0] not in ("id", "") and not set(c[0]) <= set(":-"):
        try:
            n = int(c[3])
        except ValueError:
            continue
        rules.append({"rule_id": c[0], "source": c[1], "rule": c[2], "rows_affected": n, "action": c[4], "why": c[5]})
put("eda_cleaning_rules", pd.DataFrame(rules).assign(seq=range(len(rules)))[["seq", "rule_id", "source", "rule", "rows_affected", "action", "why"]])

# ---- catalog quality (recommendable games)
g = pd.read_parquet(D / "games.parquet")
g = g[g.recommendable]
miss = lambda s: round(100 * float(s.mean()), 1)
cq = pd.DataFrame([
    {"field": "tags", "pct_missing": miss(g.tags.map(lambda t: t is None or len(t) == 0)), "note": "No user tags; genres used as a fallback"},
    {"field": "description", "pct_missing": miss(g.description.isna()), "note": "Content side falls back to title"},
    {"field": "header_image", "pct_missing": miss(g.header_image.isna()), "note": "Card shows a blank image"},
    {"field": "release_date", "pct_missing": miss(g.release_date.isna()), "note": ""},
    {"field": "steamspy_median_playtime_min", "pct_missing": miss(g.steamspy_median_playtime_min.isna()), "note": "Unknown, not zero (rule F1)"},
    {"field": "price_regular from Steam's regular price via IsThereAnyDeal (rule G24)", "pct_missing": miss(g.price_source == "itad_steam_regular"),
     "note": "Share of games, not missing: the most accurate regular price; older sources are the fallback"},
    {"field": "price_regular from the Oct 2026 crawl only, not cross-checked", "pct_missing": miss(g.price_source == "fronkon_2026_only"),
     "note": "Not on Steam's store or IsThereAnyDeal; live store price used at serving time"}])
put("eda_catalog_quality", cq)

# ---- split counts
m = D / "splits" / "manifest.json"
if m.exists():
    c = json.load(open(m))["counts"]
    put("eda_split_counts", pd.DataFrame([{"source": k.split("/")[0], "split": k.split("/")[1], **v} for k, v in c.items()]))

put("eda_facts", pd.DataFrame([{"key": k, "value": json.dumps(v)} for k, v in facts.items()]))
print("done")
