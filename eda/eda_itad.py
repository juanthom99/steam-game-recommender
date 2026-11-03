"""IsThereAnyDeal EDA for the same games sampled from Steam: buy-now-or-wait signals.

Needs ITAD_API_KEY in the environment or in .env (register at https://isthereanydeal.com/apps/my/).
Usage: python eda/eda_itad.py
Writes eda/itad_sample.json and eda/itad_report.md.
Limit: 1000 requests / 5 min (email verified). This uses ~3 requests for 300 games.
"""
import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).parent
API = "https://api.isthereanydeal.com"
STEAM_SHOP_ID = 61  # ITAD's shop id for Steam

key = os.environ.get("ITAD_API_KEY")
env = HERE.parent / ".env"
if not key and env.exists():
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("ITAD_API_KEY="):
            key = line.split("=", 1)[1].strip()
if not key:
    sys.exit("ITAD_API_KEY is not set. Add it to .env (see .env.example).")
H = {"ITAD-API-Key": key}

app_ids = [json.loads(l)["app_id"] for l in (HERE / "steam_sample.jsonl").read_text(encoding="utf-8").splitlines()]

# 1. Steam app ids -> ITAD game ids (one bulk call)
r = requests.post(f"{API}/lookup/id/shop/{STEAM_SHOP_ID}/v1", headers=H,
                  json=[f"app/{a}" for a in app_ids], timeout=30)
r.raise_for_status()
id_map = {int(k.split("/")[1]): v for k, v in r.json().items()}
itad_ids = [v for v in id_map.values() if v]


def batched(path, ids, **params):
    out = []
    for i in range(0, len(ids), 200):
        resp = requests.post(f"{API}{path}", headers=H, params={"country": "US", **params},
                             json=ids[i:i + 200], timeout=30)
        resp.raise_for_status()
        out.append(resp.json())
    return out


# 2. Current best price + all-time low across shops
overview = batched("/games/overview/v2", itad_ids)
# 3. Current prices per shop (to count shops and compare Steam vs elsewhere)
prices = [g for chunk in batched("/games/prices/v3", itad_ids) for g in chunk]
(HERE / "itad_sample.json").write_text(json.dumps({"id_map": id_map, "overview": overview, "prices": prices}), encoding="utf-8")

rev = {v: k for k, v in id_map.items() if v}
rows = []
for chunk in overview:
    for g in chunk.get("prices", []):
        cur, low = g.get("current") or {}, g.get("lowest") or {}
        rows.append({
            "app_id": rev.get(g["id"]),
            "best_now": (cur.get("price") or {}).get("amount"),
            "regular": (cur.get("regular") or {}).get("amount"),
            "best_shop": (cur.get("shop") or {}).get("name"),
            "cut_now": cur.get("cut"),
            "all_time_low": (low.get("price") or {}).get("amount"),
            "low_date": low.get("timestamp"),
            "n_bundles": len(g.get("bundled") or []) if isinstance(g.get("bundled"), list) else g.get("bundled"),
        })
o = pd.DataFrame(rows)
shops = pd.DataFrame([{"app_id": rev.get(g["id"]), "n_shops": len(g.get("deals", [])),
                       "steam_now": next((d["price"]["amount"] for d in g.get("deals", [])
                                          if d["shop"]["id"] == STEAM_SHOP_ID), None)} for g in prices])
o = o.merge(shops, on="app_id", how="left")
n_free = int((o.regular == 0).sum())
n_no_deal = int(o.best_shop.isna().sum())
o = o[(o.regular > 0) & o.best_shop.notna()]  # drop free games and games with no current deal data
o["gap_to_low_pct"] = ((o.best_now - o.all_time_low) / o.regular * 100).round(1)
o["at_or_near_low"] = o.gap_to_low_pct <= 5

L = [f"# IsThereAnyDeal EDA\n",
     f"- Steam app ids sent: {len(app_ids)}; matched to ITAD: {len(itad_ids)} ({len(itad_ids)/len(app_ids):.1%})",
     f"- Paid games with current prices (analyzed below): {len(o)}; dropped free: {n_free}, no current price: {n_no_deal}",
     f"- Has an all-time low recorded: {o.all_time_low.notna().mean():.1%}",
     f"- Shops per game: median {o.n_shops.median():.0f}, max {o.n_shops.max():.0f}",
     f"- Best price is NOT on Steam: {(o.best_shop != 'Steam').mean():.1%}",
     f"- Currently at or within 5% of all-time low ('buy now'): {o.at_or_near_low.mean():.1%}",
     f"- Median all-time-low discount vs regular price: {((1 - o.all_time_low / o.regular) * 100).median():.0f}%\n",
     "**Best-price shops**\n", o.best_shop.value_counts().head(10).to_frame("games").to_markdown(), "",
     "**Gap between price now and all-time low (% of regular price)**\n",
     o.gap_to_low_pct.describe(percentiles=[.25, .5, .75, .9]).round(1).to_frame().to_markdown(), ""]
(HERE / "itad_report.md").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))
