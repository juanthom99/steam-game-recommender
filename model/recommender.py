"""Recommendation engine: Steam library in, two rows of explained picks out.

Used by model/recommend.py (command line) and app/server.py (local web page).
- Enjoyment of each owned game = the player's playtime percentile among that game's players (stored quantiles).
- The player's taste vector is solved from the trained ALS item factors (same equation as training).
- "For you": top scores among recommendable, unowned games. "Try something new": the top 400 reranked by
  z(score) + 4 x tag distance from the player's profile. Every pick names the owned games that pushed it up most.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "model" / "artifacts"
D = Path("C:/Users/juant/data_clean")
STEAM = "https://api.steampowered.com"


def _key():
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("STEAM_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("STEAM_API_KEY missing from .env")


# ------------------------------------------------------------------ Steam lookups
class SteamError(Exception):
    pass


def resolve_steamid(text):
    """Accepts a 17-digit SteamID64, a profile URL (/profiles/<id> or /id/<name>), or a custom profile name."""
    t = (text or "").strip().rstrip("/")
    m = re.search(r"/profiles/(\d{17})", t)
    if m:
        return m.group(1)
    if re.fullmatch(r"7656\d{13}", t):
        return t
    m = re.search(r"/id/([^/?#]+)", t)
    name = m.group(1) if m else t
    if not re.fullmatch(r"[A-Za-z0-9_-]{2,64}", name):
        raise SteamError("That doesn't look like a Steam ID, profile link or custom profile name.")
    r = requests.get(f"{STEAM}/ISteamUser/ResolveVanityURL/v1/", params={"key": _key(), "vanityurl": name}, timeout=20).json()
    sid = (r.get("response") or {}).get("steamid")
    if not sid:
        raise SteamError(f"No Steam profile found for '{name}'. Try the profile link or the 17-digit Steam ID.")
    return sid


def fetch_profile(steamid):
    """Returns (summary dict, library list of (app_id, playtime_min, name)). Library is None when game details are private."""
    s = requests.get(f"{STEAM}/ISteamUser/GetPlayerSummaries/v2/", params={"key": _key(), "steamids": steamid}, timeout=20).json()
    p = ((s.get("response") or {}).get("players") or [{}])[0]
    summary = {"name": p.get("personaname"), "url": p.get("profileurl"), "avatar": p.get("avatarmedium"), "public": p.get("communityvisibilitystate") == 3,
               "country": p.get("loccountrycode")}
    r = requests.get(f"{STEAM}/IPlayerService/GetOwnedGames/v1/",
                     params={"key": _key(), "steamid": steamid, "include_appinfo": 1, "include_played_free_games": 1},
                     timeout=30).json()
    games = (r.get("response") or {}).get("games")
    lib = None if games is None else [(int(g["appid"]), int(g.get("playtime_forever", 0)), g.get("name")) for g in games]
    return summary, lib


# tags that describe format or business model, not taste: never shown as "new for you" or used for the taste profile
BROAD = {"Singleplayer", "Multiplayer", "Indie", "Free to Play", "Early Access", "Great Soundtrack", "Co-op", "Online Co-Op",
         "PvP", "Massively Multiplayer", "Controller", "Moddable", "Classic", "Remake", "Remaster", "Female Protagonist",
         "Steam Achievements", "Family Friendly", "Masterpiece", "Addictive", "Replay Value", "Difficult", "Short",
         "Beautiful", "Funny", "Cute", "Colorful", "Relaxing", "Utilities", "Software"}
NOT_NEW = {"3D", "2D", "Third Person", "First-Person", "Atmospheric", "Story Rich", "Open World", "Sandbox", "Fantasy",
           "Sci-fi", "Shooter", "Puzzle", "Platformer", "Pixel Graphics", "Retro", "Violent", "Gore", "Dark", "Exploration",
           "Character Customization", "Multiple Endings", "Choices Matter", "Anime", "Realistic", "Comedy",
           "Casual", "Action", "Adventure", "Simulation", "Strategy", "RPG"}
BROAD = {t.lower() for t in BROAD}
NOT_NEW = {t.lower() for t in NOT_NEW}


def live_prices(app_ids, cc="us"):
    """Current Steam store price for each app (one request for the batch). {app_id: {final, initial, discount, text}}."""
    out = {}
    for k in range(0, len(app_ids), 50):
        chunk = [str(a) for a in app_ids[k:k + 50]]
        try:
            r = requests.get("https://store.steampowered.com/api/appdetails",
                             params={"appids": ",".join(chunk), "filters": "price_overview", "cc": cc}, timeout=15).json()
        except (requests.RequestException, ValueError):
            continue
        for a in chunk:
            v = (r or {}).get(a) or {}
            if not v.get("success"):
                continue
            p = v.get("data") or {}
            po = p.get("price_overview") if isinstance(p, dict) else None
            out[int(a)] = ({"final": po["final"] / 100, "initial": po["initial"] / 100, "discount": po.get("discount_percent", 0),
                            "text": po.get("final_formatted")} if po else {"final": None, "initial": None, "discount": 0, "text": None})  # free or not sold
    return out


# ------------------------------------------------------------------ model
class Recommender:
    def __init__(self):
        z = np.load(A / "als.npz")
        self.Y = z["item_factors"].astype(np.float64)
        alpha, factors, reg, _, _ = z["params"]
        self.alpha, self.reg = float(alpha), float(reg)
        self.app_ids = z["app_ids"]
        self.idx = {int(a): i for i, a in enumerate(self.app_ids)}
        self.YtY = self.Y.T @ self.Y
        it = pd.read_parquet(A / "items.parquet")
        self.q = {int(a): np.asarray(q) for a, q in zip(it.app_id, it.q) if q is not None}
        g = pd.read_parquet(D / "games.parquet", columns=["app_id", "title", "tags", "genres", "price_regular", "recommendable",
                                                          "header_image", "release_date", "steam_positive", "steam_negative",
                                                          "positive_ratio", "user_reviews", "adult", "kaggle_price_regular", "price_source"])
        g = g.set_index("app_id")
        self.games = g
        pos, neg = g.steam_positive.fillna(0), g.steam_negative.fillna(0)
        n = pos + neg
        self.rating = ((pos / n.where(n > 0)).fillna(g.positive_ratio / 100)).reindex(self.app_ids).to_numpy()
        self.n_reviews = n.where(n > 0, g.user_reviews).reindex(self.app_ids).fillna(0).to_numpy()
        # regular-price estimate for when the store can't be reached: Steam regular price (G24), else the older sources
        self.est_price = g.price_regular.where(g.price_source.eq("itad_steam_regular"),   # rule G24
                                               g[["price_regular", "kaggle_price_regular"]].max(axis=1)).reindex(self.app_ids).to_numpy(float)
        rec = g.recommendable.reindex(self.app_ids).fillna(False).to_numpy(bool)
        # actionable picks only: on sale in the store, not adult, and not poorly rated
        self.candidate = rec & ~((self.rating < 0.65) & (self.n_reviews >= 50)) & (self.n_reviews >= 20)
        # user tags; ~11% of games have none in our sources, so fall back to store genres
        self.tags = {int(a): [x for x in (list(t) if t is not None and len(t) else list(ge) if ge is not None else [])
                              if x.lower() not in BROAD][:5] for a, t, ge in zip(g.index, g.tags, g.genres)}
        self.titles = g.title.to_dict()
        self.search_titles = g[g.recommendable | g.index.isin(list(self.idx))].title.dropna()

    # ---- enjoyment of an owned game
    def enjoyment(self, app_id, playtime_min):
        q = self.q.get(app_id)
        if q is None:
            return 0.5 if playtime_min >= 120 else 0.25
        return float(np.searchsorted(q, playtime_min, side="right")) / len(q)

    def taste(self, library):
        """library: list of (app_id, playtime_min). Returns (user vector, used rows [(idx, confidence, app_id, g)])."""
        rows = []
        for a, pt in library:
            i = self.idx.get(a)
            if i is None or pt <= 0:
                continue
            g = self.enjoyment(a, pt)
            rows.append((i, 1 + self.alpha * g, a, g))
        if not rows:
            return None, []
        Yu = self.Y[[r[0] for r in rows]]
        c = np.array([r[1] for r in rows])
        Amat = self.YtY + self.reg * np.eye(self.Y.shape[1]) + (Yu * (c - 1)[:, None]).T @ Yu
        b = (Yu * c[:, None]).sum(0)
        self._W = np.linalg.inv(Amat)
        return self._W @ b, rows

    def _why(self, j, rows, n=2):
        Yu = self.Y[[r[0] for r in rows]]
        contrib = np.array([r[1] for r in rows]) * (Yu @ (self._W @ self.Y[j]))
        top = np.argsort(-contrib)[:n]
        return [self.titles.get(rows[k][2], str(rows[k][2])) for k in top if contrib[k] > 0]

    def _card(self, j, score, rows, prices, extra=None):
        a = int(self.app_ids[j])
        g = self.games.loc[a] if a in self.games.index else None
        lp = prices.get(a)
        if lp and lp["final"] is not None:
            price = {"price": lp["final"], "price_initial": lp["initial"], "discount": lp["discount"], "price_text": lp["text"]}
        elif lp:                                    # store lists no price: free if our catalog says so, else check the store
            free = self.est_price[j] == 0
            price = {"price": 0.0 if free else None, "price_initial": None, "discount": 0, "price_text": "Free" if free else "See store"}
        else:                                       # store unreachable: last known regular price, marked approximate
            est = None if np.isnan(self.est_price[j]) else float(self.est_price[j])
            price = {"price": est, "price_initial": est, "discount": 0,
                     "price_text": None if est is None else ("Free" if est == 0 else f"~${est:.2f}")}
        card = {"app_id": a, "title": self.titles.get(a, str(a)), "score": round(float(score), 4),
                "because": self._why(j, rows), "tags": self.tags.get(a, [])[:4], **price,
                "rating": None if np.isnan(self.rating[j]) else round(float(self.rating[j]) * 100),
                "reviews": int(self.n_reviews[j]),
                "image": None if g is None or pd.isna(g.header_image) else g.header_image,
                "store_url": f"https://store.steampowered.com/app/{a}/"}
        card.update(extra or {})
        return card

    def recommend(self, library, owned=None, n=10, max_price=None, cc="us"):
        """library: (app_id, playtime_min) pairs; owned: every owned app_id (also excluded from picks).
        max_price is checked against the live store price (in the store currency for country cc)."""
        x, rows = self.taste(library)
        if x is None:
            return None
        s = self.Y @ x
        mask = self.candidate.copy()
        for a in set(owned or []) | {a for a, _ in library}:
            i = self.idx.get(a)
            if i is not None:
                mask[i] = False
        s = np.where(mask, s, -np.inf)
        order = [j for j in np.argsort(-s)[:600] if np.isfinite(s[j])]
        prices = {}
        if max_price is not None:
            head = order[:150]
            prices = live_prices([int(self.app_ids[j]) for j in head], cc)
            def ok(j):
                lp = prices.get(int(self.app_ids[j]))
                v = lp["final"] if lp and lp["final"] is not None else self.est_price[j]
                return not (v > max_price)
            order = [j for j in head if ok(j)] + [j for j in order[150:] if not (self.est_price[j] > max_price)]
        top = order[:n + 10]                        # spares, in case some turn out not to be on sale

        # taste profile over tags, weighted by enjoyment, for the "Try something new" row
        prof = {}
        for _, _, a, g in rows:
            for t in self.tags.get(a, [])[:3]:
                prof[t] = prof.get(t, 0) + g
        tot = sum(prof.values()) or 1
        prof = {t: v / tot for t, v in prof.items()}
        top_tags = [t for t in sorted(prof, key=prof.get, reverse=True) if t.lower() not in NOT_NEW][:5] or sorted(prof, key=prof.get, reverse=True)[:5]
        # soft rerank of the top 400: z(score) + 4 x tag distance (1 - cosine to the profile). Chosen post hoc on
        # validation players (eval/diagnosis_report.md): 93% of For you's NDCG@10 with wider tags than the old filter.
        new = []
        if prof:
            pool = [j for j in order[:400] if j not in set(top[:n])]          # never repeat a For you pick
            norm = np.sqrt(sum(v * v for v in prof.values()))
            def dist(j):
                tg = self.tags.get(int(self.app_ids[j]), [])[:3]
                return 1 - sum(prof.get(t, 0) for t in tg) / (np.sqrt(len(tg)) * norm) if tg else 0.0
            if pool:
                sc = np.array([s[j] for j in pool])
                z = (sc - sc.mean()) / (sc.std() + 1e-9)
                d = np.array([dist(j) for j in pool])
                for k in np.argsort(-(z + 4.0 * d), kind="stable")[:n + 5]:
                    j = pool[k]
                    fresh = sorted((t for t in self.tags.get(int(self.app_ids[j]), [])[:3] if t.lower() not in NOT_NEW),
                                   key=lambda t: prof.get(t, 0))
                    new.append((j, fresh[0] if fresh and prof.get(fresh[0], 0) < 0.05 else None))
        need = [int(self.app_ids[j]) for j in top + [j for j, _ in new] if int(self.app_ids[j]) not in prices]
        prices.update(live_prices(need, cc))
        if prices:                                  # drop delisted / unbuyable games (only when the store answered)
            def buyable(j):
                lp = prices.get(int(self.app_ids[j]))
                return lp is not None and (lp["final"] is not None or self.est_price[j] == 0)
            top = [j for j in top if buyable(j)]
            new = [(j, t) for j, t in new if buyable(j)]
        top = top[:n]
        new = [(j, t) for j, t in new if j not in set(top)][:n]
        played = sorted(rows, key=lambda r: -r[3])
        return {"for_you": [self._card(j, s[j], rows, prices) for j in top],
                "try_new": [self._card(j, s[j], rows, prices, {"new_tag": t}) for j, t in new], "top_tags": top_tags,
                "n_owned": len(set(owned or []) | {a for a, _ in library}), "n_used": len(rows),
                "favorites": [self.titles.get(r[2], str(r[2])) for r in played[:5]]}

    def search(self, text, n=8):
        t = text.strip().lower()
        if len(t) < 2:
            return []
        hit = self.search_titles[self.search_titles.str.lower().str.contains(re.escape(t))]
        hit = hit.loc[sorted(hit.index, key=lambda a: (-self.n_reviews[self.idx[a]] if a in self.idx else 0))][:n * 2]
        hit = hit[~hit.str.lower().duplicated()][:n]           # duplicate catalog rows: keep the most-reviewed
        return [{"app_id": int(a), "title": ti} for a, ti in hit.items()]


@lru_cache(maxsize=1)
def get():
    return Recommender()


def for_profile(text, n=10, max_price=None):
    """Full pipeline for a Steam ID / link / name. Raises SteamError with a user-facing message."""
    sid = resolve_steamid(text)
    summary, lib = fetch_profile(sid)
    who = f"Found the account '{summary['name']}' ({summary['url']}). " if summary.get("name") else ""
    if lib is None:
        raise SteamError(who + "Its game details are private. If that's not you: a Steam display name isn't unique, so paste "
                         "your profile link instead (Steam > your name > Profile, then copy the address). If it is you: "
                         "Profile > Edit Profile > Privacy Settings > set 'Game details' to Public. Or pick a few favourite games below.")
    played = [(a, pt) for a, pt, _ in lib if pt > 0]
    if not played:
        raise SteamError(who + "It shows no playtime. In Privacy Settings, untick 'Always keep my total playtime private', "
                         "or pick a few favourite games below.")
    out = get().recommend(played, owned=[a for a, _, _ in lib], n=n, max_price=max_price, cc=(summary["country"] or "us").lower())
    if out is None:
        raise SteamError("None of the games on this profile are in our data yet. Pick a few favourite games instead.")
    out["player"] = {"name": summary["name"], "avatar": summary["avatar"]}
    return out


def for_favorites(app_ids, n=10, max_price=None):
    """Fallback for private or empty profiles: treat each picked game as one the player loved."""
    r = get()
    lib = [(int(a), float(r.q[int(a)][90]) if int(a) in r.q else 6000) for a in app_ids]
    out = r.recommend(lib, owned=[a for a, _ in lib], n=n, max_price=max_price)
    if out is None:
        raise SteamError("None of those games are in our data yet. Try more popular titles.")
    return out


if __name__ == "__main__":
    print(json.dumps(get().search("hades"), indent=1))
