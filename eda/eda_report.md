# Steam Recommendations EDA

## Profile: games.csv (one row per game)

- Rows: 50,872  |  Columns: 13  |  Memory: 6 MB

| column         | dtype          |   null % |   distinct |   card. ratio |   min |      p1 |       p50 |            p95 |             p99 |           max |           mean |   zeros |
|:---------------|:---------------|---------:|-----------:|--------------:|------:|--------:|----------:|---------------:|----------------:|--------------:|---------------:|--------:|
| app_id         | int64          |        0 |      50872 |        1      |    10 | 21927.8 | 986085    |    2.14797e+06 |     2.35174e+06 |   2.5993e+06  |    1.05522e+06 |       0 |
| title          | str            |        0 |      50751 |        0.9976 |   nan |   nan   |    nan    |  nan           |   nan           | nan           |  nan           |     nan |
| date_release   | datetime64[us] |        0 |       4292 |        0.0844 |   nan |   nan   |    nan    |  nan           |   nan           | nan           |  nan           |     nan |
| win            | bool           |        0 |          2 |        0      |   nan |   nan   |    nan    |  nan           |   nan           | nan           |  nan           |     nan |
| mac            | bool           |        0 |          2 |        0      |   nan |   nan   |    nan    |  nan           |   nan           | nan           |  nan           |     nan |
| linux          | bool           |        0 |          2 |        0      |   nan |   nan   |    nan    |  nan           |   nan           | nan           |  nan           |     nan |
| rating         | str            |        0 |          9 |        0.0002 |   nan |   nan   |    nan    |  nan           |   nan           | nan           |  nan           |     nan |
| positive_ratio | int64          |        0 |        100 |        0.002  |     0 |    21   |     81    |  100           |   100           | 100           |   77.05        |      25 |
| user_reviews   | int64          |        0 |       4847 |        0.0953 |    10 |    10   |     49    | 3262           | 26064.6         |   7.49446e+06 | 1824.42        |       0 |
| price_final    | float64        |        0 |        436 |        0.0086 |     0 |     0   |      4.99 |   29.99        |    50           | 299.99        |    8.62        |    9105 |
| price_original | float64        |        0 |        183 |        0.0036 |     0 |     0   |      4.99 |   29.99        |    49.99        | 299.99        |    8.73        |   10090 |
| discount       | float64        |        0 |         75 |        0.0015 |     0 |     0   |      0    |   60           |    90           |  90           |    5.59        |   45903 |
| steam_deck     | bool           |        0 |          2 |        0      |   nan |   nan   |    nan    |  nan           |   nan           | nan           |  nan           |     nan |

- app_id unique: True
- Release dates: 1997-06-30 to 2023-10-24
- Duplicate titles: 121
- Free games (price_final == 0): 9,105 (17.9%)
- Currently discounted (discount > 0): 4,969
- price_final > price_original (suspicious): 985
- Games with < 10 user_reviews: 0 (0.0%)

**Rating label distribution**

| rating                  |   games |
|:------------------------|--------:|
| Positive                |   13502 |
| Very Positive           |   13139 |
| Mixed                   |   12157 |
| Mostly Positive         |    8738 |
| Mostly Negative         |    1849 |
| Overwhelmingly Positive |    1110 |
| Negative                |     303 |
| Very Negative           |      60 |
| Overwhelmingly Negative |      14 |

**Platform support (share of games)**

|            |   share |
|:-----------|--------:|
| win        |   0.984 |
| mac        |   0.256 |
| linux      |   0.178 |
| steam_deck |   1     |

**Games released per year (last 12 years)**

|   date_release |   games |
|---------------:|--------:|
|           2012 |     565 |
|           2013 |     822 |
|           2014 |    1921 |
|           2015 |    2963 |
|           2016 |    4209 |
|           2017 |    4989 |
|           2018 |    5461 |
|           2019 |    5057 |
|           2020 |    6135 |
|           2021 |    6774 |
|           2022 |    7265 |
|           2023 |    3425 |


## Profile: games_metadata.json (text for the RAG index)

- Rows: 50,872  |  Columns: 3  |  Memory: 18 MB

