"""Upload the team evaluation package to Supabase Storage (private bucket "team-eval").

Uploads every file in data_clean/team_eval/ plus evaluate.py, example_model.py and README.md from this folder.
The bucket is private: teammates download from the Supabase dashboard (Storage > team-eval) or with a project key.
Free plan: 50 MB per file, 1 GB total storage (separate from the 500 MB database).
  PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python team_eval/upload_supabase.py [file names...]
"""
import sys
import time
from pathlib import Path

from supabase import create_client

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = Path("C:/Users/juant/data_clean/team_eval")
BUCKET = "team-eval"
env = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))
sb = create_client(env["SUPABASE_URL"].strip(), env["SUPABASE_SERVICE_ROLE_KEY"].strip())

if BUCKET not in [b.name for b in sb.storage.list_buckets()]:
    sb.storage.create_bucket(BUCKET, options={"public": False})
    print(f"created private bucket {BUCKET}")
files = sorted(DATA.glob("*.parquet")) + [HERE / n for n in ("evaluate.py", "example_model.py", "README.md", "results.md")]
if sys.argv[1:]:                                         # upload only the named files
    files = [f for f in files if f.name in sys.argv[1:]]
too_big = [f.name for f in files if f.stat().st_size > 49 * 1024 * 1024]
if too_big:
    raise SystemExit(f"over the 50 MB file limit: {too_big}")
total = sum(f.stat().st_size for f in files)
print(f"{len(files)} files, {total / 1e6:.0f} MB")
for f in files:
    for attempt in range(4):
        try:
            sb.storage.from_(BUCKET).upload(f.name, f.read_bytes(),
                                            {"content-type": "text/plain" if f.suffix in (".py", ".md") else "application/octet-stream",
                                             "upsert": "true"})
            print(f"  {f.name} ({f.stat().st_size / 1e6:.1f} MB)", flush=True)
            break
        except Exception as e:                                    # transient network errors: retry
            if attempt == 3:
                raise
            print(f"  retry {f.name}: {str(e)[:120]}", flush=True)
            time.sleep(5 * (attempt + 1))
print("listed in bucket:", len(sb.storage.from_(BUCKET).list()))
