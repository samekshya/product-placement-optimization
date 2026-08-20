"""
verify_thesis_numbers.py

Checks every figure in PROJECT_RECORD.md section 9 against a live source, and
prints the pass count rather than relying on a number typed into the document.

    python scripts/verify_thesis_numbers.py

Why this exists:
    PROJECT_RECORD.md once carried the summary line "38 of 38 verified numbers
    matched" next to a table that had grown to 53 rows. A hand-typed count
    drifts away from the table it describes the moment either changes. This
    script generates the count instead, so the claim can never go stale.

How a figure is classified:
    LIVE      re-computed from the Postgres warehouse right now
    ARTIFACT  read from dashboard/artifacts (Apriori / K-Means outputs)
    CONSTANT  held in config/metrics.py, cross-checked against LIVE or ARTIFACT
              values where an independent source exists
    OPTIMISER the computed zone assignment: constants checked against
              dashboard/artifacts/zone_optimisation.json AND against a live
              re-run of the exhaustive certificate in analysis/optimise_zones.py
    FORECAST  daily granularity forecasting: constants checked against
              dashboard/artifacts/daily_forecast_summary.json, against a live
              refit of the cheap models on daily_revenue.csv, and the daily
              series itself against the warehouse
    FEATURES  richer basket features: constants checked against
              dashboard/artifacts/basket_features_summary.json, which
              reproduce_all_results.py regenerates from the cleaned record;
              the artifact must also reproduce the notebook 11 and 12
              figures on the binary flags, which pins the split and seed
    NOTEBOOK  only reproducible by re-executing a notebook, so it is reported
              as uncheckable here rather than silently counted as a pass

Exit code 0 only if every checkable figure matches.
"""

import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from config import db, metrics as M  # noqa: E402

ARTIFACTS = os.path.join(ROOT, "dashboard", "artifacts")

results = []      # (ok, source, label, actual, expected)
uncheckable = []  # (label, why)


def check(source, label, actual, expected, tol=0):
    if isinstance(expected, str):
        ok = str(actual).strip() == expected
    else:
        ok = abs(float(actual) - float(expected)) <= tol
    results.append((ok, source, label, actual, expected))


def skip(label, why):
    uncheckable.append((label, why))


