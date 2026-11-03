"""EDA on the live Steam store sample vs the Kaggle snapshot.

Usage: python eda/eda_steam.py <dataset_dir>
Writes eda/steam_report.md and prints it.
"""
import json
import sys
from pathlib import Path

import pandas as pd

DATA = Path(sys.argv[1])
HERE = Path(__file__).parent
raw = [json.loads(l) for l in (HERE / "steam_sample.jsonl").read_text(encoding="utf-8").splitlines()]
games = pd.read_csv(DATA / "games.csv").set_index("app_id")
L = []


def p(t=""):
    L.append(str(t))


def md(df):
    L.append(df.to_markdown())
    L.append("")


rows = []
for r in raw:
    d = r["data"] or {}
    po = d.get("price_overview") or {}
    rows.append({
        "app_id": r["app_id"],
        "http": r["http"],
        "success": r["success"],
        "returned_id": d.get("steam_appid"),
        "type": d.get("type"),
        "name": d.get("name"),
        "is_free": d.get("is_free"),
        "has_price": bool(po),
        "currency": po.get("currency"),
        "price_now": po.get("final", 0) / 100 if po else None,
        "price_initial_now": po.get("initial", 0) / 100 if po else None,
        "discount_now": po.get("discount_percent") if po else None,
        "header_image": bool(d.get("header_image")),
        "n_screenshots": len(d.get("screenshots") or []),
        "short_desc_len": len(d.get("short_description") or ""),
        "coming_soon": (d.get("release_date") or {}).get("coming_soon"),
        "n_genres": len(d.get("genres") or []),
        "has_metacritic": bool(d.get("metacritic")),
    })
s = pd.DataFrame(rows).set_index("app_id").join(games[["title", "price_final", "price_original", "discount", "user_reviews"]])
s["popular"] = s.user_reviews >= games.user_reviews.nlargest(2000).min()
ok = s[s.success]

p(f"## Steam store sample: {len(s)} games ({s.popular.sum()} popular, {(~s.popular).sum()} long-tail)\n")
p("**Response coverage**\n")
md(pd.DataFrame({
    "all": [s.success.mean(), (s.http == 200).mean()],
    "popular": [s[s.popular].success.mean(), (s[s.popular].http == 200).mean()],
    "long-tail": [s[~s.popular].success.mean(), (s[~s.popular].http == 200).mean()],
}, index=["success=true", "HTTP 200"]).round(3))
p(f"- Failed lookups (likely delisted or region-locked): {(~s.success).sum()}")
p(f"- Redirected to a different app_id: {(ok.returned_id != ok.index).sum()}")
p(f"- type values: {ok.type.value_counts().to_dict()}\n")

p("**Field coverage among successful responses**\n")
md(pd.DataFrame({
    "share": {
        "header_image": ok.header_image.mean(),
        "price_overview (paid price)": ok.has_price.mean(),
        "is_free": ok.is_free.mean(),
        "free or priced": (ok.has_price | ok.is_free.fillna(False)).mean(),
        "screenshots >= 1": (ok.n_screenshots > 0).mean(),
        "short_description": (ok.short_desc_len > 0).mean(),
        "genres": (ok.n_genres > 0).mean(),
        "metacritic": ok.has_metacritic.mean(),
    }}).round(3))
p(f"- Currencies returned: {ok.currency.value_counts(dropna=True).to_dict()}")
p(f"- Title mismatches vs Kaggle (case-insensitive): {(ok.name.str.lower() != ok.title.str.lower()).sum()}\n")

priced = ok[ok.has_price].copy()
# Kaggle leaves price_original = 0 when a paid game is not on sale; use price_final there.
priced["kaggle_base"] = priced.price_original.where(priced.price_original > 0, priced.price_final)
p("**Price drift: Kaggle snapshot (late 2023) vs live Steam today**\n")
p(f"- Note: Kaggle price_original is 0 for {(priced.price_original == 0).sum()} paid games here (not on sale); price_final used instead.")
diff = (priced.price_initial_now - priced.kaggle_base).round(2)
p(f"- Games compared: {len(priced)}")
p(f"- Base price unchanged: {(diff == 0).mean():.1%}; higher now: {(diff > 0).mean():.1%}; lower now: {(diff < 0).mean():.1%}")
p(f"- Median base price: Kaggle ${priced.kaggle_base.median():.2f} vs live ${priced.price_initial_now.median():.2f}")
p(f"- On sale right now: {(priced.discount_now > 0).mean():.1%} (Kaggle snapshot: {(priced.discount > 0).mean():.1%})")
p(f"- Kaggle 'free' games that now have a price: {((ok.price_final == 0) & ok.has_price).sum()}\n")
p("Largest base-price changes:\n")
md(priced.assign(change=diff).loc[diff.abs().sort_values(ascending=False).index[:10],
                                   ["title", "kaggle_base", "price_initial_now", "change"]])
mm = ok[ok.name.str.lower() != ok.title.str.lower()]
p("**Title mismatches (Kaggle vs live)**\n")
md(mm[["title", "name"]])

if (~s.success).any():
    p("**Failed lookups**\n")
    md(s[~s.success][["title", "user_reviews", "http"]])

out = HERE / "steam_report.md"
out.write_text("# Steam Web API EDA\n\n" + "\n".join(L), encoding="utf-8")
print(out.read_text(encoding="utf-8"))
