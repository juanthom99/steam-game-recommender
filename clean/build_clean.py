"""Clean every source into analysis-ready tables, with a logged rule for every change.

Run with the ML venv:
  C:/Users/juant/.venvs/steamrec-ml/Scripts/python clean/build_clean.py
Inputs : Kaggle (kagglehub cache), McAuley tidy parquet (eda/profile_mcauley.py), Steam catalog (eda/steam_catalog.csv)
Outputs: C:/Users/juant/data_clean/*.parquet  +  clean/cleaning_report.md

Principles
- Never silently drop: every rule records rows affected and its reason.
- Raw values are kept next to cleaned ones when the fix is a judgment call (e.g. title_raw).
- Statistics that depend on the train/test split (per-game caps, percentiles, popularity) are NOT applied here;
  rows are only *flagged*, and the model pipeline computes those statistics on training data.
- Reviews (recommend flags) are kept in their own columns for Layer 1 validation only, never as training signal.
"""
import ast
import gzip
import html
import os
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
KAGGLE = Path(os.path.expanduser("~/.cache/kagglehub/datasets/antonkozyriev/game-recommendations-on-steam/versions/28"))
MC = Path(os.path.expanduser("~/data_raw/mcauley"))
OUT = Path(os.path.expanduser("~/data_clean"))
OUT.mkdir(exist_ok=True)
CRAWL_DATE_MC = pd.Timestamp("2017-12-31")  # McAuley Australian crawl (late 2017); used only for sanity checks
LOG = []


def rule(rid, source, desc, n, action, why):
    LOG.append({"id": rid, "source": source, "rule": desc, "rows affected": int(n), "action": action, "why": why})
    print(f"[{rid}] {desc}: {int(n):,}", flush=True)


def norm_title(t):
    raw = unicodedata.normalize("NFKC", str(t))
    t = re.sub(r"[\u2122\u00ae\u00a9\ufffd]", "", raw)        # TM (R) (C) and the encoding replacement char
    t = re.sub(r"[^\w\s]", " ", t.lower())
    t = re.sub(r"\s+", " ", t).strip()
    return t or raw.strip().lower()   # punctuation-only titles keep their symbols, else they all collide


HIDDEN = re.compile(r"[\x00-\x08\x0b-\x1f\x7f\u200b-\u200f\u2028\u2029\ufeff]")


def clean_text(s):
    """Decode HTML entities (&amp; -> &) and remove control / zero-width characters."""
    if not isinstance(s, str):
        return s
    s = html.unescape(html.unescape(s))       # some strings are double-escaped (&amp;amp;)
    s = HIDDEN.sub("", s)
    return re.sub(r"\s+", " ", s).strip() or None


ADULT_TAGS = {"Sexual Content", "Nudity", "NSFW", "Hentai"}
HISTORY_TYPES = {"game", "unknown", "removed", "mod", "demo", "episode"}   # things people play; their playtime reflects taste


TOOL_RE = re.compile(r"\b(test(?! drive)|beta|playtest|dedicated server|sdk|patch testing|benchmark|editor|mod tools?)\b", re.I)


def build_type_map():
    """app_id -> type. Order: Steam catalog (GetAppList), then store-page lookups (eda/resolve_types.py).
    GetAppList omits some real games, so absence from it is NOT evidence of delisting."""
    cat = pd.read_csv(ROOT / "eda" / "steam_catalog.csv", usecols=["appid", "type"]).drop_duplicates("appid")
    tm = dict(zip(cat.appid, cat.type))
    res_path = ROOT / "eda" / "app_types_resolved.csv"
    n_res = 0
    if res_path.exists():
        res = pd.read_csv(res_path)
        for a, ok, t in zip(res.app_id, res.store_success, res.type):
            if a not in tm:
                tm[a] = t if ok and isinstance(t, str) else "removed"
                n_res += 1
    return tm, n_res


TYPE_MAP, N_RESOLVED = build_type_map()


def app_type(app_id, name=None):
    t = TYPE_MAP.get(app_id)
    if t and t not in ("removed", "unknown"):
        return t
    if isinstance(name, str) and TOOL_RE.search(name):   # test/beta builds have no store page either; not "removed games"
        return "tool"          # test/beta/server builds with no store page
    if t:
        return t
    return "unknown"           # not yet resolved: kept for training, not recommended


