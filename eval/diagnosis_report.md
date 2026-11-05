# Post-hoc diagnosis on validation players (test set not used)

8,112 validation players with 5+ visible games. Models use the tuned settings from `best_params.json`. This is exploratory and was not pre-registered; any change it suggests would need a fresh, untouched test split to be confirmed.

## 1. Regret

Played picks = top-10 picks the player went on to play (hidden games). Regret = played < 120 min. `regret_but_enjoyed` = share of regret picks that still count as enjoyed under the Layer 1 label (top half of that game's players: short games played through). `not_enjoyed` = share of played picks below the label.

| model       |   played_picks |   regret |   median_train_players |   regret_but_enjoyed |   not_enjoyed |   Regret@10 (per-player mean) |   regret at MostPopular's popularity mix |
|:------------|---------------:|---------:|-----------------------:|---------------------:|--------------:|------------------------------:|-----------------------------------------:|
| EASE        |          18051 |   0.1938 |                  41840 |               0.0832 |        0.3979 |                        0.1761 |                                   0.1088 |
| Hybrid-EASE |          18097 |   0.1953 |                  40872 |               0.0838 |        0.3972 |                        0.1777 |                                   0.1085 |
| MostPopular |           3388 |   0.1027 |                 172104 |               0.0057 |        0.4847 |                        0.1012 |                                   0.1027 |

### Regret by game popularity (share of training players; bins over picked games)

| model       |   bottom 50% |   50-80% |   80-95% |   top 5% |
|:------------|-------------:|---------:|---------:|---------:|
| EASE        |       0.3411 |   0.2847 |   0.1927 |   0.1088 |
| Hybrid-EASE |       0.342  |   0.2861 |   0.1927 |   0.1085 |
| MostPopular |     nan      | nan      | nan      |   0.1027 |

### Popularity mix of played picks

| model       |   bottom 50% |   50-80% |   80-95% |   top 5% |
|:------------|-------------:|---------:|---------:|---------:|
| EASE        |       0.0837 |   0.2448 |   0.2685 |   0.4031 |
| Hybrid-EASE |       0.0855 |   0.2484 |   0.2695 |   0.3966 |
| MostPopular |     nan      | nan      | nan      |   1      |

## 2. Try something new: accuracy vs exploration

For you (Hybrid-EASE) NDCG@10 on validation: 0.2771. The 80% margin needs >= 0.2217. `filter` keeps games from the hybrid's top `pool` with a tag below `th` share of the player's tag profile (th=0: a tag the player has never played; the shipped rule is pool=400 th=0.02). `rerank` sorts the top 400 by z(score) + lambda x tag distance.

| variant                   |   NDCG@10 |   share of For you |   tag distance gain |   players with < 10 picks | meets 80% margin   |
|:--------------------------|----------:|-------------------:|--------------------:|--------------------------:|:-------------------|
| rerank lambda=4.0         |    0.2589 |             0.9342 |              0.142  |                    0      | True               |
| filter pool=100 th=0.05   |    0.2369 |             0.8549 |              0.0735 |                    0      | True               |
| filter pool=1000 th=0.05  |    0.2369 |             0.8549 |              0.0735 |                    0      | True               |
| filter pool=200 th=0.05   |    0.2369 |             0.8549 |              0.0735 |                    0      | True               |
| filter pool=400 th=0.05   |    0.2369 |             0.8549 |              0.0735 |                    0      | True               |
| filter pool=50 th=0.05    |    0.2369 |             0.8549 |              0.0735 |                    0.0006 | True               |
| rerank lambda=2.0         |    0.2719 |             0.9811 |              0.0682 |                    0      | True               |
| filter pool=100 th=0.1    |    0.2585 |             0.9329 |              0.0353 |                    0      | True               |
| filter pool=1000 th=0.1   |    0.2585 |             0.9329 |              0.0353 |                    0      | True               |
| filter pool=200 th=0.1    |    0.2585 |             0.9329 |              0.0353 |                    0      | True               |
| filter pool=400 th=0.1    |    0.2585 |             0.9329 |              0.0353 |                    0      | True               |
| filter pool=50 th=0.1     |    0.2585 |             0.9329 |              0.0353 |                    0      | True               |
| rerank lambda=1.0         |    0.2752 |             0.993  |              0.033  |                    0      | True               |
| rerank lambda=0.5         |    0.2761 |             0.9961 |              0.0169 |                    0      | True               |
| filter pool=1000 th=0.0   |    0.1444 |             0.5211 |              0.1678 |                    0.0004 | False              |
| filter pool=200 th=0.0    |    0.1442 |             0.5202 |              0.1678 |                    0.0027 | False              |
| filter pool=400 th=0.0    |    0.1444 |             0.5209 |              0.1678 |                    0.0012 | False              |
| filter pool=100 th=0.0    |    0.1439 |             0.5192 |              0.1678 |                    0.008  | False              |
| filter pool=50 th=0.0     |    0.143  |             0.5159 |              0.1676 |                    0.0582 | False              |
| filter pool=50 th=0.005   |    0.1623 |             0.5855 |              0.1539 |                    0.0142 | False              |
| filter pool=100 th=0.005  |    0.1623 |             0.5857 |              0.1539 |                    0      | False              |
| filter pool=1000 th=0.005 |    0.1623 |             0.5857 |              0.1539 |                    0      | False              |
| filter pool=200 th=0.005  |    0.1623 |             0.5857 |              0.1539 |                    0      | False              |
| filter pool=400 th=0.005  |    0.1623 |             0.5857 |              0.1539 |                    0      | False              |
| filter pool=50 th=0.01    |    0.1786 |             0.6443 |              0.1399 |                    0.0084 | False              |
| filter pool=100 th=0.01   |    0.1786 |             0.6445 |              0.1399 |                    0      | False              |
| filter pool=1000 th=0.01  |    0.1786 |             0.6445 |              0.1399 |                    0      | False              |
| filter pool=200 th=0.01   |    0.1786 |             0.6445 |              0.1399 |                    0      | False              |
| filter pool=400 th=0.01   |    0.1786 |             0.6445 |              0.1399 |                    0      | False              |
| filter pool=100 th=0.02   |    0.202  |             0.7288 |              0.1179 |                    0      | False              |
| filter pool=1000 th=0.02  |    0.202  |             0.7288 |              0.1179 |                    0      | False              |
| filter pool=200 th=0.02   |    0.202  |             0.7288 |              0.1179 |                    0      | False              |
| filter pool=400 th=0.02   |    0.202  |             0.7288 |              0.1179 |                    0      | False              |
| filter pool=50 th=0.02    |    0.202  |             0.7288 |              0.1179 |                    0.0046 | False              |
