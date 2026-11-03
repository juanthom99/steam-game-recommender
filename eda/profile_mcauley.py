"""Profile the McAuley Australian Steam data (Wan & McAuley 2018; Kang & McAuley 2018; Pathak et al. 2017).

Source: Hugging Face mirror recommender-system/steam-review-and-bundle-dataset (copy of the UCSD files),
downloaded to ~/data_raw/mcauley/. Files are Python-dict-per-line, read with ast.literal_eval.

Run with the ML venv:
  C:/Users/juant/.venvs/steamrec-ml/Scripts/python eda/profile_mcauley.py
Writes eda/profiles/mcauley_*.md, merges the scorecard, and saves tidy parquet copies to ~/data_raw/mcauley/tidy/.
"""
import ast
import gzip
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profiling import HERE, KAGGLE, profile_df, add_section, write, write_readme  # noqa: E402

RAW = Path(os.path.expanduser("~/data_raw/mcauley"))
TIDY = RAW / "tidy"
TIDY.mkdir(exist_ok=True)


def read_loose_json(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield ast.literal_eval(line)


def to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# ---------------- users_items: full owned libraries with playtime
users, items = [], []
REUSE = (TIDY / "users_items.parquet").exists() and (TIDY / "users.parquet").exists()
for u in ([] if REUSE else read_loose_json(RAW / "australian_users_items.json.gz")):
    users.append({"user_id": u["user_id"], "steam_id": u.get("steam_id"), "items_count": u.get("items_count"),
                  "n_items_listed": len(u.get("items", []))})
    for i in u.get("items", []):
        items.append((u["user_id"], to_int(i.get("item_id")), i.get("item_name"),
                      i.get("playtime_forever"), i.get("playtime_2weeks")))
if REUSE:
    mu, mi = pd.read_parquet(TIDY / "users.parquet"), pd.read_parquet(TIDY / "users_items.parquet")
else:
    mu = pd.DataFrame(users)
    mi = pd.DataFrame(items, columns=["user_id", "app_id", "item_name", "playtime_forever", "playtime_2weeks"])
    mi["app_id"] = mi.app_id.astype("Int64")
    mi.to_parquet(TIDY / "users_items.parquet", index=False)
    mu.to_parquet(TIDY / "users.parquet", index=False)

profile_df("McAuley australian_users_items (users)", mu, "Steam user", key="user_id",
           notes=["items_count is what Steam reported; n_items_listed is what the file actually contains"])
add_section("McAuley australian_users_items (users)", "Relationships and Patterns",
            f"- Users with an empty library (private profile or no games): {(mu.n_items_listed == 0).sum():,} "
            f"({(mu.n_items_listed == 0).mean():.1%}). The live app will meet the same case.\n"
            f"- items_count ≠ n_items_listed for {(mu.items_count != mu.n_items_listed).sum():,} users.\n"
            f"- Duplicate steam_id across different user_id values: {mu.steam_id.duplicated().sum():,}.")
write("McAuley australian_users_items (users)", "mcauley_users.md")

profile_df("McAuley australian_users_items (owned games)", mi, "owned game for a user (full library)",
           key=["user_id", "app_id"],
           notes=["playtime in MINUTES, like the live Steam API; includes never-played games"])
kg = pd.read_csv(KAGGLE / "games.csv", usecols=["app_id", "title"])
cat = pd.read_csv(HERE / "steam_catalog.csv", usecols=["appid", "type"]).drop_duplicates("appid")
played = mi[mi.playtime_forever > 0]
per_user = mi.groupby("user_id").agg(owned=("app_id", "size"), played=("playtime_forever", lambda s: (s > 0).sum()))
mi_type = mi.app_id.map(cat.set_index("appid").type)
add_section("McAuley australian_users_items (owned games)", "Relationships and Patterns",
            f"- Never played (playtime 0 → *unknown* in Layer 1): {(mi.playtime_forever == 0).mean():.1%} of owned rows "
            f"(Wan & McAuley report ~36% unplayed).\n"
            f"- Played ≥ 120 min: {(mi.playtime_forever >= 120).mean():.1%} of owned rows; "
            f"{(played.playtime_forever >= 120).mean():.1%} of played rows.\n"
            f"- Owned per user: median {per_user.owned.median():.0f}, p90 {per_user.owned.quantile(.9):.0f}; "
            f"played per user: median {per_user.played.median():.0f}.\n"
            f"- Distinct games: {mi.app_id.nunique():,}; in Kaggle catalog: {mi.app_id.isin(kg.app_id).mean():.1%} of rows "
            f"({mi.app_id.drop_duplicates().isin(kg.app_id).mean():.1%} of distinct games).\n"
            f"- Steam type of owned rows: " + ", ".join(f"{k} {v:.1%}" for k, v in mi_type.fillna("delisted/unknown").value_counts(normalize=True).items()) + "\n"
            f"- Active in the 2 weeks before the crawl (playtime_2weeks > 0): {(mi.playtime_2weeks > 0).mean():.1%} of rows.")
write("McAuley australian_users_items (owned games)", "mcauley_users_items.md")

# ---------------- user reviews (recommend flag, joinable to playtime)
revs = []
for u in read_loose_json(RAW / "australian_user_reviews.json.gz"):
    for r in u.get("reviews", []):
        revs.append({"user_id": u["user_id"], "app_id": to_int(r.get("item_id")), "recommend": bool(r.get("recommend")),
                     "posted": r.get("posted"), "helpful": r.get("helpful"), "funny": r.get("funny"),
                     "review_len": len(r.get("review") or "")})
mr = pd.DataFrame(revs)
mr["posted_date"] = pd.to_datetime(mr.posted.str.replace("Posted ", "").str.rstrip("."), errors="coerce", format="mixed")
mr["app_id"] = mr.app_id.astype("Int64")
mr.drop(columns=["posted"]).to_parquet(TIDY / "user_reviews.parquet", index=False)
profile_df("McAuley australian_user_reviews", mr.drop(columns=["posted"]), "user review of a game", key=["user_id", "app_id"],
           notes=["`posted` has no year for reviews from the crawl year, so those dates parse as missing"])

# Layer 1 check on FULL-library users: label from playtime vs the review flag
pg = played.copy()
pg["g"] = pg.groupby("app_id").playtime_forever.rank(pct=True)
pg["n_players"] = pg.groupby("app_id").playtime_forever.transform("size")
pg["median_min"] = pg.groupby("app_id").playtime_forever.transform("median")
j = mr.merge(mi[["user_id", "app_id", "playtime_forever"]], on=["user_id", "app_id"], how="left") \
      .merge(pg[["user_id", "app_id", "g", "n_players", "median_min"]], on=["user_id", "app_id"], how="left")
found = j.playtime_forever.notna()
jj = j[j.g.notna() & (j.n_players >= 20)].copy()
floor_ok = (jj.playtime_forever >= 120) | (jj.median_min < 180)
lines = [f"- Reviews whose game is in the reviewer's owned list: {found.mean():.1%}; of those, played > 0: {(j.playtime_forever[found] > 0).mean():.1%}.",
         f"- Reviewed games with playtime 0 (reviewed but never launched per the crawl): {(j.playtime_forever == 0).sum():,}.",
         f"- Rows usable for the label check (played, game has ≥ 20 players): {len(jj):,}; recommended share {jj.recommend.mean():.1%}.",
         "", "| label | kappa vs recommend | enjoyed share |", "|---|---:|---:|"]
for c in (0.1, 0.2, 0.5):
    pred = (jj.g >= c) & floor_ok
    lines.append(f"| percentile ≥ {c} + 2 h floor | {cohen_kappa_score(jj.recommend, pred):.3f} | {pred.mean():.1%} |")
lines.append(f"| 2 h floor only | {cohen_kappa_score(jj.recommend, jj.playtime_forever >= 120):.3f} | {(jj.playtime_forever >= 120).mean():.1%} |")
lines.append(f"\n- ROC-AUC of game percentile g for predicting recommend: {roc_auc_score(jj.recommend, jj.g):.3f} "
             f"(Kaggle: 0.645). These users' playtime is the *crawl-time total*, not the time of the review.")
add_section("McAuley australian_user_reviews", "Layer 1 label check on full-library users", "\n".join(lines))
write("McAuley australian_user_reviews", "mcauley_user_reviews.md")

# ---------------- item metadata
gm = pd.DataFrame(read_loose_json(RAW / "steam_games.json.gz"))
gm["app_id"] = pd.to_numeric(gm.get("id"), errors="coerce").astype("Int64")
gm["release_date"] = pd.to_datetime(gm.release_date, errors="coerce")
gm["price_num"] = pd.to_numeric(gm.price, errors="coerce")
gm["price_text"] = gm.price.where(gm.price_num.isna())
gm = gm.drop(columns=[c for c in ("id", "price", "url", "reviews_url") if c in gm])
if "metascore" in gm:
    gm["metascore"] = pd.to_numeric(gm.metascore, errors="coerce")   # 'NA' strings -> null
for c in gm.columns:   # any other object column mixing scalars of different types -> string
    if gm[c].dtype == object and not gm[c].dropna().map(lambda v: isinstance(v, list)).any():
        gm[c] = gm[c].astype("string")
gm.to_parquet(TIDY / "steam_games.parquet", index=False)
profile_df("McAuley steam_games (item metadata)", gm, "Steam app (2018 crawl)", key="app_id",
           notes=["`price` mixes numbers and text such as 'Free To Play'; split into price_num / price_text"])
add_section("McAuley steam_games (item metadata)", "Relationships and Patterns",
            f"- Rows with no app id: {gm.app_id.isna().sum():,}.\n"
            f"- Overlap with Kaggle catalog: {gm.app_id.isin(kg.app_id).mean():.1%}. Kaggle is the newer, richer catalog; "
            f"this file mostly adds `specs` (single-player, co-op, controller support …) and `developer`/`publisher`.")
write("McAuley steam_games (item metadata)", "mcauley_steam_games.md")

# ---------------- bundles
bd = pd.DataFrame(read_loose_json(RAW / "bundle_data.json.gz"))
bd["n_items"] = bd["items"].apply(len)
for c in ("bundle_final_price", "bundle_price"):
    bd[c] = pd.to_numeric(bd[c].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce")
bd["bundle_discount"] = pd.to_numeric(bd.bundle_discount.astype(str).str.rstrip("%"), errors="coerce")
profile_df("McAuley bundle_data", bd.drop(columns=["bundle_url"]), "Steam bundle", key="bundle_id")
write("McAuley bundle_data", "mcauley_bundles.md")

write_readme()
