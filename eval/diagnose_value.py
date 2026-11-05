"""Post-hoc: is the value-per-dollar gap vs MostPopular a popularity effect? VALIDATION players only.

Same measure as eval/layer3.py: hours per dollar of regular price over hit picks (paid), and for free picks the
share played past 2 h / 10 h. Split by the picked game's popularity (training players).
Run: OPENBLAS_NUM_THREADS=4 PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python eval/diagnose_value.py
Out: eval/diagnosis_value.md
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from harness import load, train_matrix  # noqa: E402
from models import EASE, Hybrid, MostPopular  # noqa: E402

C = HERE / "cache"
U, rec, val = load("validation")
val = [p for p in val if p["n_visible"] >= 5]
X = train_matrix()
best = json.load(open(C / "best_params.json"))
pop = np.load(C / "n_train_players.npy")
g = pd.read_parquet("C:/Users/juant/data_clean/games.parquet", columns=["app_id", "price_regular", "kaggle_price_regular", "price_source"])
price = g.price_regular.where(g.price_source.eq("itad_steam_regular"), g[["price_regular", "kaggle_price_regular"]].max(axis=1)).set_axis(g.app_id).reindex(U).to_numpy()   # rule G24: Steam regular price when known

ids = np.load(HERE.parent / "model" / "artifacts" / "game_embedding_ids.npy")
emb = np.load(HERE.parent / "model" / "artifacts" / "game_embeddings.npy")
E = np.zeros((len(U), emb.shape[1]), np.float32)
pos = pd.Series(np.arange(len(U)), index=U).reindex(ids); ok = pos.notna().to_numpy()
E[pos[ok].astype(int).to_numpy()] = emb[ok]

t0 = time.time()
mp = MostPopular().fit(X)
ease = EASE(**best["EASE"]).fit(X)
models = {"MostPopular": mp, "EASE": ease, "Hybrid-EASE": Hybrid(ease, E, **best["Hybrid-EASE"])}
print(f"fitted ({time.time() - t0:.0f}s)", flush=True)

rows = []
for k in range(0, len(val), 256):
    batch = val[k:k + 256]
    for name, m in models.items():
        S = m.score(batch)
        for r, p in enumerate(batch):
            s = S[r]; s[~rec] = -np.inf; s[np.setdiff1d(p["owned_u"], p["hid_u"])] = -np.inf
            top = np.argpartition(-s, 10)[:10]
            top = top[np.isfinite(s[top])]
            pt = dict(zip(p["hid_u"].tolist(), p["hid_pt"].tolist()))
            hits = set(p["hit_u"].tolist())
            for t in top:
                if t in pt:
                    rows.append((name, int(t), pt[t], pop[t], price[t], t in hits))
    print(f"{k + len(batch):,}/{len(val):,} ({time.time() - t0:.0f}s)", flush=True)

P = pd.DataFrame(rows, columns=["model", "item", "pt", "pop", "price", "hit"])
edges = np.unique(np.quantile(P.drop_duplicates("item")["pop"], [0, .5, .8, .95, 1]))
P["popularity"] = pd.cut(P["pop"], edges, include_lowest=True, labels=["bottom 50%", "50-80%", "80-95%", "top 5%"][:len(edges) - 1])
paid = P[P.hit & (P.price > 0)].assign(hpd=lambda d: d.pt / 60 / d.price)
free = P[P.price == 0]

overall = pd.DataFrame({
    "paid hits": paid.groupby("model").size(),
    "median hours per $": paid.groupby("model").hpd.median(),
    "median price of paid hits": paid.groupby("model").price.median(),
    "median hours (paid hits)": paid.groupby("model").pt.median() / 60,
    "free played picks": free.groupby("model").size(),
    "free > 2 h": free.groupby("model").pt.apply(lambda x: (x >= 120).mean()),
    "free > 10 h": free.groupby("model").pt.apply(lambda x: (x >= 600).mean())})
hpd_bin = paid.pivot_table(index="model", columns="popularity", values="hpd", aggfunc="median", observed=True)
hours_bin = paid.pivot_table(index="model", columns="popularity", values="pt", aggfunc="median", observed=True) / 60
free_bin = free.assign(f2=free.pt >= 120).pivot_table(index="model", columns="popularity", values="f2", aggfunc="mean", observed=True)
mix = paid.pivot_table(index="model", columns="popularity", values="hpd", aggfunc="size", observed=True)
mix = mix.div(mix.sum(1), axis=0)

md = ["# Post-hoc: value per dollar vs game popularity (validation players, test set not used)\n",
      f"{len(val):,} validation players with 5+ visible games. Exploratory, not pre-registered. Price = regular price "
      "(same column as `eval/layer3.py`). Popularity bins are over picked games by training players.\n",
      "## Overall\n", overall.round(3).to_markdown(),
      "\n## Median hours per $ (paid hits) by popularity\n", hpd_bin.round(3).to_markdown(),
      "\n## Median hours played (paid hits) by popularity\n", hours_bin.round(1).to_markdown(),
      "\n## Free picks played > 2 h by popularity\n", free_bin.round(3).to_markdown(),
      "\n## Popularity mix of paid hits\n", mix.round(3).to_markdown()]
(HERE / "diagnosis_value.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(md))
