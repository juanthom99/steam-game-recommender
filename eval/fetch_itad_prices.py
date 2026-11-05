"""Fetch IsThereAnyDeal prices (US) for every game that appears in the saved test top-10 lists.

Per game: best current price across shops, Steam's current price, regular price, all-time low.
A snapshot on the run date (prices change daily); IsThereAnyDeal is the source and is credited in the report.
Needs ITAD_API_KEY in the environment or .env. The key is never printed.
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python eval/fetch_itad_prices.py [--all]
Out: C:/Users/juant/data_raw/itad/prices_[catalog_]<date>.parquet
"""
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
API, STEAM = "https://api.isthereanydeal.com", 61
OUT = Path("C:/Users/juant/data_raw/itad"); OUT.mkdir(parents=True, exist_ok=True)

key = os.environ.get("ITAD_API_KEY")
env = HERE.parent / ".env"
if not key and env.exists():
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("ITAD_API_KEY="):
            key = line.split("=", 1)[1].strip()
if not key:
    sys.exit("ITAD_API_KEY is not set (.env).")
H = {"ITAD-API-Key": key}

U = np.load(HERE / "cache" / "universe.npy")
ALL = "--all" in sys.argv                        # --all: every game in the cleaned catalog
if ALL:
    app_ids = sorted(pd.read_parquet("C:/Users/juant/data_clean/games.parquet", columns=["app_id"]).app_id.astype(int).unique().tolist())
else:
    res = pd.read_parquet(HERE / "cache" / "test_results.parquet", columns=["top10"])
    app_ids = sorted({int(U[i]) for t in res.top10 for i in t})
print(f"games to price: {len(app_ids):,}", flush=True)


def post(path, body, **params):
    for attempt in range(5):
        r = requests.post(f"{API}{path}", headers=H, params=params, json=body, timeout=60)
        if r.status_code == 429:
            time.sleep(30 * (attempt + 1)); continue
        r.raise_for_status()
        time.sleep(0.4)                       # stay well under 1000 requests / 5 min
        return r.json()
    raise SystemExit(f"rate limited on {path}")


# progress is saved after every batch, so a stopped run resumes where it left off (same day only)
day = dt.date.today().isoformat()
MAPF, PART = OUT / f"id_map_{day}.json", OUT / f"partial_{day}.jsonl"
id_map = {int(k): v for k, v in json.loads(MAPF.read_text()).items()} if MAPF.exists() else {}
todo = [a for a in app_ids if a not in id_map]
for i in range(0, len(todo), 200):
    id_map.update({int(k.split("/")[1]): v for k, v in post(f"/lookup/id/shop/{STEAM}/v1", [f"app/{a}" for a in todo[i:i + 200]]).items()})
    MAPF.write_text(json.dumps(id_map))
itad = [v for v in id_map.values() if v]
print(f"matched to IsThereAnyDeal: {len(itad):,}", flush=True)

rows, steam = {}, {}
if PART.exists():
    for line in PART.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        rows.update(r["rows"]); steam.update(r["steam"])
done = {i for line in (PART.read_text(encoding="utf-8").splitlines() if PART.exists() else []) for i in json.loads(line)["ids"]}
left = [i for i in itad if i not in done]
print(f"already fetched: {len(done):,}; left: {len(left):,}", flush=True)
for i in range(0, len(left), 200):
    chunk = left[i:i + 200]
    r_, s_ = {}, {}
    for gm in post("/games/overview/v2", chunk, country="US").get("prices", []):
        cur, low = gm.get("current") or {}, gm.get("lowest") or {}
        r_[gm["id"]] = {"best_now": (cur.get("price") or {}).get("amount"),
                        "regular": (cur.get("regular") or {}).get("amount"),
                        "best_shop": (cur.get("shop") or {}).get("name"),
                        "all_time_low": (low.get("price") or {}).get("amount")}
    for gm in post("/games/prices/v3", chunk, country="US"):
        d = next((d for d in gm.get("deals", []) if d["shop"]["id"] == STEAM), None)
        if d:
            s_[gm["id"]] = {"steam_now": d["price"]["amount"], "steam_regular": d["regular"]["amount"]}
    with PART.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ids": chunk, "rows": r_, "steam": s_}) + "\n")
    rows.update(r_); steam.update(s_)
    print(f"prices {len(done) + min(i + 200, len(left)):,}/{len(itad):,}", flush=True)

df = pd.DataFrame([{"app_id": a, "itad_id": id_map.get(a), **rows.get(id_map.get(a), {}), **steam.get(id_map.get(a), {})}
                   for a in app_ids])
df["fetched"] = dt.date.today().isoformat()
f = OUT / f"prices_{'catalog_' if ALL else ''}{dt.date.today().isoformat()}.parquet"
df.to_parquet(f)
print(f"wrote {f}: {len(df):,} games; with all-time low {df.all_time_low.notna().mean():.1%}; "
      f"with Steam price {df.steam_now.notna().mean():.1%}")
