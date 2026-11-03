"""Fetch live Steam store data for a sample of Kaggle games (no API key needed).

Usage: python eda/fetch_steam.py <dataset_dir> [n]
Writes eda/steam_sample.jsonl (one store response per game).
Steam allows roughly 200 store requests per 5 minutes, so this sleeps 1.6 s per call.
"""
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

DATA = Path(sys.argv[1])
N = int(sys.argv[2]) if len(sys.argv) > 2 else 300
OUT = Path(__file__).parent / "steam_sample.jsonl"

games = pd.read_csv(DATA / "games.csv")
# Half popular games (what users will search for), half random long-tail games.
popular = games.nlargest(2000, "user_reviews").sample(N // 2, random_state=1)
rest = games.drop(popular.index).sample(N - N // 2, random_state=1)
ids = pd.concat([popular, rest]).app_id.tolist()

done = set()
if OUT.exists():
    done = {json.loads(l)["app_id"] for l in OUT.read_text(encoding="utf-8").splitlines()}

with OUT.open("a", encoding="utf-8") as f:
    for i, app_id in enumerate(ids):
        if app_id in done:
            continue
        url = "https://store.steampowered.com/api/appdetails"
        for attempt in range(3):
            r = requests.get(url, params={"appids": app_id, "cc": "us", "l": "english"}, timeout=20)
            if r.status_code == 429:
                time.sleep(60)
                continue
            break
        body = r.json() if r.ok and r.text.strip() not in ("", "null") else None
        entry = (body or {}).get(str(app_id), {})
        f.write(json.dumps({"app_id": app_id, "http": r.status_code,
                            "success": entry.get("success", False),
                            "data": entry.get("data")}) + "\n")
        f.flush()
        if i % 25 == 0:
            print(f"{i}/{len(ids)}", flush=True)
        time.sleep(1.6)
print("done")
