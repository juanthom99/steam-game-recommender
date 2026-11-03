"""Apply the SteamSpy refill (collect/steamspy_refill.py) to the cleaned catalog. Run after the refill finishes.

Rule G22: games with no user tags get SteamSpy's tags, most-voted first.
Rule G23: games priced only by the October 2026 FronkonGames crawl (price_source = fronkon_2026_only) get SteamSpy's
          regular price (`initialprice`, US cents), and price_source = steamspy_regular.
Both rules append a line to clean/cleaning_report.md. Rerun clean/data_dictionary.py and dashboard/load_supabase.py after.

Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python clean/merge_steamspy.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
GAMES = Path("C:/Users/juant/data_clean/games.parquet")
SPY = Path("C:/Users/juant/data_raw/steamspy/appdetails.jsonl")

spy = pd.DataFrame([json.loads(l) for l in SPY.open(encoding="utf-8") if l.strip()]).drop_duplicates("appid", keep="last")
spy = spy[spy.error.isna()].set_index("appid")
g = pd.read_parquet(GAMES)

no_tags = g.tags.map(lambda t: t is None or len(t) == 0)
new_tags = g.app_id.map(spy.tags)
fill_t = no_tags & new_tags.map(lambda t: isinstance(t, list) and len(t) > 0)
g.loc[fill_t, "tags"] = new_tags[fill_t]
g["n_tags"] = g.tags.map(len)

reg = pd.to_numeric(g.app_id.map(spy.initialprice), errors="coerce") / 100
fill_p = g.price_source.eq("fronkon_2026_only") & reg.notna()
g.loc[fill_p, "price_regular"] = reg[fill_p]
g.loc[fill_p, "price_source"] = "steamspy_regular"

g.to_parquet(GAMES, index=False)
rows = [
    f"| G22  | SteamSpy            | Games with no user tags given SteamSpy tags (most-voted first) | {int(fill_t.sum())} | filled | "
    "the FronkonGames copy has an empty tags column (data note, concern 5) |",
    f"| G23  | SteamSpy            | Fronkon-only prices replaced by SteamSpy's regular price | {int(fill_p.sum())} | "
    "price_regular = initialprice / 100; price_source = steamspy_regular | the Oct 2026 crawl often caught sale prices (concern 6) |",
]
rep = ROOT / "clean" / "cleaning_report.md"
rep.write_text(rep.read_text(encoding="utf-8").rstrip("\n") + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
rec = g[g.recommendable]
print(f"tags filled {int(fill_t.sum()):,}; prices fixed {int(fill_p.sum()):,}; recommendable games still without tags: "
      f"{rec.tags.map(len).eq(0).mean():.1%}")
