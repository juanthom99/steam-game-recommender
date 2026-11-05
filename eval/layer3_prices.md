# Layer 3 value per dollar at three prices (test set, 5+ visible games)

> Disclosed addition: the frozen protocol lists regular price only. Computed from the saved test lists (`eval/run_test.py`); the test set was not scored again.

Prices from IsThereAnyDeal (US), snapshot 2026-11-04. 'Best price now' is the lowest current price across shops; it changes daily, so treat that column as a snapshot. Hours are the player's lifetime hours in the game. Regular price is the same column `eval/layer3.py` uses.

| model                     |   paid hits |   median hours per $ (regular) |   median hours per $ (best price now) |   median hours per $ (all-time low) |   share with a price now |   share with an all-time low |   median discount now |   hits within 5% of all-time low now |
|:--------------------------|------------:|-------------------------------:|--------------------------------------:|------------------------------------:|-------------------------:|-----------------------------:|----------------------:|-------------------------------------:|
| MostPopular               |        1058 |                          4.068 |                                 6.85  |                              31.946 |                    1     |                        1     |                 0.383 |                                0.112 |
| item-kNN                  |        5583 |                          2.208 |                                 5.283 |                              19.333 |                    0.882 |                        0.882 |                 0.224 |                                0.118 |
| EASE                      |        8025 |                          2.495 |                                 5.727 |                              20.96  |                    0.922 |                        0.922 |                 0.3   |                                0.135 |
| ALS                       |        5754 |                          2.136 |                                 5.469 |                              18.423 |                    0.919 |                        0.919 |                 0.401 |                                0.144 |
| Hybrid                    |        5766 |                          2.122 |                                 5.502 |                              18.429 |                    0.917 |                        0.917 |                 0.445 |                                0.144 |
| Hybrid-EASE               |        8062 |                          2.471 |                                 5.662 |                              20.842 |                    0.922 |                        0.922 |                 0.3   |                                0.134 |
| Hybrid: Try something new |        5056 |                          1.793 |                                 4.801 |                              16.438 |                    0.916 |                        0.916 |                 0.499 |                                0.129 |

Price data: [IsThereAnyDeal](https://isthereanydeal.com).
