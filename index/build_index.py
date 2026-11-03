"""Build the game text index: embed every Kaggle game with gte-small and upsert to Supabase.

Run with the ML venv:
  C:/Users/juant/.venvs/steamrec-ml/Scripts/python index/build_index.py [--skip-upload]

Also saves the embeddings locally (model/artifacts/) for the recommender's content side.
Safe to re-run: rows are upserted by app_id.
"""
import argparse
import math
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.path.expanduser("~/.cache/kagglehub/datasets/antonkozyriev/game-recommendations-on-steam/versions/28"))
ART = ROOT / "model" / "artifacts"
MODEL = "thenlper/gte-small"  # same model as Supabase's built-in 'gte-small'


def embed_text(title, tags, desc):
    parts = [f"{title}."]
    if tags:
        parts.append("Tags: " + ", ".join(tags) + ".")
    if desc:
        parts.append(desc)
    return " ".join(parts)


def load_catalog():
    games = pd.read_csv(DATA / "games.csv", parse_dates=["date_release"])
    meta = pd.read_json(DATA / "games_metadata.json", lines=True)
    df = games.merge(meta, on="app_id", how="left")
    df["tags"] = df.tags.apply(lambda t: t if isinstance(t, list) else [])
    df["description"] = df.description.fillna("").str.strip()
    # Kaggle leaves price_original = 0 for paid games not on sale; use price_final there.
    df["price_regular"] = df.price_original.where(df.price_original > 0, df.price_final)
    df["embed_text"] = [embed_text(t, g, d) for t, g, d in zip(df.title, df.tags, df.description)]
    # Item type from Steam's own catalog (eda/fetch_steam_catalog.py); null = delisted / unknown
    cat_path = ROOT / "eda" / "steam_catalog.csv"
    if cat_path.exists():
        cat = pd.read_csv(cat_path, usecols=["appid", "type"]).drop_duplicates("appid")
        df["item_type"] = df.app_id.map(cat.set_index("appid").type)
    else:
        df["item_type"] = None
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-upload", action="store_true")
    ap.add_argument("--batch", type=int, default=256)
    args = ap.parse_args()

    df = load_catalog()
    print(f"catalog: {len(df):,} games; empty descriptions: {(df.description == '').sum():,}", flush=True)

    from sentence_transformers import SentenceTransformer
    import torch
    torch.set_num_threads(os.cpu_count() or 4)
    # float32: the default float16 load is ~8x slower on this CPU
    model = SentenceTransformer(MODEL, device="cpu", model_kwargs={"dtype": torch.float32})

    t0 = time.time()
    texts, parts = df.embed_text.tolist(), []
    step = 5000
    for i in range(0, len(texts), step):
        parts.append(model.encode(texts[i:i + step], batch_size=args.batch, normalize_embeddings=True,
                                  show_progress_bar=False, convert_to_numpy=True).astype("float32"))
        print(f"embedded {min(i + step, len(texts)):,}/{len(texts):,} ({time.time() - t0:.0f}s)", flush=True)
    emb = np.vstack(parts)
    print(f"embedded {len(emb):,} in {time.time() - t0:.0f}s; dim={emb.shape[1]}", flush=True)

    ART.mkdir(parents=True, exist_ok=True)
    np.save(ART / "game_embeddings.npy", emb)
    np.save(ART / "game_embedding_ids.npy", df.app_id.to_numpy())

    if args.skip_upload:
        return

    from supabase import create_client
    env = dotenv_values(ROOT / ".env")
    sb = create_client(env["SUPABASE_URL"], env["SUPABASE_SERVICE_ROLE_KEY"])

    def clean(v):
        return None if v is None or (isinstance(v, float) and math.isnan(v)) else v

    rows = []
    for r, e in zip(df.itertuples(index=False), emb):
        rows.append({
            "app_id": int(r.app_id),
            "title": r.title,
            "release_date": r.date_release.date().isoformat() if pd.notna(r.date_release) else None,
            "item_type": clean(r.item_type),
            "tags": r.tags,
            "tags_text": " ".join(r.tags),
            "description": r.description,
            "description_source": "kaggle" if r.description else "none",
            "rating": clean(r.rating),
            "positive_ratio": clean(int(r.positive_ratio)),
            "user_reviews": clean(int(r.user_reviews)),
            "popularity": float(np.log1p(r.user_reviews)),
            "price_regular": clean(float(r.price_regular)),
            "embed_text": r.embed_text,
            "embedding": "[" + ",".join(f"{x:.6f}" for x in e) + "]",
        })

    t0 = time.time()
    for i in range(0, len(rows), 500):
        for attempt in range(4):
            try:
                sb.table("games").upsert(rows[i:i + 500], on_conflict="app_id").execute()
                break
            except Exception as ex:  # transient network errors
                if attempt == 3:
                    raise
                print(f"retry batch {i}: {ex}", flush=True)
                time.sleep(5 * (attempt + 1))
        if (i // 500) % 20 == 0:
            print(f"uploaded {min(i + 500, len(rows)):,}/{len(rows):,}", flush=True)
    print(f"upload done in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
