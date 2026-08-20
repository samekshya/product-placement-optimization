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

# ----------------------------------------------------------------------
# 2026-08-17: values below re-measured after the audited category remap
# (reports/CATEGORY_REMAP_SPEC.md, analysis/category_remap.py, notebook 02
# Step 7b). Before/after for every verified figure: reports/numbers_after_remap.md.
# Pre-remap values: reports/numbers_before_remap.json.
# ----------------------------------------------------------------------

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

RULES_TOTAL = 1320
RULES_SIGNIFICANT = 1318      # rules passing the chi-square test (notebook 05 Step 8)

# Rules still significant after Bonferroni correction for the 1,320
# simultaneous tests (threshold 0.05 / 1320 = 3.79e-05). Recorded output of
# notebook 05 Step 8: "Still significant after Bonferroni correction
# (p < 3.79e-05): 1,314 of 1,320".
RULES_BONFERRONI = 1314
RULES_LIFT_ABOVE_5 = 62
RULES_LIFT_ABOVE_3 = 368      # "strong" rules, the cross-sell threshold
FREQUENT_ITEMSETS = 261       # identical from Apriori and FP-Growth
NETWORK_CONNECTIONS = 44      # unique category-to-category edges, notebook 05 chart 10
MAX_LIFT_CATEGORY = 7.44
MAX_LIFT_PRODUCT = 22.41

# Kalo Dal + Rato Dal, the strongest product pair. This is a count of BASKETS
# containing both products. Notebook 09's heatmap originally reported 4,236 for
# this pair because it multiplied line counts instead of counting baskets; that
# was fixed by binarising the pivot. 3,989 is the correct figure and is the one
# used in notebook 03, the README and the dashboard.
TOP_PAIR_COUNT = 3989

ITEMS_PER_BASKET_MEAN = 3.51
# ----------------------------------------------------------------------
# Temporal validation (analysis/temporal_validation.py, measured 2026-08-17)
# ----------------------------------------------------------------------
#
# These replace a single unsourced constant, RULE_STABILITY_MEDIAN = 1.011,
# whose comment credited "notebook 05 Step 9". No such step existed in any
# notebook or module: the figure had no producing code. It does now.
#
#   python analysis/temporal_validation.py
#
# writes reports/temporal_validation.md and
# dashboard/artifacts/temporal_validation_summary.json.
#
# Rules are mined on the development window only, then each rule's lift is
# recomputed on the validation window it was not mined from:
#   stability = validation lift / development lift
# The two window basket counts reproduce the figures PROJECT_RECORD.md quoted in
# prose (141,111 and 76,926) exactly, so the original analysis was real even
# though its code was not kept. The median is 1.016 rather than the recorded
# 1.011, which is expected: the categories themselves changed in the 2026-08-17
# remap, so the rules are not the same rules.
RULE_STABILITY_DEV_BASKETS = 141111
RULE_STABILITY_VAL_BASKETS = 76926
RULE_STABILITY_DEV_RULES = 1276
RULE_STABILITY_MEDIAN = 1.016
RULE_STABILITY_MIN = 0.867
RULE_STABILITY_MAX = 1.156
RULE_STABILITY_MEAN = 1.018
RULE_STABILITY_BELOW_HALF = 0      # no rule more than halved in the second window
RULE_STABILITY_TOP20_STILL_STRONG = 20   # of 20, lift still >= 3.0 in validation
# Of the development rules at lift >= 3.0, how many are still >= 3.0 in
# validation. This one is NOT a clean sweep and should be reported as it is.
RULE_STABILITY_STRONG_RULES = 342
RULE_STABILITY_STRONG_STILL_STRONG = 334

# ======================================================================
# Clustering (notebook 06)
# ======================================================================

SILHOUETTE_COOCCURRENCE = 0.493
SILHOUETTE_FREQUENCY = 0.19

# Absolute improvement in silhouette from switching the clustering input from
# purchase frequency to co-occurrence: +0.303, from 0.190 to 0.493.
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

CROSS_SELL_CURRENT = 22      # strong rules co-located by the current layout
CROSS_SELL_OPTIMISED = 180   # strong rules co-located by the 5 re-derived zones

