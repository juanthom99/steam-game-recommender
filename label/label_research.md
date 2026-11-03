# Label research: a better way to quantify "enjoyed"

## Summary (2026-10-28)

1. **Every single playtime formula hits the same ceiling** (ROC-AUC 0.63–0.66 vs review flags on both datasets):
   raw hours, per-game percentile, playtime vs SteamSpy median, duration-bucket quantiles (Zhan et al. 2022),
   and a user + game "expected playtime" residual. The best, residual + 2-hour floor, beats the plain floor by ~0.015 kappa.
2. **Combining views of the same playtime helps.** A small gradient-boosted model over *playtime-only* features
   (hours, rank among the game's players, ratio to the game's typical length, length-bucket quantile, user+game residual,
   rank inside the user's own library) reaches AUC **0.688 (McAuley) / 0.707 (Kaggle)** vs 0.661 / 0.636.
3. **Popularity must stay out.** Adding game popularity lifts AUC to ~0.74, but popularity alone scores 0.705 on McAuley:
   the model would learn "popular games are enjoyed", which bakes in the bias we evaluate against (MostPopular baseline).
4. **Recent activity (played in the last 2 weeks) adds nothing** (AUC 0.526 alone; no gain in the model).

**Proposed technique, "learned enjoyment score":** P(enjoyed | playtime features), trained on review flags as noisy
labels, with popularity and user-level review habits excluded. Use the probability as graded relevance and ALS confidence,
and a cutoff for the binary label. Fit on the training split only.

**Limits:** reviewers are self-selected; review flags are a weak proxy (86–89% positive); gains are modest (+0.03 to +0.07 AUC).
The user study (Layer 3) is the real test.

Sources: Bunga, Batista & Ribeiro 2021 (playtime to 1–5 ratings); Zhan et al. 2022 (duration-bucket quantiles);
relative-advantage debiasing, arXiv 2508.11086 (2025); D2Co, RecSys 2023 (duration bias + noisy watching); DRGame, AAAI 2024.

## Round 2: making it better (2026-10-28)

- Added **within-game AUC** (does the score tell a game's fans from its non-fans?) and **within-user AUC** (does it rank a
  user's favorites higher?). Pooled AUC can be inflated by game quality.
- Tried: more user context, genre-relative features, pooled training across datasets, monotonic constraints. **None helped.**
- **Leakage check:** a score with *no player information*, only each game's review rate, gets within-user AUC 0.747 on Kaggle,
  higher than any playtime model. So within-user gains are partly game quality. Within-game AUC is the clean metric, and there
  every playtime method lands at 0.66–0.68 (Kaggle): **lifetime playtime has hit its ceiling as a signal.**
- **Adopted:** a player-relative model (g, resid, u_rank only), with no popularity or quality leak by construction. It matches the
  floor within-game and beats it within-user (0.686 vs 0.657 Kaggle, 0.680 vs 0.655 McAuley). Details: `enjoy_score_results.md`.
- **Next real gain needs new signals**, e.g. achievement completion and last-played dates from the Steam API.

## Round 3: Steam API pilot (2026-10-29)

- Fetched current playtime, last-played dates and achievements for 2,000 McAuley reviewed pairs (576 players; Steam IDs stored
  only as salted hashes). 281 players (49%) still show game details publicly: **1,008 usable pairs**; 79% of those games have achievements.
- **Achievements alone are about as strong as the whole playtime score** (AUC 0.681 vs 0.687), so they are a second, largely
  independent view of enjoyment. Rarity-weighted unlocks ("depth") work best.
- **Added to the adopted score:** +0.016 AUC on average (0.687 → 0.703), better in 74% of cross-validation folds, but the fold
  range crosses zero. Playtime growth since 2017 adds a little; last-played date adds nothing.
- **Verdict:** promising, not proven. About 1,000 pairs is too small to separate a +0.016 gain from noise. Reviews date from
  2011–2017 and the new signals are from 2026, which likely understates their value at serving time. Details: `pilot_results.md`.

## Round 5: tuning, scored on a locked holdout (2026-10-29)

- Locked 20% of pilot players (539 players) before any tuning; scored once at the end (1,016 pairs, 266 public players).
- **Stage 1 tuning:** +0.017 AUC (a smaller model; the default overfit). Training on Kaggle transfers badly to McAuley-style players.
- **Stage 2:** small boosted trees with 8 achievement features beat the 3-feature logistic model in cross-validation (0.724 vs 0.710).
- **Holdout:** new 0.727 vs 2-hour floor 0.672 (+0.054, CI +0.007 to +0.104) and vs the previous setup 0.713 (+0.014, CI −0.023 to +0.053).
  The jump over the floor is solid; the step from the previous setup is real in cross-validation but too small to confirm on 266 players.

## Adopted 2026-10-29: two-stage score

Stage 1 is the player-relative playtime model; stage 2 adjusts it with achievements when a profile shares them.
Cross-validated AUC on the pilot: 0.678 → 0.708 overall, 0.654 → 0.693 on pairs with achievements. To be re-tested on the
Steam reviews collection. Code: `achievements.py`, `fit_stage2.py`.

## Round 4: pilot scaled to 10k pairs (2026-10-29)

- 10,002 pairs from 2,789 players; 1,430 players (51%) still public: **5,268 usable pairs**; 81% have achievement data.
- **Achievements help, and the result now holds:** adding them to the adopted score raises AUC from 0.678 to **0.712 (+0.034)**,
  better in 98% of cross-validation folds (middle 95% of folds +0.002 to +0.064). The first pilot's +0.016 was too small a sample.
- Strongest pieces: rarity-weighted unlocks ("depth") and how many days the unlocks span. Playtime growth since 2017 and
  last-played date add nothing.
- Same caveat: reviews 2011–2017, achievements measured 2026. The Steam reviews collection (playtime and refunds at review time) will
  re-test this on current data.

## Single formulas vs review flags

Thresholds tuned on calibration users, metrics on report users. Higher is better.

| dataset   | score             |   ROC-AUC |   kappa (tuned cut) |   enjoyed share |   AUC games ≥ 20 players |   AUC games < 20 players |   mean over datasets (kappa) |
|:----------|:------------------|----------:|--------------------:|----------------:|-------------------------:|-------------------------:|-----------------------------:|
| McAuley   | hours             |     0.657 |               0.208 |           0.902 |                    0.656 |                  nan     |                        0.209 |
| McAuley   | g                 |     0.65  |               0.18  |           0.883 |                    0.649 |                  nan     |                        0.187 |
| McAuley   | ratio_ext         |     0.649 |               0.193 |           0.863 |                    0.649 |                  nan     |                        0.211 |
| McAuley   | bucket_q          |     0.649 |               0.197 |           0.88  |                    0.648 |                  nan     |                        0.211 |
| McAuley   | resid             |     0.659 |               0.197 |           0.904 |                    0.658 |                  nan     |                        0.207 |
| McAuley   | resid+floor       |     0.661 |               0.217 |           0.883 |                    0.66  |                  nan     |                        0.221 |
| McAuley   | 2 h floor (fixed) |   nan     |               0.209 |           0.892 |                  nan     |                  nan     |                        0.206 |
| Kaggle    | hours             |     0.625 |               0.209 |           0.883 |                    0.624 |                    0.698 |                        0.209 |
| Kaggle    | g                 |     0.645 |               0.194 |           0.88  |                    0.645 |                    0.634 |                        0.187 |
| Kaggle    | ratio_ext         |     0.647 |               0.228 |           0.88  |                    0.646 |                    0.635 |                        0.211 |
| Kaggle    | bucket_q          |     0.643 |               0.224 |           0.88  |                    0.643 |                    0.675 |                        0.211 |
| Kaggle    | resid             |     0.636 |               0.217 |           0.88  |                    0.636 |                    0.675 |                        0.207 |
| Kaggle    | resid+floor       |     0.637 |               0.224 |           0.88  |                    0.636 |                    0.643 |                        0.221 |
| Kaggle    | 2 h floor (fixed) |   nan     |               0.203 |           0.913 |                  nan     |                  nan     |                        0.206 |

## Combining signals (gradient-boosted model trained on calibration users' review flags)

| dataset                                             | method                                |   ROC-AUC (report users) |
|:----------------------------------------------------|:--------------------------------------|-------------------------:|
| McAuley                                             | best single formula (resid+floor)     |                    0.661 |
| McAuley                                             | combined model, with 2-week signal    |                    0.738 |
| McAuley                                             | AUC of 'played in last 2 weeks' alone |                    0.526 |
| McAuley                                             | combined model, no 2-week signal      |                    0.737 |
| Kaggle (3M-row sample; scores computed on all rows) | best single formula (resid+floor)     |                    0.636 |
| Kaggle (3M-row sample; scores computed on all rows) | combined model, no 2-week signal      |                    0.742 |

## Ablation: what drives the combined model

| dataset   | features                              |   ROC-AUC |
|:----------|:--------------------------------------|----------:|
| McAuley   | all features                          |     0.736 |
| McAuley   | playtime-only (no game_pop, no n_lib) |     0.688 |
| McAuley   | without game_pop                      |     0.692 |
| McAuley   | without n_lib                         |     0.736 |
| McAuley   | game_pop alone                        |     0.705 |
| McAuley   | n_lib alone                           |     0.532 |
| McAuley   | u_rank alone                          |     0.659 |
| Kaggle    | all features                          |     0.74  |
| Kaggle    | playtime-only (no game_pop, no n_lib) |     0.707 |
| Kaggle    | without game_pop                      |     0.71  |
| Kaggle    | without n_lib                         |     0.739 |
| Kaggle    | game_pop alone                        |     0.634 |
| Kaggle    | n_lib alone                           |     0.538 |
| Kaggle    | u_rank alone                          |     0.595 |


## Round 6 - re-test on fresh 2026 Steam reviews (2026-10-30)

The adopted two-stage score did **not** hold up on current data. On 2,276 reviewers with public libraries (one review each,
unbiased "all recent reviews" page) raw lifetime playtime scored AUC 0.693; tuned stage 1 0.662 (-0.030, CI -0.049 to -0.011);
two-stage with achievements 0.659 (-0.033). On 94,878 reviews, within-game AUC of playtime now is 0.692, and playtime now beats
playtime at review (0.664). Refunded reviews are 29% positive vs 76% overall.

Why: the stage-1 model learned on 2017 McAuley libraries (median 29 played games). Today's reviewers have played a median of 231,
so rank-in-library and user-adjusted playtime mean something different. Refitting on fresh data did not beat raw playtime either.

Artifacts caught before they were reported: recency features and library size looked strong (0.76-0.78) but came from the
sampling (older negative-review pages; prolific reviewers). The earlier "2-hour floor" baseline broke ties by playtime, so it
was really raw playtime; the pilot holdout figure of 0.672 is raw 2017 playtime.

**Decision:** for the recommender, "enjoyed" = the user's playtime percentile among the game's players (g), with the 2-hour
floor as a minimum for binary labels. Simple, works on any era of data, and nothing tested beats it on current players.
