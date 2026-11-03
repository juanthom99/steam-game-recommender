"""Reserve the final test set and the validation set (eval/PROTOCOL.md, decision 1). Run once; the result is fixed.

Unit: a player within a source (mcauley 2017 libraries, steam2026 libraries, kaggle reviewers).
  bucket = sha256("steamrec-split-v1|<source>|<player>") mod 10
  0 -> test, 1 -> validation, 2-9 -> train
Players already looked at (the 2,400 from the first offline check, and the label pilot players) can never be test:
if they land in bucket 0 they move to validation.
Inside test and validation players, each played game is hidden with
  sha256("steamrec-split-v1|<source>|<player>|<app_id>") mod 5 == 0   (about 20%)
so every model is scored on exactly the same hidden games.

Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python clean/reserve_test.py
Out: C:/Users/juant/data_clean/splits/{players.parquet, hidden_games.parquet, manifest.json}
"""
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

D = Path("C:/Users/juant/data_clean")
R = Path("C:/Users/juant/data_raw/steam_reviews")
ROOT = Path(__file__).resolve().parent.parent
OUT = D / "splits"
OUT.mkdir(exist_ok=True)
SEED = "steamrec-split-v1"
if (OUT / "manifest.json").exists():
    raise SystemExit("Split already reserved; it must not be regenerated. See splits/manifest.json.")

h = lambda s: int.from_bytes(hashlib.sha256(s.encode()).digest()[:8], "big")

# ---- played play-history rows per source (the same filter the models train on)
mc = pd.read_parquet(D / "interactions_mcauley.parquet", columns=["user_key", "app_id", "playtime_min", "played", "history_ok"])
mc = mc[mc.played & mc.history_ok][["user_key", "app_id"]].assign(src="mcauley")
kg = pd.read_parquet(D / "interactions_kaggle.parquet", columns=["user_key", "app_id", "played", "history_ok", "bulk_user"])
kg = kg[kg.played & kg.history_ok & ~kg.bulk_user.fillna(False)][["user_key", "app_id"]].assign(src="kaggle")
cat = pd.read_parquet(D / "games.parquet", columns=["app_id", "history_ok"])
bad = set(cat.app_id[~cat.history_ok.astype(bool)])
fr = pd.DataFrame([(r["uid"], a) for r in map(json.loads, (R / "libraries.jsonl").open(encoding="utf-8")) if r["public"]
                   for a, pt, _, _ in r["games"] if pt > 0 and a not in bad], columns=["user_key", "app_id"]).assign(src="steam2026")
rows = pd.concat([mc, fr, kg], ignore_index=True)
rows["user_key"] = rows.user_key.astype(str)

# ---- player buckets
players = rows[["src", "user_key"]].drop_duplicates().reset_index(drop=True)
t = time.time()
players["bucket"] = [h(f"{SEED}|{s}|{u}") % 10 for s, u in zip(players.src, players.user_key)]
print(f"hashed {len(players):,} players in {time.time() - t:.0f}s", flush=True)
players["split"] = np.select([players.bucket == 0, players.bucket == 1], ["test", "validation"], "train")

seen = pd.read_parquet(ROOT / "model" / "artifacts" / "heldout.parquet", columns=["user"]).user.unique()
seen = {tuple(u.split(":", 1)) for u in seen}
pilot = set(pd.read_parquet(D / "pilot" / "pairs.parquet", columns=["user_key"]).user_key.astype(str))
seen |= {("mcauley", u) for u in pilot}
moved = players.split.eq("test").to_numpy() & np.array([(s, u) in seen for s, u in zip(players.src, players.user_key)])
players.loc[moved, "split"] = "validation"
keep = players[players.split != "train"][["src", "user_key", "split"]]
keep.to_parquet(OUT / "players.parquet", index=False)

# ---- hidden games for test + validation players
ev = rows.merge(keep, on=["src", "user_key"])
ev["hidden"] = [h(f"{SEED}|{s}|{u}|{a}") % 5 == 0 for s, u, a in zip(ev.src, ev.user_key, ev.app_id)]
ev[["src", "user_key", "app_id", "split", "hidden"]].to_parquet(OUT / "hidden_games.parquet", index=False)

vis = ev[~ev.hidden].groupby(["src", "user_key"]).size().rename("n_visible")
hid = ev[ev.hidden].groupby(["src", "user_key"]).size().rename("n_hidden")
k = keep.set_index(["src", "user_key"]).join(vis).join(hid).fillna(0)
k["eligible"] = (k.n_visible >= 5) & (k.n_hidden >= 1)
counts = {f"{s}/{sp}": {"players": int(len(g)), "eligible_5plus": int(g.eligible.sum()),
                         "small_1to4": int(((g.n_visible >= 1) & (g.n_visible < 5) & (g.n_hidden >= 1)).sum())}
          for (s, sp), g in k.reset_index().groupby(["src", "split"])}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = {"created": time.strftime("%Y-%m-%d %H:%M"), "rule": __doc__.split("Run:")[0].strip(),
            "seed_string": SEED, "moved_from_test_to_validation_already_seen": int(moved.sum()), "counts": counts,
            "files": {f: sha(OUT / f) for f in ("players.parquet", "hidden_games.parquet")},
            "note": "Test players must be excluded from every model's training data. Test is scored once, at the end."}
json.dump(manifest, open(OUT / "manifest.json", "w"), indent=2)
print(json.dumps(manifest["counts"], indent=1), "\nmoved:", int(moved.sum()))