# The "current" layout in this study IS the frequency-based clustering
# baseline: cross_sell_summary.json labels it "Frequency-based clusters
# (unoptimised baseline)". CROSS_SELL_FREQUENCY is therefore the same 22-rule
# baseline under the name reproduce_all_results.py uses for it. It is kept as
# a separate constant so both checks in that script read clearly.
CROSS_SELL_FREQUENCY = 22

UPLIFT_SCENARIO_PCT = 5      # the primary (moderate) projection scenario

# ======================================================================
# ML validation (notebooks 09, 11 and 12)
# ======================================================================

ML_TRAIN_BASKETS = 95570
ML_TEST_BASKETS = 40959
ML_HIT_RATE = 0.28

CLASSIFIER_ACCURACY = 0.614   # Decision Tree, depth 5 (notebook 11)
CLASSIFIER_BASELINE = 0.497   # always predict the majority class
CLASSIFIER_TRAIN_BASKETS = 152625
CLASSIFIER_TEST_BASKETS = 65412
CLASSIFIER_TOP_FEATURE = 'COOKING OIL'
CLASSIFIER_TOP_FEATURE_IMPORTANCE = 0.278

# Notebook 12: same features, same split, neural network comparison
NEURAL_NET_ACCURACY = 0.6917
NEURAL_NET_PARAMETERS = 3843
DECISION_TREE_FULL_ACCURACY = 0.6767   # tree with no depth cap
DECISION_TREE_FULL_LEAVES = 11906
FEATURE_CEILING_ACCURACY = 0.7234      # best possible on these 25 binary features
DISTINCT_FEATURE_PATTERNS = 21032

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

# ======================================================================
# Recommender baselines (analysis/recommender_baselines.py, 2026-08-17)
# ======================================================================
#
# These were marked "notebook 09 evaluation, measured 2026-08-14" but notebook 09
# computes only two of them, the 19,808 test baskets and the 28.04 per cent hit
# rate. The baselines, the coverage split and the recommendation budget had no
# producing code. They are now computed by
#
#   python analysis/recommender_baselines.py
#
# which reproduces notebook 09's pipeline exactly and adds the baselines. It
# writes reports/recommender_baselines.md and
# dashboard/artifacts/recommender_baselines_summary.json.
#
# Eleven of the thirteen values below reproduced to the digit, which is why they
# are trusted: the original analysis was real, its code was simply not kept. The
# two random baselines moved slightly (2.51 -> 2.55, 5.09 -> 5.04) because a
# random baseline depends on the draw and the original seed was not recorded.
# The random draw is now seeded at 42 and reproducible.
#
# Nothing here moved in the category remap, and that is measured rather than
# assumed: the recommender works on product names among the top 100 products, so
# relabelling categories cannot reach it.
#
# All three systems were scored on the SAME 19,808 multi-product test baskets.
# "Matched budget" means each baseline received exactly as many recommendation
# slots as the model actually produced for that basket, so a baseline cannot win
# simply by guessing more often.
#
# Two popularity figures are recorded on purpose, because the choice of budget
# rule changes the conclusion and the thesis reports both:
#   matched budget      popularity gets 0 slots where the model has no rule
#   unconstrained top 5 popularity always recommends, as it would in deployment

REC_TEST_BASKETS = 19808
REC_MODEL_HIT_PCT = 28.04
REC_POPULARITY_MATCHED_PCT = 23.74
REC_POPULARITY_TOP5_PCT = 34.81
REC_RANDOM_MATCHED_PCT = 2.55
REC_RANDOM_TOP5_PCT = 5.04
REC_AVG_RECS_PER_BASKET = 2.50
REC_AVG_RECS_WHEN_COVERED = 3.96

# Coverage. The model can only answer a basket when one of its products has a
# mined rule, which is the binding limitation on the headline hit rate.
REC_PRODUCTS_WITH_RULES = 28
REC_COVERED_BASKETS = 12536
REC_UNCOVERED_BASKETS = 7272
REC_COVERED_MODEL_PCT = 44.30
REC_COVERED_POPULARITY_PCT = 37.52

