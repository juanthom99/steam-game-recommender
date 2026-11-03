"""Generate and execute the deep-EDA notebook (eda/steam_eda.ipynb) from the cleaned tables.

Run with the ML venv:
  C:/Users/juant/.venvs/steamrec-ml/Scripts/python eda/build_notebook.py
Every chart: question (markdown) -> chart -> computed "what we see" -> "what it means for the recommender".
Figures are also saved to eda/figures/ for the shareable report.
"""
from pathlib import Path

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

HERE = Path(__file__).resolve().parent
cells = []


def md(s):
    cells.append(nbf.v4.new_markdown_cell(s.strip()))


def code(s):
    cells.append(nbf.v4.new_code_cell(s.strip()))


md("""
# Steam Recommender: Exploratory Data Analysis

**Goal of the product:** anyone with a Steam account gets (1) highly accurate *For you* picks and
(2) *Try something new* picks: games outside their usual taste that the model still predicts they'll enjoy.

**Goal of this notebook:** understand every data source *after cleaning*, and turn each finding into a concrete
modeling decision. Each section follows the same pattern: **question → chart → what we see → what it means.**

| Source | What it is | Role |
|---|---|---|
| Kaggle *Game Recommendations on Steam* | 41M reviews with hours played; 50,872 games with tags and descriptions | Training rows, catalog, text for search |
| McAuley *Australian Steam* (Wan & McAuley 2018) | 88k users' **full** libraries with playtime, including never-played games | Primary training/evaluation (matches live input) |
| Steam Web API | Live store pages, the full app catalog, a user's owned games | Live input, catalog refresh, item types |
| IsThereAnyDeal | Current prices and all-time lows | Price band, value per dollar, buy-now-or-wait |

Cleaning rules and their row counts are in `clean/cleaning_report.md`.
""")

code(r'''
import json, os, warnings
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from IPython.display import Markdown, display
warnings.filterwarnings("ignore")

CLEAN = Path(os.path.expanduser("~/data_clean"))
ROOT = Path.cwd().parent if Path.cwd().name == "eda" else Path.cwd()
FIG = ROOT / "eda" / "figures"; FIG.mkdir(parents=True, exist_ok=True)

# Validated reference palette (dataviz skill): fixed categorical order, one-hue sequential, text inks.
C = {"blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "yellow": "#eda100", "magenta": "#e87ba4"}
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "figure.dpi": 110,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "font.size": 10, "axes.titlesize": 12.5, "axes.titleweight": "bold", "axes.titlecolor": INK,
    "axes.titlelocation": "left", "legend.frameon": False, "lines.linewidth": 2})

def finish(fig, ax, title, subtitle, name, source="Source: cleaned data, see clean/cleaning_report.md"):
    ax.set_title(title, pad=22)
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=INK2, fontsize=9.5, va="bottom")
    fig.text(0.01, 0.005, source, color=INK2, fontsize=7.5)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(FIG / f"{name}.png", dpi=160, bbox_inches="tight"); plt.show()

def say(s): display(Markdown(s))
pct = lambda x: f"{x:.1%}"
''')

code(r'''
games = pd.read_parquet(CLEAN / "games.parquet")
extra = pd.read_parquet(CLEAN / "steam_catalog_extra.parquet")
kag = pd.read_parquet(CLEAN / "interactions_kaggle.parquet", columns=["user_key","app_id","playtime_min","played","censored","is_game","review_recommend","review_date"])
mc = pd.read_parquet(CLEAN / "interactions_mcauley.parquet", columns=["user_key","app_id","playtime_min","playtime_2w_min","played","is_game","review_recommend"])
say(f"Loaded **{len(games):,}** catalog games, **{len(kag):,}** Kaggle interactions "
    f"({kag.user_key.nunique():,} users) and **{len(mc):,}** McAuley owned-game rows ({mc.user_key.nunique():,} users).")
''')

