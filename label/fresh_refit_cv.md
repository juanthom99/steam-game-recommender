# Refit on fresh reviews - cross-validation (holdout games untouched)


## Every review, no library needed (75,292 reviews, CV grouped by game)

| score                  |   pooled AUC |   within-game AUC |   games |
|:-----------------------|-------------:|------------------:|--------:|
| raw playtime now       |        0.664 |             0.689 |     794 |
| g (percentile in game) |        0.659 |             0.689 |     794 |
| refit: g + recent play |        0.67  |             0.689 |     794 |

## Reviewers with a public library (1,802 reviews, CV grouped by game)

| score                            |   pooled AUC |   within-game AUC |   games |
|:---------------------------------|-------------:|------------------:|--------:|
| raw playtime now                 |        0.7   |             0.725 |      47 |
| g                                |        0.684 |             0.725 |      47 |
| frozen tuned stage 1             |        0.665 |             0.714 |      47 |
| refit stage 1 (g, resid, u_rank) |        0.675 |             0.695 |      47 |
| refit stage 1, g + resid         |        0.676 |             0.717 |      47 |
| refit + recent play              |        0.699 |             0.694 |      47 |
