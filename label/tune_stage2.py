"""Tune stage 2 (achievements) on pilot players outside the locked holdout, on top of the chosen stage 1.
Candidates: logistic with the 3 base features (current), logistic with extended features, gradient boosting with
extended features. Selection by 5-fold CV grouped by player, repeated 5 times. The holdout is untouched here.
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python label/tune_stage2.py
"""
import json, pickle, sys
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from achievements import ach_features_ext, FEATURES, EXT_FEATURES  # noqa: E402
from enjoy_score import build, D  # noqa: E402

P = D / "pilot"
lines = lambda f: [json.loads(l) for l in (P / f).open(encoding="utf-8")]
NOW = pd.Timestamp("2026-10-30").timestamp()   # after the pilot fetch finished
pairs = pd.read_parquet(P / "pairs.parquet")
hold = set(json.load(open(P / "holdout_users.json"))["uids"])
pub = {r["uid"] for r in lines("owned.jsonl") if r["public"]}
now_pt = {(r["uid"], g["app_id"]): g["playtime_now"] for r in lines("owned.jsonl") for g in r["games"]}
gpct = {r["app_id"]: r["pct"] for r in lines("global_pct.jsonl")}
feat = {(r["uid"], r["app_id"]): (ach_features_ext(r["ach"], gpct.get(r["app_id"], {}), now_pt.get((r["uid"], r["app_id"])), NOW)
                                  if r["success"] else None) for r in lines("achievements.jsonl")}

s1 = pickle.load(open(HERE / "cache" / "stage1_best.pkl", "rb"))
m = pd.read_parquet(D / "interactions_mcauley.parquet", columns=["user_key", "app_id", "playtime_min", "played", "history_ok", "review_recommend"])
m = build(m[m.played & m.history_ok])
x = pairs[pairs.uid.isin(pub)].merge(m[["user_key", "app_id"] + s1["features"]], on=["user_key", "app_id"], how="left")
x["p1"] = s1["model"].predict_proba(x[s1["features"]])[:, 1]
x["logit1"] = np.log(np.clip(x.p1, 1e-4, 1 - 1e-4) / (1 - np.clip(x.p1, 1e-4, 1 - 1e-4)))
fl = [feat.get((u, int(a))) for u, a in zip(x.uid, x.app_id)]
x["has_ach"] = [f is not None for f in fl]
for k in EXT_FEATURES:
    x[k] = [f[k] if f is not None else 0.0 for f in fl]
x["y"] = x.review_recommend.astype(bool)
x["holdout"] = x.uid.isin(hold)
x.to_parquet(HERE / "cache" / "stage2_table.parquet", index=False)
dev = x[~x.holdout].reset_index(drop=True)
print(f"dev pairs {len(dev):,} (with achievements {dev.has_ach.sum():,}); holdout pairs {x.holdout.sum():,} (not used)", flush=True)

CANDS = {
    "stage 1 only": (["logit1"], lambda: LogisticRegression(max_iter=2000)),
    "logistic, 3 base features": (["logit1", "has_ach"] + FEATURES, lambda: make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))),
    "logistic, extended": (["logit1", "has_ach"] + EXT_FEATURES, lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=2000))),
    "boosting, extended (shallow)": (["logit1", "has_ach"] + EXT_FEATURES,
        lambda: HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=7, min_samples_leaf=50, l2_regularization=1.0, random_state=0)),
    "boosting, extended (deeper)": (["logit1", "has_ach"] + EXT_FEATURES,
        lambda: HistGradientBoostingClassifier(max_iter=300, learning_rate=0.03, max_leaf_nodes=15, min_samples_leaf=30, l2_regularization=1.0, random_state=0)),
}
res = {k: [] for k in CANDS}
users = dev.uid.unique()
for rep in range(5):
    rng = np.random.default_rng(rep); fold = dict(zip(users, rng.integers(0, 5, len(users)))); f = dev.uid.map(fold).to_numpy()
    for k in range(5):
        tr, te = f != k, f == k
        for name, (cols, mk) in CANDS.items():
            mdl = mk().fit(dev.loc[tr, cols], dev.y[tr])
            p = mdl.predict_proba(dev.loc[te, cols])[:, 1]
            res[name].append((roc_auc_score(dev.y[te], p), roc_auc_score(dev.y[te & dev.has_ach], p[dev.has_ach[te].to_numpy()])))
rows = []
base = np.array([a for a, _ in res["stage 1 only"]])
for name, v in res.items():
    a = np.array(v)
    rows.append({"candidate": name, "CV AUC (all)": a[:, 0].mean(), "CV AUC (with achievements)": a[:, 1].mean(),
                 "gain vs stage 1": (a[:, 0] - base).mean(), "folds better than stage 1": (a[:, 0] > base).mean()})
t = pd.DataFrame(rows).sort_values("CV AUC (all)", ascending=False)
(HERE / "stage2_tuning.md").write_text("# Stage 2 tuning\n\nPilot players outside the holdout; 5-fold x 5 repeats grouped by player. "
    f"Stage 1 = {s1['name']}.\n\n" + t.round(3).to_markdown(index=False) + "\n", encoding="utf-8")
print(t.round(3).to_string())