# ---------------------------------------------------------------- 1 catalog coverage
md("""
## 1. How much of Steam does our data cover?
**Question:** if a user owns a game, how likely is it that our catalog knows it?
""")
code(r'''
steam_games = (games.item_type == "game").sum() + len(extra)
bars = pd.Series({
    "All games on Steam today": steam_games,
    "Kaggle catalog (games only)": (games.item_type == "game").sum(),
    "Games with ≥ 1 Kaggle review": kag[kag.is_game].app_id.nunique(),
    "Games owned in McAuley libraries": mc[mc.is_game].app_id.nunique(),
})
fig, ax = plt.subplots(figsize=(8, 3.4))
y = np.arange(len(bars))[::-1]
ax.barh(y, bars.values, color=[C["blue"]] + [SEQ[3]] * 3, height=0.6)
ax.set_yticks(y, bars.index); ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v/1000:.0f}k"))
for yi, v in zip(y, bars.values): ax.text(v, yi, f"  {v:,}", va="center", color=INK, fontsize=9)
ax.grid(axis="y", visible=False); ax.set_xlim(0, bars.max() * 1.18)
finish(fig, ax, "Kaggle knows about 1 in 5 Steam games", "Number of distinct games, Steam app catalog (Oct 2026) vs our datasets", "01_catalog_coverage")
say(f"**What we see:** Steam lists **{steam_games:,}** games; Kaggle's catalog covers **{pct(bars.iloc[1]/steam_games)}** of them "
    f"and only **{bars.iloc[2]:,}** have any review signal.")
''')
md("""
**What it means:** a collaborative model trained on Kaggle cannot score most of Steam. The content side
(text embeddings of title, tags, description) and the weekly **catalog refresh** are required, not optional,
for a product that serves *anyone* with a Steam account.
""")

# ---------------------------------------------------------------- 2 item types
md("""
## 2. Are all the "games" actually games?
**Question:** how many catalog items are DLC, soundtracks or software, which we shouldn't recommend as games?
""")
code(r'''
t = games.item_type.fillna("delisted").value_counts()
fig, ax = plt.subplots(figsize=(7.5, 2.8))
y = np.arange(len(t))[::-1]
ax.barh(y, t.values, color=[C["blue"] if i == "game" else SEQ[2] for i in t.index], height=0.6)
ax.set_yticks(y, t.index)
for yi, v in zip(y, t.values): ax.text(v, yi, f"  {v:,} ({v/len(games):.0%})", va="center", fontsize=9)
ax.grid(axis="y", visible=False); ax.set_xlim(0, t.max() * 1.25)
finish(fig, ax, "1 in 6 Kaggle 'games' is DLC", "Kaggle catalog items by Steam's own app type", "02_item_types")
say(f"**What we see:** **{t.get('dlc', 0):,}** DLC, **{t.get('software', 0):,}** software, and **{t.get('delisted', 0):,}** items "
    "that no longer exist on Steam.")
''')
md("""
**What it means:** DLC playtime is still a taste signal, so keep it for **training**. But filter recommendations
to `item_type = game` and not delisted. The Steam catalog gives this label for free, which replaces a ~7-hour
IsThereAnyDeal backfill.
""")

# ---------------------------------------------------------------- 3 releases per year
md("## 3. When were these games released?")
code(r'''
yr = games[games.item_type == "game"].release_date.dt.year.value_counts().sort_index()
yr = yr[yr.index >= 2006]
fig, ax = plt.subplots(figsize=(8, 3.2))
ax.bar(yr.index, yr.values, color=C["blue"], width=0.75)
ax.set_xlabel("Release year"); ax.grid(axis="x", visible=False)
last = yr.index.max()
ax.annotate("partial year\n(snapshot Oct 2023)", (last, yr[last]), xytext=(last - 4.5, yr.max() * 0.9),
            color=INK2, fontsize=8.5, arrowprops=dict(arrowstyle="-", color=INK2))
finish(fig, ax, "Steam releases grew ~10x in a decade", "Games in the Kaggle catalog by release year", "03_releases_by_year")
say(f"**What we see:** {yr.loc[2014]:,} games from 2014 vs {yr.loc[2022]:,} from 2022. Kaggle stops in {last}.")
''')
md("""
**What it means:** the newest games, often what users ask about, are missing. New releases have no
interaction history even after the refresh, so they rely on the content side until players appear.
""")

