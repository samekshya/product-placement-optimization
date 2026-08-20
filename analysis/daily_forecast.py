"""Daily granularity revenue forecasting.

Extension of notebook 10, which fitted Linear Regression and Prophet to eleven
monthly observations and reported an R squared of -2.377 for the regression
on a three point test set. The diagnosis in that notebook was too few
observations, not the wrong method. This module tests that diagnosis by
refitting at daily granularity, where the same eleven months give 304
observations, and asks a stricter question than the monthly work did: does
any model beat the naive daily baselines on a held-out chronological test set?

WHAT IS COMPARED, ON THE SAME TEST DAYS
    Two framings, because they answer different questions and are not
    interchangeable.

    Fixed origin (train once, forecast every test day from the end of the
    training window, the "plan the next two months" question):
        naive flat              last training day repeated
        historical mean         training mean repeated (R squared is defined
                                against a mean, so this is the baseline any
                                model must beat for R squared to be positive)
        seasonal naive fixed    last observed week of training repeated
        linear regression       day-of-week dummies
        linear regression       day-of-week dummies plus a linear trend
        Prophet                 weekly seasonality on, yearly and daily off

    Rolling one step ahead (each test day predicted with everything observed
    before it, the "what will tomorrow bring" question, which is the framing
    the naive baselines are usually quoted in):
        naive persistence       yesterday's value
        expanding mean          mean of every day observed so far
        seasonal naive          same weekday last week
        linear regression       day-of-week dummies, refit every day
        Prophet                 weekly seasonality, refit every day

    Every model is scored on the identical held-out days with R squared, MAE,
    RMSE and MAPE. Daily errors are never compared with the monthly errors in
    notebook 10: they are different quantities. Each daily model is compared
    with the daily naive baselines in its own framing.

THE SPLIT
    Chronological, never random: the first 80 per cent of trading days train,
    the last 20 per cent test. A random split would put future days in the
    training set and leak information backwards.

THE DAY-OF-WEEK EFFECTS
    Notebook 03 found Friday the highest revenue day, Wednesday the highest
    average basket, and Saturday (the Nepali weekly holiday) the quietest. The
    day-of-week dummies carry those effects into the regression, and the
    module reports the per-weekday daily means so the effect can be read
    directly.

MISSING DAYS
    304 of the 308 calendar days have sales. The four missing days are
    closures (two of them are Vijaya Dashami and Bhai Tika). The series is the
    304 trading days; "yesterday" means the previous trading day and "same
    weekday last week" means the most recent earlier trading day with that
    weekday, which is seven days back except across a closure.

Run:
    python analysis/daily_forecast.py            full run, writes artifacts and chart
    python analysis/daily_forecast.py --quick    skips the rolling Prophet refits

Writes:
    dashboard/artifacts/daily_revenue.csv          the 304 day series
    dashboard/artifacts/daily_forecast_summary.json every figure reported
    reports/figures/chart25_daily_forecast.png
"""

import json
import logging
import os
import sys
import time

import numpy as np
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

CLEANED_CSV = os.environ.get(
    "PP_CLEANED_CSV", os.path.join(_ROOT, "data", "processed", "sales_data_cleaned.csv")
)
ARTIFACTS_DIR = os.environ.get(
    "PP_ARTIFACTS_DIR", os.path.join(_ROOT, "dashboard", "artifacts")
)
FIGURES_DIR = os.path.join(_ROOT, "reports", "figures")

SERIES_ARTIFACT = "daily_revenue.csv"
SUMMARY_ARTIFACT = "daily_forecast_summary.json"
FIGURE_NAME = "chart25_daily_forecast.png"

