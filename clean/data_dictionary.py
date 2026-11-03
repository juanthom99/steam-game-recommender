"""Data dictionary for every cleaned table: grain, row count, and per column the type, % missing, an example and a
description. Types, counts and examples are computed from the files; descriptions are written here.
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python clean/data_dictionary.py
Out: clean/data_dictionary.md, clean/data_dictionary.csv
"""
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

D = Path("C:/Users/juant/data_clean")
R = Path("C:/Users/juant/data_raw/steam_reviews")
HERE = Path(__file__).resolve().parent

TABLES = {
    "games.parquet": ("One row per Steam app (game, DLC, tool, removed app...). Merged catalog: Kaggle 2023 + FronkonGames "
                      "Oct 2026 + McAuley + Steam app list.", {
        "app_id": "Steam app id (primary key; joins every table)",
        "title": "Display title, HTML entities decoded, hidden characters removed",
        "release_date": "Release date (Kaggle, else Fronkon)",
        "win": "Runs on Windows", "mac": "Runs on macOS", "linux": "Runs on Linux",
        "rating": "Steam review summary label (Kaggle 2023, e.g. 'Very Positive')",
        "positive_ratio": "% positive Steam reviews (Kaggle 2023)",
        "user_reviews": "Number of Steam reviews (Kaggle 2023)",
        "steam_deck": "Steam Deck verified flag (Kaggle)",
        "description": "Short store description (Kaggle, else Fronkon, else Steam backfill)",
        "tags": "Steam user tags, most-voted first (empty list for 66% of recommendable games: the FronkonGames copy has no tags)",
        "title_raw": "Title before cleaning (audit trail)",
        "title_norm": "Lower-case title without punctuation/edition words, for matching",
        "kaggle_price_regular": "Regular USD price in Kaggle (2023)",
        "kaggle_price_final": "Price paid at Kaggle crawl time, after discount",
        "price_original_was_missing": "Kaggle listed regular price 0 on a paid game (rule G3)",
        "kaggle_discount": "Kaggle discount %",
        "description_source": "Where the description came from (kaggle / fronkon / steam / none)",
        "n_tags": "Number of tags",
        "steam_name": "Name in Steam's app list",
        "steam_last_modified": "Steam app list last-modified time",
        "item_type": "game, dlc, demo, tool, software, video, music, mod, episode, playtest, removed, unknown",
        "delisted": "Store page no longer exists (kept for history, never recommended)",
        "dup_title": "Shares a normalized title with another app (remasters, regional editions)",
        "developer": "Developer (McAuley)", "publisher": "Publisher (McAuley)",
        "specs": "Store features from McAuley (co-op, controller...)",
        "early_access": "Early Access flag (McAuley)",
        "mc_genres": "Genres from McAuley",
        "catalog_source": "Which dataset the row came from (kaggle / fronkon / mcauley)",
        "genres": "Store genres (Fronkon)", "categories": "Store categories (Fronkon)",
        "f_developers": "Developers (Fronkon)", "f_publishers": "Publishers (Fronkon)",
        "header_image": "Store header image URL",
        "steamspy_median_playtime_min": "SteamSpy median lifetime playtime, minutes (null = unknown, rule F1)",
        "steamspy_avg_playtime_min": "SteamSpy average lifetime playtime, minutes",
        "steam_positive": "Positive reviews (Fronkon, Oct 2026)", "steam_negative": "Negative reviews (Fronkon, Oct 2026)",
        "owners_lo": "Estimated owners, low end of SteamSpy band", "owners_hi": "Estimated owners, high end",
        "fronkon_price": "Price at Fronkon crawl (can be a sale price)",
        "peak_ccu": "Peak concurrent players (Fronkon)", "achievements": "Number of achievements",
        "adult": "Sexually explicit content (rule G17); excluded from recommendations",
        "mature_18": "Steam 18+ age gate (mostly violence); not filtered",
        "price_regular": "Regular USD price: higher of Kaggle 2023 regular and Fronkon 2026 when both exist (rule G18); "
                         "Fronkon-only games are re-priced from SteamSpy by clean/merge_steamspy.py",
        "price_source": "kaggle_2023_higher / fronkon_2026 / fronkon_2026_only (not yet cross-checked) / kaggle_2023 / none",
        "desc_short": "Description under 40 characters", "desc_shared": "Description shared by several apps",
        "desc_non_english": "Description mostly non-Latin script",
        "history_ok": "Counts as play history (game/unknown/removed/mod/demo/episode)",
        "recommendable": "Candidate for recommendations: game, on sale, released, not adult, has store data"}),
    "interactions_mcauley.parquet": ("One row per (player, owned app) from McAuley's Australian Steam crawl (2017): full "
                                     "libraries, played and unplayed.", {
        "source": "Always 'mcauley'", "user_key": "Integer player id (map in users_mcauley_map)",
        "app_id": "Steam app id", "playtime_min": "Lifetime playtime, minutes, at crawl time",
        "playtime_2w_min": "Playtime in the 2 weeks before the crawl, minutes",
        "played": "playtime_min > 0 (unplayed rows are 'unknown', not dislikes)",
        "censored": "Playtime hit a cap (always False here)", "is_game": "App is a game (not DLC/tool/removed)",
        "item_type": "App type from the catalog", "history_ok": "App counts as play history",
        "review_recommend": "Thumbs up (True) / down (False) if this player reviewed this game, else null",
        "review_date": "Review date", "helpful": "Helpful votes on the review", "funny": "Funny votes on the review"}),
    "interactions_kaggle.parquet": ("One row per (player, reviewed app) from the Kaggle Steam reviews dump (to Oct 2023). "
                                    "Only reviewed games: a partial library.", {
        "source": "Always 'kaggle'", "user_key": "Kaggle user id", "app_id": "Steam app id",
        "playtime_min": "Hours at review time x 60 (export caps at 1,000 h)", "playtime_2w_min": "Not available (0)",
        "played": "playtime_min > 0", "censored": "Hit the 1,000 h cap (rule K4)", "is_game": "App is a game",
        "history_ok": "App counts as play history", "bulk_user": "Bulk reviewer (rule K7)",
        "pre_release_review": "Review > 30 days before listed release (Early Access; rule K8)",
        "review_recommend": "Thumbs up / down", "review_date": "Review date",
        "helpful": "Helpful votes", "funny": "Funny votes"}),
    "users_kaggle.parquet": ("One row per Kaggle reviewer.", {
        "user_id": "Kaggle user id (= user_key)", "products": "Apps owned per Kaggle (unreliable, rule U1)",
        "reviews": "Reviews written on Steam", "reviews_in_data": "Reviews present in this dataset",
        "products_inconsistent": "0 products but has reviews", "bulk_reviewer": "Bulk reviewer (rule K7)"}),
    "users_mcauley_map.parquet": ("One row per McAuley player.", {
        "user_key": "Integer id used in interactions_mcauley", "mc_user_id": "Original McAuley user id",
        "n_owned": "Apps owned", "n_played": "Apps with playtime > 0", "n_played_hist": "Played apps that count as history",
        "collector": "Owns >= 3,000 apps", "no_played": "Owns apps but played none"}),
    "steam_catalog_extra.parquet": ("Steam apps in no dataset (names only), for the weekly catalog refresh.", {
        "app_id": "Steam app id", "name": "App name", "type": "App type", "last_modified": "Last modified on Steam"}),
}