# ---------------------------------------------------------------- 4 tags
md("""
## 4. What does the tag vocabulary look like?
**Question:** are tags rich enough to describe taste and to measure "outside your comfort zone"?
""")
code(r'''
tags = games.tags.explode().dropna()
tc = tags.value_counts()
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.2), gridspec_kw={"width_ratios": [1.3, 1]})
top = tc.head(20)[::-1]
a1.barh(top.index, top.values, color=C["blue"], height=0.65); a1.grid(axis="y", visible=False)
a1.set_title("Top 20 tags (games using each)", fontsize=10.5, loc="left")
cum = tc.cumsum() / tc.sum()
a2.plot(np.arange(1, len(cum) + 1), cum.values, color=C["blue"])
for k in (20, 100):
    a2.scatter([k], [cum.iloc[k-1]], color=C["orange"], s=36, zorder=3)
    a2.annotate(f"top {k}: {cum.iloc[k-1]:.0%}", (k, cum.iloc[k-1]), xytext=(8, -14), textcoords="offset points", fontsize=8.5)
a2.set_xscale("log"); a2.yaxis.set_major_formatter(mtick.PercentFormatter(1)); a2.set_xlabel("Number of tags (log)")
a2.set_title("Cumulative share of all tag uses", fontsize=10.5, loc="left")
fig.suptitle(f"{len(tc)} tags, but a few dominate", x=0.01, ha="left", fontweight="bold", color=INK)
fig.tight_layout(); fig.savefig(FIG / "04_tags.png", dpi=160, bbox_inches="tight"); plt.show()
say(f"**What we see:** the median game has **{games.n_tags.median():.0f}** tags. 'Indie' alone is on **{pct(tc.iloc[0]/len(games))}** of games. "
    f"The top 20 tags account for **{pct(cum.iloc[19])}** of all uses.")
''')
md("""
**What it means:** generic tags like *Indie* and *Singleplayer* say little about taste. For the tag-distance
("exploration") metric and the surprise row, **down-weight tags by how common they are** (TF-IDF style).
Otherwise every indie game looks "familiar" to every user.
""")

# ---------------------------------------------------------------- 5 price
md("## 5. What do games cost?")
code(r'''
pr = games.loc[games.item_type == "game", "kaggle_price_regular"]
free = (pr == 0).mean()
paid = pr[pr > 0].clip(upper=80)
fig, ax = plt.subplots(figsize=(8, 3.2))
ax.hist(paid, bins=np.arange(0, 82, 2.5), color=C["blue"], rwidth=0.88)
for v in (4.99, 9.99, 19.99, 29.99, 59.99):
    ax.axvline(v, color=INK2, lw=0.8, ls=":")
ax.set_xlabel("Regular price, USD (capped at $80)"); ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("${x:.0f}"))
finish(fig, ax, "Prices cluster at the usual price points", f"Paid games only; {free:.0%} of games are free (not shown)", "05_prices")
say(f"**What we see:** median paid price **${pr[pr>0].median():.2f}**, 90th percentile **${pr[pr>0].quantile(.9):.2f}**. "
    f"**{pct(games.price_original_was_missing.mean())}** of games had a miscoded original price that we repaired.")
''')
md("""
**What it means:** price bands are coarse and step-like, so the user's "comfort band" should be computed from
price **tiers**, not exact dollars. Kaggle prices are from 2023; the live app must use Steam/IsThereAnyDeal prices.
""")

# ---------------------------------------------------------------- 6 playtime distributions
md("""
## 6. How long do people play? Reviewers vs full libraries
**Question:** does Kaggle's reviewer playtime look like what a live user brings (their whole library)?
""")
code(r'''
kh = kag.loc[kag.played, "playtime_min"] / 60
mh = mc.loc[mc.played, "playtime_min"] / 60
bins = np.logspace(-1.3, 4.3, 60)
fig, ax = plt.subplots(figsize=(8.5, 3.6))
ax.hist(kh, bins=bins, density=True, histtype="step", lw=2, color=C["blue"], label="Kaggle (games people reviewed)")
ax.hist(mh, bins=bins, density=True, histtype="step", lw=2, color=C["orange"], label="McAuley (every owned game played)")
ax.axvline(2, color=INK2, ls="--", lw=1); ax.text(2.15, ax.get_ylim()[1]*0.9, "2 h refund window", color=INK2, fontsize=8.5)
ax.set_xscale("log"); ax.set_xlabel("Hours played (log scale)"); ax.set_ylabel("Density")
ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:g}"))
ax.legend(loc="upper left")
finish(fig, ax, "Reviewers play far longer than the average owner", "Playtime of played games (playtime > 0)", "06_playtime_kaggle_vs_mcauley")
say(f"**What we see:** median playtime is **{kh.median():.1f} h** for reviewed games vs **{mh.median():.1f} h** across full libraries. "
    f"**{pct((kh<2).mean())}** of reviewed games were played under 2 h vs **{pct((mh<2).mean())}** of owned games. "
    f"In McAuley, **{pct((~mc.played).mean())}** of owned games were **never launched**.")
''')
md("""
**What it means:** Kaggle over-represents engaged play, which is the selection bias the evaluation framework warns about.
Thresholds tuned on Kaggle won't transfer to live users, so **train and evaluate on McAuley-style full libraries**
and use Kaggle as extra training rows. Never-played games are *unknown*, not dislikes.
""")

