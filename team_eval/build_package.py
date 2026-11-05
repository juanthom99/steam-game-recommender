"""Build the shared team evaluation package (validation players only; the test set stays untouched).

Writes to C:/Users/juant/data_clean/team_eval/ (uploaded to Supabase Storage by team_eval/upload_supabase.py):
  games.parquet              catalog fields the metrics use (one row per game)
  train_full_partNN.parquet  every TRAIN player's played games: player_id, src, app_id, playtime_min, g
                             (split into parts under 45 MB, the Supabase free-plan file limit is 50 MB)
  train_lite_part1/2.parquet all McAuley + Steam 2026 train players and a fixed 10% of Kaggle train players
  validation.parquet         every owned game of the validation players, with three holdout columns
                             (hidden_80_20 = our official split; hidden_75_25 and hidden_50_50 for the team tests)
For our own models only (never shared):
  eval/cache/team_<holdout>_players.pkl              the same holdouts in the harness format (eval/data.py)
  data_clean/team_eval_private/player_map.parquet    player_id -> (src, user_key)

Same players, enjoyment label and Kaggle subsample as eval/data.py (validation split, 3% of Kaggle validation players).
Each source is processed on its own to keep memory low (enjoyment is computed within a source anyway).
  PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python team_eval/build_package.py
"""
import gc
import hashlib
import json
import pickle
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = Path("C:/Users/juant/data_clean")
R = Path("C:/Users/juant/data_raw/steam_reviews")
OUT = D / "team_eval"
PRIV = D / "team_eval_private"
C = ROOT / "eval" / "cache"
OUT.mkdir(exist_ok=True)
PRIV.mkdir(exist_ok=True)
for f in OUT.glob("train_full_part*.parquet"):
    f.unlink()
t0 = time.time()
log = lambda m: print(f"[{time.time() - t0:5.0f}s] {m}", flush=True)
h64 = lambda s: int.from_bytes(hashlib.sha256(s.encode()).digest()[:8], "big")

cat = pd.read_parquet(D / "games.parquet")
hist_ok = cat.app_id[cat.history_ok.astype(bool)].to_numpy()
OFFSET = {"mcauley": (1_000_000, 10_000_000), "steam2026": (2_000_000, 20_000_000), "kaggle": (3_000_000, 30_000_000)}


def load(src):
    if src == "steam2026":
        d = pd.DataFrame([(r["uid"], a, pt) for r in map(json.loads, (R / "libraries.jsonl").open(encoding="utf-8")) if r["public"]
                          for a, pt, _, _ in r["games"]], columns=["user_key", "app_id", "playtime_min"])
        d["user_key"] = d.user_key.astype(str)
    else:
        cols = ["user_key", "app_id", "playtime_min"] + (["bulk_user"] if src == "kaggle" else [])
        d = pd.read_parquet(D / f"interactions_{src}.parquet", columns=cols)
        if src == "kaggle":
            d = d[~d.bulk_user.fillna(False).to_numpy()].drop(columns="bulk_user")
    d = d.drop_duplicates(["user_key", "app_id"])
    d["app_id"] = d.app_id.astype(np.int32)
    d["playtime_min"] = d.playtime_min.astype(np.int32)
    d["played"] = (d.playtime_min.to_numpy() > 0) & np.isin(d.app_id.to_numpy(), hist_ok)
    return d


def keyconv(s, src):
    return s.astype(str) if src == "steam2026" else s.astype(np.int64)


