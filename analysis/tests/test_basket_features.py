"""Tests for the richer basket features study (analysis/basket_features.py).

Pins three things: the ceiling method agrees with the notebook 12 string
method, the reported binary-flag figures reproduce inside the new run (which
is what makes the new numbers like for like), and the artifact carries the
reported new figures.

Run:
    venv/Scripts/python -m pytest analysis/tests/ -v      (from the repo root)
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis import basket_features as BF  # noqa: E402
from config import metrics as M  # noqa: E402

ARTIFACTS = ROOT / "dashboard" / "artifacts"


@pytest.fixture(scope="module")
def summary():
    path = ARTIFACTS / BF.SUMMARY_ARTIFACT
    if not path.exists():
        pytest.skip("basket_features_summary.json not generated; run analysis/basket_features.py")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def built():
    """Labels, feature sets and split rebuilt from the cleaned record.
    Skipped on a clone without the confidential CSV."""
    if not Path(BF.CLEANED_CSV).exists():
        pytest.skip("cleaned record not present")
    df = BF.load_lines()
    labels, sets = BF.build_feature_sets(df)
    tr, te = BF.split_indices(labels)
    return labels, sets, tr, te


def test_segment_thresholds_are_the_notebook_11_ones():
    assert BF.basket_segment(499.99) == "Small"
    assert BF.basket_segment(500) == "Medium"
    assert BF.basket_segment(2000) == "Medium"
    assert BF.basket_segment(2000.01) == "Large"


def test_ceiling_matches_the_string_method_on_a_toy_frame():
    """The numpy grouping must partition rows exactly as notebook 12's
    per-row string did."""
    X = pd.DataFrame({"a": [1, 1, 0, 0, 1, 1], "b": [0, 0, 1, 1, 0, 0]})
    y = pd.Series(["Small", "Small", "Large", "Medium", "Medium", "Small"])
    got = BF.ceiling(X, y)
    pattern = X.astype(str).agg("".join, axis=1)
    frame = pd.DataFrame({"pattern": pattern.values, "label": y.values})
    expected = frame.groupby("pattern")["label"].apply(
        lambda s: s.value_counts().iloc[0]).sum() / len(frame)
    assert got["ceiling"] == pytest.approx(expected)
    assert got["distinct_patterns"] == 2
    assert got["singleton_patterns"] == 0


def test_hour_of_day_is_reported_unavailable(summary):
    assert summary["hour_of_day"]["available"] is False
    assert M.FEATURES_HOUR_OF_DAY_AVAILABLE is False


def test_split_reproduces_notebooks_11_and_12(built):
    labels, sets, tr, te = built
    assert len(tr) == M.CLASSIFIER_TRAIN_BASKETS == 152625
    assert len(te) == M.CLASSIFIER_TEST_BASKETS == 65412
    assert len(labels) == M.TOTAL_TRANSACTIONS
    assert (labels == "Small").sum() == 108349
    assert sets["binary"].shape == (218037, 25)
    assert sets["full"].shape[1] == M.FEATURES_FULL_COUNT
    # every set shares the same basket order, so the split is identical
    assert sets["binary"].index.equals(sets["full"].index)
    assert sets["binary"].index.equals(labels.index)


def test_binary_ceiling_and_tree_reproduce_the_reported_figures(built):
    """The 71.67 per cent ceiling and the 61.30 per cent tree are recomputed,
    not replaced. If this fails, the new numbers are not comparable."""
    labels, sets, tr, te = built
    c = BF.ceiling(sets["binary"], labels)
    assert round(c["ceiling"], 4) == M.FEATURE_CEILING_ACCURACY
    assert c["distinct_patterns"] == M.DISTINCT_FEATURE_PATTERNS
    res, _ = BF.fit_tree(sets["binary"].iloc[tr], labels.iloc[tr],
                         sets["binary"].iloc[te], labels.iloc[te])
    assert round(res["accuracy"], 3) == M.CLASSIFIER_ACCURACY
    top = next(iter(res["importances"]))
    assert top == M.CLASSIFIER_TOP_FEATURE
    assert round(res["importances"][top], 3) == M.CLASSIFIER_TOP_FEATURE_IMPORTANCE


def test_full_tree_reproduces_and_item_count_leads(built):
    labels, sets, tr, te = built
    res, _ = BF.fit_tree(sets["full"].iloc[tr], labels.iloc[tr],
                         sets["full"].iloc[te], labels.iloc[te])
    assert round(res["accuracy"], 4) == M.FEATURES_TREE_FULL_ACCURACY
    ranked = list(res["importances"])
    assert ranked[0] == M.FEATURES_NEW_TOP_FEATURE
    assert ranked[1] == M.FEATURES_NEW_SECOND_FEATURE
    assert res["leaves"] == 32


def test_artifact_baseline_rows_are_the_reported_figures(summary):
    bm, bc = summary["models"], summary["ceilings"]
    assert round(bm["binary_tree_depth5"]["accuracy"], 3) == M.CLASSIFIER_ACCURACY
    assert round(bm["binary_mlp"]["accuracy"], 4) == M.NEURAL_NET_ACCURACY
    assert bm["binary_mlp"]["parameters"] == M.NEURAL_NET_PARAMETERS
    assert round(bc["binary"]["ceiling"], 4) == M.FEATURE_CEILING_ACCURACY
    assert bc["binary"]["distinct_patterns"] == M.DISTINCT_FEATURE_PATTERNS


def test_artifact_new_rows_are_the_reported_figures(summary):
    bm, bc = summary["models"], summary["ceilings"]
    assert round(bm["full_tree_depth5"]["accuracy"], 4) == M.FEATURES_TREE_FULL_ACCURACY
    assert round(bm["full_mlp"]["accuracy"], 4) == M.FEATURES_MLP_FULL_ACCURACY
    assert round(bc["full"]["ceiling"], 4) == M.FEATURES_CEILING_FULL
    assert bc["full"]["distinct_patterns"] == M.FEATURES_PATTERNS_FULL
    assert bm["full_mlp"]["accuracy"] < bc["full"]["ceiling"]
    assert bm["full_mlp"]["accuracy"] > bm["binary_mlp"]["accuracy"]
    assert bm["full_tree_depth5"]["accuracy"] > bm["binary_tree_depth5"]["accuracy"]


def test_ceiling_inflates_faster_than_the_models(summary):
    """The honest reading of the new ceiling: it is a memorisation bound. Half
    the baskets have a unique pattern and a pattern lookup scores barely above
    the majority baseline out of sample."""
    bc, bm = summary["ceilings"], summary["models"]
    ceiling_gain = bc["full"]["ceiling"] - bc["binary"]["ceiling"]
    assert ceiling_gain > bm["full_mlp"]["accuracy"] - bm["binary_mlp"]["accuracy"]
    assert bc["full"]["singleton_basket_share"] > 0.45
    lookup = bc["full"]["pattern_lookup"]["test_accuracy"]
    assert lookup < bm["binary_mlp"]["accuracy"]
    assert lookup - summary["split"]["majority_baseline"] < 0.03


def test_feature_importance_story(summary):
    fi = summary["feature_importance"]
    assert fi["new_top"][0] == "n_items"
    assert fi["displaced"] is True
    assert fi["cooking_oil_new_rank"] == M.FEATURES_COOKING_OIL_NEW_RANK
    assert fi["rice_new_rank"] == M.FEATURES_RICE_NEW_RANK
    assert fi["old_top"][:2] == ["COOKING OIL", "RICE"]


def test_original_notebook_12_constants_are_untouched():
    # re-pinned 2026-08-17 after the category remap (notebooks 11 and 12 re-run)
    assert M.FEATURE_CEILING_ACCURACY == 0.7234
    assert M.DISTINCT_FEATURE_PATTERNS == 21032
    assert M.NEURAL_NET_ACCURACY == 0.6917
    assert M.CLASSIFIER_ACCURACY == 0.614
    assert (ROOT / "notebooks" / "12_neural_network.ipynb").exists()
    assert (ROOT / "reports" / "figures" / "chart24_model_comparison.png").exists()
