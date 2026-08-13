"""
refresh_artifacts.py

Regenerates the dashboard artifacts that the warehouse can produce, straight
from SQL, so the dashboard is fed by the data platform rather than by a manual
notebook run.

    python etl/refresh_artifacts.py

What it refreshes (all derived from warehouse views):
    kpi_summary.json          (warehouse-derived fields only, see below)
    monthly_revenue.csv
    category_distribution.csv
    basket_value_hist.csv
    abc_analysis.csv
    day_of_week.csv

What it deliberately does NOT touch:
    category_rules.csv, product_rules.csv, cooccurrence_matrix.csv,
    cluster_assignments.csv, top_pairs.csv, cross_sell_summary.json,
    top_products.csv

    Those come from Apriori, FP-Growth and K-Means in notebooks 05, 06 and 09.
    They are research outputs, not operational metrics, and the warehouse has
    no way to derive them. Overwriting them here would be pretending the
    pipeline computes something it does not.

kpi_summary.json is MERGED, not replaced, for the same reason: it holds both
warehouse metrics (transactions, revenue, basket values) and mining metrics
(max lift, rule counts, silhouette). Only the warehouse ones are updated; the
mining ones are read from the existing file and written back untouched.

The output schemas match dashboard/precompute_artifacts.py exactly, because the
dashboard reads these files by column name.
"""

import json
import os
import sys
import warnings

import numpy as np
import pandas as pd
import psycopg2

# pandas warns that it only officially supports SQLAlchemy connectables. Raw
# psycopg2 connections work correctly for the read-only SELECTs used here, and
# adding SQLAlchemy purely to silence a warning would put another dependency
# between a marker and a working checkout. Suppressed narrowly, by message.
warnings.filterwarnings(
    "ignore",
    message="pandas only supports SQLAlchemy connectable",
    category=UserWarning,
)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from config import db  # noqa: E402

ARTIFACTS = os.path.join(ROOT, "dashboard", "artifacts")

# The calendar span of the dataset, 17 Jul 2025 to 20 May 2026 inclusive.
# This is the span in days, which is larger than the 304 days that actually
# had sales. The existing artifacts use the span, so daily_revenue stays
# comparable with the figures already quoted in the thesis.
DATA_DAYS = 307

DAY_ORDER = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def log(msg=""):
    print(msg, flush=True)