# ---------------------------------------------------------------- 7 per-genre playtime
md("""
## 7. Why playtime must be normalized per game
**Question:** is "10 hours" a lot? It depends entirely on the game.
""")
code(r'''
gt = games.set_index("app_id").tags.apply(lambda t: t[0] if len(t) else None)
gm = mc[mc.played].assign(tag=lambda d: d.app_id.map(gt)).dropna(subset=["tag"])
top_tags = gm.tag.value_counts().head(14).index
med = gm[gm.tag.isin(top_tags)].groupby("tag").playtime_min.median().div(60).sort_values()
fig, ax = plt.subplots(figsize=(8, 4))
ax.barh(med.index, med.values, color=C["blue"], height=0.6); ax.grid(axis="y", visible=False)
for i, v in enumerate(med.values): ax.text(v, i, f"  {v:.1f} h", va="center", fontsize=8.5)
ax.set_xlabel("Median hours played (McAuley, played games)"); ax.set_xlim(0, med.max() * 1.2)
finish(fig, ax, "Typical playtime varies widely by genre", "Median playtime by a game's primary tag", "07_playtime_by_genre")
say(f"**What we see:** median playtime ranges from **{med.min():.1f} h** ({med.idxmin()}) to **{med.max():.1f} h** ({med.idxmax()}).")
''')
md("""
**What it means:** a raw-hours threshold would label every short game "disliked" and every long game "loved".
This is why the label uses each game's **own** playtime percentile (Layer 1), and why the model's confidence weight
divides by the game's median: `c = 1 + α·log(1 + playtime / median_game)`.
""")

# ---------------------------------------------------------------- 8 popularity concentration
md("""
## 8. Popularity concentration (the popularity-bias risk)
**Question:** how unequal is attention across games? This decides how easily a model can "win" by recommending hits.
""")
code(r'''
def lorenz(counts):
    c = np.sort(counts.values)[::-1]; cs = np.cumsum(c) / c.sum()
    x = np.arange(1, len(c) + 1) / len(c); return x, cs
def gini(counts):
    c = np.sort(counts.values); n = len(c); return (2 * np.sum(np.arange(1, n+1) * c) / (n * c.sum())) - (n + 1) / n
kc = kag[kag.is_game & kag.played].groupby("app_id").size(); mcn = mc[mc.is_game & mc.played].groupby("app_id").size()
fig, ax = plt.subplots(figsize=(6.8, 4.4))
for cnt, col, lab in ((kc, C["blue"], "Kaggle"), (mcn, C["orange"], "McAuley")):
    x, cs = lorenz(cnt); ax.plot(x, cs, color=col, label=f"{lab} (Gini {gini(cnt):.2f})")
ax.plot([0, 1], [0, 1], color=INK2, lw=1, ls=":")
for cnt, col in ((kc, C["blue"]), (mcn, C["orange"])):
    x, cs = lorenz(cnt); i = int(0.01 * len(x)); ax.scatter([x[i]], [cs[i]], color=col, s=40, zorder=3)
    ax.annotate(f"top 1% → {cs[i]:.0%}", (x[i], cs[i]), xytext=(10, -4), textcoords="offset points", fontsize=8.5, color=INK)
ax.xaxis.set_major_formatter(mtick.PercentFormatter(1)); ax.yaxis.set_major_formatter(mtick.PercentFormatter(1))
ax.set_xlabel("Share of games, most played first"); ax.set_ylabel("Share of all play interactions"); ax.legend(loc="lower right")
finish(fig, ax, "A tiny share of games gets most of the play", "Cumulative share of interactions by game (Lorenz curve)", "08_popularity_lorenz")
say(f"**What we see:** the top 1% of games get **{pct(lorenz(kc)[1][int(.01*len(kc))])}** of Kaggle interactions and "
    f"**{pct(lorenz(mcn)[1][int(.01*len(mcn))])}** of McAuley's. The Gini coefficients are {gini(kc):.2f} and {gini(mcn):.2f} (1 = all play on one game).")
''')
md("""
**What it means:** a "most popular" list will look strong on accuracy metrics. The evaluation must report
**popularity bias** (ARP, long-tail share, long-tail recall) next to NDCG, and the hybrid must beat a *tuned*
MostPopular baseline per user segment. This chart is also why the *Try something new* row exists.
""")

