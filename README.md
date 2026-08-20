# Data Analytics and ML Based Product Placement Optimisation
### The case study store, Pokhara, Nepal

**Student:** Samikshya Baniya | **ID:** 230360
**Module:** ST6001CEM Individual Project
**University:** Softwarica College / Coventry University

---

## Project Overview

This project analyses 11 calendar months of real Point of Sale data (17 July 2025 to 20 May 2026, both ends partial) from a Nepali grocery store to find which products are bought together and recommend how to rearrange shelves to increase sales.

**Primary KPI:** Average basket value baseline = Rs 1,001
**Projected impact:** Rs 1.30 Crore additional annual revenue at 5% uplift

---

## Key Findings

- Best association rule: Lift of 6.81 meaning customers are 6.8x more likely to buy these categories together than by random chance
- Strongest connection: CLEANING SUPPLIES connects all core categories
- Top product pair: Kalo Dal and Rato Dal bought together 3,989 times
- Highest revenue month: September 2025 (Festival/Dashain season) at Rs 23.3 Million
- Recommended store center: Daily Essentials Zone (Food Staples, Cooking Oil, Cleaning Supplies, Tea and Spices, Household Items)

---

## Dataset

| Property | Value |
|----------|-------|
| Source | Real POS data, the case study store, Pokhara |
| Raw Size | 768,222 rows, 14 columns |
| After Cleaning | 767,180 rows, 14 columns |
| Period | 17 July 2025 to 20 May 2026 (11 calendar months, both ends partial) |
| Span | 307 days, of which 304 had sales |
| Unique Transactions | 218,037 shopping trips |
| Unique Products | 5,681 |
| Categories | 25 standardized |

> Data used with permission from store management for academic research purposes only. All customer data is anonymized.

---

## Ethics and Data Use (Objective 5)

**Data provenance and consent.** This study uses **primary data** collected from the
student's own family-run store (Pokhara). The data was
obtained and used **with the explicit permission of store management**, for academic research
only. It is **not faculty-provided / secondary data** - any earlier note describing it that way
is incorrect and is corrected here: the dataset is primary data gathered directly from the store's
Point of Sale system.

**Privacy and anonymisation.** 98% of transactions are cash sales (`CASH A/C`) with no customer
identity attached, so no individual can be re-identified. No names, phone numbers, addresses or
loyalty IDs are stored or analysed - only product-level basket contents and amounts. The raw Excel
file and the 114 MB cleaned CSV are kept out of version control (gitignored); only small aggregated
artifacts are published with the dashboard.

**Honest reporting.** All association, clustering and basket figures are measured directly from the
data. The 3% / 5% / 8% revenue uplift is clearly labelled as a **projection** based on retail-industry
benchmarks, not the outcome of a live in-store experiment. The cross-sell before/after result
(notebook 07) is data-driven, computed from the association rules; only its rupee conversion is a
projection.

---

## Project Structure
product-placement-optimization/
├── data/
│   ├── raw/                    (original Excel file - not on GitHub)
│   └── processed/              (cleaned CSV files - not on GitHub)
├── notebooks/
│   ├── 01_data_audit.ipynb
│   ├── 02_data_cleaning.ipynb
│   ├── 03_eda.ipynb
│   ├── 04_transaction_encoding.ipynb
│   ├── 05_market_basket_analysis.ipynb
│   ├── 06_clustering.ipynb
│   ├── 07_placement_simulation.ipynb   (includes ADDED cross-sell before/after)
│   ├── 08_evaluation.ipynb
│   ├── 09_ml_recommendation.ipynb
│   ├── 10_demand_forecasting.ipynb
│   ├── 11_basket_classifier.ipynb      (Decision Tree)
│   ├── 12_neural_network.ipynb         (MLP, compared against the tree)
│   ├── 13_daily_forecasting.ipynb      (notebook 10 refitted at daily granularity)
│   └── 14_richer_basket_features.ipynb (notebooks 11 and 12 with richer features)
├── analysis/                   (shared analysis code, imported by notebooks, dashboard, app and tests)
│   ├── cross_sell.py           (the ONE cross-sell capture scorer behind the 28 / 56 result)
│   ├── zones.py                (the five placement zones and their ethics classification)
│   ├── optimise_zones.py       (computed zone assignment: local search + exhaustive certificate)
│   ├── daily_forecast.py       (daily revenue series, baselines, regression, Prophet)
│   ├── basket_features.py      (richer basket features, ceiling and retrained models)
│   └── tests/                  (pytest suite for the three modules above)
├── app/                        (interactive shelf layout tool: FastAPI + React, see app/README.md)
├── sql/
│   ├── 01_create_oltp.sql      (products, transactions, transaction_items)
│   └── 02_create_warehouse.sql (star schema + 7 serving views)
├── scripts/
│   ├── load_to_postgres.py     (cleaned CSV -> OLTP)
│   ├── verify_thesis_numbers.py (every reported figure checked against a live source)
│   └── run_verifications.py    (runs all three verification scripts, writes reports/verification_status.json)
├── etl/
│   ├── load_warehouse.py       (OLTP -> star schema)
│   ├── quality_checks.py       (32 data quality checks)
│   └── refresh_artifacts.py    (warehouse -> dashboard artifacts)
├── dags/
│   └── product_placement_pipeline.py   (Airflow DAG, 5 tasks)
├── config/
│   ├── db.py                   (database connection settings)
│   └── metrics.py              (single source of truth for verified numbers)
├── dashboard/
│   ├── app.py                  (Streamlit dashboard, live Postgres or artifacts)
│   ├── precompute_artifacts.py (builds the small artifacts from processed data)
│   └── artifacts/              (small precomputed files committed for the dashboard)
├── reports/
│   └── figures/                (all charts and visualizations)
├── docker-compose.yml          (Postgres 16 + Airflow 3.3.0 LocalExecutor)
├── reproduce_all_results.py    (verifies every reported number, one command)
├── pytest.ini                  (python -m pytest runs the whole test suite)
├── requirements.txt
└── README.md
---