def main():
    log("=" * 70)
    log("REFRESH DASHBOARD ARTIFACTS FROM THE WAREHOUSE")
    log("=" * 70)
    log(f"Source : {db.describe()} (warehouse schema)")
    log(f"Target : {ARTIFACTS}")

    os.makedirs(ARTIFACTS, exist_ok=True)
    conn = psycopg2.connect(**db.connection_kwargs())

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM warehouse.fact_sales")
    if cur.fetchone()[0] == 0:
        log("\nERROR: the warehouse is empty. Run etl/load_warehouse.py first.")
        cur.close()
        conn.close()
        return 1

    written = []

    # -- monthly_revenue.csv -------------------------------------------
    monthly = pd.read_sql(
        "SELECT year_month AS month, revenue, transactions AS baskets, avg_basket "
        "FROM warehouse.v_monthly_revenue ORDER BY year_month",
        conn,
    )
    monthly.to_csv(os.path.join(ARTIFACTS, "monthly_revenue.csv"), index=False)
    written.append(("monthly_revenue.csv", len(monthly)))

    # -- category_distribution.csv --------------------------------------
    cat = pd.read_sql(
        "SELECT category_name AS category, baskets, basket_penetration_pct AS pct_of_baskets "
        "FROM warehouse.v_category_performance ORDER BY baskets DESC",
        conn,
    )
    cat.to_csv(os.path.join(ARTIFACTS, "category_distribution.csv"), index=False)
    written.append(("category_distribution.csv", len(cat)))

    # -- basket_value_hist.csv ------------------------------------------
    # Same treatment as precompute_artifacts.py: clip the long tail at 5,000
    # for display only, then 40 equal bins.
    values = pd.read_sql("SELECT basket_value FROM warehouse.dim_basket", conn)
    clipped = values["basket_value"].astype(float).clip(upper=5000)
    counts, edges = np.histogram(clipped, bins=40)
    pd.DataFrame({
        "bin_left": edges[:-1].round(2),
        "bin_right": edges[1:].round(2),
        "count": counts,
    }).to_csv(os.path.join(ARTIFACTS, "basket_value_hist.csv"), index=False)
    written.append(("basket_value_hist.csv", len(counts)))

    # -- abc_analysis.csv ------------------------------------------------
    # The tiebreaker on product_name keeps the row order stable across runs;
    # many products share an identical revenue total.
    abc = pd.read_sql(
        "SELECT product_name AS product, revenue FROM warehouse.v_top_products "
        "ORDER BY revenue DESC, product_name",
        conn,
    )
    abc["revenue"] = abc["revenue"].astype(float).round(2)
    cumulative = abc["revenue"].cumsum() / abc["revenue"].sum() * 100
    abc["cumulative_pct"] = cumulative.round(4)
    abc["abc_category"] = np.where(cumulative <= 70, "A", np.where(cumulative <= 90, "B", "C"))
    abc.to_csv(os.path.join(ARTIFACTS, "abc_analysis.csv"), index=False)
    counts_abc = abc["abc_category"].value_counts()
    written.append(("abc_analysis.csv", len(abc)))
    log(f"\n  ABC classes: A {counts_abc.get('A', 0):,}  B {counts_abc.get('B', 0):,}  "
        f"C {counts_abc.get('C', 0):,}")

    # -- day_of_week.csv --------------------------------------------------
    dow = pd.read_sql(
        "SELECT day_name, revenue, transactions AS transaction_count, avg_basket "
        "FROM warehouse.v_day_of_week",
        conn,
    )
    dow["day_name"] = dow["day_name"].str.strip()
    dow = dow.set_index("day_name").reindex(DAY_ORDER).reset_index()
    dow.to_csv(os.path.join(ARTIFACTS, "day_of_week.csv"), index=False)
    written.append(("day_of_week.csv", len(dow)))

    # -- kpi_summary.json (merge, never replace) ---------------------------
    kpi_path = os.path.join(ARTIFACTS, "kpi_summary.json")
    existing = {}
    if os.path.exists(kpi_path):
        with open(kpi_path, encoding="utf-8") as fh:
            existing = json.load(fh)

    row = pd.read_sql("SELECT * FROM warehouse.v_kpi_summary", conn).iloc[0]
    top_cat = pd.read_sql(
        "SELECT category_name FROM warehouse.v_category_performance "
        "ORDER BY baskets DESC LIMIT 1", conn,
    ).iloc[0]["category_name"]

    total_revenue = float(row["total_revenue"])
    total_baskets = int(row["total_transactions"])

    warehouse_fields = {
        "total_transactions": total_baskets,
        "total_revenue": round(total_revenue, 2),
        "avg_basket_value": round(float(row["avg_basket_value"]), 2),
        "median_basket_value": round(float(row["median_basket_value"]), 2),
        "n_categories": int(row["n_categories"]),
        "n_products": int(row["n_products"]),
        "daily_revenue": round(total_revenue / DATA_DAYS, 2),
        "daily_customers": round(total_baskets / DATA_DAYS),
        "top_category": top_cat,
        "data_days": DATA_DAYS,
    }

    merged = dict(existing)
    changed = {k: (existing.get(k), v) for k, v in warehouse_fields.items()
               if existing.get(k) != v}
    merged.update(warehouse_fields)
    merged["source"] = "warehouse"

    with open(kpi_path, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=2)
    written.append(("kpi_summary.json", len(merged)))

    preserved = [k for k in existing if k not in warehouse_fields]
    log(f"  kpi_summary.json: {len(warehouse_fields)} warehouse fields refreshed, "
        f"{len(preserved)} mining fields preserved")
    if preserved:
        log(f"    preserved: {', '.join(sorted(preserved))}")
    if changed:
        log("    values that changed:")
        for k, (old, new) in changed.items():
            log(f"      {k}: {old} -> {new}")
    else:
        log("    no warehouse field changed value")

    cur.close()
    conn.close()

    log("\nArtifacts written:")
    for name, n in written:
        size = os.path.getsize(os.path.join(ARTIFACTS, name))
        log(f"  {name:28} {n:>6,} rows  {size / 1024:8.1f} KB")

    log()
    log("=" * 70)
    log("ARTIFACT REFRESH COMPLETE.")
    log("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