TEST_FRACTION = 0.2
RANDOM_SEED = 42

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Dashain 2025: Ghatasthapana 22 September, Vijaya Dashami 2 October (the
# store was closed that day). Used only to ask whether Prophet's fitted curve
# peaks inside the festival window; the model is never told these dates.
DASHAIN_WINDOW = ("2025-09-22", "2025-10-02")


# ----------------------------------------------------------------------
# the series
# ----------------------------------------------------------------------

def build_daily_series(cleaned_csv=CLEANED_CSV):
    """Daily revenue, transactions and line items from the cleaned record.

    Reads only the three columns it needs. Never writes to data/.
    """
    df = pd.read_csv(cleaned_csv, usecols=["date", "invoice_no", "total_amount"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    daily = (
        df.groupby("date")
        .agg(revenue=("total_amount", "sum"),
             transactions=("invoice_no", "nunique"),
             line_items=("invoice_no", "size"))
        .reset_index()
        .sort_values("date")
        .reset_index(drop=True)
    )
    daily["day_of_week"] = daily["date"].dt.day_name()
    return daily


def load_daily_series(artifacts_dir=ARTIFACTS_DIR):
    path = os.path.join(artifacts_dir, SERIES_ARTIFACT)
    daily = pd.read_csv(path, parse_dates=["date"])
    return daily.sort_values("date").reset_index(drop=True)


def write_daily_series(daily, artifacts_dir=ARTIFACTS_DIR):
    path = os.path.join(artifacts_dir, SERIES_ARTIFACT)
    out = daily.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out["revenue"] = out["revenue"].round(2)
    out.to_csv(path, index=False)
    return path


def chronological_split(daily, test_fraction=TEST_FRACTION):
    """First (1 - test_fraction) of trading days train, the rest test."""
    n = len(daily)
    n_test = int(round(n * test_fraction))
    n_train = n - n_test
    return daily.iloc[:n_train].copy(), daily.iloc[n_train:].copy()


# ----------------------------------------------------------------------
# metrics
# ----------------------------------------------------------------------

def metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = y_true - y_pred
    sse = float(np.sum(err ** 2))
    sst = float(np.sum((y_true - y_true.mean()) ** 2))
    return {
        "r2": 1.0 - sse / sst,
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err ** 2))),
        "mape": float(np.mean(np.abs(err) / y_true) * 100.0),
    }


# ----------------------------------------------------------------------
# baselines
# ----------------------------------------------------------------------

def naive_persistence(daily, test_idx):
    """Yesterday's value: the previous trading day's revenue."""
    rev = daily["revenue"].to_numpy()
    return np.array([rev[i - 1] for i in test_idx])


def _last_same_weekday_before(daily, i, upto=None):
    """Index of the most recent trading day before position i with the same
    weekday, searching only positions below `upto` (defaults to i)."""
    dow = daily["date"].dt.dayofweek.to_numpy()
    limit = i if upto is None else min(i, upto)
    j = limit - 1
    while j >= 0:
        if dow[j] == dow[i]:
            return j
        j -= 1
    raise ValueError("no earlier observation with the same weekday")


def seasonal_naive(daily, test_idx):
    """Same weekday last week: the most recent earlier trading day with the
    same weekday (seven days back unless a closure intervenes)."""
    rev = daily["revenue"].to_numpy()
    return np.array([rev[_last_same_weekday_before(daily, i)] for i in test_idx])


def historical_mean(daily, train_end, test_idx):
    """Fixed origin: the training mean repeated for every test day."""
    return np.full(len(test_idx), daily["revenue"].iloc[:train_end].mean())


def expanding_mean(daily, test_idx):
    """Rolling: the mean of every trading day observed before each test day."""
    rev = daily["revenue"].to_numpy()
    return np.array([rev[:i].mean() for i in test_idx])


def naive_flat(daily, train_end, test_idx):
    """Fixed origin: the last training day repeated for every test day."""
    return np.full(len(test_idx), daily["revenue"].iloc[train_end - 1])


def seasonal_naive_fixed(daily, train_end, test_idx):
    """Fixed origin: the last observed week of training repeated cyclically,
    matched by weekday."""
    rev = daily["revenue"].to_numpy()
    return np.array([rev[_last_same_weekday_before(daily, i, upto=train_end)]
                     for i in test_idx])


# ----------------------------------------------------------------------
# linear regression with day-of-week features
# ----------------------------------------------------------------------

def dow_design(dates, origin, with_trend=False):
    """One column per weekday (Monday to Sunday) plus, optionally, a linear
    trend in days since `origin`. No intercept: the seven dummies span it, and
    the fitted coefficients then read directly as weekday means."""
    dates = pd.to_datetime(pd.Series(dates)).reset_index(drop=True)
    X = pd.get_dummies(pd.Categorical(dates.dt.day_name(), categories=WEEKDAYS)).astype(float)
    if with_trend:
        X["trend"] = (dates - pd.Timestamp(origin)).dt.days.astype(float)
    return X.to_numpy()


