"""Offline check on players the model never saw (model/artifacts/heldout.parquet).

Per player: hide a random 20% of their played games, fold in the other 80% (same equation as live), rank every game
in the model's vocabulary except the 80%, and score against the hidden games they enjoyed (g >= 0.5).
Metrics: NDCG@10 (binary gain) and Recall@20, full-catalog ranking (no sampled negatives). Baseline: MostPopular
(how many training players enjoyed the game). Paired bootstrap CI over players.
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python model/eval_offline.py
Out: model/eval_offline.md
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
A = HERE / "artifacts"
z = np.load(A / "als.npz")
Y = z["item_factors"].astype(np.float64)
alpha, _, reg, _, _ = z["params"]
idx = {int(a): i for i, a in enumerate(z["app_ids"])}
pop = pd.read_parquet(A / "items.parquet").set_index("app_id").n_enjoyed.reindex(z["app_ids"]).to_numpy(float)
YtY = Y.T @ Y + reg * np.eye(Y.shape[1])
h = pd.read_parquet(A / "heldout.parquet")
h = h[h.app_id.isin(idx)]
rng = np.random.default_rng(0)
disc = 1 / np.log2(np.arange(2, 12))


def metrics(scores, known, target):
    s = scores.copy(); s[known] = -np.inf
    top = np.argpartition(-s, 20)[:20]; top = top[np.argsort(-s[top])]
    hit = np.isin(top, target)
    ideal = disc[:min(len(target), 10)].sum()
    return (hit[:10] * disc).sum() / ideal, hit.sum() / min(len(target), 20)


rows = []
for u, d in h.groupby("user"):
    d = d.sample(frac=1, random_state=int(rng.integers(1 << 30)))
    k = max(1, int(round(len(d) * 0.2)))
    test, train = d.iloc[:k], d.iloc[k:]
    target = np.array([idx[a] for a in test.app_id[test.g >= 0.5]])
    if len(target) == 0 or len(train) == 0:
        continue
    ti = np.array([idx[a] for a in train.app_id]); c = 1 + alpha * train.g.to_numpy()
    Yu = Y[ti]
    x = np.linalg.solve(YtY + (Yu * (c - 1)[:, None]).T @ Yu, (Yu * c[:, None]).sum(0))
    n1, r1 = metrics(Y @ x, ti, target)
    n0, r0 = metrics(pop, ti, target)
    rows.append({"src": d.src.iloc[0], "n_train": len(train), "ndcg_als": n1, "ndcg_pop": n0, "rec_als": r1, "rec_pop": r0})
r = pd.DataFrame(rows)
bucket = pd.cut(r.n_train, [0, 20, 100, 1e9], labels=["8-20 games", "21-100", "100+"])


def summ(x, name):
    diff = (x.ndcg_als - x.ndcg_pop).to_numpy()
    b = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(2000)]
    return {"group": name, "players": len(x), "NDCG@10 ALS": x.ndcg_als.mean(), "NDCG@10 MostPopular": x.ndcg_pop.mean(),
            "difference": diff.mean(), "95% CI": f"{np.percentile(b, 2.5):+.3f} to {np.percentile(b, 97.5):+.3f}",
            "Recall@20 ALS": x.rec_als.mean(), "Recall@20 MostPopular": x.rec_pop.mean()}


t = pd.DataFrame([summ(r, "all")] + [summ(x, f"source: {s}") for s, x in r.groupby("src")]
                 + [summ(x, f"library: {b}") for b, x in r.groupby(bucket, observed=True)])
md = ("# Offline check - held-out players\n\nHide 20% of each player's played games, fold in the rest, rank the full "
      "vocabulary. Hits = hidden games the player enjoyed (playtime percentile >= 0.5).\n\n" + t.round(3).to_markdown(index=False) + "\n")
(HERE / "eval_offline.md").write_text(md, encoding="utf-8")
print(md)
