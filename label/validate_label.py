"""Layer 1: build the playtime-only "enjoyed" label and validate it against Kaggle review flags.

Run with the ML venv:
  C:/Users/juant/.venvs/steamrec-ml/Scripts/python label/validate_label.py
Writes label/label_report.md, label/reliability.png, label/label_config.json (frozen cutoffs).

Reviews are used ONLY here, as a check. They never enter model training.
Users are split in half by user_id: cutoffs are chosen on the calibration half (max Cohen's kappa)
and every number in the report comes from the other half.
"""
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, cohen_kappa_score, confusion_matrix,
                             roc_auc_score)

HERE = Path(__file__).resolve().parent
L = []


def p(t=""):
    L.append(str(t))


def md(df):
    L.append(df.to_markdown())
    L.append("")


# ---------- load (shared prep, cached) ----------
import sys
sys.path.insert(0, str(HERE))
from prep import FLOOR_H, SHORT_GAME_H, MIN_PLAYERS, load  # noqa: E402
rec, notes = load()
for n in notes:
    p(f"- {n}")

calib = rec.calib.to_numpy()
y = rec.is_recommended.to_numpy()
p(f"- Calibration users' rows: {calib.sum():,}; report users' rows: {(~calib).sum():,}")
p(f"- Recommended share: {y.mean():.1%}  (why raw agreement is meaningless here)\n")


def rule(variant, c):
    if variant == "A_floor":
        return (rec.hours >= FLOOR_H).to_numpy()
    if variant == "B_ratio":
        return (rec.ratio >= c).to_numpy()
    # C: our rule — floor AND percentile, percentile alone for short games
    pct_ok = (rec.g >= c).to_numpy()
    return np.where(rec.short_game.to_numpy(), pct_ok, pct_ok & (rec.hours >= FLOOR_H).to_numpy())


grids = {"A_floor": [None], "B_ratio": [0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.8, 1.0, 1.5],
         "C_percentile": [0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]}
rows, chosen, curve = [], {}, []
for v, grid in grids.items():
    kap = {c: cohen_kappa_score(y[calib], rule(v, c)[calib]) for c in grid}
    curve += [{"variant": v, "cutoff": c, "kappa (calib)": k, "enjoyed share": rule(v, c)[calib].mean()} for c, k in kap.items()]
    best = max(kap, key=kap.get)
    chosen[v] = best
    pred = rule(v, best)[~calib]
    yt = y[~calib]
    tn, fp, fn, tp = confusion_matrix(yt, pred, labels=[False, True]).ravel()
    sens, spec = tp / (tp + fn), tn / (tn + fp)
    rows.append({"variant": v, "cutoff (chosen on calib)": best, "kappa": cohen_kappa_score(yt, pred),
                 "raw agreement": (pred == yt).mean(), "enjoyed share": pred.mean(),
                 "sensitivity": sens, "specificity": spec, "Youden J": sens + spec - 1,
                 "TP": tp, "FP": fp, "FN": fn, "TN": tn})
res = pd.DataFrame(rows).set_index("variant")

p("## Binary label vs review flag (report users only)\n")
md(res.round(4))
p("## Kappa at every cutoff tried (calibration users)\n")
p("Shows how far the framework's default (percentile 0.5) is from the kappa-best cutoff.\n")
md(pd.DataFrame(curve).set_index(["variant", "cutoff"]).round(4))

yt = y[~calib]
scores = {"raw hours": rec.hours, "median ratio": rec.ratio, "game percentile g": rec.g, "user percentile u": rec.u,
          "graded relevance (0/1/2)": pd.Series(np.select([(rec.g >= 0.8) & (rec.u >= 0.5), rec.g >= 0.5], [2, 1], 0))}
auc = []
for name, s in scores.items():
    s = s.to_numpy()[~calib]
    auc.append({"score": name, "ROC-AUC (recommended)": roc_auc_score(yt, s),
                "PR-AUC for NOT recommended (minority)": average_precision_score(~yt, -s),
                "PR-AUC baseline (prevalence)": (~yt).mean()})
p("## Graded scores (report users only)\n")
p("ROC-AUC for detecting *not recommended* equals the ROC-AUC above (same ranking, flipped), "
  "so the minority class is shown with PR-AUC, which does change and should be read against its prevalence baseline.\n")
md(pd.DataFrame(auc).set_index("score").round(4))

dec = pd.qcut(rec.g[~calib], 10, labels=False, duplicates="drop")
rel = pd.DataFrame({"decile of g": dec, "rec": yt}).groupby("decile of g").rec.agg(["mean", "size"])
rel.columns = ["share recommended", "rows"]
p("## Reliability: share recommended by decile of game percentile g\n")
md(rel.round(4))
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5, 3.2))
    ax.plot(rel.index + 1, rel["share recommended"], marker="o")
    ax.set_xlabel("Decile of per-game playtime percentile g")
    ax.set_ylabel("Share recommended")
    ax.set_title("Label reliability (report users)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(HERE / "reliability.png", dpi=150)
    p("![reliability](reliability.png)\n")
except ImportError:
    pass

grade = np.select([(rec.g >= 0.8) & (rec.u >= 0.5), rec.g >= 0.5], [2, 1], 0)
p("## Graded relevance distribution (all rows)\n")
md(pd.Series(grade).value_counts().sort_index().rename("rows").to_frame())

best_variant = res.kappa.idxmax()
p("## Decision\n")
p(f"- Highest kappa: **{best_variant}** (kappa {res.kappa.max():.3f}). The planned rule is C_percentile "
  f"(cutoff {chosen['C_percentile']}).")
p("- Limit: every Kaggle row is a reviewer, a self-selected and more engaged group, so this agreement is an upper bound for silent players.")
p("- These cutoffs are frozen in label_config.json before any model tuning.")

cfg = {"floor_hours": FLOOR_H, "short_game_median_hours": SHORT_GAME_H, "min_players_for_own_percentile": MIN_PLAYERS,
       "percentile_cutoff": chosen["C_percentile"], "ratio_cutoff": chosen["B_ratio"],
       "grade2_g": 0.8, "grade2_u": 0.5, "best_variant_by_kappa": best_variant}
(HERE / "label_config.json").write_text(json.dumps(cfg, indent=2))
(HERE / "label_report.md").write_text("# Layer 1: playtime 'enjoyed' label vs Kaggle reviews\n\n" + "\n".join(L), encoding="utf-8")
print("\n".join(L))
