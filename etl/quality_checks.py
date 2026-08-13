"""
quality_checks.py

Data quality gate for the pipeline. Runs after the warehouse load and fails
loudly if anything is wrong, so a broken load stops the DAG instead of quietly
feeding bad numbers to the dashboard.

    python etl/quality_checks.py

Every check is expressed as a SQL query plus an expected result. The checks are
grouped by the kind of failure they catch:

    COMPLETENESS  did every row arrive
    INTEGRITY     do the keys and relationships hold
    CONSISTENCY   does the warehouse still agree with the OLTP source
    ACCURACY      do the headline figures still match the thesis

The ACCURACY group is the one that matters most for an academic project. If a
future change to the ETL silently altered the average basket value, the thesis
and the dashboard would disagree and nobody would notice. These checks make
that impossible to miss.
"""

import os
import sys

import psycopg2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from config import db  # noqa: E402

# (group, description, sql, expected)
# expected None means "the query returns a count that must be zero"
CHECKS = [
    # -- COMPLETENESS ---------------------------------------------------
    ("COMPLETENESS", "OLTP line items loaded",
     "SELECT COUNT(*) FROM oltp.transaction_items", 767180),
    ("COMPLETENESS", "OLTP transactions loaded",
     "SELECT COUNT(*) FROM oltp.transactions", 218037),
    ("COMPLETENESS", "OLTP products loaded",
     "SELECT COUNT(*) FROM oltp.products", 5680),
    ("COMPLETENESS", "Fact rows loaded",
     "SELECT COUNT(*) FROM warehouse.fact_sales", 767180),
    ("COMPLETENESS", "Basket dimension loaded",
     "SELECT COUNT(*) FROM warehouse.dim_basket", 218037),
    ("COMPLETENESS", "Product dimension loaded",
     "SELECT COUNT(*) FROM warehouse.dim_product", 5680),
    ("COMPLETENESS", "Category dimension loaded",
     "SELECT COUNT(*) FROM warehouse.dim_category", 25),
    ("COMPLETENESS", "Date dimension loaded",
     "SELECT COUNT(*) FROM warehouse.dim_date", 304),

    # -- INTEGRITY ------------------------------------------------------
    ("INTEGRITY", "No orphan facts without a basket",
     """SELECT COUNT(*) FROM warehouse.fact_sales f
        LEFT JOIN warehouse.dim_basket b ON b.basket_key = f.basket_key
        WHERE b.basket_key IS NULL""", 0),
    ("INTEGRITY", "No orphan facts without a product",
     """SELECT COUNT(*) FROM warehouse.fact_sales f
        LEFT JOIN warehouse.dim_product p ON p.product_key = f.product_key
        WHERE p.product_key IS NULL""", 0),
    ("INTEGRITY", "No orphan facts without a date",
     """SELECT COUNT(*) FROM warehouse.fact_sales f
        LEFT JOIN warehouse.dim_date d ON d.date_key = f.date_key
        WHERE d.date_key IS NULL""", 0),
    ("INTEGRITY", "Every category has a placement zone",
     "SELECT COUNT(*) FROM warehouse.dim_category WHERE zone_assignment IS NULL OR zone_assignment = ''", 0),
    ("INTEGRITY", "All 5 placement zones present",
     "SELECT COUNT(DISTINCT zone_assignment) FROM warehouse.dim_category", 5),
    ("INTEGRITY", "No duplicate invoice numbers",
     """SELECT COUNT(*) FROM (
            SELECT invoice_no FROM warehouse.dim_basket
            GROUP BY invoice_no HAVING COUNT(*) > 1) d""", 0),
    ("INTEGRITY", "No duplicate basket/line pairs in the fact table",
     """SELECT COUNT(*) FROM (
            SELECT basket_key, line_no FROM warehouse.fact_sales
            GROUP BY basket_key, line_no HAVING COUNT(*) > 1) d""", 0),
    ("INTEGRITY", "No negative or zero line amounts",
     "SELECT COUNT(*) FROM warehouse.fact_sales WHERE total_amount <= 0", 0),
    ("INTEGRITY", "No negative quantities",
     "SELECT COUNT(*) FROM warehouse.fact_sales WHERE quantity <= 0", 0),

    # -- CONSISTENCY ----------------------------------------------------
    ("CONSISTENCY", "Fact grain matches OLTP line items",
     """SELECT (SELECT COUNT(*) FROM warehouse.fact_sales)
             - (SELECT COUNT(*) FROM oltp.transaction_items)""", 0),
    ("CONSISTENCY", "Warehouse revenue reconciles to OLTP",
     """SELECT ROUND(ABS(
            (SELECT SUM(total_amount) FROM warehouse.fact_sales) -
            (SELECT SUM(total_amount) FROM oltp.transaction_items)), 2)""", 0),
    ("CONSISTENCY", "Basket values reconcile to their line items",
     """SELECT COUNT(*) FROM (
            SELECT b.basket_key
            FROM warehouse.dim_basket b
            JOIN warehouse.fact_sales f ON f.basket_key = b.basket_key
            GROUP BY b.basket_key, b.basket_value
            HAVING ABS(b.basket_value - SUM(f.total_amount)) > 0.01) d""", 0),
    ("CONSISTENCY", "Basket item counts reconcile to the fact table",
     """SELECT COUNT(*) FROM (
            SELECT b.basket_key
            FROM warehouse.dim_basket b
            JOIN warehouse.fact_sales f ON f.basket_key = b.basket_key
            GROUP BY b.basket_key, b.n_items
            HAVING b.n_items <> COUNT(*)) d""", 0),

    # -- ACCURACY (the thesis numbers) -----------------------------------
    ("ACCURACY", "Total revenue is Rs 218,214,456.88",
     "SELECT ROUND(SUM(total_amount), 2) FROM warehouse.fact_sales", 218214456.88),
    ("ACCURACY", "Average basket value is Rs 1,000.81",
     "SELECT ROUND(AVG(basket_value), 2) FROM warehouse.dim_basket", 1000.81),
    ("ACCURACY", "Median basket value is Rs 500.00",
     """SELECT ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY basket_value)::NUMERIC, 2)
        FROM warehouse.dim_basket""", 500.00),
    ("ACCURACY", "Small baskets number 108,349 (notebook 03 Chart 9)",
     "SELECT COUNT(*) FROM warehouse.dim_basket WHERE basket_segment = 'Small'", 108349),
    ("ACCURACY", "Medium baskets number 79,868",
     "SELECT COUNT(*) FROM warehouse.dim_basket WHERE basket_segment = 'Medium'", 79868),
    ("ACCURACY", "Large baskets number 29,820",
     "SELECT COUNT(*) FROM warehouse.dim_basket WHERE basket_segment = 'Large'", 29820),
    ("ACCURACY", "Large baskets carry 52.1% of revenue",
     """SELECT ROUND(100.0 * SUM(basket_value) FILTER (WHERE basket_segment = 'Large')
                    / SUM(basket_value), 1) FROM warehouse.dim_basket""", 52.1),
    ("ACCURACY", "FOOD STAPLES is the top category by basket count",
     """SELECT category_name FROM warehouse.v_category_performance
        ORDER BY baskets DESC LIMIT 1""", "FOOD STAPLES"),
    ("ACCURACY", "Friday is the highest revenue day",
     "SELECT day_name FROM warehouse.v_day_of_week ORDER BY revenue DESC LIMIT 1", "Friday"),
    ("ACCURACY", "September 2025 is the peak month (Dashain)",
     "SELECT year_month FROM warehouse.v_monthly_revenue ORDER BY revenue DESC LIMIT 1", "2025-09"),
    ("ACCURACY", "Zone 1 (the anchor zone) carries the largest revenue share",
     """SELECT zone_assignment FROM warehouse.v_zone_performance
        ORDER BY revenue DESC LIMIT 1""", "Zone 1 - Center"),
]


