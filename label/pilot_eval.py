"""Pilot evaluation: do achievements / last-played / later playtime add signal beyond the adopted playtime score?

Baseline = the adopted player-relative model (g, resid, u_rank), trained on McAuley reviewers NOT in the pilot.
New signals (game-relative where possible, so they can't just encode game quality):
  ach_frac       share of the game's achievements the player unlocked
  ach_rel        ach_frac minus the average player's share (from global unlock percentages)  <- game-relative
  ach_depth      rarity-weighted unlocks: sum of -log(global %) over unlocked / over all achievements
  ach_span_days  days between first and last unlock (long engagement)
  growth         log playtime now (2026) minus log playtime at the 2017 crawl (kept playing?)
  recent         played in the last 365 days (rtime_last_played)
Caveat: the reviews are from ~2011-2017 and the new signals are measured in 2026.
Metrics: AUC on pilot pairs; combined models by 5-fold cross-validation grouped by user; bootstrap CI over users.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from enjoy_score import build, model, D  # noqa: E402

P = D / "pilot"
NOW = pd.Timestamp("2026-10-28").timestamp()
pairs = pd.read_parquet(P / "pairs.parquet")
lines = lambda f: [json.loads(l) for l in (P / f).open(encoding="utf-8")]

own = pd.DataFrame([{"uid": r["uid"], **g} for r in lines("owned.jsonl") for g in r["games"]])
pub = {r["uid"] for r in lines("owned.jsonl") if r["public"]}
gpct = {r["app_id"]: r["pct"] for r in lines("global_pct.jsonl")}
ach_rows = []
for r in lines("achievements.jsonl"):
    a = r["ach"]
    if not (r["success"] and a):
        ach_rows.append({"uid": r["uid"], "app_id": r["app_id"], "has_ach": False}); continue
    pct = gpct.get(r["app_id"], {})
    unl = [x for x in a if x["a"]]
    ts = [x["t"] for x in unl if x["t"] > 0]
    w = lambda x: -np.log(max(pct.get(x["n"], 50.0), 0.1) / 100)
    exp_frac = np.mean([pct.get(x["n"], np.nan) for x in a]) / 100 if pct else np.nan
    ach_rows.append({"uid": r["uid"], "app_id": r["app_id"], "has_ach": True, "ach_frac": len(unl) / len(a),
                     "ach_rel": len(unl) / len(a) - exp_frac,
                     "ach_depth": sum(w(x) for x in unl) / max(sum(w(x) for x in a), 1e-9),
                     "ach_span_days": (max(ts) - min(ts)) / 86400 if len(ts) >= 2 else 0.0})
ach = pd.DataFrame(ach_rows)

x = pairs[pairs.uid.isin(pub)].merge(own, on=["uid", "app_id"], how="left").merge(ach, on=["uid", "app_id"], how="left")
x["still_owned"] = x.playtime_now.notna()
x["growth"] = np.log1p(x.playtime_now.fillna(x.playtime_2017)) - np.log1p(x.playtime_2017)
x["recent"] = (x.last_played.fillna(0) > NOW - 365 * 86400).astype(int)
x["has_ach"] = x.has_ach.fillna(False).astype(bool)
for c in ("ach_frac", "ach_rel", "ach_depth", "ach_span_days"):
    x[c + "_miss"] = x[c].isna().astype(int)
    x[c] = x[c].fillna(0.0)
x["ach_span_log"] = np.log1p(x.ach_span_days)
x["y"] = x.review_recommend.astype(bool)

# baseline: adopted model trained on McAuley reviewers outside the pilot
m = pd.read_parquet(D / "interactions_mcauley.parquet", columns=["user_key", "app_id", "playtime_min", "played", "history_ok", "review_recommend"])
m = build(m[m.played & m.history_ok])
feats = ["g", "resid", "u_rank"]
tr = m[m.review_recommend.notna() & ~m.user_key.isin(pairs.user_key)]
base = model(feats, False).fit(tr[feats], tr.review_recommend.astype(bool))
x = x.merge(m[["user_key", "app_id"] + feats], on=["user_key", "app_id"], how="left")
x["base"] = base.predict_proba(x[feats])[:, 1]

summary = [f"- Pilot pairs: {len(pairs):,} ({pairs.uid.nunique():,} users). Public game details now: {len(pub):,} users, "
           f"{len(x):,} pairs. Still own the game: {x.still_owned.mean():.0%}. Game has achievements and data returned: {x.has_ach.mean():.0%}.",
           f"- Recommend share in pilot: {x.y.mean():.1%}."]
rows = []
for c in ["base", "ach_frac", "ach_rel", "ach_depth", "ach_span_log", "growth", "recent"]:
    sub = x if not c.startswith("ach") else x[x.has_ach]
    if sub.y.nunique() == 2:
        rows.append({"signal (alone)": c, "pairs": len(sub), "AUC": roc_auc_score(sub.y, sub[c])})

def fold_aucs(cols, data, reps=10):
    """AUC computed inside each held-out fold (no cross-fold calibration mixing), over repeated shuffled group splits."""
    out = []
    for rep in range(reps):
        rng_r = np.random.default_rng(rep)
        g = data.uid.map({u: rng_r.random() for u in data.uid.unique()})
        fold = (g.rank(method="dense").astype(int) % 5).to_numpy()
        for k in range(5):
            tr, te = fold != k, fold == k
            if data.y[te].nunique() < 2:
                continue
            clf = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=1000)).fit(data[cols][tr], data.y[tr])
            out.append(roc_auc_score(data.y[te], clf.predict_proba(data[cols][te])[:, 1]))
    return np.array(out)

new = ["ach_rel", "ach_depth", "ach_span_log", "ach_rel_miss", "growth", "recent"]
SETS = {"baseline score only": ["base"],
        "+ achievements": ["base", "ach_rel", "ach_depth", "ach_span_log", "ach_rel_miss"],
        "+ later playtime & last played": ["base", "growth", "recent"],
        "+ all new signals": ["base"] + new}
res = {k: fold_aucs(v, x) for k, v in SETS.items()}
d = res["+ all new signals"] - res["baseline score only"]          # paired: same folds
da = res["+ achievements"] - res["baseline score only"]
comb = pd.DataFrame([{"model (5-fold x 10 repeats, grouped by user)": k, "mean fold AUC": v.mean()} for k, v in res.items()])
summary.append(f"- Fold-paired AUC gain, all new signals: {d.mean():+.3f} (middle 95% of folds {np.percentile(d, 2.5):+.3f} to "
               f"{np.percentile(d, 97.5):+.3f}; better in {(d > 0).mean():.0%} of folds). Achievements only: {da.mean():+.3f} "
               f"(better in {(da > 0).mean():.0%} of folds).")
coef = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=1000)).fit(x[["base"] + new], x.y)[-1].coef_[0]
summary.append("- Standardized coefficients (full pilot): " + ", ".join(f"{c} {v:+.2f}" for c, v in zip(["base"] + new, coef)))
md = ("# Pilot: new engagement signals vs review flags\n\n" + "\n".join(summary) + "\n\n## Each signal alone\n\n"
      + pd.DataFrame(rows).round(3).to_markdown(index=False) + "\n\n## Combined with the adopted score\n\n"
      + comb.round(3).to_markdown(index=False) + "\n\nCaveat: reviews date from ~2011–2017; achievements, playtime and last-played are "
      "measured in Oct 2026, so these are long-run engagement signals, not what the player had done at review time.\n")
(HERE / "pilot_results.md").write_text(md, encoding="utf-8")
print(md)