| column      | dtype   |   null % |   distinct |   card. ratio |   min |      p1 |    p50 |           p95 |           p99 |          max |          mean |   zeros |
|:------------|:--------|---------:|-----------:|--------------:|------:|--------:|-------:|--------------:|--------------:|-------------:|--------------:|--------:|
| app_id      | int64   |        0 |      50872 |        1      |    10 | 21927.8 | 986085 |   2.14797e+06 |   2.35174e+06 |   2.5993e+06 |   1.05522e+06 |       0 |
| description | str     |        0 |      40244 |        0.7911 |   nan |   nan   |    nan | nan           | nan           | nan          | nan           |     nan |
| tags        | object  |        0 |      41069 |        0.8073 |   nan |   nan   |    nan | nan           | nan           | nan          | nan           |     nan |

- Empty descriptions: 10,373 (20.4%)
- Games with no tags: 1,244 (2.4%)
- Description length (chars): median 178, p95 298, max 530
- Tags per game: median 11, max 20
- metadata app_ids missing from games.csv: 0
- games.csv app_ids missing metadata: 0

- Distinct tags: 441

**Top 25 tags**

| tags           |   games |
|:---------------|--------:|
| Indie          |   27957 |
| Singleplayer   |   22566 |
| Action         |   21897 |
| Adventure      |   20183 |
| Casual         |   17844 |
| Simulation     |   12691 |
| 2D             |   11438 |
| Strategy       |   11093 |
| RPG            |   10156 |
| Atmospheric    |    8688 |
| Puzzle         |    7585 |
| Story Rich     |    7149 |
| Multiplayer    |    6575 |
| 3D             |    6142 |
| Pixel Graphics |    6028 |
| Exploration    |    5769 |
| Cute           |    5702 |
| Colorful       |    5693 |
| Free to Play   |    5645 |
| First-Person   |    5570 |
| Early Access   |    5308 |
| Fantasy        |    5174 |
| Anime          |    5002 |
| Funny          |    4956 |
| Horror         |    4789 |


## Profile: users.csv (one row per user)

- Rows: 14,306,064  |  Columns: 3  |  Memory: 343 MB

| column   | dtype   |   null % |   distinct |   card. ratio |   min |     p1 |          p50 |           p95 |          p99 |             max |          mean |   zeros |
|:---------|:--------|---------:|-----------:|--------------:|------:|-------:|-------------:|--------------:|-------------:|----------------:|--------------:|--------:|
| user_id  | int64   |        0 |   14306064 |        1      |     0 | 143061 |  7.15303e+06 |   1.35908e+07 |   1.4163e+07 |     1.43061e+07 |   7.15303e+06 |       1 |
| products | int64   |        0 |       7572 |        0.0005 |     0 |      2 | 55           | 401           | 946          | 32214           | 116.37        |  139318 |
| reviews  | int64   |        0 |        681 |        0      |     0 |      0 |  1           |   9           |  24          |  6045           |   2.88        |  525005 |

- user_id unique: True
- Users with 0 reviews: 525,005
- Users with >= 5 reviews: 1,910,831 (13.4%)


## Profile: recommendations.csv (one row per user review of a game)

- Rows: 41,154,794  |  Columns: 8  |  Memory: 1,358 MB

| column         | dtype          |   null % |   distinct |   card. ratio |   min |       p1 |              p50 |           p95 |           p99 |             max |             mean |            zeros |
|:---------------|:---------------|---------:|-----------:|--------------:|------:|---------:|-----------------:|--------------:|--------------:|----------------:|-----------------:|-----------------:|
| app_id         | int32          |        0 |      37610 |        0.0009 |    10 |    420   | 435150           |   1.54545e+06 |   1.91959e+06 |     2.25329e+06 | 603272           |      0           |
| helpful        | int32          |        0 |       3910 |        0.0001 |     0 |      0   |      0           |   8           |  49           | 36212           |      3.2         |      3.24615e+07 |
| funny          | int32          |        0 |       2756 |        0.0001 |     0 |      0   |      0           |   2           |  13           | 28109           |      1.06        |      3.85515e+07 |
| date           | datetime64[us] |        0 |       4450 |        0.0001 |   nan |    nan   |    nan           | nan           | nan           |   nan           |    nan           |    nan           |
| is_recommended | bool           |        0 |          2 |        0      |   nan |    nan   |    nan           | nan           | nan           |   nan           |    nan           |    nan           |
| hours          | float32        |        0 |      10001 |        0.0002 |     0 |      0.2 |     27.3         | 517.4         | 864.5         |  1000           |    100.6         | 176329           |
| user_id        | int32          |        0 |   13781059 |        0.3349 |     0 | 154110   |      7.54645e+06 |   1.35846e+07 |   1.41631e+07 |     1.43061e+07 |      7.45058e+06 |     28           |
| review_id      | int32          |        0 |   41154794 |        1      |     0 | 411548   |      2.05774e+07 |   3.90971e+07 |   4.07432e+07 |     4.11548e+07 |      2.05774e+07 |      1           |

