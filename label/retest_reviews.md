# Re-test on fresh Steam reviews

94,924 reviews from the unbiased 'all recent reviews' page (of 129,473 collected), 1,004 games, 76% positive. The extra negative-review page is left out: it reaches further back in time, so it would leak review age into the features.

## Test A - every review (94,878 with playtime > 0)

Within-game AUC is the clean number (it removes game quality).

| signal                           |   pooled AUC |   within-game AUC |   games |
|:---------------------------------|-------------:|------------------:|--------:|
| playtime at review               |        0.639 |             0.664 |     922 |
| playtime now                     |        0.661 |             0.692 |     922 |
| 2-hour floor, at review          |        0.608 |             0.601 |     922 |
| 2-hour floor, now                |        0.619 |             0.609 |     922 |
| play after review (log)          |        0.635 |             0.635 |     922 |
| share of play after review       |        0.626 |             0.626 |     922 |
| still playing (last 2 weeks > 0) |        0.658 |             0.684 |     922 |

Reviews from the last 180 days only (29,226): within-game AUC playtime at review 0.660, playtime now 0.690.

**Refunds:** 673 refunded reviews on the all page (1,576 across both pages), 29% positive (all reviews: 76%). Median playtime at review for refunded: 39 min.

0.0% of reviews have zero playtime at review (off-Steam keys, family share): excluded above.

## Test B - reviewers with a public library

Frozen models, no refitting. The live app sees playtime **now**, so the 'now' rows are the production-relevant ones. Game-stratified AUC compares reviewers of the same game only (few reviewers per game, so it is noisy). One review per reviewer.

### All (2,276 reviewers)

| score                          |   AUC |   vs raw playtime (now) | 95% CI           |   game-stratified AUC |
|:-------------------------------|------:|------------------------:|:-----------------|----------------------:|
| raw playtime (now)             | 0.693 |                   0     | -                |                 0.7   |
| raw playtime (at review)       | 0.673 |                  -0.019 | -0.027 to -0.010 |                 0.67  |
| 2-hour floor (now), ties kept  | 0.643 |                  -0.049 | -0.062 to -0.037 |                 0.615 |
| tuned stage 1 (at review)      | 0.636 |                  -0.056 | -0.078 to -0.035 |                 0.628 |
| tuned stage 1 (now)            | 0.662 |                  -0.03  | -0.049 to -0.011 |                 0.65  |
| two-stage (now + achievements) | 0.659 |                  -0.033 | -0.055 to -0.010 |                 0.634 |

### With achievement data (1,269 reviewers)

| score                          |   AUC |   vs raw playtime (now) | 95% CI           |   game-stratified AUC |
|:-------------------------------|------:|------------------------:|:-----------------|----------------------:|
| raw playtime (now)             | 0.674 |                   0     | -                |                 0.688 |
| raw playtime (at review)       | 0.651 |                  -0.024 | -0.034 to -0.012 |                 0.657 |
| 2-hour floor (now), ties kept  | 0.616 |                  -0.059 | -0.080 to -0.038 |                 0.599 |
| tuned stage 1 (at review)      | 0.623 |                  -0.051 | -0.082 to -0.023 |                 0.618 |
| tuned stage 1 (now)            | 0.653 |                  -0.022 | -0.049 to +0.006 |                 0.657 |
| two-stage (now + achievements) | 0.628 |                  -0.047 | -0.082 to -0.012 |                 0.612 |