# ======================================================================
# Layout reach (measured 2026-08-14 from the warehouse)
# ======================================================================
#
# Only 14 of the 25 categories appear in any strong rule (lift >= 3.0), so
# only baskets containing at least one of those 14 can be influenced by any
# zone arrangement this study proposes. Measured with:
#   baskets containing >= 1 strong-rule category / all 218,037 baskets
# and the revenue carried by the remaining baskets. The dashboard recomputes
# these live when the warehouse is running; these constants are the recorded
# fallback for a clone without a database.
LAYOUT_REACHABLE_BASKET_PCT = 89.80
LAYOUT_UNREACHABLE_BASKET_PCT = 10.20
LAYOUT_UNREACHABLE_REVENUE_PCT = 9.91

# ======================================================================
# Computed zone assignment (analysis/optimise_zones.py, measured 2026-08-15)
# ======================================================================
#
# Greedy local search with random restarts (200 restarts, master seed 42)
# over the SAME score_layout objective that produces CROSS_SELL_OPTIMISED,
# with every run certified against exhaustive enumeration. Reproduce with
#     python analysis/optimise_zones.py
# which writes dashboard/artifacts/zone_optimisation.json.
#
# Read these with two facts in mind. First, score_layout has no notion of
# shelf capacity, so with unlimited zone sizes the optimum is one zone
# holding all 14 rule-bearing categories, which captures every rule. That is
# a property of the metric, not a shelf plan, and it is reported as such.
# The capacity-matched figures hold every zone to its hand-built size
# (5/6/3/4/7) and are the buildable answer. Second, the study's constraints
# (dairy and frozen locked to the cold zone; alcohol, tobacco and rice locked
# to the perimeter) now cost 106 of the 368 strong rules, 27.0 capture-rate
# points, once zone capacities are held fixed. The price is slot competition,
# not adjacency: alcohol, tobacco and frozen foods appear in no strong rule at
# all, but three locks in the 7-slot perimeter zone leave only four free slots
# there, so the largest anchor cluster that fits anywhere is six rather than
# seven. Before the 2026-08-17 remap and re-derivation this price was zero. It
# is now the measured cost of the section 13.5 ethical decision.
ZONE_OPT_RESTARTS = 200
ZONE_OPT_SEED = 42
ZONE_OPT_RULE_BEARING_CATEGORIES = 14   # of 25; the other 13 cannot move the score

ZONE_OPT_UNCONSTRAINED_RULES = 368      # every strong rule, one mega-zone
ZONE_OPT_UNCONSTRAINED_SUPPORT = 4.9157
ZONE_OPT_UNCONSTRAINED_PCT = 100.0
ZONE_OPT_CONSTRAINED_RULES = 366        # identical: the constraints do not bind
ZONE_OPT_CONSTRAINED_SUPPORT = 4.8878
ZONE_OPT_CONSTRAINED_PCT = 99.4

# Zone sizes fixed to the hand-built 5/6/3/4/7. Same result with and without
# the physical and ethical constraints.
ZONE_OPT_CAPACITY_RULES = 180
ZONE_OPT_CAPACITY_SUPPORT = 2.6614
ZONE_OPT_CAPACITY_PCT = 54.1

# Unconstrained minus constrained, at either zone-size setting.
# The capacity-matched optimum WITHOUT the study's locks: the ceiling a layout
# could reach if refrigeration, ethics and handling imposed nothing.
ZONE_OPT_CAPACITY_RULES_UNCONSTRAINED = 286
ZONE_OPT_CAPACITY_SUPPORT_UNCONSTRAINED = 3.9878
ZONE_OPT_CAPACITY_PCT_UNCONSTRAINED = 81.1

# Cost of the constraints, per scope. These were a single pair of constants
# while the answer was zero in both scopes. Since the 2026-08-17 re-derivation
# they differ sharply, so they are recorded separately: with unlimited zone
# sizes the locks cost almost nothing, and it is holding the zones to their real
# capacities that makes them expensive.
ZONE_OPT_CONSTRAINT_COST_RULES_UNLIMITED = 2
ZONE_OPT_CONSTRAINT_COST_SUPPORT_UNLIMITED = 0.0279
ZONE_OPT_CONSTRAINT_COST_RULES_CAPACITY = 106
ZONE_OPT_CONSTRAINT_COST_SUPPORT_CAPACITY = 1.3264

