# Data Profile: McAuley steam_games (item metadata)

## Overview
- Grain: one row per Steam app (2018 crawl)
- Rows: 32,135 | Columns: 15 | Memory: 17.9 MB
- Column types: 4 Text, 3 Structural, 3 Metric, 2 Dimension, 1 Temporal, 1 Boolean, 1 Identifier
- Date range `release_date`: 1970-07-15 00:00:00 to 2021-12-31 00:00:00
- Primary key `app_id` unique: False (2 duplicates)
- `price` mixes numbers and text such as 'Free To Play'; split into price_num / price_text

## Column Details (grouped by class)

| column         | class      | dtype          |   null % | completeness   |   distinct |   card. | top values                                                                                                                                                                   | rarest                                                           | stats                                                                                                                                              |
|:---------------|:-----------|:---------------|---------:|:---------------|-----------:|--------:|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------|
| app_id         | Identifier | Int64          |     0.01 | Green          |      32132 |  0.9999 | 612880 (0.0%); 761140 (0.0%); 643980 (0.0%); 670290 (0.0%); 767400 (0.0%)                                                                                                    | 610660; 658870; 681550                                           | min 10 / max 2028850; card. 1.000                                                                                                                  |
| price_text     | Dimension  | string         |    94.06 | Red            |         18 |  0.0006 | Free (47.4%); Free to Play (27.2%); Free To Play (24.2%); Free Mod (0.2%); Free Demo (0.2%)                                                                                  | Free to Try; Free Movie; Free to Use                             | len min 4 / avg 8 / max 29; empty 0; lead/trail whitespace 0; placeholders 0; case mixed                                                           |
| sentiment      | Dimension  | str            |    22.35 | Red            |         18 |  0.0006 | Mixed (16.4%); Very Positive (15.5%); Positive (13.1%); Mostly Positive (11.0%); 1 user reviews (10.0%)                                                                      | Negative; Very Negative; Overwhelmingly Negat                    | len min 5 / avg 12 / max 23; empty 0; lead/trail whitespace 0; placeholders 0; case mixed                                                          |
| discount_price | Metric     | float64        |    99.3  | Red            |         82 |  0.0026 | 22.66 (15.6%); 0.49 (10.2%); 0.89 (3.1%); 59.11 (3.1%); 0.69 (3.1%)                                                                                                          | 3.19; 11.69; 11.99                                               | min 0.49 / p1 0.49 / p5 0.49 / p25 1.39 / p50 4.19 / p75 22.66 / p95 49.96 / p99 74.98 / max 139.99; mean 11.93 sd 17.49; zeros 0; neg 0; skew 3.1 |
| metascore      | Metric     | float64        |    91.89 | Red            |         70 |  0.0022 | 80.0 (4.8%); 74.0 (4.1%); 77.0 (4.0%); 75.0 (4.0%); 76.0 (3.9%)                                                                                                              | 27.0; 29.0; 30.0                                                 | min 20.00 / p1 40.06 / p5 53.0 / p25 66.0 / p50 74.0 / p75 80.0 / p95 87.0 / p99 92.0 / max 96.00; mean 72.26 sd 10.83; zeros 0; neg 0; skew -0.8  |
| price_num      | Metric     | float64        |    10.23 | Orange         |        144 |  0.0045 | 4.99 (14.8%); 9.99 (13.5%); 2.99 (11.9%); 0.99 (9.0%); 1.99 (8.8%)                                                                                                           | 124.99; 19.98; 160.91                                            | min 0.49 / p1 0.99 / p5 0.99 / p25 2.99 / p50 4.99 / p75 9.99 / p95 29.99 / p99 59.99 / max 995.00; mean 9.45 sd 16.25; zeros 0; neg 0; skew 20.5  |
| release_date   | Temporal   | datetime64[us] |     7.32 | Orange         |       3457 |  0.1076 | 2012-10-16 00:00:00 (0.3%); 2017-08-31 00:00:00 (0.3%); 2017-09-26 00:00:00 (0.3%); 2017-06-21 00:00:00 (0.3%); 2017-07-25 00:00:00 (0.3%)                                   | 2004-03-01 00:00:00; 2016-11-19 00:00:00; 2018-10-01 00:00:00    | min 1970-07-15 00:00:00 / max 2021-12-31 00:00:00; future 0; years w/ no rows [1971, 1972, 1973, 1974, 1976, 1977, 1978, 1979, 2020]               |
| early_access   | Boolean    | bool           |     0    | Green          |          2 |  0.0001 | False (93.9%); True (6.1%)                                                                                                                                                   | False; True                                                      | true 1,947 / false 30,188; true rate 6.1%                                                                                                          |
| app_name       | Text       | str            |     0.01 | Green          |      32094 |  0.9987 | Soundtrack (0.0%); Batman: Arkham City - Game o (0.0%); The Dream Machine: Chapter 4 (0.0%); Dark Matter (0.0%); Taxi (0.0%)                                                 | Russian Roads; EXIT 2 - Directions; Maze Run VR                  | len min 1 / avg 27 / max 105; empty 0; lead/trail whitespace 0; placeholders 0; case mixed                                                         |
| developer      | Text       | str            |    10.27 | Orange         |      10992 |  0.3421 | Ubisoft - San Francisco (4.4%); SmiteWorks USA, LLC (2.8%); Dovetail Games (0.9%); KOEI TECMO GAMES CO., LTD. (0.8%); Paradox Development Studio (0.5%)                      | Oscar Ortigueira Lóp; INGAME; Bidoniera Games                    | len min 1 / avg 17 / max 191; empty 0; lead/trail whitespace 0; placeholders 0; case mixed                                                         |
| publisher      | Text       | str            |    25.06 | Red            |       8239 |  0.2564 | Ubisoft (1.6%); Dovetail Games - Trains (1.5%); Degica (1.2%); Paradox Interactive (1.1%); SEGA (1.0%)                                                                       | OrtiGames/OrtiSoft; INGAME; Bidoniera Games                      | len min 1 / avg 16 / max 82; empty 0; lead/trail whitespace 0; placeholders 22; case mixed                                                         |
| title          | Text       | str            |     6.38 | Orange         |      30054 |  0.9352 | Soundtrack (0.0%); Batman: Arkham City - Game o (0.0%); The Dream Machine: Chapter 4 (0.0%); Dark Matter (0.0%); Taxi (0.0%)                                                 | LOGistICAL: South Af; Russian Roads; EXIT 2 - Directions         | len min 1 / avg 28 / max 109; empty 0; lead/trail whitespace 0; placeholders 0; case mixed                                                         |
| genres         | Structural | object         |    10.22 | Orange         |        884 |  0.0275 | NaN (10.2%); ["Action"] (5.9%); ["Action", "Indie"] (5.1%); ["Simulation"] (4.3%); ["Casual", "Simulation"] (4.2%)                                                           | ["Strategy", "Action; ["Casual", "Strategy; ["Adventure", "Casua | length min 1 / median 2 / max 11; empty 0                                                                                                          |
| specs          | Structural | object         |     2.08 | Yellow         |       4650 |  0.1447 | ["Single-player"] (8.7%); ["Single-player", "Downloada (3.7%); ["Single-player", "Shared/Sp (3.2%); ["Single-player", "Steam Ach (2.6%); ["Multi-player", "Co-op", "C (2.4%) | ["Steam Workshop", "; ["Single-player", "M; ["Multi-player", "Co | length min 1 / median 4 / max 21; empty 0                                                                                                          |
| tags           | Structural | object         |     0.51 | Green          |      15396 |  0.4791 | ["Casual", "Simulation"] (4.0%); ["Action"] (3.4%); ["Simulation"] (3.4%); ["Strategy", "RPG", "Indie"] (2.0%); ["Strategy"] (1.9%)                                          | ["Action", "Indie", ; ["Indie", "Casual", ; ["Early Access", "Ad | length min 1 / median 4 / max 20; empty 0                                                                                                          |

## Data Quality Issues

- **High**: `discount_price`: 99.3% null (alert)
- **High**: `publisher`: 25.1% null (alert)
- **High**: `sentiment`: 22.3% null (alert)
- **High**: `metascore`: 91.9% null (alert)
- **High**: `app_id` has 2 duplicate rows
- **High**: `price_text`: 94.1% null (alert)
- **Medium**: `release_date`: 7.3% null (warn)
- **Medium**: `developer`: 10.3% null (warn)
- **Medium**: `price_num`: 10.2% null (warn)
- **Medium**: `genres`: 10.2% null (warn)
- **Medium**: `title`: 6.4% null (warn)
- **Low**: `price_text`: 1 values differ only by case/whitespace
- **Info**: `price_num` is heavily skewed (skew 20.5): use medians/log scale, not means

## Relationships and Patterns

- Rows with no app id: 2.
- Overlap with Kaggle catalog: 50.5%. Kaggle is the newer, richer catalog; this file mostly adds `specs` (single-player, co-op, controller support …) and `developer`/`publisher`.
