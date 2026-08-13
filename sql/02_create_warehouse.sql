-- =====================================================================
-- Star schema warehouse for the Product Placement Optimisation project
-- Student: Samikshya Baniya | ID: 230360 | Module: ST6001CEM
-- =====================================================================
--
-- The OLTP schema stores the data as the shop recorded it, normalised for
-- correctness. This warehouse restructures the same facts for analysis:
-- one central fact table surrounded by dimensions, so questions like
-- "revenue by zone by month" are a single join rather than a nest of
-- subqueries.
--
--                      dim_date
--                          |
--     dim_product ---- fact_sales ---- dim_basket
--                          |
--                     dim_category
--
-- Expected after a successful load:
--     dim_date         304 rows (distinct trading days)
--     dim_category      25 rows
--     dim_product    5,680 rows
--     dim_basket   218,037 rows
--     fact_sales   767,180 rows
--
-- What makes this warehouse specific to THIS research:
--     dim_category.zone_assignment carries the 5 placement zones derived in
--     notebook 07 from the association rules and co-occurrence clustering.
--     Storing the research finding as a dimension attribute means the
--     recommended layout can be queried directly. "What revenue would
--     Zone 1 carry?" becomes a GROUP BY rather than a separate analysis.
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS warehouse;

-- ---------------------------------------------------------------------
-- dim_date: one row per trading day
-- ---------------------------------------------------------------------
-- is_festival_season flags September and October, the Dashain and Tihar
-- period identified in notebook 07 as the store's revenue peak
-- (September 2025 was the highest month at Rs 23.3 million).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS warehouse.dim_date (
    date_key           INTEGER     PRIMARY KEY,   -- YYYYMMDD
    full_date          DATE        NOT NULL UNIQUE,
    date_nepali        VARCHAR(10),
    day_of_week        SMALLINT    NOT NULL,      -- 1 = Monday
    day_name           VARCHAR(10) NOT NULL,
    month_number       SMALLINT    NOT NULL,
    month_name         VARCHAR(10) NOT NULL,
    year_number        SMALLINT    NOT NULL,
    year_month         VARCHAR(7)  NOT NULL,      -- YYYY-MM
    is_weekend_nepal   BOOLEAN     NOT NULL,      -- Saturday is the Nepali weekend
    is_festival_season BOOLEAN     NOT NULL
);

-- ---------------------------------------------------------------------
-- dim_category: the 25 categories, carrying the research finding
-- ---------------------------------------------------------------------
-- zone_assignment and zone_location come from notebook 07. This is the
-- column that ties the warehouse to the dissertation's recommendation.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS warehouse.dim_category (
    category_key    SERIAL      PRIMARY KEY,
    category_name   VARCHAR(50) NOT NULL UNIQUE,
    zone_assignment VARCHAR(30) NOT NULL,
    zone_label      VARCHAR(30) NOT NULL,
    zone_location   VARCHAR(30) NOT NULL
);

-- ---------------------------------------------------------------------
-- dim_product: the catalogue, conformed to its category
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS warehouse.dim_product (
    product_key   SERIAL       PRIMARY KEY,
    product_name  VARCHAR(100) NOT NULL UNIQUE,
    product_group VARCHAR(50)  NOT NULL,
    category_key  INTEGER      NOT NULL REFERENCES warehouse.dim_category(category_key)
);

-- ---------------------------------------------------------------------
-- dim_basket: one row per shopping trip
-- ---------------------------------------------------------------------
-- basket_segment uses the same Rs 500 / Rs 2,000 thresholds as notebook 03
-- Chart 9 and the classifiers in notebooks 11 and 12, so the segment counts
-- in SQL agree with the segment counts in the notebooks by construction
-- rather than by coincidence.
-- ---------------------------------------------------------------------
-- basket_value uses scale 6 for the reason documented in 01_create_oltp.sql:
-- at scale 4 the rounding moves 2 baskets across the Rs 500 boundary and the
-- SQL segment counts stop agreeing with the notebooks.
CREATE TABLE IF NOT EXISTS warehouse.dim_basket (
    basket_key     SERIAL         PRIMARY KEY,
    invoice_no     VARCHAR(20)    NOT NULL UNIQUE,
    date_key       INTEGER        NOT NULL REFERENCES warehouse.dim_date(date_key),
    basket_value   NUMERIC(18, 6) NOT NULL,
    n_items        SMALLINT       NOT NULL,
    n_categories   SMALLINT       NOT NULL,
    basket_segment VARCHAR(10)    NOT NULL
);

