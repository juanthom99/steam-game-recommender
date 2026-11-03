"""D2 figures. Each figure's numbers are saved as a small table (eda/d2_tables/*.parquet) that the data note, the
Supabase load and the Streamlit dashboard reuse, so every view shows the same numbers.

F1 playtime is heavy-tailed, and Kaggle is capped and measured at review time
F2 2026 libraries are ~8x bigger than 2017 libraries (why the 2017-trained label adjustments failed)
F3 a few games take most of the play (popularity bias to beat)
F4 the label works: share of thumbs-up rises with the player's within-game playtime percentile
F5 coverage by release year: each source sees a different era of games (sampling concern)
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python eda/d2_figures.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

D = Path("C:/Users/juant/data_clean")
R = Path("C:/Users/juant/data_raw/steam_reviews")
HERE = Path(__file__).resolve().parent
FIG, TAB = HERE / "figures", HERE / "d2_tables"
FIG.mkdir(exist_ok=True); TAB.mkdir(exist_ok=True)
# Okabe-Ito: colorblind-safe, fixed order per source (color follows the source, never the rank)
COL = {"McAuley 2017": "#0072B2", "Steam 2026": "#D55E00", "Kaggle (to 2023)": "#009E73"}
INK, MUTED, GRID = "#1f2328", "#59636e", "#d8dee4"
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.titleweight": "semibold",
                     "axes.titlesize": 12, "legend.frameon": False, "figure.dpi": 150})
facts = {}


def save(fig, name, title, sub):
    fig.suptitle(title, x=0.01, ha="left", fontsize=13, fontweight="semibold", color=INK)
    fig.text(0.01, 0.905, sub, ha="left", fontsize=9.5, color=MUTED)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight"); plt.close(fig)


# ------------------------------------------------------------------ load
mc = pd.read_parquet(D / "interactions_mcauley.parquet", columns=["user_key", "app_id", "playtime_min", "played", "history_ok"])
mc = mc[mc.played & mc.history_ok]
kg = pd.read_parquet(D / "interactions_kaggle.parquet", columns=["user_key", "app_id", "playtime_min", "played", "history_ok", "bulk_user", "censored"])
kg = kg[kg.played & kg.history_ok & ~kg.bulk_user.fillna(False)]
cat = pd.read_parquet(D / "games.parquet", columns=["app_id", "history_ok", "release_date"])
bad = set(cat.app_id[~cat.history_ok.astype(bool)])
fr = pd.DataFrame([(r["uid"], a, pt) for r in map(json.loads, (R / "libraries.jsonl").open(encoding="utf-8")) if r["public"]
                   for a, pt, _, _ in r["games"] if pt > 0 and a not in bad], columns=["user_key", "app_id", "playtime_min"])
src = {"McAuley 2017": mc, "Steam 2026": fr, "Kaggle (to 2023)": kg}
print("loaded", {k: len(v) for k, v in src.items()}, flush=True)

# ------------------------------------------------------------------ F1 playtime distribution
bins = np.linspace(0, 6, 61)
rows = []
fig, ax = plt.subplots(figsize=(8, 4.2))
for name, d in src.items():
    h, _ = np.histogram(np.log10(d.playtime_min.clip(lower=1)), bins=bins)
    share = h / h.sum()
    rows += [{"source": name, "log10_minutes": round(b, 2), "share": s} for b, s in zip(bins[:-1], share)]
    ax.plot(bins[:-1] + 0.05, share * 100, color=COL[name], lw=2, label=f"{name} (median {d.playtime_min.median() / 60:.1f} h)")
    facts[f"median_hours_{name}"] = round(float(d.playtime_min.median() / 60), 1)
ticks = [1, 10, 60, 600, 6000, 60000, 600000]
ax.set_xticks(np.log10(ticks)); ax.set_xticklabels(["1 min", "10 min", "1 h", "10 h", "100 h", "1,000 h", "10,000 h"])
ax.set_ylabel("% of played (player, game) rows"); ax.legend(loc="upper left")
cap = kg.censored.mean() * 100
ax.annotate(f"Kaggle export cap at 1,000 h\n({kg.censored.sum():,} rows)", xy=(np.log10(60000), 0.4), xytext=(4.9, 3),
            fontsize=8.5, color=MUTED, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
save(fig, "f1_playtime", "Playtime spans five orders of magnitude",
     "Log scale. Raw hours can't be compared across games or players, so the label ranks each player within each game.")
pd.DataFrame(rows).to_parquet(TAB / "playtime_hist.parquet")

# ------------------------------------------------------------------ F2 library size
fig, ax = plt.subplots(figsize=(8, 4.2))
lb = np.logspace(0, 4, 41)
rows = []
for name in ("McAuley 2017", "Steam 2026"):
    n = src[name].groupby("user_key").size()
    h, _ = np.histogram(n, bins=lb)
    share = h / h.sum() * 100
    rows += [{"source": name, "games_from": float(a), "games_to": float(b), "share": s} for a, b, s in zip(lb[:-1], lb[1:], share)]
    ax.stairs(share, lb, color=COL[name], lw=2, label=f"{name}: median {n.median():.0f} played games ({len(n):,} players)")
    ax.axvline(n.median(), color=COL[name], lw=1, ls="--")
    facts[f"median_library_{name}"] = int(n.median())
ax.set_xscale("log"); ax.set_xlabel("Played games per player (log scale)"); ax.set_ylabel("% of players"); ax.legend(loc="upper left")
save(fig, "f2_library_size", "Today's players have played about 8x more games than in 2017",
     "Full Steam libraries, played games only. Models and labels tuned on 2017 libraries can misfire on 2026 players.")
pd.DataFrame(rows).to_parquet(TAB / "library_hist.parquet")

# ------------------------------------------------------------------ F3 popularity concentration
fig, ax = plt.subplots(figsize=(8, 4.2))
rows = []
for name, d in src.items():
    c = d.groupby("app_id").size().sort_values(ascending=False).to_numpy()
    x = np.arange(1, len(c) + 1) / len(c); y = np.cumsum(c) / c.sum()
    idx = np.unique(np.r_[np.linspace(0, len(c) - 1, 200).astype(int)])
    rows += [{"source": name, "share_of_games": float(x[i]), "share_of_plays": float(y[i])} for i in idx]
    top1 = y[max(int(len(c) * 0.01) - 1, 0)]
    facts[f"top1pct_share_{name}"] = round(float(top1) * 100, 1)
    ax.plot(x * 100, y * 100, color=COL[name], lw=2, label=f"{name}: top 1% of games = {top1:.0%} of plays")
ax.set_xscale("log"); ax.set_xlim(0.01, 100)
ax.set_xticks([0.01, 0.1, 1, 10, 100]); ax.set_xticklabels(["0.01%", "0.1%", "1%", "10%", "100%"])
ax.set_xlabel("Share of games, most played first (log scale)"); ax.set_ylabel("Cumulative % of played rows"); ax.legend(loc="upper left")
save(fig, "f3_popularity", "A small share of games gets most of the play",
     "Any model can score well by recommending hits; that's why MostPopular is a required baseline and long-tail recall is tracked.")
pd.DataFrame(rows).to_parquet(TAB / "popularity_curve.parquet")

# ------------------------------------------------------------------ F4 label validity
rev = pd.read_json(R / "reviews.jsonl", lines=True)
rev = rev[rev.rid.notna()].drop_duplicates("rid")
rev = rev[(rev.page == "all") & (rev.playtime_forever > 0)].copy()
rev["g"] = rev.groupby("app_id").playtime_forever.rank(pct=True)
kr = pd.read_parquet(D / "interactions_kaggle.parquet", columns=["app_id", "playtime_min", "played", "bulk_user", "review_recommend"])
kr = kr[kr.played & ~kr.bulk_user.fillna(False)].sample(3_000_000, random_state=0)
kr["g"] = kr.groupby("app_id").playtime_min.rank(pct=True)
fig, ax = plt.subplots(figsize=(8, 4.2))
rows = []
for name, d, y in (("Steam 2026", rev, "voted_up"), ("Kaggle (to 2023)", kr, "review_recommend")):
    dec = np.minimum((d.g * 10).astype(int), 9)
    pos = d.groupby(dec)[y].mean() * 100
    rows += [{"source": name, "decile": int(k) + 1, "pct_positive": float(v), "n": int((dec == k).sum())} for k, v in pos.items()]
    ax.plot(pos.index + 1, pos.values, color=COL[name], lw=2, marker="o", ms=5, label=f"{name} ({len(d):,} reviews)")
    facts[f"label_pos_bottom_top_{name}"] = [round(float(pos.iloc[0]), 1), round(float(pos.iloc[-1]), 1)]
ref = pd.read_json(R / "reviews.jsonl", lines=True)
ref = ref[ref.rid.notna()].drop_duplicates("rid")
ref = ref[ref.page == "all"]                       # unbiased page only (the negative page over-samples negatives)
facts["refund_positive_pct"] = round(float(ref[ref.refunded == True].voted_up.mean() * 100), 1)  # noqa: E712
facts["all_reviews_positive_pct"] = round(float(ref.voted_up.mean() * 100), 1)
ax.set_xticks(range(1, 11)); ax.set_xticklabels(["bottom\n10%"] + [str(i) for i in range(2, 10)] + ["top\n10%"])
ax.set_xlabel("Player's playtime rank among the same game's players (decile)"); ax.set_ylabel("% of reviews that are positive")
ax.legend(loc="lower right")
save(fig, "f4_label_validity", "Players who play a game longer than its other players mostly liked it",
     "Within-game playtime percentile vs the thumbs-up. Reviews validate the label; they are never used to train on.")
pd.DataFrame(rows).to_parquet(TAB / "label_curve.parquet")

# ------------------------------------------------------------------ F5 coverage by release year
yr = cat.set_index("app_id").release_date.dt.year
fig, ax = plt.subplots(figsize=(8, 4.2))
rows = []
for name, d in src.items():
    y = d.app_id.map(yr).dropna().astype(int)
    y = y[(y >= 2000) & (y <= 2026)]
    s = y.value_counts(normalize=True).sort_index() * 100
    rows += [{"source": name, "release_year": int(k), "pct_of_plays": float(v)} for k, v in s.items()]
    ax.plot(s.index, s.values, color=COL[name], lw=2, label=name)
ax.set_xlabel("Release year of the game"); ax.set_ylabel("% of played rows"); ax.legend(loc="upper left")
save(fig, "f5_release_year", "Each source sees a different era of games",
     "McAuley stops in 2017 and Kaggle in 2023; only the 2026 libraries cover recent releases, so they are reported as their own test slice.")
pd.DataFrame(rows).to_parquet(TAB / "release_year.parquet")

json.dump(facts, open(TAB / "facts.json", "w"), indent=2)
print(json.dumps(facts, indent=1))