# ---------------------------------------------------------------- 9 user activity / cold start
md("""
## 9. How much history does each user have? (cold start)
**Question:** how many users have too little history for a collaborative model?
""")
code(r'''
ku = kag[kag.played].groupby("user_key").size(); mu = mc[mc.played].groupby("user_key").size()
edges = [0, 1, 4, 20, 100, 10**6]; labels = ["1", "2–4", "5–20", "21–100", "100+"]
kb = pd.cut(ku, edges, labels=labels).value_counts(normalize=True).reindex(labels)
mb = pd.cut(mu, edges, labels=labels).value_counts(normalize=True).reindex(labels)
x = np.arange(len(labels)); w = 0.38
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.bar(x - w/2 - 0.01, kb.values, w, color=C["blue"], label="Kaggle (reviews per user)")
ax.bar(x + w/2 + 0.01, mb.values, w, color=C["orange"], label="McAuley (played games per user)")
ax.set_xticks(x, labels); ax.set_xlabel("Games per user"); ax.yaxis.set_major_formatter(mtick.PercentFormatter(1))
ax.grid(axis="x", visible=False); ax.legend()
finish(fig, ax, "Most Kaggle users have one review; McAuley users have libraries", "Share of users by number of played games", "09_user_history")
say(f"**What we see:** **{pct(kb['1'])}** of Kaggle users have a single review, but the median McAuley user has played "
    f"**{mu.median():.0f}** games (they own a median of **{mc.groupby('user_key').size().median():.0f}**).")
''')
md("""
**What it means:** Kaggle's user side is mostly cold start, so its users teach the model little about individuals.
That's another reason McAuley-style libraries are the primary training and evaluation data. Live users bring whole
libraries too, so they look like McAuley users, not Kaggle users. Light users (1–4 games) still exist, and the hybrid
leans on content for them; the evaluation reports that segment separately.
""")

# ---------------------------------------------------------------- 10 sparsity thresholds
md("""
## 10. How strict can the training filters be?
**Question:** if we keep only users with ≥ *k* played games and games with ≥ *m* players, how much data survives?
""")
code(r'''
rows = []
for k in (1, 3, 5, 10, 20):
    for m in (1, 5, 10, 20, 50):
        d = mc[mc.played & mc.is_game]
        d = d[d.app_id.map(d.app_id.value_counts()) >= m]
        d = d[d.user_key.map(d.user_key.value_counts()) >= k]
        rows.append({"min games per user (k)": k, "min players per game (m)": m, "users": d.user_key.nunique(),
                     "games": d.app_id.nunique(), "interactions": len(d)})
grid = pd.DataFrame(rows)
piv = grid.pivot(index="min games per user (k)", columns="min players per game (m)", values="users")
fig, ax = plt.subplots(figsize=(7, 3.6))
im = ax.imshow(piv.values / piv.values.max(), cmap=plt.matplotlib.colors.LinearSegmentedColormap.from_list("seq", SEQ), aspect="auto", vmin=0, vmax=1)
ax.set_xticks(range(piv.shape[1]), piv.columns); ax.set_yticks(range(piv.shape[0]), piv.index)
ax.set_xlabel("Minimum players per game (m)"); ax.set_ylabel("Minimum games per user (k)"); ax.grid(False)
for i in range(piv.shape[0]):
    for j in range(piv.shape[1]):
        v = piv.values[i, j]; ax.text(j, i, f"{v/1000:.1f}k", ha="center", va="center", fontsize=8.5,
                                       color="white" if v / piv.values.max() > 0.55 else INK)
finish(fig, ax, "Filters barely shrink McAuley's user base", "McAuley users kept under each filter (one pass, games only)", "10_filter_grid")
pick = grid[(grid["min games per user (k)"] == 5) & (grid["min players per game (m)"] == 10)].iloc[0]
say(f"**What we see:** with k = 5 and m = 10, we keep **{pick.users:,}** users, **{pick.games:,}** games and **{pick.interactions:,}** interactions.")
''')
md("""
**What it means:** the framework's "users with ≥ 5 positives" filter is affordable on McAuley. Games below the
player threshold are not lost: they're scored by the content side.
""")

