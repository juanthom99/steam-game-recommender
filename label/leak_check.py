"""How much of the within-user gain could come from game quality instead of the player's own playtime?"""
import sys; from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from enjoy_score import load, metrics, model, V1
a = load(); a["y"] = a.review_recommend.astype(bool); a["cal"] = a.user_key % 2 == 0
rows = []
for ds in ("McAuley", "Kaggle"):
    d = a[a.ds == ds]; c, r = d[d.cal], d[~d.cal]
    rate = c.groupby("app_id").y.agg(["sum", "size"]); prior = c.y.mean()
    quality = r.app_id.map((rate["sum"] + 20 * prior) / (rate["size"] + 20)).fillna(prior)   # pure game quality, no player info
    rows.append({"dataset": ds, "score": "game quality only (review rate, no player info)", **metrics(r.y.to_numpy(), quality.to_numpy(), r)})
    rows.append({"dataset": ds, "score": "game length only", **metrics(r.y.to_numpy(), r.log_len.to_numpy(), r)})
    # V1 with game length removed from what it can reconstruct: residualize every feature within game (player-relative only)
    rel = ["g", "resid", "u_rank"]
    m = model(rel, False).fit(c[rel], c.y); rows.append({"dataset": ds, "score": "player-relative only (g, resid, u_rank)",
        **metrics(r.y.to_numpy(), m.predict_proba(r[rel])[:, 1], r)})
    m = model(V1, False).fit(c[V1], c.y); rows.append({"dataset": ds, "score": "V1", **metrics(r.y.to_numpy(), m.predict_proba(r[V1])[:, 1], r)})
    for x in rows[-4:]: print(x, flush=True)
t = pd.DataFrame(rows).round(3)
with open(Path(__file__).resolve().parent / "enjoy_score_results.md", "a", encoding="utf-8") as f:
    f.write("\n## Leakage check: game-level scores with no player information\n\n" + t.to_markdown(index=False) + "\n")
print(t.to_string())
