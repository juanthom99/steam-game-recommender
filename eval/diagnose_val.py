"""Post-hoc diagnosis of the two Layer 3 misses, on VALIDATION players only (the test set is not touched).

1. Regret: why do our picks show more regret than MostPopular's? Splits played picks by game popularity and
   checks how many "regret" picks (played < 120 min) were actually enjoyed (short games the player finished).
2. Try something new: accuracy vs exploration as the rule's knobs vary (candidate pool, "new tag" threshold),
   plus a soft rerank (score + lambda * tag distance). The shipped rule is pool 400, threshold 0.02.
Run: OPENBLAS_NUM_THREADS=4 PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python eval/diagnose_val.py
Out: eval/diagnosis_report.md
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from harness import DISC, load, train_matrix  # noqa: E402
from models import EASE, Hybrid, MostPopular  # noqa: E402

C = HERE / "cache"
U, rec, val = load("validation")
val = [p for p in val if p["n_visible"] >= 5]
assert "hid_pt" in val[0], "validation players lack hidden playtime"
X = train_matrix()
best = json.load(open(C / "best_params.json"))
pop = np.load(C / "n_train_players.npy")

ids = np.load(HERE.parent / "model" / "artifacts" / "game_embedding_ids.npy")
emb = np.load(HERE.parent / "model" / "artifacts" / "game_embeddings.npy")
E = np.zeros((len(U), emb.shape[1]), np.float32)
pos = pd.Series(np.arange(len(U)), index=U).reindex(ids); ok = pos.notna().to_numpy()
E[pos[ok].astype(int).to_numpy()] = emb[ok]
TAGS = [t.split("|") if t else [] for t in np.load(C / "universe_tags.npy", allow_pickle=True)]

t0 = time.time()
mp = MostPopular().fit(X)
ease = EASE(**best["EASE"]).fit(X)
hyb = Hybrid(ease, E, **best["Hybrid-EASE"])
print(f"fitted ({time.time() - t0:.0f}s); validation players {len(val):,}", flush=True)


def profile(p):
    prof = {}
    for u, gg in zip(p["vis_u"], p["vis_g"]):
        for t in TAGS[u]:
            prof[t] = prof.get(t, 0) + gg
    return prof


def dist(item, prof, norm):
    tg = TAGS[item]
    if not tg or not norm:
        return np.nan
    return 1 - sum(prof.get(t, 0) for t in tg) / (np.sqrt(len(tg)) * norm)


def ndcg(top, gain):
    hit = np.array([t in gain for t in top[:10]], float)
    return (hit * DISC[:len(hit)]).sum() / DISC[:min(len(gain), 10)].sum()


def mask(s, p):
    s = s.copy(); s[~rec] = -np.inf; s[np.setdiff1d(p["owned_u"], p["hid_u"])] = -np.inf
    return s


def topk(s, k):
    t = np.argpartition(-s, k)[:k]
    t = t[np.argsort(-s[t], kind="stable")]
    return t[np.isfinite(s[t])]


POOLS, THS, LAMS = (50, 100, 200, 400, 1000), (0.0, 0.005, 0.01, 0.02, 0.05, 0.10), (0.5, 1.0, 2.0, 4.0)
picks, curve = [], []
for k in range(0, len(val), 256):
    batch = val[k:k + 256]
    S = {"MostPopular": mp.score(batch), "EASE": ease.score(batch), "Hybrid-EASE": hyb.score(batch)}
    for r, p in enumerate(batch):
        gain = dict(zip(p["hit_u"].tolist(), p["hit_gain"].tolist()))
        pt = dict(zip(p["hid_u"].tolist(), p["hid_pt"].tolist()))
        prof = profile(p); tot = sum(prof.values()) or 1
        norm = np.sqrt(sum(v * v for v in prof.values()))
        for name, M in S.items():
            for t in topk(mask(M[r], p), 10):
                if t in pt:
                    picks.append((name, p["src"], p["user"], int(t), pt[t], pop[t], t in gain))
        s = mask(S["Hybrid-EASE"][r], p)
        cand = topk(s, max(POOLS))
        fy = cand[:10]
        row = {"src": p["src"], "user": p["user"], "For you|ndcg": ndcg(fy, gain),
               "For you|dist": np.nanmean([dist(t, prof, norm) for t in fy])}
        share = {t: max((prof.get(g, 0) / tot for g in TAGS[t]), default=1) for t in cand}
        minshare = {t: min((prof.get(g, 0) / tot for g in TAGS[t]), default=1) for t in cand}
        for pool in POOLS:
            for th in THS:
                c = [t for t in cand[:pool] if TAGS[t] and minshare[t] <= th] if th == 0.0 else \
                    [t for t in cand[:pool] if TAGS[t] and minshare[t] < th]
                c = c[:10]
                key = f"filter pool={pool} th={th}"
                row[key + "|ndcg"] = ndcg(c, gain) if c else 0.0
                row[key + "|dist"] = np.nanmean([dist(t, prof, norm) for t in c]) if c else np.nan
                row[key + "|n"] = len(c)
        z = s[cand[:400]]; z = (z - z.mean()) / (z.std() + 1e-9)
        dd = np.nan_to_num(np.array([dist(t, prof, norm) for t in cand[:400]]), nan=0.0)
        for lam in LAMS:
            c = cand[:400][np.argsort(-(z + lam * dd), kind="stable")][:10]
            key = f"rerank lambda={lam}"
            row[key + "|ndcg"] = ndcg(c, gain)
            row[key + "|dist"] = np.nanmean([dist(t, prof, norm) for t in c])
            row[key + "|n"] = 10
        curve.append(row)
    print(f"{k + len(batch):,}/{len(val):,} ({time.time() - t0:.0f}s)", flush=True)

# ---------------------------------------------------------------- 1. regret
P = pd.DataFrame(picks, columns=["model", "src", "user", "item", "pt", "pop", "enjoyed"])
P["regret"] = P.pt < 120
edges = np.quantile(P.drop_duplicates("item")["pop"], [0, .5, .8, .95, 1])
P["popularity"] = pd.cut(P["pop"], np.unique(edges), include_lowest=True,
                         labels=["bottom 50%", "50-80%", "80-95%", "top 5%"][:len(np.unique(edges)) - 1])
reg = P.groupby("model").agg(played_picks=("regret", "size"), regret=("regret", "mean"),
                             median_train_players=("pop", "median"),
                             regret_but_enjoyed=("enjoyed", lambda e: (e & P.loc[e.index, "regret"]).sum() / P.loc[e.index, "regret"].sum()),
                             not_enjoyed=("enjoyed", lambda e: 1 - e.mean()))
# per player first (as layer3 does), then mean
per_player = P.groupby(["model", "src", "user"]).regret.mean().groupby("model").mean().rename("Regret@10 (per-player mean)")
reg = reg.join(per_player)
by_pop = P.pivot_table(index="model", columns="popularity", values="regret", aggfunc="mean", observed=True)
mix = P.pivot_table(index="model", columns="popularity", values="regret", aggfunc="size", observed=True)
mix = mix.div(mix.sum(1), axis=0)
# regret ours would have if it had MostPopular's popularity mix (direct standardisation)
std = (by_pop * mix.loc["MostPopular"]).sum(1).rename("regret at MostPopular's popularity mix")
reg = reg.join(std)

# ---------------------------------------------------------------- 2. try something new
Cv = pd.DataFrame(curve)
base = Cv["For you|ndcg"].mean()
variants = sorted({c.split("|")[0] for c in Cv.columns if c.startswith(("filter", "rerank"))})
tn = []
for v in variants:
    d = (Cv[v + "|dist"] - Cv["For you|dist"]).mean()
    tn.append({"variant": v, "NDCG@10": Cv[v + "|ndcg"].mean(), "share of For you": Cv[v + "|ndcg"].mean() / base,
               "tag distance gain": d, "players with < 10 picks": (Cv[v + "|n"] < 10).mean(),
               "meets 80% margin": Cv[v + "|ndcg"].mean() >= 0.8 * base})
tn = pd.DataFrame(tn).sort_values(["meets 80% margin", "tag distance gain"], ascending=[False, False])

md = ["# Post-hoc diagnosis on validation players (test set not used)\n",
      f"{len(val):,} validation players with 5+ visible games. Models use the tuned settings from `best_params.json`. "
      "This is exploratory and was not pre-registered; any change it suggests would need a fresh, untouched test "
      "split to be confirmed.\n",
      "## 1. Regret\n",
      "Played picks = top-10 picks the player went on to play (hidden games). Regret = played < 120 min. "
      "`regret_but_enjoyed` = share of regret picks that still count as enjoyed under the Layer 1 label "
      "(top half of that game's players: short games played through). `not_enjoyed` = share of played picks "
      "below the label.\n",
      reg.round(4).to_markdown(),
      "\n### Regret by game popularity (share of training players; bins over picked games)\n",
      by_pop.round(4).to_markdown(),
      "\n### Popularity mix of played picks\n",
      mix.round(4).to_markdown(),
      "\n## 2. Try something new: accuracy vs exploration\n",
      f"For you (Hybrid-EASE) NDCG@10 on validation: {base:.4f}. The 80% margin needs >= {0.8 * base:.4f}. "
      "`filter` keeps games from the hybrid's top `pool` with a tag below `th` share of the player's tag profile "
      "(th=0: a tag the player has never played; the shipped rule is pool=400 th=0.02). `rerank` sorts the top 400 by "
      "z(score) + lambda x tag distance.\n",
      tn.round(4).to_markdown(index=False)]
(HERE / "diagnosis_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(md))
