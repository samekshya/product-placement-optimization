"""
load_warehouse.py

Populates the star schema warehouse from the OLTP schema.

    python etl/load_warehouse.py

The OLTP layer must be loaded first (scripts/load_to_postgres.py).

Design:
    Every step is a single INSERT ... SELECT that runs inside Postgres. No
    data is pulled into Python and pushed back. That is the whole point of
    having the OLTP layer: the database does the work, and the ETL is a
    sequence of set-based transformations rather than row-by-row Python.

Idempotency:
    Every insert carries ON CONFLICT DO NOTHING against a natural key, so a
    second run inserts nothing. The Airflow DAG depends on this: re-running
    a task must never double the fact table.

The zone assignments:
    ZONE_MAP below is the placement recommendation, re-derived on 17 August
    2026 by analysis/optimise_zones.py from the post-remap association rules
    (notebook 05), capacity-matched and certified against exhaustive
    enumeration. It is the one piece of the warehouse that is not mechanical
    restructuring of the source data: it is the research finding itself,
    stored as a queryable dimension attribute.
"""

import os
import sys
import time

import psycopg2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from config import db  # noqa: E402

DDL_PATH = os.path.join(ROOT, "sql", "02_create_warehouse.sql")

EXPECTED = {
    "warehouse.dim_date": 304,
    "warehouse.dim_category": 25,
    "warehouse.dim_product": 5680,
    "warehouse.dim_basket": 218037,
    "warehouse.fact_sales": 767180,
}

# The 5 placement zones, RE-DERIVED 17 August 2026 from the post-remap
# association rules. Membership and the reasoning are in analysis/zones.py;
# this map is the same content in the shape dim_category stores.
# category -> (zone_assignment, zone_label, zone_location)
ZONE_MAP = {
    # Zone 1: the anchor cluster the strong rules bind together, centre of store
    "FOOD STAPLES":               ("Zone 1 - Center", "Anchor Cluster", "Store Center"),
    "CANNED AND PACKAGED FOODS":  ("Zone 1 - Center", "Anchor Cluster", "Store Center"),
    "CLEANING SUPPLIES":          ("Zone 1 - Center", "Anchor Cluster", "Store Center"),
    "TEA AND SPICES":             ("Zone 1 - Center", "Anchor Cluster", "Store Center"),
    "PERSONAL CARE":              ("Zone 1 - Center", "Anchor Cluster", "Store Center"),
    "COOKING OIL":                ("Zone 1 - Center", "Anchor Cluster", "Store Center"),
    # Zone 2: impulse categories, near the entrance
    "CONFECTIONERY":              ("Zone 2 - Entrance", "Impulse Purchase", "Near Entrance"),
    "SNACKS":                     ("Zone 2 - Entrance", "Impulse Purchase", "Near Entrance"),
    "NOODLES":                    ("Zone 2 - Entrance", "Impulse Purchase", "Near Entrance"),
    "HOUSEHOLD ITEMS":            ("Zone 2 - Entrance", "Impulse Purchase", "Near Entrance"),
    "POOJA ITEMS":                ("Zone 2 - Entrance", "Impulse Purchase", "Near Entrance"),
    # Zone 3: destination, off the main flow
    "BISCUITS AND COOKIES":       ("Zone 3 - Side Aisle", "Destination", "Side Aisle"),
    "BABY CARE":                  ("Zone 3 - Side Aisle", "Destination", "Side Aisle"),
    "STATIONERY":                 ("Zone 3 - Side Aisle", "Destination", "Side Aisle"),
    # Zone 4: refrigeration constrained, back wall
    "DAIRY PRODUCTS":             ("Zone 4 - Back Wall", "Cold Storage", "Back Wall"),
    "FROZEN FOODS":               ("Zone 4 - Back Wall", "Cold Storage", "Back Wall"),
    "FRESH PRODUCE":              ("Zone 4 - Back Wall", "Cold Storage", "Back Wall"),
    "BAKERY":                     ("Zone 4 - Back Wall", "Cold Storage", "Back Wall"),
    # Zone 5: speciality and restricted, perimeter
    "RICE":                       ("Zone 5 - Perimeter", "Speciality", "Perimeter"),
    "ALCOHOLIC BEVERAGES":        ("Zone 5 - Perimeter", "Speciality", "Perimeter"),
    "CIGARETTE AND TOBACCO":      ("Zone 5 - Perimeter", "Speciality", "Perimeter"),
    "SOFT DRINKS AND JUICES":     ("Zone 5 - Perimeter", "Speciality", "Perimeter"),
    "BREAKFAST CEREALS":          ("Zone 5 - Perimeter", "Speciality", "Perimeter"),
    "ELECTRICAL SUPPLIES":        ("Zone 5 - Perimeter", "Speciality", "Perimeter"),
    "PARTY SUPPLIES":             ("Zone 5 - Perimeter", "Speciality", "Perimeter"),
}


