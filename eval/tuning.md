# Tuning on validation players (>= 5 visible games)

Selection: highest NDCG@10. Test players never used.

| model       | params   |   NDCG@10 |   Recall@20 |   NDCG@10 kaggle |   NDCG@10 mcauley |   NDCG@10 steam2026 |   seconds |
|:------------|:---------|----------:|------------:|-----------------:|------------------:|--------------------:|----------:|
| MostPopular | {}       |    0.0378 |      0.1117 |           0.0252 |            0.0426 |              0.0522 |         6 |

Chosen:

```json
{
  "MostPopular": {}
}
```
