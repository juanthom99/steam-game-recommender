# Data Profile: Kaggle recommendations.csv

## Overview
- Grain: one row per user review of a game
- Rows: 41,154,794 | Columns: 8 | Memory: 1,358.1 MB
- Column types: 3 Identifier, 3 Metric, 1 Temporal, 1 Boolean
- Date range `date`: 2010-10-15 00:00:00 to 2022-12-31 00:00:00
- Primary key `review_id` unique: True (0 duplicates)
- (user_id, app_id) duplicates: 21
- hours at the 1000 cap: 372

## Column Details (grouped by class)

| column         | class      | dtype          |   null % | completeness   |   distinct |   card. | top values                                                                                                                                 | rarest                                                        | stats                                                                                                                                                   |
|:---------------|:-----------|:---------------|---------:|:---------------|-----------:|--------:|:-------------------------------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------|
| app_id         | Identifier | int32          |        0 | Green          |      37610 |  0.0009 | 440 (0.8%); 252490 (0.7%); 1091500 (0.6%); 730 (0.5%); 570 (0.5%)                                                                          | 2094760; 1916940; 2121260                                     | min 10 / max 2253290; card. 0.001                                                                                                                       |
| review_id      | Identifier | int32          |        0 | Green          |   41154794 |  1      | 0 (0.0%); 1 (0.0%); 2 (0.0%); 3 (0.0%); 4 (0.0%)                                                                                           | 41154791; 41154792; 41154793                                  | min 0 / max 41154793; card. 1.000                                                                                                                       |
| user_id        | Identifier | int32          |        0 | Green          |   13781059 |  0.3349 | 11764552 (0.0%); 5112758 (0.0%); 11656130 (0.0%); 5669734 (0.0%); 11553593 (0.0%)                                                          | 5020742; 492792; 2306695                                      | min 0 / max 14306063; card. 0.335                                                                                                                       |
| funny          | Metric     | int32          |        0 | Green          |       2756 |  0.0001 | 0 (93.7%); 2 (2.4%); 3 (1.0%); 4 (0.6%); 5 (0.4%)                                                                                          | 2548; 2381; 2035                                              | min 0.00 / p1 0.0 / p5 0.0 / p25 0.0 / p50 0.0 / p75 0.0 / p95 2.0 / p99 13.0 / max 28109.00; mean 1.06 sd 28.67; zeros 38,551,484; neg 0; skew 222.3   |
| helpful        | Metric     | int32          |        0 | Green          |       3910 |  0.0001 | 0 (78.9%); 2 (7.4%); 3 (3.5%); 4 (2.0%); 5 (1.3%)                                                                                          | 11577; 5442; 2277                                             | min 0.00 / p1 0.0 / p5 0.0 / p25 0.0 / p50 0.0 / p75 0.0 / p95 8.0 / p99 49.0 / max 36212.00; mean 3.20 sd 46.94; zeros 32,461,479; neg 0; skew 140.2   |
| hours          | Metric     | float32        |        0 | Green          |      10001 |  0.0002 | 1.0 (1.1%); 0.20000000298023224 (0.7%); 2.0 (0.7%); 0.30000001192092896 (0.6%); 3.0 (0.6%)                                                 | 984.5; 986.5; 1000.0                                          | min 0.00 / p1 0.2 / p5 0.9 / p25 7.8 / p50 27.3 / p75 99.2 / p95 517.4 / p99 864.5 / max 1000.00; mean 100.60 sd 176.17; zeros 176,329; neg 0; skew 2.8 |
| date           | Temporal   | datetime64[us] |        0 | Green          |       4450 |  0.0001 | 2019-06-29 00:00:00 (0.5%); 2022-11-22 00:00:00 (0.4%); 2021-11-24 00:00:00 (0.4%); 2022-11-23 00:00:00 (0.4%); 2019-06-30 00:00:00 (0.3%) | 2010-10-27 00:00:00; 2010-11-16 00:00:00; 2010-11-04 00:00:00 | min 2010-10-15 00:00:00 / max 2022-12-31 00:00:00; future 0; years w/ no rows none                                                                      |
| is_recommended | Boolean    | bool           |        0 | Green          |          2 |  0      | True (85.8%); False (14.2%)                                                                                                                | True; False                                                   | true 35,304,398 / false 5,850,396; true rate 85.8%                                                                                                      |

## Data Quality Issues

- **Medium**: `funny`: one value (0) is 94% of rows (default/placeholder?)
- **Medium**: `helpful`: one value (0) is 79% of rows (default/placeholder?)
- **Info**: `helpful` is heavily skewed (skew 140.2): use medians/log scale, not means
- **Info**: `funny` is heavily skewed (skew 222.3): use medians/log scale, not means

## Relationships and Patterns

- FKs: `app_id` → games (orphans 0), `user_id` → users.
- Recommended share by year: 2010: 97%, 2011: 97%, 2012: 96%, 2013: 93%, 2014: 88%, 2015: 83%, 2016: 83%, 2017: 82%, 2018: 81%, 2019: 87%, 2020: 88%, 2021: 87%, 2022: 85%
- Spearman(hours, is_recommended) = 0.156; Spearman(helpful, funny) = 0.408.
- Months with the most reviews: 2022-11 (1,282,247), 2021-11 (1,185,050), 2022-12 (1,002,583); quietest recent month: 2020-02.
