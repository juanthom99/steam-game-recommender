# Team evaluation package

Use this to compare everyone's models on the same players, the same hidden games and the same metrics. It covers validation players only, because the test set is reserved and has already been scored.

## What you get (the shared `team_eval` data folder)

| File | One row per | Columns |
|---|---|---|
| `games.parquet` | game | app_id, title, tags, genres, release_year, price_regular, rating, user_reviews, median_playtime_min, content_level, explicit, recommendable, n_train_players |
| `train_full_part01..09.parquet` | played game of a train player (read all parts and concatenate) | player_id, src, app_id, playtime_min, g |
| `train_lite_part1..2.parquet` | same rows for fewer players | all McAuley and Steam 2026 train players, plus 10% of Kaggle train players. Use it if your laptop struggles with the full file. |
| `validation.parquet` | owned game of a validation player | player_id, src, app_id, playtime_min, played, g, enjoyed, hidden_80_20, hidden_75_25, hidden_50_50 |
| `recs_ease.parquet`, `recs_hybrid_ease.parquet`, `recs_mostpopular.parquet` | pick | our models' top-10 lists to compare against (EASE is our candidate) |
| `results.md` | | our scores on all three holdouts |

Column notes:

- `src`: `mcauley` means full libraries from 2017, `steam2026` means full libraries collected in October 2026, and `kaggle` means reviewers only, up to 2023.
- `g`: the enjoyment percentile. It is the player's playtime ranked among everyone who played that game in the same source, from 0 to 1. A game is **enjoyed** when g ≥ 0.5.
- `player_id`: an integer that replaces the real account id.
- `hidden_80_20`: the official split. Each played game is hidden with a fixed hash, so about 20% are hidden.
- `hidden_75_25` and `hidden_50_50`: the same idea with 25% and 50% hidden, for Rob's library-holdout test.

## How to compare a model

1. Fit your model on the `train_full` parts or the `train_lite` parts (files are split to stay under Supabase's 50MB file limit).
2. For each holdout and each validation player, recommend 10 games using only the player's **visible** games (`played` and not hidden).
   - Skip games the player owns that aren't hidden.
   - Pick only games where `recommendable` is True.
3. Save the picks as a parquet or CSV file with the columns `player_id, holdout, rank, app_id`. `holdout` is `80_20`, `75_25` or `50_50`.
4. Score your file next to ours:

```
python evaluate.py --data <team_eval folder> recs_ease.parquet recs_hybrid_ease.parquet recs_mostpopular.parquet recs_yours.parquet --out results.md
```

`example_model.py` is a working template with MostPopular in it. Replace the `MyModel` class with yours.

## Metrics

All metrics are computed on the top 10. The full definitions are at the top of `evaluate.py`. Players count when they have at least 1 hidden enjoyed game and at least 5 visible played games.

- **NDCG@10:** finds hidden enjoyed games and ranks them near the top. This is our primary metric.
- **HitRate@10:** whether at least one hidden enjoyed game is in the list. **HitRate@10 (any)** counts any hidden played game instead.
- **Coverage, popularity and tag distance:** how varied the picks are, how mainstream they are, and how far they move from the player's usual tags.
- **Playtime gap and "within 2×":** how close a game's median playtime is to the player's median playtime. Medians are used because playtime is very skewed; the "(avg)" rows repeat it with averages, as Rob specified.
- **Regret:** among picks the player had played, the share played under 2 hours.
- **Warning flags (soft fails):**
  - negative reviews (Mostly Negative or worse)
  - a short game (median of 2 hours or less)
  - "like quit games" (the game's tags are closer to the player's under-2-hour games than to their kept games)
  - the share of picks with any flag, and with 2 or more flags

With two or more files, the first one is the reference. You also get the paired NDCG@10 difference with a 95% bootstrap confidence interval.

## Rules that keep it fair

- Tune and compare on validation only. Nobody touches the test set.
- Never train on hidden validation rows.
- Explicit games (`explicit` = True) are scored like any other game here, to match our earlier results. The live app hides them by default.

## Rebuilding (Juan's machine only)

`build_package.py` rebuilds the data folder from the cleaned data. `run_ours.py` writes our recs files. Both are memory-heavy, so run them alone.
