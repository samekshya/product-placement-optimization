# Verified figures before and after the category remap

Baseline: `reports/numbers_before_remap.json` (captured 2026-08-17T20:19:54, 263 of 263 passing). After: `reports/numbers_after_remap_raw.json` (captured 2026-08-17T21:14:59, verifier 188 of 263 passing against the pre-remap constants).

Remap: `reports/CATEGORY_REMAP_SPEC.md`, implemented by `analysis/category_remap.py`, applied in notebook 02 Step 7b. 638 products moved, two categories renamed, 5,680 products and 25 categories unchanged.

## Summary

| group | figures | changed | unchanged |
|---|---:|---:|---:|
| CONSTANT | 42 | 8 | 34 |
| LIVE | 21 | 1 | 20 |
| ARTIFACT | 16 | 10 | 6 |
| FORECAST | 81 | 0 | 81 |
| FEATURES | 61 | 37 | 24 |
| OPTIMISER | 42 | 27 | 15 |
| **all checkable** | **263** | **83** | **180** |
| not auto-checkable | 6 | 3 + 2 open | 1 |

Changed figures are listed first within each group. `after` for CONSTANT rows is taken from the notebook or artifact that produces the figure, not from the verifier's actual, because the verifier compares the constant against a literal of itself and would report every constant as unchanged. The source is in the note.

## CONSTANT  (8 changed of 42)

