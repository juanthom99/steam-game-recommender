"""Shared Layer 1 prep: Kaggle reviews -> cleaned playtime with per-game (g) and per-user (u) percentiles.

load() returns (rec, notes). The result is cached to label/cache/rec.parquet so later scripts skip the ~5 min prep.
Reviews (is_recommended) are carried along ONLY for validation; they are never a training signal.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "rec.parquet"
DATA = Path(os.path.expanduser("~/.cache/kagglehub/datasets/antonkozyriev/game-recommendations-on-steam/versions/28"))
FLOOR_H = 2.0          # Steam refund window: 120 minutes (cited)
SHORT_GAME_H = 3.0     # team choice: games with median < 3 h use the percentile rule alone
MIN_PLAYERS = 20       # team choice: below this, blend the game percentile with its main tag's


def load():
    if CACHE.exists():
        rec = pd.read_parquet(CACHE)
        return rec, rec.attrs.get("notes", [])
    notes = []
    rec = pd.read_csv(DATA / "recommendations.csv", usecols=["app_id", "user_id", "hours", "is_recommended", "date"],
                      dtype={"app_id": "int32", "user_id": "int32", "hours": "float32", "is_recommended": "bool"},
                      parse_dates=["date"])
    meta = pd.read_json(DATA / "games_metadata.json", lines=True)
    main_tag = meta.set_index("app_id").tags.apply(lambda t: t[0] if t else "_none")
    n_all = len(rec)
    zero = rec.hours <= 0
    censored = int((rec.hours >= 999.9).sum())
    rec = rec[~zero].reset_index(drop=True)
    notes.append(f"Rows: {n_all:,}; zero-playtime rows dropped as *unknown*: {int(zero.sum()):,}; "
                 f"hours at the 1000 h cap (censored): {censored:,}")

    # cap at each game's 99th percentile
    p99 = rec.groupby("app_id").hours.transform(lambda s: s.quantile(0.99))
    rec["hours"] = np.minimum(rec.hours, p99).astype("float32")

    # per-game percentile g, shrunk toward the main tag for games with few players
    grp = rec.groupby("app_id")
    rec["g"] = grp.hours.rank(pct=True, method="average").astype("float32")
    n_players = grp.hours.transform("size")
    med = grp.hours.transform("median").astype("float32")
    tag = rec.app_id.map(main_tag).fillna("_none").astype("category")
    small = n_players < MIN_PLAYERS
    if small.any():
        g_tag = np.empty(int(small.sum()), dtype="float32")
        sub = pd.DataFrame({"tag": tag[small], "hours": rec.hours[small]})
        for t, idx in sub.groupby("tag", observed=True).groups.items():
            ref = np.sort(rec.hours[tag == t].to_numpy())
            g_tag[sub.index.get_indexer(idx)] = np.searchsorted(ref, sub.loc[idx, "hours"].to_numpy(), side="right") / len(ref)
        w = (n_players[small] / MIN_PLAYERS).to_numpy()
        rec.loc[small, "g"] = (w * rec.loc[small, "g"].to_numpy() + (1 - w) * g_tag).astype("float32")
    notes.append(f"Games: {rec.app_id.nunique():,}; rows in games with < {MIN_PLAYERS} players "
                 f"(shrunk toward main tag): {int(small.sum()):,}")

    rec["u"] = rec.groupby("user_id").g.rank(pct=True, method="average").astype("float32")
    rec["ratio"] = (rec.hours / med).astype("float32")
    rec["short_game"] = (med < SHORT_GAME_H).to_numpy()
    rec["n_user"] = rec.groupby("user_id").g.transform("size").astype("int32")
    rec["calib"] = (rec.user_id % 2 == 0).to_numpy()

    CACHE.parent.mkdir(exist_ok=True)
    rec.attrs["notes"] = notes
    rec.to_parquet(CACHE, index=False)
    return rec, notes