# ---------------------------------------------------------------- 11 temporal
md("## 11. How has reviewing changed over time? (Kaggle)")
code(r'''
monthly = kag.set_index("review_date").resample("MS").size()
monthly = monthly[monthly.index >= "2012-01-01"]
fig, ax = plt.subplots(figsize=(8.5, 3.2))
ax.fill_between(monthly.index, monthly.values, color=SEQ[1]); ax.plot(monthly.index, monthly.values, color=C["blue"], lw=1.6)
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v/1e6:.1f}M" if v >= 1e6 else f"{v/1e3:.0f}k"))
peak = monthly.idxmax(); ax.annotate(f"peak {peak:%b %Y}", (peak, monthly.max()), xytext=(-110, -8), textcoords="offset points", fontsize=8.5)
finish(fig, ax, "Review volume exploded after 2019", "Kaggle reviews per month", "11a_reviews_per_month")
share = kag.groupby(kag.review_date.dt.year).review_recommend.mean()
share = share[share.index >= 2011]
fig, ax = plt.subplots(figsize=(8.5, 3.0))
ax.plot(share.index, share.values, color=C["blue"], marker="o", ms=5)
ax.yaxis.set_major_formatter(mtick.PercentFormatter(1)); ax.set_ylim(0.75, 1.0)
finish(fig, ax, "Reviews became more critical, then recovered", "Share of Kaggle reviews that recommend the game, by year", "11b_recommend_share_by_year")
say(f"**What we see:** the share of positive reviews fell from **{pct(share.iloc[0])}** ({share.index[0]}) to a low of "
    f"**{pct(share.min())}** ({share.idxmin()}), and was **{pct(share.iloc[-1])}** in {share.index[-1]}.")
''')
md("""
**What it means:** 86% of reviews are positive, so raw agreement with reviews is meaningless and Cohen's kappa is
needed. The positive share also drifts by year, so label validation should be checked by year (a follow-up).
""")

# ---------------------------------------------------------------- 12 label reliability
md("""
## 12. Does playtime predict enjoyment? (Layer 1 label check)
**Question:** when a game's playtime is high *for that game*, is the player more likely to recommend it?
""")
code(r'''
cache = ROOT / "label" / "cache" / "rec.parquet"
kr = pd.read_parquet(cache, columns=["g", "is_recommended", "calib"])
kr = kr[~kr.calib]
kd = kr.groupby(pd.qcut(kr.g, 10, labels=False, duplicates="drop")).is_recommended.mean()
mp = mc[mc.played & mc.review_recommend.notna()].copy()
pl = mc[mc.played]; gpct = pl.groupby("app_id").playtime_min.rank(pct=True)
mp["g"] = gpct.reindex(mp.index)
mp["n"] = mp.app_id.map(pl.app_id.value_counts()); mp = mp[mp.n >= 20]
md_ = mp.groupby(pd.qcut(mp.g, 10, labels=False, duplicates="drop")).review_recommend.mean()
fig, ax = plt.subplots(figsize=(7.5, 3.8))
ax.plot(kd.index + 1, kd.values, color=C["blue"], marker="o", ms=6, label=f"Kaggle reviewers (n={len(kr)/1e6:.1f}M)")
ax.plot(md_.index + 1, md_.values.astype(float), color=C["orange"], marker="o", ms=6, label=f"McAuley full-library users (n={len(mp):,})")
ax.set_xticks(range(1, 11)); ax.set_xlabel("Playtime decile within the game (1 = least played)")
ax.yaxis.set_major_formatter(mtick.PercentFormatter(1)); ax.set_ylabel("Share who recommend"); ax.legend(loc="lower right")
finish(fig, ax, "More playtime, more recommendations, but the effect is modest", "Share recommending the game, by per-game playtime decile", "12_label_reliability")
say(f"**What we see:** Kaggle goes from **{pct(kd.iloc[0])}** recommend (bottom decile) to **{pct(kd.iloc[-1])}** (top decile). "
    f"McAuley goes from **{pct(float(md_.iloc[0]))}** to **{pct(float(md_.iloc[-1]))}**. The bottom decile is where dislikes concentrate.")
''')
md("""
**What it means:** playtime carries real but **loose** signal (kappa ≈ 0.2 at best; see `label/label_tests.md`).
Most of the information is at the **low end**: very short playtime relative to the game is a meaningful negative,
while "above median" doesn't separate love from like. The label should mark *clear* dislikes and *clear* likes
and leave the ambiguous middle out (the two-sided label being tested).
""")

