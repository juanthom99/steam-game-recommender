"""Shared profiling helpers (data:explore-data checklist) used by profile_all.py and profile_mcauley.py.
"""
import ast
import gzip
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import dotenv_values

HERE = Path(__file__).resolve().parent
OUT = HERE / "profiles"
OUT.mkdir(exist_ok=True)
KAGGLE = Path(os.path.expanduser("~/.cache/kagglehub/datasets/antonkozyriev/game-recommendations-on-steam/versions/28"))
MCAULEY = Path(os.path.expanduser("~/data_raw/mcauley/australian_users_items.json.gz"))
TODAY = pd.Timestamp("2026-10-28")
PLACEHOLDERS = {"", "n/a", "na", "none", "null", "tbd", "test", "xxx", "-", "?"}
SUMMARY, PROFILES = [], {}


# ---------------------------------------------------------------- column profiling
def classify(name, s):
    n = name.lower()
    if n in ("app_id", "appid", "user_id", "review_id", "id", "steamid") or n.endswith("_id") or n.endswith("id") and pd.api.types.is_integer_dtype(s):
        return "Identifier"
    if pd.api.types.is_bool_dtype(s):
        return "Boolean"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "Temporal"
    if s.dropna().map(lambda v: isinstance(v, (list, dict))).any() if s.dtype == object else False:
        return "Structural"
    if pd.api.types.is_numeric_dtype(s):
        return "Dimension" if s.nunique() <= 12 else "Metric"
    st = s.dropna().astype(str)
    if len(st) and (st.str.len().mean() > 60):
        return "Text"
    return "Dimension" if s.nunique() <= max(50, 0.01 * len(s)) else "Text"


def grade(nonnull):
    return ("Green" if nonnull > 0.99 else "Yellow" if nonnull >= 0.95 else "Orange" if nonnull >= 0.80 else "Red")


def fmt_top(vc, k=5):
    tot = vc.sum()
    return "; ".join(f"{str(i)[:28]} ({c / tot:.1%})" for i, c in vc.head(k).items())


