"""Global achievement unlock rates for the games in the Steam reviews collection (public endpoint, no key).
Reuses rates already fetched for the pilot. Resumable.
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python collect/global_pct.py
Out: C:/Users/juant/data_raw/steam_reviews/global_pct.jsonl  ({"app_id", "pct": {apiname: percent}})
"""
import json
import time
from pathlib import Path

import requests

OUT = Path("C:/Users/juant/data_raw/steam_reviews")
PILOT = Path("C:/Users/juant/data_clean/pilot/global_pct.jsonl")
f_out = OUT / "global_pct.jsonl"

apps = {json.loads(l)["app_id"] for l in (OUT / "achievements.jsonl").open(encoding="utf-8")}
have = {json.loads(l)["app_id"] for l in f_out.open(encoding="utf-8")} if f_out.exists() else set()
pilot = {r["app_id"]: r for r in map(json.loads, PILOT.open(encoding="utf-8"))} if PILOT.exists() else {}
todo = sorted(apps - have)
print(f"apps {len(apps)}  already {len(have)}  todo {len(todo)}  (pilot has {len(set(todo) & set(pilot))})", flush=True)

with f_out.open("a", encoding="utf-8") as f:
    for i, a in enumerate(todo):
        if a in pilot:
            f.write(json.dumps(pilot[a]) + "\n"); continue
        lst = []
        for _ in range(3):
            try:
                r = requests.get("https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/",
                                 params={"gameid": a}, timeout=25)
                if r.status_code == 429:
                    time.sleep(60); continue
                lst = ((r.json() if r.text.strip()[:1] == "{" else {}).get("achievementpercentages") or {}).get("achievements") or []
                break
            except (requests.RequestException, ValueError):
                time.sleep(5)
        f.write(json.dumps({"app_id": a, "pct": {x["name"]: float(x["percent"]) for x in lst}}) + "\n"); f.flush()
        time.sleep(0.5)
        if i % 100 == 0:
            print(f"{i + 1}/{len(todo)}", flush=True)
print("done", flush=True)