def fit_linear(dates, y, origin, with_trend=False):
    from sklearn.linear_model import LinearRegression
    X = dow_design(dates, origin, with_trend)
    model = LinearRegression(fit_intercept=False)
    model.fit(X, np.asarray(y, dtype=float))
    return model


def linear_fixed(daily, train_end, test_idx, with_trend=False):
    origin = daily["date"].iloc[0]
    train = daily.iloc[:train_end]
    model = fit_linear(train["date"], train["revenue"], origin, with_trend)
    X_test = dow_design(daily["date"].iloc[test_idx], origin, with_trend)
    return model.predict(X_test), model


def linear_rolling(daily, test_idx, with_trend=False):
    """Refit on every trading day observed before each test day."""
    origin = daily["date"].iloc[0]
    preds = []
    for i in test_idx:
        hist = daily.iloc[:i]
        model = fit_linear(hist["date"], hist["revenue"], origin, with_trend)
        X = dow_design(daily["date"].iloc[[i]], origin, with_trend)
        preds.append(float(model.predict(X)[0]))
    return np.array(preds)


# ----------------------------------------------------------------------
# Prophet with weekly seasonality
# ----------------------------------------------------------------------

def _quiet_prophet():
    for name in ("prophet", "cmdstanpy"):
        logging.getLogger(name).setLevel(logging.WARNING)
        logging.getLogger(name).disabled = True


def fit_prophet(dates, y, **prophet_kwargs):
    from prophet import Prophet
    _quiet_prophet()
    np.random.seed(RANDOM_SEED)
    frame = pd.DataFrame({"ds": pd.to_datetime(pd.Series(dates)).values,
                          "y": np.asarray(y, dtype=float)})
    model = Prophet(yearly_seasonality=False, weekly_seasonality=True,
                    daily_seasonality=False, **prophet_kwargs)
    model.fit(frame)
    return model


def prophet_fixed(daily, train_end, test_idx, **prophet_kwargs):
    train = daily.iloc[:train_end]
    model = fit_prophet(train["date"], train["revenue"], **prophet_kwargs)
    future = pd.DataFrame({"ds": daily["date"].iloc[test_idx].values})
    forecast = model.predict(future)
    return forecast["yhat"].to_numpy(), model


def prophet_rolling(daily, test_idx, progress=None):
    """Refit Prophet on every trading day observed before each test day.
    Slow (one Stan fit per test day) but the only fair one-step comparison
    against the naive baselines."""
    preds = []
    for k, i in enumerate(test_idx):
        hist = daily.iloc[:i]
        model = fit_prophet(hist["date"], hist["revenue"])
        forecast = model.predict(pd.DataFrame({"ds": [daily["date"].iloc[i]]}))
        preds.append(float(forecast["yhat"].iloc[0]))
        if progress and (k + 1) % 10 == 0:
            progress(k + 1, len(test_idx))
    return np.array(preds)


def dashain_check(model, train):
    """Does the Prophet fit, told nothing about festivals, peak in Dashain?

    Looks at the fitted curve over the training days: the date of its
    maximum, the date of the trend component's maximum, and how the fitted
    mean inside the Dashain window compares with the fitted mean outside it.
    """
    fitted = model.predict(pd.DataFrame({"ds": train["date"].values}))
    fitted["ds"] = pd.to_datetime(fitted["ds"])
    lo, hi = pd.Timestamp(DASHAIN_WINDOW[0]), pd.Timestamp(DASHAIN_WINDOW[1])
    inside = fitted["ds"].between(lo, hi)
    actual = train.set_index("date")["revenue"]
    peak_fit = fitted.loc[fitted["yhat"].idxmax()]
    peak_trend = fitted.loc[fitted["trend"].idxmax()]
    return {
        "window": list(DASHAIN_WINDOW),
        "actual_peak_day": str(actual.idxmax().date()),
        "actual_peak_revenue": float(actual.max()),
        "fitted_peak_day": str(peak_fit["ds"].date()),
        "fitted_peak_value": float(peak_fit["yhat"]),
        "trend_peak_day": str(peak_trend["ds"].date()),
        "fitted_mean_inside_window": float(fitted.loc[inside, "yhat"].mean()),
        "fitted_mean_outside_window": float(fitted.loc[~inside, "yhat"].mean()),
        "actual_mean_inside_window": float(actual[inside.to_numpy()].mean()),
        "actual_mean_outside_window": float(actual[~inside.to_numpy()].mean()),
        "fitted_peak_inside_window": bool(lo <= peak_fit["ds"] <= hi),
        "trend_peak_inside_window": bool(lo <= peak_trend["ds"] <= hi),
    }


