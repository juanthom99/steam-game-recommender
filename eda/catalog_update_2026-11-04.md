# Catalog changes since D2 (addendum)

The D2 data note (`d2/DATA_NOTE.md`, submitted, tag `d2-final`) describes the catalog before these fixes. Concerns 5 (missing tags) and 6 (sale prices in `price_regular`) are now largely resolved. Rules are listed in `clean/cleaning_report.md`; the backups are `games.before_steamspy.parquet` and `games.before_itad.parquet`.

| Rule | Source | What changed |
|---|---|---|
| G22 | SteamSpy | 46,184 games with no user tags got SteamSpy's tags (most-voted first) |
| G23 | SteamSpy | 70,151 crawl-only prices replaced by SteamSpy's regular price |
| G24 | IsThereAnyDeal | 112,906 prices replaced by Steam's current regular price (snapshot 2026-11-04); 82 paid games that showed $0 fixed, 994 games that went free marked free |

## Recommendable catalog, before and after

|                                                                  | at D2 (before refill)   | now (2026-11-04)   |
|:-----------------------------------------------------------------|:------------------------|:-------------------|
| recommendable games                                              | 111,167                 | 111,167            |
| no user tags (genres used instead)                               | 66.4%                   | 25.7%              |
| median tags per game                                             | 0                       | 11                 |
| regular price from Steam via IsThereAnyDeal (G24)                | 0.0%                    | 89.7%              |
| regular price from SteamSpy (G23)                                | 0.0%                    | 6.3%               |
| regular price from the Oct 2026 crawl only (may be a sale price) | 65.6%                   | 0.7%               |
| free games                                                       | 15.7%                   | 16.2%              |
| median regular price of paid games                               | $4.99                   | $5.99              |

## Effect on the model

- Content embeddings were rebuilt over the full catalog (113,498 games, `model/embed_catalog.py`); before, they covered only the 38k Kaggle titles.
- The evaluation was rerun with these inputs (Run 2, `eval/eval_report.md`); Run 1 is archived in `eval/run1/`.
- Value-per-dollar uses the G24 price (`eval/layer3_prices.md`).
