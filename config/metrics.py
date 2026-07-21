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
"""

# ------------------------------------------------------------------
# Dataset scale (notebooks 01 and 02)
# ------------------------------------------------------------------
TOTAL_RAW_ROWS = 768222
TOTAL_CLEAN_ROWS = 767180
TOTAL_TRANSACTIONS = 218037
TOTAL_PRODUCTS = 5681
TOTAL_CATEGORIES = 25

# ------------------------------------------------------------------
# Revenue and baskets (notebook 03)
# ------------------------------------------------------------------
TOTAL_REVENUE = 218214456.88
MEAN_BASKET_VALUE = 1000.81
FRIDAY_REVENUE = 32803986        # busiest day by total revenue
WEDNESDAY_AVG_BASKET = 1031.33   # highest average basket day

# ------------------------------------------------------------------
# Time coverage
# ------------------------------------------------------------------
DATA_START = "2025-07-17"
DATA_END = "2026-05-20"
DATA_DAYS = 307                  # days of trading covered by the data
CALENDAR_MONTHS = 11             # July 2025 to May 2026 inclusive
PARTIAL_MONTH_NOTE = "July 2025 contains only 14 days from July 17"

# ------------------------------------------------------------------
# Association rules (notebooks 05 and 09)
# ------------------------------------------------------------------
RULES_TOTAL = 1228               # category-level rules (Apriori = FP-Growth)
RULES_SIGNIFICANT = 1226         # rules with chi-square p below 0.05
MAX_LIFT_CATEGORY = 6.81
MAX_LIFT_PRODUCT = 22.41
TOP_PAIR_COUNT = 3989            # Kalo Dal + Rato Dal co-occurrences

# ------------------------------------------------------------------
# Clustering (notebook 06)
# ------------------------------------------------------------------
SILHOUETTE_COOCCURRENCE = 0.554  # co-occurrence K-Means at k=3
SILHOUETTE_FREQUENCY = 0.19      # frequency K-Means at k=5
# Report the change as an absolute increase in the score, NOT a percentage:
# the silhouette scale is -1 to 1, so a percentage of a small base overstates it.
SILHOUETTE_INCREASE = round(SILHOUETTE_COOCCURRENCE - SILHOUETTE_FREQUENCY, 3)  # 0.364

# ------------------------------------------------------------------
# Placement simulation (notebook 07)
# ------------------------------------------------------------------
CROSS_SELL_CURRENT = 28          # strong rules co-located by current layout
CROSS_SELL_OPTIMISED = 56        # strong rules co-located by optimised layout
# The rupee uplift shown in notebook 07 and the dashboard is an INDUSTRY
# BENCHMARK SCENARIO (3 to 8 percent range, 5 percent midpoint), not a
# prediction or model output.
UPLIFT_SCENARIO_PCT = 5

# ------------------------------------------------------------------
# ML validation (notebook 09)
# ------------------------------------------------------------------
ML_TRAIN_BASKETS = 95570         # 70 percent training split
ML_TEST_BASKETS = 40959          # 30 percent held-out split
ML_HIT_RATE = 0.28               # top-5 hit rate on unseen test baskets

# ------------------------------------------------------------------
# Basket size classifier (notebook 11)
# ------------------------------------------------------------------
CLASSIFIER_ACCURACY = 0.613
CLASSIFIER_BASELINE = 0.497      # majority-class baseline (Small baskets)

# ------------------------------------------------------------------
# ABC analysis (notebook 03)
# ------------------------------------------------------------------
ABC_CLASS_A_PRODUCTS = 342
ABC_CLASS_A_REVENUE_PCT = 70.0
