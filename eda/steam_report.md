# Steam Web API EDA

## Steam store sample: 300 games (155 popular, 145 long-tail)

**Response coverage**

|              |   all |   popular |   long-tail |
|:-------------|------:|----------:|------------:|
| success=true |     1 |         1 |           1 |
| HTTP 200     |     1 |         1 |           1 |

- Failed lookups (likely delisted or region-locked): 0
- Redirected to a different app_id: 0
- type values: {'game': 272, 'dlc': 25, 'demo': 1, 'series': 1, 'music': 1}

**Field coverage among successful responses**

|                             |   share |
|:----------------------------|--------:|
| header_image                |   1     |
| price_overview (paid price) |   0.783 |
| is_free                     |   0.167 |
| free or priced              |   0.95  |
| screenshots >= 1            |   1     |
| short_description           |   1     |
| genres                      |   0.997 |
| metacritic                  |   0.283 |

- Currencies returned: {'USD': 235}
- Title mismatches vs Kaggle (case-insensitive): 13

**Price drift: Kaggle snapshot (late 2023) vs live Steam today**

- Note: Kaggle price_original is 0 for 41 paid games here (not on sale); price_final used instead.
- Games compared: 235
- Base price unchanged: 72.3%; higher now: 12.8%; lower now: 14.9%
- Median base price: Kaggle $12.99 vs live $14.99
- On sale right now: 19.1% (Kaggle snapshot: 9.8%)
- Kaggle 'free' games that now have a price: 1

Largest base-price changes:

|   app_id | title                                  |   kaggle_base |   price_initial_now |   change |
|---------:|:---------------------------------------|--------------:|--------------------:|---------:|
|    21090 | F.E.A.R.                               |         54.99 |                9.99 |   -45    |
|  1577120 | The Quarry                             |         20    |               59.99 |    39.99 |
|   698670 | Scorn                                  |         16    |               49.99 |    33.99 |
|  1937780 | Total War: PHARAOH                     |         60    |               29.99 |   -30.01 |
|   950050 | Starlink: Battle for Atlas             |         59.99 |               29.99 |   -30    |
|   242050 | Assassin’s Creed® IV Black Flag™       |         12    |               39.99 |    27.99 |
|  1328660 | Need for Speed™ Hot Pursuit Remastered |          4    |               29.99 |    25.99 |
|  1182900 | A Plague Tale: Requiem                 |         25    |               49.99 |    24.99 |
|   728880 | Overcooked! 2                          |         25    |               48.49 |    23.49 |
|     8850 | BioShock® 2                            |          0    |               19.99 |    19.99 |

**Title mismatches (Kaggle vs live)**

|   app_id | title                                               | name                                                       |
|---------:|:----------------------------------------------------|:-----------------------------------------------------------|
|  1476970 | IdleOn - The Idle MMO                               | IdleOn - The Incremental MMO                               |
|   248820 | Risk of Rain                                        | Risk of Rain (2013)                                        |
|  1250410 | Microsoft Flight Simulator 40th Anniversary Edition | Microsoft Flight Simulator (2020) 40th Anniversary Edition |
|    32370 | STAR WARS™ - Knights of the Old Republic™           | STAR WARS™ Knights of the Old Republic™                    |
|     9450 | Warhammer® 40000: Dawn of War® - Soulstorm          | Warhammer® 40,000: Dawn of War® - Soulstorm                |
|   457490 | Forgotten Not Lost - A Kinetic Novel                | Forgotten, Not Lost - A Kinetic Novel                      |
|   385370 | Radiator 2: Anniversary Edition                     | Radiator Forever                                           |
|  1093150 | Just Sleep - Meditate Focus Relax                   | Just Sleep - Meditate, Focus, Relax                        |
|  1461050 | The Game of Life 2 - The Ultimate Life Collection   | THE GAME OF LIFE 2: Ultimate Life Collection               |
|   922550 | keyg                                                | keyg: the last prison                                      |
|   950620 | Priest Simulator                                    | Priest Simulator: Vampire Show                             |
|  1644210 | Northgard - Ratatoskr Clan of the Squirrel          | Northgard - Ratatoskr, Clan of the Squirrel                |
|  1304600 | Hunt: Showdown - The Revenant                       | Hunt: Showdown 1896 - The Revenant                         |
