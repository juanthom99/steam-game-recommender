"""Profile every data source with one consistent checklist (data:explore-data skill).

Run with the ML venv:
  C:/Users/juant/.venvs/steamrec-ml/Scripts/python eda/profile_all.py [--skip-big]
Writes eda/profiles/<source>.md and merges the scorecard into eda/profiles/README.md.
McAuley is profiled separately by eda/profile_mcauley.py.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profiling import HERE, OUT, KAGGLE, SUMMARY, PROFILES, profile_df, add_section, write, write_readme  # noqa: E402

# ---------------------------------------------------------------- sources
skip_big = "--skip-big" in sys.argv
games = pd.read_csv(KAGGLE / "games.csv", parse_dates=["date_release"])
profile_df("Kaggle games.csv", games, "game (Steam app)", key="app_id",
           notes=["price_original = 0 on paid games not on sale (see issues)"])
add_section("Kaggle games.csv", "Relationships and Patterns",
            f"- `app_id` joins every other source (Steam appid).\n"
            f"- price_final > price_original on {(games.price_final > games.price_original).sum():,} rows, all with price_original = 0: a missing-value code, not a real price.\n"
            f"- Derived: discount = 1 − price_final/price_original; `rating` is a banded `positive_ratio` × `user_reviews`.\n"
            f"- Spearman(price_final, price_original) = {games[['price_final', 'price_original']].corr('spearman').iloc[0, 1]:.2f} (near-redundant).")
write("Kaggle games.csv", "kaggle_games.md")

meta = pd.read_json(KAGGLE / "games_metadata.json", lines=True)
profile_df("Kaggle games_metadata.json", meta, "game", key="app_id",
           notes=["Text source for the search index and the model's content side"])
tags = meta.tags.explode().dropna()
add_section("Kaggle games_metadata.json", "Relationships and Patterns",
            f"- 1:1 with games.csv on `app_id` (missing either way: {(~meta.app_id.isin(games.app_id)).sum()} / {(~games.app_id.isin(meta.app_id)).sum()}).\n"
            f"- {tags.nunique()} distinct tags; top 20 tags cover {tags.value_counts().head(20).sum() / len(tags):.0%} of tag uses (tag vocabulary is concentrated).")
write("Kaggle games_metadata.json", "kaggle_games_metadata.md")

if not skip_big:
    users = pd.read_csv(KAGGLE / "users.csv")
    profile_df("Kaggle users.csv", users, "user", key="user_id",
               notes=["`products` = games owned; `reviews` = reviews written (both counts)"])
    add_section("Kaggle users.csv", "Relationships and Patterns",
                f"- Reviews per owned game: median {(users.reviews / users.products.replace(0, np.nan)).median():.3f}: "
                f"users review a small share of what they own, so Kaggle sees only reviewed games.\n"
                f"- Users owning 0 products but with reviews: {((users.products == 0) & (users.reviews > 0)).sum():,} (inconsistent).")
    write("Kaggle users.csv", "kaggle_users.md")
    del users

    rec = pd.read_csv(KAGGLE / "recommendations.csv", parse_dates=["date"],
                      dtype={"app_id": "int32", "helpful": "int32", "funny": "int32", "hours": "float32",
                             "user_id": "int32", "review_id": "int32", "is_recommended": "bool"})
    profile_df("Kaggle recommendations.csv", rec, "user review of a game", key="review_id",
               notes=[f"(user_id, app_id) duplicates: {rec.duplicated(['user_id', 'app_id']).sum():,}",
                      f"hours at the 1000 cap: {(rec.hours >= 999.9).sum():,}"])
    by_month = rec.set_index("date").resample("MS").size()
    add_section("Kaggle recommendations.csv", "Relationships and Patterns",
                f"- FKs: `app_id` → games (orphans {(~rec.app_id.isin(games.app_id)).sum():,}), `user_id` → users.\n"
                f"- Recommended share by year: " + ", ".join(f"{y}: {v:.0%}" for y, v in rec.groupby(rec.date.dt.year).is_recommended.mean().items()) + "\n"
                f"- Spearman(hours, is_recommended) = {rec[['hours', 'is_recommended']].astype(float).sample(2_000_000, random_state=0).corr('spearman').iloc[0, 1]:.3f}; "
                f"Spearman(helpful, funny) = {rec[['helpful', 'funny']].sample(2_000_000, random_state=0).corr('spearman').iloc[0, 1]:.3f}.\n"
                f"- Months with the most reviews: " + ", ".join(f"{d:%Y-%m} ({n:,})" for d, n in by_month.nlargest(3).items()) +
                f"; quietest recent month: {by_month['2020':].idxmin():%Y-%m}.")
    write("Kaggle recommendations.csv", "kaggle_recommendations.md")
    rec_apps = set(rec.app_id.unique())
    del rec
else:
    rec_apps = set()

# Steam store sample (300 appdetails responses)
raw = [json.loads(l) for l in (HERE / "steam_sample.jsonl").read_text(encoding="utf-8").splitlines()]
ss = pd.DataFrame([{
    "app_id": r["app_id"], "success": r["success"], "type": (r["data"] or {}).get("type"), "name": (r["data"] or {}).get("name"),
    "is_free": (r["data"] or {}).get("is_free"), "currency": ((r["data"] or {}).get("price_overview") or {}).get("currency"),
    "price_initial": (((r["data"] or {}).get("price_overview") or {}).get("initial") or np.nan) / 100,
    "price_final": (((r["data"] or {}).get("price_overview") or {}).get("final") or np.nan) / 100,
    "discount_percent": ((r["data"] or {}).get("price_overview") or {}).get("discount_percent"),
    "short_description": (r["data"] or {}).get("short_description"), "header_image": (r["data"] or {}).get("header_image"),
    "genres": [g["description"] for g in (r["data"] or {}).get("genres") or []],
    "metacritic_score": ((r["data"] or {}).get("metacritic") or {}).get("score"),
    "release_date": ((r["data"] or {}).get("release_date") or {}).get("date"),
    "required_age": (r["data"] or {}).get("required_age"),
} for r in raw])
ss["release_date"] = pd.to_datetime(ss.release_date, errors="coerce", format="mixed")
profile_df("Steam store appdetails (300-game sample)", ss, "game (live store page)", key="app_id",
           notes=["No key needed; ~200 requests / 5 min; prices in the requested country's currency"])
add_section("Steam store appdetails (300-game sample)", "Relationships and Patterns",
            f"- `price_overview` is absent for free games and unreleased items: a structural null, not missing data.\n"
            f"- `metacritic_score` exists mainly for popular games: popularity-biased, don't use as a feature.\n"
            f"- Fills Kaggle's empty descriptions via `short_description`.")
write("Steam store appdetails (300-game sample)", "steam_store_sample.md")

cat = pd.read_csv(HERE / "steam_catalog.csv", parse_dates=["last_modified"])
profile_df("Steam IStoreService app catalog", cat, "Steam app (any type)", key="appid",
           notes=["Requires STEAM_API_KEY; gives the type for every app in one pass"])
g_ids = set(games.app_id)
cat_games = cat[cat.type == "game"]
add_section("Steam IStoreService app catalog", "Relationships and Patterns",
            "| type | apps | in Kaggle games.csv |\n|---|---:|---:|\n" +
            "\n".join(f"| {t} | {n:,} | {cat[(cat.type == t) & cat.appid.isin(g_ids)].shape[0]:,} |" for t, n in cat.type.value_counts().items()) +
            f"\n\n- Kaggle app_ids not in today's catalog (delisted or removed): {len(g_ids - set(cat.appid)):,}\n"
            f"- Steam **games** not in Kaggle: {(~cat_games.appid.isin(g_ids)).sum():,}. They include releases after Oct 2023 "
            f"(handled by the weekly catalog refresh) and older games Kaggle left out, since it kept only games with ≥ 10 user reviews.\n"
            f"- Kaggle items Steam types as DLC: {cat[(cat.type == 'dlc') & cat.appid.isin(g_ids)].shape[0]:,}. This gives `item_type` for nearly all games in one pass, replacing the ~7 h IsThereAnyDeal backfill.")
write("Steam IStoreService app catalog", "steam_catalog.md")

lib = pd.read_csv(HERE / "steam_my_library.csv", parse_dates=["rtime_last_played"])
profile_df("Steam GetOwnedGames (your library)", lib, "owned game for one user", key="appid",
           notes=["This is exactly what a live user brings: owned games incl. never-played ones, minutes not hours"])
add_section("Steam GetOwnedGames (your library)", "Relationships and Patterns",
            f"- Never played (playtime 0 → *unknown* in Layer 1): {(lib.playtime_forever == 0).sum()} of {len(lib)}.\n"
            f"- Played ≥ 120 min: {(lib.playtime_forever >= 120).sum()}.\n"
            f"- In Kaggle catalog: {lib.appid.isin(g_ids).sum()} / {len(lib)}; in Kaggle *review* data (collaborative model can use): "
            f"{lib.appid.isin(rec_apps).sum() if rec_apps else 'n/a'} / {len(lib)}.\n"
            f"- Unit check: Steam gives minutes; Kaggle gives hours. Convert before applying the 120-minute floor.")
write("Steam GetOwnedGames (your library)", "steam_my_library.md")

it = json.loads((HERE / "itad_sample.json").read_text(encoding="utf-8"))
rev = {v: int(k) for k, v in it["id_map"].items() if v}
ov = []
for chunk in it["overview"]:
    for g in chunk.get("prices", []):
        cur, low = g.get("current") or {}, g.get("lowest") or {}
        ov.append({"app_id": rev.get(g["id"]), "itad_id": g["id"],
                   "best_price_now": (cur.get("price") or {}).get("amount"), "regular_price": (cur.get("regular") or {}).get("amount"),
                   "best_shop": (cur.get("shop") or {}).get("name"), "cut_now": cur.get("cut"),
                   "all_time_low": (low.get("price") or {}).get("amount"), "low_shop": (low.get("shop") or {}).get("name"),
                   "low_date": pd.to_datetime(low.get("timestamp"), utc=True, errors="coerce").tz_localize(None) if low.get("timestamp") else pd.NaT,
                   "n_deals": next((len(p.get("deals", [])) for p in it["prices"] if p["id"] == g["id"]), 0)})
ov = pd.DataFrame(ov)
profile_df("IsThereAnyDeal overview + prices (300-game sample)", ov, "game (ITAD id) with current and historical-low price", key="app_id",
           notes=[f"Steam ids sent {len(it['id_map'])}, matched {len(rev)}; no overview for {len(rev) - len(ov)} matched ids"])
add_section("IsThereAnyDeal overview + prices (300-game sample)", "Relationships and Patterns",
            f"- `app_id` ↔ `itad_id` via /lookup/id/shop/61; ITAD ids are UUIDs.\n"
            f"- all_time_low ≤ best_price_now always holds: {(ov.all_time_low <= ov.best_price_now + 1e-9).mean():.0%} of rows.\n"
            f"- Free games show regular_price 0, so exclude them from value-per-dollar math.")
write("IsThereAnyDeal overview + prices (300-game sample)", "itad_sample.md")

# Supabase games table (the built index)
env = dotenv_values(HERE.parent / ".env")
try:
    from supabase import create_client
    sb = create_client(env["SUPABASE_URL"], env["SUPABASE_SERVICE_ROLE_KEY"])
    rows, start = [], 0
    while True:
        part = sb.table("games").select("app_id,title,release_date,item_type,tags,description_source,rating,positive_ratio,"
                                        "user_reviews,popularity,price_regular,embed_text").range(start, start + 999).execute().data
        rows += part
        if len(part) < 1000:
            break
        start += 1000
    nemb = sb.table("games").select("app_id", count="exact").not_.is_("embedding", "null").limit(1).execute().count
    sg = pd.DataFrame(rows)
    if len(sg):
        sg["release_date"] = pd.to_datetime(sg.release_date)
        profile_df("Supabase public.games (search index)", sg, "game in the search index", key="app_id",
                   notes=[f"Rows with an embedding: {nemb:,} of {len(sg):,}"])
        write("Supabase public.games (search index)", "supabase_games.md")
except Exception as ex:
    print("Supabase profile skipped:", ex)

write_readme()
