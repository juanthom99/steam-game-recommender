"""Compare ways to turn playtime into an 'enjoyed' score, on both datasets.

Candidates (continuous scores; higher = more enjoyed):
  hours        raw log playtime (the 2-hour floor is a threshold on this)
  g            percentile of the user's playtime among that game's players
  ratio_ext    playtime / SteamSpy median playtime (external length prior from FronkonGames, Oct 2026)
  bucket_q     percentile within games of similar typical length (Zhan et al. 2022 duration buckets)
  resid        log playtime minus what is expected for this user AND this game
               (two-way fixed effects: log1p(t) ~ mu + b_user + b_game; 'relative advantage' idea)
  resid+floor  resid, but anything under 2 h scores as the minimum

Protocol: thresholds picked on calibration users (user_key % 2 == 0), metrics on report users.
Target: the user's own review flag. Kaggle bulk reviewers are excluded.
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python label/research_labels.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score, roc_auc_score

D = Path("C:/Users/juant/data_clean")
OUT = Path(__file__).resolve().parent / "label_research.md"
g_cat = pd.read_parquet(D / "games.parquet", columns=["app_id", "steamspy_median_playtime_min"]).set_index("app_id")


def scores(df):
    """df: played, history_ok rows of one dataset (user_key, app_id, playtime_min). Adds candidate scores."""
    df = df.copy()
    lt = np.log1p(df.playtime_min.astype("float64"))
    df["hours"] = lt
    df["g"] = df.groupby("app_id").playtime_min.rank(pct=True)
    df["n_players"] = df.groupby("app_id").playtime_min.transform("size")
    med = df.groupby("app_id").playtime_min.transform("median")
    ext = df.app_id.map(g_cat.steamspy_median_playtime_min)
    df["ratio_ext"] = np.log1p(df.playtime_min) - np.log1p(ext.fillna(med))
    # duration buckets: deciles of each game's typical length (external median if known, else our median)
    length = ext.fillna(med)
    df["bucket"] = pd.qcut(np.log1p(length), 10, labels=False, duplicates="drop")
    df["bucket_q"] = df.groupby("bucket").playtime_min.rank(pct=True)
    # two-way fixed effects by alternating means (8 sweeps is plenty for convergence here)
    mu = lt.mean()
    bu = pd.Series(0.0, index=df.user_key.unique())
    bi = pd.Series(0.0, index=df.app_id.unique())
    for _ in range(8):
        r = lt - mu - df.app_id.map(bi).to_numpy()
        bu = r.groupby(df.user_key).sum() / (df.groupby("user_key").size() + 5)      # shrink small users
        r = lt - mu - df.user_key.map(bu).to_numpy()
        bi = r.groupby(df.app_id).sum() / (df.groupby("app_id").size() + 5)          # shrink small games
    df["resid"] = lt - mu - df.user_key.map(bu).to_numpy() - df.app_id.map(bi).to_numpy()
    df["resid+floor"] = df.resid.where(df.playtime_min >= 120, df.resid.min() - 1)
    return df


CANDS = ["hours", "g", "ratio_ext", "bucket_q", "resid", "resid+floor"]


def evaluate(df, name):
    y = df.review_recommend.astype(bool)
    cal = df.user_key % 2 == 0
    rows = []
    for c in CANDS:
        s = df[c]
        qs = np.unique(np.quantile(s[cal], np.linspace(0.02, 0.6, 30)))
        best = max(qs, key=lambda t: cohen_kappa_score(y[cal], s[cal] >= t))
        rep = ~cal
        pred = s[rep] >= best
        rows.append({"dataset": name, "score": c,
                     "ROC-AUC": roc_auc_score(y[rep], s[rep]),
                     "kappa (tuned cut)": cohen_kappa_score(y[rep], pred),
                     "enjoyed share": pred.mean(),
                     "AUC games ≥ 20 players": roc_auc_score(y[rep & (df.n_players >= 20)], s[rep & (df.n_players >= 20)]),
                     "AUC games < 20 players": roc_auc_score(y[rep & (df.n_players < 20)], s[rep & (df.n_players < 20)])
                     if (rep & (df.n_players < 20)).sum() > 500 and y[rep & (df.n_players < 20)].nunique() == 2 else np.nan})
    # fixed 2-hour floor for reference
    rep = ~cal
    rows.append({"dataset": name, "score": "2 h floor (fixed)", "ROC-AUC": np.nan,
                 "kappa (tuned cut)": cohen_kappa_score(y[rep], df.playtime_min[rep] >= 120),
                 "enjoyed share": (df.playtime_min[rep] >= 120).mean()})
    return rows


results = []
m = pd.read_parquet(D / "interactions_mcauley.parquet", columns=["user_key", "app_id", "playtime_min", "played", "history_ok", "review_recommend"])
m = scores(m[m.played & m.history_ok])
mr = m[m.review_recommend.notna()]
print("mcauley reviewed rows", len(mr), flush=True)
results += evaluate(mr, "McAuley")
del m, mr

k = pd.read_parquet(D / "interactions_kaggle.parquet",
                    columns=["user_key", "app_id", "playtime_min", "played", "history_ok", "bulk_user", "review_recommend"])
k = k[k.played & k.history_ok & ~k.bulk_user].drop(columns=["played", "history_ok", "bulk_user"])
k = scores(k)
print("kaggle rows", len(k), flush=True)
results += evaluate(k, "Kaggle")

t = pd.DataFrame(results)
t["mean over datasets (kappa)"] = t.groupby("score")["kappa (tuned cut)"].transform("mean")
OUT.write_text("# Label research: candidate scores vs review flags\n\n"
               "Thresholds tuned on calibration users, metrics on report users. Higher is better.\n\n"
               + t.round(3).to_markdown(index=False) + "\n", encoding="utf-8")
print(t.round(3).to_string())