def log(msg=""):
    print(msg, flush=True)


def load_dim_date(cur):
    """One row per trading day, derived from the transaction dates."""
    cur.execute("""
        INSERT INTO warehouse.dim_date (
            date_key, full_date, date_nepali, day_of_week, day_name,
            month_number, month_name, year_number, year_month,
            is_weekend_nepal, is_festival_season
        )
        SELECT DISTINCT
            TO_CHAR(t.txn_date, 'YYYYMMDD')::INTEGER,
            t.txn_date,
            MIN(t.date_nepali) OVER (PARTITION BY t.txn_date),
            EXTRACT(ISODOW FROM t.txn_date)::SMALLINT,
            TRIM(TO_CHAR(t.txn_date, 'Day')),
            EXTRACT(MONTH FROM t.txn_date)::SMALLINT,
            TRIM(TO_CHAR(t.txn_date, 'Month')),
            EXTRACT(YEAR FROM t.txn_date)::SMALLINT,
            TO_CHAR(t.txn_date, 'YYYY-MM'),
            EXTRACT(ISODOW FROM t.txn_date) = 6,
            EXTRACT(MONTH FROM t.txn_date) IN (9, 10)
        FROM oltp.transactions t
        ON CONFLICT (date_key) DO NOTHING;
    """)
    return cur.rowcount


def load_dim_category(cur):
    """The 25 categories, each carrying its re-derived zone assignment."""
    rows = [(name,) + zones for name, zones in sorted(ZONE_MAP.items())]
    args = ",".join(cur.mogrify("(%s,%s,%s,%s)", r).decode() for r in rows)
    cur.execute(f"""
        INSERT INTO warehouse.dim_category
            (category_name, zone_assignment, zone_label, zone_location)
        VALUES {args}
        ON CONFLICT (category_name) DO NOTHING;
    """)
    return cur.rowcount


def load_dim_product(cur):
    cur.execute("""
        INSERT INTO warehouse.dim_product (product_name, product_group, category_key)
        SELECT p.product_name, p.product_group, c.category_key
        FROM oltp.products p
        JOIN warehouse.dim_category c ON c.category_name = p.category
        ON CONFLICT (product_name) DO NOTHING;
    """)
    return cur.rowcount


def load_dim_basket(cur):
    """One row per trip, with its value, size and segment precomputed.

    Segment thresholds match notebook 03 Chart 9 and notebooks 11 and 12.
    """
    cur.execute("""
        INSERT INTO warehouse.dim_basket
            (invoice_no, date_key, basket_value, n_items, n_categories, basket_segment)
        SELECT
            t.invoice_no,
            TO_CHAR(t.txn_date, 'YYYYMMDD')::INTEGER,
            SUM(i.total_amount),
            COUNT(*),
            COUNT(DISTINCT p.category),
            CASE
                WHEN SUM(i.total_amount) < 500  THEN 'Small'
                WHEN SUM(i.total_amount) <= 2000 THEN 'Medium'
                ELSE 'Large'
            END
        FROM oltp.transactions t
        JOIN oltp.transaction_items i ON i.transaction_id = t.transaction_id
        JOIN oltp.products p          ON p.product_id     = i.product_id
        GROUP BY t.invoice_no, t.txn_date
        ON CONFLICT (invoice_no) DO NOTHING;
    """)
    return cur.rowcount


