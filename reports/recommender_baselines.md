# Product recommender against its baselines

Generated 2026-08-20T02:18:58 by `analysis/recommender_baselines.py`.

Notebook 09 reports a hit rate. A hit rate on its own cannot say whether the recommender
learned anything, because a system that always names the shop's best sellers also scores.
This compares the model against popularity and random on the same baskets, under the same
recommendation budget.

## Setup

Notebook 09's parameters, unchanged: top 100 products, 70/30 split at random_state=42, apriori at 0.5% support,
rules at lift >= 1.0, top 5 consequents by lift. Random baselines seeded at 42.

| | value |
|---|---:|
| training baskets | 95,570 |
| test baskets | 40,959 |
| product rules mined | 100 |
| products carrying at least one rule | 28 of 100 |
| multi-product test baskets scored | 19,808 |

## Hit rate against the baselines

| system | budget | hit rate |
|---|---|---:|
| **model (association rules)** | up to 5 per known product | **28.04%** |
| popularity | matched to the model | 23.74% |
| popularity | unconstrained top 5 | 34.81% |
| random | matched to the model | 2.55% |
| random | unconstrained top 5 | 5.04% |

## Coverage, which is what constrains the headline

The model can only answer when one of the basket's known products carries a mined rule.

| | value |
|---|---:|
| average recommendations per basket | 2.50 |
| average when the model can answer | 3.96 |
| covered baskets | 12,536 |
| uncovered baskets | 7,272 |
| **model hit rate where covered** | **44.30%** |
| popularity hit rate where covered | 37.52% |

## Reading this honestly

- At a matched budget the model beats popularity, 28.04% against 23.74%.
- Against an unconstrained popularity widget the model loses, 28.04% against 34.81%. Both are reported
  because the choice of budget rule changes the conclusion.
- Where the model has coverage it reaches 44.30% against popularity's 37.52%. Coverage, not ranking quality,
  is the binding limitation.

Notebook 09's recommender matches a rule when the queried product appears anywhere in the
antecedent set, without requiring the rule's other antecedents to be present in the basket.
That loose match is reproduced here deliberately, so this measures the recommender the
dissertation describes rather than a corrected one. It inflates coverage slightly.
