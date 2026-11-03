"""Does combining behavior signals beat any single playtime formula? (weakly supervised by review flags)
Trains on calibration users, reports ROC-AUC on report users. Run after research_labels.py."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util
spec = importlib.util.spec_from_file_location("rl", Path(__file__).resolve().parent / "research_labels.py")
src = open(spec.origin, encoding="utf-8").read().split("results = []")[0]   # reuse scores() only
ns = {"__file__": spec.origin}; exec(src, ns); scores = ns["scores"]; D = ns["D"]

def feats(df, has2w):
    df["u_rank"] = df.groupby("user_key").playtime_min.rank(pct=True)        # rank inside the user's own library
    df["n_lib"] = np.log1p(df.groupby("user_key").app_id.transform("size"))
    df["game_pop"] = np.log1p(df.n_players)
    cols = ["hours", "g", "ratio_ext", "bucket_q", "resid", "u_rank", "n_lib", "game_pop"]
    if has2w:
        df["active_2w"] = (df.playtime_2w_min.fillna(0) > 0).astype(int)
        df["log_2w"] = np.log1p(df.playtime_2w_min.fillna(0))
        cols += ["active_2w", "log_2w"]
    return cols

out = []
def run(df, name, has2w):
    cols = feats(df, has2w)
    y = df.review_recommend.astype(bool).to_numpy(); cal = (df.user_key % 2 == 0).to_numpy()
    m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, random_state=0)
    m.fit(df.loc[cal, cols], y[cal]); p = m.predict_proba(df.loc[~cal, cols])[:, 1]
    base = roc_auc_score(y[~cal], df.loc[~cal, "resid+floor"])
    out.append((name, "best single formula (resid+floor)", round(base, 3)))
    out.append((name, "combined model, " + ("with" if has2w else "no") + " 2-week signal", round(roc_auc_score(y[~cal], p), 3)))
    if has2w:
        out.append((name, "AUC of 'played in last 2 weeks' alone", round(roc_auc_score(y[~cal], df.loc[~cal, "log_2w"]), 3)))
        m2 = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=0)
        c2 = [c for c in cols if c not in ("active_2w", "log_2w")]
        m2.fit(df.loc[cal, c2], y[cal])
        out.append((name, "combined model, no 2-week signal", round(roc_auc_score(y[~cal], m2.predict_proba(df.loc[~cal, c2])[:, 1]), 3)))

m = pd.read_parquet(D / "interactions_mcauley.parquet", columns=["user_key","app_id","playtime_min","playtime_2w_min","played","history_ok","review_recommend"])
m = scores(m[m.played & m.history_ok]); m = m[m.review_recommend.notna()].copy()
run(m, "McAuley", True)
k = pd.read_parquet(D / "interactions_kaggle.parquet", columns=["user_key","app_id","playtime_min","played","history_ok","bulk_user","review_recommend"])
k = scores(k[k.played & k.history_ok & ~k.bulk_user].drop(columns=["played","history_ok","bulk_user"]))
k = feats_k = k.sample(3_000_000, random_state=0) if len(k) > 3_000_000 else k
run(k.copy(), "Kaggle (3M-row sample; scores computed on all rows)", False)
t = pd.DataFrame(out, columns=["dataset", "method", "ROC-AUC (report users)"])
print(t.to_string())
with open(Path(__file__).resolve().parent / "label_research.md", "a", encoding="utf-8") as f:
    f.write("\n## Combining signals (gradient-boosted model trained on calibration users' review flags)\n\n" + t.to_markdown(index=False) + "\n")
