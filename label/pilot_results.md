# Pilot: new engagement signals vs review flags

- Pilot pairs: 10,002 (2,789 users). Public game details now: 1,430 users, 5,268 pairs. Still own the game: 97%. Game has achievements and data returned: 81%.
- Recommend share in pilot: 87.5%.
- Fold-paired AUC gain, all new signals: +0.033 (middle 95% of folds +0.002 to +0.064; better in 98% of folds). Achievements only: +0.034 (better in 98% of folds).
- Standardized coefficients (full pilot): base +0.44, ach_rel -0.20, ach_depth +0.52, ach_span_log +0.35, ach_rel_miss +0.08, growth +0.07, recent +0.00

## Each signal alone

| signal (alone)   |   pairs |   AUC |
|:-----------------|--------:|------:|
| base             |    5268 | 0.678 |
| ach_frac         |    4282 | 0.681 |
| ach_rel          |    4282 | 0.662 |
| ach_depth        |    4282 | 0.678 |
| ach_span_log     |    4282 | 0.647 |
| growth           |    5268 | 0.604 |
| recent           |    5268 | 0.5   |

## Combined with the adopted score

| model (5-fold x 10 repeats, grouped by user)   |   mean fold AUC |
|:-----------------------------------------------|----------------:|
| baseline score only                            |           0.678 |
| + achievements                                 |           0.712 |
| + later playtime & last played                 |           0.675 |
| + all new signals                              |           0.711 |

Caveat: reviews date from ~2011–2017; achievements, playtime and last-played are measured in Oct 2026, so these are long-run engagement signals, not what the player had done at review time.
