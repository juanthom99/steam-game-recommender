#!/bin/sh
# Run 2 (PROTOCOL section 8, change 4). Waits for the SteamSpy refill, then:
# merge tags/prices -> data dictionary -> re-embed the catalog -> retune both hybrids on validation
# -> score the test set (second time, disclosed) -> Layer 3. Run 1 is archived in eval/run1/.
cd "$(dirname "$0")/.."
PY=/c/Users/juant/.venvs/steamrec-ml/Scripts/python
REFILL_PID=${1:-24996}
export PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1
step() { echo "=== $1 $(date)"; }
fail() { echo "FAILED: $1"; exit 1; }

while tasklist //FI "PID eq $REFILL_PID" 2>/dev/null | grep -q "$REFILL_PID"; do sleep 300; done
step "refill finished: $(wc -l < /c/Users/juant/data_raw/steamspy/appdetails.jsonl) rows"

cp -n /c/Users/juant/data_clean/games.parquet /c/Users/juant/data_clean/games.before_steamspy.parquet
step merge;      $PY clean/merge_steamspy.py   > clean/merge_steamspy.log 2>&1 || fail merge;  tail -1 clean/merge_steamspy.log
step dictionary; $PY clean/data_dictionary.py  > clean/data_dictionary.log 2>&1 || fail dictionary
step embed;      $PY model/embed_catalog.py    > model/embed_catalog.log 2>&1 || fail embed;    tail -1 model/embed_catalog.log

# content-free models keep their validation tuning (identical inputs); both hybrids are retuned
$PY - <<'EOF' || fail "reset hybrid tuning"
import json
p = "eval/cache/tuning_rows.jsonl"
rows = [json.loads(l) for l in open(p)]
keep = [r for r in rows if r["model"] not in ("Hybrid", "Hybrid-EASE")]
open(p, "w").write("".join(json.dumps(r) + "\n" for r in keep))
print(f"kept {len(keep)} tuning rows, dropped {len(rows) - len(keep)} hybrid rows")
EOF
step tune;       $PY eval/tune.py Hybrid Hybrid-EASE > eval/tune_run2.log 2>&1 || fail tune
step test;       $PY eval/run_test.py > eval/run_test.log 2>&1 || { tail -20 eval/run_test.log; fail test; }
step layer3;     $PY eval/layer3.py   > eval/layer3.log   2>&1 || { tail -20 eval/layer3.log; fail layer3; }

note="> **Run 2** (PROTOCOL section 8, change 4): completed tags and full-catalog content embeddings; the test set's second use, disclosed. Run 1, the pre-registered result: \`eval/run1/\`."
for f in eval/eval_report.md eval/layer3_report.md; do
  { head -1 "$f"; echo; echo "$note"; tail -n +2 "$f"; } > "$f.tmp" && mv "$f.tmp" "$f"
done
step done