train_parts, val_parts, n_train = [], [], {}
vmaps = []
for src in ("mcauley", "steam2026", "kaggle"):
    d = load(src)
    pl = pd.read_parquet(D / "splits" / "players.parquet", filters=[("src", "==", src)], columns=["user_key", "split"])
    pl["user_key"] = keyconv(pl.user_key, src)
    val_keys = pl.user_key[pl.split == "validation"]
    not_train = set(pl.user_key)
    if src == "kaggle":                                         # same fixed 3% subsample as eval/data.py
        val_keys = val_keys[[h64(f"steamrec-kaggle-sub-v1|{u}") % 100 < 3 for u in val_keys]]
    val_keys = set(val_keys)
    del pl
    is_eval = d.user_key.isin(not_train).to_numpy()
    log(f"{src}: rows {len(d):,}; train rows {(~is_eval).sum():,}")

    # ---- train: enjoyment g = percentile of playtime among this game's train players (0.5 if < 10 of them)
    tr = d[~is_eval & d.played.to_numpy()][["user_key", "app_id", "playtime_min"]]
    ev = d[d.user_key.isin(val_keys).to_numpy()].copy()
    del d, is_eval, not_train
    gc.collect()
    grp = tr.groupby("app_id").playtime_min
    g = grp.rank(pct=True).astype(np.float32)
    g[grp.transform("size") < 10] = 0.5
    tr = tr.assign(g=g.astype(np.float16))
    del g, grp
    for a, c in tr.app_id.value_counts().items():
        n_train[a] = n_train.get(a, 0) + int(c)
    codes = pd.factorize(tr.user_key)[0]
    tr = pd.DataFrame({"player_id": (codes + OFFSET[src][1]).astype(np.int32), "src": src, "app_id": tr.app_id.to_numpy(),
                       "playtime_min": tr.playtime_min.to_numpy(), "g": tr.g.to_numpy()})
    tr["src"] = tr.src.astype("category")

    # ---- validation players: g against the train distribution of the same game
    srt = tr.sort_values(["app_id", "playtime_min"])[["app_id", "playtime_min"]]
    apps, start = np.unique(srt.app_id.to_numpy(), return_index=True)
    size = np.diff(np.r_[start, len(srt)])
    pts = srt.playtime_min.to_numpy()
    del srt
    ev["g"] = np.float32(np.nan)
    pl_ev = ev.played.to_numpy()
    a_idx = np.searchsorted(apps, ev.app_id.to_numpy())
    known = (a_idx < len(apps)) & (apps[np.minimum(a_idx, len(apps) - 1)] == ev.app_id.to_numpy())
    gv = np.full(len(ev), 0.5, np.float32)
    for i in np.where(pl_ev & known)[0]:
        j = a_idx[i]
        if size[j] >= 10:
            s0 = start[j]
            gv[i] = np.searchsorted(pts[s0:s0 + size[j]], ev.playtime_min.iat[i], side="right") / size[j]
    ev.loc[pl_ev, "g"] = gv[pl_ev]
    del pts

    hid = pd.read_parquet(D / "splits" / "hidden_games.parquet", filters=[("src", "==", src), ("split", "==", "validation")],
                          columns=["user_key", "app_id", "hidden"])
    hid["user_key"] = keyconv(hid.user_key, src)
    hid["app_id"] = hid.app_id.astype(np.int32)
    ev = ev.merge(hid, on=["user_key", "app_id"], how="left")
    del hid
    ev["hidden_80_20"] = ev.hidden.fillna(False).astype(bool) & ev.played
    hv = np.array([h64(f"steamrec-team-v1|{src}|{u}|{a}") for u, a in zip(ev.user_key, ev.app_id)], dtype=np.uint64)
    ev["hidden_75_25"] = ev.played & (hv % np.uint64(4) == 0)
    ev["hidden_50_50"] = ev.played & (hv % np.uint64(2) == 0)
    ev["enjoyed"] = ev.played & (ev.g >= 0.5)
    vk = pd.DataFrame({"user_key": ev.user_key.drop_duplicates().to_numpy()})
    vk["player_id"] = (np.arange(len(vk)) + OFFSET[src][0]).astype(np.int32)
    ev = ev.merge(vk, on="user_key")
    ev["src"] = src
    vmaps.append(vk.assign(src=src, user_key=vk.user_key.astype(str)))
    val_parts.append(ev.drop(columns=["hidden"]))
    train_parts.append(tr)
    log(f"{src}: train players {tr.player_id.nunique():,}; validation players {len(vk):,}, rows {len(ev):,}")
    del tr, ev
    gc.collect()

# ------------------------------------------------------------------ shared files
pd.concat(vmaps, ignore_index=True)[["player_id", "src", "user_key"]].to_parquet(PRIV / "player_map.parquet", index=False)
price = cat.price_regular.where(cat.price_source.eq("itad_steam_regular"), cat[["price_regular", "kaggle_price_regular"]].max(axis=1))
n_rev = cat.steam_positive.fillna(0) + cat.steam_negative.fillna(0)
ratio = cat.steam_positive / n_rev.replace(0, np.nan)
derived = pd.cut(ratio, [-0.01, 0.1999, 0.3999, 0.6999, 0.7999, 1.0],
                 labels=["Very Negative", "Mostly Negative", "Mixed", "Mostly Positive", "Very Positive"]).astype(object)
