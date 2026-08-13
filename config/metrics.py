"""
Single source of truth for every verified project number.

All headline figures quoted in the notebooks, the dashboard and the report
live here as constants. If a number ever needs to change (for example after
re-running a notebook on refreshed data), change it HERE ONCE and every
consumer stays consistent.

Sources:
    Notebook 01/02  raw and clean row counts
    Notebook 03     revenue, baskets, ABC, day-of-week figures
    Notebook 05     category-level association rules and chi-square counts
    Notebook 06     clustering silhouette scores
    Notebook 07     cross-sell before/after capture counts
    Notebook 09     product-level rules and ML validation split
    Notebook 11     basket size classifier accuracy
    Notebook 12     neural network comparison

Reconstruction note (2026-08-13):
    This file was lost from disk at some point after 2026-07-18 and had never
    been committed, which left reproduce_all_results.py unable to import it.
    It has been rebuilt from three sources, not from memory:
      1. config/__pycache__/metrics.cpython-313.pyc, the compiled copy of the
         original, which preserved every constant name and literal value
      2. dashboard/artifacts/kpi_summary.json and cross_sell_summary.json
      3. the notebook outputs themselves
    Every value below was cross-checked against at least two of those.
"""

# ======================================================================
# Dataset scale (notebooks 01 and 02)
# ======================================================================

TOTAL_RAW_ROWS = 768222
TOTAL_CLEAN_ROWS = 767180
TOTAL_TRANSACTIONS = 218037

# 5,681 distinct products were counted in the raw audit. One of them was
# removed entirely during cleaning, so 5,680 products have sales in the
# cleaned data and in the warehouse. Both numbers are correct; they answer
# different questions. kpi_summary.json stores 5,680.
TOTAL_PRODUCTS = 5681
TOTAL_PRODUCTS_WITH_SALES = 5680

TOTAL_CATEGORIES = 25

# ======================================================================
# Revenue and baskets (notebook 03)
# ======================================================================

TOTAL_REVENUE = 218214456.88
MEAN_BASKET_VALUE = 1000.81
MEDIAN_BASKET_VALUE = 500.00

FRIDAY_REVENUE = 32803986        # highest revenue day
WEDNESDAY_AVG_BASKET = 1031.33   # highest average basket day

# ======================================================================
# Time coverage
# ======================================================================

DATA_START = '2025-07-17'
DATA_END = '2026-05-20'
DATA_DAYS = 307        # calendar span, inclusive
TRADING_DAYS = 304     # days that actually had sales (warehouse dim_date)
CALENDAR_MONTHS = 11
PARTIAL_MONTH_NOTE = 'July 2025 contains only 14 days from July 17'

# ======================================================================
# Association rules (notebooks 05 and 09)
# ======================================================================

RULES_TOTAL = 1228
RULES_SIGNIFICANT = 1226      # rules passing the chi-square test (notebook 05 Step 8)
RULES_LIFT_ABOVE_5 = 48
RULES_LIFT_ABOVE_3 = 360      # "strong" rules, the cross-sell threshold
FREQUENT_ITEMSETS = 243       # identical from Apriori and FP-Growth
NETWORK_CONNECTIONS = 38      # unique category-to-category edges, notebook 05 chart 10
MAX_LIFT_CATEGORY = 6.81
MAX_LIFT_PRODUCT = 22.41

# Kalo Dal + Rato Dal, the strongest product pair. This is a count of BASKETS
# containing both products. Notebook 09's heatmap originally reported 4,236 for
# this pair because it multiplied line counts instead of counting baskets; that
# was fixed by binarising the pivot. 3,989 is the correct figure and is the one
# used in notebook 03, the README and the dashboard.
TOP_PAIR_COUNT = 3989

ITEMS_PER_BASKET_MEAN = 3.51
RULE_STABILITY_MEDIAN = 1.011   # notebook 05 Step 9 temporal validation

# ======================================================================
# Clustering (notebook 06)
# ======================================================================

SILHOUETTE_COOCCURRENCE = 0.554
SILHOUETTE_FREQUENCY = 0.19

# Absolute improvement in silhouette from switching the clustering input from
# purchase frequency to co-occurrence: +0.364, from 0.190 to 0.554.
#
# Always quote this as an absolute increase. Silhouette is bounded on [-1, 1]
# and has no meaningful zero, so a percentage change between two silhouette
# scores has no interpretation. An earlier draft described this as a "189%
# improvement", which implies the clustering became nearly three times better.
# That framing was removed deliberately and should not be reintroduced.
SILHOUETTE_INCREASE = round(SILHOUETTE_COOCCURRENCE - SILHOUETTE_FREQUENCY, 3)

# ======================================================================
# Cross-sell before/after (notebook 07, RQ2 / Objective 4)
# ======================================================================

CROSS_SELL_CURRENT = 28      # strong rules co-located by the current layout
CROSS_SELL_OPTIMISED = 56    # strong rules co-located by the 5 designed zones

# The "current" layout in this study IS the frequency-based clustering
# baseline: cross_sell_summary.json labels it "Frequency-based clusters
# (unoptimised baseline)". CROSS_SELL_FREQUENCY is therefore the same 28-rule
# baseline under the name reproduce_all_results.py uses for it. It is kept as
# a separate constant so both checks in that script read clearly.
CROSS_SELL_FREQUENCY = 28

UPLIFT_SCENARIO_PCT = 5      # the primary (moderate) projection scenario

# ======================================================================
# ML validation (notebooks 09, 11 and 12)
# ======================================================================

ML_TRAIN_BASKETS = 95570
ML_TEST_BASKETS = 40959
ML_HIT_RATE = 0.28

CLASSIFIER_ACCURACY = 0.613   # Decision Tree, depth 5 (notebook 11)
CLASSIFIER_BASELINE = 0.497   # always predict the majority class
CLASSIFIER_TRAIN_BASKETS = 152625
CLASSIFIER_TEST_BASKETS = 65412
CLASSIFIER_TOP_FEATURE = 'COOKING OIL'
CLASSIFIER_TOP_FEATURE_IMPORTANCE = 0.280

# Notebook 12: same features, same split, neural network comparison
NEURAL_NET_ACCURACY = 0.6905
NEURAL_NET_PARAMETERS = 3843
DECISION_TREE_FULL_ACCURACY = 0.6785   # tree with no depth cap
DECISION_TREE_FULL_LEAVES = 10231
FEATURE_CEILING_ACCURACY = 0.7167      # best possible on these 25 binary features
DISTINCT_FEATURE_PATTERNS = 17532

# ======================================================================
# Demand forecasting (notebook 10)
# ======================================================================

LINREG_MAE = 3395703
LINREG_RMSE = 4700487
LINREG_R2 = -2.377          # negative and expected: 11 points, 3 in the test set
PROPHET_MAE = 2909633
PROPHET_RMSE = 3946262
PROPHET_IMPROVEMENT_PCT = 14.3   # MAE reduction versus Linear Regression

# ======================================================================
# ABC analysis (notebook 03, Chart 10)
# ======================================================================

ABC_CLASS_A_PRODUCTS = 342
ABC_CLASS_A_REVENUE_PCT = 70.0