# ----------------------------------------------------------------------
# the study
# ----------------------------------------------------------------------

def run(daily, rolling_prophet=True, log=print):
    """Fit and score everything. Returns the summary dict."""
    n = len(daily)
    train, test = chronological_split(daily)
    train_end = len(train)
    test_idx = list(range(train_end, n))
    y_test = test["revenue"].to_numpy()

    log(f"Series: {n} trading days, {daily['date'].min().date()} to "
        f"{daily['date'].max().date()}")
    log(f"Split: train {len(train)} days ({train['date'].min().date()} to "
        f"{train['date'].max().date()}), test {len(test)} days "
        f"({test['date'].min().date()} to {test['date'].max().date()})")

    models = {}

    def score(key, name, framing, pred, extra=None):
        m = metrics(y_test, pred)
        m.update({"name": name, "framing": framing})
        if extra:
            m.update(extra)
        models[key] = m
        log(f"  {name:44} {framing:10} R2 {m['r2']:7.3f}  MAE {m['mae']:>10,.0f}  "
            f"MAPE {m['mape']:5.2f}%")
        return pred

    preds = {}
    log("\nFixed origin (forecast every test day from the end of training):")
    preds["naive_flat"] = score("naive_flat", "Naive flat (last training day repeated)",
                                "fixed", naive_flat(daily, train_end, test_idx))
    preds["historical_mean"] = score(
        "historical_mean", "Historical mean (training mean repeated)", "fixed",
        historical_mean(daily, train_end, test_idx))
    preds["seasonal_naive_fixed"] = score(
        "seasonal_naive_fixed", "Seasonal naive (last training week repeated)",
        "fixed", seasonal_naive_fixed(daily, train_end, test_idx))
    lr_pred, lr_model = linear_fixed(daily, train_end, test_idx)
    coefs = {d: float(c) for d, c in zip(WEEKDAYS, lr_model.coef_)}
    preds["linear_dow"] = score(
        "linear_dow", "Linear regression, day-of-week dummies", "fixed", lr_pred,
        {"weekday_coefficients": coefs,
         "highest_weekday": max(coefs, key=coefs.get),
         "lowest_weekday": min(coefs, key=coefs.get)})
    lrt_pred, lrt_model = linear_fixed(daily, train_end, test_idx, with_trend=True)
    preds["linear_dow_trend"] = score(
        "linear_dow_trend", "Linear regression, day-of-week plus trend", "fixed",
        lrt_pred, {"trend_per_day": float(lrt_model.coef_[-1])})
    pf_pred, pf_model = prophet_fixed(daily, train_end, test_idx)
    preds["prophet_weekly"] = score(
        "prophet_weekly", "Prophet, weekly seasonality", "fixed", pf_pred)

    log("\nRolling one step ahead (each test day from everything before it):")
    preds["naive_persistence"] = score(
        "naive_persistence", "Naive persistence (yesterday's value)", "rolling",
        naive_persistence(daily, test_idx))
    preds["expanding_mean"] = score(
        "expanding_mean", "Expanding mean (all days observed so far)", "rolling",
        expanding_mean(daily, test_idx))
    preds["seasonal_naive"] = score(
        "seasonal_naive", "Seasonal naive (same weekday last week)", "rolling",
        seasonal_naive(daily, test_idx))
    preds["linear_dow_rolling"] = score(
        "linear_dow_rolling", "Linear regression, day-of-week, refit daily",
        "rolling", linear_rolling(daily, test_idx))
    if rolling_prophet:
        pr = prophet_rolling(daily, test_idx,
                             progress=lambda k, m: log(f"    Prophet refit {k}/{m}"))
        preds["prophet_weekly_rolling"] = score(
            "prophet_weekly_rolling", "Prophet, weekly seasonality, refit daily",
            "rolling", pr, {"refits": len(test_idx)})

    # Day-of-week effects on the whole series and on the training days.
    def dow_table(frame):
        g = frame.groupby("day_of_week")["revenue"]
        return {d: {"mean_revenue": float(g.mean()[d]), "days": int(g.count()[d]),
                    "total_revenue": float(g.sum()[d])} for d in WEEKDAYS}

    dow_all = dow_table(daily)
    means = {d: v["mean_revenue"] for d, v in dow_all.items()}
    totals = {d: v["total_revenue"] for d, v in dow_all.items()}

    # Verdicts, stated as data.
    fixed_keys = ["naive_flat", "historical_mean", "seasonal_naive_fixed",
                  "linear_dow", "linear_dow_trend", "prophet_weekly"]
    rolling_keys = [k for k in ("naive_persistence", "expanding_mean", "seasonal_naive",
                                "linear_dow_rolling", "prophet_weekly_rolling")
                    if k in models]

    # Sensitivity, outside the main table: Prophet with a trend flexible
    # enough to chase a festival spike (changepoint_prior_scale 0.5 instead of
    # the default 0.05). Reported because it answers the Dashain question
    # fully: can Prophet see the peak at all at daily granularity, and what
    # does it cost out of sample when it does.
    pflex_pred, pflex_model = prophet_fixed(daily, train_end, test_idx,
                                            changepoint_prior_scale=0.5)
    flex_metrics = metrics(y_test, pflex_pred)
    flex_metrics.update({"name": "Prophet, weekly seasonality, flexible trend "
                                 "(changepoint_prior_scale 0.5)",
                         "framing": "fixed", "changepoint_prior_scale": 0.5,
                         "dashain": dashain_check(pflex_model, train)})
    log(f"  sensitivity: flexible-trend Prophet R2 {flex_metrics['r2']:.3f} "
        f"MAE {flex_metrics['mae']:,.0f} MAPE {flex_metrics['mape']:.2f}%")

    # Error structure: how much of the best fixed model's squared error the
    # two Nepali New Year days (13 and 14 April 2026) carry. Context only;
    # the headline metrics keep every day.
    anomalies = pd.to_datetime(["2026-04-13", "2026-04-14"])
    is_anom = test["date"].isin(anomalies).to_numpy()
    lr_err = y_test - preds["linear_dow"]
    error_structure = {
        "days": [str(d.date()) for d in anomalies],
        "what": "Nepali New Year eve and day: 83 transactions on the 13th, "
                "the busiest test day on the 14th",
        "share_of_linear_dow_sse_pct": float(
            np.sum(lr_err[is_anom] ** 2) / np.sum(lr_err ** 2) * 100),
        "linear_dow_mae_excluding_days": float(np.mean(np.abs(lr_err[~is_anom]))),
        "linear_dow_r2_excluding_days": float(
            1 - np.sum(lr_err[~is_anom] ** 2)
            / np.sum((y_test[~is_anom] - y_test[~is_anom].mean()) ** 2)),
    }

    def best(keys):
        return min(keys, key=lambda k: models[k]["mae"])

    def improvement(k, base):
        return {
            "mae_change_pct": round(
                (models[base]["mae"] - models[k]["mae"]) / models[base]["mae"] * 100, 2),
            "beats": bool(models[k]["mae"] < models[base]["mae"]),
        }

    verdict = {
        "fixed": {
            "best_model": best(fixed_keys),
            "vs_naive_flat": {k: improvement(k, "naive_flat")
                              for k in fixed_keys if k != "naive_flat"},
            "vs_historical_mean": {k: improvement(k, "historical_mean")
                                   for k in fixed_keys if k != "historical_mean"},
            "vs_seasonal_naive_fixed": {k: improvement(k, "seasonal_naive_fixed")
                                        for k in fixed_keys if k != "seasonal_naive_fixed"},
        },
        "rolling": {
            "best_model": best(rolling_keys),
            "vs_naive_persistence": {k: improvement(k, "naive_persistence")
                                     for k in rolling_keys if k != "naive_persistence"},
            "vs_expanding_mean": {k: improvement(k, "expanding_mean")
                                  for k in rolling_keys if k != "expanding_mean"},
            "vs_seasonal_naive": {k: improvement(k, "seasonal_naive")
                                  for k in rolling_keys if k != "seasonal_naive"},
        },
        "any_model_r2_positive_fixed": bool(any(models[k]["r2"] > 0 for k in fixed_keys)),
        "any_model_r2_positive_rolling": bool(any(models[k]["r2"] > 0 for k in rolling_keys)),
        "test_mean_revenue": float(y_test.mean()),
        "test_std_revenue": float(y_test.std(ddof=0)),
    }

    full = pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")
    missing = full.difference(daily["date"])

    summary = {
        "generated_from": os.path.relpath(CLEANED_CSV, _ROOT).replace("\\", "/"),
        "series": {
            "trading_days": int(n),
            "first_date": str(daily["date"].min().date()),
            "last_date": str(daily["date"].max().date()),
            "calendar_span_days": int(len(full)),
            "missing_days": [str(d.date()) for d in missing],
            "total_revenue": float(daily["revenue"].sum()),
            "mean_daily_revenue": float(daily["revenue"].mean()),
            "std_daily_revenue": float(daily["revenue"].std(ddof=0)),
        },
        "split": {
            "method": "chronological, first 80 per cent of trading days train",
            "test_fraction": TEST_FRACTION,
            "train_days": int(len(train)),
            "test_days": int(len(test)),
            "train_start": str(train["date"].min().date()),
            "train_end": str(train["date"].max().date()),
            "test_start": str(test["date"].min().date()),
            "test_end": str(test["date"].max().date()),
        },
        "day_of_week": {
            "by_weekday": dow_all,
            "highest_mean_revenue": max(means, key=means.get),
            "lowest_mean_revenue": min(means, key=means.get),
            "highest_total_revenue": max(totals, key=totals.get),
            "lowest_total_revenue": min(totals, key=totals.get),
        },
        "models": models,
        "verdict": verdict,
        "dashain": dashain_check(pf_model, train),
        "prophet_sensitivity": flex_metrics,
        "error_structure": error_structure,
        "prophet_settings": {"yearly_seasonality": False, "weekly_seasonality": True,
                             "daily_seasonality": False, "seasonality_mode": "additive",
                             "point_estimate": "MAP (deterministic)"},
        "random_seed": RANDOM_SEED,
    }
    return summary, preds, test


