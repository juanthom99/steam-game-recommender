"""Learned enjoyment score: P(enjoyed | playtime signals), weakly supervised by review flags.

Only signals a live user's Steam library provides are allowed (playtime_forever per game) plus each game's
*typical length*. No popularity, no review counts, no user review habits: the score must rank a user's games
against each other, not say which games are good in general.

Metrics (report users; thresholds and models fit on calibration users):
  AUC          pooled ROC-AUC vs review flag (can be inflated by game quality)
  within-game  mean per-game AUC (games with >= 30 report reviews and >= 5 of each class), weighted by reviews:
               does the score separate a game's fans from its non-fans?  <- primary
  within-user  same, per user (users with >= 5 reviews and both classes): does it rank a user's favorites higher?

Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python label/enjoy_score.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

D = Path("C:/Users/juant/data_clean")
HERE = Path(__file__).resolve().parent
KAGGLE_USER_SHARE = 0.25          # sample of Kaggle users (speed); every statistic is computed inside the sample

cat = pd.read_parquet(D / "games.parquet", columns=["app_id", "steamspy_median_playtime_min", "tags"]).set_index("app_id")
main_tag = cat.tags.map(lambda l: l[0] if len(l) else "none")


def build(df):
    """Feature table from (user_key, app_id, playtime_min). All stats from the given rows only."""
    df = df.copy()
    t = df.playtime_min.astype("float64")
    lt = np.log1p(t)
    df["hours"] = lt
    gp = df.groupby("app_id").playtime_min
    df["g"] = gp.rank(pct=True)
    med = gp.transform("median")
    length = df.app_id.map(cat.steamspy_median_playtime_min).fillna(med)
    df["log_len"] = np.log1p(length)                                  # typical length (not popularity)
    df["ratio_len"] = lt - df.log_len
    df["bucket_q"] = df.groupby(pd.qcut(df.log_len, 10, labels=False, duplicates="drop")).playtime_min.rank(pct=True)
    # user + game expected playtime (two-way fixed effects, shrunk)
    mu = lt.mean()
    bi = pd.Series(0.0, index=df.app_id.unique())
    for _ in range(8):
        bu = (lt - mu - df.app_id.map(bi).to_numpy()).groupby(df.user_key).sum() / (df.groupby("user_key").size() + 5)
        bi = (lt - mu - df.user_key.map(bu).to_numpy()).groupby(df.app_id).sum() / (df.groupby("app_id").size() + 5)
    df["resid"] = lt - mu - df.user_key.map(bu).to_numpy() - df.app_id.map(bi).to_numpy()
    up = df.groupby("user_key")
    df["u_rank"] = up.playtime_min.rank(pct=True)
    df["u_med"] = up.hours.transform("median")                          # how heavy a player this user is
    df["u_ratio_rank"] = up.ratio_len.rank(pct=True)                    # rank of length-adjusted playtime in own library
    # genre-relative: rank among players of games sharing the main tag, and the user's affinity for that tag
    df["tag"] = df.app_id.map(main_tag).fillna("none")
    df["tag_q"] = df.groupby("tag").ratio_len.rank(pct=True)
    tag_hours = df.groupby(["user_key", "tag"]).hours.transform("sum")
    df["u_tag_share"] = tag_hours / up.hours.transform("sum").replace(0, np.nan)
    df["u_tag_n"] = np.log1p(df.groupby(["user_key", "tag"]).app_id.transform("size"))
    return df


V1 = ["hours", "g", "ratio_len", "bucket_q", "resid", "u_rank"]                      # the adopted first version
V2 = V1 + ["u_med", "u_ratio_rank"]                                                   # + user context
V3 = V2 + ["tag_q", "u_tag_share", "u_tag_n"]                                         # + genre-relative
MONO = {"hours": 1, "g": 1, "ratio_len": 1, "bucket_q": 1, "resid": 1, "u_rank": 1, "u_ratio_rank": 1, "tag_q": 1}


def model(cols, mono):
    cst = [MONO.get(c, 0) for c in cols] if mono else None
    return HistGradientBoostingClassifier(max_iter=400, learning_rate=0.05, max_leaf_nodes=31, l2_regularization=1.0,
                                          monotonic_cst=cst, random_state=0)


def grouped_auc(y, s, key, min_n, min_class):
    d = pd.DataFrame({"y": y, "s": s, "k": key})
    out, w = [], []
    for _, x in d.groupby("k"):
        pos = x.y.sum()
        if len(x) >= min_n and pos >= min_class and len(x) - pos >= min_class:
            out.append(roc_auc_score(x.y, x.s)); w.append(len(x))
    return np.average(out, weights=w) if out else np.nan, len(out)


def metrics(y, s, df):
    wg, ng = grouped_auc(y, s, df.app_id.to_numpy(), 30, 5)
    wu, nu = grouped_auc(y, s, df.user_key.to_numpy(), 5, 1)
    return {"AUC": roc_auc_score(y, s), "within-game AUC": wg, "games": ng, "within-user AUC": wu, "users": nu}


def load():
    m = pd.read_parquet(D / "interactions_mcauley.parquet",
                        columns=["user_key", "app_id", "playtime_min", "played", "history_ok", "review_recommend"])
    m = build(m[m.played & m.history_ok])
    m = m[m.review_recommend.notna()].copy()
    m["ds"] = "McAuley"
    k = pd.read_parquet(D / "interactions_kaggle.parquet",
                        columns=["user_key", "app_id", "playtime_min", "played", "history_ok", "bulk_user", "review_recommend"])
    k = k[k.played & k.history_ok & ~k.bulk_user]
    users = k.user_key.drop_duplicates().sample(frac=KAGGLE_USER_SHARE, random_state=0)
    k = build(k[k.user_key.isin(users)].drop(columns=["played", "history_ok", "bulk_user"]))
    k["ds"] = "Kaggle"
    return pd.concat([m, k], ignore_index=True)


if __name__ == "__main__":
    a = load()
    a["y"] = a.review_recommend.astype(bool)
    a["cal"] = a.user_key % 2 == 0
    print({d: int((a.ds == d).sum()) for d in a.ds.unique()}, flush=True)
    rows = []

    def report(name, score_fn):
        for ds in ("McAuley", "Kaggle"):
            r = a[(a.ds == ds) & ~a.cal]
            rows.append({"variant": name, "dataset": ds, **metrics(r.y.to_numpy(), score_fn(r), r)})
            print(rows[-1], flush=True)

    report("2-hour floor (hours)", lambda r: r.hours.to_numpy())
    report("resid (best single formula)", lambda r: r.resid.to_numpy())
    variants = [("V1 per-dataset", V1, False, False), ("V1 pooled", V1, False, True), ("V1 pooled + monotonic", V1, True, True),
                ("V2 pooled + monotonic", V2, True, True), ("V3 pooled + monotonic", V3, True, True),
                ("V3 pooled, free", V3, False, True)]
    fitted = {}
    for name, cols, mono, pooled in variants:
        if pooled:
            c = a[a.cal]
            # balance the datasets so Kaggle's size doesn't drown McAuley (live users look like McAuley)
            wts = np.where(c.ds == "McAuley", (c.ds != "McAuley").sum() / max((c.ds == "McAuley").sum(), 1), 1.0)
            mdl = model(cols, mono).fit(c[cols], c.y, sample_weight=wts)
            fitted[name] = (mdl, cols)
            report(name, lambda r: mdl.predict_proba(r[cols])[:, 1])
        else:
            mods = {ds: model(cols, mono).fit(a[(a.ds == ds) & a.cal][cols], a[(a.ds == ds) & a.cal].y) for ds in ("McAuley", "Kaggle")}
            report(name, lambda r: mods[r.ds.iloc[0]].predict_proba(r[cols])[:, 1])
    t = pd.DataFrame(rows)
    (HERE / "enjoy_score_results.md").write_text(
        "# Enjoyment score variants\n\nReport users only. Primary metric: within-game AUC.\n\n" + t.round(3).to_markdown(index=False) + "\n",
        encoding="utf-8")
    import pickle
    pickle.dump(fitted, open(HERE / "cache" / "enjoy_models.pkl", "wb"))
    print(t.round(3).to_string())
