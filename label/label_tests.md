# Layer 1 follow-up: testing better labels

- Beta mixture fitted per user for 1,903,309 users with ≥ 5 played games (54.4% of rows); pooled mixture for the rest (component means [0.319, 0.702]).
- Per-user component separation |mean_high − mean_low|: median 0.42, share of users with separation < 0.1 (mixture barely splits): 2.9%

## Comparison on report users

Kappa is the primary score; *coverage* below 100% means the label leaves ambiguous rows out (they are excluded from both training positives and evaluation negatives).

|                                          |   kappa |   coverage (rows labeled) |   enjoyed share |   sensitivity |   specificity |   Youden J |   precision of 'not enjoyed' |   ROC-AUC (score) |   PR-AUC not-rec (score) |
|:-----------------------------------------|--------:|--------------------------:|----------------:|--------------:|--------------:|-----------:|-----------------------------:|------------------:|-------------------------:|
| C percentile ≥ 0.1                       |  0.2078 |                    1      |          0.8861 |        0.9131 |        0.2781 |     0.1912 |                       0.344  |            0.6448 |                   0.265  |
| B ratio ≥ 0.2                            |  0.2141 |                    1      |          0.8721 |        0.9011 |        0.3048 |     0.2059 |                       0.3356 |            0.6467 |                   0.2836 |
| D two-sided (lo 0.1, hi 0.4)             |  0.2564 |                    0.7045 |          0.8512 |        0.8873 |        0.3802 |     0.2675 |                       0.3448 |          nan      |                 nan      |
| E Beta mixture, t = 0.5 (DP2Rec default) |  0.0893 |                    1      |          0.5051 |        0.5309 |        0.6523 |     0.1832 |                       0.1856 |            0.6242 |                   0.2056 |
| E Beta mixture, t = 0.1 (tuned)          |  0.143  |                    1      |          0.7278 |        0.7558 |        0.443  |     0.1987 |                       0.2292 |            0.6242 |                   0.2056 |
| E + 2 h floor, t = 0.1                   |  0.1469 |                    1      |          0.7236 |        0.7527 |        0.4534 |     0.206  |                       0.231  |          nan      |                 nan      |

## Two-sided grid (calibration users)

Pre-declared selection rule: highest kappa with coverage ≥ 70%.

|   lo |     0.2 |     0.3 |   0.4 |   0.5 |   0.6 |   0.7 |
|-----:|--------:|--------:|------:|------:|------:|------:|
| 0.05 |   0.215 |   0.24  | 0.265 | 0.29  | 0.315 | 0.34  |
| 0.1  |   0.22  |   0.24  | 0.257 | 0.272 | 0.285 | 0.293 |
| 0.15 |   0.203 |   0.218 | 0.229 | 0.238 | 0.243 | 0.241 |
| 0.2  | nan     |   0.194 | 0.202 | 0.206 | 0.206 | 0.2   |
| 0.3  | nan     | nan     | 0.154 | 0.154 | 0.15  | 0.141 |

|   lo |     0.2 |     0.3 |   0.4 |   0.5 |   0.6 |   0.7 |
|-----:|--------:|--------:|------:|------:|------:|------:|
| 0.05 |   0.852 |   0.757 | 0.658 | 0.558 | 0.459 | 0.359 |
| 0.1  |   0.899 |   0.803 | 0.705 | 0.605 | 0.505 | 0.406 |
| 0.15 |   0.947 |   0.852 | 0.753 | 0.654 | 0.554 | 0.454 |
| 0.2  | nan     |   0.9   | 0.802 | 0.702 | 0.603 | 0.503 |
| 0.3  | nan     | nan     | 0.9   | 0.801 | 0.701 | 0.602 |

## Beta-mixture threshold (calibration users)

|     |   kappa (calib) |
|----:|----------------:|
| 0.1 |          0.1432 |
| 0.2 |          0.1283 |
| 0.3 |          0.1144 |
| 0.4 |          0.1016 |
| 0.5 |          0.0898 |

## Kappa by reviews per user (report users)

| reviews per user   |    rows (report) |   kappa C |   kappa D |   kappa E |
|:-------------------|-----------------:|----------:|----------:|----------:|
| 1–4                |      9.34332e+06 |    0.1858 |    0.2253 |    0.167  |
| 5–20               |      7.131e+06   |    0.2195 |    0.2714 |    0.1087 |
| 21–100             |      3.2706e+06  |    0.2272 |    0.2855 |    0.154  |
| 100+               | 740381           |    0.1721 |    0.2307 |    0.1465 |