# ----------------------------------------------------------------------
# chart
# ----------------------------------------------------------------------

def draw_chart(daily, summary, preds, test, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    ink, muted, grid = "#1f1f1f", "#6b6b6b", "#e6e6e6"
    series = {  # fixed categorical order, never cycled
        "prophet_weekly": ("#2a78d6", "Prophet, weekly seasonality", "-"),
        "linear_dow": ("#eb6834", "Linear regression, day-of-week", "--"),
        "seasonal_naive_fixed": ("#1baf7a", "Seasonal naive, last week repeated", ":"),
        "naive_flat": ("#eda100", "Naive flat, last day repeated", "-."),
        "historical_mean": ("#8a8a8a", "Historical mean (training mean)", (0, (6, 3))),
        "prophet_weekly_rolling": ("#2a78d6", "Prophet, refit daily", "-"),
        "linear_dow_rolling": ("#eb6834", "Linear regression, refit daily", "--"),
        "seasonal_naive": ("#1baf7a", "Seasonal naive, same weekday last week", ":"),
        "naive_persistence": ("#eda100", "Naive persistence, yesterday", "-."),
        "expanding_mean": ("#8a8a8a", "Expanding mean", (0, (6, 3))),
    }

    fig, axes = plt.subplots(3, 1, figsize=(14, 13.5),
                             gridspec_kw={"height_ratios": [1.15, 1, 1]})
    m = 1_000_000.0
    split = summary["split"]
    test_start = pd.Timestamp(split["test_start"])

    ax = axes[0]
    ax.plot(daily["date"], daily["revenue"] / m, color=ink, linewidth=1.2,
            label="Actual daily revenue")
    ax.axvspan(test_start, daily["date"].max(), color=grid, alpha=0.6,
               label=f"Test window ({split['test_days']} days)")
    for d in summary["series"]["missing_days"]:
        ax.axvline(pd.Timestamp(d), color=muted, linewidth=0.8, linestyle=":")
    lo, hi = [pd.Timestamp(x) for x in summary["dashain"]["window"]]
    ax.axvspan(lo, hi, color="#2a78d6", alpha=0.10)
    ax.annotate("Dashain window\n(closed on Vijaya Dashami)",
                xy=(hi, daily["revenue"].max() / m), xytext=(12, -4),
                textcoords="offset points", fontsize=9, color=muted, va="top")
    ax.annotate("dotted lines: the four days with no sales",
                xy=(0.01, 0.97), xycoords="axes fraction", fontsize=8.5,
                color=muted, va="top")
    ax.set_title("Daily revenue, 17 July 2025 to 20 May 2026: 304 trading days, "
                 "chronological 80/20 split", fontsize=12, loc="left", color=ink)
    ax.set_ylabel("Revenue (Rs million)")
    ax.legend(loc="upper right", frameon=False, fontsize=9)

    def test_panel(ax, keys, title):
        ax.plot(test["date"], test["revenue"] / m, color=ink, linewidth=1.8,
                marker="o", markersize=3.5, label="Actual")
        for k in keys:
            if k not in preds:
                continue
            colour, label, style = series[k]
            mm = summary["models"][k]
            ax.plot(test["date"], preds[k] / m, color=colour, linewidth=1.6,
                    linestyle=style,
                    label=f"{label}  (MAE {mm['mae']/1000:,.0f}k, R2 {mm['r2']:.2f})")
        ax.set_title(title, fontsize=11, loc="left", color=ink)
        ax.set_ylabel("Revenue (Rs million)")
        ax.legend(loc="upper left", frameon=False, fontsize=8.5, ncol=1)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))

    test_panel(axes[1], ["naive_flat", "historical_mean", "seasonal_naive_fixed",
                         "linear_dow", "prophet_weekly"],
               "Fixed origin: every test day forecast from the end of training")
    test_panel(axes[2], ["naive_persistence", "expanding_mean", "seasonal_naive",
                         "linear_dow_rolling", "prophet_weekly_rolling"],
               "Rolling one step ahead: each test day from everything observed before it")

    for ax in axes:
        ax.grid(axis="y", color=grid, linewidth=0.8)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.spines["left"].set_color(muted)
        ax.spines["bottom"].set_color(muted)
        ax.tick_params(colors=muted, labelsize=9)
    fig.text(0.01, 0.005,
             "Chart 25. Daily models against daily naive baselines on the same 61 held-out days. "
             "Not comparable with the monthly errors in notebook 10.",
             fontsize=8.5, color=muted)
    fig.tight_layout(rect=(0, 0.015, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# ----------------------------------------------------------------------
# entry point
# ----------------------------------------------------------------------

def _serialisable(obj):
    if isinstance(obj, dict):
        return {k: _serialisable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialisable(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        return round(float(obj), 6)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    quick = "--quick" in argv
    t0 = time.time()
    daily = build_daily_series()
    series_path = write_daily_series(daily)
    print(f"Wrote {os.path.relpath(series_path, _ROOT)}")
    # Model the series exactly as the artifact stores it (revenue rounded to
    # the paisa). Prophet's optimiser is deterministic for identical input but
    # its stopping point moves at the fourth significant figure under
    # sub-paisa perturbations, so fitting the artifact values is what makes
    # every reported figure reproduce byte for byte from the artifact.
    daily = load_daily_series()
    summary, preds, test = run(daily, rolling_prophet=not quick)
    if quick:
        summary["note"] = "quick run: rolling Prophet refits skipped"
    os.makedirs(FIGURES_DIR, exist_ok=True)
    fig_path = draw_chart(daily, summary, preds, test, os.path.join(FIGURES_DIR, FIGURE_NAME))
    print(f"Wrote {os.path.relpath(fig_path, _ROOT)}")
    out_path = os.path.join(ARTIFACTS_DIR, SUMMARY_ARTIFACT)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(_serialisable(summary), fh, indent=2)
    print(f"Wrote {os.path.relpath(out_path, _ROOT)}")

    d = summary["dashain"]
    print("\nDashain check (Prophet fitted on training days, told nothing about festivals):")
    print(f"  actual peak day {d['actual_peak_day']}, fitted peak day {d['fitted_peak_day']}, "
          f"trend peak day {d['trend_peak_day']}")
    print(f"  fitted mean inside window Rs {d['fitted_mean_inside_window']:,.0f} vs outside "
          f"Rs {d['fitted_mean_outside_window']:,.0f}; actual Rs "
          f"{d['actual_mean_inside_window']:,.0f} vs Rs {d['actual_mean_outside_window']:,.0f}")
    dw = summary["day_of_week"]
    print(f"\nDay of week: highest mean {dw['highest_mean_revenue']}, lowest mean "
          f"{dw['lowest_mean_revenue']}; highest total {dw['highest_total_revenue']}, "
          f"lowest total {dw['lowest_total_revenue']}")
    print(f"({time.time() - t0:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
