"""Embed the whole cleaned catalog for the recommender's content side (local only, no Supabase upload).

The first content side (index/build_index.py) covered only the 50,872 Kaggle games, so 2024-2026 releases had no
embedding. This embeds every game in the evaluation universe plus every recommendable game, from the cleaned catalog:
title + genres + tags (SteamSpy-refilled) + description, with the same gte-small model.

Run: OPENBLAS_NUM_THREADS=1 PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python model/embed_catalog.py [--limit N]
Out: model/artifacts/game_embeddings.npy, game_embedding_ids.npy (old pair kept as *_kaggle_only.npy)
"""
import argparse
import os
import shutil
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "model" / "artifacts"
MODEL = "thenlper/gte-small"


def as_list(v):
    return [str(x) for x in v] if v is not None and len(v) else []


def text(title, genres, tags, desc):
    parts = [f"{title}."]
    if genres:
        parts.append("Genres: " + ", ".join(genres) + ".")
    if tags:
        parts.append("Tags: " + ", ".join(tags[:15]) + ".")
    if desc:
        parts.append(desc)
    return " ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="embed only N games and write nothing (smoke test)")
    args = ap.parse_args()

    g = pd.read_parquet("C:/Users/juant/data_clean/games.parquet",
                        columns=["app_id", "title", "genres", "tags", "description", "recommendable"])
    U = np.load(ROOT / "eval" / "cache" / "universe.npy", allow_pickle=True)
    g = g[g.recommendable | g.app_id.isin(U)].reset_index(drop=True)
    texts = [text(t, as_list(ge), as_list(tg), d if isinstance(d, str) else "")
             for t, ge, tg, d in zip(g.title, g.genres, g.tags, g.description)]
    if args.limit:
        texts = texts[:args.limit]
    print(f"games to embed: {len(texts):,}", flush=True)

    from sentence_transformers import SentenceTransformer
    import torch
    torch.set_num_threads(os.cpu_count() or 4)
    model = SentenceTransformer(MODEL, device="cpu", model_kwargs={"dtype": torch.float32})

    t0, parts, step = time.time(), [], 5000
    for i in range(0, len(texts), step):
        parts.append(model.encode(texts[i:i + step], batch_size=256, normalize_embeddings=True,
                                  show_progress_bar=False, convert_to_numpy=True).astype("float32"))
        print(f"embedded {min(i + step, len(texts)):,}/{len(texts):,} ({time.time() - t0:.0f}s)", flush=True)
    emb = np.vstack(parts)
    if args.limit:
        print(f"smoke test ok: {emb.shape}", flush=True)
        return

    for n in ("game_embeddings", "game_embedding_ids"):
        old, keep = ART / f"{n}.npy", ART / f"{n}_kaggle_only.npy"
        if old.exists() and not keep.exists():
            shutil.copyfile(old, keep)
    np.save(ART / "game_embeddings.npy", emb)
    np.save(ART / "game_embedding_ids.npy", g.app_id.to_numpy())
    print(f"saved {len(emb):,} embeddings in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
