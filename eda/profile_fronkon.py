"""Profile the FronkonGames Steam games dataset (Hugging Face, MIT license, updated 2026-10-15).

Source: https://huggingface.co/datasets/FronkonGames/steam-games-dataset  -> ~/data_raw/fronkon/games.parquet
Run with the ML venv:  C:/Users/juant/.venvs/steamrec-ml/Scripts/python eda/profile_fronkon.py
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profiling import HERE, KAGGLE, profile_df, add_section, write, write_readme  # noqa: E402

f = pd.read_parquet(os.path.expanduser("~/data_raw/fronkon/games.parquet"))
f["app_id"] = pd.to_numeric(f.appID, errors="coerce").astype("int64")
f["release_date"] = pd.to_datetime(f.release_date, errors="coerce", format="mixed")
# array columns -> lists so the profiler treats them as structural
for c in f.columns:
    if f[c].dtype == object and len(f) and isinstance(f[c].dropna().iloc[0] if f[c].notna().any() else None, np.ndarray):
        f[c] = f[c].map(lambda v: list(v) if isinstance(v, np.ndarray) else v)
prof = f.drop(columns=["appID", "detailed_description", "screenshots", "movies", "packages", "reviews", "notes",
                       "support_email", "support_url", "website", "metacritic_url"], errors="ignore")
profile_df("FronkonGames steam-games-dataset", prof, "Steam game (store page + SteamSpy stats, Oct 2026)", key="app_id",
           notes=["Zeros in median/average playtime, metacritic and user_score mean *not available* (SteamSpy/Metacritic gaps), not zero"])

k = pd.read_csv(KAGGLE / "games.csv", usecols=["app_id"])
cat = pd.read_csv(HERE / "steam_catalog.csv", usecols=["appid", "type"])
lib = pd.read_csv(HERE / "steam_my_library.csv")
F, K = set(f.app_id), set(k.app_id)
G = set(cat[cat.type == "game"].appid)
yrs = f.release_date.dt.year.value_counts().sort_index()
add_section("FronkonGames steam-games-dataset", "Relationships and Patterns",
            f"- Joins on Steam `app_id`. Overlap with Kaggle: {len(F & K):,}; Fronkon-only games: {len(F - K):,}; "
            f"Kaggle games missing here: {len(K - F):,}.\n"
            f"- Steam games covered: Kaggle {len(G & K) / len(G):.1%} → Kaggle + Fronkon **{len(G & (K | F)) / len(G):.1%}**.\n"
            f"- Your library known: Kaggle {lib.appid.isin(K).sum()}/{len(lib)} → combined **{lib.appid.isin(K | F).sum()}/{len(lib)}**.\n"
            f"- Releases 2024: {yrs.get(2024, 0):,}; 2025: {yrs.get(2025, 0):,}; 2026 (to {f.release_date.max():%b %d}): {yrs.get(2026, 0):,}.\n"
            f"- median_playtime_forever available (> 0) for {(f.median_playtime_forever > 0).mean():.1%} of games: "
            f"usable as a per-game playtime prior for games with no interactions in our data.\n"
            f"- Tags present for {(f.tags.map(lambda t: len(t) if isinstance(t, (list, dict)) else 0) > 0).mean():.1%} of games; "
            f"categories (co-op, controller, achievements…) for {(f.categories.map(lambda t: len(t) if isinstance(t, list) else 0) > 0).mean():.1%}.\n"
            f"- `estimated_owners` is a SteamSpy band string (e.g. '0 - 20000'); parse to the band's lower/upper bound.")
write("FronkonGames steam-games-dataset", "fronkon_games.md")
write_readme()
