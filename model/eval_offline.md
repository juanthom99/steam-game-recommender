# Offline check - held-out players

Hide 20% of each player's played games, fold in the rest, rank the full vocabulary. Hits = hidden games the player enjoyed (playtime percentile >= 0.5).

| group               |   players |   NDCG@10 ALS |   NDCG@10 MostPopular |   difference | 95% CI           |   Recall@20 ALS |   Recall@20 MostPopular |
|:--------------------|----------:|--------------:|----------------------:|-------------:|:-----------------|----------------:|------------------------:|
| all                 |      2284 |         0.218 |                 0.056 |        0.162 | +0.153 to +0.171 |           0.312 |                   0.129 |
| source: mcauley     |      1885 |         0.218 |                 0.052 |        0.166 | +0.157 to +0.176 |           0.337 |                   0.14  |
| source: steam2026   |       399 |         0.215 |                 0.071 |        0.144 | +0.126 to +0.162 |           0.194 |                   0.074 |
| library: 8-20 games |       538 |         0.209 |                 0.054 |        0.155 | +0.133 to +0.178 |           0.399 |                   0.176 |
| library: 21-100     |      1324 |         0.208 |                 0.05  |        0.158 | +0.148 to +0.168 |           0.308 |                   0.125 |
| library: 100+       |       422 |         0.26  |                 0.076 |        0.184 | +0.166 to +0.201 |           0.215 |                   0.078 |
