"""Tune stage 1 (playtime-only enjoyment score).

Training data never includes pilot players. Selection set = pilot players NOT in the locked holdout
(their McAuley reviews; stage 1 needs only playtime, so private profiles count too). The holdout is untouched here.

Candidates
  - training source: McAuley only | Kaggle only (25% user sample) | pooled (McAuley up-weighted)
  - feature set: S1 (g, resid, u_rank) | S1x (+ u_med, u_ratio_rank, tag_q: still player-relative, no popularity)
  - hyperparameters: 12 random configs, chosen by grouped CV inside the training data (never on the selection set)
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python label/tune_stage1.py
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from enjoy_score import load, grouped_auc, D  # noqa: E402

S1 = ["g", "resid", "u_rank"]
S1X = S1 + ["u_med", "u_ratio_rank", "tag_q"]
pairs = pd.read_parquet(D / "pilot" / "pairs.parquet")
hold = set(json.load(open(D / "pilot" / "holdout_users.json"))["uids"])
pilot_keys = set(pairs.user_key)
sel_keys = set(pairs.user_key[~pairs.uid.isin(hold)])

a = load()
a["y"] = a.review_recommend.astype(bool)
mc = a[a.ds == "McAuley"]
train_mc = mc[~mc.user_key.isin(pilot_keys)]
sel = mc[mc.user_key.isin(sel_keys)]
train_kg = a[a.ds == "Kaggle"]
print(f"McAuley train {len(train_mc):,}  selection {len(sel):,}  Kaggle train {len(train_kg):,}", flush=True)

rng = np.random.default_rng(0)
grid = [dict(learning_rate=float(rng.choice([0.03, 0.05, 0.1])), max_leaf_nodes=int(rng.choice([7, 15, 31, 63])),
             min_samples_leaf=int(rng.choice([20, 100, 400])), l2_regularization=float(rng.choice([0.0, 1.0, 5.0])),
             max_iter=int(rng.choice([150, 300, 600]))) for _ in range(12)]


def fit(params, X, y, w=None):
    return HistGradientBoostingClassifier(random_state=0, early_stopping=False, **params).fit(X, y, sample_weight=w)


def cv_pick(df, cols, w=None, folds=3):
    """Pick hyperparameters by grouped CV inside the training data (users split by key)."""
    f = (df.user_key.to_numpy() * 2654435761 % 2**32) % folds
    best, best_auc = None, -1
    for params in grid:
        aucs = []
        for k in range(folds):
            tr, te = f != k, f == k
            m = fit(params, df[cols][tr], df.y[tr], None if w is None else w[tr])
            aucs.append(roc_auc_score(df.y[te], m.predict_proba(df[cols][te])[:, 1]))
        if np.mean(aucs) > best_auc:
            best, best_auc = params, float(np.mean(aucs))
    return best, best_auc


DEFAULT = dict(learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=20, l2_regularization=1.0, max_iter=400)
rows, models = [], {}


def score(name, m, cols, params, cv_auc):
    p = m.predict_proba(sel[cols])[:, 1]
    wu, nu = grouped_auc(sel.y.to_numpy(), p, sel.user_key.to_numpy(), 2, 1)
    rows.append({"candidate": name, "features": "S1x" if cols == S1X else "S1", "selection AUC": roc_auc_score(sel.y, p),
                 "selection within-user AUC": wu, "users": nu, "train-CV AUC": cv_auc, "params": json.dumps(params)})
    models[name] = (m, cols)
    print(rows[-1], flush=True)


for cols in (S1, S1X):
    tag = "S1x" if cols == S1X else "S1"
    score(f"McAuley default {tag}", fit(DEFAULT, train_mc[cols], train_mc.y), cols, DEFAULT, np.nan)
    p, c = cv_pick(train_mc, cols)
    score(f"McAuley tuned {tag}", fit(p, train_mc[cols], train_mc.y), cols, p, c)
    kg = train_kg.sample(min(len(train_kg), 1_500_000), random_state=0)      # tuning sample (speed)
    p, c = cv_pick(kg, cols)
    score(f"Kaggle tuned {tag}", fit(p, train_kg[cols], train_kg.y), cols, p, c)
    pool = pd.concat([train_mc, train_kg], ignore_index=True)
    w = np.where(pool.ds == "McAuley", len(train_kg) / len(train_mc), 1.0)
    score(f"Pooled (McAuley weighted) {tag}", fit(p, pool[cols], pool.y, w), cols, p, c)

t = pd.DataFrame(rows).sort_values("selection AUC", ascending=False)
best = t.iloc[0].candidate
pickle.dump({"name": best, "model": models[best][0], "features": models[best][1]}, open(HERE / "cache" / "stage1_best.pkl", "wb"))
(HERE / "stage1_tuning.md").write_text(
    "# Stage 1 tuning\n\nTraining never includes pilot players; scored on non-holdout pilot players' McAuley reviews.\n\n"
    + t.drop(columns=["params"]).round(3).to_markdown(index=False) + f"\n\nChosen: **{best}**\n\nParams:\n\n"
    + t[["candidate", "params"]].to_markdown(index=False) + "\n", encoding="utf-8")
print("chosen:", best)
