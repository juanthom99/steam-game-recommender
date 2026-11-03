# Data Profile: Kaggle games_metadata.json

## Overview
- Grain: one row per game
- Rows: 50,872 | Columns: 3 | Memory: 18.2 MB
- Column types: 1 Identifier, 1 Text, 1 Structural
- Primary key `app_id` unique: True (0 duplicates)
- Text source for the search index and the model's content side

## Column Details (grouped by class)

| column      | class      | dtype   |   null % | completeness   |   distinct |   card. | top values                                                                                                                                                  | rarest                                                           | stats                                                                                                 |
|:------------|:-----------|:--------|---------:|:---------------|-----------:|--------:|:------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------|:------------------------------------------------------------------------------------------------------|
| app_id      | Identifier | int64   |        0 | Green          |      50872 |  1      | 13500 (0.0%); 22364 (0.0%); 113020 (0.0%); 226560 (0.0%); 249050 (0.0%)                                                                                     | 1402110; 2272250; 2488510                                        | min 10 / max 2599300; card. 1.000                                                                     |
| description | Text       | str     |        0 | Green          |      40244 |  0.7911 | (20.4%); Find the objects that are hi (0.1%); Minimal physical puzzle with (0.0%); Higurashi When They Cry is a (0.0%); Collect a 3D puzzle, transfe (0.0%) | Build better, togeth; Seiji Maruyama is a ; Embark on a journey  | len min 0 / avg 160 / max 530; empty 10,373; lead/trail whitespace 0; placeholders 10,375; case mixed |
| tags        | Structural | object  |        0 | Green          |      41069 |  0.8073 | [] (2.4%); ["Simulation"] (1.5%); ["Action"] (1.4%); ["Action", "Adventure"] (0.6%); ["Strategy"] (0.5%)                                                    | ["Early Access", "Li; ["Side Scroller", "B; ["Early Access", "FP | length min 0 / median 11 / max 20; empty 1,244                                                        |

## Data Quality Issues

- **High**: `description`: 20.4% empty strings

## Relationships and Patterns

- 1:1 with games.csv on `app_id` (missing either way: 0 / 0).
- 441 distinct tags; top 20 tags cover 39% of tag uses (tag vocabulary is concentrated).
