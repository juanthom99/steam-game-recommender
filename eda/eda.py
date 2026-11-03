"""EDA for the Kaggle 'Game Recommendations on Steam' dataset.

Usage: python eda/eda.py <dataset_dir>
Writes eda/eda_report.md and prints it.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(sys.argv[1])
OUT = Path(__file__).parent / "eda_report.md"
lines = []


def h(text):
    lines.append(f"\n## {text}\n")


def p(text=""):
    lines.append(str(text))


def md(df):
    lines.append(df.to_markdown())
    lines.append("")


def profile(df, name):
    h(f"Profile: {name}")
    p(f"- Rows: {len(df):,}  |  Columns: {df.shape[1]}  |  Memory: {df.memory_usage(deep=True).sum()/1e6:,.0f} MB\n")
    rows = []
    for c in df.columns:
        s = df[c]
        nn = s.isna().mean()
        try:
            nuniq = s.nunique()
        except TypeError:  # lists
            nuniq = s.astype(str).nunique()
        row = {"column": c, "dtype": str(s.dtype), "null %": round(nn * 100, 2),
               "distinct": nuniq, "card. ratio": round(nuniq / max(len(s), 1), 4)}
        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            q = s.quantile([0, .01, .5, .95, .99, 1]).round(2).tolist()
            row.update({"min": q[0], "p1": q[1], "p50": q[2], "p95": q[3], "p99": q[4], "max": q[5],
                        "mean": round(s.mean(), 2), "zeros": int((s == 0).sum())})
        rows.append(row)
    md(pd.DataFrame(rows).set_index("column"))


# ---------------- games.csv ----------------
games = pd.read_csv(DATA / "games.csv", parse_dates=["date_release"])
profile(games, "games.csv (one row per game)")
p(f"- app_id unique: {games.app_id.is_unique}")
p(f"- Release dates: {games.date_release.min().date()} to {games.date_release.max().date()}")
p(f"- Duplicate titles: {games.title.duplicated().sum():,}")
p(f"- Free games (price_final == 0): {(games.price_final == 0).sum():,} ({(games.price_final == 0).mean():.1%})")
p(f"- Currently discounted (discount > 0): {(games.discount > 0).sum():,}")
p(f"- price_final > price_original (suspicious): {(games.price_final > games.price_original).sum():,}")
p(f"- Games with < 10 user_reviews: {(games.user_reviews < 10).sum():,} ({(games.user_reviews < 10).mean():.1%})\n")
p("**Rating label distribution**\n")
md(games.rating.value_counts().to_frame("games"))
p("**Platform support (share of games)**\n")
md(games[["win", "mac", "linux", "steam_deck"]].mean().round(3).to_frame("share"))
p("**Games released per year (last 12 years)**\n")
md(games.date_release.dt.year.value_counts().sort_index().tail(12).to_frame("games"))

# ---------------- games_metadata.json ----------------
meta = pd.read_json(DATA / "games_metadata.json", lines=True)
profile(meta, "games_metadata.json (text for the RAG index)")
meta["desc_len"] = meta.description.fillna("").str.len()
meta["n_tags"] = meta.tags.apply(len)
p(f"- Empty descriptions: {(meta.desc_len == 0).sum():,} ({(meta.desc_len == 0).mean():.1%})")
p(f"- Games with no tags: {(meta.n_tags == 0).sum():,} ({(meta.n_tags == 0).mean():.1%})")
p(f"- Description length (chars): median {meta.desc_len.median():.0f}, p95 {meta.desc_len.quantile(.95):.0f}, max {meta.desc_len.max()}")
p(f"- Tags per game: median {meta.n_tags.median():.0f}, max {meta.n_tags.max()}")
p(f"- metadata app_ids missing from games.csv: {(~meta.app_id.isin(games.app_id)).sum():,}")
p(f"- games.csv app_ids missing metadata: {(~games.app_id.isin(meta.app_id)).sum():,}\n")
tags = meta.tags.explode().value_counts()
p(f"- Distinct tags: {len(tags):,}\n")
p("**Top 25 tags**\n")
md(tags.head(25).to_frame("games"))

# ---------------- users.csv ----------------
users = pd.read_csv(DATA / "users.csv")
profile(users, "users.csv (one row per user)")
p(f"- user_id unique: {users.user_id.is_unique}")
p(f"- Users with 0 reviews: {(users.reviews == 0).sum():,}")
p(f"- Users with >= 5 reviews: {(users.reviews >= 5).sum():,} ({(users.reviews >= 5).mean():.1%})\n")

# ---------------- recommendations.csv ----------------
rec = pd.read_csv(
    DATA / "recommendations.csv",
    dtype={"app_id": "int32", "helpful": "int32", "funny": "int32", "hours": "float32",
           "user_id": "int32", "review_id": "int32", "is_recommended": "bool"},
    parse_dates=["date"],
)
profile(rec, "recommendations.csv (one row per user review of a game)")
p(f"- review_id unique: {rec.review_id.is_unique}")
dup = rec.duplicated(["user_id", "app_id"]).sum()
p(f"- Duplicate (user_id, app_id) pairs: {dup:,}")
p(f"- Date range: {rec.date.min().date()} to {rec.date.max().date()}")
p(f"- Future dates (after 2026-10-28): {(rec.date > '2026-10-28').sum():,}")
p(f"- Recommended share: {rec.is_recommended.mean():.1%}  <- class imbalance for training")
p(f"- hours == 0: {(rec.hours == 0).sum():,}; hours >= 999: {(rec.hours >= 999).sum():,} (possible cap)")
p(f"- app_ids not in games.csv: {(~rec.app_id.isin(games.app_id)).sum():,}")
p(f"- user_ids not in users.csv: {(~rec.user_id.isin(users.user_id)).sum():,}\n")

n_u, n_i = rec.user_id.nunique(), rec.app_id.nunique()
p(f"- Interaction matrix: {n_u:,} users x {n_i:,} games, density {len(rec)/(n_u*n_i):.6%}\n")

upu = rec.groupby("user_id").size()
ipg = rec.groupby("app_id").size()
p("**Reviews per user / per game (long tail check)**\n")
md(pd.DataFrame({
    "reviews per user": upu.describe(percentiles=[.5, .75, .9, .99]).round(1),
    "reviews per game": ipg.describe(percentiles=[.5, .75, .9, .99]).round(1),
}))
top1 = ipg.sort_values(ascending=False)
p(f"- Top 1% of games get {top1.head(max(1, len(top1)//100)).sum()/len(rec):.1%} of all reviews (popularity bias)")
p(f"- Users with 1 review (cold start): {(upu == 1).sum():,} ({(upu == 1).mean():.1%})")
p(f"- Users with >= 5 reviews: {(upu >= 5).sum():,} ({(upu >= 5).mean():.1%})\n")

p("**Reviews per year**\n")
md(rec.date.dt.year.value_counts().sort_index().to_frame("reviews"))

p("**Hours played vs recommendation**\n")
md(rec.groupby("is_recommended").hours.describe(percentiles=[.5, .9]).round(1))

p("**Correlations (sample of 2M reviews)**\n")
smp = rec.sample(min(2_000_000, len(rec)), random_state=0)
md(smp[["helpful", "funny", "hours", "is_recommended"]].astype(float).corr(method="spearman").round(3))

p("**games.csv numeric correlations (Spearman)**\n")
md(games[["positive_ratio", "user_reviews", "price_final", "price_original", "discount"]].corr(method="spearman").round(3))

OUT.write_text("# Steam Recommendations EDA\n" + "\n".join(lines), encoding="utf-8")
print(OUT.read_text(encoding="utf-8"))