| figure | before | after | changed | note |
|---|---:|---:|:---:|---|
| Silhouette increase (absolute) | 0.364 | 0.303 | **yes** | nb06: 0.493 - 0.19 |
| Classifier accuracy | 0.613 | 0.614 | **yes** | nb11 printed 61.4% (0.6138) |
| Neural network accuracy | 0.6905 | 0.6917 | **yes** | nb12 printed 69.17% |
| Fully grown tree accuracy | 0.6785 | 0.6767 | **yes** | nb12 printed 67.67% |
| Fully grown tree leaves | 10,231 | 11,906 | **yes** | nb12 printed 11,906 leaves |
| MLP model family advantage (points) | 1.2 | 1.5 | **yes** | (0.6917 - 0.6767) x 100 |
| Feature ceiling | 0.7167 | 0.7234 | **yes** | nb12 printed 72.34% |
| Distinct feature patterns | 17,532 | 21,032 | **yes** | nb12 printed 21,032 |
| Raw rows | 768,222 | 768,222 | no | constant, no dependency on category |
| Days of data (span) | 307 | 307 | no | constant, no dependency on category |
| Products raw audit count | 5,681 | 5,681 | no | constant, no dependency on category |
| Frequency silhouette | 0.19 | 0.19 | no | nb06 printed 0.1942, rounds to 0.19 |
| Recommender hit rate | 0.28 | 0.28 | no | nb09 printed 28.0%, product-level, category-independent |
| Recommender training baskets | 95,570 | 95,570 | no | nb09 printed 95,570 |
| Recommender test baskets | 40,959 | 40,959 | no | nb09 printed 40,959 / 19,808 |
| Linear Regression MAE | 3,395,703 | 3,395,703 | no | nb10 printed 3,395,703, revenue by month, category-independent |
| Prophet MAE | 2,909,633 | 2,909,633 | no | nb10 printed 2,909,633 |
| Prophet improvement pct | 14.3 | 14.3 | no | nb10 printed 14.3% |
| Prophet actually beats Linear Regression | 1 | 1 | no | constant, no dependency on category |
| Linear Regression R squared | -2.377 | -2.377 | no | nb10 printed -2.377 |
| Classifier baseline | 0.497 | 0.497 | no | nb11 printed 49.7% |
| Classifier test baskets | 65,412 | 65,412 | no | nb11 printed 65,412 |
| Classifier beats baseline | 1 | 1 | no | constant, no dependency on category |
| Neural network parameters | 3,843 | 3,843 | no | nb12 printed 3,843 |
| No model exceeds the ceiling | 1 | 1 | no | 0.6917 < 0.7234 |
| Recommender test baskets | 19,808 | 19,808 | no | nb09 printed 40,959 / 19,808 |
| Model hit rate | 28.04 | 28.04 | no | no producing code: constant 'measured 2026-08-14', nb09 does not compute it; nb09 is product-level and its hit rate, split and 19,808 test baskets reproduce exactly, so treated as unchanged |
| Popularity, matched budget | 23.74 | 23.74 | no | no producing code: constant 'measured 2026-08-14', nb09 does not compute it; nb09 is product-level and its hit rate, split and 19,808 test baskets reproduce exactly, so treated as unchanged |
| Popularity, unconstrained top 5 | 34.81 | 34.81 | no | no producing code: constant 'measured 2026-08-14', nb09 does not compute it; nb09 is product-level and its hit rate, split and 19,808 test baskets reproduce exactly, so treated as unchanged |
| Random, matched budget | 2.51 | 2.51 | no | no producing code: constant 'measured 2026-08-14', nb09 does not compute it; nb09 is product-level and its hit rate, split and 19,808 test baskets reproduce exactly, so treated as unchanged |
| Random, unconstrained top 5 | 5.09 | 5.09 | no | no producing code: constant 'measured 2026-08-14', nb09 does not compute it; nb09 is product-level and its hit rate, split and 19,808 test baskets reproduce exactly, so treated as unchanged |
| Avg recommendations per basket | 2.5 | 2.5 | no | no producing code: constant 'measured 2026-08-14', nb09 does not compute it; nb09 is product-level and its hit rate, split and 19,808 test baskets reproduce exactly, so treated as unchanged |
| Avg recommendations when covered | 3.96 | 3.96 | no | no producing code: constant 'measured 2026-08-14', nb09 does not compute it; nb09 is product-level and its hit rate, split and 19,808 test baskets reproduce exactly, so treated as unchanged |
| Products with at least one rule | 28 | 28 | no | no producing code: constant 'measured 2026-08-14', nb09 does not compute it; nb09 is product-level and its hit rate, split and 19,808 test baskets reproduce exactly, so treated as unchanged |
| Covered baskets | 12,536 | 12,536 | no | no producing code: constant 'measured 2026-08-14', nb09 does not compute it; nb09 is product-level and its hit rate, split and 19,808 test baskets reproduce exactly, so treated as unchanged |
| Uncovered baskets | 7,272 | 7,272 | no | no producing code: constant 'measured 2026-08-14', nb09 does not compute it; nb09 is product-level and its hit rate, split and 19,808 test baskets reproduce exactly, so treated as unchanged |
| Covered plus uncovered equals test baskets | 19,808 | 19,808 | no | no producing code: constant 'measured 2026-08-14', nb09 does not compute it; nb09 is product-level and its hit rate, split and 19,808 test baskets reproduce exactly, so treated as unchanged |
| Model where covered | 44.3 | 44.3 | no | no producing code: constant 'measured 2026-08-14', nb09 does not compute it; nb09 is product-level and its hit rate, split and 19,808 test baskets reproduce exactly, so treated as unchanged |
| Popularity where covered | 37.52 | 37.52 | no | no producing code: constant 'measured 2026-08-14', nb09 does not compute it; nb09 is product-level and its hit rate, split and 19,808 test baskets reproduce exactly, so treated as unchanged |
| Model beats popularity at matched budget | 1 | 1 | no | no producing code: constant 'measured 2026-08-14', nb09 does not compute it; nb09 is product-level and its hit rate, split and 19,808 test baskets reproduce exactly, so treated as unchanged |
| Model loses to unconstrained popularity | 1 | 1 | no | no producing code: constant 'measured 2026-08-14', nb09 does not compute it; nb09 is product-level and its hit rate, split and 19,808 test baskets reproduce exactly, so treated as unchanged |
| Model beats popularity where it has coverage | 1 | 1 | no | no producing code: constant 'measured 2026-08-14', nb09 does not compute it; nb09 is product-level and its hit rate, split and 19,808 test baskets reproduce exactly, so treated as unchanged |

## LIVE  (1 changed of 21)

| figure | before | after | changed | note |
|---|---:|---:|:---:|---|
| Zone 1 share of revenue | 40.64 | 37.41 | **yes** | verifier actual, after remap |
| Cleaned rows / line items | 767,180 | 767,180 | no | verifier actual, after remap |
| Transactions | 218,037 | 218,037 | no | verifier actual, after remap |
| Total revenue | 218,214,456.88 | 218,214,456.88 | no | verifier actual, after remap |
| Products with sales | 5,680 | 5,680 | no | verifier actual, after remap |
| Categories | 25 | 25 | no | verifier actual, after remap |
| Mean basket | 1,000.81 | 1,000.81 | no | verifier actual, after remap |
| Median basket | 500 | 500 | no | verifier actual, after remap |
| Warehouse trading days | 304 | 304 | no | verifier actual, after remap |
| Items per basket (mean) | 3.52 | 3.52 | no | verifier actual, after remap |
| Daily revenue | 710,796.28 | 710,796.28 | no | verifier actual, after remap |
| Daily customers | 710 | 710 | no | verifier actual, after remap |
| Large baskets share of trips | 13.7 | 13.7 | no | verifier actual, after remap |
| Large baskets share of revenue | 52.1 | 52.1 | no | verifier actual, after remap |
| Busiest day | Friday | Friday | no | verifier actual, after remap |
| Friday revenue (Rs M) | 32.8 | 32.8 | no | verifier actual, after remap |
| Peak month | 2025-09 | 2025-09 | no | verifier actual, after remap |
| Peak month revenue (Rs M) | 23.3 | 23.3 | no | verifier actual, after remap |
| Zone 1 category count | 5 | 5 | no | verifier actual, after remap |
| Daily series days match warehouse | 304 | 304 | no | verifier actual, after remap |
| Daily series revenue matches warehouse (max abs diff) | 0 | 0 | no | verifier actual, after remap |

