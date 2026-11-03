#!/bin/sh
# Waits for the running ALS/Hybrid tuning, then: tune Hybrid-EASE -> score the test set once -> Layer 3.
cd "$(dirname "$0")/.."
PY=/c/Users/juant/.venvs/steamrec-ml/Scripts/python
while tasklist //FI "PID eq 5588" 2>/dev/null | grep -q 5588; do sleep 60; done
echo "=== tune Hybrid-EASE $(date)"
OPENBLAS_NUM_THREADS=1 PYTHONUTF8=1 $PY eval/tune.py Hybrid-EASE >> eval/tune.log 2>&1 || { echo "tune failed"; exit 1; }
echo "=== run_test $(date)"
OPENBLAS_NUM_THREADS=1 PYTHONUTF8=1 $PY eval/run_test.py > eval/run_test.log 2>&1 || { echo "run_test failed"; tail -20 eval/run_test.log; exit 1; }
echo "=== layer3 $(date)"
PYTHONUTF8=1 $PY eval/layer3.py > eval/layer3.log 2>&1 || { echo "layer3 failed"; tail -20 eval/layer3.log; exit 1; }
echo "=== done $(date)"
