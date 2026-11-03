"""Fit the two-stage enjoyment score on the 10k-pair pilot and save it.

Stage 1: the player-relative playtime model (g, resid, u_rank), trained on McAuley reviewers outside the pilot.
Stage 2: logistic model on [logit(stage 1), has_ach, ach_depth, ach_span_log, ach_rel], trained on pilot pairs.
Rows without achievement data fall back to a recalibrated stage-1 score.
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python label/fit_stage2.py
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from achievements import ach_features, stage2_matrix, STAGE2_COLUMNS  # noqa: E402
from enjoy_score import build, model, D  # noqa: E402

P = D / "pilot"
lines = lambda f: [json.loads(l) for l in (P / f).open(encoding="utf-8")]
pairs = pd.read_parquet(P / "pairs.parquet")
pub = {r["uid"] for r in lines("owned.jsonl") if r["public"]}
gpct = {r["app_id"]: r["pct"] for r in lines("global_pct.jsonl")}
feat = {(r["uid"], r["app_id"]): (ach_features(r["ach"], gpct.get(r["app_id"], {})) if r["success"] else None)
        for r in lines("achievements.jsonl")}

m = pd.read_parquet(D / "interactions_mcauley.parquet", columns=["user_key", "app_id", "playtime_min", "played", "history_ok", "review_recommend"])
m = build(m[m.played & m.history_ok])
S1 = ["g", "resid", "u_rank"]
tr = m[m.review_recommend.notna() & ~m.user_key.isin(pairs.user_key)]
stage1 = model(S1, False).fit(tr[S1], tr.review_recommend.astype(bool))

x = pairs[pairs.uid.isin(pub)].merge(m[["user_key", "app_id"] + S1], on=["user_key", "app_id"], how="left")
x["p1"] = stage1.predict_proba(x[S1])[:, 1]
fl = [feat.get((u, int(a))) for u, a in zip(x.uid, x.app_id)]
X, y = stage2_matrix(x.p1, fl), x.review_recommend.astype(bool).to_numpy()
has = X[:, 1] == 1

# cross-validated check (grouped by player), then refit on everything
users = x.uid.unique(); rng = np.random.default_rng(0); fold = dict(zip(users, rng.integers(0, 5, len(users))))
f = x.uid.map(fold).to_numpy(); p2 = np.zeros(len(x))
for k in range(5):
    clf = LogisticRegression(C=1.0, max_iter=2000).fit(X[f != k], y[f != k]); p2[f == k] = clf.predict_proba(X[f == k])[:, 1]
res = {"pairs": int(len(x)), "with_achievements": int(has.sum()),
       "auc_stage1_all": round(roc_auc_score(y, x.p1), 3), "auc_two_stage_all": round(roc_auc_score(y, p2), 3),
       "auc_stage1_with_ach": round(roc_auc_score(y[has], x.p1[has]), 3), "auc_two_stage_with_ach": round(roc_auc_score(y[has], p2[has]), 3)}
stage2 = LogisticRegression(C=1.0, max_iter=2000).fit(X, y)
res["stage2_coefficients"] = {c: round(float(v), 3) for c, v in zip(STAGE2_COLUMNS, stage2.coef_[0])}
res["stage2_intercept"] = round(float(stage2.intercept_[0]), 3)
(HERE / "cache").mkdir(exist_ok=True)
pickle.dump({"stage1": stage1, "stage1_features": S1, "stage2": stage2, "stage2_columns": STAGE2_COLUMNS},
            open(HERE / "cache" / "enjoy_two_stage.pkl", "wb"))
print(json.dumps(res, indent=2))
json.dump(res, open(HERE / "cache" / "enjoy_two_stage_fit.json", "w"), indent=2)
