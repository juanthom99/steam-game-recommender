"""Write rule G25 content levels (clean/flag_explicit.py) to Supabase public.games. Updates only; deletes nothing.
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python index/update_content_levels.py
"""
from pathlib import Path

import sys
import time

import pandas as pd
from dotenv import dotenv_values
from supabase import create_client

ROOT = Path(__file__).resolve().parent.parent
g = pd.read_parquet("C:/Users/juant/data_clean/games.parquet", columns=["app_id", "recommendable", "explicit", "content_level", "explicit_reason"])
g = g[g.recommendable & g.content_level.ne("none")]
if len(sys.argv) > 1:                                   # optional: only these reasons, e.g. "tag:Sexual Content; tag:Nudity"
    g = g[g.explicit_reason.isin(sys.argv[1:])]
env = dotenv_values(ROOT / ".env")
sb = create_client(env["SUPABASE_URL"], env["SUPABASE_SERVICE_ROLE_KEY"])
n = 0
for (lvl, why, ex), part in g.groupby(["content_level", "explicit_reason", "explicit"]):
    ids = part.app_id.astype(int).tolist()
    for k in range(0, len(ids), 5):           # small batches: each update also re-inserts into the HNSW index
        for attempt in range(5):
            try:
                sb.table("games").update({"content_level": lvl, "explicit_reason": why, "explicit": bool(ex)}).in_("app_id", ids[k:k + 5]).execute()
                break
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(3 * (attempt + 1))
    n += len(ids)
    print(f"{lvl:14s} {why:40s} {len(ids):5d}", flush=True)
print(f"updated {n:,} rows")
