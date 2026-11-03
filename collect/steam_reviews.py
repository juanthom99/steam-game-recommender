"""Collect current Steam reviews with playtime AT REVIEW TIME, plus libraries and achievements for a sample of reviewers.

Why: Kaggle and McAuley only give playtime measured at some other time than the review. Steam's official reviews API
(IUserReviewsService/GetAppReviews) returns, per review, the author's playtime at review, playtime now,
last-two-weeks playtime, last played, and whether the game was refunded.

Per game (about 1,000 games, stratified by release era x popularity):
  1. IUserReviewsService/GetAppReviews  - one page of recent reviews (all) + one page of recent negative reviews
  2. for up to AUTHORS_PER_GAME new reviewers: IPlayerService/GetOwnedGames (full library, if public)
  3. for those public reviewers: ISteamUserStats/GetPlayerAchievements for the reviewed game

Privacy: Steam IDs never reach disk (salted SHA-256 hash only). No review text is stored (only its length).
Private profiles are recorded as not public and skipped. ~1 request/second; resumable per game.

Run:  PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python collect/steam_reviews.py [--limit N]
Out:  C:/Users/juant/data_raw/steam_reviews/{games.csv, reviews.jsonl, libraries.jsonl, achievements.jsonl}
"""
import argparse
import hashlib
import json
import secrets
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = Path("C:/Users/juant/data_raw/steam_reviews")
OUT.mkdir(parents=True, exist_ok=True)
N_GAMES, AUTHORS_PER_GAME, PAUSE, SEED = 1000, 5, 1.0, 11

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=None, help="process only the first N games of the fixed sample")
args = ap.parse_args()

KEY = next(l.split("=", 1)[1].strip() for l in (ROOT / ".env").read_text().splitlines() if l.startswith("STEAM_API_KEY="))
salt_f = OUT / ".salt"
if not salt_f.exists():
    salt_f.write_text(secrets.token_hex(16))
SALT = salt_f.read_text().strip()
H = lambda sid: hashlib.sha256((SALT + str(sid)).encode()).hexdigest()[:20]

# ------------------------------------------------------------------ game sample (fixed once, then reused)
games_f = OUT / "games.csv"
if games_f.exists():
    games = pd.read_csv(games_f)
else:
    g = pd.read_parquet("C:/Users/juant/data_clean/games.parquet",
                        columns=["app_id", "title", "release_date", "recommendable", "user_reviews", "steam_positive", "steam_negative"])
    g = g[g.recommendable].copy()
    g["n_rev"] = (g.steam_positive.fillna(0) + g.steam_negative.fillna(0)).where(lambda s: s > 0, g.user_reviews)
    g = g[g.n_rev >= 50]
    yr = pd.to_datetime(g.release_date, errors="coerce").dt.year
    g["era"] = np.select([yr < 2018, yr < 2024], ["pre-2018", "2018-2023"], "2024-2026")
    g["pop"] = g.groupby("era").n_rev.transform(lambda s: pd.qcut(s.rank(method="first"), 3, labels=["low", "mid", "high"]))
    per = int(np.ceil(N_GAMES / 9))
    games = (g.sample(frac=1, random_state=SEED).groupby(["era", "pop"], observed=True).head(per)
              [["app_id", "title", "era", "pop", "n_rev"]].reset_index(drop=True))
    games = games.sample(frac=1, random_state=SEED).reset_index(drop=True)   # interleave strata so a partial run is balanced
    games.to_csv(games_f, index=False)
games = games.head(args.limit) if args.limit else games
print(f"games in sample: {len(games):,}  " + str(games.groupby(['era', 'pop'], observed=True).size().to_dict()), flush=True)


def get(url, **params):
    for _ in range(4):
        try:
            r = requests.get(url, params=params, timeout=25)
            if r.status_code == 429:
                time.sleep(60); continue
            return r.status_code, (r.json() if r.text.strip()[:1] == "{" else {})
        except (requests.RequestException, ValueError):
            time.sleep(5)
    return None, {}


def done_games():
    f = OUT / "reviews.jsonl"
    return {json.loads(l)["app_id"] for l in f.open(encoding="utf-8")} if f.exists() else set()


