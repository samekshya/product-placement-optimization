"""
Tests that verify the dashboard's precomputed artifact files exist, have the
expected shape, and agree with config/metrics.py.

These tests do NOT touch the confidential raw or processed data. They only
check the small aggregate files in dashboard/artifacts/, which is exactly
what the dashboard itself is allowed to load. Run these after running
dashboard/precompute_artifacts.py.

Run with: pytest tests/test_artifacts.py -v
"""

import json
import os
import pytest
import pandas as pd
from config import metrics as M

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboard", "artifacts")

REQUIRED_ARTIFACT_FILES = [
    "kpi_summary.json",
    "cross_sell_summary.json",
    "monthly_revenue.csv",
    "category_distribution.csv",
    "basket_value_hist.csv",
    "category_rules.csv",
    "product_rules.csv",
    "cooccurrence_matrix.csv",
    "top_pairs.csv",
    "top_products.csv",
    "cluster_assignments.csv",
    "abc_analysis.csv",
    "day_of_week.csv",
]


@pytest.fixture(scope="module")
def artifacts_exist():
    """Skip the whole module cleanly if artifacts have not been generated,
    rather than failing every test with a confusing FileNotFoundError."""
    if not os.path.isdir(ARTIFACTS_DIR):
        pytest.skip(
            "dashboard/artifacts/ not found. Run "
            "`python dashboard/precompute_artifacts.py` first."
        )
    return True


class TestArtifactFilesExist:
    def test_all_required_files_present(self, artifacts_exist):
        missing = [
            f for f in REQUIRED_ARTIFACT_FILES
            if not os.path.exists(os.path.join(ARTIFACTS_DIR, f))
        ]
        assert not missing, f"Missing artifact files: {missing}. Re-run precompute_artifacts.py"


class TestKPISummary:
    @pytest.fixture
    def kpi(self, artifacts_exist):
        with open(os.path.join(ARTIFACTS_DIR, "kpi_summary.json")) as f:
            return json.load(f)

    def test_transaction_count_matches_config(self, kpi):
        assert kpi["total_transactions"] == M.TOTAL_TRANSACTIONS

    def test_category_count_matches_config(self, kpi):
        assert kpi["n_categories"] == M.TOTAL_CATEGORIES

    def test_has_generated_timestamp(self, kpi):
        # Freshness indicator so the dashboard can warn if artifacts are stale
        # relative to the notebooks that produced them.
        assert "generated_at" in kpi, (
            "kpi_summary.json should carry a generated_at timestamp so the "
            "dashboard can show when the data was last refreshed."
        )


class TestMonthlyRevenue:
    @pytest.fixture
    def monthly(self, artifacts_exist):
        return pd.read_csv(os.path.join(ARTIFACTS_DIR, "monthly_revenue.csv"))

    def test_has_eleven_months(self, monthly):
        assert len(monthly) == M.CALENDAR_MONTHS

    def test_no_negative_revenue(self, monthly):
        assert (monthly["revenue"] >= 0).all()

    def test_revenue_sums_to_total(self, monthly):
        assert monthly["revenue"].sum() == pytest.approx(M.TOTAL_REVENUE, rel=0.01)


class TestCategoryRules:
    @pytest.fixture
    def rules(self, artifacts_exist):
        return pd.read_csv(os.path.join(ARTIFACTS_DIR, "category_rules.csv"))

    def test_rule_count_matches_config(self, rules):
        assert len(rules) == M.RULES_TOTAL

    def test_required_columns_present(self, rules):
        required = {"antecedents", "consequents", "support", "confidence", "lift"}
        assert required.issubset(set(rules.columns))

    def test_lift_values_all_positive(self, rules):
        assert (rules["lift"] > 0).all()

    def test_support_and_confidence_are_valid_probabilities(self, rules):
        assert (rules["support"] > 0).all() and (rules["support"] <= 1).all()
        assert (rules["confidence"] > 0).all() and (rules["confidence"] <= 1).all()

    def test_max_lift_matches_config(self, rules):
        assert rules["lift"].max() == pytest.approx(M.MAX_LIFT_CATEGORY, abs=0.01)


class TestClusterAssignments:
    @pytest.fixture
    def clusters(self, artifacts_exist):
        return pd.read_csv(os.path.join(ARTIFACTS_DIR, "cluster_assignments.csv"))

    def test_every_category_assigned(self, clusters):
        assert len(clusters) == M.TOTAL_CATEGORIES

    def test_exactly_three_clusters(self, clusters):
        assert clusters["cooccurrence_cluster"].nunique() == 3

    def test_no_category_appears_twice(self, clusters):
        assert clusters["category"].is_unique


class TestABCAnalysis:
    @pytest.fixture
    def abc(self, artifacts_exist):
        return pd.read_csv(os.path.join(ARTIFACTS_DIR, "abc_analysis.csv"))

    def test_only_valid_classes(self, abc):
        assert set(abc["abc_category"].unique()).issubset({"A", "B", "C"})

    def test_class_a_count_matches_config(self, abc):
        a_count = (abc["abc_category"] == "A").sum()
        assert a_count == M.ABC_CLASS_A_PRODUCTS

    def test_cumulative_percentage_reaches_100(self, abc):
        assert abc["cumulative_pct"].max() == pytest.approx(100, abs=0.5)