# Deltas against the hand-built layout (56 rules, 0.813 support, 16.3%).
ZONE_OPT_UNCONSTRAINED_GAIN_RULES = 188
ZONE_OPT_CAPACITY_GAIN_RULES = 0
ZONE_OPT_HAND_BUILT_SHARE_OF_CAPACITY_OPTIMUM_PCT = 100.0   # 0.8130 / 3.5599

# The two moves that account for the whole capacity-matched gain: add these
# two categories to the hand-built Zone 1 five and the group of seven
# captures 250 rules. Recorded from the greedy trace out of the hand-built
# layout (restart 0), where they are the first and second moves.
ZONE_OPT_MOVE_1 = 'BISCUITS AND COOKIES'
ZONE_OPT_MOVE_1_RULES = 106
ZONE_OPT_MOVE_2 = 'SNACKS'
ZONE_OPT_MOVE_2_RULES = 30
# Rules captured after those two moves. Before the 2026-08-17 remap this equalled
# the capacity-matched optimum (250), which is where the "two moves reach the
# optimum" wording came from. After the remap two moves reach 196 of the 286
# capacity optimum and the greedy path needs nine moves, so that wording is
# retired. Reported as a plain count.
ZONE_OPT_RULES_AFTER_TWO_MOVES = 316

# ======================================================================
# Daily granularity forecasting (analysis/daily_forecast.py, measured 2026-08-15)
# ======================================================================
#
# Extension of notebook 10, not a replacement. The monthly figures above
# (LINREG_*, PROPHET_*) stay as the reported finding; these are a second,
# separate result at daily granularity on the same eleven months.
#
# The series is the 304 trading days. Split is chronological: the first 243
# days train (17 Jul 2025 to 20 Mar 2026), the last 61 test (21 Mar to
# 20 May 2026). Every model is scored on the same 61 days. Two framings:
#   fixed    train once, forecast all 61 days from the end of training
#   rolling  each test day predicted from everything observed before it
#            (the framing "yesterday's value" belongs to)
# DAILY errors must never be set against the MONTHLY errors above; they are
# different quantities. Each daily model is read against the daily baselines
# in its own framing.
#
# Reproduce with  python analysis/daily_forecast.py  which writes
# dashboard/artifacts/daily_revenue.csv, daily_forecast_summary.json and
# reports/figures/chart25_daily_forecast.png. Prophet is fitted on the
# artifact values (revenue to the paisa) so the run reproduces exactly.
DAILY_TRAIN_DAYS = 243
DAILY_TEST_DAYS = 61
DAILY_TRAIN_END = '2026-03-20'
DAILY_TEST_START = '2026-03-21'
DAILY_MEAN_REVENUE = 717810.71          # mean over the 304 trading days
DAILY_TEST_MEAN_REVENUE = 717954.24     # the test window sits on the same level

# Fixed origin, MAE in rupees, R squared on the 61 test days, MAPE in per cent
DAILY_NAIVE_FLAT_MAE = 74994
DAILY_NAIVE_FLAT_R2 = -0.000
DAILY_HISTORICAL_MEAN_MAE = 74959
DAILY_HISTORICAL_MEAN_R2 = -0.000
DAILY_SEASONAL_NAIVE_FIXED_MAE = 101417
DAILY_SEASONAL_NAIVE_FIXED_R2 = -0.523
DAILY_LINREG_DOW_MAE = 69473            # best fixed-origin model
DAILY_LINREG_DOW_R2 = -0.022
DAILY_LINREG_DOW_MAPE = 11.37
DAILY_LINREG_DOW_TREND_MAE = 76461      # adding a trend makes it worse
DAILY_LINREG_DOW_TREND_R2 = -0.078
DAILY_PROPHET_MAE = 75114
DAILY_PROPHET_R2 = -0.063
DAILY_PROPHET_MAPE = 12.50

