"""
Tests for config/metrics.py — the single source of truth for every verified
number quoted in the thesis and dashboard.

These tests exist to catch the exact bug class that caused problems earlier
in the project: a number changing in one place (a notebook output) without
being updated everywhere else it is quoted (README, dashboard, thesis).

Run with: pytest tests/test_metrics.py -v
"""

import pytest
from config import metrics as M


class TestDatasetIntegrity:
    """The raw counts must be internally consistent with each other."""

    def test_clean_rows_less_than_raw_rows(self):
        assert M.CLEAN_ROWS < M.RAW_ROWS, (
            "Cleaning should always remove rows (duplicates, invalid records), "
            "never add them."
        )

    def test_clean_rows_are_positive(self):
        assert M.CLEAN_ROWS > 0
        assert M.TOTAL_TRANSACTIONS > 0
        assert M.TOTAL_PRODUCTS > 0
        assert M.TOTAL_CATEGORIES > 0

    def test_transactions_less_than_clean_rows(self):
        # Multiple product lines belong to one transaction (invoice),
        # so transactions must be fewer than total product rows.
        assert M.TOTAL_TRANSACTIONS < M.CLEAN_ROWS

    def test_category_count_is_25(self):
        # This number is quoted in every notebook, the README, and the
        # thesis. If the cleaning pipeline ever changes the mapping,
        # this test catches the drift immediately.
        assert M.TOTAL_CATEGORIES == 25


class TestRevenueConsistency:
    """Revenue figures must be plausible and internally consistent."""

    def test_total_revenue_is_positive(self):
        assert M.TOTAL_REVENUE > 0

    def test_mean_basket_value_is_plausible(self):
        # Sanity range check, not an exact value check — catches gross
        # errors like a misplaced decimal point or a unit mismatch.
        assert 100 < M.MEAN_BASKET_VALUE < 10000

    def test_mean_basket_times_transactions_approximates_revenue(self):
        implied_revenue = M.MEAN_BASKET_VALUE * M.TOTAL_TRANSACTIONS
        # Allow 1% tolerance for rounding in the stored mean basket value.
        assert implied_revenue == pytest.approx(M.TOTAL_REVENUE, rel=0.01), (
            "Mean basket value x transaction count should reproduce total "
            "revenue within rounding tolerance. A mismatch here usually means "
            "one of the two numbers was updated without updating the other."
        )


class TestAssociationRules:
    """Rule counts and statistical validation numbers must be consistent."""

    def test_significant_rules_not_more_than_total(self):
        assert M.RULES_SIGNIFICANT <= M.RULES_TOTAL

    def test_max_lift_product_exceeds_max_lift_category(self):
        # Product-level rules are more specific than category-level rules,
        # so they should show stronger (higher) lift values.
        assert M.MAX_LIFT_PRODUCT > M.MAX_LIFT_CATEGORY

    def test_lift_values_are_above_one(self):
        # A lift below 1 would mean a negative association, which should
        # never be reported as a "strongest rule" finding.
        assert M.MAX_LIFT_CATEGORY > 1.0
        assert M.MAX_LIFT_PRODUCT > 1.0


class TestClustering:
    """Silhouette scores must fall in the valid range and show the expected
    improvement from frequency-based to co-occurrence-based clustering."""

    def test_silhouette_scores_in_valid_range(self):
        # Silhouette score is mathematically bounded between -1 and 1.
        assert -1 <= M.SILHOUETTE_FREQUENCY <= 1
        assert -1 <= M.SILHOUETTE_COOCCURRENCE <= 1

    def test_cooccurrence_beats_frequency_clustering(self):
        assert M.SILHOUETTE_COOCCURRENCE > M.SILHOUETTE_FREQUENCY, (
            "The entire justification for using co-occurrence clustering "
            "over frequency clustering rests on this improvement. If this "
            "ever fails, the clustering methodology section needs rewriting."
        )


class TestCrossSellComparison:
    """The optimised layout must outperform the baselines it is compared
    against, or the central technical claim of the thesis is false."""

    def test_optimised_beats_current_layout(self):
        assert M.CROSS_SELL_OPTIMISED > M.CROSS_SELL_CURRENT

    def test_optimised_beats_frequency_baseline(self):
        assert M.CROSS_SELL_OPTIMISED > M.CROSS_SELL_FREQUENCY

    def test_frequency_beats_random(self):
        assert M.CROSS_SELL_FREQUENCY > M.CROSS_SELL_RANDOM


class TestBasketClassifier:
    """The classifier must beat its own baseline or the finding is void."""

    def test_classifier_beats_majority_baseline(self):
        assert M.CLASSIFIER_ACCURACY > M.CLASSIFIER_BASELINE

    def test_accuracy_values_are_valid_probabilities(self):
        assert 0 < M.CLASSIFIER_ACCURACY < 1
        assert 0 < M.CLASSIFIER_BASELINE < 1


class TestABCAnalysis:
    """ABC class proportions must sum sensibly and Class A must be the
    smallest product group generating the largest revenue share."""

    def test_class_a_is_smaller_product_count_than_class_c(self):
        assert M.ABC_CLASS_A_PRODUCTS < M.ABC_CLASS_C_PRODUCTS, (
            "Class A should be a small, high-priority set of products. "
            "If it is not smaller than Class C, the ABC cutoffs are wrong."
        )

    def test_class_a_revenue_percentage_is_majority(self):
        assert M.ABC_CLASS_A_REVENUE_PCT >= 50


class TestDateRange:
    """The data window must match what every notebook and the thesis states."""

    def test_calendar_months_is_eleven(self):
        assert M.CALENDAR_MONTHS == 11

    def test_data_start_before_data_end(self):
        assert M.DATA_START < M.DATA_END