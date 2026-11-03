# Data Profile: Steam IStoreService app catalog

## Overview
- Grain: one row per Steam app (any type)
- Rows: 264,125 | Columns: 4 | Memory: 15.7 MB
- Column types: 1 Identifier, 1 Text, 1 Dimension, 1 Temporal
- Date range `last_modified`: 2015-11-12 17:55:14 to 2026-10-28 23:53:26
- Primary key `appid` unique: True (0 duplicates)
- Requires STEAM_API_KEY; gives the type for every app in one pass

## Column Details (grouped by class)

| column        | class      | dtype          |   null % | completeness   |   distinct |   card. | top values                                                                                                                                 | rarest                                                           | stats                                                                                        |
|:--------------|:-----------|:---------------|---------:|:---------------|-----------:|--------:|:-------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------|:---------------------------------------------------------------------------------------------|
| appid         | Identifier | int64          |     0    | Green          |     264125 |  1      | 10 (0.0%); 20 (0.0%); 30 (0.0%); 40 (0.0%); 50 (0.0%)                                                                                      | 4978440; 4978460; 4978480                                        | min 10 / max 5513550; card. 1.000                                                            |
| type          | Dimension  | str            |     0    | Green          |          5 |  0      | game (74.6%); dlc (24.2%); software (1.1%); video (0.0%); hardware (0.0%)                                                                  | software; video; hardware                                        | len min 3 / avg 4 / max 8; empty 0; lead/trail whitespace 0; placeholders 0; case lower      |
| last_modified | Temporal   | datetime64[us] |     0    | Green          |     262119 |  0.9924 | 2026-05-14 19:55:19 (0.0%); 2026-06-02 22:57:25 (0.0%); 2026-02-13 02:15:04 (0.0%); 2026-10-16 21:23:09 (0.0%); 2026-06-02 22:57:28 (0.0%) | 2026-09-18 22:29:49; 2026-09-18 22:29:36; 2026-09-18 22:30:04    | min 2015-11-12 17:55:14 / max 2026-10-28 23:53:26; future 3,420; years w/ no rows none       |
| name          | Text       | str            |     0.01 | Green          |     261431 |  0.9898 | Echoes (0.0%); Prism (0.0%); Abyss (0.0%); Don't Fall (0.0%); No Way Out (0.0%)                                                            | Steam Frame Ergonomi; Steam Frame Accessor; Steam Hardware Power | len min 1 / avg 22 / max 414; empty 0; lead/trail whitespace 351; placeholders 5; case mixed |

## Data Quality Issues

- **High**: `last_modified`: 3,420 dates after 2026-10-28
- **Low**: `name`: 351 values with leading/trailing whitespace

## Relationships and Patterns

| type | apps | in Kaggle games.csv |
|---|---:|---:|
| game | 197,118 | 38,379 |
| dlc | 64,013 | 7,955 |
| software | 2,923 | 689 |
| video | 54 | 43 |
| hardware | 17 | 1 |

- Kaggle app_ids not in today's catalog (delisted or removed): 3,805
- Steam **games** not in Kaggle: 158,739. They include releases after Oct 2023 (handled by the weekly catalog refresh) and older games Kaggle left out, since it kept only games with ≥ 10 user reviews.
- Kaggle items Steam types as DLC: 7,955. This gives `item_type` for nearly all games in one pass, replacing the ~7 h IsThereAnyDeal backfill.
