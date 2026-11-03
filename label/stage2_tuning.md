# Stage 2 tuning

Pilot players outside the holdout; 5-fold x 5 repeats grouped by player. Stage 1 = McAuley tuned S1.

| candidate                    |   CV AUC (all) |   CV AUC (with achievements) |   gain vs stage 1 |   folds better than stage 1 |
|:-----------------------------|---------------:|-----------------------------:|------------------:|----------------------------:|
| boosting, extended (shallow) |          0.724 |                        0.71  |             0.043 |                        0.96 |
| boosting, extended (deeper)  |          0.722 |                        0.706 |             0.041 |                        0.92 |
| logistic, extended           |          0.712 |                        0.696 |             0.032 |                        0.92 |
| logistic, 3 base features    |          0.71  |                        0.69  |             0.03  |                        0.92 |
| stage 1 only                 |          0.681 |                        0.648 |             0     |                        0    |