## How to Run

**Step 1: Clone the repository**
git clone https://github.com/samekshya/product-placement-optimization.git

**Step 2: Create virtual environment**
python -m venv venv
venv\Scripts\activate

**Step 3: Install required libraries**
pip install -r requirements.txt

**Step 4: Add the raw data file**
Place sales_data_raw.xlsx inside the data/raw/ folder.
This file is not on GitHub as it contains confidential store data.

**Step 5: Run notebooks in order**
Run from 01_data_audit.ipynb through to 12_neural_network.ipynb.
Each notebook builds on the previous one.

---

## Run the Dashboard

The dashboard runs entirely from the small precomputed files in `dashboard/artifacts/`,
so a marker can launch it from a fresh clone **without** the confidential CSV and without
re-running Apriori:

```
pip install -r requirements.txt
streamlit run dashboard/app.py
```

It opens on a landing page ("The Result") and then offers two modes: **Store Owner**
(three pages) and **Examiner** (eight pages, including live verification status). Pages
are titled as the question each answers, with the former topic name and dissertation
section number kept as the subtitle. All charts are interactive (hover/zoom) and the
layout works in both light and dark themes.

To rebuild the artifacts after re-running the notebooks (requires the processed CSVs):

```
python dashboard/precompute_artifacts.py
```

---

## Run the Data Platform (Postgres + Airflow)

The project also ships a full data platform: a Postgres OLTP schema, a star schema warehouse and an
Airflow DAG that orchestrates the load. This is optional for viewing the dashboard, which falls back
to the committed artifacts, but it is what feeds the dashboard's live mode.

**Start everything** (needs Docker Desktop):

```
docker compose up -d
```

| Service | URL | Login |
|---------|-----|-------|
| Airflow UI | http://localhost:8082 | airflow / airflow |
| Postgres | localhost:5435 | postgres / postgres |

Ports are non-default on purpose to avoid clashing with other stacks.

**Run the pipeline.** The DAG `product_placement_pipeline` is unpaused and runs daily, or trigger it
from the Airflow UI. Five tasks run in order:

```
load_raw_to_oltp >> oltp_to_warehouse >> run_quality_checks >> update_artifacts >> done
```

Re-running is safe. Every load uses `ON CONFLICT DO NOTHING` against a natural key, so a second run
inserts nothing and no row count moves.

**Or run each step by hand**, without Airflow:

```
python scripts/load_to_postgres.py     # cleaned CSV  -> OLTP     (767,180 line items)
python etl/load_warehouse.py           # OLTP         -> warehouse (star schema)
python etl/quality_checks.py           # 32 data quality checks
python etl/refresh_artifacts.py        # warehouse    -> dashboard artifacts
```

**Verify every number in the report with one command:**

```
python reproduce_all_results.py
```

It regenerates every artifact (including the three extension studies below), runs 26 checks across
12 steps, calls the full thesis-number sweep as its last step, saves a timestamped log to `reports/`,
and exits 0 only if every check passes.

```
python scripts/verify_thesis_numbers.py   # every reported figure against a live source (263 checkable)
python etl/quality_checks.py              # 32 warehouse quality checks
python -m pytest                          # 54 tests: app, dashboard and the analysis modules
python scripts/run_verifications.py       # all three scripts, status written to reports/verification_status.json
```

---

## Algorithms Used

| Algorithm | Type | Purpose |
|-----------|------|---------|
| Apriori | Unsupervised ML | Find frequent itemsets and association rules |
| FP-Growth | Unsupervised ML | Faster association rule mining for comparison |
| K-Means | Unsupervised ML | Group categories into natural placement zones |
| Linear Regression | Supervised ML | Forecast monthly revenue from the trend |
| Prophet | Supervised ML | Forecast revenue including the Dashain seasonal peak |
| Decision Tree | Supervised ML | Identify which categories predict basket value |
| MLP Neural Network | Supervised ML | Test whether more model capacity beats the tree |
| Greedy local search with random restarts | Optimisation | Find the best category-to-zone assignment under the cross-sell metric, certified by exhaustive enumeration |
| Naive baselines, day-of-week regression, Prophet (daily) | Supervised ML | Refit the forecasting question on 304 daily observations |

