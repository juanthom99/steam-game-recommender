# Data Profile: McAuley australian_users_items (users)

## Overview
- Grain: one row per Steam user
- Rows: 88,310 | Columns: 4 | Memory: 5.6 MB
- Column types: 2 Identifier, 2 Metric
- Primary key `user_id` unique: False (684 duplicates)
- items_count is what Steam reported; n_items_listed is what the file actually contains

## Column Details (grouped by class)

| column         | class      | dtype   |   null % | completeness   |   distinct |   card. | top values                                                                                                                       | rarest                                                     | stats                                                                                                                                                  |
|:---------------|:-----------|:--------|---------:|:---------------|-----------:|--------:|:---------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------|
| steam_id       | Identifier | str     |        0 | Green          |      87625 |  0.9922 | 76561198056857968 (0.0%); 76561198072861800 (0.0%); 76561198072634646 (0.0%); 76561198309337430 (0.0%); 76561198045953692 (0.0%) | 76561198328759259; 76561198329548331; 76561198331598578    |                                                                                                                                                        |
| user_id        | Identifier | str     |        0 | Green          |      87626 |  0.9923 | 76561198056857968 (0.0%); 76561198072861800 (0.0%); blablabla174 (0.0%); 76561198309337430 (0.0%); 76561198045953692 (0.0%)      | XxLaughingJackClown7; 76561198329548331; edward_tremethick |                                                                                                                                                        |
| items_count    | Metric     | int64   |        0 | Green          |        925 |  0.0105 | 0 (19.0%); 1 (3.7%); 2 (2.0%); 3 (1.7%); 4 (1.6%)                                                                                | 787; 3603; 1173                                            | min 0.00 / p1 0.0 / p5 0.0 / p25 3.0 / p50 26.0 / p75 73.0 / p95 211.0 / p99 437.0 / max 7762.00; mean 58.35 sd 122.31; zeros 16,806; neg 0; skew 17.0 |
| n_items_listed | Metric     | int64   |        0 | Green          |        925 |  0.0105 | 0 (19.0%); 1 (3.7%); 2 (2.0%); 3 (1.7%); 4 (1.6%)                                                                                | 787; 3603; 1173                                            | min 0.00 / p1 0.0 / p5 0.0 / p25 3.0 / p50 26.0 / p75 73.0 / p95 211.0 / p99 437.0 / max 7762.00; mean 58.35 sd 122.31; zeros 16,806; neg 0; skew 17.0 |

## Data Quality Issues

- **High**: `user_id` has 684 duplicate rows
- **Info**: `n_items_listed` is heavily skewed (skew 17.0): use medians/log scale, not means
- **Info**: `items_count` is heavily skewed (skew 17.0): use medians/log scale, not means

## Relationships and Patterns

- Users with an empty library (private profile or no games): 16,806 (19.0%). The live app will meet the same case.
- items_count ≠ n_items_listed for 0 users.
- Duplicate steam_id across different user_id values: 685.