- review_id unique: True
- Duplicate (user_id, app_id) pairs: 21
- Date range: 2010-10-15 to 2022-12-31
- Future dates (after 2026-10-28): 0
- Recommended share: 85.8%  <- class imbalance for training
- hours == 0: 176,329; hours >= 999: 3,024 (possible cap)
- app_ids not in games.csv: 0
- user_ids not in users.csv: 0

- Interaction matrix: 13,781,059 users x 37,610 games, density 0.007940%

**Reviews per user / per game (long tail check)**

|       |   reviews per user |   reviews per game |
|:------|-------------------:|-------------------:|
| count |        1.37811e+07 |            37610   |
| mean  |        3           |             1094.3 |
| std   |        8.1         |             7689.3 |
| min   |        1           |                1   |
| 50%   |        1           |               39   |
| 75%   |        3           |              179.8 |
| 90%   |        6           |              969.1 |
| 99%   |       25           |            23476.2 |
| max   |     6045           |           319492   |

- Top 1% of games get 55.6% of all reviews (popularity bias)
- Users with 1 review (cold start): 7,573,027 (55.0%)
- Users with >= 5 reviews: 1,910,831 (13.9%)

**Reviews per year**

|   date |   reviews |
|-------:|----------:|
|   2010 |     12201 |
|   2011 |     71546 |
|   2012 |    101726 |
|   2013 |    335335 |
|   2014 |   1143156 |
|   2015 |   1477099 |
|   2016 |   2226413 |
|   2017 |   2834442 |
|   2018 |   2845219 |
|   2019 |   4226834 |
|   2020 |   7488439 |
|   2021 |   8802857 |
|   2022 |   9589527 |

**Hours played vs recommendation**

| is_recommended   |       count |   mean |   std |   min |   50% |   90% |   max |
|:-----------------|------------:|-------:|------:|------:|------:|------:|------:|
| False            | 5.8504e+06  |   80.9 | 170.6 |     0 |  11.1 | 255.1 |  1000 |
| True             | 3.53044e+07 |  103.9 | 176.9 |     0 |  30.3 | 310.9 |  1000 |

**Correlations (sample of 2M reviews)**

|                |   helpful |   funny |   hours |   is_recommended |
|:---------------|----------:|--------:|--------:|-----------------:|
| helpful        |     1     |   0.408 |  -0.042 |           -0.198 |
| funny          |     0.408 |   1     |  -0.043 |           -0.117 |
| hours          |    -0.042 |  -0.043 |   1     |            0.156 |
| is_recommended |    -0.198 |  -0.117 |   0.156 |            1     |

**games.csv numeric correlations (Spearman)**

|                |   positive_ratio |   user_reviews |   price_final |   price_original |   discount |
|:---------------|-----------------:|---------------:|--------------:|-----------------:|-----------:|
| positive_ratio |            1     |          0.046 |         0.016 |           -0.003 |      0.019 |
| user_reviews   |            0.046 |          1     |         0.18  |            0.109 |     -0.064 |
| price_final    |            0.016 |          0.18  |         1     |            0.893 |     -0.122 |
| price_original |           -0.003 |          0.109 |         0.893 |            1     |      0.102 |
| discount       |            0.019 |         -0.064 |        -0.122 |            0.102 |      1     |