## ARTIFACT  (10 changed of 16)

| figure | before | after | changed | note |
|---|---:|---:|:---:|---|
| Association rules | 1,228 | 1,320 | **yes** | verifier actual, after remap |
| Rules with lift above 5 | 48 | 62 | **yes** | verifier actual, after remap |
| Strong rules (lift >= 3) | 360 | 368 | **yes** | verifier actual, after remap |
| Max category lift | 6.81 | 7.44 | **yes** | verifier actual, after remap |
| Co-occurrence silhouette | 0.554 | 0.493 | **yes** | verifier actual, after remap |
| Cross-sell captured, current | 28 | 22 | **yes** | verifier actual, after remap |
| Cross-sell captured, optimised | 56 | 16 | **yes** | verifier actual, after remap |
| Cross-sell capture pct, current | 8.2 | 5.7 | **yes** | verifier actual, after remap |
| Cross-sell capture pct, optimised | 16.3 | 5.7 | **yes** | verifier actual, after remap |
| Cross-sell improvement (x) | 2 | 0.7 | **yes** | verifier actual, after remap |
| Max product lift | 22.41 | 22.41 | no | verifier actual, after remap |
| Top product pair count | 3,989 | 3,989 | no | verifier actual, after remap |
| Top product pair identity | Kalo Dal + Rato Dal | Kalo Dal + Rato Dal | no | verifier actual, after remap |
| Revenue projection at 5% (Rs Crore) | 1.3 | 1.3 | no | verifier actual, after remap |
| Class A products | 342 | 342 | no | verifier actual, after remap |
| Class A share of products | 6 | 6 | no | verifier actual, after remap |

## FORECAST  (0 changed of 81)

