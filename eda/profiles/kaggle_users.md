# Data Profile: Kaggle users.csv

## Overview
- Grain: one row per user
- Rows: 14,306,064 | Columns: 3 | Memory: 343.3 MB
- Column types: 2 Metric, 1 Identifier
- Primary key `user_id` unique: True (0 duplicates)
- `products` = games owned; `reviews` = reviews written (both counts)

## Column Details (grouped by class)

| column   | class      | dtype   |   null % | completeness   |   distinct |   card. | top values                                                                      | rarest                    | stats                                                                                                                                                       |
|:---------|:-----------|:--------|---------:|:---------------|-----------:|--------:|:--------------------------------------------------------------------------------|:--------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------|
| user_id  | Identifier | int64   |        0 | Green          |   14306064 |  1      | 7360263 (0.0%); 14020781 (0.0%); 8762579 (0.0%); 4820647 (0.0%); 5167327 (0.0%) | 5059205; 5074363; 5081164 | min 0 / max 14306063; card. 1.000                                                                                                                           |
| products | Metric     | int64   |        0 | Green          |       7572 |  0.0005 | 7 (1.2%); 8 (1.2%); 6 (1.2%); 9 (1.2%); 10 (1.2%)                               | 7799; 9972; 12372         | min 0.00 / p1 2.0 / p5 5.0 / p25 23.0 / p50 55.0 / p75 127.0 / p95 401.0 / p99 946.0 / max 32214.00; mean 116.37 sd 243.85; zeros 139,318; neg 0; skew 18.4 |
| reviews  | Metric     | int64   |        0 | Green          |        681 |  0      | 1 (52.9%); 2 (17.0%); 3 (8.2%); 4 (4.8%); 0 (3.7%)                              | 2272; 750; 599            | min 0.00 / p1 0.0 / p5 1.0 / p25 1.0 / p50 1.0 / p75 3.0 / p95 9.0 / p99 24.0 / max 6045.00; mean 2.88 sd 7.99; zeros 525,005; neg 0; skew 112.9            |

## Data Quality Issues

- **Medium**: `reviews`: one value (1) is 53% of rows (default/placeholder?)
- **Info**: `products` is heavily skewed (skew 18.4): use medians/log scale, not means
- **Info**: `reviews` is heavily skewed (skew 112.9): use medians/log scale, not means

## Relationships and Patterns

- Reviews per owned game: median 0.031: users review a small share of what they own, so Kaggle sees only reviewed games.
- Users owning 0 products but with reviews: 125,242 (inconsistent).