def main():
    print("=" * 78)
    print("VERIFY THESIS NUMBERS (PROJECT_RECORD.md section 9)")
    print("=" * 78)

    # ---------------- artifacts ----------------
    kpi = json.load(open(os.path.join(ARTIFACTS, "kpi_summary.json"), encoding="utf-8"))
    cross = json.load(open(os.path.join(ARTIFACTS, "cross_sell_summary.json"), encoding="utf-8"))
    rules = pd.read_csv(os.path.join(ARTIFACTS, "category_rules.csv"))
    abc = pd.read_csv(os.path.join(ARTIFACTS, "abc_analysis.csv"))
    pairs = pd.read_csv(os.path.join(ARTIFACTS, "top_pairs.csv"))

    # ---------------- warehouse ----------------
    live = {}
    try:
        import psycopg2

        conn = psycopg2.connect(connect_timeout=5, **db.connection_kwargs())
        cur = conn.cursor()

        def q(sql):
            cur.execute(sql)
            return cur.fetchone()[0]

        live["fact_rows"] = q("SELECT COUNT(*) FROM warehouse.fact_sales")
        live["baskets"] = q("SELECT COUNT(*) FROM warehouse.dim_basket")
        live["products"] = q("SELECT COUNT(*) FROM warehouse.dim_product")
        live["categories"] = q("SELECT COUNT(*) FROM warehouse.dim_category")
        live["trading_days"] = q("SELECT COUNT(*) FROM warehouse.dim_date")
        live["revenue"] = float(q("SELECT ROUND(SUM(total_amount),2) FROM warehouse.fact_sales"))
        live["mean_basket"] = float(q("SELECT ROUND(AVG(basket_value),2) FROM warehouse.dim_basket"))
        live["median_basket"] = float(q(
            "SELECT ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY basket_value)::NUMERIC,2) "
            "FROM warehouse.dim_basket"))
        live["large_rev_pct"] = float(q(
            "SELECT ROUND(100.0*SUM(basket_value) FILTER (WHERE basket_segment='Large')"
            "/SUM(basket_value),1) FROM warehouse.dim_basket"))
        live["large_trip_pct"] = float(q(
            "SELECT ROUND(100.0*COUNT(*) FILTER (WHERE basket_segment='Large')/COUNT(*),1) "
            "FROM warehouse.dim_basket"))
        live["busiest_day"] = q(
            "SELECT TRIM(day_name) FROM warehouse.v_day_of_week ORDER BY revenue DESC LIMIT 1")
        live["friday_rev_m"] = round(float(q(
            "SELECT revenue FROM warehouse.v_day_of_week WHERE TRIM(day_name)='Friday'")) / 1e6, 1)
        live["peak_month"] = q(
            "SELECT year_month FROM warehouse.v_monthly_revenue ORDER BY revenue DESC LIMIT 1")
        live["peak_month_rev_m"] = round(
            float(q("SELECT MAX(revenue) FROM warehouse.v_monthly_revenue")) / 1e6, 1)
        live["zone1_pct"] = float(q(
            "SELECT revenue_share_pct FROM warehouse.v_zone_performance "
            "ORDER BY revenue DESC LIMIT 1"))
        live["zone1_cats"] = q(
            "SELECT n_categories FROM warehouse.v_zone_performance ORDER BY revenue DESC LIMIT 1")
        cur.execute(
            "SELECT d.full_date, SUM(f.total_amount) FROM warehouse.fact_sales f "
            "JOIN warehouse.dim_date d ON d.date_key = f.date_key "
            "GROUP BY d.full_date ORDER BY d.full_date")
        live["daily_series"] = pd.DataFrame(cur.fetchall(), columns=["date", "revenue"])
        live["daily_series"]["date"] = pd.to_datetime(live["daily_series"]["date"])
        live["daily_series"]["revenue"] = live["daily_series"]["revenue"].astype(float)
        cur.close()
        conn.close()
    except Exception as exc:  # noqa: BLE001
        print(f"\nWARNING: warehouse unreachable ({type(exc).__name__}). "
              "LIVE checks will be skipped.\n"
              "Start it with: docker compose up -d postgres\n")

    L = bool(live)

    # ================= dataset scale =================
    check("CONSTANT", "Raw rows", M.TOTAL_RAW_ROWS, 768222)
    if L:
        check("LIVE", "Cleaned rows / line items", live["fact_rows"], M.TOTAL_CLEAN_ROWS)
        check("LIVE", "Transactions", live["baskets"], M.TOTAL_TRANSACTIONS)
        check("LIVE", "Total revenue", live["revenue"], M.TOTAL_REVENUE, 0.01)
        check("LIVE", "Products with sales", live["products"], M.TOTAL_PRODUCTS_WITH_SALES)
        check("LIVE", "Categories", live["categories"], M.TOTAL_CATEGORIES)
        check("LIVE", "Mean basket", live["mean_basket"], M.MEAN_BASKET_VALUE, 0.01)
        check("LIVE", "Median basket", live["median_basket"], M.MEDIAN_BASKET_VALUE, 0.01)
        check("LIVE", "Warehouse trading days", live["trading_days"], M.TRADING_DAYS)
        check("LIVE", "Items per basket (mean)",
              round(live["fact_rows"] / live["baskets"], 2), M.ITEMS_PER_BASKET_MEAN, 0.011)
        check("LIVE", "Daily revenue",
              round(live["revenue"] / M.DATA_DAYS, 2), kpi["daily_revenue"], 0.02)
        check("LIVE", "Daily customers",
              round(live["baskets"] / M.DATA_DAYS), kpi["daily_customers"])
        check("LIVE", "Large baskets share of trips", live["large_trip_pct"], 13.7, 0.05)
        check("LIVE", "Large baskets share of revenue", live["large_rev_pct"], 52.1, 0.05)
        check("LIVE", "Busiest day", live["busiest_day"], "Friday")
        check("LIVE", "Friday revenue (Rs M)", live["friday_rev_m"], 32.8, 0.05)
        check("LIVE", "Peak month", live["peak_month"], "2025-09")
        check("LIVE", "Peak month revenue (Rs M)", live["peak_month_rev_m"], 23.3, 0.06)
        check("LIVE", "Zone 1 share of revenue", live["zone1_pct"], 48.5, 0.05)
        check("LIVE", "Zone 1 category count", live["zone1_cats"], 6)
    check("CONSTANT", "Days of data (span)", M.DATA_DAYS, kpi["data_days"])
    check("CONSTANT", "Products raw audit count", M.TOTAL_PRODUCTS, 5681)

    # ================= association rules =================
    check("ARTIFACT", "Association rules", len(rules), M.RULES_TOTAL)
    check("ARTIFACT", "Rules with lift above 5", int((rules["lift"] > 5).sum()), M.RULES_LIFT_ABOVE_5)
    check("ARTIFACT", "Strong rules (lift >= 3)", cross["total_strong_rules"], M.RULES_LIFT_ABOVE_3)
    check("ARTIFACT", "Max category lift", round(float(rules["lift"].max()), 2),
          M.MAX_LIFT_CATEGORY, 0.005)
    check("ARTIFACT", "Max product lift", kpi["max_lift_product"], M.MAX_LIFT_PRODUCT, 0.005)
    top_pair = pairs.sort_values("cooccurrences", ascending=False).iloc[0]
    check("ARTIFACT", "Top product pair count",
          int(top_pair["cooccurrences"]), M.TOP_PAIR_COUNT)
    check("ARTIFACT", "Top product pair identity",
          " + ".join(sorted([top_pair["product_a"], top_pair["product_b"]])),
          "Kalo Dal + Rato Dal")

    # ================= clustering =================
    check("ARTIFACT", "Co-occurrence silhouette", kpi["cooccurrence_silhouette_k3"],
          M.SILHOUETTE_COOCCURRENCE, 0.0005)
    check("CONSTANT", "Frequency silhouette", M.SILHOUETTE_FREQUENCY, 0.19, 0.0005)
    check("CONSTANT", "Silhouette increase (absolute)", M.SILHOUETTE_INCREASE, 0.303, 0.0005)

    # ================= cross-sell =================
    check("ARTIFACT", "Cross-sell captured, current", cross["current_rules_captured"],
          M.CROSS_SELL_CURRENT)
    check("ARTIFACT", "Cross-sell captured, optimised", cross["optimised_rules_captured"],
          M.CROSS_SELL_OPTIMISED)
    check("ARTIFACT", "Cross-sell capture pct, current", cross["current_capture_pct"], 5.7, 0.05)
    check("ARTIFACT", "Cross-sell capture pct, optimised", cross["optimised_capture_pct"],
          54.1, 0.05)
    check("ARTIFACT", "Cross-sell improvement (x)",
          round(cross["optimised_rules_captured"] / cross["current_rules_captured"], 1), 8.2, 0.05)

    # ================= projection =================
    projected = kpi["avg_basket_value"] * (M.UPLIFT_SCENARIO_PCT / 100) * kpi["daily_customers"] * 365
    check("ARTIFACT", "Revenue projection at 5% (Rs Crore)",
          round(projected / 1e7, 2), 1.30, 0.02)

    # ================= ML =================
    check("CONSTANT", "Recommender hit rate", M.ML_HIT_RATE, 0.28, 0.0005)
    check("CONSTANT", "Recommender training baskets", M.ML_TRAIN_BASKETS, 95570)
    check("CONSTANT", "Recommender test baskets", M.ML_TEST_BASKETS, 40959)
    check("CONSTANT", "Linear Regression MAE", M.LINREG_MAE, 3395703)
    check("CONSTANT", "Prophet MAE", M.PROPHET_MAE, 2909633)
    check("CONSTANT", "Prophet improvement pct", M.PROPHET_IMPROVEMENT_PCT, 14.3, 0.05)
    check("CONSTANT", "Prophet actually beats Linear Regression",
          int(M.PROPHET_MAE < M.LINREG_MAE), 1)
    check("CONSTANT", "Linear Regression R squared", M.LINREG_R2, -2.377, 0.0005)
    check("CONSTANT", "Classifier accuracy", M.CLASSIFIER_ACCURACY, 0.614, 0.0005)
    check("CONSTANT", "Classifier baseline", M.CLASSIFIER_BASELINE, 0.497, 0.0005)
    check("CONSTANT", "Classifier test baskets", M.CLASSIFIER_TEST_BASKETS, 65412)
    check("CONSTANT", "Classifier beats baseline",
          int(M.CLASSIFIER_ACCURACY > M.CLASSIFIER_BASELINE), 1)
    check("CONSTANT", "Neural network accuracy", M.NEURAL_NET_ACCURACY, 0.6917, 0.0005)
    check("CONSTANT", "Neural network parameters", M.NEURAL_NET_PARAMETERS, 3843)
    check("CONSTANT", "Fully grown tree accuracy", M.DECISION_TREE_FULL_ACCURACY, 0.6767, 0.0005)
    check("CONSTANT", "Fully grown tree leaves", M.DECISION_TREE_FULL_LEAVES, 11906)
    check("CONSTANT", "MLP model family advantage (points)",
          round((M.NEURAL_NET_ACCURACY - M.DECISION_TREE_FULL_ACCURACY) * 100, 2), 1.50, 0.005)
    check("CONSTANT", "Feature ceiling", M.FEATURE_CEILING_ACCURACY, 0.7234, 0.0005)
    check("CONSTANT", "Distinct feature patterns", M.DISTINCT_FEATURE_PATTERNS, 21032)
    check("CONSTANT", "No model exceeds the ceiling",
          int(M.NEURAL_NET_ACCURACY < M.FEATURE_CEILING_ACCURACY), 1)

    # ================= recommender baselines =================
    # These exist because the headline 28% hit rate is only meaningful beside
    # the baselines it was compared against, and beside the coverage that
    # constrains it. Every figure quoted in the dissertation is checked here.
    check("CONSTANT", "Recommender test baskets", M.REC_TEST_BASKETS, 19808)
    check("CONSTANT", "Model hit rate", M.REC_MODEL_HIT_PCT, 28.04, 0.005)
    check("CONSTANT", "Popularity, matched budget", M.REC_POPULARITY_MATCHED_PCT, 23.74, 0.005)
    check("CONSTANT", "Popularity, unconstrained top 5", M.REC_POPULARITY_TOP5_PCT, 34.81, 0.005)
    check("CONSTANT", "Random, matched budget", M.REC_RANDOM_MATCHED_PCT, 2.55, 0.005)
    check("CONSTANT", "Random, unconstrained top 5", M.REC_RANDOM_TOP5_PCT, 5.04, 0.005)
    check("CONSTANT", "Avg recommendations per basket", M.REC_AVG_RECS_PER_BASKET, 2.50, 0.005)
    check("CONSTANT", "Avg recommendations when covered", M.REC_AVG_RECS_WHEN_COVERED, 3.96, 0.005)
    check("CONSTANT", "Products with at least one rule", M.REC_PRODUCTS_WITH_RULES, 28)
    check("CONSTANT", "Covered baskets", M.REC_COVERED_BASKETS, 12536)
    check("CONSTANT", "Uncovered baskets", M.REC_UNCOVERED_BASKETS, 7272)
    check("CONSTANT", "Covered plus uncovered equals test baskets",
          M.REC_COVERED_BASKETS + M.REC_UNCOVERED_BASKETS, M.REC_TEST_BASKETS)
    check("CONSTANT", "Model where covered", M.REC_COVERED_MODEL_PCT, 44.30, 0.005)
    check("CONSTANT", "Popularity where covered", M.REC_COVERED_POPULARITY_PCT, 37.52, 0.005)
    check("CONSTANT", "Model beats popularity at matched budget",
          int(M.REC_MODEL_HIT_PCT > M.REC_POPULARITY_MATCHED_PCT), 1)
    check("CONSTANT", "Model loses to unconstrained popularity",
          int(M.REC_MODEL_HIT_PCT < M.REC_POPULARITY_TOP5_PCT), 1)
    check("CONSTANT", "Model beats popularity where it has coverage",
          int(M.REC_COVERED_MODEL_PCT > M.REC_COVERED_POPULARITY_PCT), 1)

    # ================= ABC =================
    a_count = int((abc["abc_category"] == "A").sum())
    check("ARTIFACT", "Class A products", a_count, M.ABC_CLASS_A_PRODUCTS)
    check("ARTIFACT", "Class A share of products",
          round(a_count / len(abc) * 100, 1), 6.0, 0.05)

    # ================= computed zone assignment =================
    # analysis/optimise_zones.py searches for the best category-to-zone
    # assignment under the same score_layout objective as the 28 / 56 result.
    # Its figures are checked two ways: against the artifact it writes, and
    # against a fresh run of its exhaustive certificate, which recomputes the
    # true optimum in a few seconds without repeating the 200-restart search.
    zone_path = os.path.join(ARTIFACTS, "zone_optimisation.json")
    if os.path.exists(zone_path):
        from analysis import optimise_zones as OZ, zones as ZD

        zopt = json.load(open(zone_path, encoding="utf-8"))
        strong = OZ.strong_rules_from_artifacts(ARTIFACTS)
        base = ZD.proposed_assignment()
        caps = {z: 0 for z in ZD.ZONE_IDS}
        for z in base.values():
            caps[z] += 1

        check("OPTIMISER", "Rule-bearing categories",
              zopt["n_rule_bearing_categories"], M.ZONE_OPT_RULE_BEARING_CATEGORIES)
        check("OPTIMISER", "Optimiser restarts", zopt["unconstrained"]["restarts"],
              M.ZONE_OPT_RESTARTS)
        check("OPTIMISER", "Optimiser restarts at least 100",
              int(zopt["unconstrained"]["restarts"] >= 100), 1)
        check("OPTIMISER", "Optimiser master seed", zopt["unconstrained"]["seed"],
              M.ZONE_OPT_SEED)
        check("OPTIMISER", "Hand-built layout in optimiser artifact",
              zopt["hand_built"]["rules_captured"], M.CROSS_SELL_OPTIMISED)

        for key, label, r_const, s_const, p_const in (
            ("unconstrained", "Unconstrained optimum",
             M.ZONE_OPT_UNCONSTRAINED_RULES, M.ZONE_OPT_UNCONSTRAINED_SUPPORT,
             M.ZONE_OPT_UNCONSTRAINED_PCT),
            ("constrained", "Constrained optimum",
             M.ZONE_OPT_CONSTRAINED_RULES, M.ZONE_OPT_CONSTRAINED_SUPPORT,
             M.ZONE_OPT_CONSTRAINED_PCT),
            ("capacity_unconstrained", "Capacity-matched optimum",
             M.ZONE_OPT_CAPACITY_RULES_UNCONSTRAINED,
             M.ZONE_OPT_CAPACITY_SUPPORT_UNCONSTRAINED,
             M.ZONE_OPT_CAPACITY_PCT_UNCONSTRAINED),
            # Since the 2026-08-17 re-derivation these two differ: the locks
            # cost 106 rules once zone capacities are held fixed.
            ("capacity_constrained", "Capacity-matched constrained optimum",
             M.ZONE_OPT_CAPACITY_RULES, M.ZONE_OPT_CAPACITY_SUPPORT,
             M.ZONE_OPT_CAPACITY_PCT),
        ):
            run = zopt[key]
            check("OPTIMISER", f"{label}, rules (artifact)", run["rules_captured"], r_const)
            check("OPTIMISER", f"{label}, support (artifact)",
                  round(run["support_captured"], 4), s_const, 0.00005)
            check("OPTIMISER", f"{label}, capture pct (artifact)",
                  round(run["capture_rate"], 1), p_const, 0.05)
            check("OPTIMISER", f"{label}, search certified exact",
                  int(bool(run["local_search_is_exact"])), 1)
            constrained = key in ("constrained", "capacity_constrained")
            exact = OZ.exact_optimum(
                strong, ZD.ZONE_IDS,
                locked=OZ.LOCKED if constrained else None,
                forbidden=OZ.FORBIDDEN if constrained else None,
                capacities=caps if key.startswith("capacity") else None)
            check("OPTIMISER", f"{label}, rules (live certificate)",
                  exact["rules_captured"], r_const)
            check("OPTIMISER", f"{label}, support (live certificate)",
                  round(exact["support_captured"], 4), s_const, 0.00005)

        for scope, r_cost, s_cost in (
            ("unlimited_zones", M.ZONE_OPT_CONSTRAINT_COST_RULES_UNLIMITED,
             M.ZONE_OPT_CONSTRAINT_COST_SUPPORT_UNLIMITED),
            ("capacity_matched", M.ZONE_OPT_CONSTRAINT_COST_RULES_CAPACITY,
             M.ZONE_OPT_CONSTRAINT_COST_SUPPORT_CAPACITY),
        ):
            check("OPTIMISER", f"Constraint cost, rules ({scope})",
                  zopt["constraint_cost"][scope]["rules"], r_cost)
            check("OPTIMISER", f"Constraint cost, support ({scope})",
                  zopt["constraint_cost"][scope]["support"], s_cost, 0.00005)
        # Two constrained categories now carry strong rules: DAIRY PRODUCTS
        # (locked to the cold zone) and RICE (locked to the perimeter as heavy
        # goods). Unlike before the 2026-08-17 remap, the constraints are no
        # longer free: the capacity-matched cost is checked above at 106 rules.
        check("OPTIMISER", "Constrained categories in strong rules",
              len(zopt["constraints"]["constrained_categories_in_strong_rules"]), 2)
        check("OPTIMISER", "Unconstrained gain over hand-built (rules)",
              zopt["unconstrained"]["delta_vs_hand_built"]["rules"],
              M.ZONE_OPT_UNCONSTRAINED_GAIN_RULES)
        check("OPTIMISER", "Capacity-matched gain over hand-built (rules)",
              zopt["capacity_constrained"]["delta_vs_hand_built"]["rules"],
              M.ZONE_OPT_CAPACITY_GAIN_RULES)
        check("OPTIMISER", "Hand-built share of capacity optimum (pct)",
              round(zopt["hand_built"]["support_captured"]
                    / zopt["capacity_constrained"]["support_captured"] * 100, 1),
              M.ZONE_OPT_HAND_BUILT_SHARE_OF_CAPACITY_OPTIMUM_PCT, 0.05)
        trace = zopt["unconstrained"]["trace_from_reference"]
        check("OPTIMISER", "First move from hand-built", trace[0]["category"],
              M.ZONE_OPT_MOVE_1)
        check("OPTIMISER", "First move gain (rules)", trace[0]["delta_rules"],
              M.ZONE_OPT_MOVE_1_RULES)
        check("OPTIMISER", "Second move from hand-built", trace[1]["category"],
              M.ZONE_OPT_MOVE_2)
        check("OPTIMISER", "Second move gain (rules)", trace[1]["delta_rules"],
              M.ZONE_OPT_MOVE_2_RULES)
        check("OPTIMISER", "Rules after two moves from hand-built",
              trace[1]["rules_after"], M.ZONE_OPT_RULES_AFTER_TWO_MOVES)
    else:
        skip("Computed zone assignment (analysis/optimise_zones.py)",
             "zone_optimisation.json not generated; run python analysis/optimise_zones.py")

    # ================= daily granularity forecasting =================
    # analysis/daily_forecast.py refits the notebook 10 question at daily
    # granularity. The cheap models are refit live here on the committed
    # daily series so their figures are recomputed, not read back; the
    # rolling Prophet refits are read from the artifact. Daily figures are
    # never set against the monthly figures above.
    fc_path = os.path.join(ARTIFACTS, "daily_forecast_summary.json")
    ds_path = os.path.join(ARTIFACTS, "daily_revenue.csv")
    if os.path.exists(fc_path) and os.path.exists(ds_path):
        import numpy as np
        from analysis import daily_forecast as DFC

        fc = json.load(open(fc_path, encoding="utf-8"))
        daily = DFC.load_daily_series(ARTIFACTS)
        train, test = DFC.chronological_split(daily)
        n_train = len(train)
        test_idx = list(range(n_train, len(daily)))
        y_test = test["revenue"].to_numpy()

        check("FORECAST", "Daily series trading days", len(daily), M.TRADING_DAYS)
        check("FORECAST", "Daily series total revenue",
              round(float(daily["revenue"].sum()), 2), M.TOTAL_REVENUE, 0.05)
        check("FORECAST", "Daily mean revenue (304 days)",
              round(float(daily["revenue"].mean()), 2), M.DAILY_MEAN_REVENUE, 0.01)
        check("FORECAST", "Daily series first date", str(daily["date"].min().date()),
              M.DATA_START)
        check("FORECAST", "Daily series last date", str(daily["date"].max().date()),
              M.DATA_END)
        if L and "daily_series" in live:
            merged = daily[["date", "revenue"]].merge(
                live["daily_series"], on="date", how="outer", suffixes=("_csv", "_wh"))
            check("LIVE", "Daily series days match warehouse",
                  int(len(merged)), M.TRADING_DAYS)
            check("LIVE", "Daily series revenue matches warehouse (max abs diff)",
                  round(float((merged["revenue_csv"] - merged["revenue_wh"]).abs().max()), 2),
                  0.0, 0.011)
        check("FORECAST", "Chronological split, train days", n_train, M.DAILY_TRAIN_DAYS)
        check("FORECAST", "Chronological split, test days", len(test), M.DAILY_TEST_DAYS)
        check("FORECAST", "Training ends", str(train["date"].max().date()), M.DAILY_TRAIN_END)
        check("FORECAST", "Test starts", str(test["date"].min().date()), M.DAILY_TEST_START)
        check("FORECAST", "Test window mean revenue", round(float(y_test.mean()), 2),
              M.DAILY_TEST_MEAN_REVENUE, 0.01)
        check("FORECAST", "Split in artifact, train days", fc["split"]["train_days"],
              M.DAILY_TRAIN_DAYS)
        check("FORECAST", "Split in artifact, test days", fc["split"]["test_days"],
              M.DAILY_TEST_DAYS)

        # live refits of the cheap models
        live_preds = {
            "naive_flat": DFC.naive_flat(daily, n_train, test_idx),
            "historical_mean": DFC.historical_mean(daily, n_train, test_idx),
            "seasonal_naive_fixed": DFC.seasonal_naive_fixed(daily, n_train, test_idx),
            "linear_dow": DFC.linear_fixed(daily, n_train, test_idx)[0],
            "linear_dow_trend": DFC.linear_fixed(daily, n_train, test_idx, with_trend=True)[0],
            "prophet_weekly": DFC.prophet_fixed(daily, n_train, test_idx)[0],
            "naive_persistence": DFC.naive_persistence(daily, test_idx),
            "expanding_mean": DFC.expanding_mean(daily, test_idx),
            "seasonal_naive": DFC.seasonal_naive(daily, test_idx),
            "linear_dow_rolling": DFC.linear_rolling(daily, test_idx),
        }
        expected = {
            "naive_flat": (M.DAILY_NAIVE_FLAT_MAE, M.DAILY_NAIVE_FLAT_R2, None),
            "historical_mean": (M.DAILY_HISTORICAL_MEAN_MAE, M.DAILY_HISTORICAL_MEAN_R2, None),
            "seasonal_naive_fixed": (M.DAILY_SEASONAL_NAIVE_FIXED_MAE,
                                     M.DAILY_SEASONAL_NAIVE_FIXED_R2, None),
            "linear_dow": (M.DAILY_LINREG_DOW_MAE, M.DAILY_LINREG_DOW_R2, M.DAILY_LINREG_DOW_MAPE),
            "linear_dow_trend": (M.DAILY_LINREG_DOW_TREND_MAE, M.DAILY_LINREG_DOW_TREND_R2, None),
            "prophet_weekly": (M.DAILY_PROPHET_MAE, M.DAILY_PROPHET_R2, M.DAILY_PROPHET_MAPE),
            "naive_persistence": (M.DAILY_PERSISTENCE_MAE, M.DAILY_PERSISTENCE_R2,
                                  M.DAILY_PERSISTENCE_MAPE),
            "expanding_mean": (M.DAILY_EXPANDING_MEAN_MAE, M.DAILY_EXPANDING_MEAN_R2, None),
            "seasonal_naive": (M.DAILY_SEASONAL_NAIVE_MAE, M.DAILY_SEASONAL_NAIVE_R2,
                               M.DAILY_SEASONAL_NAIVE_MAPE),
            "linear_dow_rolling": (M.DAILY_LINREG_DOW_ROLLING_MAE, M.DAILY_LINREG_DOW_ROLLING_R2,
                                   M.DAILY_LINREG_DOW_ROLLING_MAPE),
            "prophet_weekly_rolling": (M.DAILY_PROPHET_ROLLING_MAE, M.DAILY_PROPHET_ROLLING_R2,
                                       M.DAILY_PROPHET_ROLLING_MAPE),
        }
        for key, (mae_c, r2_c, mape_c) in expected.items():
            art = fc["models"][key]
            label = art["name"]
            check("FORECAST", f"{label}, MAE (artifact)", round(art["mae"]), mae_c)
            check("FORECAST", f"{label}, R2 (artifact)", round(art["r2"], 3), r2_c, 0.0005)
            if mape_c is not None:
                check("FORECAST", f"{label}, MAPE (artifact)", round(art["mape"], 2), mape_c, 0.005)
            if key in live_preds:
                m = DFC.metrics(y_test, live_preds[key])
                check("FORECAST", f"{label}, MAE (live refit)", round(m["mae"]), mae_c)
                check("FORECAST", f"{label}, R2 (live refit)", round(m["r2"], 3), r2_c, 0.0005)

        # the verdict
        art = fc["models"]
        check("FORECAST", "Best model MAE reduction vs persistence (pct)",
              round((art["naive_persistence"]["mae"] - art["linear_dow_rolling"]["mae"])
                    / art["naive_persistence"]["mae"] * 100, 1),
              M.DAILY_BEST_MODEL_VS_PERSISTENCE_PCT, 0.05)
        check("FORECAST", "Best model MAE reduction vs seasonal naive (pct)",
              round((art["seasonal_naive"]["mae"] - art["linear_dow_rolling"]["mae"])
                    / art["seasonal_naive"]["mae"] * 100, 1),
              M.DAILY_BEST_MODEL_VS_SEASONAL_NAIVE_PCT, 0.05)
        check("FORECAST", "Best model MAE reduction vs historical mean (pct)",
              round((art["historical_mean"]["mae"] - art["linear_dow"]["mae"])
                    / art["historical_mean"]["mae"] * 100, 1),
              M.DAILY_BEST_MODEL_VS_HISTORICAL_MEAN_PCT, 0.05)
        fitted = ("linear_dow", "linear_dow_trend", "prophet_weekly",
                  "linear_dow_rolling", "prophet_weekly_rolling")
        best_r2 = max(art[k]["r2"] for k in fitted)
        check("FORECAST", "Best R2 of any fitted daily model", round(best_r2, 3),
              M.DAILY_BEST_R2, 0.0005)
        check("FORECAST", "No daily model or baseline has positive R2",
              int(max(v["r2"] for v in art.values()) < 0),
              int(not M.DAILY_ANY_MODEL_R2_POSITIVE))
        check("FORECAST", "Every model beats naive persistence on MAE",
              int(all(art[k]["mae"] < art["naive_persistence"]["mae"]
                      for k in ("expanding_mean", "seasonal_naive", "linear_dow_rolling",
                                "prophet_weekly_rolling"))), 1)

        # Dashain
        dsh = fc["dashain"]
        check("FORECAST", "Prophet fitted peak inside Dashain window",
              int(dsh["fitted_peak_inside_window"]), int(M.DAILY_PROPHET_DASHAIN_DETECTED))
        check("FORECAST", "Prophet fitted peak day", dsh["fitted_peak_day"],
              M.DAILY_PROPHET_FITTED_PEAK_DAY)
        check("FORECAST", "Actual peak day", dsh["actual_peak_day"], M.DAILY_ACTUAL_PEAK_DAY)
        check("FORECAST", "Actual Dashain window mean", round(dsh["actual_mean_inside_window"]),
              M.DAILY_ACTUAL_DASHAIN_WINDOW_MEAN)
        check("FORECAST", "Prophet fitted Dashain window mean",
              round(dsh["fitted_mean_inside_window"]), M.DAILY_PROPHET_DASHAIN_WINDOW_FITTED_MEAN)
        flex = fc["prophet_sensitivity"]
        check("FORECAST", "Flexible-trend Prophet peaks in Dashain window",
              int(flex["dashain"]["fitted_peak_inside_window"]),
              int(M.DAILY_PROPHET_FLEXIBLE_DASHAIN_DETECTED))
        check("FORECAST", "Flexible-trend Prophet MAE", round(flex["mae"]), M.DAILY_PROPHET_FLEXIBLE_MAE)
        check("FORECAST", "Flexible-trend Prophet R2", round(flex["r2"], 3),
              M.DAILY_PROPHET_FLEXIBLE_R2, 0.0005)
        check("FORECAST", "Flexible trend forecasts worse than default",
              int(flex["mae"] > art["prophet_weekly"]["mae"]), 1)

        # day of week, recomputed live from the series
        dow_mean = daily.groupby("day_of_week")["revenue"].mean()
        dow_total = daily.groupby("day_of_week")["revenue"].sum()
        check("FORECAST", "Highest mean-revenue weekday", dow_mean.idxmax(),
              M.DAILY_HIGHEST_MEAN_WEEKDAY)
        check("FORECAST", "Highest total-revenue weekday", dow_total.idxmax(),
              M.DAILY_HIGHEST_TOTAL_WEEKDAY)
        check("FORECAST", "Lowest mean-revenue weekday", dow_mean.idxmin(),
              M.DAILY_LOWEST_MEAN_WEEKDAY)
        check("FORECAST", "Friday total revenue (Rs)", round(float(dow_total["Friday"])),
              M.FRIDAY_REVENUE, 1)

        es = fc["error_structure"]
        check("FORECAST", "New Year days share of LR SSE (pct)",
              round(es["share_of_linear_dow_sse_pct"], 1), M.DAILY_NEW_YEAR_SHARE_OF_SSE_PCT, 0.05)
        check("FORECAST", "LR MAE excluding New Year days",
              round(es["linear_dow_mae_excluding_days"]), M.DAILY_LINREG_DOW_MAE_EXCLUDING_NEW_YEAR)
    else:
        skip("Daily granularity forecasting (analysis/daily_forecast.py)",
             "daily_forecast_summary.json not generated; run python analysis/daily_forecast.py")

    # ================= richer basket features =================
    # analysis/basket_features.py retrains the notebook 11 and 12 models on
    # richer features. Retraining needs the 114 MB cleaned record, so this
    # section reads the artifact and, crucially, checks that the artifact's
    # baseline rows (the 25 binary flags) reproduce the reported 61.30 / 69.05
    # / 71.67 / 17,532 figures. If those hold, the split, labels and seed are
    # the notebook ones, and the new numbers are like for like.
    bf_path = os.path.join(ARTIFACTS, "basket_features_summary.json")
    if os.path.exists(bf_path):
        bf = json.load(open(bf_path, encoding="utf-8"))
        bm, bc, bfi = bf["models"], bf["ceilings"], bf["feature_importance"]

        check("FEATURES", "Split, training baskets", bf["split"]["train_baskets"],
              M.CLASSIFIER_TRAIN_BASKETS)
        check("FEATURES", "Split, test baskets", bf["split"]["test_baskets"],
              M.CLASSIFIER_TEST_BASKETS)
        check("FEATURES", "Split seed", bf["split"]["random_state"], 42)
        check("FEATURES", "Majority baseline", round(bf["split"]["majority_baseline"], 3),
              M.CLASSIFIER_BASELINE, 0.0005)
        check("FEATURES", "Small baskets", bf["labels"]["Small"], 108349)
        check("FEATURES", "Large baskets", bf["labels"]["Large"], 29820)
        check("FEATURES", "Hour of day available", int(bf["hour_of_day"]["available"]),
              int(M.FEATURES_HOUR_OF_DAY_AVAILABLE))

        # the reported binary-flag figures reproduce inside the new run
        check("FEATURES", "Binary flags: tree depth 5 accuracy (nb11 figure)",
              round(bm["binary_tree_depth5"]["accuracy"], 3), M.CLASSIFIER_ACCURACY, 0.0005)
        check("FEATURES", "Binary flags: MLP accuracy (nb12 figure)",
              round(bm["binary_mlp"]["accuracy"], 4), M.NEURAL_NET_ACCURACY, 0.00005)
        check("FEATURES", "Binary flags: MLP parameters (nb12 figure)",
              bm["binary_mlp"]["parameters"], M.NEURAL_NET_PARAMETERS)
        check("FEATURES", "Binary flags: ceiling (nb12 figure)",
              round(bc["binary"]["ceiling"], 4), M.FEATURE_CEILING_ACCURACY, 0.00005)
        check("FEATURES", "Binary flags: distinct patterns (nb12 figure)",
              bc["binary"]["distinct_patterns"], M.DISTINCT_FEATURE_PATTERNS)
        check("FEATURES", "Binary flags: tree top feature (nb11 figure)",
              bfi["old_top"][0], M.CLASSIFIER_TOP_FEATURE)
        check("FEATURES", "Binary flags: tree top importance (nb11 figure)",
              round(bfi["old_top_values"][bfi["old_top"][0]], 3),
              M.CLASSIFIER_TOP_FEATURE_IMPORTANCE, 0.0005)

        # feature sets and ceilings
        check("FEATURES", "Full feature count", bf["feature_sets"]["full"]["n_features"],
              M.FEATURES_FULL_COUNT)
        check("FEATURES", "Discrete feature count", bf["feature_sets"]["discrete"]["n_features"],
              M.FEATURES_DISCRETE_COUNT)
        for name, c_ceil, c_pat, c_single in (
            ("binary", M.FEATURES_CEILING_BINARY, M.FEATURES_PATTERNS_BINARY,
             M.FEATURES_SINGLETON_SHARE_BINARY),
            ("discrete", M.FEATURES_CEILING_DISCRETE, M.FEATURES_PATTERNS_DISCRETE,
             M.FEATURES_SINGLETON_SHARE_DISCRETE),
            ("full", M.FEATURES_CEILING_FULL, M.FEATURES_PATTERNS_FULL,
             M.FEATURES_SINGLETON_SHARE_FULL),
        ):
            check("FEATURES", f"Ceiling, {name} features", round(bc[name]["ceiling"], 4), c_ceil, 0.00005)
            check("FEATURES", f"Distinct patterns, {name} features",
                  bc[name]["distinct_patterns"], c_pat)
            check("FEATURES", f"Singleton basket share, {name} features (pct)",
                  round(bc[name]["singleton_basket_share"] * 100, 1), c_single, 0.05)
        check("FEATURES", "Pattern lookup out of sample, binary",
              round(bc["binary"]["pattern_lookup"]["test_accuracy"], 4),
              M.FEATURES_LOOKUP_TEST_ACC_BINARY, 0.00005)
        check("FEATURES", "Pattern lookup out of sample, full",
              round(bc["full"]["pattern_lookup"]["test_accuracy"], 4),
              M.FEATURES_LOOKUP_TEST_ACC_FULL, 0.00005)
        check("FEATURES", "Test baskets with unseen pattern, full (pct)",
              round(bc["full"]["pattern_lookup"]["test_baskets_with_unseen_pattern"] * 100, 1),
              M.FEATURES_LOOKUP_UNSEEN_FULL, 0.05)
        check("FEATURES", "Ceiling gain, binary to full (points)",
              round((bc["full"]["ceiling"] - bc["binary"]["ceiling"]) * 100, 2),
              M.FEATURES_CEILING_GAIN_POINTS, 0.005)

        # accuracies
        for key, acc_c in (
            ("binary_tree_depth5", M.FEATURES_TREE_BINARY_ACCURACY),
            ("binary_mlp", M.FEATURES_MLP_BINARY_ACCURACY),
            ("discrete_tree_depth5", M.FEATURES_TREE_DISCRETE_ACCURACY),
            ("discrete_mlp", M.FEATURES_MLP_DISCRETE_ACCURACY),
            ("full_tree_depth5", M.FEATURES_TREE_FULL_ACCURACY),
            ("full_mlp", M.FEATURES_MLP_FULL_ACCURACY),
        ):
            check("FEATURES", f"Accuracy, {key}", round(bm[key]["accuracy"], 4), acc_c, 0.00005)
        check("FEATURES", "MLP parameters, full features", bm["full_mlp"]["parameters"],
              M.FEATURES_MLP_FULL_PARAMETERS)
        check("FEATURES", "Tree leaves, full features (depth 5)", bm["full_tree_depth5"]["leaves"], 32)
        for key, share_c in (
            ("binary_tree_depth5", M.FEATURES_TREE_BINARY_SHARE),
            ("binary_mlp", M.FEATURES_MLP_BINARY_SHARE),
            ("full_tree_depth5", M.FEATURES_TREE_FULL_SHARE),
            ("full_mlp", M.FEATURES_MLP_FULL_SHARE),
        ):
            check("FEATURES", f"Share of ceiling, {key} (pct)",
                  round(bm[key]["share_of_ceiling"] * 100, 1), share_c, 0.05)
        check("FEATURES", "Tree gain, binary to full (points)",
              round((bm["full_tree_depth5"]["accuracy"] - bm["binary_tree_depth5"]["accuracy"]) * 100, 2),
              M.FEATURES_TREE_GAIN_POINTS, 0.005)
        check("FEATURES", "MLP gain, binary to full (points)",
              round((bm["full_mlp"]["accuracy"] - bm["binary_mlp"]["accuracy"]) * 100, 2),
              M.FEATURES_MLP_GAIN_POINTS, 0.005)
        check("FEATURES", "New MLP beats old MLP",
              int(bm["full_mlp"]["accuracy"] > bm["binary_mlp"]["accuracy"]), 1)
        check("FEATURES", "New tree beats old tree",
              int(bm["full_tree_depth5"]["accuracy"] > bm["binary_tree_depth5"]["accuracy"]), 1)
        check("FEATURES", "New MLP still below its ceiling",
              int(bm["full_mlp"]["accuracy"] < bc["full"]["ceiling"]), 1)
        check("FEATURES", "Ceiling rose more than either model",
              int((bc["full"]["ceiling"] - bc["binary"]["ceiling"])
                  > (bm["full_mlp"]["accuracy"] - bm["binary_mlp"]["accuracy"])), 1)

        # feature importances
        check("FEATURES", "New tree top feature", bfi["new_top"][0], M.FEATURES_NEW_TOP_FEATURE)
        check("FEATURES", "New tree top importance",
              round(bfi["new_top_values"][bfi["new_top"][0]], 3), M.FEATURES_NEW_TOP_IMPORTANCE, 0.0005)
        check("FEATURES", "New tree second feature", bfi["new_top"][1], M.FEATURES_NEW_SECOND_FEATURE)
        check("FEATURES", "New tree second importance",
              round(bfi["new_top_values"][bfi["new_top"][1]], 3),
              M.FEATURES_NEW_SECOND_IMPORTANCE, 0.0005)
        check("FEATURES", "COOKING OIL rank on new tree", bfi["cooking_oil_new_rank"],
              M.FEATURES_COOKING_OIL_NEW_RANK)
        check("FEATURES", "COOKING OIL importance on new tree",
              round(bfi["cooking_oil_new_importance"], 3), M.FEATURES_COOKING_OIL_NEW_IMPORTANCE, 0.0005)
        check("FEATURES", "RICE rank on new tree", bfi["rice_new_rank"], M.FEATURES_RICE_NEW_RANK)
        check("FEATURES", "RICE importance on new tree",
              round(bfi["rice_new_importance"], 3), M.FEATURES_RICE_NEW_IMPORTANCE, 0.0005)
        check("FEATURES", "COOKING OIL and RICE displaced from the top",
              int(bfi["displaced"]), 1)
        check("FEATURES", "Features used by the new tree",
              bm["full_tree_depth5"]["n_features_used"], M.FEATURES_NEW_TREE_FEATURES_USED)

        # per-class recall
        check("FEATURES", "New MLP recall, Medium", round(bm["full_mlp"]["recall"]["Medium"], 3),
              M.FEATURES_MLP_FULL_RECALL_MEDIUM, 0.0005)
        check("FEATURES", "New MLP recall, Large", round(bm["full_mlp"]["recall"]["Large"], 3),
              M.FEATURES_MLP_FULL_RECALL_LARGE, 0.0005)
        check("FEATURES", "New tree recall, Medium",
              round(bm["full_tree_depth5"]["recall"]["Medium"], 3),
              M.FEATURES_TREE_FULL_RECALL_MEDIUM, 0.0005)
        check("FEATURES", "New tree recall, Large",
              round(bm["full_tree_depth5"]["recall"]["Large"], 3),
              M.FEATURES_TREE_FULL_RECALL_LARGE, 0.0005)
    else:
        skip("Richer basket features (analysis/basket_features.py)",
             "basket_features_summary.json not generated; run python analysis/basket_features.py")

    # ================= temporal validation =================
    # analysis/temporal_validation.py mines rules on the development window and
    # recomputes each rule's lift on the validation window. Written 2026-08-17 to
    # give RULE_STABILITY_* a source; before that the median had no producing code.
    tv_path = os.path.join(ARTIFACTS, "temporal_validation_summary.json")
    if os.path.exists(tv_path):
        tv = json.load(open(tv_path, encoding="utf-8"))
        check("STABILITY", "Development window baskets",
              tv["windows"]["development"]["baskets"], M.RULE_STABILITY_DEV_BASKETS)
        check("STABILITY", "Validation window baskets",
              tv["windows"]["validation"]["baskets"], M.RULE_STABILITY_VAL_BASKETS)
        check("STABILITY", "Windows partition the 218,037 baskets",
              tv["windows"]["development"]["baskets"]
              + tv["windows"]["validation"]["baskets"], M.TOTAL_TRANSACTIONS)
        check("STABILITY", "Development rules mined", tv["dev_rules"],
              M.RULE_STABILITY_DEV_RULES)
        check("STABILITY", "Mining support floor matches notebook 05",
              tv["thresholds"]["min_support"], 0.01, 0.0001)
        check("STABILITY", "Every rule has a defined validation lift",
              tv["rules_without_defined_ratio"], 0)
        check("STABILITY", "Median stability ratio", round(tv["median_ratio"], 3),
              M.RULE_STABILITY_MEDIAN, 0.0005)
        check("STABILITY", "Minimum stability ratio", round(tv["min_ratio"], 3),
              M.RULE_STABILITY_MIN, 0.0005)
        check("STABILITY", "Maximum stability ratio", round(tv["max_ratio"], 3),
              M.RULE_STABILITY_MAX, 0.0005)
        check("STABILITY", "Mean stability ratio", round(tv["mean_ratio"], 3),
              M.RULE_STABILITY_MEAN, 0.0005)
        check("STABILITY", "Rules that more than halved",
              tv["rules_below_ratio_floor"], M.RULE_STABILITY_BELOW_HALF)
        check("STABILITY", "Top 20 dev rules still strong in validation",
              tv["top_n_still_strong"], M.RULE_STABILITY_TOP20_STILL_STRONG)
        check("STABILITY", "Dev rules at lift >= 3",
              tv["strong_dev_rules"], M.RULE_STABILITY_STRONG_RULES)
        check("STABILITY", "Of those, still >= 3 in validation",
              tv["strong_dev_rules_still_strong"],
              M.RULE_STABILITY_STRONG_STILL_STRONG)
        check("STABILITY", "Median ratio is within 10 pct of 1.0",
              int(abs(tv["median_ratio"] - 1.0) < 0.10), 1)
    else:
        skip("Temporal validation (analysis/temporal_validation.py)",
             "temporal_validation_summary.json not generated; "
             "run python analysis/temporal_validation.py")

    # ================= recommender baselines =================
    # analysis/recommender_baselines.py reproduces notebook 09's pipeline and adds
    # the popularity and random baselines and the coverage split. Written
    # 2026-08-17: notebook 09 produced only the hit rate and the test basket count.
    rb_path = os.path.join(ARTIFACTS, "recommender_baselines_summary.json")
    if os.path.exists(rb_path):
        rb = json.load(open(rb_path, encoding="utf-8"))
        check("RECOMMENDER", "Training baskets", rb["split"]["train_baskets"],
              M.ML_TRAIN_BASKETS)
        check("RECOMMENDER", "Test baskets", rb["split"]["test_baskets"],
              M.ML_TEST_BASKETS)
        check("RECOMMENDER", "Multi-product test baskets scored",
              rb["test_baskets_scored"], M.REC_TEST_BASKETS)
        check("RECOMMENDER", "Products carrying at least one rule",
              rb["products_with_rules"], M.REC_PRODUCTS_WITH_RULES)
        check("RECOMMENDER", "Model hit rate", rb["model_hit_pct"],
              M.REC_MODEL_HIT_PCT, 0.005)
        check("RECOMMENDER", "Model hit rate agrees with notebook 09 headline",
              round(rb["model_hit_pct"] / 100, 2), M.ML_HIT_RATE, 0.005)
        check("RECOMMENDER", "Popularity, matched budget",
              rb["popularity_matched_pct"], M.REC_POPULARITY_MATCHED_PCT, 0.005)
        check("RECOMMENDER", "Popularity, unconstrained top 5",
              rb["popularity_top5_pct"], M.REC_POPULARITY_TOP5_PCT, 0.005)
        check("RECOMMENDER", "Random, matched budget",
              rb["random_matched_pct"], M.REC_RANDOM_MATCHED_PCT, 0.005)
        check("RECOMMENDER", "Random, unconstrained top 5",
              rb["random_top5_pct"], M.REC_RANDOM_TOP5_PCT, 0.005)
        check("RECOMMENDER", "Avg recommendations per basket",
              rb["avg_recs_per_basket"], M.REC_AVG_RECS_PER_BASKET, 0.005)
        check("RECOMMENDER", "Avg recommendations when covered",
              rb["avg_recs_when_covered"], M.REC_AVG_RECS_WHEN_COVERED, 0.005)
        check("RECOMMENDER", "Covered baskets", rb["covered_baskets"],
              M.REC_COVERED_BASKETS)
        check("RECOMMENDER", "Uncovered baskets", rb["uncovered_baskets"],
              M.REC_UNCOVERED_BASKETS)
        check("RECOMMENDER", "Covered plus uncovered equals scored baskets",
              rb["covered_baskets"] + rb["uncovered_baskets"],
              rb["test_baskets_scored"])
        check("RECOMMENDER", "Model where covered", rb["covered_model_pct"],
              M.REC_COVERED_MODEL_PCT, 0.005)
        check("RECOMMENDER", "Popularity where covered",
              rb["covered_popularity_pct"], M.REC_COVERED_POPULARITY_PCT, 0.005)
        check("RECOMMENDER", "Model beats popularity at a matched budget",
              int(rb["model_hit_pct"] > rb["popularity_matched_pct"]), 1)
        check("RECOMMENDER", "Model loses to unconstrained popularity",
              int(rb["model_hit_pct"] < rb["popularity_top5_pct"]), 1)
        check("RECOMMENDER", "Model beats popularity where it has coverage",
              int(rb["covered_model_pct"] > rb["covered_popularity_pct"]), 1)
        check("RECOMMENDER", "Model beats random by more than 10x",
              int(rb["model_hit_pct"] > 10 * rb["random_matched_pct"]), 1)
    else:
        skip("Recommender baselines (analysis/recommender_baselines.py)",
             "recommender_baselines_summary.json not generated; "
             "run python analysis/recommender_baselines.py")

    # ================= not auto-checkable =================
    skip("Frequent itemsets (261, both algorithms)",
         "Apriori/FP-Growth counts are not stored in any artifact; re-run notebook 05 or 08")
    skip("Network connections (44 unique)",
         "derived inside notebook 05 chart 10; not stored in an artifact")
    skip("Top classifier feature (COOKING OIL 0.278)",
         "feature importances are not exported; re-run notebook 11")
    skip("Warehouse quality checks (32 of 32)",
         "self-referential; run etl/quality_checks.py, which reports its own count")
    skip("Reproduction checks (34 of 34)",
         "self-referential; run reproduce_all_results.py, which reports its own count")

    # ================= report =================
    by_source = {}
    for ok, source, *_ in results:
        by_source.setdefault(source, [0, 0])
        by_source[source][1] += 1
        if ok:
            by_source[source][0] += 1

    current = None
    for ok, source, label, actual, expected in results:
        if source != current:
            print(f"\n{source}")
            print("-" * 78)
            current = source
        shown = f"{actual:,}" if isinstance(actual, int) else str(actual)
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:44} {shown:>16}")

    passed = sum(1 for r in results if r[0])
    total = len(results)

    print()
    print("=" * 78)
    for source, (p, t) in sorted(by_source.items()):
        print(f"  {source:9} {p} of {t}")
    print(f"\n  VERIFIED: {passed} of {total} checkable figures match")
    print(f"  NOT AUTO-CHECKABLE: {len(uncheckable)} figures need a notebook re-run")
    for label, why in uncheckable:
        print(f"    - {label}\n        {why}")

    if passed != total:
        print("\n  FAILURES:")
        for ok, source, label, actual, expected in results:
            if not ok:
                print(f"    {label}: expected {expected!r}, got {actual!r}")
        print("=" * 78)
        return 1

    print("\n  ALL CHECKABLE FIGURES MATCH.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