| figure | before | after | changed | note |
|---|---:|---:|:---:|---|
| Daily series trading days | 304 | 304 | no | verifier actual, after remap |
| Daily series total revenue | 218,214,456.85 | 218,214,456.85 | no | verifier actual, after remap |
| Daily mean revenue (304 days) | 717,810.71 | 717,810.71 | no | verifier actual, after remap |
| Daily series first date | 2025-07-17 | 2025-07-17 | no | verifier actual, after remap |
| Daily series last date | 2026-05-20 | 2026-05-20 | no | verifier actual, after remap |
| Chronological split, train days | 243 | 243 | no | verifier actual, after remap |
| Chronological split, test days | 61 | 61 | no | verifier actual, after remap |
| Training ends | 2026-03-20 | 2026-03-20 | no | verifier actual, after remap |
| Test starts | 2026-03-21 | 2026-03-21 | no | verifier actual, after remap |
| Test window mean revenue | 717,954.24 | 717,954.24 | no | verifier actual, after remap |
| Split in artifact, train days | 243 | 243 | no | verifier actual, after remap |
| Split in artifact, test days | 61 | 61 | no | verifier actual, after remap |
| Naive flat (last training day repeated), MAE (artifact) | 74,994 | 74,994 | no | verifier actual, after remap |
| Naive flat (last training day repeated), R2 (artifact) | -0 | -0 | no | verifier actual, after remap |
| Naive flat (last training day repeated), MAE (live refit) | 74,994 | 74,994 | no | verifier actual, after remap |
| Naive flat (last training day repeated), R2 (live refit) | -0 | -0 | no | verifier actual, after remap |
| Historical mean (training mean repeated), MAE (artifact) | 74,959 | 74,959 | no | verifier actual, after remap |
| Historical mean (training mean repeated), R2 (artifact) | -0 | -0 | no | verifier actual, after remap |
| Historical mean (training mean repeated), MAE (live refit) | 74,959 | 74,959 | no | verifier actual, after remap |
| Historical mean (training mean repeated), R2 (live refit) | -0 | -0 | no | verifier actual, after remap |
| Seasonal naive (last training week repeated), MAE (artifact) | 101,417 | 101,417 | no | verifier actual, after remap |
| Seasonal naive (last training week repeated), R2 (artifact) | -0.523 | -0.523 | no | verifier actual, after remap |
| Seasonal naive (last training week repeated), MAE (live refit) | 101,417 | 101,417 | no | verifier actual, after remap |
| Seasonal naive (last training week repeated), R2 (live refit) | -0.523 | -0.523 | no | verifier actual, after remap |
| Linear regression, day-of-week dummies, MAE (artifact) | 69,473 | 69,473 | no | verifier actual, after remap |
| Linear regression, day-of-week dummies, R2 (artifact) | -0.022 | -0.022 | no | verifier actual, after remap |
| Linear regression, day-of-week dummies, MAPE (artifact) | 11.37 | 11.37 | no | verifier actual, after remap |
| Linear regression, day-of-week dummies, MAE (live refit) | 69,473 | 69,473 | no | verifier actual, after remap |
| Linear regression, day-of-week dummies, R2 (live refit) | -0.022 | -0.022 | no | verifier actual, after remap |
| Linear regression, day-of-week plus trend, MAE (artifact) | 76,461 | 76,461 | no | verifier actual, after remap |
| Linear regression, day-of-week plus trend, R2 (artifact) | -0.078 | -0.078 | no | verifier actual, after remap |
| Linear regression, day-of-week plus trend, MAE (live refit) | 76,461 | 76,461 | no | verifier actual, after remap |
| Linear regression, day-of-week plus trend, R2 (live refit) | -0.078 | -0.078 | no | verifier actual, after remap |
| Prophet, weekly seasonality, MAE (artifact) | 75,114 | 75,114 | no | verifier actual, after remap |
| Prophet, weekly seasonality, R2 (artifact) | -0.063 | -0.063 | no | verifier actual, after remap |
| Prophet, weekly seasonality, MAPE (artifact) | 12.5 | 12.5 | no | verifier actual, after remap |
| Prophet, weekly seasonality, MAE (live refit) | 75,114 | 75,114 | no | verifier actual, after remap |
| Prophet, weekly seasonality, R2 (live refit) | -0.063 | -0.063 | no | verifier actual, after remap |
| Naive persistence (yesterday's value), MAE (artifact) | 119,611 | 119,611 | no | verifier actual, after remap |
| Naive persistence (yesterday's value), R2 (artifact) | -1.6 | -1.6 | no | verifier actual, after remap |
| Naive persistence (yesterday's value), MAPE (artifact) | 18.17 | 18.17 | no | verifier actual, after remap |
| Naive persistence (yesterday's value), MAE (live refit) | 119,611 | 119,611 | no | verifier actual, after remap |
| Naive persistence (yesterday's value), R2 (live refit) | -1.6 | -1.6 | no | verifier actual, after remap |
| Expanding mean (all days observed so far), MAE (artifact) | 75,074 | 75,074 | no | verifier actual, after remap |
| Expanding mean (all days observed so far), R2 (artifact) | -0.004 | -0.004 | no | verifier actual, after remap |
| Expanding mean (all days observed so far), MAE (live refit) | 75,074 | 75,074 | no | verifier actual, after remap |
| Expanding mean (all days observed so far), R2 (live refit) | -0.004 | -0.004 | no | verifier actual, after remap |
| Seasonal naive (same weekday last week), MAE (artifact) | 97,759 | 97,759 | no | verifier actual, after remap |
| Seasonal naive (same weekday last week), R2 (artifact) | -0.596 | -0.596 | no | verifier actual, after remap |
| Seasonal naive (same weekday last week), MAPE (artifact) | 15.24 | 15.24 | no | verifier actual, after remap |
| Seasonal naive (same weekday last week), MAE (live refit) | 97,759 | 97,759 | no | verifier actual, after remap |
| Seasonal naive (same weekday last week), R2 (live refit) | -0.596 | -0.596 | no | verifier actual, after remap |
| Linear regression, day-of-week, refit daily, MAE (artifact) | 69,794 | 69,794 | no | verifier actual, after remap |
| Linear regression, day-of-week, refit daily, R2 (artifact) | -0.015 | -0.015 | no | verifier actual, after remap |
| Linear regression, day-of-week, refit daily, MAPE (artifact) | 11.39 | 11.39 | no | verifier actual, after remap |
| Linear regression, day-of-week, refit daily, MAE (live refit) | 69,794 | 69,794 | no | verifier actual, after remap |
| Linear regression, day-of-week, refit daily, R2 (live refit) | -0.015 | -0.015 | no | verifier actual, after remap |
| Prophet, weekly seasonality, refit daily, MAE (artifact) | 73,423 | 73,423 | no | verifier actual, after remap |
| Prophet, weekly seasonality, refit daily, R2 (artifact) | -0.044 | -0.044 | no | verifier actual, after remap |
| Prophet, weekly seasonality, refit daily, MAPE (artifact) | 12.14 | 12.14 | no | verifier actual, after remap |
| Best model MAE reduction vs persistence (pct) | 41.6 | 41.6 | no | verifier actual, after remap |
| Best model MAE reduction vs seasonal naive (pct) | 28.6 | 28.6 | no | verifier actual, after remap |
| Best model MAE reduction vs historical mean (pct) | 7.3 | 7.3 | no | verifier actual, after remap |
| Best R2 of any fitted daily model | -0.015 | -0.015 | no | verifier actual, after remap |
| No daily model or baseline has positive R2 | 1 | 1 | no | verifier actual, after remap |
| Every model beats naive persistence on MAE | 1 | 1 | no | verifier actual, after remap |
| Prophet fitted peak inside Dashain window | 0 | 0 | no | verifier actual, after remap |
| Prophet fitted peak day | 2026-03-18 | 2026-03-18 | no | verifier actual, after remap |
| Actual peak day | 2025-10-01 | 2025-10-01 | no | verifier actual, after remap |
| Actual Dashain window mean | 988,038 | 988,038 | no | verifier actual, after remap |
| Prophet fitted Dashain window mean | 716,206 | 716,206 | no | verifier actual, after remap |
| Flexible-trend Prophet peaks in Dashain window | 1 | 1 | no | verifier actual, after remap |
| Flexible-trend Prophet MAE | 102,647 | 102,647 | no | verifier actual, after remap |
| Flexible-trend Prophet R2 | -0.521 | -0.521 | no | verifier actual, after remap |
| Flexible trend forecasts worse than default | 1 | 1 | no | verifier actual, after remap |
| Highest mean-revenue weekday | Wednesday | Wednesday | no | verifier actual, after remap |
| Highest total-revenue weekday | Friday | Friday | no | verifier actual, after remap |
| Lowest mean-revenue weekday | Saturday | Saturday | no | verifier actual, after remap |
| Friday total revenue (Rs) | 32,803,986 | 32,803,986 | no | verifier actual, after remap |
| New Year days share of LR SSE (pct) | 51.2 | 51.2 | no | verifier actual, after remap |
| LR MAE excluding New Year days | 56,873 | 56,873 | no | verifier actual, after remap |

## FEATURES  (37 changed of 61)

| figure | before | after | changed | note |
|---|---:|---:|:---:|---|
| Binary flags: tree depth 5 accuracy (nb11 figure) | 0.613 | 0.614 | **yes** | verifier actual, after remap |
| Binary flags: MLP accuracy (nb12 figure) | 0.6905 | 0.6917 | **yes** | verifier actual, after remap |
| Binary flags: ceiling (nb12 figure) | 0.7167 | 0.7234 | **yes** | verifier actual, after remap |
| Binary flags: distinct patterns (nb12 figure) | 17,532 | 21,032 | **yes** | verifier actual, after remap |
| Binary flags: tree top importance (nb11 figure) | 0.28 | 0.278 | **yes** | verifier actual, after remap |
| Ceiling, binary features | 0.7167 | 0.7234 | **yes** | verifier actual, after remap |
| Distinct patterns, binary features | 17,532 | 21,032 | **yes** | verifier actual, after remap |
| Singleton basket share, binary features (pct) | 5.1 | 6.3 | **yes** | verifier actual, after remap |
| Ceiling, discrete features | 0.8462 | 0.8548 | **yes** | verifier actual, after remap |
| Distinct patterns, discrete features | 90,048 | 95,521 | **yes** | verifier actual, after remap |
| Singleton basket share, discrete features (pct) | 32.9 | 35.3 | **yes** | verifier actual, after remap |
| Ceiling, full features | 0.9127 | 0.9187 | **yes** | verifier actual, after remap |
| Distinct patterns, full features | 122,891 | 126,437 | **yes** | verifier actual, after remap |
| Singleton basket share, full features (pct) | 49.1 | 50.8 | **yes** | verifier actual, after remap |
| Pattern lookup out of sample, binary | 0.6444 | 0.6368 | **yes** | verifier actual, after remap |
| Pattern lookup out of sample, full | 0.5163 | 0.5166 | **yes** | verifier actual, after remap |
| Test baskets with unseen pattern, full (pct) | 51.5 | 53.2 | **yes** | verifier actual, after remap |
| Ceiling gain, binary to full (points) | 19.6 | 19.53 | **yes** | verifier actual, after remap |
| Accuracy, binary_tree_depth5 | 0.613 | 0.6138 | **yes** | verifier actual, after remap |
| Accuracy, binary_mlp | 0.6905 | 0.6917 | **yes** | verifier actual, after remap |
| Accuracy, discrete_tree_depth5 | 0.7059 | 0.7053 | **yes** | verifier actual, after remap |
| Accuracy, discrete_mlp | 0.7252 | 0.7236 | **yes** | verifier actual, after remap |
| Accuracy, full_tree_depth5 | 0.7198 | 0.7228 | **yes** | verifier actual, after remap |
| Accuracy, full_mlp | 0.7575 | 0.7587 | **yes** | verifier actual, after remap |
| Share of ceiling, binary_tree_depth5 (pct) | 85.5 | 84.9 | **yes** | verifier actual, after remap |
| Share of ceiling, binary_mlp (pct) | 96.3 | 95.6 | **yes** | verifier actual, after remap |
| Share of ceiling, full_tree_depth5 (pct) | 78.9 | 78.7 | **yes** | verifier actual, after remap |
| Share of ceiling, full_mlp (pct) | 83 | 82.6 | **yes** | verifier actual, after remap |
| Tree gain, binary to full (points) | 10.68 | 10.9 | **yes** | verifier actual, after remap |
| MLP gain, binary to full (points) | 6.7 | 6.71 | **yes** | verifier actual, after remap |
| New tree top importance | 0.735 | 0.73 | **yes** | verifier actual, after remap |
| New tree second importance | 0.147 | 0.141 | **yes** | verifier actual, after remap |
| RICE importance on new tree | 0.147 | 0.141 | **yes** | verifier actual, after remap |
| New MLP recall, Medium | 0.664 | 0.661 | **yes** | verifier actual, after remap |
| New MLP recall, Large | 0.551 | 0.56 | **yes** | verifier actual, after remap |
| New tree recall, Medium | 0.554 | 0.558 | **yes** | verifier actual, after remap |
| New tree recall, Large | 0.524 | 0.517 | **yes** | verifier actual, after remap |
| Split, training baskets | 152,625 | 152,625 | no | verifier actual, after remap |
| Split, test baskets | 65,412 | 65,412 | no | verifier actual, after remap |
| Split seed | 42 | 42 | no | verifier actual, after remap |
| Majority baseline | 0.497 | 0.497 | no | verifier actual, after remap |
| Small baskets | 108,349 | 108,349 | no | verifier actual, after remap |
| Large baskets | 29,820 | 29,820 | no | verifier actual, after remap |
| Hour of day available | 0 | 0 | no | verifier actual, after remap |
| Binary flags: MLP parameters (nb12 figure) | 3,843 | 3,843 | no | verifier actual, after remap |
| Binary flags: tree top feature (nb11 figure) | COOKING OIL | COOKING OIL | no | verifier actual, after remap |
| Full feature count | 45 | 45 | no | verifier actual, after remap |
| Discrete feature count | 45 | 45 | no | verifier actual, after remap |
| MLP parameters, full features | 5,123 | 5,123 | no | verifier actual, after remap |
| Tree leaves, full features (depth 5) | 32 | 32 | no | verifier actual, after remap |
| New MLP beats old MLP | 1 | 1 | no | verifier actual, after remap |
| New tree beats old tree | 1 | 1 | no | verifier actual, after remap |
| New MLP still below its ceiling | 1 | 1 | no | verifier actual, after remap |
| Ceiling rose more than either model | 1 | 1 | no | verifier actual, after remap |
| New tree top feature | n_items | n_items | no | verifier actual, after remap |
| New tree second feature | RICE qty | RICE qty | no | verifier actual, after remap |
| COOKING OIL rank on new tree | 5 | 5 | no | verifier actual, after remap |
| COOKING OIL importance on new tree | 0.01 | 0.01 | no | verifier actual, after remap |
| RICE rank on new tree | 2 | 2 | no | verifier actual, after remap |
| COOKING OIL and RICE displaced from the top | 1 | 1 | no | verifier actual, after remap |
| Features used by the new tree | 8 | 8 | no | verifier actual, after remap |

## OPTIMISER  (27 changed of 42)

| figure | before | after | changed | note |
|---|---:|---:|:---:|---|
| Rule-bearing categories | 12 | 14 | **yes** | verifier actual, after remap |
| Hand-built layout in optimiser artifact | 56 | 16 | **yes** | verifier actual, after remap |
| Unconstrained optimum, rules (artifact) | 360 | 368 | **yes** | verifier actual, after remap |
| Unconstrained optimum, support (artifact) | 4.986 | 4.9157 | **yes** | verifier actual, after remap |
| Unconstrained optimum, rules (live certificate) | 360 | 368 | **yes** | verifier actual, after remap |
| Unconstrained optimum, support (live certificate) | 4.986 | 4.9157 | **yes** | verifier actual, after remap |
| Constrained optimum, rules (artifact) | 360 | 368 | **yes** | verifier actual, after remap |
| Constrained optimum, support (artifact) | 4.986 | 4.9157 | **yes** | verifier actual, after remap |
| Constrained optimum, rules (live certificate) | 360 | 368 | **yes** | verifier actual, after remap |
| Constrained optimum, support (live certificate) | 4.986 | 4.9157 | **yes** | verifier actual, after remap |
| Capacity-matched optimum, rules (artifact) | 250 | 286 | **yes** | verifier actual, after remap |
| Capacity-matched optimum, support (artifact) | 3.5599 | 3.9878 | **yes** | verifier actual, after remap |
| Capacity-matched optimum, capture pct (artifact) | 71.4 | 81.1 | **yes** | verifier actual, after remap |
| Capacity-matched optimum, rules (live certificate) | 250 | 286 | **yes** | verifier actual, after remap |
| Capacity-matched optimum, support (live certificate) | 3.5599 | 3.9878 | **yes** | verifier actual, after remap |
| Capacity-matched constrained optimum, rules (artifact) | 250 | 286 | **yes** | verifier actual, after remap |
| Capacity-matched constrained optimum, support (artifact) | 3.5599 | 3.9878 | **yes** | verifier actual, after remap |
| Capacity-matched constrained optimum, capture pct (artifact) | 71.4 | 81.1 | **yes** | verifier actual, after remap |
| Capacity-matched constrained optimum, rules (live certificate) | 250 | 286 | **yes** | verifier actual, after remap |
| Capacity-matched constrained optimum, support (live certificate) | 3.5599 | 3.9878 | **yes** | verifier actual, after remap |
| Constrained categories in strong rules | 0 | 1 | **yes** | verifier actual, after remap |
| Unconstrained gain over hand-built (rules) | 304 | 352 | **yes** | verifier actual, after remap |
| Capacity-matched gain over hand-built (rules) | 194 | 270 | **yes** | verifier actual, after remap |
| Hand-built share of capacity optimum (pct) | 22.8 | 7.1 | **yes** | verifier actual, after remap |
| First move gain (rules) | 100 | 70 | **yes** | verifier actual, after remap |
| Second move gain (rules) | 94 | 110 | **yes** | verifier actual, after remap |
| Two moves reach the capacity optimum | 250 | 196 | **yes** | verifier actual, after remap |
| Optimiser restarts | 200 | 200 | no | verifier actual, after remap |
| Optimiser restarts at least 100 | 1 | 1 | no | verifier actual, after remap |
| Optimiser master seed | 42 | 42 | no | verifier actual, after remap |
| Unconstrained optimum, capture pct (artifact) | 100 | 100 | no | verifier actual, after remap |
| Unconstrained optimum, search certified exact | 1 | 1 | no | verifier actual, after remap |
| Constrained optimum, capture pct (artifact) | 100 | 100 | no | verifier actual, after remap |
| Constrained optimum, search certified exact | 1 | 1 | no | verifier actual, after remap |
| Capacity-matched optimum, search certified exact | 1 | 1 | no | verifier actual, after remap |
| Capacity-matched constrained optimum, search certified exact | 1 | 1 | no | verifier actual, after remap |
| Constraint cost, rules (unlimited_zones) | 0 | 0 | no | verifier actual, after remap |
| Constraint cost, support (unlimited_zones) | 0 | 0 | no | verifier actual, after remap |
| Constraint cost, rules (capacity_matched) | 0 | 0 | no | verifier actual, after remap |
| Constraint cost, support (capacity_matched) | 0 | 0 | no | verifier actual, after remap |
| First move from hand-built | CANNED AND PACKAGED FOODS | CANNED AND PACKAGED FOODS | no | verifier actual, after remap |
| Second move from hand-built | PERSONAL CARE | PERSONAL CARE | no | verifier actual, after remap |

## Not auto-checkable  (6)

| figure | before | after | changed | note |
|---|---:|---:|:---:|---|
| Frequent itemsets (243, both algorithms) | 243 | 261 | **yes** | nb05 and nb08 both print 261; Apriori and FP-Growth identical |
| Network connections (38 unique) | 38 | 44 | **yes** | nb05 chart 10: 25 nodes, 44 edges |
| Rule temporal stability (median 1.011) | 1.011 | NOT COMPUTABLE | open | no notebook or module contains the step; constant has no producing code |
| Top classifier feature (COOKING OIL 0.280) | COOKING OIL 0.280 | COOKING OIL 0.278 | **yes** | nb11: COOKING OIL 0.2783, RICE 0.2118 |
| Warehouse quality checks (32 of 32) | 32 of 32 | 32 of 32 | no | Airflow run manual__2026-08-17T15:16:36, all pass |
| Reproduction checks (12 of 12) | 12 of 12 | pending STEP H | open | reproduce_all_results.py not yet re-run at the time of this table |

## Notes on provenance gaps found during this run

- **Rule temporal stability median 1.011**: `config/metrics.py` and PROJECT_RECORD.md attribute it to 'notebook 05 Step 9'. No notebook or module contains that step (searched for `stabil`, `temporal`, `141,111`, `76,926`, `opportunity_rank`, `associated_basket_revenue`: zero hits, working copy and HEAD). It cannot be recomputed and is not restated as an after value.
- **Recommender baselines** (popularity, random, coverage: 13 constants): no producing code. Notebook 09 prints the split, 19,808 tested baskets and the 28.0% hit rate, all reproduced exactly, but not the baselines. Treated as unchanged because the recommender is product-level and category-independent.
- **Constrained categories in strong rules**: was 0, now 1 (DAIRY PRODUCTS). The verifier asserts this as a literal 0, which encodes the claim that no locked cold-storage category appears in any strong rule. That claim no longer holds.

## Addendum: five zones re-derived, 17 August 2026

After this table was written the five placement zones were re-derived from the
post-remap rules, because section 23.3 states they are derived from the
association rules and the stale hand-built layout had stopped beating its own
baseline. `analysis/optimise_zones.py`, capacity-matched, certified exact, under
three hard constraints: DAIRY PRODUCTS and FROZEN FOODS locked to zone 4
(refrigeration); ALCOHOLIC BEVERAGES, CIGARETTE AND TOBACCO locked to zone 5
(section 13.5 ethics); RICE locked to zone 5 (heavy goods handling).

| figure | pre-remap | post-remap, stale zones | post-re-derivation |
|---|---:|---:|---:|
| Proposed layout, rules captured | 56 | 16 | **180** |
| Proposed layout, support captured | 0.8130 | 0.2814 | **2.6614** |
| Proposed layout, capture rate | 16.3% | 5.7% | **54.1%** |
| Existing frequency layout | 28 / 8.2% | 22 / 5.7% | 22 / 5.7% |
| Proposed vs existing | 2.0x | 0.7x | **8.2x** |
| Capacity-matched ceiling, no locks | 250 | 286 | 286 |
| Constraint cost, unlimited zone sizes | 0 rules | 0 rules | **2 rules** |
| Constraint cost, capacity-matched | 0 rules | 0 rules | **106 rules** |
| Zone 1 categories / revenue share | 5 / 40.6% | 5 / 37.4% | **6 / 48.5%** |

Zone sizes are 6 / 5 / 3 / 4 / 7. The capacity multiset is unchanged from
5 / 6 / 3 / 4 / 7, so the metric still cannot be gamed by pooling categories,
but the centre holds six rather than five: the anchor cluster the rules identify
is six categories, and with three categories locked into zone 5 the centre was
the only position able to hold it.

**The measured price of the constraints is no longer zero.** It is 106 of 368
strong rules, 27.0 capture-rate points, and the cause is slot competition rather
than adjacency: ALCOHOLIC BEVERAGES, CIGARETTE AND TOBACCO and FROZEN FOODS
appear in no strong rule at all, but three locks in the 7-slot perimeter zone
leave four free slots there, so the largest anchor cluster that fits anywhere is
six rather than seven. This is the quantified cost of the section 13.5 ethical
decision and replaces the earlier claim that the constraints were free.
