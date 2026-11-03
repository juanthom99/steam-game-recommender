"""Refill user tags and regular prices for games that only FronkonGames has (data note, concerns 5 and 6).

Our Hugging Face copy of FronkonGames has an empty tags column, and its October 2026 price is often a sale price.
SteamSpy's appdetails endpoint returns both: tags with vote counts (most-voted first) and `initialprice`, the
regular price in US cents. SteamSpy asks for at most one request per second, so this runs for about a day.
It is resumable: finished app ids are skipped on restart. Recommendable games go first.

Run:  PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python collect/steamspy_refill.py
Out:  C:/Users/juant/data_raw/steamspy/appdetails.jsonl  (one JSON object per app; merged by clean/merge_steamspy.py)
"""
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

OUT = Path("C:/Users/juant/data_raw/steamspy/appdetails.jsonl")
OUT.parent.mkdir(parents=True, exist_ok=True)
URL = "https://steamspy.com/api.php?request=appdetails&appid={}"

g = pd.read_parquet("C:/Users/juant/data_clean/games.parquet", columns=["app_id", "catalog_source", "recommendable"])
todo = g[g.catalog_source == "fronkon"].sort_values("recommendable", ascending=False).app_id.tolist()
done = set()
if OUT.exists():
    done = {json.loads(l)["appid"] for l in OUT.open(encoding="utf-8") if l.strip()}
todo = [a for a in todo if a not in done]
print(f"{len(done):,} done, {len(todo):,} to go", flush=True)

with OUT.open("a", encoding="utf-8") as f:
    for i, app in enumerate(todo):
        t0 = time.time()
        for attempt in range(4):
            try:
                req = urllib.request.Request(URL.format(app), headers={"User-Agent": "steamrec-course-project"})
                d = json.load(urllib.request.urlopen(req, timeout=30))
                break
            except Exception as e:                       # network hiccup or rate limit: back off and retry
                d = {"error": str(e)[:200]}
                time.sleep(5 * (attempt + 1))
        tags = d.get("tags") or {}
        rec = {"appid": int(app), "tags": list(tags) if isinstance(tags, dict) else [],
               "tag_votes": list(tags.values()) if isinstance(tags, dict) else [],
               "initialprice": d.get("initialprice"), "price": d.get("price"), "error": d.get("error")}
        f.write(json.dumps(rec) + "\n")
        if i % 500 == 0:
            f.flush()
            print(f"{i:,}/{len(todo):,}", flush=True)
        time.sleep(max(0.0, 1.05 - (time.time() - t0)))   # SteamSpy limit: 1 request per second