rating = cat.rating.where(cat.rating.notna(), derived.where(n_rev >= 10))
games = pd.DataFrame({
    "app_id": cat.app_id.astype(np.int32), "title": cat.title, "tags": cat.tags, "genres": cat.genres,
    "release_year": pd.to_datetime(cat.release_date, errors="coerce").dt.year.astype("Int16"),
    "price_regular": price.round(2), "rating": rating, "user_reviews": cat.user_reviews,
    "median_playtime_min": cat.steamspy_median_playtime_min, "avg_playtime_min": cat.steamspy_avg_playtime_min, "content_level": cat.content_level, "explicit": cat.explicit.astype(bool),
    "recommendable": cat.recommendable.astype(bool), "n_train_players": cat.app_id.map(n_train).fillna(0).astype(np.int32)})
games.to_parquet(OUT / "games.parquet", index=False)
log(f"games.parquet {len(games):,}")

ROWS_PER_PART = 5_000_000
part = 0
lite = []
for tr in train_parts:
    lite.append(tr if tr.src.iat[0] != "kaggle" else tr[tr.player_id.to_numpy() % 10 == 0])
    for k in range(0, len(tr), ROWS_PER_PART):
        part += 1
        tr.iloc[k:k + ROWS_PER_PART].to_parquet(OUT / f"train_full_part{part:02d}.parquet", index=False)
lite_df = pd.concat(lite, ignore_index=True)
h = len(lite_df) // 2
lite_df.iloc[:h].to_parquet(OUT / "train_lite_part1.parquet", index=False)
lite_df.iloc[h:].to_parquet(OUT / "train_lite_part2.parquet", index=False)
del lite_df
log(f"train_full: {sum(len(t) for t in train_parts):,} rows in {part} parts; train_lite {sum(len(t) for t in lite):,} rows")
del train_parts, lite
gc.collect()

ev = pd.concat(val_parts, ignore_index=True)
vcols = ["player_id", "src", "app_id", "playtime_min", "played", "g", "enjoyed", "hidden_80_20", "hidden_75_25", "hidden_50_50"]
ev[vcols].to_parquet(OUT / "validation.parquet", index=False)
log(f"validation.parquet {len(ev):,} rows")

# ------------------------------------------------------------------ harness-format holdouts for our own models
U = np.load(C / "universe.npy")
uidx = pd.Series(np.arange(len(U)), index=U)
ev["u"] = ev.app_id.map(uidx).fillna(-1).astype(np.int64)
for hcol in ("hidden_80_20", "hidden_75_25", "hidden_50_50"):
    out = []
    for (s, pid), d in ev.groupby(["src", "player_id"], sort=False):
        hid = d[d[hcol]]
        hits = hid[hid.g >= 0.5]
        if len(hits) == 0:
            continue
        vis = d[d.played & ~d[hcol] & (d.u >= 0)]
        out.append({"src": s, "user": str(d.user_key.iat[0]), "player_id": int(pid), "n_visible": int((d.played & ~d[hcol]).sum()),
                    "vis_u": vis.u.to_numpy(np.int64), "vis_g": vis.g.to_numpy(np.float32), "vis_pt": vis.playtime_min.to_numpy(np.int64),
                    "hit_u": hits.u.to_numpy(np.int64), "hit_gain": np.where(hits.g >= 0.8, 2, 1).astype(np.int8),
                    "hid_u": hid.u.to_numpy(np.int64), "hid_pt": hid.playtime_min.to_numpy(np.int64), "hid_g": hid.g.to_numpy(np.float32),
                    "owned_u": d.u[d.u >= 0].to_numpy(np.int64)})
    pickle.dump(out, open(C / f"team_{hcol[7:]}_players.pkl", "wb"))
    log(f"{hcol}: {len(out):,} players with >= 1 hidden enjoyed game")
for f in sorted(OUT.glob("*.parquet")):
    log(f"  {f.name}: {f.stat().st_size / 1e6:.1f} MB")
log("done")
