"""Load the evaluation reports into Supabase public.eval_results (long format), so the team can query and chart them.

Parses every markdown table in the reports below; the report files stay the source of truth.
Table: supabase/migrations/20261104_03_eval_results.sql. Replaces all rows of each report it loads.
Uses SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY from .env (never printed).
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python dashboard/load_eval_supabase.py [--dry-run]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = {"layer2": "eval/eval_report.md", "layer3": "eval/layer3_report.md", "layer3_prices": "eval/layer3_prices.md",
           "diagnosis": "eval/diagnosis_report.md", "diagnosis_value": "eval/diagnosis_value.md",
           "layer2_run1": "eval/run1/eval_report.md", "layer3_run1": "eval/run1/layer3_report.md", "team_comparison": "team_eval/results.md"}


def num(s):
    t = s.replace("*", "").replace(",", "").strip()
    m = re.fullmatch(r"[+-]?\d+(\.\d+)?([eE][+-]?\d+)?%?", t)
    if not m:
        return None
    return float(t[:-1]) / 100 if t.endswith("%") else float(t)


def parse(text, report):
    rows, section, lines = [], "", text.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("#"):
            section = ln.lstrip("#").strip()
        if ln.startswith("|") and i + 1 < len(lines) and re.fullmatch(r"\|[\s:|-]+\|", lines[i + 1].strip()):
            head = [c.strip() for c in ln.strip("|").split("|")]
            i += 2
            seq = 0
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                for h, c in zip(head[1:], cells[1:]):
                    rows.append({"report": report, "section": section or "(top)", "row_label": cells[0].replace("*", ""),
                                 "metric": h, "value": num(c), "value_text": c, "seq": seq})
                seq += 1
                i += 1
            continue
        i += 1
    return rows


def main():
    out = {}
    for rep, f in REPORTS.items():
        p = ROOT / f
        if p.exists():
            out[rep] = parse(p.read_text(encoding="utf-8"), rep)
            print(f"{rep}: {len(out[rep])} cells from {f}")
        else:
            print(f"{rep}: {f} missing, skipped")
    if "--dry-run" in sys.argv:
        print(next(iter(out.values()))[:3])
        return
    from dotenv import dotenv_values
    from supabase import create_client
    env = dotenv_values(ROOT / ".env")
    sb = create_client(env["SUPABASE_URL"], env["SUPABASE_SERVICE_ROLE_KEY"])
    for rep, recs in out.items():
        sb.table("eval_results").delete().eq("report", rep).execute()
        for k in range(0, len(recs), 500):
            sb.table("eval_results").insert(recs[k:k + 500]).execute()
    print("done")


if __name__ == "__main__":
    main()
