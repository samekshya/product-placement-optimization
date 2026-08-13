-- =====================================================================
-- OLTP schema for the Product Placement Optimisation project
-- Student: Samikshya Baniya | ID: 230360 | Module: ST6001CEM
-- =====================================================================
--
-- This is the transactional (normalised) layer. It stores the store's Point
-- of Sale history as it actually happened: one row per product sold, grouped
-- into invoices, referencing a product catalogue.
--
-- Source: data/processed/sales_data_cleaned.csv (767,180 line items)
--
-- Expected after a successful load:
--     products            5,680 rows
--     transactions      218,037 rows
--     transaction_items 767,180 rows
--
-- Three design decisions are driven by facts measured in the source data,
-- not by convention. Each is commented at the table it affects.
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS oltp;

-- ---------------------------------------------------------------------
-- products: the store's catalogue
-- ---------------------------------------------------------------------
-- Verified in the source data: every product name maps to exactly one
-- category, one product_group and one product_group_clean (0 violations),
-- so those attributes belong here.
--
-- 'unit' is deliberately NOT stored here. 356 products are sold in more
-- than one unit (for example both PCS and KG), so unit is a property of
-- the individual sale, not of the product. It lives on transaction_items.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS oltp.products (
    product_id          SERIAL       PRIMARY KEY,
    product_name        VARCHAR(100) NOT NULL UNIQUE,
    product_group       VARCHAR(50)  NOT NULL,
    product_group_clean VARCHAR(50)  NOT NULL,
    category            VARCHAR(50)  NOT NULL
);

-- ---------------------------------------------------------------------
-- transactions: one shopping trip (one invoice)
-- ---------------------------------------------------------------------
-- Verified in the source data: each invoice_no maps to exactly one date
-- and one customer (0 violations), so invoice_no is a sound natural key
-- and the date/customer attributes belong at this level rather than on
-- the line items.
--
-- 'customer' is almost always the literal 'CASH A/C'. It is retained
-- because it is what the POS recorded, and it carries no personal data:
-- 98% of trips are anonymous cash sales.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS oltp.transactions (
    transaction_id SERIAL      PRIMARY KEY,
    invoice_no     VARCHAR(20) NOT NULL UNIQUE,
    txn_date       DATE        NOT NULL,
    date_nepali    VARCHAR(10),
    customer       VARCHAR(60)
);

-- ---------------------------------------------------------------------
-- transaction_items: one product sold on one invoice
-- ---------------------------------------------------------------------
-- line_no exists for a measured reason. 1,587 invoice+product combinations
-- legitimately appear more than once on the same invoice (up to 4 times),
-- for example the same item rung up separately at different prices. That
-- means (transaction_id, product_id) is NOT unique and cannot be the key.
--
-- line_no is assigned from the source row order within each invoice, which
-- restores a stable natural key: (transaction_id, line_no). That key is what
-- makes reloading idempotent, so re-running the pipeline inserts nothing
-- twice instead of duplicating 767,180 rows.
--
-- quantity is NUMERIC, not INTEGER: the store sells fractional quantities
-- (the minimum observed is 0.05).
--
-- vat is nullable: 157 source rows have no VAT recorded. Storing those as
-- NULL is honest; storing them as 0 would silently invent data.
--
-- The scale of 6 on the money columns is measured, not arbitrary. total_amount
-- carries up to 6 decimal places in the source (2.9% of rows), and unit_price
-- up to 7. Storing money at the more usual scale of 4 rounds those values, and
-- because 978 baskets sit within Rs 0.1 of the Rs 500 segment boundary, that
-- rounding moves 2 baskets from Medium to Small and changes total revenue by
-- 1 paisa. Scale 6 (and 8 for unit_price) reproduces the notebook figures
-- exactly: 108,349 Small / 79,868 Medium / 29,820 Large, Rs 218,214,456.88.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS oltp.transaction_items (
    item_id        BIGSERIAL      PRIMARY KEY,
    transaction_id INTEGER        NOT NULL REFERENCES oltp.transactions(transaction_id),
    product_id     INTEGER        NOT NULL REFERENCES oltp.products(product_id),
    line_no        SMALLINT       NOT NULL,
    unit           VARCHAR(10),
    quantity       NUMERIC(18, 6) NOT NULL,
    unit_price     NUMERIC(18, 8) NOT NULL,
    base_amount    NUMERIC(18, 6) NOT NULL,
    vat            NUMERIC(18, 6),
    total_amount   NUMERIC(18, 6) NOT NULL,
    CONSTRAINT uq_transaction_line UNIQUE (transaction_id, line_no)
);

-- ---------------------------------------------------------------------
-- Indexes for the aggregate queries the warehouse ETL and dashboard run
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_items_transaction ON oltp.transaction_items(transaction_id);
CREATE INDEX IF NOT EXISTS idx_items_product     ON oltp.transaction_items(product_id);
CREATE INDEX IF NOT EXISTS idx_txn_date          ON oltp.transactions(txn_date);
CREATE INDEX IF NOT EXISTS idx_products_category ON oltp.products(category);
