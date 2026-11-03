"""Fetch Steam's full app catalog by type with IStoreService/GetAppList (needs STEAM_API_KEY).

Usage: python eda/fetch_steam_catalog.py
Writes eda/steam_catalog.csv (appid, name, type, last_modified) and
eda/steam_my_library.csv (the key owner's own owned games, for profiling the live input shape).
"""
from pathlib import Path

import os
import pandas as pd
import requests
from dotenv import dotenv_values

HERE = Path(__file__).resolve().parent
KEY = dotenv_values(HERE.parent / ".env")["STEAM_API_KEY"]
URL = "https://api.steampowered.com/IStoreService/GetAppList/v1/"
TYPES = ["games", "dlc", "software", "videos", "hardware"]

rows = []
for t in TYPES:
    last = 0
    while True:
        params = {"key": KEY, "max_results": 50000, "last_appid": last, **{f"include_{x}": int(x == t) for x in TYPES}}
        r = requests.get(URL, params=params, timeout=60)
        r.raise_for_status()
        resp = r.json().get("response", {})
        apps = resp.get("apps", [])
        rows += [{"appid": a["appid"], "name": a.get("name", ""), "type": t.rstrip("s") if t != "software" else t,
                  "last_modified": a.get("last_modified")} for a in apps]
        if not resp.get("have_more_results"):
            break
        last = resp["last_appid"]
    print(t, sum(1 for x in rows if x["type"].startswith(t[:4])), flush=True)

cat = pd.DataFrame(rows)
cat["last_modified"] = pd.to_datetime(cat.last_modified, unit="s")
cat.to_csv(HERE / "steam_catalog.csv", index=False)
print("catalog rows:", len(cat))

# The key owner's own library: the exact shape a live user brings.
SID = os.environ["STEAM_ID"]   # your own 64-bit Steam ID; never commit it
r = requests.get("https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/",
                 params={"key": KEY, "steamid": SID, "include_appinfo": 1, "include_played_free_games": 1}, timeout=30)
games = r.json()["response"].get("games", [])
lib = pd.DataFrame(games)
keep = [c for c in ["appid", "name", "playtime_forever", "playtime_2weeks", "rtime_last_played",
                    "playtime_windows_forever", "playtime_mac_forever", "playtime_linux_forever",
                    "playtime_deck_forever", "playtime_disconnected", "has_community_visible_stats"] if c in lib]
lib = lib[keep]
if "rtime_last_played" in lib:
    lib["rtime_last_played"] = pd.to_datetime(lib.rtime_last_played.replace(0, pd.NA), unit="s")
lib.to_csv(HERE / "steam_my_library.csv", index=False)
print("library rows:", len(lib))
