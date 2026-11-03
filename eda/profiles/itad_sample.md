# Data Profile: IsThereAnyDeal overview + prices (300-game sample)

## Overview
- Grain: one row per game (ITAD id) with current and historical-low price
- Rows: 277 | Columns: 10 | Memory: 0.0 MB
- Column types: 5 Metric, 2 Identifier, 2 Dimension, 1 Temporal
- Date range `low_date`: 2013-07-30 17:13:04 to 2026-10-26 17:21:40
- Primary key `app_id` unique: True (0 duplicates)
- Steam ids sent 300, matched 300; no overview for 23 matched ids

## Column Details (grouped by class)

| column         | class      | dtype          |   null % | completeness   |   distinct |   card. | top values                                                                                                                                                                              | rarest                                                           | stats                                                                                                                                            |
|:---------------|:-----------|:---------------|---------:|:---------------|-----------:|--------:|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------|
| app_id         | Identifier | int64          |        0 | Green          |        277 |  1      | 880830 (0.4%); 48000 (0.4%); 304390 (0.4%); 8850 (0.4%); 1074320 (0.4%)                                                                                                                 | 2025330; 1304600; 1461050                                        | min 3830 / max 2350550; card. 1.000                                                                                                              |
| itad_id        | Identifier | str            |        0 | Green          |        277 |  1      | 018d937e-ea09-72f4-8a35-bb36 (0.4%); 018d937e-ea32-7036-ad1c-5f8f (0.4%); 018d937e-ea45-71c7-84fa-91cf (0.4%); 018d937e-ea52-713b-b1d2-963f (0.4%); 018d937e-ea78-727d-b0a2-a48a (0.4%) | 018d97b6-162a-7235-b; 0191551d-b356-7307-9; 019546e7-494a-72b8-9 |                                                                                                                                                  |
| best_shop      | Dimension  | str            |        0 | Green          |         23 |  0.083  | Steam (48.7%); GOG (8.7%); GameBillet (7.9%); Fanatical (6.5%); Humble Store (4.3%)                                                                                                     | Playsum; GamesPlanet DE; EA Store                                | len min 3 / avg 8 / max 15; empty 0; lead/trail whitespace 0; placeholders 0; case mixed                                                         |
| low_shop       | Dimension  | str            |       13 | Orange         |         21 |  0.0758 | Steam (60.6%); GameBillet (13.7%); Fanatical (5.0%); Humble Store (2.9%); GreenManGaming (2.9%)                                                                                         | Blizzard; EA Store; JoyBuggy                                     | len min 3 / avg 7 / max 15; empty 0; lead/trail whitespace 0; placeholders 0; case mixed                                                         |
| all_time_low   | Metric     | float64        |       13 | Orange         |        131 |  0.4729 | 1.49 (5.8%); 0.49 (5.4%); 0.99 (4.6%); 2.99 (3.3%); 5.99 (3.3%)                                                                                                                         | 6.7; 5.91; 6.14                                                  | min 0.19 / p1 0.27 / p5 0.49 / p25 0.99 / p50 2.19 / p75 5.93 / p95 17.49 / p99 23.57 / max 41.04; mean 4.40 sd 5.49; zeros 0; neg 0; skew 2.7   |
| best_price_now | Metric     | float64        |        0 | Green          |        105 |  0.3791 | 0.0 (17.7%); 2.99 (5.4%); 4.99 (4.7%); 9.99 (4.3%); 1.99 (3.6%)                                                                                                                         | 26.09; 6.79; 3.1                                                 | min 0.00 / p1 0.0 / p5 0.0 / p25 1.25 / p50 4.99 / p75 9.99 / p95 29.99 / p99 52.22 / max 59.99; mean 8.63 sd 10.93; zeros 49; neg 0; skew 2.2   |
| cut_now        | Metric     | int64          |        0 | Green          |         49 |  0.1769 | 0 (50.5%); 80 (4.7%); 70 (4.3%); 75 (3.6%); 90 (3.2%)                                                                                                                                   | 13; 66; 56                                                       | min 0.00 / p1 0.0 / p5 0.0 / p25 0.0 / p50 0.0 / p75 65.0 / p95 86.0 / p99 90.0 / max 92.00; mean 28.25 sd 34.22; zeros 140; neg 0; skew 0.6     |
| n_deals        | Metric     | int64          |        0 | Green          |         26 |  0.0939 | 1 (42.6%); 3 (11.2%); 2 (10.1%); 4 (4.3%); 16 (2.9%)                                                                                                                                    | 21; 29; 26                                                       | min 1.00 / p1 1.0 / p5 1.0 / p25 1.0 / p50 2.0 / p75 9.0 / p95 20.0 / p99 24.0 / max 29.00; mean 5.63 sd 6.68; zeros 0; neg 0; skew 1.4          |
| regular_price  | Metric     | float64        |        0 | Green          |         35 |  0.1264 | 0.0 (17.7%); 9.99 (10.1%); 19.99 (9.7%); 29.99 (8.3%); 14.99 (6.9%)                                                                                                                     | 4.95; 8.99; 16.99                                                | min 0.00 / p1 0.0 / p5 0.0 / p25 2.99 / p50 9.99 / p75 19.99 / p95 49.99 / p99 59.99 / max 66.91; mean 14.94 sd 15.43; zeros 49; neg 0; skew 1.3 |
| low_date       | Temporal   | datetime64[us] |       13 | Orange         |        240 |  0.8664 | 2025-11-24 00:55:48 (0.8%); 2019-02-04 19:12:05 (0.4%); 2022-12-22 18:34:05 (0.4%); 2025-12-18 20:29:38 (0.4%); 2026-10-23 08:26:17 (0.4%)                                              | 2026-06-25 18:21:39; 2021-08-25 17:33:25; 2026-09-13 23:17:21    | min 2013-07-30 17:13:04 / max 2026-10-26 17:21:40; future 0; years w/ no rows none                                                               |

## Data Quality Issues

- **Medium**: `low_shop`: 13.0% null (warn)
- **Medium**: `cut_now`: one value (0) is 51% of rows (default/placeholder?)
- **Medium**: `all_time_low`: 13.0% null (warn)
- **Medium**: `low_date`: 13.0% null (warn)

## Relationships and Patterns

- `app_id` ↔ `itad_id` via /lookup/id/shop/61; ITAD ids are UUIDs.
- all_time_low ≤ best_price_now always holds: 82% of rows.
- Free games show regular_price 0, so exclude them from value-per-dollar math.
