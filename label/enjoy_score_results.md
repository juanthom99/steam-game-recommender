# Enjoyment score variants

Report users only. Primary metric: within-game AUC.

| variant                     | dataset   |   AUC |   within-game AUC |   games |   within-user AUC |   users |
|:----------------------------|:----------|------:|------------------:|--------:|------------------:|--------:|
| 2-hour floor (hours)        | McAuley   | 0.657 |             0.606 |      63 |             0.655 |     568 |
| 2-hour floor (hours)        | Kaggle    | 0.624 |             0.676 |    6657 |             0.657 |  131765 |
| resid (best single formula) | McAuley   | 0.659 |             0.615 |      63 |             0.666 |     568 |
| resid (best single formula) | Kaggle    | 0.637 |             0.664 |    6657 |             0.677 |  131765 |
| V1 per-dataset              | McAuley   | 0.688 |             0.617 |      63 |             0.694 |     568 |
| V1 per-dataset              | Kaggle    | 0.712 |             0.68  |    6657 |             0.719 |  131765 |
| V1 pooled                   | McAuley   | 0.685 |             0.596 |      63 |             0.689 |     568 |
| V1 pooled                   | Kaggle    | 0.682 |             0.676 |    6657 |             0.704 |  131765 |
| V1 pooled + monotonic       | McAuley   | 0.671 |             0.608 |      63 |             0.676 |     568 |
| V1 pooled + monotonic       | Kaggle    | 0.656 |             0.675 |    6657 |             0.685 |  131765 |
| V2 pooled + monotonic       | McAuley   | 0.673 |             0.596 |      63 |             0.675 |     568 |
| V2 pooled + monotonic       | Kaggle    | 0.665 |             0.67  |    6657 |             0.689 |  131765 |
| V3 pooled + monotonic       | McAuley   | 0.696 |             0.608 |      63 |             0.703 |     568 |
| V3 pooled + monotonic       | Kaggle    | 0.666 |             0.672 |    6657 |             0.687 |  131765 |
| V3 pooled, free             | McAuley   | 0.699 |             0.6   |      63 |             0.713 |     568 |
| V3 pooled, free             | Kaggle    | 0.683 |             0.674 |    6657 |             0.701 |  131765 |

## Leakage check: game-level scores with no player information

| dataset   | score                                           |   AUC |   within-game AUC |   games |   within-user AUC |   users |
|:----------|:------------------------------------------------|------:|------------------:|--------:|------------------:|--------:|
| McAuley   | game quality only (review rate, no player info) | 0.741 |             0.5   |      63 |             0.733 |     568 |
| McAuley   | game length only                                | 0.574 |             0.5   |      63 |             0.559 |     568 |
| McAuley   | player-relative only (g, resid, u_rank)         | 0.669 |             0.608 |      63 |             0.68  |     568 |
| McAuley   | V1                                              | 0.688 |             0.617 |      63 |             0.694 |     568 |
| Kaggle    | game quality only (review rate, no player info) | 0.74  |             0.5   |    6657 |             0.747 |  131765 |
| Kaggle    | game length only                                | 0.506 |             0.5   |    6657 |             0.516 |  131765 |
| Kaggle    | player-relative only (g, resid, u_rank)         | 0.672 |             0.675 |    6657 |             0.686 |  131765 |
| Kaggle    | V1                                              | 0.712 |             0.68  |    6657 |             0.719 |  131765 |
