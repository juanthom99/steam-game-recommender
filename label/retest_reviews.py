"""Re-test the adopted enjoyment score on fresh Steam reviews (collected Oct 2026), fully independent of the pilot.

Test A - all reviews (no library needed): within-game AUC of playtime vs the thumbs-up, comparing playtime AT REVIEW
         (timing-matched) with playtime NOW (what the live app sees), plus refunds and play after the review.
Test B - reviewers with a public library: the 2-hour floor vs tuned stage 1 vs the two-stage score (with achievements).
         Stage-1 features come from build() on the reviewers' modern libraries; g for the reviewed game is the
         percentile among all of that game's reviewers. Models are the frozen ones from label/cache (no refitting).
         CIs: 1,000 bootstrap resamples of reviewers.
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python label/retest_reviews.py
Out: label/retest_reviews.md
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from achievements import ach_features_ext, EXT_FEATURES  # noqa: E402
from enjoy_score import build, grouped_auc  # noqa: E402

R = Path("C:/Users/juant/data_raw/steam_reviews")
rd = lambda n: [json.loads(l) for l in (R / n).open(encoding="utf-8")]

rev = pd.read_json(R / "reviews.jsonl", lines=True)
rev = rev[rev.rid.notna()].drop_duplicates("rid").copy()
n_all, n_ref_all = len(rev), int((rev.refunded == True).sum())  # noqa: E712
# Clean sample: only the "all recent reviews" page. The extra negative page reaches further back in time than the all
# page, so it makes negatives older on average and would leak review age into recency and playtime features.
rev = rev[rev.page == "all"].copy()
rev["y"] = rev.voted_up.astype(bool)
rev["pt_review"] = rev.playtime_at_review.fillna(rev.playtime_forever)
rev["pt_now"] = rev.playtime_forever
rev["post"] = (rev.pt_now - rev.pt_review).clip(lower=0)
rev["days_since"] = (rev.created.max() - rev.created) / 86400
out = [f"# Re-test on fresh Steam reviews\n\n{len(rev):,} reviews from the unbiased 'all recent reviews' page "
       f"(of {n_all:,} collected), {rev.app_id.nunique():,} games, {rev.y.mean():.0%} positive. The extra negative-review "
       "page is left out: it reaches further back in time, so it would leak review age into the features.\n"]

# ------------------------------------------------------------------ Test A: all reviews
def wg(score, d, min_n=30, min_c=5):
    v, n = grouped_auc(d.y.to_numpy(), np.asarray(score, float), d.app_id.to_numpy(), min_n, min_c)
    return v, n

played = rev[rev.pt_review > 0]
rows = []
tie = lambda s: 1e-6 * s       # break ties inside floor groups by playtime so AUC isn't flattered or penalised by ties
for name, s in [("playtime at review", played.pt_review),
                ("playtime now", played.pt_now),
                ("2-hour floor, at review", (played.pt_review >= 120) + 0.0),
                ("2-hour floor, now", (played.pt_now >= 120) + 0.0),
                ("play after review (log)", np.log1p(played.post)),
                ("share of play after review", played.post / played.pt_now.clip(lower=1)),
                ("still playing (last 2 weeks > 0)", (played.playtime_2w > 0) + tie(played.pt_now))]:
    v, n = wg(s, played)
    rows.append({"signal": name, "pooled AUC": roc_auc_score(played.y, s), "within-game AUC": v, "games": n})
out.append(f"## Test A - every review ({len(played):,} with playtime > 0)\n\nWithin-game AUC is the clean number "
           "(it removes game quality).\n\n" + pd.DataFrame(rows).round(3).to_markdown(index=False))
# reviews written soon after purchase vs. later: does post-review play matter more for recent reviews?
recent = played[played.days_since <= 180]
if len(recent) > 1000:
    out.append(f"\nReviews from the last 180 days only ({len(recent):,}): within-game AUC playtime at review "
               f"{wg(recent.pt_review, recent)[0]:.3f}, playtime now {wg(recent.pt_now, recent)[0]:.3f}.")
ref = rev[rev.refunded == True]  # noqa: E712
out.append(f"\n**Refunds:** {len(ref):,} refunded reviews on the all page ({n_ref_all:,} across both pages), {ref.y.mean():.0%} positive (all reviews: {rev.y.mean():.0%}). "
           f"Median playtime at review for refunded: {ref.pt_review.median():.0f} min.")
zero = (rev.pt_review == 0).mean()
out.append(f"\n{zero:.1%} of reviews have zero playtime at review (off-Steam keys, family share): excluded above.")

# ------------------------------------------------------------------ Test B: reviewers with public libraries
libs = {r["uid"]: r for r in rd("libraries.jsonl") if r["public"]}
gpct = {r["app_id"]: r["pct"] for r in rd("global_pct.jsonl")} if (R / "global_pct.jsonl").exists() else {}
ach = {(r["uid"], r["app_id"]): r for r in rd("achievements.jsonl")}
cat = pd.read_parquet("C:/Users/juant/data_clean/games.parquet", columns=["app_id", "history_ok"])
not_hist = set(cat.app_id[~cat.history_ok.astype(bool)])
target_keys = set(zip(rev.uid, rev.app_id))
L = pd.DataFrame([(u, a, pt) for u, r in libs.items() for a, pt, _, _ in r["games"]
                  if pt > 0 and a not in not_hist and (u, a) not in target_keys], columns=["user_key", "app_id", "playtime_min"])
lib_pt = {(u, a): pt for u, r in libs.items() for a, pt, _, _ in r["games"]}
print(f"library rows {len(L):,} from {len(libs):,} public libraries", flush=True)

s1 = pickle.load(open(HERE / "cache" / "stage1_best.pkl", "rb"))
two = pickle.load(open(HERE / "cache" / "enjoy_two_stage.pkl", "rb"))
S1 = s1["features"]


def stage1_table(col):
    T = played[["uid", "app_id", col]].rename(columns={"uid": "user_key", col: "playtime_min"})
    T["target"] = True
    df = build(pd.concat([L.assign(target=False), T], ignore_index=True))
    t = df[df.target].copy()
    t["g"] = t.groupby("app_id").playtime_min.rank(pct=True)       # among this game's reviewers only
    t = t[t.user_key.isin(libs)]
    p = np.clip(s1["model"].predict_proba(t[S1])[:, 1], 1e-4, 1 - 1e-4)
    t["logit1"] = np.log(p / (1 - p))
    return t.rename(columns={"user_key": "uid"})[["uid", "app_id", "playtime_min", "logit1"] + S1]


tA, tB = stage1_table("pt_review"), stage1_table("pt_now")
x = played[played.uid.isin(libs)][["uid", "app_id", "y", "pt_review", "pt_now", "refunded"]]
# one review per reviewer: 650 prolific reviewers wrote most of the library-linked reviews and would dominate the test
x = x.sample(frac=1, random_state=0).drop_duplicates("uid")
x = x.merge(tA[["uid", "app_id", "logit1"]].rename(columns={"logit1": "logit_review"}), on=["uid", "app_id"])
x = x.merge(tB[["uid", "app_id", "logit1"]], on=["uid", "app_id"])
feats = []
for u, a, ptn in zip(x.uid, x.app_id, x.pt_now):
    r = ach.get((u, a))
    f = ach_features_ext(r["ach"], gpct.get(a, {}), playtime_min=lib_pt.get((u, a), ptn), now_ts=libs[u]["fetched"]) \
        if r and r["success"] else None
    feats.append(f)
x["has_ach"] = [f is not None for f in feats]
for c in EXT_FEATURES:
    x[c] = [f[c] if f is not None else 0.0 for f in feats]
x["two_stage"] = two["stage2"].predict_proba(x[two["stage2_columns"]])[:, 1]
print(f"test B pairs {len(x):,}  with achievements {x.has_ach.sum():,}", flush=True)

scores = {"raw playtime (now)": x.pt_now,
          "raw playtime (at review)": x.pt_review,
          "2-hour floor (now), ties kept": (x.pt_now >= 120) + 0.0,
          "tuned stage 1 (at review)": x.logit_review,
          "tuned stage 1 (now)": x.logit1,
          "two-stage (now + achievements)": x.two_stage}
y = x.y.to_numpy()
base = scores["raw playtime (now)"].to_numpy()


def table(mask, label):
    rows, n = [], int(mask.sum())
    boots = [np.random.default_rng(i).integers(0, n, n) for i in range(1000)]       # resample reviewers
    for k, s in scores.items():
        s = np.asarray(s, float)[mask]; b = base[mask]; yy = y[mask]
        d = [roc_auc_score(yy[i], s[i]) - roc_auc_score(yy[i], b[i]) for i in boots] if k != "raw playtime (now)" else [0.0]
        rows.append({"score": k, "AUC": roc_auc_score(yy, s),
                     "vs raw playtime (now)": np.mean(d), "95% CI": f"{np.percentile(d, 2.5):+.3f} to {np.percentile(d, 97.5):+.3f}",
                     "game-stratified AUC": grouped_auc(yy, s, x.app_id.to_numpy()[mask], 2, 1)[0]})
    rows[0]["95% CI"] = "-"
    return f"\n### {label} ({mask.sum():,} reviewers)\n\n" + pd.DataFrame(rows).round(3).to_markdown(index=False)


out.append("\n## Test B - reviewers with a public library\n\nFrozen models, no refitting. The live app sees playtime "
           "**now**, so the 'now' rows are the production-relevant ones. Game-stratified AUC compares reviewers of the same "
           "game only (few reviewers per game, so it is noisy). One review per reviewer.")
out.append(table(np.ones(len(x), bool), "All"))
out.append(table(x.has_ach.to_numpy(), "With achievement data"))
(HERE / "retest_reviews.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