def read_loose(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield ast.literal_eval(line)


# =========================================================================== GAMES (unified catalog)
g = pd.read_csv(KAGGLE / "games.csv", parse_dates=["date_release"])
meta = pd.read_json(KAGGLE / "games_metadata.json", lines=True)
g = g.merge(meta, on="app_id", how="left", validate="1:1")
n0 = len(g)

g["title_raw"] = g.title
bad = g.title.str.contains("\ufffd")
g["title"] = g.title.str.replace("\ufffd", "", regex=False).str.replace(r"\s+", " ", regex=True).str.strip()
rule("G1", "Kaggle games", "Titles containing the encoding replacement char (lost ™/®/’)", bad.sum(),
     "removed the char; raw kept in title_raw", "broken characters hurt text search and title matching")
ws = g.title_raw.str.strip() != g.title_raw
rule("G2", "Kaggle games", "Titles with leading/trailing whitespace", ws.sum(), "stripped", "consistency")
g["title_norm"] = g.title.map(norm_title)

pm = (g.price_original == 0) & (g.price_final > 0)
g["kaggle_price_regular"] = g.price_original.where(~pm, g.price_final)
g["kaggle_price_final"] = g.price_final
g["price_original_was_missing"] = pm
rule("G3", "Kaggle games", "price_original = 0 on a paid game (missing-value code)", pm.sum(),
     "regular price := price_final; flagged", "otherwise the game looks free or 'discounted above list'")
g["kaggle_discount"] = g.discount
g = g.drop(columns=["price_final", "price_original", "discount"])

const = [c for c in ["steam_deck", "win"] if c in g and g[c].nunique() == 1]
rule("G4", "Kaggle games", f"Constant columns dropped: {const or 'none'}", n0 if const else 0, "dropped", "no information")
g = g.drop(columns=const)

g["description"] = g.description.fillna("").str.strip()
empty = g.description == ""
g["description"] = g.description.mask(empty)
g["description_source"] = np.where(empty, "none", "kaggle")
rule("G5", "Kaggle games", "Empty descriptions", empty.sum(), "set to null; description_source = none (Steam backfill later)",
     "an empty string is missing data, not a short description")

g["tags"] = g.tags.apply(lambda t: [x.strip() for x in t] if isinstance(t, list) else [])
g["n_tags"] = g.tags.apply(len)
rule("G6", "Kaggle games", "Games with no tags", (g.n_tags == 0).sum(), "kept; n_tags = 0",
     "content side falls back to title/description for these")

cat = pd.read_csv(ROOT / "eda" / "steam_catalog.csv", parse_dates=["last_modified"]).drop_duplicates("appid")
g = g.merge(cat.drop(columns=["type"]).rename(columns={"appid": "app_id", "name": "steam_name",
                                                        "last_modified": "steam_last_modified"}), on="app_id", how="left")
in_cat = g.app_id.isin(cat.appid)
# No name rule here: these apps have a Kaggle store row, so a title like "The Penguin IQ Test" is a real product.
g["item_type"] = [app_type(a) for a in g.app_id]
rule("G7", "Kaggle games", "Missing from Steam's GetAppList (which omits some real games)", (~in_cat).sum(),
     f"type taken from store-page lookups ({N_RESOLVED:,} resolved so far) or left 'unknown'",
     "e.g. Half-Life 2: Episode One is missing from GetAppList but is on sale")
g["delisted"] = g.item_type == "removed"
rule("G8", "Kaggle games", "Store page no longer exists (removed)", g.delisted.sum(),
     "kept; delisted = True (train on it, never recommend it)", "users still own and play removed games")
rule("G8b", "Kaggle games", "Typed as non-game (dlc/software/video/hardware/tool)",
     (~g.item_type.isin(["game", "unknown", "removed"])).sum(), "kept; item_type set",
     "the app hides non-games by default; their playtime is still a taste signal")
rule("G8c", "Kaggle games", "Type still unknown (pending store lookup)", (g.item_type == "unknown").sum(),
     "kept; re-run after eda/resolve_types.py finishes", "transparent about what is unresolved")

dup = g.duplicated("title_norm", keep=False)
g["dup_title"] = dup
rule("G9", "Kaggle games", "Games sharing a normalized title with another app", dup.sum(), "kept; dup_title = True",
     "remasters and regional editions are different apps; flag so search can group them")

mg = pd.read_parquet(MC / "tidy" / "steam_games.parquet")
mg = mg.dropna(subset=["app_id"]).drop_duplicates("app_id")
mg["app_id"] = mg.app_id.astype("int64")
keep = [c for c in ["app_id", "developer", "publisher", "specs", "early_access", "genres"] if c in mg]
g = g.merge(mg[keep].rename(columns={"genres": "mc_genres"}), on="app_id", how="left")
rule("G10", "McAuley steam_games", "Kaggle games enriched with developer/publisher/specs", g.developer.notna().sum(),
     "joined on app_id", "specs (co-op, controller…) and developer are useful content features")

g = g.rename(columns={"date_release": "release_date"})
g["catalog_source"] = "kaggle"

# =========================================================================== FRONKONGAMES (fresh catalog, Oct 2026)
FR = Path(os.path.expanduser("~/data_raw/fronkon/games.parquet"))
if FR.exists():
    f = pd.read_parquet(FR)
    f["app_id"] = pd.to_numeric(f.appID, errors="coerce").astype("int64")
    f = f.drop_duplicates("app_id")

    def as_tags(v):
        if isinstance(v, dict):
            return [k for k, _ in sorted(v.items(), key=lambda kv: -(kv[1] or 0))]
        if isinstance(v, (list, np.ndarray)):
            return [str(x).strip() for x in v]
        return []

    def as_list(v):
        return [str(x) for x in v] if isinstance(v, (list, np.ndarray)) else []

    strip_html = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip() if isinstance(s, str) else ""
    f["f_desc"] = f.short_description.map(strip_html)
    f.loc[f.f_desc == "", "f_desc"] = f.detailed_description.map(strip_html).str.slice(0, 600)
    f["f_tags"] = f.tags.map(as_tags)
    f["f_release"] = pd.to_datetime(f.release_date, errors="coerce", format="mixed")
    for c in ("median_playtime_forever", "average_playtime_forever"):
        f[c] = f[c].where(f[c] > 0)                        # 0 = not available (SteamSpy gap), not zero playtime
    owners = f.estimated_owners.str.extract(r"(\d[\d,]*)\s*-\s*(\d[\d,]*)")
    f["owners_lo"] = pd.to_numeric(owners[0].str.replace(",", ""), errors="coerce")
    f["owners_hi"] = pd.to_numeric(owners[1].str.replace(",", ""), errors="coerce")
    rule("F1", "FronkonGames", "Zero median/average playtime (SteamSpy has no data)", int(f.median_playtime_forever.isna().sum()),
         "set to null", "0 here means unknown, not unplayed")
    extra_cols = {"genres": "genres", "categories": "categories", "developers": "f_developers", "publishers": "f_publishers",
                  "header_image": "header_image", "median_playtime_forever": "steamspy_median_playtime_min",
                  "average_playtime_forever": "steamspy_avg_playtime_min", "positive": "steam_positive",
                  "negative": "steam_negative", "owners_lo": "owners_lo", "owners_hi": "owners_hi",
                  "price": "fronkon_price", "peak_ccu": "peak_ccu", "achievements": "achievements"}
    fx = f[["app_id"] + list(extra_cols)].rename(columns=extra_cols)
    for c in ("genres", "categories", "f_developers", "f_publishers"):
        fx[c] = fx[c].map(as_list)
    g = g.merge(fx, on="app_id", how="left")
    both = g.app_id.isin(f.app_id)
    g.loc[both, "catalog_source"] = "both"

    fd = f.set_index("app_id")
    fill_d = g.description.isna() & both & g.app_id.map(fd.f_desc).fillna("").ne("")
    g.loc[fill_d, "description"] = g.loc[fill_d, "app_id"].map(fd.f_desc)
    g.loc[fill_d, "description_source"] = "fronkon"
    rule("F2", "FronkonGames", "Empty Kaggle descriptions filled from Fronkon short_description", fill_d.sum(),
         "filled; description_source = fronkon", "more text for search and the content side")
    fill_t = (g.n_tags == 0) & both & g.app_id.map(fd.f_tags.map(len)).fillna(0).gt(0)
    g.loc[fill_t, "tags"] = g.loc[fill_t, "app_id"].map(fd.f_tags)
    g["n_tags"] = g.tags.apply(len)
    rule("F3", "FronkonGames", "Kaggle games with no tags given Fronkon tags", fill_t.sum(), "filled", "content features")
    unk_fix = g.item_type.eq("unknown") & both
    g.loc[unk_fix, "item_type"] = "game"
    rule("F4", "FronkonGames", "Kaggle items of unknown type that Fronkon lists as games", unk_fix.sum(),
         "item_type = game", "Fronkon is a games-only store crawl")

    fo = f[~f.app_id.isin(g.app_id)]
    newrows = pd.DataFrame({
        "app_id": fo.app_id, "title": fo.name.fillna("").str.strip(), "title_raw": fo.name,
        "release_date": fo.f_release, "rating": None,
        "positive_ratio": (100 * fo.positive / (fo.positive + fo.negative).replace(0, np.nan)).round(),
        "user_reviews": (fo.positive + fo.negative), "mac": fo.mac, "linux": fo.linux,
        "description": fo.f_desc.where(fo.f_desc != ""), "tags": fo.f_tags,
        "description_source": np.where(fo.f_desc != "", "fronkon", "none"),
        "item_type": [TYPE_MAP.get(a, "game") for a in fo.app_id], "catalog_source": "fronkon",
    })
    newrows["title_norm"] = newrows.title.map(norm_title)
    newrows["n_tags"] = newrows.tags.apply(len)
    newrows["delisted"] = newrows.item_type == "removed"
    newrows = newrows.merge(fx, on="app_id", how="left")
    g = pd.concat([g, newrows], ignore_index=True)
    rule("F5", "FronkonGames", "Games added that Kaggle lacks (incl. 2024–2026 releases)", len(newrows),
         "appended; catalog_source = fronkon", "coverage for 'anyone with a Steam account'")
    rule("F6", "FronkonGames", "Added games with no description and no tags", int(((newrows.description.isna()) & (newrows.n_tags == 0)).sum()),
         "kept; content side has only the title", "flag weak content rows")

# ---------------------------------------------------------------- McAuley-only apps (so every interaction joins)
mc_names = (pd.read_parquet(MC / "tidy" / "users_items.parquet", columns=["app_id", "item_name"])
            .dropna(subset=["app_id"]).astype({"app_id": "int64"}).drop_duplicates("app_id"))
mo = mc_names[~mc_names.app_id.isin(g.app_id)]
mrows = pd.DataFrame({"app_id": mo.app_id, "title": mo.item_name, "title_raw": mo.item_name,
                      "item_type": [app_type(a, n) for a, n in zip(mo.app_id, mo.item_name)],   # name rule allowed here
                      "catalog_source": "mcauley", "description_source": "none"})
mrows["tags"] = [[] for _ in range(len(mrows))]
mrows["n_tags"] = 0
mrows["title_norm"] = mrows.title.map(norm_title)
mrows["delisted"] = mrows.item_type == "removed"
g = pd.concat([g, mrows], ignore_index=True)
rule("G13", "McAuley items", "Owned apps in no catalog (test/beta builds, delisted games)", len(mrows),
     "added as name-only rows; catalog_source = mcauley; never recommended",
     "every interaction must join to a catalog row; " + ", ".join(f"{k} {v:,}" for k, v in mrows.item_type.value_counts().items()))

# ---------------------------------------------------------------- text cleanup
t_before, d_before = g.title.copy(), g.description.copy()
g["title"] = g.title.map(clean_text)
g["description"] = g.description.map(clean_text)
rule("G14", "Catalog", "Titles with HTML entities or hidden characters", int((t_before.fillna("") != g.title.fillna("")).sum()),
     "decoded / removed (title_raw kept)", "'Fish &amp; Ships' must read 'Fish & Ships' in search and on screen")
rule("G15", "Catalog", "Descriptions with HTML entities or hidden characters",
     int((d_before.fillna("") != g.description.fillna("")).sum()), "decoded / removed", "clean text for embeddings")
g["title_norm"] = g.title.map(norm_title)

# ---------------------------------------------------------------- playtests
pt = g.title.fillna("").str.contains(r"(?i)\bplaytest\b") & g.item_type.isin(["game", "unknown"])
g.loc[pt, "item_type"] = "playtest"
rule("G16", "Catalog", "Steam Playtest apps (separate app ids for test builds)", pt.sum(), "item_type = playtest",
     "a playtest is not something to recommend or buy")

# ---------------------------------------------------------------- adult content
# Steam's 18+ age gate also covers violent M-rated games (Dragon Age, Nioh), and the words "sexual"/"nudity" appear
# in the content notes of Dota 2, Rust and GTA V. So: explicit-content notices, NSFW/Hentai tags, or
# Sexual Content/Nudity among the game's 5 most-voted tags. The age gate is kept separately as mature_18.
EXPLICIT_NOTE = r"(?i)explicit|intended for adults|adult only|frequent nudity|hentai|pornograph"
adult_ids, mature_ids = set(), set()
if FR.exists():
    fr_note = f.notes.fillna("").str.contains(EXPLICIT_NOTE)
    fr_any = f.f_tags.map(lambda l: bool({"NSFW", "Hentai"} & set(l)))
    fr_top5 = f.f_tags.map(lambda l: bool({"Sexual Content", "Nudity"} & set(l[:5])))
    adult_ids = set(f.app_id[fr_note | fr_any | fr_top5])
    mature_ids = set(f.app_id[pd.to_numeric(f.required_age, errors="coerce").fillna(0) >= 18])
k_top5 = g.tags.map(lambda l: bool({"Sexual Content", "Nudity"} & set(list(l)[:5])) or bool({"NSFW", "Hentai"} & set(l)))
g["adult"] = g.app_id.isin(adult_ids) | k_top5
g["mature_18"] = g.app_id.isin(mature_ids)
rule("G17", "Catalog", "Sexually explicit games (explicit-content notice, NSFW/Hentai tag, or top-5 Sexual Content/Nudity tag)",
     g.adult.sum(), "adult = True; excluded from recommendations unless the user opts in",
     f"safe default for 'anyone with a Steam account'; the broader 18+ age gate ({g.mature_18.sum():,} games, mostly violence) "
     "is kept as mature_18 and not filtered")

# ---------------------------------------------------------------- one regular price
# The Fronkon crawl (Oct 2026) often caught a sale price, so a lone Fronkon price can be too low. When both sources
# have a price, the higher one is the better estimate of the regular price (prices rarely rise after launch).
fp = pd.to_numeric(g.get("fronkon_price"), errors="coerce")
kp = g.kaggle_price_regular
both_p = fp.notna() & kp.notna()
g["price_regular"] = np.where(both_p, np.fmax(fp, kp), fp.where(fp.notna(), kp))
g["price_source"] = np.select([both_p & (kp > fp), both_p, fp.notna(), kp.notna()],
                              ["kaggle_2023_higher", "fronkon_2026", "fronkon_2026_only", "kaggle_2023"], "none")
rule("G18", "Catalog", "Regular price = higher of Kaggle 2023 regular and Fronkon 2026 price when both exist",
     int((both_p & (kp > fp)).sum()),
     "price_regular raised to the 2023 regular price where the Oct 2026 crawl was lower; price_source set",
     "the Oct 2026 crawl often caught sale prices ($5.99 for a $59.99 game); Fronkon-only games are re-priced from "
     "SteamSpy's regular price (collect/steamspy_refill.py, clean/merge_steamspy.py)")

# ---------------------------------------------------------------- weak-text flags (content side)
desc = g.description.fillna("")
g["desc_short"] = desc.str.len().between(1, 19)
g["desc_shared"] = desc.ne("") & desc.duplicated(keep=False)
g["desc_non_english"] = desc.map(lambda s: sum(ord(c) > 127 for c in s) / max(len(s), 1) > 0.3)
rule("G19", "Catalog", "Descriptions that are very short, shared with other apps, or mostly non-Latin",
     int((g.desc_short | g.desc_shared | g.desc_non_english).sum()), "flagged (desc_short / desc_shared / desc_non_english)",
     "template or non-English text gives the English embedding model little to go on")

untitled = g.title.fillna("").str.strip().eq("")
rule("G12", "Catalog", "Apps with no title in any source (Steam included)", int(untitled.sum()),
     "dropped", "can't be shown to a user")
g = g[~untitled].reset_index(drop=True)

g["dup_title"] = g.duplicated("title_norm", keep=False)

# Two separate questions: does playing it say something about taste? can we show it as a pick?
g["history_ok"] = g.item_type.isin(HISTORY_TYPES)
TODAY = pd.Timestamp("2026-10-28")
g["recommendable"] = (g.item_type.eq("game") & ~g.delisted.fillna(False).astype(bool) & ~g.adult
                      & g.catalog_source.ne("mcauley") & (pd.to_datetime(g.release_date, errors="coerce") <= TODAY))
rule("G20", "Catalog", "Apps usable as play history (game/unknown/removed/mod/demo/episode)", g.history_ok.sum(),
     "history_ok = True", "delisted games like Skyrim (2011) or Rocket League still show what a user enjoys")
rule("G21", "Catalog", "Apps that can be recommended", g.recommendable.sum(),
     "recommendable = True (game, on sale, not adult, released, has store data)", "the candidate pool for both rows")
g.to_parquet(OUT / "games.parquet", index=False)

# Steam-only catalog: games no source describes yet (names only, for the catalog refresh)
new = cat[(cat.type == "game") & ~cat.appid.isin(g.app_id)].rename(columns={"appid": "app_id"})
new.to_parquet(OUT / "steam_catalog_extra.parquet", index=False)
rule("G11", "Steam catalog", "Steam games in no dataset (names only)", len(new), "saved to steam_catalog_extra",
     "details fetched by the weekly catalog refresh")

# =========================================================================== KAGGLE INTERACTIONS
k = pd.read_csv(KAGGLE / "recommendations.csv", parse_dates=["date"],
                dtype={"app_id": "int32", "helpful": "int32", "funny": "int32", "hours": "float32",
                       "user_id": "int32", "review_id": "int32", "is_recommended": "bool"})
nk = len(k)
k = k.sort_values("date")
d = k.duplicated(["user_id", "app_id"], keep="last")
rule("K1", "Kaggle reviews", "Duplicate (user, game) reviews", d.sum(), "kept the latest", "one interaction per user-game pair")
k = k[~d]
orph = ~k.app_id.isin(g.app_id)
rule("K2", "Kaggle reviews", "Reviews of games missing from games.csv", orph.sum(), "dropped", "no catalog row to join")
k = k[~orph]
k["playtime_min"] = (k.hours * 60).round().astype("int32")
k["played"] = k.hours > 0
rule("K3", "Kaggle reviews", "Zero playtime on a reviewed game", (~k.played).sum(), "kept; played = False (*unknown* in Layer 1)",
     "zero could mean refunded, played offline, or hidden; not a dislike")
k["censored"] = k.hours >= 999.9
rule("K4", "Kaggle reviews", "Hours at the 1000 h export cap", k.censored.sum(), "kept; censored = True",
     "true playtime is ≥ 1000 h; per-game caps are computed later on training data")
nogame = k.app_id.map(g.set_index("app_id").item_type) != "game"  # unknown/removed/dlc/tool all count as not-a-game here
rule("K5", "Kaggle reviews", "Reviews of non-game items (DLC etc.) or delisted apps", nogame.sum(),
     "kept; is_game flag", "train on everything, recommend games only")
k["is_game"] = ~nogame.to_numpy()
gi = g.set_index("app_id")
k["history_ok"] = k.app_id.map(gi.history_ok).fillna(False).astype(bool).to_numpy()

ucount = k.groupby("user_id").size()
same = k[k.user_id.isin(ucount[ucount >= 10].index)].groupby("user_id").hours.nunique()
fake = same[same == 1].index
rule("K6", "Kaggle reviews", f"Users (≥ 10 reviews) with identical hours on every game ({len(fake)} users)",
     k.user_id.isin(fake).sum(), "dropped", "copy-paste or scripted accounts; their playtime carries no signal")
k = k[~k.user_id.isin(fake)]

per_day = k.groupby(["user_id", "date"]).size()
bulk = set(per_day[per_day >= 50].index.get_level_values(0)) | set(ucount[ucount >= 1000].index)
k["bulk_user"] = k.user_id.isin(bulk)
rule("K7", "Kaggle reviews", f"Rows from bulk reviewers ({len(bulk):,} users with a ≥ 50-review day or ≥ 1,000 reviews)",
     k.bulk_user.sum(), "kept; bulk_user = True; excluded from Layer 1 label validation",
     "mass reviewing is legal but those review flags say little about each game")

rel = pd.to_datetime(k.app_id.map(gi.release_date), errors="coerce")
k["pre_release_review"] = (k.date < rel - pd.Timedelta(days=30)).to_numpy()
rule("K8", "Kaggle reviews", "Reviews > 30 days before the listed release date", k.pre_release_review.sum(),
     "kept; pre_release_review = True", "Early Access games (Rust, DayZ, Bannerlord) list their 1.0 date; playtime is still real")

ki = pd.DataFrame({"source": "kaggle", "user_key": k.user_id.astype("int64"), "app_id": k.app_id.astype("int32"),
                   "playtime_min": k.playtime_min, "playtime_2w_min": pd.array([pd.NA] * len(k), dtype="Int32"),
                   "played": k.played, "censored": k.censored, "is_game": k.is_game, "history_ok": k.history_ok,
                   "bulk_user": k.bulk_user, "pre_release_review": k.pre_release_review,
                   "review_recommend": k.is_recommended, "review_date": k.date, "helpful": k.helpful, "funny": k.funny})
ki.to_parquet(OUT / "interactions_kaggle.parquet", index=False)
rule("K0", "Kaggle reviews", f"Rows in → out ({nk:,} → {len(ki):,})", nk - len(ki), "reconciled", "audit trail")

u = pd.read_csv(KAGGLE / "users.csv")
cnt = ki.groupby("user_key").size()
u["reviews_in_data"] = u.user_id.map(cnt).fillna(0).astype("int32")
bad_u = (u.products == 0) & (u.reviews > 0)
u["products_inconsistent"] = bad_u
u["bulk_reviewer"] = u.user_id.isin(bulk)
u = u[~u.user_id.isin(fake)]
rule("U1", "Kaggle users", "Users with 0 products but ≥ 1 review", bad_u.sum(), "kept; products_inconsistent = True",
     "`products` can't be trusted as library size for these users")
u.to_parquet(OUT / "users_kaggle.parquet", index=False)
del k

# =========================================================================== McAULEY INTERACTIONS (full libraries)
mi = pd.read_parquet(MC / "tidy" / "users_items.parquet")
nm = len(mi)
na = mi.app_id.isna()
rule("M1", "McAuley items", "Owned rows with no app id", na.sum(), "dropped", "can't join to any catalog")
mi = mi[~na]
mi["app_id"] = mi.app_id.astype("int64")
d = mi.duplicated(["user_id", "app_id"], keep=False)
rule("M2", "McAuley items", "Duplicate (user, game) rows", mi.duplicated(["user_id", "app_id"]).sum(),
     "kept the row with the most playtime", "a user owns a game once")
mi = mi.sort_values("playtime_forever", kind="stable").drop_duplicates(["user_id", "app_id"], keep="last")
neg = (mi.playtime_forever < 0) | (mi.playtime_2weeks < 0)
rule("M3", "McAuley items", "Negative playtime", neg.sum(), "dropped", "impossible values")
mi = mi[~neg]
over = mi.playtime_2weeks > 20160
rule("M4", "McAuley items", "playtime_2weeks > 20,160 min (more than 24 h/day)", over.sum(), "capped at 20,160; flagged",
     "idle or tracking errors (framework rule)")
mi["playtime_2weeks"] = mi.playtime_2weeks.clip(upper=20160)
mi["played"] = mi.playtime_forever > 0
rule("M5", "McAuley items", "Owned but never played", (~mi.played).sum(), "kept; played = False (*unknown*)",
     "bundles and gifts; not a dislike")
mi["item_type"] = mi.app_id.map(gi.item_type).fillna("unknown")   # same typing as the catalog (G13/G16)
inv = mi.playtime_2weeks > mi.playtime_forever
rule("M9", "McAuley items", "2-week playtime larger than lifetime playtime", inv.sum(),
     "lifetime raised to the 2-week value", "the lifetime counter was stale at crawl time; lifetime can't be smaller")
mi.loc[inv, "playtime_forever"] = mi.loc[inv, "playtime_2weeks"]
mi["played"] = mi.playtime_forever > 0
mi["history_ok"] = mi.app_id.map(gi.history_ok).fillna(True).astype(bool)
types = mi.item_type
for t, n in types.value_counts().items():
    if t != "game":
        rule("M6", "McAuley items", f"Owned items typed '{t}'", n, "kept; is_game = False", "train on all, recommend games only")
mu = pd.read_parquet(MC / "tidy" / "users.parquet")
empty_lib = (mu.n_items_listed == 0).sum()
rule("M7", "McAuley users", "Users with an empty library (private/no games)", empty_lib, "excluded from interactions (no rows)",
     "the live app must handle this case with the pick-your-favorites fallback")
codes, uniques = pd.factorize(mi.user_id)
umap = pd.DataFrame({"user_key": np.arange(len(uniques), dtype="int64") + 100_000_000, "mc_user_id": uniques})
lib = (mi.assign(c=codes, ph=mi.played & mi.history_ok)
       .groupby("c").agg(n_owned=("app_id", "size"), n_played=("played", "sum"), n_played_hist=("ph", "sum")))
umap = umap.join(lib, how="left")
umap["collector"] = umap.n_owned >= 3000
umap["no_played"] = umap.n_played_hist == 0
rule("M10", "McAuley users", "Collectors (≥ 3,000 owned items)", umap.collector.sum(), "kept; collector = True",
     "huge libraries are mostly unplayed bundles; reported as their own segment")
rule("M11", "McAuley users", "Users who own games but played none of them", umap.no_played.sum(),
     "kept; no_played = True", "no positives to learn from; the live app uses the pick-your-favorites fallback")
umap.to_parquet(OUT / "users_mcauley_map.parquet", index=False)

rv = pd.read_parquet(MC / "tidy" / "user_reviews.parquet").dropna(subset=["app_id"])
rv["app_id"] = rv.app_id.astype("int64")
rv = rv.sort_values("posted_date").drop_duplicates(["user_id", "app_id"], keep="last")
mi = mi.merge(rv[["user_id", "app_id", "recommend", "posted_date"]], on=["user_id", "app_id"], how="left")
rule("M8", "McAuley reviews", "Owned rows that also have a review (for Layer 1 validation)", mi.recommend.notna().sum(),
     "joined as review_recommend", "validation only")

mci = pd.DataFrame({"source": "mcauley", "user_key": codes.astype("int64") + 100_000_000, "app_id": mi.app_id.astype("int32"),
                    "playtime_min": mi.playtime_forever.astype("int32"), "playtime_2w_min": mi.playtime_2weeks.astype("Int32"),
                    "played": mi.played, "censored": False,
                    "is_game": (mi.item_type == "game").to_numpy(), "item_type": mi.item_type.to_numpy(),
                    "history_ok": mi.history_ok.to_numpy(),
                    "review_recommend": mi.recommend.astype("boolean"), "review_date": mi.posted_date,
                    "helpful": pd.array([pd.NA] * len(mi), dtype="Int32"), "funny": pd.array([pd.NA] * len(mi), dtype="Int32")})
mci.to_parquet(OUT / "interactions_mcauley.parquet", index=False)
rule("M0", "McAuley items", f"Rows in → out ({nm:,} → {len(mci):,})", nm - len(mci), "reconciled", "audit trail")

# =========================================================================== VALIDATION CHECKS (assertions)
checks = []


def check(name, ok, detail=""):
    checks.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})