# Rolling one step ahead
DAILY_PERSISTENCE_MAE = 119611          # yesterday's value
DAILY_PERSISTENCE_R2 = -1.600
DAILY_PERSISTENCE_MAPE = 18.17
DAILY_EXPANDING_MEAN_MAE = 75074
DAILY_EXPANDING_MEAN_R2 = -0.004
DAILY_SEASONAL_NAIVE_MAE = 97759        # same weekday last week
DAILY_SEASONAL_NAIVE_R2 = -0.596
DAILY_SEASONAL_NAIVE_MAPE = 15.24
DAILY_LINREG_DOW_ROLLING_MAE = 69794    # best rolling model
DAILY_LINREG_DOW_ROLLING_R2 = -0.015
DAILY_LINREG_DOW_ROLLING_MAPE = 11.39
DAILY_PROPHET_ROLLING_MAE = 73423
DAILY_PROPHET_ROLLING_R2 = -0.044
DAILY_PROPHET_ROLLING_MAPE = 12.14

# The verdict, as numbers
DAILY_BEST_MODEL_VS_PERSISTENCE_PCT = 41.6     # MAE reduction, LR day-of-week refit daily
DAILY_BEST_MODEL_VS_SEASONAL_NAIVE_PCT = 28.6
DAILY_BEST_MODEL_VS_HISTORICAL_MEAN_PCT = 7.3  # the demanding baseline: a constant
DAILY_BEST_R2 = -0.015                         # highest R squared of any fitted model (LR day-of-week, refit daily)
DAILY_ANY_MODEL_R2_POSITIVE = False            # nothing explains test variance beyond its mean

# Dashain at daily granularity. Prophet with the specified settings (weekly
# seasonality, default trend flexibility), told nothing about festivals:
DAILY_PROPHET_DASHAIN_DETECTED = False
DAILY_PROPHET_FITTED_PEAK_DAY = '2026-03-18'   # end of training, not the festival
DAILY_ACTUAL_PEAK_DAY = '2025-10-01'           # the day before Vijaya Dashami
DAILY_ACTUAL_DASHAIN_WINDOW_MEAN = 988038      # actual mean, 22 Sep to 2 Oct 2025
DAILY_PROPHET_DASHAIN_WINDOW_FITTED_MEAN = 716206
# With a trend flexible enough to chase the spike (changepoint_prior_scale
# 0.5) Prophet does peak inside the window in sample, and forecasts worse:
DAILY_PROPHET_FLEXIBLE_DASHAIN_DETECTED = True
DAILY_PROPHET_FLEXIBLE_MAE = 102647
DAILY_PROPHET_FLEXIBLE_R2 = -0.521

# Day-of-week effects in the daily series (all 304 days)
DAILY_HIGHEST_MEAN_WEEKDAY = 'Wednesday'       # Rs 750,109 mean; Friday Rs 745,545
DAILY_HIGHEST_TOTAL_WEEKDAY = 'Friday'         # 44 Fridays against 43 Wednesdays
DAILY_LOWEST_MEAN_WEEKDAY = 'Saturday'         # Rs 652,803 mean

# Error structure: the two Nepali New Year days (13 and 14 April 2026) carry
# 51.2 per cent of the best fixed model's squared error. Context, not a
# correction; the headline metrics keep every day.
DAILY_NEW_YEAR_SHARE_OF_SSE_PCT = 51.2
DAILY_LINREG_DOW_MAE_EXCLUDING_NEW_YEAR = 56873

# ======================================================================
# Richer features for the basket value classifier
# (analysis/basket_features.py, measured 2026-08-15)
# ======================================================================
#
# Extension of notebooks 11 and 12, not a replacement. CLASSIFIER_ACCURACY,
# NEURAL_NET_ACCURACY, FEATURE_CEILING_ACCURACY and DISTINCT_FEATURE_PATTERNS
# above stay as the reported finding on the 25 binary flags. The module
# recomputes those four in the same run, on the same labels, split
# (test_size 0.30, random_state 42, stratified) and seed, and they reproduce
# exactly, which is what guarantees the new numbers are like for like.
#
# Feature sets:
#   binary    the 25 category flags (the reported result)
#   discrete  flags + item count + category count + day of week + month  (45)
#   full      the same, with each flag replaced by the quantity bought   (45)
# Hour of day is not available: every timestamp in the raw export is
# 00:00:00, so the source records the date only.
#
# The ceiling is the notebook 12 method (majority label per exact feature
# pattern, all 218,037 baskets). With richer features patterns become nearly
# unique and the ceiling stops binding: it is reported as asked, beside the
# share of baskets whose pattern occurs once and beside a pattern-lookup
# scored out of sample, so its inflation is visible rather than hidden.
FEATURES_HOUR_OF_DAY_AVAILABLE = False