---

## Results Summary

| Metric | Value |
|--------|-------|
| Total association rules found | 1,228 |
| Strong rules with lift above 5 | 48 |
| Maximum lift score | 6.81 |
| Clustering silhouette score | 0.55 |
| Current average basket value | Rs 1,000.81 |
| Projected basket at 5 percent uplift | Rs 1,050.85 |
| Extra daily revenue at 5 percent | Rs 35,540 |
| Extra annual revenue at 5 percent | Rs 1.30 Crore |

**Cross-sell before/after (RQ2 / Objective 4, data-driven):** the optimised 5-zone layout
co-locates **56** strong cross-sell rules (lift ≥ 3) versus **28** for the current
frequency-driven layout - a **2.0x** increase, raising captured strong-rule support from
8.2% to 16.3%. This result is measured from the association rules; the rupee uplift above
remains a projection.

---

## Extensions (added 15 August 2026)

Three follow-up studies, each an extension of a reported result rather than a replacement. All
figures below are held in `config/metrics.py` and checked by `scripts/verify_thesis_numbers.py`.

**1. Computed zone assignment (`analysis/optimise_zones.py`, `dashboard/artifacts/zone_optimisation.json`).**
Greedy local search with 200 seeded restarts over the same `score_layout` objective as the 28 / 56
result, certified against exhaustive enumeration. Only 12 of the 25 categories appear in any strong
rule. With no limit on zone size the optimum puts all 12 in one zone and captures every rule
(360, 100 per cent): a property of the metric, not a shelf plan. With each zone held to its
hand-built size (5/6/3/4/7) the certified optimum is 250 rules (71.4 per cent) against the
hand-built 56 (16.3 per cent), and the whole gain comes from two moves: CANNED AND PACKAGED FOODS
and PERSONAL CARE into the Daily Essentials group. The cold-storage and entrance constraints cost
nothing, because none of the four constrained categories appears in a strong rule.

**2. Daily granularity forecasting (`analysis/daily_forecast.py`, notebook 13, chart 25).** The
monthly forecast (notebook 10, R squared -2.377 on three test months) is kept as reported. On the
304 trading days, split chronologically 243 / 61, every fitted model beats naive persistence
(the best, day-of-week regression refit daily, by 41.6 per cent in MAE) but no model reaches a
positive R squared on the held-out days, and Prophet does not detect the Dashain peak at daily
granularity unless its trend is loosened enough to overfit. Daily forecasting is usable as a
level-and-weekday planning rule (about 11 per cent MAPE) and fails as a model of variation.

**3. Richer basket features (`analysis/basket_features.py`, notebook 14, chart 26).** The 71.67 per
cent ceiling on 25 binary flags is kept as reported and recomputed in the same run. Adding item
count, category count, per-category quantity, day of week and month (45 features; hour of day does
not exist in the source) moves the depth-5 tree from 61.30 to 71.98 per cent and the MLP from 69.05
to 75.75 per cent on the same split. The same-method ceiling rises to 91.27 per cent, but 49 per
cent of baskets then have a unique pattern, so that ceiling is a memorisation bound rather than
headroom. Item count displaces COOKING OIL (0.280 to 0.010) as the top tree feature; RICE stays
second.

---

## Placement Recommendation

Based on MBA analysis of 218,037 real transactions:

| Zone | Categories | Location |
|------|-----------|---------|
| Zone 1: Daily Essentials | Food Staples, Cooking Oil, Cleaning Supplies, Tea and Spices, Household Items | Store center |
| Zone 2: Snacks and Drinks | Noodles, Soft Drinks, Biscuits, Confectionery, Canned Foods | Near entrance |
| Zone 3: Personal Care | Personal Care, Baby Care, Stationery | Side aisle |
| Zone 4: Dairy and Fresh | Dairy, Frozen Foods, Fruits, Bakery | Back of store |
| Zone 5: Special Categories | Rice, Alcohol, Cigarettes, Pooja Items, Cereals | Store perimeter |

---

## Limitations

- Revenue projections are based on retail industry benchmarks not a live experiment
- 98 percent of customers are anonymous so individual tracking is not possible
- Single store dataset may not generalize to other Nepali grocery stores
- Data covers 11 calendar months (17 July 2025 to 20 May 2026), with July 2025 and May 2026 both partial, so a full 12 month cycle and a second Dashain season are not available

---

## Future Work

- Conduct live A/B test comparing old vs new shelf layout
- Install loyalty card system to track individual customers
- Expand analysis to product level with all 5,681 products
- Build real time recommendation system for cashiers
- Replicate study with full 12 months of data