gg = pd.read_parquet(OUT / "games.parquet")
check("games: app_id unique", gg.app_id.is_unique)
check("games: no negative prices", (gg.kaggle_price_regular.dropna() >= 0).all())
check("games: no replacement chars left in title", ~gg.title.str.contains("\ufffd").any())
kp = gg.dropna(subset=["kaggle_price_regular", "kaggle_price_final"])
check("games: regular price ≥ final price (Kaggle rows)", (kp.kaggle_price_regular + 1e-9 >= kp.kaggle_price_final).all(),
      f"{(kp.kaggle_price_regular + 1e-9 < kp.kaggle_price_final).sum()} violations")
check("games: every row has a title", gg.title.fillna("").str.len().gt(0).all(), f"{gg.title.fillna('').eq('').sum()} empty")
check("games: catalog_source set", gg.catalog_source.notna().all(), gg.catalog_source.value_counts().to_dict().__str__())
for name, df in (("kaggle", ki), ("mcauley", mci)):
    check(f"{name} interactions: (user, game) unique", not df.duplicated(["user_key", "app_id"]).any())
    check(f"{name} interactions: playtime ≥ 0", (df.playtime_min >= 0).all())
    cov = df.app_id.isin(gg.app_id).mean()
    check(f"{name} interactions: share of rows whose game is in the catalog", cov == 1.0, f"{cov:.1%}")
