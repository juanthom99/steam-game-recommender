# Stage 1 tuning

Training never includes pilot players; scored on non-holdout pilot players' McAuley reviews.

| candidate                     | features   |   selection AUC |   selection within-user AUC |   users |   train-CV AUC |
|:------------------------------|:-----------|----------------:|----------------------------:|--------:|---------------:|
| McAuley tuned S1x             | S1x        |           0.691 |                       0.685 |     676 |          0.688 |
| McAuley tuned S1              | S1         |           0.689 |                       0.691 |     676 |          0.683 |
| McAuley default S1x           | S1x        |           0.684 |                       0.689 |     676 |        nan     |
| Pooled (McAuley weighted) S1x | S1x        |           0.679 |                       0.679 |     676 |          0.7   |
| Pooled (McAuley weighted) S1  | S1         |           0.675 |                       0.688 |     676 |          0.673 |
| McAuley default S1            | S1         |           0.672 |                       0.669 |     676 |        nan     |
| Kaggle tuned S1x              | S1x        |           0.65  |                       0.667 |     676 |          0.7   |
| Kaggle tuned S1               | S1         |           0.587 |                       0.613 |     676 |          0.673 |

Chosen: **McAuley tuned S1x**

Params:

| candidate                     | params                                                                                                            |
|:------------------------------|:------------------------------------------------------------------------------------------------------------------|
| McAuley tuned S1x             | {"learning_rate": 0.1, "max_leaf_nodes": 7, "min_samples_leaf": 20, "l2_regularization": 5.0, "max_iter": 150}    |
| McAuley tuned S1              | {"learning_rate": 0.05, "max_leaf_nodes": 7, "min_samples_leaf": 20, "l2_regularization": 0.0, "max_iter": 150}   |
| McAuley default S1x           | {"learning_rate": 0.05, "max_leaf_nodes": 31, "min_samples_leaf": 20, "l2_regularization": 1.0, "max_iter": 400}  |
| Pooled (McAuley weighted) S1x | {"learning_rate": 0.05, "max_leaf_nodes": 63, "min_samples_leaf": 100, "l2_regularization": 1.0, "max_iter": 600} |
| Pooled (McAuley weighted) S1  | {"learning_rate": 0.03, "max_leaf_nodes": 63, "min_samples_leaf": 400, "l2_regularization": 0.0, "max_iter": 300} |
| McAuley default S1            | {"learning_rate": 0.05, "max_leaf_nodes": 31, "min_samples_leaf": 20, "l2_regularization": 1.0, "max_iter": 400}  |
| Kaggle tuned S1x              | {"learning_rate": 0.05, "max_leaf_nodes": 63, "min_samples_leaf": 100, "l2_regularization": 1.0, "max_iter": 600} |
| Kaggle tuned S1               | {"learning_rate": 0.03, "max_leaf_nodes": 63, "min_samples_leaf": 400, "l2_regularization": 0.0, "max_iter": 300} |
\nOverride: chose **McAuley tuned S1** (simpler; S1x's +0.002 is within noise and its within-user AUC is lower).