def profile(path, desc):
    f = pq.ParquetFile(path)
    n = f.metadata.num_rows
    rows = []
    for col in f.schema_arrow:
        s = pd.read_parquet(path, columns=[col.name])[col.name]
        nn = s.dropna()
        ex = nn.iloc[len(nn) // 2] if len(nn) else None
        if hasattr(ex, "__len__") and not isinstance(ex, str):
            ex = list(ex)[:3]
        ex = str(ex)[:40]
        rows.append({"column": col.name, "type": str(col.type).replace("large_", ""), "% missing": round(100 * (1 - len(nn) / n), 1),
                     "example": ex, "description": desc.get(col.name, "")})
    return n, pd.DataFrame(rows)


out = ["# Data dictionary\n\nCleaned tables in `data_clean/` (built by `clean/build_clean.py`; rules G/F/K/M/U in "
       "`clean/cleaning_report.md`). Missing % and examples are computed from the files.\n"]
allrows = []
for name, (grain, desc) in TABLES.items():
    n, t = profile(D / name, desc)
    print(name, n, flush=True)
    out.append(f"## {name}\n\n**Grain:** {grain}  \n**Rows:** {n:,}\n\n" + t.to_markdown(index=False) + "\n")
    allrows.append(t.assign(table=name))

# the 2026 collection (raw JSON lines; hashed ids only, no review text)
out.append("## steam_reviews 2026 collection (`data_raw/steam_reviews/`)\n\nCollected Oct 2026 from Steam's official "
           "IUserReviewsService and Web API. Player ids are salted SHA-256 hashes; no review text is stored.\n\n"
           "| file | grain | key fields |\n|---|---|---|\n"
           "| reviews.jsonl | one recent review (an 'all' page and a 'negative' page per game, 1,004 games) | uid, app_id, voted_up, "
           "playtime_at_review, playtime_forever, playtime_2w, last_played, refunded, created, page |\n"
           "| libraries.jsonl | one reviewer's full library (public profiles only; 2,696 public) | uid, public, games "
           "[app_id, playtime_forever, playtime_2w, last_played] |\n"
           "| achievements.jsonl | one reviewer x reviewed game | uid, app_id, success, ach [name, achieved, unlock time] |\n"
           "| global_pct.jsonl | one game | app_id, pct {achievement: global unlock %} |\n")
m = json.load(open(D / "splits" / "manifest.json")) if (D / "splits" / "manifest.json").exists() else None
out.append("## splits/ (reserved evaluation data)\n\n| file | grain |\n|---|---|\n"
           "| players.parquet | one test or validation player: src, user_key, split |\n"
           "| hidden_games.parquet | one played game of a test/validation player: src, user_key, app_id, split, hidden |\n"
           "| manifest.json | the rule, counts and SHA-256 of each file |\n"
           + ("" if m is None else f"\nCreated {m['created']}; see `eval/PROTOCOL.md`.\n"))
(HERE / "data_dictionary.md").write_text("\n".join(out), encoding="utf-8")
pd.concat(allrows).to_csv(HERE / "data_dictionary.csv", index=False)
print("written")
