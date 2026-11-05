"""Upsert the full recommendable catalog (~111k games) into Supabase public.games, with the gte-small embeddings
from model/embed_catalog.py stored as halfvec. Replaces index/build_index.py (Kaggle-only, 50k).

Order: apply supabase/migrations/20261104_01_games_halfvec.sql, run this, then 20261104_02_games_hnsw.sql.
Upserts by app_id (deletes nothing). Prices follow rule G24; ratings missing from Kaggle are derived from Steam
review counts with Steam's own labels. Uses SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY from .env (never printed).
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python index/load_games.py [--dry-run] [--start N]
"""
import argparse
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
D = Path("C:/Users/juant/data_clean")
ART = ROOT / "model" / "artifacts"


def steam_label(pos, n):
    """Steam's review-summary labels from the positive share and review count."""
    if not n or n < 10:
        return None
    r = pos / n
    if r >= 0.95 and n >= 500: return "Overwhelmingly Positive"
    if r >= 0.80: return "Very Positive" if n >= 50 else "Positive"
    if r >= 0.70: return "Mostly Positive"
    if r >= 0.40: return "Mixed"
    if r >= 0.20: return "Mostly Negative"
    return "Overwhelmingly Negative" if n >= 500 else ("Very Negative" if n >= 50 else "Negative")


def clean(v):
    if v is None:
        return None
    if isinstance(v, (float, np.floating)) and math.isnan(v):
        return None
    return v.item() if isinstance(v, np.generic) else v


def build_rows():
    g = pd.read_parquet(D / "games.parquet")
    g = g[g.recommendable].reset_index(drop=True)
    ids = np.load(ART / "game_embedding_ids.npy")
    emb = np.load(ART / "game_embeddings.npy")
    pos = pd.Series(np.arange(len(ids)), index=ids)
    g = g[g.app_id.isin(pos.index)].reset_index(drop=True)
    E = emb[pos.loc[g.app_id].to_numpy()]
    price = g.price_regular.where(g.price_source.eq("itad_steam_regular"), g[["price_regular", "kaggle_price_regular"]].max(axis=1))
    sp, sn = g.steam_positive.fillna(0), g.steam_negative.fillna(0)
    n_steam = sp + sn
    n_rev = n_steam.where(n_steam > 0, g.user_reviews).fillna(0)
    ratio = (100 * sp / n_steam.where(n_steam > 0)).fillna(g.positive_ratio)
    rows = []
    for k, r in enumerate(g.itertuples(index=False)):
        tags = [str(t) for t in (r.tags if r.tags is not None and len(r.tags) else (r.genres if r.genres is not None else []))]
        n = int(n_rev.iat[k])
        rating = r.rating if isinstance(r.rating, str) else steam_label(sp.iat[k], int(n_steam.iat[k]))
        rows.append({
            "app_id": int(r.app_id), "title": r.title,
            "release_date": pd.Timestamp(r.release_date).date().isoformat() if pd.notna(r.release_date) else None,
            "item_type": r.item_type, "tags": tags, "tags_text": " ".join(tags),
            "description": (r.description if isinstance(r.description, str) else "")[:1000],
            "description_source": {"kaggle": "kaggle", "fronkon": "steam"}.get(r.description_source, "none"),   # Fronkon crawled the Steam store
            "rating": rating, "positive_ratio": None if pd.isna(ratio.iat[k]) else int(round(ratio.iat[k])),
            "user_reviews": n, "popularity": float(np.log1p(n)),
            "price_regular": clean(None if pd.isna(price.iat[k]) else round(float(price.iat[k]), 2)),
            "price_source": r.price_source,
            "explicit": bool(r.explicit), "content_level": r.content_level, "explicit_reason": r.explicit_reason,   # rule G25
            "embedding": "[" + ",".join(f"{x:.5f}" for x in E[k]) + "]"})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--start", type=int, default=0, help="resume from this row")
    ap.add_argument("--batch", type=int, default=250)
    a = ap.parse_args()
    rows = build_rows()
    print(f"rows: {len(rows):,}; with rating {sum(r['rating'] is not None for r in rows):,}; "
          f"with price {sum(r['price_regular'] is not None for r in rows):,}", flush=True)
    if a.dry_run:
        r = dict(rows[0]); r["embedding"] = r["embedding"][:40] + "..."
        print(r)
        return
    from supabase import create_client
    env = dotenv_values(ROOT / ".env")
    sb = create_client(env["SUPABASE_URL"], env["SUPABASE_SERVICE_ROLE_KEY"])
    t0 = time.time()
    for i in range(a.start, len(rows), a.batch):
        for attempt in range(5):
            try:
                sb.table("games").upsert(rows[i:i + a.batch], on_conflict="app_id").execute()
                break
            except Exception as ex:
                if attempt == 4:
                    raise SystemExit(f"failed at row {i} (rerun with --start {i}): {ex}")
                time.sleep(5 * (attempt + 1))
        if (i // a.batch) % 40 == 0:
            print(f"uploaded {min(i + a.batch, len(rows)):,}/{len(rows):,} ({time.time() - t0:.0f}s)", flush=True)
    print(f"done: {len(rows):,} rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
