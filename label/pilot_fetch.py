"""Pilot: fetch new engagement signals for ~2,000 McAuley reviewed (user, game) pairs from the Steam Web API.

Per user  : IPlayerService/GetOwnedGames  -> current playtime, rtime_last_played (only if game details are public)
Per pair  : ISteamUserStats/GetPlayerAchievements -> achieved flags + unlock times
Per game  : ISteamUserStats/GetGlobalAchievementPercentagesForApp -> how rare each achievement is

Privacy: Steam IDs are never written to disk; rows carry a salted SHA-256 hash. Private profiles are recorded as
'private' and skipped. ~1 request/second (well under Steam's 100k/day). Resumable.
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python label/pilot_fetch.py
"""
import hashlib
import json
import os
import secrets
import time
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = Path("C:/Users/juant/data_clean/pilot")
OUT.mkdir(exist_ok=True)
N_PAIRS, SEED, PAUSE = 10000, 7, 1.0

key = next(l.split("=", 1)[1].strip() for l in (ROOT / ".env").read_text().splitlines() if l.startswith("STEAM_API_KEY="))
salt_file = OUT / ".salt"
if not salt_file.exists():
    salt_file.write_text(secrets.token_hex(16))
SALT = salt_file.read_text().strip()
h = lambda sid: hashlib.sha256((SALT + str(sid)).encode()).hexdigest()[:20]

# ---------------------------------------------------------------- sample (extends an existing sample; same shuffle order)
pairs_path = OUT / "pairs.parquet"
m = pd.read_parquet("C:/Users/juant/data_clean/interactions_mcauley.parquet",
                    columns=["user_key", "app_id", "playtime_min", "played", "history_ok", "review_recommend"])
m = m[m.played & m.history_ok & m.review_recommend.notna()]
umap = pd.read_parquet("C:/Users/juant/data_clean/users_mcauley_map.parquet", columns=["user_key", "mc_user_id"])
mu = pd.read_parquet("C:/Users/juant/data_raw/mcauley/tidy/users.parquet", columns=["user_id", "steam_id"])
m = m.merge(umap, on="user_key").merge(mu.drop_duplicates("user_id"), left_on="mc_user_id", right_on="user_id")
m["uid"] = m.steam_id.map(h)
old = pd.read_parquet(pairs_path) if pairs_path.exists() else None
if old is not None:   # player keys come from row order in the cleaner; make sure they still point to the same people
    chk = old[["uid", "user_key"]].drop_duplicates().merge(m[["user_key", "uid"]].drop_duplicates(), on="user_key", how="left")
    assert (chk.uid_x == chk.uid_y).all(), "user_key mapping changed since the first sample"
n = m.groupby("user_key").size()
users = n[n >= 2].index.to_series().sample(frac=1, random_state=SEED)
have = set(old.user_key) if old is not None else set()
picked, total = list(have), (len(old) if old is not None else 0)
for u in users:
    if total >= N_PAIRS:
        break
    if u not in have:
        picked.append(u); total += n[u]
new = m[m.user_key.isin(picked) & ~m.user_key.isin(have)]
new = new[["uid", "user_key", "app_id", "playtime_min", "review_recommend"]].rename(columns={"playtime_min": "playtime_2017"})
pairs = pd.concat([old, new], ignore_index=True) if old is not None else new
pairs.to_parquet(pairs_path, index=False)
sid_of = dict(zip(m.uid, m.steam_id))          # in memory only
print(f"pairs {len(pairs):,}, users {pairs.uid.nunique():,}, games {pairs.app_id.nunique():,}", flush=True)


def get(url, **params):
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, timeout=20)
            if r.status_code == 429:
                time.sleep(60); continue
            return r.status_code, (r.json() if r.text.strip().startswith("{") else {})
        except (requests.RequestException, ValueError):
            time.sleep(5)
    return None, {}


def jsonl_done(path, key_fields):
    if not path.exists():
        return set()
    return {tuple(json.loads(l)[k] for k in key_fields) for l in path.open(encoding="utf-8")}


# ---------------------------------------------------------------- per user: owned games
owned_p = OUT / "owned.jsonl"
done = jsonl_done(owned_p, ["uid"])
with owned_p.open("a", encoding="utf-8") as f:
    for i, uid in enumerate(sorted(set(pairs.uid) - {d[0] for d in done})):
        st, js = get("https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/", key=key, steamid=sid_of[uid],
                     include_played_free_games=1, include_appinfo=0)
        games = (js.get("response") or {}).get("games")
        want = set(pairs.app_id[pairs.uid == uid])
        rec = {"uid": uid, "status": st, "public": games is not None,
               "games": [{"app_id": g["appid"], "playtime_now": g.get("playtime_forever"), "last_played": g.get("rtime_last_played")}
                         for g in (games or []) if g["appid"] in want],
               "n_owned_now": len(games or [])}
        f.write(json.dumps(rec) + "\n"); f.flush()
        if i % 50 == 0:
            print(f"owned {i}", flush=True)
        time.sleep(PAUSE)

public = {json.loads(l)["uid"] for l in owned_p.open(encoding="utf-8") if json.loads(l)["public"]}
print(f"public game details: {len(public):,} of {pairs.uid.nunique():,} users", flush=True)

# ---------------------------------------------------------------- per pair: achievements
ach_p = OUT / "achievements.jsonl"
done = jsonl_done(ach_p, ["uid", "app_id"])
todo = pairs[pairs.uid.isin(public)]
with ach_p.open("a", encoding="utf-8") as f:
    for i, (uid, a) in enumerate(zip(todo.uid, todo.app_id)):
        if (uid, int(a)) in done:
            continue
        st, js = get("https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/", key=key, steamid=sid_of[uid], appid=int(a))
        ps = js.get("playerstats") or {}
        f.write(json.dumps({"uid": uid, "app_id": int(a), "status": st, "success": bool(ps.get("success")),
                            "error": ps.get("error"),
                            "ach": [{"n": x["apiname"], "a": x["achieved"], "t": x.get("unlocktime", 0)} for x in ps.get("achievements") or []]}) + "\n")
        f.flush()
        if i % 100 == 0:
            print(f"achievements {i}/{len(todo)}", flush=True)
        time.sleep(PAUSE)

# ---------------------------------------------------------------- per game: global rarity
glob_p = OUT / "global_pct.jsonl"
done = jsonl_done(glob_p, ["app_id"])
with glob_p.open("a", encoding="utf-8") as f:
    for a in sorted(set(todo.app_id.astype(int)) - {d[0] for d in done}):
        st, js = get("https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/", gameid=a)
        lst = (js.get("achievementpercentages") or {}).get("achievements") or []
        f.write(json.dumps({"app_id": a, "pct": {x["name"]: float(x["percent"]) for x in lst}}) + "\n"); f.flush()
        time.sleep(PAUSE / 2)
print("done", flush=True)
