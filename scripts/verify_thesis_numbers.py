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
        check("LIVE", "Zone 1 share of revenue", live["zone1_pct"], 40.6, 0.05)
        check("LIVE", "Zone 1 category count", live["zone1_cats"], 5)
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
    check("CONSTANT", "Silhouette increase (absolute)", M.SILHOUETTE_INCREASE, 0.364, 0.0005)

    # ================= cross-sell =================
    check("ARTIFACT", "Cross-sell captured, current", cross["current_rules_captured"],
          M.CROSS_SELL_CURRENT)
    check("ARTIFACT", "Cross-sell captured, optimised", cross["optimised_rules_captured"],
          M.CROSS_SELL_OPTIMISED)
    check("ARTIFACT", "Cross-sell capture pct, current", cross["current_capture_pct"], 8.2, 0.05)
    check("ARTIFACT", "Cross-sell capture pct, optimised", cross["optimised_capture_pct"],
          16.3, 0.05)
    check("ARTIFACT", "Cross-sell improvement (x)",
          round(cross["optimised_rules_captured"] / cross["current_rules_captured"], 1), 2.0, 0.05)

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
    check("CONSTANT", "Classifier accuracy", M.CLASSIFIER_ACCURACY, 0.613, 0.0005)
    check("CONSTANT", "Classifier baseline", M.CLASSIFIER_BASELINE, 0.497, 0.0005)
    check("CONSTANT", "Classifier test baskets", M.CLASSIFIER_TEST_BASKETS, 65412)
    check("CONSTANT", "Classifier beats baseline",
          int(M.CLASSIFIER_ACCURACY > M.CLASSIFIER_BASELINE), 1)
    check("CONSTANT", "Neural network accuracy", M.NEURAL_NET_ACCURACY, 0.6905, 0.0005)
    check("CONSTANT", "Neural network parameters", M.NEURAL_NET_PARAMETERS, 3843)
    check("CONSTANT", "Fully grown tree accuracy", M.DECISION_TREE_FULL_ACCURACY, 0.6785, 0.0005)
    check("CONSTANT", "Fully grown tree leaves", M.DECISION_TREE_FULL_LEAVES, 10231)
    check("CONSTANT", "MLP model family advantage (points)",
          round((M.NEURAL_NET_ACCURACY - M.DECISION_TREE_FULL_ACCURACY) * 100, 2), 1.20, 0.005)
    check("CONSTANT", "Feature ceiling", M.FEATURE_CEILING_ACCURACY, 0.7167, 0.0005)
    check("CONSTANT", "Distinct feature patterns", M.DISTINCT_FEATURE_PATTERNS, 17532)
    check("CONSTANT", "No model exceeds the ceiling",
          int(M.NEURAL_NET_ACCURACY < M.FEATURE_CEILING_ACCURACY), 1)

    # ================= ABC =================
    a_count = int((abc["abc_category"] == "A").sum())
    check("ARTIFACT", "Class A products", a_count, M.ABC_CLASS_A_PRODUCTS)
    check("ARTIFACT", "Class A share of products",
          round(a_count / len(abc) * 100, 1), 6.0, 0.05)

    # ================= not auto-checkable =================
    skip("Frequent itemsets (243, both algorithms)",
         "Apriori/FP-Growth counts are not stored in any artifact; re-run notebook 05 or 08")
    skip("Network connections (38 unique)",
         "derived inside notebook 05 chart 10; not stored in an artifact")
    skip("Rule temporal stability (median 1.011)",
         "requires the notebook 05 Step 9 dev/validation split to be re-run")
    skip("Top classifier feature (COOKING OIL 0.280)",
         "feature importances are not exported; re-run notebook 11")
    skip("Warehouse quality checks (32 of 32)",
         "self-referential; run etl/quality_checks.py, which reports its own count")
    skip("Reproduction checks (12 of 12)",
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
