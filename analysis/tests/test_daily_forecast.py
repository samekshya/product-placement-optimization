"""Tests for daily granularity forecasting (analysis/daily_forecast.py).

Pins the split, the baselines, the reported figures and the two claims that
matter: every fitted model beats naive persistence, and no model reaches a
positive R squared on the held-out days. Also pins that the monthly result
in notebook 10 is untouched.

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

from analysis import daily_forecast as DF  # noqa: E402
from config import metrics as M  # noqa: E402

ARTIFACTS = ROOT / "dashboard" / "artifacts"


@pytest.fixture(scope="module")
def daily():
    path = ARTIFACTS / DF.SERIES_ARTIFACT
    if not path.exists():
        pytest.skip("daily_revenue.csv not generated; run analysis/daily_forecast.py")
    return DF.load_daily_series(str(ARTIFACTS))


@pytest.fixture(scope="module")
def summary():
    path = ARTIFACTS / DF.SUMMARY_ARTIFACT
    if not path.exists():
        pytest.skip("daily_forecast_summary.json not generated; run analysis/daily_forecast.py")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def split(daily):
    train, test = DF.chronological_split(daily)
    return train, test, list(range(len(train), len(daily)))


def test_series_is_the_304_trading_days(daily):
    assert len(daily) == M.TRADING_DAYS == 304
    assert round(float(daily["revenue"].sum()), 2) == pytest.approx(M.TOTAL_REVENUE, abs=0.05)
    assert str(daily["date"].min().date()) == M.DATA_START
    assert str(daily["date"].max().date()) == M.DATA_END
    full = pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")
    missing = full.difference(daily["date"])
    assert [str(d.date()) for d in missing] == [
        "2025-09-10", "2025-10-02", "2025-10-23", "2026-03-05"]


def test_split_is_chronological_and_leak_free(split):
    train, test, _ = split
    assert len(train) == M.DAILY_TRAIN_DAYS == 243
    assert len(test) == M.DAILY_TEST_DAYS == 61
    assert train["date"].max() < test["date"].min()
    assert str(train["date"].max().date()) == M.DAILY_TRAIN_END
    assert str(test["date"].min().date()) == M.DAILY_TEST_START
    assert set(train["date"]).isdisjoint(set(test["date"]))


def test_naive_persistence_is_yesterday(daily, split):
    _, _, idx = split
    pred = DF.naive_persistence(daily, idx)
    rev = daily["revenue"].to_numpy()
    assert np.allclose(pred, rev[[i - 1 for i in idx]])


def test_seasonal_naive_uses_the_same_weekday(daily, split):
    _, test, idx = split
    pred = DF.seasonal_naive(daily, idx)
    dow = daily["date"].dt.dayofweek.to_numpy()
    rev = daily["revenue"].to_numpy()
    for k, i in enumerate(idx):
        j = i - 7  # no closures inside the test window, so exactly a week back
        assert dow[j] == dow[i]
        assert pred[k] == rev[j]


def test_baselines_reproduce(daily, split):
    _, test, idx = split
    y = test["revenue"].to_numpy()
    assert round(DF.metrics(y, DF.naive_persistence(daily, idx))["mae"]) == M.DAILY_PERSISTENCE_MAE
    assert round(DF.metrics(y, DF.seasonal_naive(daily, idx))["mae"]) == M.DAILY_SEASONAL_NAIVE_MAE
    assert round(DF.metrics(y, DF.historical_mean(daily, len(daily) - len(idx), idx))["mae"]) \
        == M.DAILY_HISTORICAL_MEAN_MAE


def test_linear_dow_reproduces_and_beats_the_naive_baselines(daily, split):
    _, test, idx = split
    y = test["revenue"].to_numpy()
    n_train = len(daily) - len(idx)
    fixed, model = DF.linear_fixed(daily, n_train, idx)
    m_fixed = DF.metrics(y, fixed)
    assert round(m_fixed["mae"]) == M.DAILY_LINREG_DOW_MAE
    assert round(m_fixed["r2"], 3) == pytest.approx(M.DAILY_LINREG_DOW_R2, abs=0.0005)
    rolling = DF.linear_rolling(daily, idx)
    m_roll = DF.metrics(y, rolling)
    assert round(m_roll["mae"]) == M.DAILY_LINREG_DOW_ROLLING_MAE
    assert m_roll["mae"] < DF.metrics(y, DF.naive_persistence(daily, idx))["mae"]
    assert m_roll["mae"] < DF.metrics(y, DF.seasonal_naive(daily, idx))["mae"]
    # the day-of-week coefficients carry the notebook 03 ordering at the ends
    coefs = dict(zip(DF.WEEKDAYS, model.coef_))
    assert min(coefs, key=coefs.get) == "Saturday"


def test_prophet_fixed_origin_reproduces(daily, split):
    _, test, idx = split
    y = test["revenue"].to_numpy()
    pred, _ = DF.prophet_fixed(daily, len(daily) - len(idx), idx)
    m = DF.metrics(y, pred)
    assert round(m["mae"]) == M.DAILY_PROPHET_MAE
    assert round(m["r2"], 3) == pytest.approx(M.DAILY_PROPHET_R2, abs=0.0005)


def test_no_daily_model_reaches_positive_r2(summary):
    for key, m in summary["models"].items():
        assert m["r2"] < 0, key
    assert summary["verdict"]["any_model_r2_positive_fixed"] is False
    assert summary["verdict"]["any_model_r2_positive_rolling"] is False


def test_every_rolling_model_beats_persistence(summary):
    base = summary["models"]["naive_persistence"]["mae"]
    for key in ("expanding_mean", "seasonal_naive", "linear_dow_rolling",
                "prophet_weekly_rolling"):
        assert summary["models"][key]["mae"] < base


def test_prophet_does_not_find_dashain_by_default_but_can_be_forced(summary):
    assert summary["dashain"]["fitted_peak_inside_window"] is False
    assert summary["dashain"]["actual_peak_day"] == "2025-10-01"
    flex = summary["prophet_sensitivity"]
    assert flex["dashain"]["fitted_peak_inside_window"] is True
    assert flex["mae"] > summary["models"]["prophet_weekly"]["mae"]


def test_day_of_week_effects(daily):
    means = daily.groupby("day_of_week")["revenue"].mean()
    totals = daily.groupby("day_of_week")["revenue"].sum()
    assert means.idxmin() == "Saturday"
    assert means.idxmax() == "Wednesday"
    assert totals.idxmax() == "Friday"
    assert round(float(totals["Friday"])) == M.FRIDAY_REVENUE


def test_monthly_result_is_untouched():
    """The daily work is an extension. Notebook 10's figures stay as reported."""
    assert M.LINREG_R2 == -2.377
    assert M.LINREG_MAE == 3395703
    assert M.PROPHET_MAE == 2909633
    assert M.PROPHET_IMPROVEMENT_PCT == 14.3
    assert (ROOT / "notebooks" / "10_demand_forecasting.ipynb").exists()
    assert (ROOT / "reports" / "figures" / "chart20_linear_regression_forecast.png").exists()
    assert (ROOT / "reports" / "figures" / "chart21_prophet_forecast.png").exists()