def main():
    print("=" * 74, flush=True)
    print("DATA QUALITY CHECKS", flush=True)
    print("=" * 74, flush=True)
    print(f"Target: {db.describe()}\n", flush=True)

    conn = psycopg2.connect(**db.connection_kwargs())
    cur = conn.cursor()

    failures = []
    current_group = None
    for group, description, sql, expected in CHECKS:
        if group != current_group:
            print(f"\n{group}", flush=True)
            print("-" * 74, flush=True)
            current_group = group

        cur.execute(sql)
        actual = cur.fetchone()[0]

        if isinstance(expected, str):
            ok = str(actual).strip() == expected
        elif isinstance(expected, float):
            ok = abs(float(actual) - expected) < 0.011
        else:
            ok = int(actual) == expected

        status = "PASS" if ok else "FAIL"
        shown = f"{actual:,}" if isinstance(actual, int) else str(actual).strip()
        print(f"  [{status}] {description:58} {shown}", flush=True)
        if not ok:
            failures.append((description, expected, actual))

    cur.close()
    conn.close()

    print()
    print("=" * 74, flush=True)
    if failures:
        print(f"QUALITY CHECKS FAILED: {len(failures)} of {len(CHECKS)}", flush=True)
        for description, expected, actual in failures:
            print(f"  {description}\n    expected {expected!r}, got {actual!r}", flush=True)
        print("=" * 74, flush=True)
        return 1

    print(f"ALL {len(CHECKS)} QUALITY CHECKS PASSED.", flush=True)
    print("The warehouse agrees with the OLTP source and with the thesis figures.", flush=True)
    print("=" * 74, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
