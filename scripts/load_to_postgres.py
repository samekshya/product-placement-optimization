"""
load_to_postgres.py

Loads the cleaned Point of Sale CSV into the Postgres OLTP schema.

    python scripts/load_to_postgres.py

What it does:
    1. Creates the oltp schema if it does not exist (runs sql/01_create_oltp.sql)
    2. Loads products, transactions and transaction_items
    3. Asserts the row counts match the verified numbers in the thesis

Idempotency:
    Re-running this script inserts nothing a second time. Rows are staged with
    COPY into TEMP tables and then moved across with ON CONFLICT DO NOTHING
    against each table's natural key:

        products          product_name
        transactions      invoice_no
        transaction_items (transaction_id, line_no)

    line_no is derived from source row order within each invoice. It exists
    because 1,587 invoice+product combinations legitimately repeat on the same
    invoice, so product alone cannot identify a line. See sql/01_create_oltp.sql.

Why COPY into a staging table rather than executemany:
    767,180 rows. COPY moves them in seconds; row-by-row inserts take minutes.
    Staging first is what lets us keep COPY's speed and still get ON CONFLICT.

This script reads data/processed/sales_data_cleaned.csv and never modifies it.
"""

import io
import os
import sys
import time

import pandas as pd
import psycopg2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from config import db  # noqa: E402

CSV_PATH = os.path.join(ROOT, "data", "processed", "sales_data_cleaned.csv")
DDL_PATH = os.path.join(ROOT, "sql", "01_create_oltp.sql")

EXPECTED_PRODUCTS = 5680
EXPECTED_TRANSACTIONS = 218037
EXPECTED_ITEMS = 767180


def log(msg=""):
    print(msg, flush=True)


def copy_into(cur, df, table, columns):
    """Stream a dataframe into an existing table using COPY."""
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, columns=columns, na_rep="\\N")
    buf.seek(0)
    cur.copy_expert(
        f"COPY {table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv, NULL '\\N')",
        buf,
    )


