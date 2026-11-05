"""Starter template: plug your model in, write a recs file, then run evaluate.py.

  python example_model.py --data <team_eval folder> --train train_lite --out recs_mymodel.parquet

Replace MyModel with yours. Rules that keep the comparison fair:
  - fit only on a train file (never on validation.parquet rows that are hidden)
  - recommend from the player's VISIBLE games only (played and hidden_<holdout> == False)
  - skip games the player owns that are not hidden, and pick only recommendable games
The baseline below is MostPopular: the games most often enjoyed (g >= 0.5) by train players.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

HOLDOUTS = ["80_20", "75_25", "50_50"]


class MyModel:
    def fit(self, train, games):
        """train: player_id, src, app_id, playtime_min, g (enjoyment percentile 0-1 within the game)."""
        ok = set(games.app_id[games.recommendable])
        pop = train[(train.g >= 0.5) & train.app_id.isin(ok)].app_id.value_counts()
        self.ranking = pop.index.to_numpy()
        return self

    def recommend(self, visible, exclude, k=10):
        """visible: this player's visible rows (app_id, playtime_min, g); exclude: set of app ids not to pick."""
        out = []
        for a in self.ranking:
            if a not in exclude:
                out.append(a)
                if len(out) == k:
                    break
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(Path(__file__).resolve().parent))
    ap.add_argument("--train", default="train_lite", help="train_lite or train_full (reads every part)")
    ap.add_argument("--out", default="recs_mymodel.parquet")
    a = ap.parse_args()
    d = Path(a.data)
    games = pd.read_parquet(d / "games.parquet")
    train = pd.concat([pd.read_parquet(f) for f in sorted(d.glob(f"{a.train}_part*.parquet"))], ignore_index=True)
    model = MyModel().fit(train, games)
    val = pd.read_parquet(d / "validation.parquet")
    rows = []
    for h in HOLDOUTS:
        hcol = f"hidden_{h}"
        for pid, p in val.groupby("player_id", sort=False):
            vis = p[p.played & ~p[hcol]]
            exclude = set(p.app_id[~p[hcol]])                 # everything owned except the hidden games
            for r, app in enumerate(model.recommend(vis, exclude), 1):
                rows.append((pid, h, r, int(app)))
    pd.DataFrame(rows, columns=["player_id", "holdout", "rank", "app_id"]).to_parquet(a.out, index=False)
    print(f"wrote {a.out}: {len(rows):,} picks")


if __name__ == "__main__":
    main()
