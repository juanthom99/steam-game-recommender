# Data dictionary

Cleaned tables in `data_clean/` (built by `clean/build_clean.py`; rules G/F/K/M/U in `clean/cleaning_report.md`). Missing % and examples are computed from the files.

## games.parquet

**Grain:** One row per Steam app (game, DLC, tool, removed app...). Merged catalog: Kaggle 2023 + FronkonGames Oct 2026 + McAuley + Steam app list.  
**Rows:** 137,725

| column                       | type                  |   % missing | example                                  | description                                                                                                                                                             |
|:-----------------------------|:----------------------|------------:|:-----------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| app_id                       | int64                 |         0   | 3255380                                  | Steam app id (primary key; joins every table)                                                                                                                           |
| title                        | string                |         0   | LUNAR Remastered Collection              | Display title, HTML entities decoded, hidden characters removed                                                                                                         |
| release_date                 | timestamp[us]         |         1.6 | 2025-07-03 00:00:00                      | Release date (Kaggle, else Fronkon)                                                                                                                                     |
| win                          | bool                  |        63.1 | True                                     | Runs on Windows                                                                                                                                                         |
| mac                          | bool                  |         1.6 | False                                    | Runs on macOS                                                                                                                                                           |
| linux                        | bool                  |         1.6 | False                                    | Runs on Linux                                                                                                                                                           |
| rating                       | string                |        63.1 | Positive                                 | Steam review summary label (Kaggle 2023, e.g. 'Very Positive')                                                                                                          |
| positive_ratio               | double                |        29.8 | 71.0                                     | % positive Steam reviews (Kaggle 2023)                                                                                                                                  |
| user_reviews                 | double                |         1.6 | 0.0                                      | Number of Steam reviews (Kaggle 2023)                                                                                                                                   |
| steam_deck                   | bool                  |        63.1 | True                                     | Steam Deck verified flag (Kaggle)                                                                                                                                       |
| description                  | string                |        14.5 | Experience the thrill of being a bus dri | Short store description (Kaggle, else Fronkon, else Steam backfill)                                                                                                     |
| tags                         | list<element: string> |         0   | []                                       | Steam user tags, most-voted first (empty list for 66% of recommendable games: the FronkonGames copy has no tags)                                                        |
| title_raw                    | string                |         0   | LUNAR Remastered Collection              | Title before cleaning (audit trail)                                                                                                                                     |
| title_norm                   | string                |         0   | lunar remastered collection              | Lower-case title without punctuation/edition words, for matching                                                                                                        |
| kaggle_price_regular         | double                |        63.1 | 0.0                                      | Regular USD price in Kaggle (2023)                                                                                                                                      |
| kaggle_price_final           | double                |        63.1 | 0.0                                      | Price paid at Kaggle crawl time, after discount                                                                                                                         |
| price_original_was_missing   | bool                  |        63.1 | False                                    | Kaggle listed regular price 0 on a paid game (rule G3)                                                                                                                  |
| kaggle_discount              | double                |        63.1 | 0.0                                      | Kaggle discount %                                                                                                                                                       |
| description_source           | string                |         0   | fronkon                                  | Where the description came from (kaggle / fronkon / steam / none)                                                                                                       |
| n_tags                       | int64                 |         0   | 0                                        | Number of tags                                                                                                                                                          |
| steam_name                   | string                |        65.8 | Bitburner                                | Name in Steam's app list                                                                                                                                                |
| steam_last_modified          | timestamp[us]         |        65.8 | 2026-09-15 16:25:45                      | Steam app list last-modified time                                                                                                                                       |
| item_type                    | string                |         0   | game                                     | game, dlc, demo, tool, software, video, music, mod, episode, playtest, removed, unknown                                                                                 |
| delisted                     | bool                  |         0   | False                                    | Store page no longer exists (kept for history, never recommended)                                                                                                       |
| dup_title                    | bool                  |         0   | False                                    | Shares a normalized title with another app (remasters, regional editions)                                                                                               |
| developer                    | string                |        89.2 | Indie Games Studio                       | Developer (McAuley)                                                                                                                                                     |
| publisher                    | string                |        89.7 | EuroVideo Medien                         | Publisher (McAuley)                                                                                                                                                     |
| specs                        | list<element: string> |        88.3 | ['Single-player', 'Multi-player', 'Co-op | Store features from McAuley (co-op, controller...)                                                                                                                      |
| early_access                 | bool                  |        88.2 | False                                    | Early Access flag (McAuley)                                                                                                                                             |
| mc_genres                    | list<element: string> |        89.1 | ['Casual']                               | Genres from McAuley                                                                                                                                                     |
| catalog_source               | string                |         0   | fronkon                                  | Which dataset the row came from (kaggle / fronkon / mcauley)                                                                                                            |
| genres                       | list<element: string> |         9.9 | ['Adventure', 'Casual', 'Indie']         | Store genres (Fronkon)                                                                                                                                                  |
| categories                   | list<element: string> |         9.9 | ['Single-player', 'Family Sharing']      | Store categories (Fronkon)                                                                                                                                              |
| f_developers                 | list<element: string> |         9.9 | ['ZERO5GAMES']                           | Developers (Fronkon)                                                                                                                                                    |
| f_publishers                 | list<element: string> |         9.9 | ['ZERO5GAMES']                           | Publishers (Fronkon)                                                                                                                                                    |
| header_image                 | string                |         9.9 | https://shared.akamai.steamstatic.com/st | Store header image URL                                                                                                                                                  |
| steamspy_median_playtime_min | double                |        81   | 7.0                                      | SteamSpy median lifetime playtime, minutes (null = unknown, rule F1)                                                                                                    |
| steamspy_avg_playtime_min    | double                |        81   | 7.0                                      | SteamSpy average lifetime playtime, minutes                                                                                                                             |
| steam_positive               | double                |         9.9 | 90.0                                     | Positive reviews (Fronkon, Oct 2026)                                                                                                                                    |
| steam_negative               | double                |         9.9 | 19.0                                     | Negative reviews (Fronkon, Oct 2026)                                                                                                                                    |
| owners_lo                    | double                |         9.9 | 0.0                                      | Estimated owners, low end of SteamSpy band                                                                                                                              |
| owners_hi                    | double                |         9.9 | 20000.0                                  | Estimated owners, high end                                                                                                                                              |
| fronkon_price                | double                |         9.9 | 0.99                                     | Price at Fronkon crawl (can be a sale price)                                                                                                                            |
| peak_ccu                     | double                |         9.9 | 0.0                                      | Peak concurrent players (Fronkon)                                                                                                                                       |
| achievements                 | double                |         9.9 | 0.0                                      | Number of achievements                                                                                                                                                  |
| adult                        | bool                  |         0   | False                                    | Sexually explicit content (rule G17); excluded from recommendations                                                                                                     |
| mature_18                    | bool                  |         0   | False                                    | Steam 18+ age gate (mostly violence); not filtered                                                                                                                      |
| price_regular                | double                |         1.6 | 0.0                                      | Regular USD price: higher of Kaggle 2023 regular and Fronkon 2026 when both exist (rule G18); Fronkon-only games are re-priced from SteamSpy by clean/merge_steamspy.py |
| price_source                 | string                |         0   | fronkon_2026_only                        | kaggle_2023_higher / fronkon_2026 / fronkon_2026_only (not yet cross-checked) / kaggle_2023 / none                                                                      |
| desc_short                   | bool                  |         0   | False                                    | Description under 40 characters                                                                                                                                         |
| desc_shared                  | bool                  |         0   | False                                    | Description shared by several apps                                                                                                                                      |
| desc_non_english             | bool                  |         0   | False                                    | Description mostly non-Latin script                                                                                                                                     |
| history_ok                   | bool                  |         0   | True                                     | Counts as play history (game/unknown/removed/mod/demo/episode)                                                                                                          |
| recommendable                | bool                  |         0   | True                                     | Candidate for recommendations: game, on sale, released, not adult, has store data                                                                                       |

## interactions_mcauley.parquet

**Grain:** One row per (player, owned app) from McAuley's Australian Steam crawl (2017): full libraries, played and unplayed.  
**Rows:** 5,094,082

| column           | type          |   % missing | example             | description                                                                  |
|:-----------------|:--------------|------------:|:--------------------|:-----------------------------------------------------------------------------|
| source           | string        |         0   | mcauley             | Always 'mcauley'                                                             |
| user_key         | int64         |         0   | 100053657           | Integer player id (map in users_mcauley_map)                                 |
| app_id           | int32         |         0   | 420                 | Steam app id                                                                 |
| playtime_min     | int32         |         0   | 34                  | Lifetime playtime, minutes, at crawl time                                    |
| playtime_2w_min  | int32         |         0   | 0                   | Playtime in the 2 weeks before the crawl, minutes                            |
| played           | bool          |         0   | True                | playtime_min > 0 (unplayed rows are 'unknown', not dislikes)                 |
| censored         | bool          |         0   | False               | Playtime hit a cap (always False here)                                       |
| is_game          | bool          |         0   | True                | App is a game (not DLC/tool/removed)                                         |
| item_type        | string        |         0   | game                | App type from the catalog                                                    |
| history_ok       | bool          |         0   | True                | App counts as play history                                                   |
| review_recommend | bool          |        99.1 | True                | Thumbs up (True) / down (False) if this player reviewed this game, else null |
| review_date      | timestamp[us] |        99.1 | 2014-11-27 00:00:00 | Review date                                                                  |
| helpful          | int32         |       100   | None                | Helpful votes on the review                                                  |
| funny            | int32         |       100   | None                | Funny votes on the review                                                    |

## interactions_kaggle.parquet

**Grain:** One row per (player, reviewed app) from the Kaggle Steam reviews dump (to Oct 2023). Only reviewed games: a partial library.  
**Rows:** 41,154,753

| column             | type          |   % missing | example             | description                                                    |
|:-------------------|:--------------|------------:|:--------------------|:---------------------------------------------------------------|
| source             | string        |           0 | kaggle              | Always 'kaggle'                                                |
| user_key           | int64         |           0 | 13596               | Kaggle user id                                                 |
| app_id             | int32         |           0 | 739630              | Steam app id                                                   |
| playtime_min       | int32         |           0 | 1182                | Hours at review time x 60 (export caps at 1,000 h)             |
| playtime_2w_min    | int32         |         100 | None                | Not available (0)                                              |
| played             | bool          |           0 | True                | playtime_min > 0                                               |
| censored           | bool          |           0 | False               | Hit the 1,000 h cap (rule K4)                                  |
| is_game            | bool          |           0 | True                | App is a game                                                  |
| history_ok         | bool          |           0 | True                | App counts as play history                                     |
| bulk_user          | bool          |           0 | False               | Bulk reviewer (rule K7)                                        |
| pre_release_review | bool          |           0 | False               | Review > 30 days before listed release (Early Access; rule K8) |
| review_recommend   | bool          |           0 | True                | Thumbs up / down                                               |
| review_date        | timestamp[us] |           0 | 2020-10-08 00:00:00 | Review date                                                    |
| helpful            | int32         |           0 | 2                   | Helpful votes                                                  |
| funny              | int32         |           0 | 0                   | Funny votes                                                    |

## users_kaggle.parquet

**Grain:** One row per Kaggle reviewer.  
**Rows:** 14,306,062

| column                | type   |   % missing |   example | description                                 |
|:----------------------|:-------|------------:|----------:|:--------------------------------------------|
| user_id               | int64  |           0 |   3402481 | Kaggle user id (= user_key)                 |
| products              | int64  |           0 |        13 | Apps owned per Kaggle (unreliable, rule U1) |
| reviews               | int64  |           0 |         1 | Reviews written on Steam                    |
| reviews_in_data       | int32  |           0 |         1 | Reviews present in this dataset             |
| products_inconsistent | bool   |           0 |     False | 0 products but has reviews                  |
| bulk_reviewer         | bool   |           0 |     False | Bulk reviewer (rule K7)                     |

## users_mcauley_map.parquet

**Grain:** One row per McAuley player.  
**Rows:** 70,912

| column        | type   |   % missing |           example | description                             |
|:--------------|:-------|------------:|------------------:|:----------------------------------------|
| user_key      | int64  |           0 |         100035456 | Integer id used in interactions_mcauley |
| mc_user_id    | string |           0 | 76561198009000573 | Original McAuley user id                |
| n_owned       | int64  |           0 |               206 | Apps owned                              |
| n_played      | int64  |           0 |               143 | Apps with playtime > 0                  |
| n_played_hist | int64  |           0 |               141 | Played apps that count as history       |
| collector     | bool   |           0 |             False | Owns >= 3,000 apps                      |
| no_played     | bool   |           0 |             False | Owns apps but played none               |

## steam_catalog_extra.parquet

**Grain:** Steam apps in no dataset (names only), for the weekly catalog refresh.  
**Rows:** 85,030

| column        | type          |   % missing | example             | description            |
|:--------------|:--------------|------------:|:--------------------|:-----------------------|
| app_id        | int64         |           0 | 4210130             | Steam app id           |
| name          | string        |           0 | RAID VR             | App name               |
| type          | string        |           0 | game                | App type               |
| last_modified | timestamp[us] |           0 | 2026-02-13 10:38:43 | Last modified on Steam |

## steam_reviews 2026 collection (`data_raw/steam_reviews/`)

Collected Oct 2026 from Steam's official IUserReviewsService and Web API. Player ids are salted SHA-256 hashes; no review text is stored.

| file | grain | key fields |
|---|---|---|
| reviews.jsonl | one recent review (an 'all' page and a 'negative' page per game, 1,004 games) | uid, app_id, voted_up, playtime_at_review, playtime_forever, playtime_2w, last_played, refunded, created, page |
| libraries.jsonl | one reviewer's full library (public profiles only; 2,696 public) | uid, public, games [app_id, playtime_forever, playtime_2w, last_played] |
| achievements.jsonl | one reviewer x reviewed game | uid, app_id, success, ach [name, achieved, unlock time] |
| global_pct.jsonl | one game | app_id, pct {achievement: global unlock %} |

## splits/ (reserved evaluation data)

| file | grain |
|---|---|
| players.parquet | one test or validation player: src, user_key, split |
| hidden_games.parquet | one played game of a test/validation player: src, user_key, app_id, split, hidden |
| manifest.json | the rule, counts and SHA-256 of each file |

Created 2026-11-02 16:20; see `eval/PROTOCOL.md`.