FEATURES_FULL_COUNT = 45
FEATURES_DISCRETE_COUNT = 45

FEATURES_CEILING_BINARY = 0.7234           # equals FEATURE_CEILING_ACCURACY, recomputed
FEATURES_CEILING_DISCRETE = 0.8548
FEATURES_CEILING_FULL = 0.9187             # the new ceiling, same method
FEATURES_PATTERNS_BINARY = 21032           # equals DISTINCT_FEATURE_PATTERNS
FEATURES_PATTERNS_DISCRETE = 95521
FEATURES_PATTERNS_FULL = 126437
FEATURES_SINGLETON_SHARE_BINARY = 6.3      # per cent of baskets whose pattern occurs once
FEATURES_SINGLETON_SHARE_DISCRETE = 35.3
FEATURES_SINGLETON_SHARE_FULL = 50.8
FEATURES_LOOKUP_TEST_ACC_BINARY = 0.6368   # memorise training patterns, score on test
FEATURES_LOOKUP_TEST_ACC_FULL = 0.5166     # 51.5 per cent of test baskets have an unseen pattern
FEATURES_LOOKUP_UNSEEN_FULL = 53.2

# Accuracies on the same 65,412 test baskets
FEATURES_TREE_BINARY_ACCURACY = 0.6138     # equals CLASSIFIER_ACCURACY, recomputed
FEATURES_MLP_BINARY_ACCURACY = 0.6917      # equals NEURAL_NET_ACCURACY, recomputed
FEATURES_TREE_DISCRETE_ACCURACY = 0.7053
FEATURES_MLP_DISCRETE_ACCURACY = 0.7236
FEATURES_TREE_FULL_ACCURACY = 0.7228       # depth 5, 32 leaves
FEATURES_MLP_FULL_ACCURACY = 0.7587        # 64-32, 5,123 parameters, 30 epochs
FEATURES_MLP_FULL_PARAMETERS = 5123

# Share of the ceiling reached
FEATURES_TREE_BINARY_SHARE = 84.9
FEATURES_MLP_BINARY_SHARE = 95.6
FEATURES_TREE_FULL_SHARE = 78.7
FEATURES_MLP_FULL_SHARE = 82.6

# Gains, in accuracy points, old to new (binary to full)
FEATURES_TREE_GAIN_POINTS = 10.90
FEATURES_MLP_GAIN_POINTS = 6.71
FEATURES_CEILING_GAIN_POINTS = 19.53

# Feature importances of the depth-5 tree on the full set. Item count
# displaces COOKING OIL as the top predictor; RICE quantity stays second.
FEATURES_NEW_TOP_FEATURE = 'n_items'
FEATURES_NEW_TOP_IMPORTANCE = 0.730
FEATURES_NEW_SECOND_FEATURE = 'RICE qty'
FEATURES_NEW_SECOND_IMPORTANCE = 0.141
FEATURES_COOKING_OIL_NEW_RANK = 5
FEATURES_COOKING_OIL_NEW_IMPORTANCE = 0.010     # was 0.280 on the flags
FEATURES_RICE_NEW_RANK = 2
FEATURES_RICE_NEW_IMPORTANCE = 0.141            # was 0.215 on the flags
FEATURES_NEW_TREE_FEATURES_USED = 8             # of 45; the old tree used 11 of 25

# Per-class recall, full feature set
FEATURES_MLP_FULL_RECALL_MEDIUM = 0.661         # was 0.550
FEATURES_MLP_FULL_RECALL_LARGE = 0.560          # was 0.472
FEATURES_TREE_FULL_RECALL_MEDIUM = 0.558        # was 0.273
FEATURES_TREE_FULL_RECALL_LARGE = 0.517         # was 0.367
