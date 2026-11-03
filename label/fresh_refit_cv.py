"""Does refitting the enjoyment score on fresh (2026) Steam reviews beat raw playtime? Cross-validation only.

A locked holdout of 20% of games (sha256('fresh-holdout-v1' + app_id) % 5 == 0) is set aside and NOT touched here.
CV: 5 folds grouped by game, on the remaining games.
Clean sample (inherited from retest_reviews.py): only the unbiased 'all recent reviews' page, one review per reviewer
in the library table. Library size and days-since-last-played were dropped: both were sampling artifacts (prolific
reviewers; the negative page reaching further back in time).
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python label/fresh_refit_cv.py
Out: label/fresh_refit_cv.md, label/cache/fresh_table.parquet
"""
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
src = (HERE / "retest_reviews.py").read_text(encoding="utf-8").split("tA, tB =")[0]
ns = {"__file__": str(HERE / "retest_reviews.py")}
exec(src, ns)                                  # reuse the re-test's data loading and stage-1 feature builder
from enjoy_score import grouped_auc  # noqa: E402

played, libs = ns["played"], ns["libs"]
hold = lambda a: int(hashlib.sha256(f"fresh-holdout-v1{a}".encode()).hexdigest(), 16) % 5 == 0
fetch_ts = played.created.max()

# ---- library-free table: every review (within-game features only)
A = played[["uid", "app_id", "y", "pt_now", "playtime_2w", "last_played"]].copy()
A["g"] = A.groupby("app_id").pt_now.rank(pct=True)
A["log_2w"] = np.log1p(A.playtime_2w.fillna(0))
A["recent"] = (A.playtime_2w.fillna(0) > 0).astype(float)
A["share_2w"] = A.playtime_2w.fillna(0) / A.pt_now.clip(lower=1)
A["g_2w"] = A.groupby("app_id").playtime_2w.rank(pct=True)
A["last_age"] = np.log1p(((fetch_ts - A.last_played) / 86400).clip(lower=0))
A["holdout"] = A.app_id.map(hold)

# ---- library table: reviewers with a public library (adds resid, u_rank from their library)
t = ns["stage1_table"]("pt_now")[["uid", "app_id", "resid", "u_rank", "logit1"]]
B = A.merge(t, on=["uid", "app_id"])
B = B.sample(frac=1, random_state=0).drop_duplicates("uid")          # one review per reviewer
A.to_parquet(HERE / "cache" / "fresh_table.parquet")
B.to_parquet(HERE / "cache" / "fresh_table_lib.parquet")

HGB = dict(max_iter=200, learning_rate=0.05, max_leaf_nodes=7, min_samples_leaf=50, l2_regularization=1.0, random_state=0)


def cv(df, cols, folds=5):
    f = df.app_id.map(lambda a: int(hashlib.sha256(f"cv{a}".encode()).hexdigest(), 16) % folds).to_numpy()
    p = np.zeros(len(df))
    for k in range(folds):
        m = HistGradientBoostingClassifier(**HGB).fit(df[cols][f != k], df.y[f != k])
        p[f == k] = m.predict_proba(df[cols][f == k])[:, 1]
    return p


def report(df, cands, title, min_n):
    rows = []
    for name, s in cands.items():
        s = cv(df, s) if isinstance(s, list) else np.asarray(s, float)
        wg, ng = grouped_auc(df.y.to_numpy(), s, df.app_id.to_numpy(), min_n, 1)
        rows.append({"score": name, "pooled AUC": roc_auc_score(df.y, s), "within-game AUC": wg, "games": ng})
    return f"## {title} ({len(df):,} reviews, CV grouped by game)\n\n" + pd.DataFrame(rows).round(3).to_markdown(index=False)


dA, dB = A[~A.holdout], B[~B.holdout]
out = ["# Refit on fresh reviews - cross-validation (holdout games untouched)\n",
       report(dA, {"raw playtime now": dA.pt_now, "g (percentile in game)": dA.g,
                   "refit: g + recent play": ["g", "log_2w", "recent", "share_2w", "g_2w"]},
              "Every review, no library needed", 30),
       report(dB, {"raw playtime now": dB.pt_now, "g": dB.g, "frozen tuned stage 1": dB.logit1,
                   "refit stage 1 (g, resid, u_rank)": ["g", "resid", "u_rank"],
                   "refit stage 1, g + resid": ["g", "resid"],
                   "refit + recent play": ["g", "resid", "u_rank", "log_2w", "recent", "share_2w", "g_2w"]},
              "Reviewers with a public library", 5)]
(HERE / "fresh_refit_cv.md").write_text("\n\n".join(out) + "\n", encoding="utf-8")
print("\n\n".join(out))
