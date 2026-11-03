"""Resolve the Steam type of apps that IStoreService/GetAppList leaves out.

GetAppList omits some real, purchasable games (e.g. Half-Life 2: Episode One, Skyrim 2011), so "not in the
catalog" does not mean "delisted". This asks each app's store page instead.

Usage: python eda/resolve_types.py   (resumable; ~1.6 s per app to respect Steam's ~200 req / 5 min)
Writes eda/app_types_resolved.csv: app_id, store_success, type, name, short_description, is_free
"""
import csv
import os
import time
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
OUT = HERE / "app_types_resolved.csv"
KAGGLE = Path(os.path.expanduser("~/.cache/kagglehub/datasets/antonkozyriev/game-recommendations-on-steam/versions/28"))
MC = Path(os.path.expanduser("~/data_raw/mcauley/tidy/users_items.parquet"))

cat = set(pd.read_csv(HERE / "steam_catalog.csv", usecols=["appid"]).appid)
ids = set(pd.read_csv(KAGGLE / "games.csv", usecols=["app_id"]).app_id) - cat
if MC.exists():
    mi = pd.read_parquet(MC, columns=["app_id"]).dropna()
    ids |= set(mi.app_id.astype(int)) - cat
done = set(pd.read_csv(OUT).app_id) if OUT.exists() else set()
todo = sorted(ids - done)
print(f"unknown apps: {len(ids):,}; already resolved: {len(done):,}; to do: {len(todo):,}", flush=True)

new_file = not OUT.exists()
with OUT.open("a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    if new_file:
        w.writerow(["app_id", "store_success", "type", "name", "short_description", "is_free"])
    for i, a in enumerate(todo):
        for attempt in range(5):
            try:
                r = requests.get("https://store.steampowered.com/api/appdetails",
                                 params={"appids": a, "cc": "us", "l": "english"}, timeout=20)
                if r.status_code == 429:
                    time.sleep(60)
                    continue
                body = (r.json() or {}).get(str(a), {}) if r.text.strip() not in ("", "null") else {}
                break
            except (requests.RequestException, ValueError):
                time.sleep(10)
                body = {}
        d = body.get("data") or {}
        w.writerow([a, bool(body.get("success")), d.get("type"), d.get("name"),
                    (d.get("short_description") or "").replace("\n", " "), d.get("is_free")])
        f.flush()
        if i % 200 == 0:
            print(f"{i:,}/{len(todo):,}", flush=True)
        time.sleep(1.6)
print("done", flush=True)