def profile_df(name, df, grain, key=None, notes=()):
    L = [f"# Data Profile: {name}\n", "## Overview", f"- Grain: one row per {grain}",
         f"- Rows: {len(df):,} | Columns: {df.shape[1]} | Memory: {df.memory_usage(deep=True).sum() / 1e6:,.1f} MB"]
    classes = {c: classify(c, df[c]) for c in df.columns}
    counts = pd.Series(classes).value_counts().to_dict()
    L.append("- Column types: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
    dates = [c for c, k in classes.items() if k == "Temporal"]
    for c in dates:
        L.append(f"- Date range `{c}`: {df[c].min()} to {df[c].max()}")
    issues = []
    if key:
        dup = df.duplicated(key).sum()
        L.append(f"- Primary key `{key}` unique: {dup == 0} ({dup:,} duplicates)")
        if dup:
            issues.append(("High", f"`{key}` has {dup:,} duplicate rows"))
    L += [f"- {n}" for n in notes]

    rows = []
    for c in df.columns:
        s, k = df[c], classes[c]
        nonnull = s.notna().mean()
        hashable = s if k != "Structural" else s.map(lambda v: json.dumps(v, sort_keys=True, default=str))
        nun = hashable.nunique()
        vc = hashable.value_counts()
        r = {"column": c, "class": k, "dtype": str(s.dtype), "null %": round(100 * (1 - nonnull), 2),
             "completeness": grade(nonnull), "distinct": nun, "card.": round(nun / max(len(s), 1), 4),
             "top values": fmt_top(vc), "rarest": "; ".join(str(i)[:20] for i in vc.tail(3).index)}
        if k in ("Metric", "Dimension") and pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            x = s.dropna().astype(float)
            if len(x):
                q = x.quantile([.01, .05, .25, .5, .75, .95, .99]).round(2).tolist()
                r["stats"] = (f"min {x.min():.2f} / p1 {q[0]} / p5 {q[1]} / p25 {q[2]} / p50 {q[3]} / p75 {q[4]} / "
                              f"p95 {q[5]} / p99 {q[6]} / max {x.max():.2f}; mean {x.mean():.2f} sd {x.std():.2f}; "
                              f"zeros {(x == 0).sum():,}; neg {(x < 0).sum():,}; skew {x.skew():.1f}")
                if (x < 0).any():
                    issues.append(("High", f"`{c}` has {(x < 0).sum():,} negative values"))
                if abs(x.skew()) > 5:
                    issues.append(("Info", f"`{c}` is heavily skewed (skew {x.skew():.1f}): use medians/log scale, not means"))
                top_share = vc.iloc[0] / vc.sum() if len(vc) else 0
                if k == "Metric" and top_share > 0.5:
                    issues.append(("Medium", f"`{c}`: one value ({vc.index[0]}) is {top_share:.0%} of rows (default/placeholder?)"))
        elif k in ("Text", "Dimension") and not pd.api.types.is_numeric_dtype(s):
            st = s.dropna().astype(str)
            if len(st):
                ln = st.str.len()
                empty = (st.str.strip() == "").sum()
                ws = (st != st.str.strip()).sum()
                ph = st.str.strip().str.lower().isin(PLACEHOLDERS).sum()
                case = ("upper" if st.str.isupper().all() else "lower" if st.str.islower().all() else "mixed")
                r["stats"] = (f"len min {ln.min()} / avg {ln.mean():.0f} / max {ln.max()}; empty {empty:,}; "
                              f"lead/trail whitespace {ws:,}; placeholders {ph:,}; case {case}")
                if empty / len(s) > 0.05:
                    issues.append(("High" if empty / len(s) > 0.2 else "Medium", f"`{c}`: {empty / len(s):.1%} empty strings"))
                if ws:
                    issues.append(("Low", f"`{c}`: {ws:,} values with leading/trailing whitespace"))
                bad = st.str.contains("\ufffd").sum()
                if bad:
                    issues.append(("Low", f"`{c}`: {bad:,} values contain the replacement character (encoding issue)"))
                if k == "Dimension":
                    norm = st.str.strip().str.lower()
                    if norm.nunique() < st.nunique():
                        issues.append(("Low", f"`{c}`: {st.nunique() - norm.nunique()} values differ only by case/whitespace"))
        elif k == "Temporal":
            d = s.dropna()
            if len(d):
                fut = (d > TODAY).sum()
                by_year = d.dt.year.value_counts().sort_index()
                gaps = sorted(set(range(int(by_year.index.min()), int(by_year.index.max()) + 1)) - set(by_year.index))
                r["stats"] = f"min {d.min()} / max {d.max()}; future {fut:,}; years w/ no rows {gaps or 'none'}"
                if fut:
                    issues.append(("High", f"`{c}`: {fut:,} dates after {TODAY.date()}"))
        elif k == "Boolean":
            r["stats"] = f"true {s.sum():,} / false {(~s.astype(bool)).sum():,}; true rate {s.mean():.1%}"
            if s.nunique() == 1:
                issues.append(("Medium", f"`{c}` is constant ({s.iloc[0]}): carries no information"))
        elif k == "Structural":
            lens = s.dropna().map(lambda v: len(v) if hasattr(v, "__len__") else 0)
            r["stats"] = f"length min {lens.min()} / median {lens.median():.0f} / max {lens.max()}; empty {(lens == 0).sum():,}"
            if (lens == 0).mean() > 0.05:
                issues.append(("Medium", f"`{c}`: {(lens == 0).mean():.1%} empty lists"))
        elif k == "Identifier":
            if pd.api.types.is_numeric_dtype(s):
                r["stats"] = f"min {s.min()} / max {s.max()}; card. {nun / max(len(s), 1):.3f}"
        if 1 - nonnull > 0.20:
            issues.append(("High", f"`{c}`: {100 * (1 - nonnull):.1f}% null (alert)"))
        elif 1 - nonnull > 0.05:
            issues.append(("Medium", f"`{c}`: {100 * (1 - nonnull):.1f}% null (warn)"))
        rows.append(r)

    tab = pd.DataFrame(rows)
    tab["order"] = tab["class"].map({"Identifier": 0, "Dimension": 1, "Metric": 2, "Temporal": 3, "Boolean": 4, "Text": 5, "Structural": 6})
    L.append("\n## Column Details (grouped by class)\n")
    L.append(tab.sort_values(["order", "column"]).drop(columns=["order"]).fillna("").to_markdown(index=False))
    L.append("\n## Data Quality Issues\n")
    order = {"High": 0, "Medium": 1, "Low": 2, "Info": 3}
    issues = sorted(set(issues), key=lambda t: order[t[0]])
    L += [f"- **{sev}**: {msg}" for sev, msg in issues] or ["- None flagged by the automatic checks."]
    worst = tab.completeness.map({"Green": 0, "Yellow": 1, "Orange": 2, "Red": 3}).max()
    SUMMARY.append({"source": name, "grain": grain, "rows": len(df), "columns": df.shape[1],
                    "worst completeness": ["Green", "Yellow", "Orange", "Red"][int(worst)],
                    "high issues": sum(1 for s, _ in issues if s == "High"),
                    "medium issues": sum(1 for s, _ in issues if s == "Medium")})
    PROFILES[name] = L
    return L


def add_section(name, title, body):
    PROFILES[name] += [f"\n## {title}\n", body]


def write(name, fname):
    (OUT / fname).write_text("\n".join(PROFILES[name]) + "\n", encoding="utf-8")
    print("wrote", fname, flush=True)




def write_readme():
    """Merge this run's scorecard rows into profiles/summary.json and rebuild README.md."""
    sp = OUT / "summary.json"
    old = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else []
    new = {r["source"]: r for r in old}
    for r in SUMMARY:
        new[r["source"]] = {k: (int(v) if isinstance(v, np.integer) else v) for k, v in r.items()}
    sp.write_text(json.dumps(list(new.values()), indent=2), encoding="utf-8")
    summ = pd.DataFrame(list(new.values()))
    files = ", ".join(f"[{f.name}]({f.name})" for f in sorted(OUT.glob("*.md")) if f.name not in ("README.md", "FINDINGS.md"))
    idx = ["# Data Profiles: all sources", "",
           "One profile per source, same checklist: structure, column classes, completeness grade "
           "(Green > 99% non-null, Yellow 95-99, Orange 80-95, Red < 80), distributions, quality flags, relationships. "
           "Cross-source conclusions: [FINDINGS.md](FINDINGS.md).", "",
           summ.to_markdown(index=False), "", "Files: " + files]
    (OUT / "README.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    print(summ.to_string())
