"""Compare candidate "enjoyed" labels against Kaggle review flags (Layer 1 follow-up).

Run with the ML venv:
  C:/Users/juant/.venvs/steamrec-ml/Scripts/python label/test_labels.py
Writes label/label_tests.md. Same user split as validate_label.py: cutoffs chosen on calibration users,
all reported numbers come from report users.

Candidates
  C  current best percentile rule (g >= c, plus the 2 h floor except for short games)
  B  current best median-ratio rule (hours / game median >= r)
  D  two-sided: enjoyed if g >= hi (with floor rule), NOT enjoyed if g < lo or hours < 0.5,
     anything in between is "ambiguous" and left out of both training positives and negatives.
     Pre-declared selection rule (team choice): highest kappa among settings that label >= 70% of rows.
  E  DP2Rec-style per-user Beta mixture on g: two Beta components per user (EM, method of moments);
     enjoyed if P(high component) > t. Users with < 5 played games use one pooled mixture.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import betaln
from sklearn.metrics import cohen_kappa_score, roc_auc_score, average_precision_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from prep import FLOOR_H, load  # noqa: E402

MIN_COVERAGE = 0.70
L = []


def p(t=""):
    L.append(str(t))


def md(df):
    L.append(df.to_markdown())
    L.append("")


rec, notes = load()
calib = rec.calib.to_numpy()
rep = ~calib
y = rec.is_recommended.to_numpy()
g = rec.g.to_numpy()
hours = rec.hours.to_numpy()
short = rec.short_game.to_numpy()
floor_ok = np.where(short, True, hours >= FLOOR_H)


def metrics(pred, mask=None, score=None):
    m = rep if mask is None else rep & mask
    yt, pt = y[m], pred[m]
    tn = ((~yt) & (~pt)).sum(); fp = ((~yt) & pt).sum(); fn = (yt & ~pt).sum(); tp = (yt & pt).sum()
    sens, spec = tp / max(tp + fn, 1), tn / max(tn + fp, 1)
    out = {"kappa": cohen_kappa_score(yt, pt), "coverage (rows labeled)": m.sum() / rep.sum(),
           "enjoyed share": pt.mean(), "sensitivity": sens, "specificity": spec, "Youden J": sens + spec - 1,
           "precision of 'not enjoyed'": tn / max(tn + fn, 1)}
    if score is not None:
        out["ROC-AUC (score)"] = roc_auc_score(yt, score[m])
        out["PR-AUC not-rec (score)"] = average_precision_score(~yt, -score[m])
    return out


results = {}

# ---- C and B: current best single-threshold rules (re-tuned here so the table is self-contained)
kc = {c: cohen_kappa_score(y[calib], ((g >= c) & floor_ok)[calib]) for c in [0.05, 0.1, 0.15, 0.2]}
c_best = max(kc, key=kc.get)
results[f"C percentile ≥ {c_best}"] = metrics((g >= c_best) & floor_ok, score=g)
ratio = rec.ratio.to_numpy()
kb = {r: cohen_kappa_score(y[calib], (ratio >= r)[calib]) for r in [0.1, 0.15, 0.2, 0.3]}
r_best = max(kb, key=kb.get)
results[f"B ratio ≥ {r_best}"] = metrics(ratio >= r_best, score=ratio)

# ---- D: two-sided with an ambiguous middle band
grid = []
for lo in [0.05, 0.1, 0.15, 0.2, 0.3]:
    for hi in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7]:
        if hi <= lo:
            continue
        pos = (g >= hi) & floor_ok
        neg = (g < lo) | (hours < 0.5)
        lab = pos | neg
        cov = lab[calib].mean()
        k = cohen_kappa_score(y[calib & lab], pos[calib & lab])
        grid.append({"lo": lo, "hi": hi, "kappa (calib)": k, "coverage (calib)": cov})
gd = pd.DataFrame(grid)
ok = gd[gd["coverage (calib)"] >= MIN_COVERAGE]
best_d = ok.loc[ok["kappa (calib)"].idxmax()]
lo, hi = best_d.lo, best_d.hi
pos = (g >= hi) & floor_ok
lab = pos | (g < lo) | (hours < 0.5)
results[f"D two-sided (lo {lo}, hi {hi})"] = metrics(pos, mask=lab)

# ---- E: per-user Beta mixture (DP2Rec-style), vectorized EM across users
x = np.clip(g, 1e-3, 1 - 1e-3).astype("float64")
lx, l1x = np.log(x), np.log1p(-x)


def em(idx, n_groups, iters=30):
    """Two-component Beta mixture per group. Returns posterior P(high) per row and per-group params."""
    a = np.tile([2.0, 5.0], (n_groups, 1)); b = np.tile([5.0, 2.0], (n_groups, 1)); pi = np.full((n_groups, 2), 0.5)
    xi, lxi, l1xi = x[idx[1]], lx[idx[1]], l1x[idx[1]]
    gi = idx[0]
    for _ in range(iters):
        lp = np.stack([np.log(pi[gi, k]) + (a[gi, k] - 1) * lxi + (b[gi, k] - 1) * l1xi - betaln(a[gi, k], b[gi, k])
                       for k in (0, 1)], axis=1)
        lp -= lp.max(axis=1, keepdims=True)
        r = np.exp(lp); r /= r.sum(axis=1, keepdims=True)
        for k in (0, 1):
            w = np.bincount(gi, weights=r[:, k], minlength=n_groups) + 1e-6
            m = np.bincount(gi, weights=r[:, k] * xi, minlength=n_groups) / w
            v = np.bincount(gi, weights=r[:, k] * (xi - m[gi]) ** 2, minlength=n_groups) / w
            m = np.clip(m, 0.02, 0.98)
            v = np.maximum(v, 1e-4)
            common = np.clip(m * (1 - m) / v - 1, 1.0, 200.0)
            a[:, k], b[:, k] = m * common, (1 - m) * common
            pi[:, k] = w / np.bincount(gi, minlength=n_groups).clip(1)
        pi = np.clip(pi, 1e-3, 1)
        pi /= pi.sum(axis=1, keepdims=True)
    mean = a / (a + b)
    high = (mean[:, 1] >= mean[:, 0]).astype(int)          # which component is "high interest"
    post_high = np.where(high[gi] == 1, r[:, 1], r[:, 0])
    return post_high, mean


post = np.empty(len(rec))
big = (rec.n_user >= 5).to_numpy()
codes, _ = pd.factorize(rec.user_id[big])
rows_big = np.flatnonzero(big)
post[rows_big], user_means = em((codes, rows_big), codes.max() + 1)
rows_small = np.flatnonzero(~big)
post[rows_small], pooled_means = em((np.zeros(len(rows_small), dtype=int), rows_small), 1)
sep = np.abs(user_means[:, 1] - user_means[:, 0])
p(f"- Beta mixture fitted per user for {codes.max() + 1:,} users with ≥ 5 played games "
  f"({big.mean():.1%} of rows); pooled mixture for the rest (component means {np.round(pooled_means[0], 3).tolist()}).")
p(f"- Per-user component separation |mean_high − mean_low|: median {np.median(sep):.2f}, "
  f"share of users with separation < 0.1 (mixture barely splits): {(sep < 0.1).mean():.1%}")
ke = {t: cohen_kappa_score(y[calib], (post >= t)[calib]) for t in [0.1, 0.2, 0.3, 0.4, 0.5]}
t_best = max(ke, key=ke.get)
results["E Beta mixture, t = 0.5 (DP2Rec default)"] = metrics(post >= 0.5, score=post)
if t_best != 0.5:
    results[f"E Beta mixture, t = {t_best} (tuned)"] = metrics(post >= t_best, score=post)

# ---- E+floor: mixture combined with the 2 h refund floor
results[f"E + 2 h floor, t = {t_best}"] = metrics((post >= t_best) & floor_ok)

# ---- report
p("\n## Comparison on report users\n")
p("Kappa is the primary score; *coverage* below 100% means the label leaves ambiguous rows out "
  "(they are excluded from both training positives and evaluation negatives).\n")
md(pd.DataFrame(results).T.round(4))
p("## Two-sided grid (calibration users)\n")
p(f"Pre-declared selection rule: highest kappa with coverage ≥ {MIN_COVERAGE:.0%}.\n")
md(gd.pivot(index="lo", columns="hi", values="kappa (calib)").round(3))
md(gd.pivot(index="lo", columns="hi", values="coverage (calib)").round(3))
p("## Beta-mixture threshold (calibration users)\n")
md(pd.Series(ke, name="kappa (calib)").round(4).to_frame())

# Kappa by library size: does the label work for light users as well as heavy ones?
seg = pd.cut(rec.n_user, [0, 4, 20, 100, 10**6], labels=["1–4", "5–20", "21–100", "100+"])
seg_rows = []
cands = {"C": (g >= c_best) & floor_ok, "D": pos, "E": post >= t_best}
for s in seg.cat.categories:
    m = (seg == s).to_numpy()
    row = {"reviews per user": s, "rows (report)": int((m & rep).sum())}
    for name, pred in cands.items():
        mm = m & (lab if name == "D" else True)
        row[f"kappa {name}"] = cohen_kappa_score(y[rep & mm], pred[rep & mm]) if (rep & mm).sum() > 100 else np.nan
    seg_rows.append(row)
p("## Kappa by reviews per user (report users)\n")
md(pd.DataFrame(seg_rows).set_index("reviews per user").round(4))

(HERE / "label_tests.md").write_text("# Layer 1 follow-up: testing better labels\n\n" + "\n".join(L), encoding="utf-8")
print("\n".join(L))