-- ---------------------------------------------------------------------
-- fact_sales: the grain is one product sold on one invoice
-- ---------------------------------------------------------------------
-- Same grain as oltp.transaction_items, so fact_sales must contain exactly
-- 767,180 rows. Any other number means the ETL dropped or duplicated rows,
-- which is what the quality checks look for.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS warehouse.fact_sales (
    sales_key    BIGSERIAL      PRIMARY KEY,
    date_key     INTEGER        NOT NULL REFERENCES warehouse.dim_date(date_key),
    product_key  INTEGER        NOT NULL REFERENCES warehouse.dim_product(product_key),
    category_key INTEGER        NOT NULL REFERENCES warehouse.dim_category(category_key),
    basket_key   INTEGER        NOT NULL REFERENCES warehouse.dim_basket(basket_key),
    line_no      SMALLINT       NOT NULL,
    quantity     NUMERIC(18, 6) NOT NULL,
    unit_price   NUMERIC(18, 8) NOT NULL,
    base_amount  NUMERIC(18, 6) NOT NULL,
    vat          NUMERIC(18, 6),
    total_amount NUMERIC(18, 6) NOT NULL,
    CONSTRAINT uq_fact_basket_line UNIQUE (basket_key, line_no)
);

CREATE INDEX IF NOT EXISTS idx_fact_date     ON warehouse.fact_sales(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_product  ON warehouse.fact_sales(product_key);
CREATE INDEX IF NOT EXISTS idx_fact_category ON warehouse.fact_sales(category_key);
CREATE INDEX IF NOT EXISTS idx_fact_basket   ON warehouse.fact_sales(basket_key);
CREATE INDEX IF NOT EXISTS idx_basket_date   ON warehouse.dim_basket(date_key);

-- =====================================================================
-- Serving views. The dashboard reads these instead of querying the star
-- directly, so the SQL lives in one place and the dashboard stays readable.
-- =====================================================================

-- Headline KPIs, one row. Mirrors dashboard/artifacts/kpi_summary.json.
CREATE OR REPLACE VIEW warehouse.v_kpi_summary AS
SELECT
    (SELECT COUNT(*) FROM warehouse.dim_basket)                      AS total_transactions,
    (SELECT ROUND(SUM(total_amount), 2) FROM warehouse.fact_sales)   AS total_revenue,
    (SELECT ROUND(AVG(basket_value), 2) FROM warehouse.dim_basket)   AS avg_basket_value,
    (SELECT ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY basket_value)::NUMERIC, 2)
       FROM warehouse.dim_basket)                                    AS median_basket_value,
    (SELECT COUNT(*) FROM warehouse.dim_category)                    AS n_categories,
    (SELECT COUNT(*) FROM warehouse.dim_product)                     AS n_products,
    (SELECT COUNT(*) FROM warehouse.dim_date)                        AS trading_days;

-- Revenue and trips per calendar month.
CREATE OR REPLACE VIEW warehouse.v_monthly_revenue AS
SELECT d.year_month,
       ROUND(SUM(f.total_amount), 2)     AS revenue,
       COUNT(DISTINCT f.basket_key)      AS transactions,
       ROUND(SUM(f.total_amount) / NULLIF(COUNT(DISTINCT f.basket_key), 0), 2) AS avg_basket