def main():
    log("=" * 70)
    log("LOAD CLEANED POS DATA INTO POSTGRES OLTP")
    log("=" * 70)
    log(f"Target : {db.describe()}")
    log(f"Source : {CSV_PATH}")

    if not os.path.exists(CSV_PATH):
        log("\nERROR: cleaned CSV not found.")
        log("Run notebooks 01 and 02 first to produce it.")
        return 1

    # -- Step 1: schema -------------------------------------------------
    log("\n[1/5] Creating schema if needed...")
    with open(DDL_PATH, encoding="utf-8") as fh:
        ddl = fh.read()

    conn = psycopg2.connect(**db.connection_kwargs())
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute(ddl)
    conn.commit()
    log("      oltp schema ready.")

    # -- Step 2: read and shape ----------------------------------------
    log("\n[2/5] Reading cleaned CSV...")
    t0 = time.time()
    df = pd.read_csv(CSV_PATH)
    log(f"      {len(df):,} rows read in {time.time() - t0:.1f}s")

    df["date"] = pd.to_datetime(df["date"]).dt.date

    # line_no restores a stable natural key for the line items.
    df["line_no"] = df.groupby("invoice_no").cumcount() + 1

    products = (
        df[["product", "product_group", "product_group_clean", "category"]]
        .drop_duplicates(subset=["product"])
        .rename(columns={"product": "product_name"})
        .sort_values("product_name")
    )
    transactions = (
        df[["invoice_no", "date", "date_nepali", "customer"]]
        .drop_duplicates(subset=["invoice_no"])
        .rename(columns={"date": "txn_date"})
        .sort_values("invoice_no")
    )
    log(f"      {len(products):,} distinct products")
    log(f"      {len(transactions):,} distinct transactions")

    # -- Step 3: products and transactions ------------------------------
    log("\n[3/5] Loading products and transactions...")
    cur.execute("""
        CREATE TEMP TABLE stg_products (
            product_name VARCHAR(100), product_group VARCHAR(50),
            product_group_clean VARCHAR(50), category VARCHAR(50)
        ) ON COMMIT DROP;
        CREATE TEMP TABLE stg_transactions (
            invoice_no VARCHAR(20), txn_date DATE,
            date_nepali VARCHAR(10), customer VARCHAR(60)
        ) ON COMMIT DROP;
    """)

    copy_into(cur, products, "stg_products",
              ["product_name", "product_group", "product_group_clean", "category"])
    copy_into(cur, transactions, "stg_transactions",
              ["invoice_no", "txn_date", "date_nepali", "customer"])

    cur.execute("""
        INSERT INTO oltp.products (product_name, product_group, product_group_clean, category)
        SELECT product_name, product_group, product_group_clean, category FROM stg_products
        ON CONFLICT (product_name) DO NOTHING;
    """)
    inserted_products = cur.rowcount
    cur.execute("""
        INSERT INTO oltp.transactions (invoice_no, txn_date, date_nepali, customer)
        SELECT invoice_no, txn_date, date_nepali, customer FROM stg_transactions
        ON CONFLICT (invoice_no) DO NOTHING;
    """)
    inserted_txns = cur.rowcount
    log(f"      products inserted this run     : {inserted_products:,}")
    log(f"      transactions inserted this run : {inserted_txns:,}")

    # -- Step 4: line items ---------------------------------------------
    log("\n[4/5] Loading transaction items (767,180 rows, this is the slow one)...")
    t0 = time.time()
    cur.execute("""
        CREATE TEMP TABLE stg_items (
            invoice_no VARCHAR(20), product_name VARCHAR(100), line_no SMALLINT,
            unit VARCHAR(10), quantity NUMERIC(18,6), unit_price NUMERIC(18,8),
            base_amount NUMERIC(18,6), vat NUMERIC(18,6), total_amount NUMERIC(18,6)
        ) ON COMMIT DROP;
    """)

    items = df.rename(columns={"product": "product_name"})
    copy_into(cur, items, "stg_items",
              ["invoice_no", "product_name", "line_no", "unit", "quantity",
               "unit_price", "base_amount", "vat", "total_amount"])
    log(f"      staged in {time.time() - t0:.1f}s, resolving foreign keys...")

    cur.execute("""
        INSERT INTO oltp.transaction_items (
            transaction_id, product_id, line_no, unit,
            quantity, unit_price, base_amount, vat, total_amount
        )
        SELECT t.transaction_id, p.product_id, s.line_no, s.unit,
               s.quantity, s.unit_price, s.base_amount, s.vat, s.total_amount
        FROM stg_items s
        JOIN oltp.transactions t ON t.invoice_no   = s.invoice_no
        JOIN oltp.products     p ON p.product_name = s.product_name
        ON CONFLICT (transaction_id, line_no) DO NOTHING;
    """)
    inserted_items = cur.rowcount
    conn.commit()
    log(f"      items inserted this run        : {inserted_items:,}")
    log(f"      completed in {time.time() - t0:.1f}s")

    # -- Step 5: verify --------------------------------------------------
    log("\n[5/5] Verifying row counts against the thesis numbers...")
    checks = [
        ("oltp.products", EXPECTED_PRODUCTS),
        ("oltp.transactions", EXPECTED_TRANSACTIONS),
        ("oltp.transaction_items", EXPECTED_ITEMS),
    ]
    all_ok = True
    for table, expected in checks:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        actual = cur.fetchone()[0]
        ok = actual == expected
        all_ok = all_ok and ok
        log(f"      [{'PASS' if ok else 'FAIL'}] {table:26} {actual:>9,} (expected {expected:,})")

    cur.execute("SELECT COALESCE(SUM(total_amount), 0) FROM oltp.transaction_items")
    revenue = float(cur.fetchone()[0])
    # Tight tolerance: at NUMERIC scale 6 the stored sum is 218,214,456.878649,
    # which rounds to the thesis figure exactly. A wider tolerance would hide
    # precision loss rather than catch it.
    revenue_ok = abs(revenue - 218214456.88) < 0.01
    all_ok = all_ok and revenue_ok
    log(f"      [{'PASS' if revenue_ok else 'FAIL'}] total revenue              "
        f"Rs {revenue:,.2f} (expected Rs 218,214,456.88)")

    cur.close()
    conn.close()

    log()
    log("=" * 70)
    if all_ok:
        log("OLTP LOAD COMPLETE. All row counts match.")
        if inserted_items == 0 and inserted_txns == 0 and inserted_products == 0:
            log("Nothing was inserted this run: the database was already loaded.")
            log("This confirms the load is idempotent.")
        log("=" * 70)
        return 0
    log("OLTP LOAD FAILED verification. See FAIL lines above.")
    log("=" * 70)
    return 1


if __name__ == "__main__":
    sys.exit(main())