def seen_authors():
    f = OUT / "libraries.jsonl"
    return {json.loads(l)["uid"] for l in f.open(encoding="utf-8")} if f.exists() else set()


finished, have = done_games(), seen_authors()
rng = np.random.default_rng(SEED)
fr, fl, fa = (open(OUT / n, "a", encoding="utf-8") for n in ("reviews.jsonl", "libraries.jsonl", "achievements.jsonl"))
for i, row in games.iterrows():
    a = int(row.app_id)
    if a in finished:
        continue
    revs, sids = {}, {}
    for review_type, rt in (("all", 0), ("negative", 2)):
        # official Web API replacement for the deprecated store /appreviews endpoint (no key: shared, lower rate limit)
        st, js = get("https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/",
                     input_json=json.dumps({"appid": a, "filter": 1, "languages": ["all"], "review_type": rt,
                                            "purchase_type": 1, "num_per_page": 100, "cursor": "*"}))
        body = js.get("response", js)
        for r in body.get("reviews") or []:
            au = r.get("author") or {}
            sid = au.get("steamid")
            if not sid or r["recommendationid"] in revs:
                continue
            uid = H(sid); sids[uid] = sid
            revs[r["recommendationid"]] = {
                "app_id": a, "rid": r["recommendationid"], "uid": uid, "page": review_type,
                "voted_up": r.get("voted_up"), "created": r.get("timestamp_created"), "updated": r.get("timestamp_updated"),
                "playtime_at_review": au.get("playtime_at_review"), "playtime_forever": au.get("playtime_forever"),
                "playtime_2w": au.get("playtime_last_two_weeks"), "last_played": au.get("last_played"),
                "num_reviews": au.get("num_reviews"), "refunded": r.get("refunded"),
                "steam_purchase": r.get("steam_purchase"), "received_for_free": r.get("received_for_free"),
                "early_access": r.get("written_during_early_access"), "votes_up": r.get("votes_up"), "language": r.get("language"),
                "review_len": len(r.get("review") or "")}
        time.sleep(PAUSE)
    # libraries + achievements for a few reviewers we haven't fetched yet (mix of positive and negative reviewers)
    cand = [v for v in revs.values() if v["uid"] not in have]
    neg = [v for v in cand if not v["voted_up"]]; pos = [v for v in cand if v["voted_up"]]
    pick = (list(rng.permutation(neg))[:2] if neg else []) + list(rng.permutation(pos))[:AUTHORS_PER_GAME]
    for v in pick[:AUTHORS_PER_GAME]:
        uid = v["uid"]
        st, js = get("https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/", key=KEY, steamid=sids[uid],
                     include_played_free_games=1, include_appinfo=0)
        lib = (js.get("response") or {}).get("games")
        fl.write(json.dumps({"uid": uid, "via_app": a, "public": lib is not None, "fetched": int(time.time()),
                             "games": [[x["appid"], x.get("playtime_forever", 0), x.get("playtime_2weeks", 0), x.get("rtime_last_played", 0)]
                                       for x in (lib or [])]}) + "\n")
        have.add(uid)
        time.sleep(PAUSE)
        if lib is not None:
            st, js = get("https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/", key=KEY, steamid=sids[uid], appid=a)
            ps = js.get("playerstats") or {}
            fa.write(json.dumps({"uid": uid, "app_id": a, "success": bool(ps.get("success")), "error": ps.get("error"),
                                 "ach": [[x["apiname"], x["achieved"], x.get("unlocktime", 0)] for x in ps.get("achievements") or []]}) + "\n")
            time.sleep(PAUSE)
    # game marker last, so a crash mid-game redoes the whole game (reviews are deduplicated by rid at analysis time)
    for v in revs.values():
        fr.write(json.dumps(v) + "\n")
    if not revs:
        fr.write(json.dumps({"app_id": a, "rid": None, "empty": True}) + "\n")
    for f in (fr, fl, fa):
        f.flush()
    if i % 25 == 0:
        print(f"game {i + 1}/{len(games)}  reviews so far ~{sum(1 for _ in open(OUT / 'reviews.jsonl', encoding='utf-8')):,}  "
              f"authors {len(have):,}", flush=True)
print("done", flush=True)
