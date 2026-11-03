"""One-time score on the locked 20% pilot holdout. Compares the 2-hour floor, the previous setup (untuned stage 1 +
3-feature logistic stage 2) and the tuned setup (tuned stage 1 + shallow boosted stage 2). Stage 2 models are fit on
non-holdout pilot players only. Bootstrap CIs resample holdout players."""
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
from achievements import FEATURES, EXT_FEATURES  # noqa: E402
from enjoy_score import build, model, D  # noqa: E402

x = pd.read_parquet(HERE / "cache" / "stage2_table.parquet")       # tuned stage 1 (logit1) + achievement features
pairs = pd.read_parquet(D / "pilot" / "pairs.parquet")
m = pd.read_parquet(D / "interactions_mcauley.parquet", columns=["user_key","app_id","playtime_min","played","history_ok","review_recommend"])
m = build(m[m.played & m.history_ok]); S1 = ["g", "resid", "u_rank"]
tr = m[m.review_recommend.notna() & ~m.user_key.isin(set(pairs.user_key))]
old1 = model(S1, False).fit(tr[S1], tr.review_recommend.astype(bool))           # previous (untuned) stage 1
x = x.merge(m[["user_key", "app_id"] + S1].rename(columns={c: c + "_m" for c in S1}), on=["user_key", "app_id"], how="left")
n0 = len(x); x = x[x[[c + "_m" for c in S1]].notna().all(axis=1)].copy()   # pairs whose app is no longer play history after re-cleaning
print(f"dropped {n0 - len(x)} pairs without stage-1 features (same rule for every score)")
x["playtime_min"] = x.playtime_2017
po = np.clip(old1.predict_proba(x[[c + "_m" for c in S1]].set_axis(S1, axis=1))[:, 1], 1e-4, 1 - 1e-4); x["logit_old"] = np.log(po / (1 - po))
dev, ho = x[~x.holdout], x[x.holdout]

old2 = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(dev[["logit_old", "has_ach"] + FEATURES], dev.y)
new_cols = ["logit1", "has_ach"] + EXT_FEATURES
new2 = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=7, min_samples_leaf=50,
                                      l2_regularization=1.0, random_state=0).fit(dev[new_cols], dev.y)
scores = {"2-hour floor": (ho.playtime_min >= 120).astype(float).to_numpy() + 1e-6 * ho.playtime_min.to_numpy(),
          "previous setup": old2.predict_proba(ho[["logit_old", "has_ach"] + FEATURES])[:, 1],
          "tuned stage 1 only": ho.logit1.to_numpy(),
          "tuned two-stage (new)": new2.predict_proba(ho[new_cols])[:, 1]}
y = ho.y.to_numpy(); users = ho.uid.unique(); idx = {u: np.where(ho.uid.to_numpy() == u)[0] for u in users}
rng = np.random.default_rng(0); boots = [np.concatenate([idx[u] for u in rng.choice(users, len(users))]) for _ in range(2000)]
rows = []
for k, s in scores.items():
    b = [roc_auc_score(y[i], s[i]) for i in boots if len(set(y[i])) == 2]
    d = [roc_auc_score(y[i], scores["tuned two-stage (new)"][i]) - roc_auc_score(y[i], s[i]) for i in boots if len(set(y[i])) == 2]
    rows.append({"score": k, "holdout AUC": roc_auc_score(y, s), "95% CI": f"{np.percentile(b, 2.5):.3f}–{np.percentile(b, 97.5):.3f}",
                 "new minus this (95% CI)": "—" if k.startswith("tuned two") else f"{np.mean(d):+.3f} ({np.percentile(d, 2.5):+.3f} to {np.percentile(d, 97.5):+.3f})"})
t = pd.DataFrame(rows)
hdr = f"# Holdout result (scored once, 2026-10-29)\n\n{len(ho):,} pairs from {len(users):,} held-out players; {ho.has_ach.mean():.0%} with achievements; {ho.y.mean():.1%} recommend.\n\n"
(HERE / "holdout_result.md").write_text(hdr + t.round(3).to_markdown(index=False) + "\n", encoding="utf-8")
pickle.dump({"stage1": pickle.load(open(HERE / "cache" / "stage1_best.pkl", "rb")), "stage2": new2, "stage2_columns": new_cols},
            open(HERE / "cache" / "enjoy_two_stage.pkl", "wb"))
print(hdr + t.round(3).to_string())