check("user keys don't collide across sources", ki.user_key.max() < 100_000_000)
for name, df in (("kaggle", ki), ("mcauley", mci)):
    check(f"{name} interactions: every app_id joins to games", df.app_id.isin(gg.app_id).all(),
          f"{(~df.app_id.isin(gg.app_id)).sum():,} orphans")
check("games: no HTML entities in titles", ~gg.title.str.contains(r"&(amp|quot|#\d+|lt|gt);").any())
check("games: no hidden characters in titles", ~gg.title.str.contains(HIDDEN).any())
check("games: recommendable ⇒ game, not adult, not delisted, has store data",
      not (gg.recommendable & (gg.item_type.ne("game") | gg.adult | gg.delisted.fillna(False).astype(bool)
                               | gg.catalog_source.eq("mcauley"))).any(),
      f"{gg.recommendable.sum():,} recommendable")
check("games: no playtest is recommendable", not (gg.recommendable & gg.item_type.eq("playtest")).any())
check("mcauley interactions: 2-week ≤ lifetime playtime", not (mci.playtime_2w_min.fillna(0) > mci.playtime_min).any())
check("games: every row has item_type", gg.item_type.notna().all())

rep = ["# Cleaning report", "",
       "Built by `clean/build_clean.py`. Outputs in `C:/Users/juant/data_clean/` (parquet).", "",
       "## Rules applied", "", pd.DataFrame(LOG).to_markdown(index=False), "",
       "## Validation checks after cleaning", "", pd.DataFrame(checks).to_markdown(index=False), "",
       "## Output tables", "",
       "| table | rows | grain |", "|---|---:|---|",
       f"| games.parquet | {len(gg):,} | game (Kaggle catalog, enriched) |",
       f"| steam_catalog_extra.parquet | {len(new):,} | Steam game missing from Kaggle (names only) |",
       f"| interactions_kaggle.parquet | {len(ki):,} | user × game (reviewers; playtime + review flag) |",
       f"| interactions_mcauley.parquet | {len(mci):,} | user × owned game (full libraries) |",
       f"| users_kaggle.parquet | {len(u):,} | Kaggle user |",
       f"| users_mcauley_map.parquet | {len(umap):,} | McAuley user ↔ user_key |", "",
       "Deliberately **not** done here (computed later on training data only, to avoid leakage): per-game 99th-percentile "
       "playtime caps, per-game/per-user percentiles, popularity, train/test splits.", "",
       "## Label status (Layer 1)", "",
       "Adopted 2026-10-29: a two-stage enjoyment score, player-relative playtime plus achievements when shared (see label/label_config.json). "
       "Within-game AUC 0.675 (Kaggle) / 0.608 (McAuley), matching the floor; within-user AUC 0.686 / 0.680 vs 0.657 / 0.655. "
       "No popularity or game-quality features. Research in `label/label_research.md`."]
(ROOT / "clean" / "cleaning_report.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
print(pd.DataFrame(checks).to_string())
