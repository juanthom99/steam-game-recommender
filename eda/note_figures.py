"""Compact versions of Figures 1-5 sized for the 3-page D2 data note (same data as eda/d2_figures.py).

Reads eda/d2_tables/*.parquet and facts.json. Colors match the dashboard (Okabe-Ito, fixed per source).
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python eda/note_figures.py
Out: d2/final/figures/n1..n5_*.png
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
T = ROOT / "eda" / "d2_tables"
OUT = ROOT / "d2" / "final" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
C = {"McAuley 2017": "#0072B2", "Steam 2026": "#D55E00", "Kaggle (to 2023)": "#009E73"}
facts = json.load(open(T / "facts.json"))
plt.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "axes.titleweight": "bold", "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e6e6", "grid.linewidth": 0.5,
                     "legend.fontsize": 6, "legend.frameon": False, "font.family": "Segoe UI"})


def fig(w=3.35, h=2.0):
    f, ax = plt.subplots(figsize=(w, h), dpi=220)
    return f, ax


def save(f, name):
    f.tight_layout(pad=0.6)
    f.savefig(OUT / name)
    plt.close(f)


# 1. playtime
d = pd.read_parquet(T / "playtime_hist.parquet")
f, ax = fig()
for s, g in d.groupby("source", sort=False):
    g = g.assign(b=(np.floor(g.log10_minutes / 0.25 + 1e-9) * 0.25)).groupby("b").share.sum()
    ax.plot(10 ** (g.index + 0.125) / 60, g.values * 100, color=C[s], lw=1.3, label=s)
for s, ls in (("McAuley 2017", ":"), ("Kaggle (to 2023)", "--")):
    ax.axvline(facts[f"median_hours_{s}"], color=C[s], lw=0.8, ls=ls)
ax.set_xscale("log"); ax.set_xticks([1 / 60, 1 / 6, 1, 10, 100, 1000]); ax.set_xticklabels(["1m", "10m", "1h", "10h", "100h", "1000h"])
ax.set_ylim(0, 22); ax.set_ylabel("% of played rows"); ax.set_title("Fig 1. Playtime per (player, game)")
ax.text(facts["median_hours_Kaggle (to 2023)"] * 1.15, 21, f"Kaggle median {facts['median_hours_Kaggle (to 2023)']} h", fontsize=6, color=C["Kaggle (to 2023)"])
ax.text(facts["median_hours_McAuley 2017"] / 1.15, 21, f"full-library median {facts['median_hours_McAuley 2017']} h", fontsize=6, ha="right", color=C["McAuley 2017"])
ax.legend(loc="upper right", bbox_to_anchor=(1, 0.86))
save(f, "n1_playtime.png")

# 2. library size
d = pd.read_parquet(T / "library_hist.parquet")
f, ax = fig()
for s, g in d.groupby("source", sort=False):
    g = g.assign(b=np.floor(np.log10(g.games_from) / 0.2 + 1e-9) * 0.2).groupby("b").share.sum()
    ax.plot(10 ** (g.index + 0.1), g.values, color=C[s], lw=1.3, label=s)
    m = facts[f"median_library_{s}"]
    ax.axvline(m, color=C[s], lw=0.8, ls="--")
    ax.text(m * 1.1, 16.5, f"median {m}", fontsize=6, color=C[s])
ax.set_xscale("log"); ax.set_ylim(0, 18); ax.set_xlabel("played games per player"); ax.set_ylabel("% of players")
ax.set_title("Fig 2. Library size, 2017 vs 2026"); ax.legend(loc="center right")
save(f, "n2_library.png")

# 3. popularity
d = pd.read_parquet(T / "popularity_curve.parquet")
f, ax = fig()
for s, g in d.groupby("source", sort=False):
    g = g.sort_values("share_of_games")
    ax.plot(g.share_of_games * 100, g.share_of_plays * 100, color=C[s], lw=1.3, label=s)
    v = facts[f"top1pct_share_{s}"]
    ax.plot([1], [v], "o", color=C[s], ms=3); ax.text(0.8, v + 2, f"{v:.0f}%", fontsize=6, ha="right", color=C[s])
ax.axvline(1, color="#888", lw=0.7, ls="--")
ax.set_xscale("log"); ax.set_xlim(0.01, 100); ax.set_xticks([0.01, 0.1, 1, 10, 100]); ax.set_xticklabels(["0.01%", "0.1%", "1%", "10%", "100%"])
ax.set_xlabel("share of games, most played first"); ax.set_ylabel("% of plays (cumulative)")
ax.set_title("Fig 3. Popularity concentration"); ax.legend(loc="lower right")
save(f, "n3_popularity.png")

# 4. label validity
d = pd.read_parquet(T / "label_curve.parquet")
f, ax = fig()
for s, g in d.groupby("source", sort=False):
    ax.plot(g.decile, g.pct_positive, "o-", color=C[s], lw=1.3, ms=2.5, label=s)
ax.axhline(facts["refund_positive_pct"], color="#888", lw=0.7, ls="--")
ax.text(1, facts["refund_positive_pct"] + 2, f"refunded games: {facts['refund_positive_pct']:.1f}% positive", fontsize=6, ha="left", color="#555")
ax.set_ylim(20, 100); ax.set_xticks(range(1, 11)); ax.set_xlabel("playtime decile within the game (1 = bottom 10%)")
ax.set_ylabel("% of reviews positive"); ax.set_title("Fig 4. Label check: playtime vs thumbs-up"); ax.legend(loc="lower right", bbox_to_anchor=(1, 0.2))
save(f, "n4_label.png")

# 5. release year
d = pd.read_parquet(T / "release_year.parquet")
f, ax = fig()
for s, g in d.groupby("source", sort=False):
    ax.plot(g.release_year, g.pct_of_plays, color=C[s], lw=1.3, label=s)
for y, lab in ((2017, "McAuley crawl"), (2023, "Kaggle ends")):
    ax.axvline(y, color="#888", lw=0.7, ls="--"); ax.text(y - 0.3, 15.2, lab, fontsize=6, ha="right", color="#555")
ax.set_ylim(0, 16.5); ax.set_xlabel("game release year"); ax.set_ylabel("% of played rows")
ax.set_title("Fig 5. Release years each source covers"); ax.legend(loc="upper left")
save(f, "n5_release.png")
print("ok")
