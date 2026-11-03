# Cross-source findings (data profiles, 2026-10-28)

The per-source profiles are in this folder. [README.md](README.md) has the scorecard. Layer 1 label results are in [../../label/label_report.md](../../label/label_report.md).

## Sources profiled

| Source | Grain | Rows | Worst completeness | Main issue |
|---|---|---:|---|---|
| Kaggle games.csv | game | 50,872 | Green | `price_original = 0` is a missing-value code on 985 paid games |
| Kaggle games_metadata.json | game | 50,872 | Green | 20.4% empty descriptions (High) |
| Kaggle users.csv | user | 14.3M | Green | 125,242 users own 0 products yet have reviews (inconsistent) |
| Kaggle recommendations.csv | review | 41.2M | Green | Reviewers only, 86% positive; helpful/funny mostly 0 |
| Steam store appdetails (sample) | game | 300 | Red* | *Price nulls are structural (free or unreleased), not missing |
| Steam app catalog (IStoreService) | app | 264,125 | Green | Kaggle covers 38k of Steam's 197k games |
| Steam GetOwnedGames (your library) | owned game | 21 | Red* | *`rtime_last_played` is null for never-played games |
| IsThereAnyDeal (sample) | game | 277 | Orange | 13% have no all-time-low record |
| McAuley Australian users-items | owned game | not downloaded | n/a | The UCSD file host is unreachable from both this machine's shell and Chrome (2026-10-28). Retry later |
| Supabase public.games | game | pending | pending | Profiled once the index upload finishes |

## Findings that change the plan

1. **The collaborative model alone can't serve real users.**
   - In your own library, only **7 of 21** games appear in Kaggle's review data, and 11 of 21 appear in Kaggle's catalog at all.
   - Steam has **197,118 games**; Kaggle covers **38,379** of them.
   - So the content side (embeddings) and the weekly catalog refresh are required for "anyone with a Steam account", not optional.
2. **Item types are now free.**
   - Steam's app catalog labels every app. 7,955 of Kaggle's "games" (16%) are actually DLC.
   - This replaces the planned ~7 h IsThereAnyDeal backfill. `build_index.py` now fills `item_type` from it.
3. **The Layer 1 label agrees only weakly with reviews.**
   - All three variants reach kappa of about 0.20–0.21 ("fair").
   - The framework's default percentile cutoff of 0.5 scores **kappa 0.09**. The kappa-best cutoff is 0.1, where 89% of rows count as "enjoyed".
   - The reliability curve is monotone: share recommended rises from 66% in the lowest playtime decile to 91% in the highest. So playtime carries signal, but a single threshold is a blunt label.
   - Per the framework ("if kappa is weak, fix the label before tuning"), the label needs a decision before model tuning.
4. **Live input differs from training input.**
   - Steam reports **minutes** and includes never-played games: 5 of 21 in your library. Kaggle reports **hours** and only for reviewed games.
   - Convert units, and treat zero playtime as unknown.
5. **Kaggle prices are stale and partly miscoded.** Use live Steam and IsThereAnyDeal prices in the app. Kaggle prices are only good as rough priors.

## Recommended next analyses

1. **Fix the label:**
   - Test a two-sided label: "enjoyed" when g ≥ 0.1, "not enjoyed" when g < 0.1 or played under 30 min.
   - Test a per-user Beta mixture (DP2Rec) and compare kappa on the same report split.
2. **Coverage:** for a sample of public Steam profiles, measure the share of owned games the collaborative model knows vs only the content side. This sizes how much the content side carries.
3. **Recency drift:** the recommended share drops from 97% (2010) to about 82% (2017–18), then recovers. Check whether the label cutoff should vary by review year.
4. **Popularity skew:** `user_reviews` has skew 138. Report ARP and long-tail recall from the start of model evaluation, not as an afterthought.
5. **McAuley:** retry the download. If it stays unreachable, the Kaggle "Steam Video Games" dataset (200k purchase-and-play rows, includes never-played purchases) is a smaller substitute. It needs title-to-appid matching against the Steam catalog.
