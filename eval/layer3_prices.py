"""Layer 3 value per dollar at three prices: regular (as in eval/layer3.py), current best deal, and all-time low.

Disclosed addition (not in the frozen protocol, which lists regular price only). Reads the saved test top-10 lists;
the test set is not scored again. Prices: IsThereAnyDeal, US, snapshot in data_raw/itad/prices_<date>.parquet.
Paid hits only (regular price > 0, rule G24 regular price; games now free count as free); a hit is dropped from a column when that column's price is missing or 0.
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python eval/layer3_prices.py
Out: eval/layer3_prices.md
"""
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from harness import load  # noqa: E402

C = HERE / "cache"
res = pd.read_parquet(C / "test_results.parquet")
res = res[res.n_visible >= 5]
U, rec, test = load("test")
P = {(p["src"], p["user"]): p for p in test}
g = pd.read_parquet("C:/Users/juant/data_clean/games.parquet", columns=["app_id", "price_regular", "kaggle_price_regular", "price_source"])
regular = g.price_regular.where(g.price_source.eq("itad_steam_regular"), g[["price_regular", "kaggle_price_regular"]].max(axis=1)).set_axis(g.app_id).reindex(U).to_numpy()   # rule G24: Steam regular price when known
f = sorted(glob.glob("C:/Users/juant/data_raw/itad/prices_*.parquet"))[-1]
it = pd.read_parquet(f).set_index("app_id")
now = it.best_now.reindex(U).to_numpy(float)
low = it.all_time_low.reindex(U).to_numpy(float)
low = np.where(low <= regular, low, np.nan)   # an all-time low above the regular price is a bundle or edition mismatch
snap = it.fetched.iloc[0]

rows = []
for r in res.itertuples():
    p = P[(r.src, r.user)]
    pt = dict(zip(p["hid_u"].tolist(), p["hid_pt"].tolist()))
    hits = set(p["hit_u"].tolist())
    for t in r.top10:
        if t in hits and regular[t] > 0:
            rows.append((r.model, t, pt[t] / 60, regular[t], now[t], low[t]))
H = pd.DataFrame(rows, columns=["model", "item", "hours", "regular", "now", "low"])


def med(h, price):
    ok = np.isfinite(price) & (price > 0)
    return np.median(h[ok] / price[ok]) if ok.any() else np.nan, ok.mean()


order = ["MostPopular", "item-kNN", "EASE", "ALS", "Hybrid", "Hybrid-EASE", "Hybrid: Try something new"]
tab = []
for m in order:
    x = H[H.model == m]
    if not len(x):
        continue
    hr, _ = med(x.hours.to_numpy(), x.regular.to_numpy())
    hn, cn = med(x.hours.to_numpy(), x.now.to_numpy())
    hl, cl = med(x.hours.to_numpy(), x.low.to_numpy())
    gap = (x.now - x.low) / x.regular
    tab.append({"model": m, "paid hits": len(x), "median hours per $ (regular)": hr,
                "median hours per $ (best price now)": hn, "median hours per $ (all-time low)": hl,
                "share with a price now": cn, "share with an all-time low": cl,
                "median discount now": np.nanmedian(1 - x.now / x.regular),
                "hits within 5% of all-time low now": (gap[np.isfinite(gap)] <= 0.05).mean()})
tab = pd.DataFrame(tab)
md = ["# Layer 3 value per dollar at three prices (test set, 5+ visible games)\n",
      "> Disclosed addition: the frozen protocol lists regular price only. Computed from the saved test lists "
      "(`eval/run_test.py`); the test set was not scored again.\n",
      f"Prices from IsThereAnyDeal (US), snapshot {snap}. 'Best price now' is the lowest current price across shops; "
      "it changes daily, so treat that column as a snapshot. Hours are the player's lifetime hours in the game. "
      "Regular price is the same column `eval/layer3.py` uses.\n",
      tab.round(3).to_markdown(index=False),
      "\nPrice data: [IsThereAnyDeal](https://isthereanydeal.com)."]
(HERE / "layer3_prices.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(md))