# ---------------------------------------------------------------- 13 live coverage
md("""
## 13. Can the model see a real user's library?
**Question:** for a live user (example: the project owner's library), how many owned games can each part of the model use?
""")
code(r'''
lib = pd.read_csv(ROOT / "eda" / "steam_my_library.csv")
known_cf = set(mc[mc.played].app_id) | set(kag[kag.played].app_id)
parts = pd.Series({"Owned": len(lib),
                   "Played at least once": int((lib.playtime_forever > 0).sum()),
                   "Known to the content side (in catalog)": int(lib.appid.isin(games.app_id).sum()),
                   "Known to the collaborative model": int(lib.appid.isin(known_cf).sum())})
fig, ax = plt.subplots(figsize=(7.5, 2.8))
y = np.arange(len(parts))[::-1]
ax.barh(y, parts.values, color=[SEQ[2], SEQ[3], C["blue"], C["orange"]], height=0.6); ax.set_yticks(y, parts.index)
for yi, v in zip(y, parts.values): ax.text(v, yi, f"  {v}", va="center", fontsize=9)
ax.grid(axis="y", visible=False); ax.set_xlim(0, parts.max() * 1.15)
finish(fig, ax, "Only part of a real library is usable today", "One live Steam library (21 games) through each part of the model", "13_live_library_coverage",
       source="Source: Steam Web API GetOwnedGames, Oct 2026")
say(f"**What we see:** of **{parts['Owned']}** owned games, the collaborative model knows **{parts.iloc[3]}** and the catalog knows **{parts.iloc[2]}**.")
''')
md("""
**What it means:** this is the "anyone with a Steam account" problem in one picture. The catalog refresh
(adding post-2023 games with Steam descriptions) raises the content-side bar. The collaborative bar only rises as
interaction data for newer games is collected, for example from consenting users of the app.
""")

md("""
## Summary: decisions this EDA supports
| # | Finding | Decision |
|---|---|---|
| 1 | Kaggle covers about 1 in 5 Steam games | Content side + weekly catalog refresh are required |
| 2 | 16% of Kaggle "games" are DLC | Recommend `item_type = game` only; keep DLC for training |
| 4 | A few generic tags dominate | IDF-weight tags for taste profiles and the exploration metric |
| 6 | Reviewers play much longer than owners; many owned games are never played | Train and evaluate on full libraries (McAuley); zero playtime = unknown |
| 7 | Typical playtime varies ~10x by genre | Normalize playtime per game (percentile / median ratio) |
| 8 | Top 1% of games get most of the play | Report popularity bias; tuned MostPopular baseline; surprise row |
| 9 | Most Kaggle users have one review | McAuley is the primary user-side data; segment results by history size |
| 12 | Playtime predicts recommends only loosely | Two-sided label with an ambiguous middle (pending the label test) |
| 13 | A real library is only partly visible to the model | Hybrid scoring; content fallback; measure coverage per user |
""")

nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3"}})
ExecutePreprocessor(timeout=3600, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(HERE)}})
nbf.write(nb, HERE / "steam_eda.ipynb")
print("wrote", HERE / "steam_eda.ipynb")