def load_fact_sales(cur):
    """The fact table. Same grain as oltp.transaction_items."""
    cur.execute("""
        INSERT INTO warehouse.fact_sales (
            date_key, product_key, category_key, basket_key, line_no,
            quantity, unit_price, base_amount, vat, total_amount
        )
        SELECT
            b.date_key, dp.product_key, dp.category_key, b.basket_key, i.line_no,
            i.quantity, i.unit_price, i.base_amount, i.vat, i.total_amount
        FROM oltp.transaction_items i
        JOIN oltp.transactions t  ON t.transaction_id = i.transaction_id
        JOIN oltp.products     p  ON p.product_id     = i.product_id
        JOIN warehouse.dim_basket  b  ON b.invoice_no   = t.invoice_no
        JOIN warehouse.dim_product dp ON dp.product_name = p.product_name
        ON CONFLICT (basket_key, line_no) DO NOTHING;
    """)
    return cur.rowcount


STEPS = [
    ("dim_date", load_dim_date),
    ("dim_category", load_dim_category),
    ("dim_product", load_dim_product),
    ("dim_basket", load_dim_basket),
    ("fact_sales", load_fact_sales),
]


def main():
    log("=" * 70)
    log("LOAD STAR SCHEMA WAREHOUSE FROM OLTP")
    log("=" * 70)
    log(f"Target : {db.describe()}")

    conn = psycopg2.connect(**db.connection_kwargs())
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM oltp.transaction_items")
    oltp_items = cur.fetchone()[0]
    if oltp_items == 0:
        log("\nERROR: the OLTP schema is empty.")
        log("Run scripts/load_to_postgres.py first.")
        cur.close()
        conn.close()
        return 1
    log(f"Source : oltp.transaction_items has {oltp_items:,} rows")

    log("\n[1/3] Creating warehouse schema and views if needed...")
    with open(DDL_PATH, encoding="utf-8") as fh:
        cur.execute(fh.read())
    conn.commit()
    log("      warehouse schema and 7 serving views ready.")

    log("\n[2/3] Loading dimensions then the fact table...")
    inserted_total = 0
    for name, fn in STEPS:
        t0 = time.time()
        n = fn(cur)
        conn.commit()
        inserted_total += n
        log(f"      {name:14} inserted {n:>9,} rows in {time.time() - t0:5.1f}s")

    log("\n[3/3] Verifying the warehouse against expected row counts...")
    all_ok = True
    for table, expected in EXPECTED.items():
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        actual = cur.fetchone()[0]
        ok = actual == expected
        all_ok = all_ok and ok
        log(f"      [{'PASS' if ok else 'FAIL'}] {table:26} {actual:>9,} (expected {expected:,})")

    # The fact table must reconcile with the source it was built from.
    cur.execute("SELECT COUNT(*) FROM warehouse.fact_sales")
    fact_rows = cur.fetchone()[0]
    grain_ok = fact_rows == oltp_items
    all_ok = all_ok and grain_ok
    log(f"      [{'PASS' if grain_ok else 'FAIL'}] fact grain matches OLTP     "
        f"{fact_rows:,} vs {oltp_items:,}")

    cur.execute("""
        SELECT ROUND(ABS(
            (SELECT SUM(total_amount) FROM warehouse.fact_sales) -
            (SELECT SUM(total_amount) FROM oltp.transaction_items)
        ), 4)
    """)
    revenue_gap = float(cur.fetchone()[0])
    revenue_ok = revenue_gap < 0.01
    all_ok = all_ok and revenue_ok
    log(f"      [{'PASS' if revenue_ok else 'FAIL'}] revenue reconciles to OLTP  "
        f"difference Rs {revenue_gap}")

    cur.close()
    conn.close()

    log()
    log("=" * 70)
    if all_ok:
        log("WAREHOUSE LOAD COMPLETE. Star schema matches the OLTP source.")
        if inserted_total == 0:
            log("Nothing was inserted this run: the warehouse was already built.")
            log("This confirms the ETL is idempotent.")
        log("=" * 70)
        return 0
    log("WAREHOUSE LOAD FAILED verification. See FAIL lines above.")
    log("=" * 70)
    return 1


if __name__ == "__main__":
    sys.exit(main())
