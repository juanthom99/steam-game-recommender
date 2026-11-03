# Data Profiles: all sources

One profile per source, same checklist: structure, column classes, completeness grade (Green > 99% non-null, Yellow 95-99, Orange 80-95, Red < 80), distributions, quality flags, relationships. Cross-source conclusions: [FINDINGS.md](FINDINGS.md).

| source                                             | grain                                                |     rows |   columns | worst completeness   |   high issues |   medium issues |
|:---------------------------------------------------|:-----------------------------------------------------|---------:|----------:|:---------------------|--------------:|----------------:|
| Kaggle games.csv                                   | game (Steam app)                                     |    50872 |        13 | Green                |             0 |               1 |
| Kaggle games_metadata.json                         | game                                                 |    50872 |         3 | Green                |             1 |               0 |
| Kaggle users.csv                                   | user                                                 | 14306064 |         3 | Green                |             0 |               1 |
| Kaggle recommendations.csv                         | user review of a game                                | 41154794 |         8 | Green                |             0 |               2 |
| Steam store appdetails (300-game sample)           | game (live store page)                               |      300 |        15 | Red                  |             5 |               2 |
| Steam IStoreService app catalog                    | Steam app (any type)                                 |   264125 |         4 | Green                |             1 |               0 |
| Steam GetOwnedGames (your library)                 | owned game for one user                              |       21 |        10 | Red                  |             1 |               0 |
| IsThereAnyDeal overview + prices (300-game sample) | game (ITAD id) with current and historical-low price |      277 |        10 | Orange               |             0 |               4 |
| FronkonGames steam-games-dataset                   | Steam game (store page + SteamSpy stats, Oct 2026)   |   124146 |        31 | Green                |             1 |              18 |
| McAuley australian_users_items (users)             | Steam user                                           |    88310 |         4 | Green                |             1 |               0 |
| McAuley australian_users_items (owned games)       | owned game for a user (full library)                 |  5153209 |         5 | Green                |             1 |               1 |
| McAuley australian_user_reviews                    | user review of a game                                |    59305 |         7 | Green                |             2 |               0 |
| McAuley steam_games (item metadata)                | Steam app (2018 crawl)                               |    32135 |        15 | Red                  |             6 |               5 |
| McAuley bundle_data                                | Steam bundle                                         |      615 |         7 | Green                |             0 |               0 |

Files: [fronkon_games.md](fronkon_games.md), [itad_sample.md](itad_sample.md), [kaggle_games.md](kaggle_games.md), [kaggle_games_metadata.md](kaggle_games_metadata.md), [kaggle_recommendations.md](kaggle_recommendations.md), [kaggle_users.md](kaggle_users.md), [mcauley_bundles.md](mcauley_bundles.md), [mcauley_steam_games.md](mcauley_steam_games.md), [mcauley_user_reviews.md](mcauley_user_reviews.md), [mcauley_users.md](mcauley_users.md), [mcauley_users_items.md](mcauley_users_items.md), [steam_catalog.md](steam_catalog.md), [steam_my_library.md](steam_my_library.md), [steam_store_sample.md](steam_store_sample.md)
