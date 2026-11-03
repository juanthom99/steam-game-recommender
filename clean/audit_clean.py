"""Audit the cleaned tables for problems the cleaning rules don't catch yet.

Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python clean/audit_clean.py
Writes clean/audit_report.md. Each finding lists a count, examples and a suggested rule.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

D = Path("C:/Users/juant/data_clean")
OUT = Path(__file__).resolve().parent / "audit_report.md"
TODAY = pd.Timestamp("2026-10-28")
md = ["# Audit of cleaned data\n"]


def finding(table, name, mask_or_n, examples=None, note=""):
    n = int(mask_or_n.sum()) if hasattr(mask_or_n, "sum") else int(mask_or_n)
    md.append(f"- **{table} · {name}:** {n:,}" + (f" — {note}" if note else ""))
    if examples is not None and len(examples):
        md.append("  - e.g. " + "; ".join(str(e)[:90] for e in list(examples)[:6]))
    print(f"{table} | {name}: {n:,}", flush=True)


# ============================================================ games
g = pd.read_parquet(D / "games.parquet")
md.append(f"\n## games ({len(g):,} rows)\n")
t = g.title.fillna("")
finding("games", "titles with HTML entities", t.str.contains(r"&(amp|quot|#\d+|lt|gt);"), t[t.str.contains(r"&(amp|quot|#\d+|lt|gt);")])
finding("games", "titles with ™/®/©", t.str.contains("[™®©]"), t[t.str.contains("[™®©]")], "strip for matching only (title_norm)")
finding("games", "titles with control/zero-width chars", t.str.contains(r"[\x00-\x1f\u200b-\u200f\ufeff]"))
finding("games", "titles > 100 chars", t.str.len() > 100, t[t.str.len() > 100])
finding("games", "titles that look like placeholders", t.str.fullmatch(r"(?i)(test|untitled|tbd|game|app|\d+|.{1,2})"),
        t[t.str.fullmatch(r"(?i)(test|untitled|tbd|game|app|\d+|.{1,2})")])

d = g.description.fillna("")
finding("games", "descriptions containing HTML tags", d.str.contains(r"<[a-zA-Z/][^>]*>"), d[d.str.contains(r"<[a-zA-Z/][^>]*>")])
finding("games", "descriptions containing HTML entities", d.str.contains(r"&(amp|quot|nbsp|#\d+);"))
finding("games", "descriptions < 20 chars (non-empty)", d.str.len().between(1, 19), d[d.str.len().between(1, 19)])
dupd = d[d.str.len() > 0].duplicated(keep=False)
finding("games", "descriptions shared by 2+ apps", dupd, d[d.str.len() > 0][dupd].value_counts().head(6).index,
        "template text; weak content signal")
nonascii = d.map(lambda s: sum(ord(c) > 127 for c in s) / max(len(s), 1))
finding("games", "descriptions mostly non-Latin (>30% non-ASCII)", nonascii > 0.3, g.title[nonascii > 0.3],
        "embedding model is English-only")

rd = pd.to_datetime(g.release_date, errors="coerce")
finding("games", "release_date missing", rd.isna())
finding("games", "release_date in the future (unreleased)", rd > TODAY, g.title[rd > TODAY], "can't be played yet")
finding("games", "release_date before 1980", rd < "1980-01-01", g.title[rd < "1980-01-01"] + " " + rd[rd < "1980-01-01"].astype(str))

for c in ("kaggle_price_regular", "fronkon_price"):
    if c in g:
        p = pd.to_numeric(g[c], errors="coerce")
        finding("games", f"{c} > $150", p > 150, (g.title[p > 150] + " $" + p[p > 150].astype(str)))
both = g.kaggle_price_regular.notna() & g.fronkon_price.notna() & (g.fronkon_price > 0) & (g.kaggle_price_regular > 0)
gap = (g.fronkon_price[both] - g.kaggle_price_regular[both]).abs() / g.kaggle_price_regular[both]
finding("games", "Kaggle vs Fronkon regular price differ > 50%", gap > 0.5, g.title[both][gap > 0.5],
        "prices change over time; IsThereAnyDeal is the live source anyway")
finding("games", "positive_ratio outside 0–100", ~g.positive_ratio.dropna().between(0, 100))
finding("games", "owners_lo > owners_hi", (g.owners_lo > g.owners_hi))

tags = g.tags.map(lambda v: list(v) if isinstance(v, (list, np.ndarray)) else [])
finding("games", "tag lists with duplicates", tags.map(lambda l: len(l) != len(set(l))))
vocab = pd.Series([x for l in tags for x in l]).value_counts()
low = {}
for x in vocab.index:
    low.setdefault(x.strip().lower(), []).append(x)
variants = {k: v for k, v in low.items() if len(v) > 1}
finding("games", "tag spellings differing only by case/space", len(variants), list(variants.values()))
finding("games", "tags used by < 5 games", (vocab < 5).sum(), vocab[vocab < 5].index, f"vocabulary {len(vocab):,}")

ty = g.item_type.fillna("missing")
md.append("  - item_type: " + ", ".join(f"{k} {v:,}" for k, v in ty.value_counts().items()))
tool = g[ty == "tool"]
finding("games", "typed 'tool' by the name rule", len(tool), tool.title.sample(min(6, len(tool)), random_state=0) if len(tool) else None,
        "check for false positives like 'Beta Squad' or 'Test Drive'")
finding("games", "duplicate titles (title_norm)", g.dup_title, g[g.dup_title].sort_values("title_norm").title.head(12))

# adult content (raw Fronkon fields not yet carried)
fr = pd.read_parquet("C:/Users/juant/data_raw/fronkon/games.parquet", columns=["appID", "required_age", "notes", "tags", "categories"])
fr_tags = fr.tags.map(lambda v: list(v.keys()) if isinstance(v, dict) else (list(v) if isinstance(v, (list, np.ndarray)) else []))
adult = (pd.to_numeric(fr.required_age, errors="coerce") >= 18) | fr.notes.fillna("").str.contains(r"(?i)sexual|nudity") \
        | fr_tags.map(lambda l: any(x in ("Sexual Content", "Nudity", "NSFW", "Hentai") for x in l))
finding("games", "adult/sexual content (Fronkon age ≥ 18, notes or tags)", adult, note="flag; exclude by default")
md.append(f"  - Fronkon tags type: {type(fr.tags.dropna().iloc[0]).__name__}")

# ============================================================ Kaggle interactions
cols = ["user_key", "app_id", "playtime_min", "played", "censored", "is_game", "review_date", "helpful", "funny"]
k = pd.read_parquet(D / "interactions_kaggle.parquet", columns=cols)
md.append(f"\n## interactions_kaggle ({len(k):,} rows)\n")
finding("kaggle", "app_id not in games", ~k.app_id.isin(g.app_id))
finding("kaggle", "review_date in the future", k.review_date > TODAY)
finding("kaggle", "review_date before game's release", (k.review_date < k.app_id.map(rd.set_axis(g.app_id))) )
rd_map = rd.set_axis(g.app_id)
early = k.review_date < (k.app_id.map(rd_map) - pd.Timedelta(days=30))
finding("kaggle", "review > 30 days before release (early access/beta keys or bad release date)", early,
        g.set_index("app_id").title.reindex(k.app_id[early].value_counts().head(6).index))
finding("kaggle", "not a game (is_game False) incl. unresolved types", ~k.is_game)
per_day = k.groupby(["user_key", "review_date"]).size()
finding("kaggle", "user-days with ≥ 50 reviews (bot/bulk-review pattern)", per_day >= 50)
bulk_users = per_day[per_day >= 50].index.get_level_values(0).unique()
finding("kaggle", "users with any ≥ 50-review day", len(bulk_users))
uc = k.groupby("user_key").size()
finding("kaggle", "users with ≥ 1,000 reviews", uc >= 1000, uc[uc >= 1000].sort_values().tail(6).astype(str))
same = k[k.user_key.isin(uc[uc >= 10].index)].groupby("user_key").playtime_min.nunique()
finding("kaggle", "users (≥10 reviews) whose playtime is identical on every game", same == 1, note="copy-paste/bot")
finding("kaggle", "helpful > 10,000", k.helpful > 10000)
del k

# ============================================================ McAuley interactions
m = pd.read_parquet(D / "interactions_mcauley.parquet")
md.append(f"\n## interactions_mcauley ({len(m):,} rows)\n")
finding("mcauley", "app_id not in games", ~m.app_id.isin(g.app_id),
        m.app_id[~m.app_id.isin(g.app_id)].value_counts().head(6).index.astype(str))
finding("mcauley", "2-week playtime > lifetime playtime", m.playtime_2w_min > m.playtime_min)
finding("mcauley", "lifetime playtime > 50,000 h (≈ 5.7 years nonstop)", m.playtime_min > 3_000_000)
hp = m.playtime_min / 60
finding("mcauley", "lifetime playtime > 10,000 h", hp > 10000, (m.app_id[hp > 10000].map(g.set_index("app_id").title).value_counts().head(6).index))
lib = m.groupby("user_key").agg(n=("app_id", "size"), played=("played", "sum"), tot=("playtime_min", "sum"))
finding("mcauley", "users with ≥ 3,000 owned items", lib.n >= 3000, lib.n[lib.n >= 3000].sort_values().tail(6).astype(str))
finding("mcauley", "users with games but zero played", (lib.n > 0) & (lib.played == 0))
finding("mcauley", "users with total playtime > 8,760 h per year since 2009 (> 24h/day)", lib.tot / 60 > 24 * 365 * 9)
md.append("  - item_type of owned rows: " + ", ".join(f"{k_} {v:,}" for k_, v in m.item_type.fillna("missing").value_counts().items()))
top_tool = m[m.item_type == "tool"].app_id.value_counts().head(8)
md.append("  - most-owned items typed 'tool': " + "; ".join(f"{a} {g.set_index('app_id').title.get(a, '?')} ({n:,})" for a, n in top_tool.items()))
top_unk = m[m.item_type == "unknown"].app_id.value_counts().head(8)
md.append("  - most-owned items typed 'unknown': " + "; ".join(f"{a} {g.set_index('app_id').title.get(a, '?')} ({n:,})" for a, n in top_unk.items()))

OUT.write_text("\n".join(md), encoding="utf-8")
print("wrote", OUT)
