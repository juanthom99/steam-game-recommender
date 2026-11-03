# Data Profile: McAuley australian_users_items (owned games)

## Overview
- Grain: one row per owned game for a user (full library)
- Rows: 5,153,209 | Columns: 5 | Memory: 376.7 MB
- Column types: 2 Identifier, 2 Metric, 1 Dimension
- Primary key `['user_id', 'app_id']` unique: False (59,127 duplicates)
- playtime in MINUTES, like the live Steam API; includes never-played games

## Column Details (grouped by class)

| column           | class      | dtype   |   null % | completeness   |   distinct |   card. | top values                                                                                                         | rarest                                          | stats                                                                                                                                                             |
|:-----------------|:-----------|:--------|---------:|:---------------|-----------:|--------:|:-------------------------------------------------------------------------------------------------------------------|:------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| app_id           | Identifier | Int64   |        0 | Green          |      10978 |  0.0021 | 205790 (1.0%); 730 (0.8%); 4000 (0.8%); 304930 (0.8%); 550 (0.7%)                                                  | 354280; 433920; 485270                          | min 10 / max 530720; card. 0.002                                                                                                                                  |
| user_id          | Identifier | str     |        0 | Green          |      70912 |  0.0138 | phrostb (0.2%); thugnificent (0.1%); chidvd (0.1%); piepai (0.1%); mayshowganmore (0.1%)                           | POMFP0MF; 76561198315899135; 76561198316040453  |                                                                                                                                                                   |
| item_name        | Dimension  | str     |        0 | Green          |      10947 |  0.0021 | Dota 2 Test (1.0%); Counter-Strike: Global Offen (0.8%); Garry's Mod (0.8%); Unturned (0.8%); Left 4 Dead 2 (0.7%) | ChaosTower; Aveyond 4: Shadow Of; Arachnophobia | len min 1 / avg 19 / max 99; empty 0; lead/trail whitespace 26,738; placeholders 0; case mixed                                                                    |
| playtime_2weeks  | Metric     | int64   |        0 | Green          |       4450 |  0.0009 | 0 (97.3%); 1 (0.2%); 2 (0.1%); 3 (0.0%); 4 (0.0%)                                                                  | 2145; 2925; 3046                                | min 0.00 / p1 0.0 / p5 0.0 / p25 0.0 / p50 0.0 / p75 0.0 / p95 0.0 / p99 148.0 / max 19967.00; mean 9.10 sd 140.39; zeros 5,014,707; neg 0; skew 38.4             |
| playtime_forever | Metric     | int64   |        0 | Green          |      48861 |  0.0095 | 0 (36.2%); 1 (2.0%); 2 (0.7%); 3 (0.6%); 4 (0.6%)                                                                  | 42740; 121694; 34753                            | min 0.00 / p1 0.0 / p5 0.0 / p25 0.0 / p50 34.0 / p75 355.0 / p95 3675.0 / p99 17947.0 / max 642773.00; mean 991.50 sd 5418.20; zeros 1,867,963; neg 0; skew 20.5 |

## Data Quality Issues

- **High**: `['user_id', 'app_id']` has 59,127 duplicate rows
- **Medium**: `playtime_2weeks`: one value (0) is 97% of rows (default/placeholder?)
- **Low**: `item_name`: 4 values differ only by case/whitespace
- **Low**: `item_name`: 26,738 values with leading/trailing whitespace
- **Info**: `playtime_forever` is heavily skewed (skew 20.5): use medians/log scale, not means
- **Info**: `playtime_2weeks` is heavily skewed (skew 38.4): use medians/log scale, not means

## Relationships and Patterns

- Never played (playtime 0 → *unknown* in Layer 1): 36.2% of owned rows (Wan & McAuley report ~36% unplayed).
- Played ≥ 120 min: 38.1% of owned rows; 59.8% of played rows.
- Owned per user: median 40, p90 164; played per user: median 28.
- Distinct games: 10,978; in Kaggle catalog: 79.3% of rows (72.8% of distinct games).
- Steam type of owned rows: game 73.1%, delisted/unknown 26.0%, dlc 0.3%, software 0.3%, video 0.2%
- Active in the 2 weeks before the crawl (playtime_2weeks > 0): 2.7% of rows.
