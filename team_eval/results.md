# Team comparison: our models on the shared validation holdouts

Built with `team_eval/` (validation players only; the test set is untouched). Scored by `team_eval/evaluate.py`, the same
script teammates use, so any model scored with it is directly comparable. Run date: 2026-11-04.

**Summary**
- EASE and Hybrid-EASE beat MostPopular on every accuracy and playtime metric, on all three holdouts (80/20, 75/25, 50/50).
  80/20: NDCG@10 0.276 vs 0.038; HitRate@10 (any hidden game) 0.75 vs 0.33; picks within 2x of the player's playtime 36% vs 22%.
- Hybrid-EASE vs EASE: +0.001 NDCG@10 on 80/20 and 75/25, no difference on 50/50. We lead with EASE (simpler); the hybrid's
  content side matters for new games EASE cannot score, which this offline test barely contains.
- Weak spot: Rob's soft-fail flags. About 32% of our picks carry at least one flag (mostly "like quit games"), vs 17% for
  MostPopular, and regret is 19% vs 10%. Earlier diagnosis (eval/diagnosis_report.md): the regret gap is mostly a popularity-mix
  effect, since MostPopular only picks the very top games.
- Check: 80/20 reproduces Run 2's validation numbers (MostPopular 0.0379, Hybrid-EASE 0.2773 vs 0.2771 in tuning).

## Holdout 80/20 (visible/hidden)

|                     |      ease |   hybrid_ease |   mostpopular |
|:--------------------|----------:|--------------:|--------------:|
| players             | 8112.0000 |     8112.0000 |     8112.0000 |
| picks per player    |   10.0000 |       10.0000 |       10.0000 |
| owned picks %       |    0.0000 |        0.0000 |        0.0000 |
| not recommendable % |    0.0000 |        0.0000 |        0.0000 |
| NDCG@10             |    0.2763 |        0.2773 |        0.0379 |
| HitRate@10          |    0.6371 |        0.6384 |        0.1903 |
| HitRate@10 (any)    |    0.7465 |        0.7479 |        0.3320 |
| Coverage@10         |    0.0240 |        0.0245 |        0.0003 |
| Popularity pct      |   99.7119 |       99.7039 |       99.9960 |
| Tag distance        |    0.5028 |        0.5016 |        0.5786 |
| Playtime gap        |    0.5313 |        0.5284 |        0.7422 |
| Within 2x %         |   36.3895 |       36.5953 |       21.6211 |
| Playtime known %    |   96.4559 |       96.3178 |      100.0000 |
| Playtime gap (avg)  |    0.5559 |        0.5538 |        0.7842 |
| Within 2x (avg) %   |   33.0002 |       33.1921 |       20.3538 |
| Regret %            |   19.3840 |       19.5281 |       10.2715 |
| Flag: negative %    |    0.1146 |        0.1183 |        0.0000 |
| Flag: short %       |    8.2236 |        8.3703 |        0.0000 |
| Flag: like quit %   |   27.8094 |       28.0067 |       16.8676 |
| Any flag %          |   31.6827 |       31.9798 |       16.8676 |
| 2+ flags %          |    4.4625 |        4.5131 |        0.0000 |

| model       |   NDCG@10 minus ease | 95% CI             |
|:------------|---------------------:|:-------------------|
| hybrid_ease |              +0.0010 | +0.0003 to +0.0017 |
| mostpopular |              -0.2384 | -0.2444 to -0.2326 |

## Holdout 75/25 (visible/hidden)

|                     |      ease |   hybrid_ease |   mostpopular |
|:--------------------|----------:|--------------:|--------------:|
| players             | 8411.0000 |     8411.0000 |     8411.0000 |
| picks per player    |   10.0000 |       10.0000 |       10.0000 |
| owned picks %       |    0.0000 |        0.0000 |        0.0000 |
| not recommendable % |    0.0000 |        0.0000 |        0.0000 |
| NDCG@10             |    0.2799 |        0.2807 |        0.0426 |
| HitRate@10          |    0.6526 |        0.6539 |        0.2298 |
| HitRate@10 (any)    |    0.7785 |        0.7795 |        0.3871 |
| Coverage@10         |    0.0249 |        0.0255 |        0.0003 |
| Popularity pct      |   99.7106 |       99.7014 |       99.9961 |
| Tag distance        |    0.5040 |        0.5030 |        0.5820 |
| Playtime gap        |    0.5375 |        0.5348 |        0.7460 |
| Within 2x %         |   35.6809 |       35.8472 |       21.6371 |
| Playtime known %    |   96.4439 |       96.3215 |      100.0000 |
| Playtime gap (avg)  |    0.5644 |        0.5623 |        0.7919 |
| Within 2x (avg) %   |   32.4782 |       32.7034 |       20.5671 |
| Regret %            |   19.7758 |       19.9360 |       10.7602 |
| Flag: negative %    |    0.1272 |        0.1260 |        0.0000 |
| Flag: short %       |    8.1049 |        8.2808 |        0.0000 |
| Flag: like quit %   |   28.0311 |       28.2297 |       17.8124 |
| Any flag %          |   31.9344 |       32.2387 |       17.8124 |
| 2+ flags %          |    4.3217 |        4.3907 |        0.0000 |

| model       |   NDCG@10 minus ease | 95% CI             |
|:------------|---------------------:|:-------------------|
| hybrid_ease |              +0.0008 | +0.0002 to +0.0013 |
| mostpopular |              -0.2373 | -0.2427 to -0.2318 |

## Holdout 50/50 (visible/hidden)

|                     |      ease |   hybrid_ease |   mostpopular |
|:--------------------|----------:|--------------:|--------------:|
| players             | 8020.0000 |     8020.0000 |     8020.0000 |
| picks per player    |   10.0000 |       10.0000 |       10.0000 |
| owned picks %       |    0.0000 |        0.0000 |        0.0000 |
| not recommendable % |    0.0000 |        0.0000 |        0.0000 |
| NDCG@10             |    0.3164 |        0.3166 |        0.0585 |
| HitRate@10          |    0.7643 |        0.7636 |        0.3638 |
| HitRate@10 (any)    |    0.8731 |        0.8722 |        0.5843 |
| Coverage@10         |    0.0253 |        0.0258 |        0.0002 |
| Popularity pct      |   99.6857 |       99.6776 |       99.9963 |
| Tag distance        |    0.5120 |        0.5108 |        0.5906 |
| Playtime gap        |    0.5504 |        0.5476 |        0.7860 |
| Within 2x %         |   35.3626 |       35.5509 |       20.1496 |
| Playtime known %    |   96.1608 |       96.0549 |      100.0000 |
| Playtime gap (avg)  |    0.5969 |        0.5948 |        0.8460 |
| Within 2x (avg) %   |   30.9345 |       31.0894 |       18.9102 |
| Regret %            |   19.0034 |       19.1167 |        9.8567 |
| Flag: negative %    |    0.1259 |        0.1259 |        0.0000 |
| Flag: short %       |    8.4426 |        8.6322 |        0.0000 |
| Flag: like quit %   |   29.7057 |       29.8541 |       19.6733 |
| Any flag %          |   33.8017 |       34.0661 |       19.6733 |
| 2+ flags %          |    4.4688 |        4.5424 |        0.0000 |

| model       |   NDCG@10 minus ease | 95% CI             |
|:------------|---------------------:|:-------------------|
| hybrid_ease |              +0.0002 | -0.0003 to +0.0007 |
| mostpopular |              -0.2579 | -0.2635 to -0.2527 |