FROM warehouse.fact_sales f
JOIN warehouse.dim_date d ON d.date_key = f.date_key
GROUP BY d.year_month
ORDER BY d.year_month;

-- Category performance, carrying the zone each category is assigned to.
CREATE OR REPLACE VIEW warehouse.v_category_performance AS
SELECT c.category_name,
       c.zone_assignment,
       c.zone_location,
       ROUND(SUM(f.total_amount), 2)  AS revenue,
       COUNT(DISTINCT f.basket_key)   AS baskets,
       ROUND(100.0 * COUNT(DISTINCT f.basket_key)
             / (SELECT COUNT(*) FROM warehouse.dim_basket), 2) AS basket_penetration_pct
FROM warehouse.fact_sales f
JOIN warehouse.dim_category c ON c.category_key = f.category_key
GROUP BY c.category_name, c.zone_assignment, c.zone_location
ORDER BY revenue DESC;

-- Revenue by placement zone. This is the query the OLTP layer could not
-- answer at all, and it exists because the research finding is stored as
-- a dimension attribute.
CREATE OR REPLACE VIEW warehouse.v_zone_performance AS
SELECT c.zone_assignment,
       c.zone_label,
       c.zone_location,
       COUNT(DISTINCT c.category_name) AS n_categories,
       ROUND(SUM(f.total_amount), 2)   AS revenue,
       ROUND(100.0 * SUM(f.total_amount)
             / SUM(SUM(f.total_amount)) OVER (), 2) AS revenue_share_pct,
       COUNT(DISTINCT f.basket_key)    AS baskets
FROM warehouse.fact_sales f
JOIN warehouse.dim_category c ON c.category_key = f.category_key
GROUP BY c.zone_assignment, c.zone_label, c.zone_location
ORDER BY c.zone_assignment;

-- Basket size segments. Reproduces notebook 03 Chart 9 in SQL.
CREATE OR REPLACE VIEW warehouse.v_basket_segments AS
SELECT basket_segment,
       COUNT(*)                        AS baskets,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS share_of_baskets_pct,
       ROUND(SUM(basket_value), 2)     AS revenue,
       ROUND(100.0 * SUM(basket_value) / SUM(SUM(basket_value)) OVER (), 2) AS share_of_revenue_pct,
       ROUND(AVG(basket_value), 2)     AS avg_basket_value
FROM warehouse.dim_basket
GROUP BY basket_segment;

-- Revenue by day of week. Reproduces notebook 03 Chart 11 in SQL.
CREATE OR REPLACE VIEW warehouse.v_day_of_week AS
SELECT d.day_of_week,
       d.day_name,
       ROUND(SUM(f.total_amount), 2)   AS revenue,
       COUNT(DISTINCT f.basket_key)    AS transactions,
       ROUND(SUM(f.total_amount) / NULLIF(COUNT(DISTINCT f.basket_key), 0), 2) AS avg_basket
FROM warehouse.fact_sales f
JOIN warehouse.dim_date d ON d.date_key = f.date_key
GROUP BY d.day_of_week, d.day_name
ORDER BY d.day_of_week;

-- Top products by revenue, with their zone.
CREATE OR REPLACE VIEW warehouse.v_top_products AS
SELECT p.product_name,
       c.category_name,
       c.zone_assignment,
       ROUND(SUM(f.total_amount), 2) AS revenue,
       COUNT(DISTINCT f.basket_key)  AS transactions,
       ROUND(SUM(f.quantity), 2)     AS units_sold
FROM warehouse.fact_sales f
JOIN warehouse.dim_product  p ON p.product_key  = f.product_key
JOIN warehouse.dim_category c ON c.category_key = f.category_key
GROUP BY p.product_name, c.category_name, c.zone_assignment
-- product_name is a deliberate tiebreaker, not decoration. Many products share
-- an identical revenue total, and without a second sort key Postgres may return
-- tied rows in a different order on each run, which would make the generated
-- ABC artifact churn between pipeline runs for no real reason.
ORDER BY revenue DESC, product_name;
