"""Achievement features for the enjoyment score (stage 2).

Input per (player, game): the player's achievement list from GetPlayerAchievements and the game's global unlock
percentages from GetGlobalAchievementPercentagesForApp. Accepts the pilot format (dicts {"n","a","t"}) and the
collector format (lists [name, achieved, unlocktime]).

Features (None when the game has no achievements or the data isn't available):
  ach_depth      rarity-weighted share unlocked: sum of -log(global %) over unlocked / over all achievements
  ach_span_log   log(1 + days between first and last unlock)  - long engagement
  ach_rel        share unlocked minus the average player's share for this game (game-relative)
"""
import numpy as np

FEATURES = ["ach_depth", "ach_span_log", "ach_rel"]


def _norm(x):
    if isinstance(x, dict):
        return x.get("n") or x.get("apiname"), bool(x.get("a", x.get("achieved"))), int(x.get("t", x.get("unlocktime", 0)) or 0)
    name, achieved, t = x
    return name, bool(achieved), int(t or 0)


def ach_features(ach_list, global_pct):
    """ach_list: list of achievements (either format); global_pct: {apiname: percent 0-100} (may be empty)."""
    items = [_norm(x) for x in (ach_list or [])]
    if not items:
        return None
    pct = global_pct or {}
    w = {n: -np.log(max(pct.get(n, 50.0), 0.1) / 100) for n, _, _ in items}
    unl = [(n, t) for n, a, t in items if a]
    ts = [t for _, t in unl if t > 0]
    known = [pct[n] for n, _, _ in items if n in pct]
    frac = len(unl) / len(items)
    return {"ach_depth": sum(w[n] for n, _ in unl) / max(sum(w.values()), 1e-9),
            "ach_span_log": float(np.log1p((max(ts) - min(ts)) / 86400)) if len(ts) >= 2 else 0.0,
            "ach_rel": frac - (np.mean(known) / 100 if known else frac)}


def stage2_matrix(base_prob, feats):
    """Design matrix for the stage-2 logistic model.
    base_prob: array of stage-1 probabilities; feats: list of dicts or None per row (None = no achievement data).
    Rows without achievements get zeros in the achievement columns and has_ach = 0, so the model falls back to a
    recalibrated stage-1 score for them."""
    p = np.clip(np.asarray(base_prob, dtype=float), 1e-4, 1 - 1e-4)
    has = np.array([f is not None for f in feats], dtype=float)
    cols = [np.log(p / (1 - p)), has]
    for k in FEATURES:
        cols.append(np.array([f[k] if f is not None else 0.0 for f in feats], dtype=float))
    return np.column_stack(cols)


STAGE2_COLUMNS = ["logit_stage1", "has_ach"] + FEATURES


EXT_FEATURES = FEATURES + ["ach_n_log", "ach_unlocked_log", "ach_rarest", "ach_last_age_log", "ach_rate"]


def ach_features_ext(ach_list, global_pct, playtime_min=None, now_ts=None):
    """Base features plus: number of achievements, number unlocked, rarest unlock (-log global %), days since the
    last unlock, and unlocks per hour played (needs current playtime)."""
    base = ach_features(ach_list, global_pct)
    if base is None:
        return None
    items = [_norm(x) for x in ach_list]
    pct = global_pct or {}
    unl = [(n, t) for n, a, t in items if a]
    ts = [t for _, t in unl if t > 0]
    hours = (playtime_min or 0) / 60
    base.update({
        "ach_n_log": float(np.log1p(len(items))),
        "ach_unlocked_log": float(np.log1p(len(unl))),
        "ach_rarest": float(max((-np.log(max(pct.get(n, 50.0), 0.1) / 100) for n, _ in unl), default=0.0)),
        "ach_last_age_log": float(np.log1p(max(now_ts - max(ts), 0) / 86400)) if ts and now_ts else 0.0,
        "ach_rate": len(unl) / hours if hours > 0 else 0.0})
    return base
