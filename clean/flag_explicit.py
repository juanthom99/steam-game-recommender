"""Rule G25: content levels for sexual and mature content. Nothing is removed (transparency).

  content_level = 'explicit'       sexual content is the point of the game: G17 adult (Steam content descriptor),
                                   a 'Hentai' or 'NSFW' user tag, or 'hentai' in the title.
                                   Hidden from recommendations unless the player turns on "Show adult games" (off by default).
                  'sexual_themes'  a 'Sexual Content' or 'Nudity' user tag in an otherwise mainstream game
                                   (e.g. The Witcher 2, Far Cry 3). Shown normally.
                  'mature'         Steam's 18+ age gate (mostly violence). Shown normally.
                  'none'
  explicit        = content_level == 'explicit'
  explicit_reason = which signals set the level (e.g. 'tag:Hentai; title'), empty for 'none'.
Limits: user tags are crowd-sourced and noisy (FIFA 22 has a 'Nudity' tag); an explicit game nobody tagged is missed.
Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python clean/flag_explicit.py   (then clean/data_dictionary.py)
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
GAMES = Path("C:/Users/juant/data_clean/games.parquet")
HARD, SOFT = ("Hentai", "NSFW"), ("Sexual Content", "Nudity")

g = pd.read_parquet(GAMES)
tags = g.tags.map(lambda t: set(t) if t is not None else set())
adult = g.adult.fillna(False).astype(bool)
title = g.title.fillna("").str.contains(r"\bhentai\b", case=False, regex=True)
mature = g.mature_18.fillna(False).astype(bool)


def reasons(i):
    hard = (["steam:adult_descriptor"] if adult.iat[i] else []) + [f"tag:{t}" for t in HARD if t in tags.iat[i]] + \
           (["title:hentai"] if title.iat[i] else [])
    if hard:
        return "explicit", "; ".join(hard)
    soft = [f"tag:{t}" for t in SOFT if t in tags.iat[i]]
    if soft:
        return "sexual_themes", "; ".join(soft)
    if mature.iat[i]:
        return "mature", "steam:mature_18"
    return "none", ""


lv = [reasons(i) for i in range(len(g))]
g["content_level"] = [a for a, _ in lv]
g["explicit_reason"] = [b for _, b in lv]
g["explicit"] = g.content_level.eq("explicit")
g.to_parquet(GAMES, index=False)

r = g[g.recommendable]
counts = r.content_level.value_counts()
newly = int((g.explicit & ~adult).sum())
row = (f"| G25  | Catalog             | Content levels: explicit / sexual_themes / mature (flagged, not removed) | {newly} | "
       "content_level, explicit, explicit_reason; only 'explicit' is hidden, and only unless the player opts in | "
       f"G17 used Steam content descriptors most new games lack; recommendable: {counts.get('explicit', 0)} explicit, "
       f"{counts.get('sexual_themes', 0)} sexual themes, {counts.get('mature', 0)} mature |")
rep = ROOT / "clean" / "cleaning_report.md"
lines = [l for l in rep.read_text(encoding="utf-8").rstrip("\n").splitlines() if not l.startswith("| G25 ")]
rep.write_text("\n".join(lines) + "\n" + row + "\n", encoding="utf-8")
print("recommendable by level:", counts.to_dict(), "| newly explicit (not G17):", newly)
