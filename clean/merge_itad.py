"""Rule G24: Steam's current regular price (from IsThereAnyDeal) becomes the main regular price.

Why: a check of 8,658 games found ~1 in 4 of our regular prices more than 10% off Steam's real regular price
(leftover sale prices, price changes since 2023, games that went free). Games IsThereAnyDeal has no Steam price for
keep their old value. The old value is kept in `price_regular_old`; a backup of the catalog is written first.
Input: C:/Users/juant/data_raw/itad/prices_catalog_<date>.parquet (eval/fetch_itad_prices.py --all).
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python clean/merge_itad.py
Then rerun clean/data_dictionary.py.
"""
import glob
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
GAMES = Path("C:/Users/juant/data_clean/games.parquet")
BACKUP = GAMES.with_name("games.before_itad.parquet")
f = sorted(glob.glob("C:/Users/juant/data_raw/itad/prices_catalog_*.parquet"))[-1]

if not BACKUP.exists():
    shutil.copy2(GAMES, BACKUP)
g = pd.read_parquet(GAMES)
if "price_regular_old" in g.columns:
    raise SystemExit("G24 already applied (price_regular_old exists). Restore games.before_itad.parquet to redo it.")
it = pd.read_parquet(f).drop_duplicates("app_id").set_index("app_id")
snap = it.fetched.iloc[0]

old = g[["price_regular", "kaggle_price_regular"]].max(axis=1)
steam = g.app_id.map(it.steam_regular)
use = steam.notna()
g["price_regular_old"] = g.price_regular
g.loc[use, "price_regular"] = steam[use]
g.loc[use, "price_source"] = "itad_steam_regular"

both = use & old.notna()
rel = ((old - steam) / steam.where(steam > 0))[both]
went_free = int((both & (steam == 0) & (old > 0)).sum())
was_zero = int((both & (steam > 0) & (old == 0)).sum())
g.to_parquet(GAMES, index=False)

row = (f"| G24  | IsThereAnyDeal      | Regular price replaced by Steam's current regular price (snapshot {snap}) | {int(use.sum())} | "
       "price_regular = Steam regular; old value in price_regular_old; price_source = itad_steam_regular | "
       f"{(rel.abs() > 0.10).mean():.0%} of old prices were >10% off; {was_zero} paid games had $0, {went_free} games have gone free |")
rep = ROOT / "clean" / "cleaning_report.md"
rep.write_text(rep.read_text(encoding="utf-8").rstrip("\n") + "\n" + row + "\n", encoding="utf-8")
rec = g[g.recommendable]
print(f"snapshot {snap}: replaced {int(use.sum()):,} of {len(g):,} prices "
      f"({rec.price_source.eq('itad_steam_regular').mean():.1%} of recommendable games)")
print(f"old price >10% off: {(rel.abs() > 0.10).mean():.1%} (too low {(rel < -0.10).mean():.1%}, too high {(rel > 0.10).mean():.1%}); "
      f"paid games that had $0: {was_zero}; went free since: {went_free}")
print(g.price_source.value_counts().to_string())
