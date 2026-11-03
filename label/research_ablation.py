"""Where does the combined model's gain come from? Refit with feature groups removed (report-user AUC)."""
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
here = Path(__file__).resolve().parent
src = open(here / "research_labels.py", encoding="utf-8").read().split("results = []")[0]
ns = {"__file__": str(here / "research_labels.py")}; exec(src, ns); scores, D = ns["scores"], ns["D"]

def prep(df):
    df["u_rank"] = df.groupby("user_key").playtime_min.rank(pct=True)
    df["n_lib"] = np.log1p(df.groupby("user_key").app_id.transform("size"))
    df["game_pop"] = np.log1p(df.n_players)
    return df
SETS = {
    "all features": ["hours", "g", "ratio_ext", "bucket_q", "resid", "u_rank", "n_lib", "game_pop"],
    "playtime-only (no game_pop, no n_lib)": ["hours", "g", "ratio_ext", "bucket_q", "resid", "u_rank"],
    "without game_pop": ["hours", "g", "ratio_ext", "bucket_q", "resid", "u_rank", "n_lib"],
    "without n_lib": ["hours", "g", "ratio_ext", "bucket_q", "resid", "u_rank", "game_pop"],
    "game_pop alone": ["game_pop"],
    "n_lib alone": ["n_lib"],
    "u_rank alone": ["u_rank"],
}
rows = []
def run(df, name):
    y = df.review_recommend.astype(bool).to_numpy(); cal = (df.user_key % 2 == 0).to_numpy()
    for s, cols in SETS.items():
        m = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, random_state=0).fit(df.loc[cal, cols], y[cal])
        rows.append((name, s, round(roc_auc_score(y[~cal], m.predict_proba(df.loc[~cal, cols])[:, 1]), 3)))
        print(rows[-1], flush=True)
m = pd.read_parquet(D / "interactions_mcauley.parquet", columns=["user_key","app_id","playtime_min","played","history_ok","review_recommend"])
m = prep(scores(m[m.played & m.history_ok])); run(m[m.review_recommend.notna()].copy(), "McAuley")
k = pd.read_parquet(D / "interactions_kaggle.parquet", columns=["user_key","app_id","playtime_min","played","history_ok","bulk_user","review_recommend"])
k = prep(scores(k[k.played & k.history_ok & ~k.bulk_user].drop(columns=["played","history_ok","bulk_user"])))
run(k.sample(3_000_000, random_state=0).copy(), "Kaggle")
t = pd.DataFrame(rows, columns=["dataset", "features", "ROC-AUC"])
with open(here / "label_research.md", "a", encoding="utf-8") as f:
    f.write("\n## Ablation: what drives the combined model\n\n" + t.to_markdown(index=False) + "\n")
