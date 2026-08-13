# Project Record: Everything Planned, Done and Accomplished

**Project:** Data Analytics and ML Based Product Placement Optimisation
**Student:** Samikshya Baniya | **ID:** 230360
**Module:** ST6001CEM Individual Project, Softwarica College / Coventry University
**Case study:** A family-run grocery store in Pokhara, Nepal
**Record compiled:** 2026-08-13, revised 2026-08-14
**Repository state:** branch `main`, 818 commits, first commit 2026-05-28, latest commit 2026-08-12
(`486b14d removed the names`). **The data platform, notebook 12 and every fix described in sections
4b and 8 are uncommitted working-tree changes**, so `git log` will not show them until they are
committed.

---

## 0. What this document is

`PROJECT_LOG.md` is a flat chronological list of 500 commit messages. It shows *when* things
happened but not *what the project is* or *what was achieved*.

This document is the opposite: it is the structured record. It states what was planned, what was
actually built, what every verified number is, what was hardened during viva preparation, and what
is still open. Every figure quoted here was read back out of the notebooks, the artifacts or the
dashboard at compile time, not from memory.

---

## 1. The plan

### 1.1 Problem

The store arranges its shelves by habit and by supplier convenience. Nobody has ever looked at the
Point of Sale history to ask which products customers actually buy together. If products that are
bought together sit far apart, every one of those trips is a cross-sell that did not happen.

### 1.2 Aim

Use real transaction data plus data analytics and machine learning to recommend an evidence-based
shelf layout, and quantify what that layout is worth.

### 1.3 Objectives as stated in the repository

The full objective and research question wording lives in the dissertation document
(`SamikshyaBaniya_230360.pdf`, gitignored). The objectives explicitly referenced inside the code and
notebooks are:

| Reference | Where it appears | What it required |
|---|---|---|
| RQ2 / Objective 4 | notebook 07, README, dashboard Placement Zones page | Produce a **data-driven** before/after comparison of layouts, not just a projection |
| Objective 5 | README ethics section, dashboard Ethics and Data page | Responsible and documented use of real store data |

The remaining objectives map onto the pipeline stages in section 3: audit and clean the data,
characterise buying behaviour, mine association rules, derive placement zones, and evaluate.

### 1.4 Planned pipeline

Twelve notebooks, each one branch, each one feeding the next:

```
01 audit  ->  02 clean  ->  03 EDA  ->  04 encode  ->  05 MBA  ->  06 cluster
                                                                      |
   12 neural net   11 classifier   10 forecasting   09 product ML     v
            \            \              |            /            07 placement
             \            \             |           /                  |
              -------------->  08 evaluation  <-----------------------+
                                       |
                                       v
                           dashboard (artifacts only)
```

### 1.5 Standing rules the project was built under

- Never modify `data/raw/` or `data/processed/`. All analysis is read-only against the source.
- Never alter a verified number to make a result look better. If output changes, the text changes.
- Confidential data stays out of version control. The raw Excel, the 114 MB cleaned CSV and the
  dissertation PDF are all gitignored.
- Projections must be labelled as projections. Measured results must be labelled as measured.

---

## 2. The dataset

| Property | Value |
|---|---|
| Source | Primary data, real POS export from the case study store, used with owner permission |
| Raw size | 768,222 rows, 14 columns |
| After cleaning | 767,180 rows, 14 columns |
| Period covered | 17 July 2025 to 20 May 2026 (11 calendar months, both ends partial) |
| Days of data | 307 as used in the daily averages, see the note below |
| Days with recorded sales | 304 |
| Unique transactions | 218,037 shopping trips |
| Unique products | 5,681 in the raw audit, 5,680 with sales after cleaning |
| Categories | 25 standardised |
| Total revenue | Rs 218,214,456.88 |
| Cash-only share | 98% of transactions (`CASH A/C`, no customer identity attached) |

**On the product count.** Both numbers are correct and the difference is documented in notebook 03:
the raw audit counted 5,681 unique products, one of which was removed entirely during cleaning,
leaving 5,680 products with sales in the cleaned data. `kpi_summary.json` stores 5,680.

**On the day count.** There are three different day numbers in this dataset and it is worth being
exact about which is which, because they are easy to mix up:

| Count | Meaning |
|---|---|
| **308** | inclusive calendar span, 17 July 2025 to 20 May 2026 counting both end dates |
| **307** | the arithmetic difference between the first and last dates, `(max - min).days` |
| **304** | days that actually have recorded sales |

The published `daily_revenue` (Rs 710,796.28) and `daily_customers` (710) divide by **307**. That is
an off-by-one against the inclusive span: it is the gap between the two dates rather than the number
of days covered. The figure is retained for now because it is already quoted throughout the project,
but see section 8 item 7, which sets out the choice.

---

## 3. What was built, stage by stage

### Notebook 01: Data Audit
Examined the raw Excel without modifying it. Key finding: the real header is on **row 7**, not row 1,
so a naive load produces garbage. Documented column names, dtypes, missing values and the ethics
statement. 45 cells.

### Notebook 02: Data Cleaning
Fixed every issue the audit found: renamed columns, dropped unused ones, standardised the product
group column into 25 categories, removed 1,042 unusable rows (768,222 to 767,180). Output:
`data/processed/sales_data_cleaned.csv`. 30 cells.

### Notebook 03: Exploratory Data Analysis
Eleven charts, each with a written finding. What it established:

- **Chart 1:** Sugar is in 23,083 transactions, Rato Dal 12,533, Salt 7,756. These anchor daily traffic.
- **Chart 2:** FOOD STAPLES is the store anchor, appearing in **42.19% of baskets** (91,988 of
  218,037) and accounting for 23.34% of all line items sold. Both figures are real and measure
  different things; basket penetration is the one that matters for placement, because placement is
  about how many shopping trips pass a category. An earlier version of this record quoted the
  23% line-item share as though it were the transaction share, which was wrong wording. Notebook 03
  now prints both measures side by side so they cannot be confused again.
- **Chart 4:** Basket value is heavily right skewed. Mean Rs 1,000.81, median Rs 500.00. The gap is
  the whole business case: a small group of large baskets carries revenue.
- **Chart 5:** Mean 3.51 items per basket. Most trips are quick top-ups, not weekly shops.
- **Chart 6:** Most baskets hold only 1 or 2 categories, so co-located products matter more than
  browsing does.
- **Chart 7:** Co-occurrence heatmap. FOOD STAPLES and CANNED AND PACKAGED FOODS co-occur most
  strongly; CLEANING SUPPLIES is a connector across many pairs. This is the visual foundation of the
  placement zones.
- **Chart 8:** Kalo Dal and Rato Dal are bought together **3,989** times, the strongest product pair
  in the dataset.
- **Chart 9 (basket segmentation):** 108,349 baskets (49.7%) are under Rs 500 and produce 11.4% of
  revenue (Rs 24.8M). 29,820 baskets (13.7%) above Rs 2,000 produce **52.1%** of revenue
  (Rs 113.6M), averaging Rs 3,810.
- **Chart 10 (ABC analysis):** Concentration beats the 80/20 rule. **342 products (6.0%)** generate
  the first 70% of revenue (Class A, daily stock check). Class B is 1,065 products (18.8%) for the
  next 20%. Class C is the 4,273-product long tail (75.2%).
- **Chart 11 (day of week):** Friday busiest (Rs 32.8M, 32,290 transactions). Wednesday has the
  highest average basket at Rs 1,031.33. Saturday, the Nepali weekly holiday, is quietest
  (Rs 28.7M, Rs 949.09 average). Only about a 14% spread between quietest and busiest day.

### Notebook 04: Transaction Encoding
Converted the cleaned rows into one-hot basket format via `TransactionEncoder`, the input Apriori
and FP-Growth require. Output: `basket_encoded.csv`.

### Notebook 05: Market Basket Analysis
The analytical core.

- Apriori found **243 frequent itemsets** in 0.47s across 218,037 baskets at 1% minimum support
  (2,180 baskets).
- FP-Growth found **exactly the same 243 itemsets** in 0.49s. Two independent algorithms agreeing
  is the project's internal correctness check.
- **1,228 association rules** extracted. **48 rules with lift above 5.0**.
- **Maximum category lift 6.81**: CLEANING SUPPLIES + CANNED AND PACKAGED FOODS leads to TEA AND
  SPICES + HOUSEHOLD ITEMS.
- **CLEANING SUPPLIES is the central connector.** It appears in nearly every strong rule.
- **Chart 10 network graph:** the 360 rules with lift above 3 condense to 38 unique category-to-category
  connections. CLEANING SUPPLIES ties for most connected with 9 links, level with FOOD STAPLES,
  CANNED AND PACKAGED FOODS and BISCUITS AND COOKIES. Eight of the ten most connected categories are
  Daily Essentials, and nearly all link back to the two staples hubs.
- **Revenue impact analysis:** lift alone does not equal money. A rule is a placement priority only
  if it clears all three thresholds together: lift above 3.0, support above 1%, confidence above 0.3.
  High-support, moderate-lift rules move more total revenue than rare high-lift rules.

### Notebook 06: Clustering
The most instructive result in the project, because the first attempt failed honestly.

- **Frequency-based K-Means: silhouette 0.19**, flat from k=3 to k=10. The algorithm was clustering
  on how *often* categories sell, not on what sells *together*. Useless for placement.
- **Co-occurrence-based K-Means: silhouette 0.554.** Same algorithm, better question. That is
  **an increase of 0.364, from 0.190 to 0.554**, and it came from reframing the input, not from
  tuning the model. It is stated as an absolute increase on purpose: silhouette is bounded on
  [-1, 1] with no meaningful zero, so a percentage change between two silhouette scores has no
  interpretation.
- Three natural clusters emerged: Core Staples (FOOD STAPLES + CANNED AND PACKAGED FOODS), Daily
  Essentials (10 categories), Occasional and Speciality (13 categories).

### Notebook 07: Placement Simulation
Turned the analysis into a layout and a number.

**The 5 zones** (3 clusters expanded using the association rules):

| Zone | Location | Categories |
|---|---|---|
| 1 Daily Essentials | Store centre | Food Staples, Cooking Oil, Cleaning Supplies, Tea and Spices, Household Items |
| 2 Snacks and Drinks | Near entrance | Noodles, Soft Drinks, Biscuits, Confectionery, Namkeen, Canned Foods |
| 3 Personal Care | Side aisle | Personal Care, Baby Care, Stationery |
| 4 Dairy and Fresh | Back of store | Dairy, Frozen, Fruits, Bakery |
| 5 Special Categories | Perimeter | Rice, Alcohol, Cigarettes, Pooja, Cereals, Electrical, Party |

**Revenue projections** (labelled as projections throughout, based on the 2% to 8% uplift range in
retail literature):

| Scenario | Uplift | Extra annual revenue |
|---|---|---|
| Conservative | 3% | Rs 0.78 Crore |
| **Moderate (primary recommendation)** | **5%** | **Rs 1.30 Crore** |
| Optimistic | 8% | Rs 2.08 Crore |

Baseline: average basket Rs 1,000.81, daily revenue Rs 710,796, 710 customer trips per day.

**The data-driven result (RQ2 / Objective 4).** Because a projection cannot answer a research
question, notebook 07 measures cross-sell capture directly from the rules. A strong rule (lift >= 3)
is *captured* when every category in it sits in the same layout group, meaning the cross-sell can
physically happen on the shelf.

| Layout | Strong rules captured | Support captured | Capture rate |
|---|---|---|---|
| Current (frequency-based clusters) | 28 | 0.4106 | 8.2% |
| Optimised (5 designed zones) | **56** | **0.813** | **16.3%** |
| Delta | +28 (2.0x) | +0.4024 | +8.1 pts |

Out of 360 total strong rules carrying 4.986 total support. This is measured, not projected.

**Honesty additions in this notebook:** a 95% confidence interval for mean basket value computed from
the actual variance across all 218,037 baskets, so the projection rests on a range from the store's
own data rather than a single point; an explicit note that data-driven zones must still respect
physical constraints (refrigeration, entry points, aisle width, shelf infrastructure); and a note
that May 2026 looks weak only because it is a partial month.

### Notebook 08: Evaluation
Cross-checked everything. Apriori and FP-Growth confirmed identical (243 itemsets, 1,228 rules,
identical lift values), with a note that timing varies by hardware so only the agreement matters.
Clustering comparison (0.19 weak vs 0.554 reasonable). Final evaluation summary covering data,
algorithm performance, rule quality, business impact and six honest limitations. A pilot study
protocol was added so the recommendation can actually be tested in store rather than just asserted.

### Notebook 09: Product-Level ML Recommendation
Moved from 25 categories down to individual products.

- Focused on the **top 100 products** (Sugar leads with 23,083 transactions).
- Trained on **95,570 baskets**, mined **100 product-level rules**.
- **Maximum product lift 22.41**: Surya and Shikhar Ice.
- Other strong rules: PRAWN and SADA PAPAD (11.89), Mong Khosta and Aadar Dal (10.20), Rato Dal +
  Sugar + Kalo Dal (7.72, the classic dal bhat pattern).
- Kalo Dal buyers buy Rato Dal with **0.69 confidence**.
- Wai Wai Chicken and RARA, two competing noodle brands, co-occur at lift 6.94.
- Local Milk returns no recommendations, correctly identifying it as a destination product.
- **Validation: 28.0% hit rate**, measured on the **19,808 multi-product baskets** inside the
  40,959-basket unseen test set (5,554 correct). Single-product baskets are excluded because a
  one-item basket cannot test a co-purchase recommendation. Against roughly 1% for random guessing
  across 100 products, that is about 28x better than chance on data the model never saw.

### Notebook 10: Demand Forecasting
Added forward-looking supervised ML.

| Model | MAE | RMSE |
|---|---|---|
| Linear Regression | Rs 3,395,703 | Rs 4,700,487 |
| **Prophet** | **Rs 2,909,633** | **Rs 3,946,262** |

Prophet is **14.3% more accurate** and detected the Dashain seasonal peak without being told about
it. Linear Regression alone scores **R-squared -2.377**, and the notebook explains precisely why
this is expected rather than hiding it: only 11 monthly points against a best-practice minimum of
about 30, a 3-point test set, the July 2025 partial month acting as an outlier, and festival spikes
that a straight line cannot represent. That explanation is the justification for adding Prophet.
Business framing included: use the upper confidence bound as the stock planning target.

### Notebook 11: Basket Value Classifier
A supervised Decision Tree predicting small / medium / large basket value from category presence alone.

- Trained on **152,625 baskets**, tested on **65,412 unseen baskets**.
- **61.3% accuracy** against a **49.7% majority-class baseline**, so **+11.6 points** of genuine signal.
- Per class: Small recall 0.931, Large recall 0.367 (precision 0.586), Medium recall 0.273. Medium is
  hardest because it overlaps both neighbours, and the notebook says so instead of glossing over it.
- **Feature importance:** COOKING OIL 0.280 and RICE 0.215 dominate, then CLEANING SUPPLIES 0.146,
  ALCOHOLIC BEVERAGES 0.130, CANNED AND PACKAGED FOODS 0.127. **14 of 25 categories score zero.**
- Large baskets average 4.27 distinct categories against 1.51 for small baskets.
- Fully explainable: depth 5, 32 leaves, readable as if-then rules.
- **Why it matters:** a completely different method independently confirms the notebook 07 layout.
  The categories that predict high-value baskets are the same ones the optimised layout clusters
  around the staples anchor.

### Notebook 12: Neural Network Basket Classifier
Answers the obvious challenge to notebook 11: could a more powerful model do better on the same
information? Rebuilds the same features, labels and split from scratch (same `random_state=42`, so
the identical baskets) and trains both models in one run, so no numbers are copied across.

An MLPClassifier with two hidden layers (64 and 32 neurons, **3,843 parameters**) trained in 10.3
seconds, stopped early at 10 epochs.

| Model | Accuracy | Size | Share of achievable maximum |
|---|---|---|---|
| Majority baseline | 49.69% | n/a | n/a |
| Decision Tree, depth 5 (nb11) | 61.30% | 32 leaves | 85.5% |
| Decision Tree, fully grown | 67.85% | 10,231 leaves | 94.7% |
| **MLP neural network** | **69.05%** | 3,843 parameters | **96.3%** |
| Ceiling for these 25 features | 71.67% | n/a | n/a |

**The finding that matters.** The raw gap over notebook 11 is 7.75 points, but **6.55 of those
points are the depth 5 cap**, which was an interpretability choice rather than a limit of decision
trees. Letting the tree grow freely reaches 67.85%, so the genuine model-family advantage is only
**1.20 points**. The network is nonetheless both more accurate and about a third the size of the
fully grown tree, because it expresses category combinations as weighted sums instead of
enumerating them as branches.

**Where the win actually comes from.** Per-class recall shows the depth 5 tree was taking the easy
route: Small recall 0.931 but Medium recall 0.273. The network trades some Small accuracy (0.854)
to genuinely separate the other two classes: **Medium recall 0.273 to 0.550** and **Large recall
0.367 to 0.472**. Large baskets are 13.7% of trips but 52.1% of revenue, so that trade favours the
classes that carry the money.

**The ceiling.** There are 17,532 distinct category patterns across 218,037 baskets, and identical
patterns often carry different labels because quantity and price are not in the feature set. The
best score any model could achieve on these 25 binary features is **71.67%**. The network reaches
96.3% of it, so the remaining gap needs richer features, not a better algorithm.

**Honest verdict recorded in the notebook:** the network wins on accuracy, the Decision Tree wins on
usefulness to this project. Notebook 11 existed to identify *which categories carry the signal* so an
independent method could confirm the placement zones, and only the tree can state that as readable
rules. The network predicts better and explains nothing. Output: `chart24_model_comparison.png`.

---

## 4. The dashboard

`dashboard/app.py`, roughly 1,100 lines of Streamlit. Rebuilt on 2026-08-01 from a chart gallery into
a practical two-mode tool.

**Store Owner mode** (three pages, built for the person who runs the shop):
- **Shelf Planner** - pick a product, get its co-purchase recommendations with lift, confidence and support
- **Monthly Stock Plan** - pick a month, get a seasonal stocking plan
- **Store Performance** - headline KPIs and trends

**Examiner mode** (seven pages, built for marking):
- Project Overview
- Store Analytics (ABC analysis, day of week)
- Association Rules
- Clustering Results
- Model Validation
- Placement Zones (carries the RQ2 cross-sell before/after result)
- Ethics and Data (Objective 5)

**Design and engineering decisions:**
- Runs **entirely from `dashboard/artifacts/`**, thirteen small precomputed files. A marker can clone
  the repo and launch it with no confidential CSV and without re-running Apriori.
- Light theme default with a dark mode toggle. Every chart draws from the theme palette, so all
  visuals stay legible in both modes.
- Plotly throughout, so charts are interactive (hover and zoom) rather than static PNGs.
- Missing artifacts produce a clear `st.error` and stop, not a raw traceback.
- Recommendation cards show all three metrics (lift, confidence, support), not lift alone.
- Zone cards carry a methodology note so the zones are not mistaken for arbitrary choices.
- A 4-step controlled testing implementation guide, so the recommendation ships with a way to verify it.

**Artifacts committed** (13 files): `abc_analysis.csv`, `basket_value_hist.csv`,
`category_distribution.csv`, `category_rules.csv`, `cluster_assignments.csv`,
`cooccurrence_matrix.csv`, `cross_sell_summary.json`, `day_of_week.csv`, `kpi_summary.json`,
`monthly_revenue.csv`, `product_rules.csv`, `top_pairs.csv`, `top_products.csv`. Rebuilt with
`python dashboard/precompute_artifacts.py`.

---

## 4b. The data platform (added 2026-08-13)

The project originally read CSVs directly from notebooks. It now sits on a real data platform:
Postgres OLTP, a star schema warehouse, an Airflow DAG that orchestrates the whole thing, and a
dashboard that reads live from the warehouse.

### Architecture

```
data/processed/sales_data_cleaned.csv        (notebooks 01-02 produce this)
        |
        v
  [ oltp schema ]        products / transactions / transaction_items
        |                normalised, one row per product sold
        v
  [ warehouse schema ]   dim_date  dim_category  dim_product  dim_basket
        |                            \    |    /
        |                             fact_sales
        |                + 7 serving views
        v
  dashboard  <-- live SQL, or committed CSV artifacts as fallback
```

Everything runs from one `docker-compose.yml`: Postgres 16 on host port **5435**, Airflow 3.3.0
LocalExecutor on **8082**. Those ports are deliberate, because 5432, 5433, 5434, 8080 and 8081 are
already taken by other stacks on the development machine.

### The OLTP layer

`sql/01_create_oltp.sql` plus `scripts/load_to_postgres.py`. Loads 767,180 line items in about 17
seconds by staging with `COPY` and then moving rows across with `ON CONFLICT DO NOTHING`.

**Three schema decisions were driven by measurements of the data, not by convention:**

1. **`unit` is not on the product table.** 356 products are sold in more than one unit, so unit is a
   property of the sale, not the product. Putting it on `products` would have been wrong.
2. **`transaction_items` needs a `line_no`.** 1,587 invoice+product combinations legitimately repeat
   on the same invoice, up to 4 times, so `(transaction_id, product_id)` is not unique and cannot be
   the key. `line_no` restores a natural key of `(transaction_id, line_no)`, and that key is what
   makes reloading idempotent.
3. **Money is stored at NUMERIC scale 6, not the usual 4.** `total_amount` carries up to 6 decimal
   places in the source and `unit_price` up to 7. At scale 4, rounding moved **2 baskets** across the
   Rs 500 segment boundary (978 baskets sit within Rs 0.1 of it) and shifted total revenue by 1
   paisa, so the SQL segment counts disagreed with the notebooks. At scale 6 they agree exactly.

**How each of those was actually found**, since they are specific enough to invite a follow-up
question. All three were discovered by checking assumptions before writing the DDL, not afterwards:

| Finding | How it was found | Re-run it |
|---|---|---|
| 356 multi-unit products | Grouped by `product` and counted distinct `unit` before deciding where `unit` belonged | `df.groupby('product')['unit'].nunique().gt(1).sum()` |
| 1,587 repeating invoice+product pairs | Grouped by `(invoice_no, product)` and counted group sizes, to test whether that pair could serve as a primary key. It could not, so `line_no` was added | `df.groupby(['invoice_no','product']).size().gt(1).sum()` |
| 6 decimal places on `total_amount` | Re-read the CSV as raw strings and measured the digits after the decimal point, because reading as float hides the source precision | `raw['total_amount'].str.split('.').str[1].str.len().max()` |
| 2 baskets crossing the Rs 500 line | Found by comparing SQL segment counts against the notebook counts after the first load. SQL said 108,351 Small, the notebooks said 108,349. Rounding the same column to 4 and to 6 decimal places with `Decimal` reproduced both numbers exactly, which identified the scale as the cause | see `scripts/verify_thesis_numbers.py` and section 8 item 5 |

The 2-basket difference is the one worth being able to walk through: the check that exposed it was
simply refusing to accept that the warehouse and the notebooks could disagree by any amount, however
small. Every claim in this section was re-verified against the source data on 2026-08-14, and seven
of eight matched exactly; the eighth is section 8 item 7.

### The star schema warehouse

`sql/02_create_warehouse.sql` plus `etl/load_warehouse.py`. Every step is a set-based
`INSERT ... SELECT` executed inside Postgres; no data is pulled into Python and pushed back.

| Table | Rows |
|---|---|
| `dim_date` | 304 trading days |
| `dim_category` | 25 |
| `dim_product` | 5,680 |
| `dim_basket` | 218,037 |
| `fact_sales` | 767,180 |

**What makes this warehouse specific to this research:** `dim_category.zone_assignment` carries the
5 placement zones derived in notebook 07. Storing the research finding as a dimension attribute
means "what revenue would each zone carry?" is a `GROUP BY` rather than a separate analysis. All 25
categories map to exactly one zone, verified with no orphans in either direction.

Measured from the warehouse, Zone 1 (the anchor zone: Food Staples, Cooking Oil, Cleaning Supplies,
Tea and Spices, Household Items) carries **40.6% of all revenue from 5 of the 25 categories**, which
is the quantified justification for putting it at the centre of the store.

Seven serving views ship with it: `v_kpi_summary`, `v_monthly_revenue`, `v_category_performance`,
`v_zone_performance`, `v_basket_segments`, `v_day_of_week`, `v_top_products`.

### The Airflow DAG

`dags/product_placement_pipeline.py`. Five tasks in a straight line:

```
load_raw_to_oltp >> oltp_to_warehouse >> run_quality_checks >> update_artifacts >> done
```

Each task wraps a script that also runs standalone from the command line, so nothing about the logic
is Airflow-specific and the same code can be demonstrated with or without the scheduler.

**`run_quality_checks` runs 32 checks in four groups:** completeness (did every row arrive),
integrity (orphans, duplicates, negative amounts, all 5 zones present), consistency (does the
warehouse still reconcile to the OLTP source) and **accuracy** (do the headline thesis figures still
hold). The accuracy group is the important one for an academic project: if a future ETL change
silently moved the average basket value, the pipeline fails instead of quietly feeding a wrong
number to the dashboard.

**`update_artifacts` refreshes only what the warehouse can derive** and leaves the Apriori, K-Means
and cross-sell artifacts alone, because the warehouse cannot compute those and overwriting them
would be pretending it does. `kpi_summary.json` is merged rather than replaced for the same reason:
its warehouse fields are refreshed, its mining fields (max lift, rule counts, silhouette) are
preserved untouched.

**Verified behaviour:** a full run against an empty database rebuilds everything and all five tasks
go green in about 70 seconds. A second run also goes green and inserts **0 rows**, with every table
count unchanged, because every load carries `ON CONFLICT DO NOTHING` against a natural key.

### The dashboard, connected

`dashboard/app.py` now prefers the warehouse and falls back to the committed CSV artifacts when
Postgres is not running. The sidebar states which source is live: a green dot with
"Live: Postgres warehouse" and the row count, or an amber dot with "Static: CSV artifacts" and the
command to start the database.

The fallback is not a nicety. A marker cloning the repository has no Postgres and no 114 MB CSV, and
the dashboard still has to run for them. All 10 pages were verified rendering in both modes.

The Placement Zones page gains a **Revenue by Placement Zone** chart that appears only in live mode,
because there is no artifact equivalent. It is the clearest demonstration of why the zone assignment
was stored in the warehouse rather than left in a notebook.

### End-to-end verification

The whole stack was torn down with `docker compose down -v`, both volumes destroyed, and rebuilt
from nothing. The Airflow scheduler then rebuilt the entire warehouse autonomously on its scheduled
run, with no manual trigger. After that rebuild:

- 32 of 32 warehouse quality checks passed
- 13 of 13 reproduction checks passed across 9 steps, exit code 0
- **60 of 60 checkable section 9 figures matched**, with no drift. Six further figures in that
  table are declared not auto-checkable (they need a notebook re-run) rather than being counted
  as passes. That count is produced by `scripts/verify_thesis_numbers.py`, not typed in by hand,
  so it cannot drift away from the table it describes. An earlier version of this record claimed
  "38 of 38" beside a table that had grown to 53 rows, which is exactly the failure the generated
  count now prevents.
- all 10 dashboard pages rendered in both live and fallback mode

---

## 5. Reproducibility

`reproduce_all_results.py` exists so that any examiner can confirm every thesis number with **one
command** instead of re-executing twelve notebooks and hunting through outputs. It regenerates the
artifacts, prints a full verification report, saves a timestamped log to `reports/`, and exits 0 if
every check passes or 1 if any fails.

**Status: working (fixed 2026-08-13).** It runs 12 checks across 8 steps and exits 0. The missing
`config/metrics.py` it depends on was rebuilt; see section 8, item 1 for how.

There are now three independent verification layers, which check different things:

| Command | Checks | Verifies against |
|---|---|---|
| `python etl/quality_checks.py` | 32 | the live warehouse (completeness, integrity, consistency, accuracy) |
| `python reproduce_all_results.py` | 13 across 9 steps | the committed artifacts and the notebook figures; calls the sweep below as its final step |
| `python scripts/verify_thesis_numbers.py` | 60 checkable, 6 declared uncheckable | every figure in section 9, against the warehouse, the artifacts and `config/metrics.py` |
| the Airflow DAG's `run_quality_checks` task | 32 | the warehouse, on every pipeline run |

---

## 6. Charts produced

28 figures in `reports/figures/`, covering products by count and revenue, category distribution,
basket value and size distributions, category co-occurrence, top product pairs, association rule
scatter, elbow and silhouette plots, network graph, ABC analysis, day of week, store planogram,
before/after layout, revenue impact, monthly trends, algorithm comparison, product rule scatter and
heatmap, monthly revenue trend, Linear Regression forecast, Prophet forecast, cross-sell before/after,
basket classifier feature importance, and the neural network versus decision tree comparison.

---

## 7. Viva preparation and hardening

A dedicated ten-task hardening pass was completed on 2026-07-19, ahead of the viva window. What it
changed:

1. **Causal language sweep** across notebooks 01, 03, 05, 06, 07, 08, 10 and the dashboard. Wording
   that implied causation where only correlation was measured was corrected throughout.
2. **Centralised metrics module** so no number could drift between notebook and dashboard.
3. **Temporal stability validation** added to notebook 05: development window July 2025 to January
   2026 (141,111 baskets) against validation window February to May 2026 (76,926 baskets). Every one
   of the top 20 development rules kept lift above 3 in validation. Stability ratios 0.941 to 1.039
   (mean 0.986). Across all 1,228 rules, stability ranged 0.851 to 1.178 with median 1.011 and
   **none below 0.5**. The rules are not an artifact of one time period.
4. **Metric renamed** from `revenue_impact` to `associated_basket_revenue`, because the original name
   implied a causal claim the data cannot support. An `opportunity_rank` (associated revenue x
   stability) was added. Rank 1 is FOOD STAPLES + CANNED AND PACKAGED FOODS at Rs 31.1M with
   stability 1.0.
5. **Notebook 11 reframed** from prediction to characterisation, with a segment characterisation step
   quantifying which categories mark large baskets (RICE 16.34x, ALCOHOL 11.8x, COOKING OIL 7.51x,
   CLEANING 5.63x, CIGARETTE 4.18x) versus quick-trip categories (CONFECTIONERY, BAKERY, SOFT DRINKS,
   DAIRY, all around 1.3x to 1.4x).
6. **Negative R-squared explained precisely** in notebook 10 against the naive mean predictor.
7. **Pilot study protocol** added to notebook 08 so the recommendation is testable in store.
8. **Four dashboard robustness fixes**: sidebar CSS, chart width handling, data freshness captions on
   every examiner page, and graceful handling of missing artifacts.
9. **Date range corrected** from "10 months" to the precise 11 calendar months (17 July 2025 to
   20 May 2026) wherever it appeared.

**Verified by execution at the time:** notebooks 03, 05, 06, 07, 08, 10 and 11 all ran clean top to
bottom; the dashboard passed AppTest on all pages; the missing-artifact path showed a clear message.

Since that pass, the dashboard was rebuilt into owner/examiner modes (2026-08-01) and store
identifiers were removed from the repository (2026-08-12, commit `486b14d`), with the store referred
to throughout as "the case study store".

---

## 8. Open items

These are the only things known to be outstanding. Each is small.

**1. `reproduce_all_results.py` was broken, now fixed (resolved 2026-08-13).** It executes
`from config import metrics as M`, but `config/metrics.py` had been lost from disk and was never
committed, so the import raised `ImportError`. The module was rebuilt rather than guessed: the stale
`config/__pycache__/metrics.cpython-313.pyc` was unmarshalled to recover all 33 constant names and
their exact literal values, and the one computed field was recovered by disassembling its bytecode
(`SILHOUETTE_INCREASE = round(SILHOUETTE_COOCCURRENCE - SILHOUETTE_FREQUENCY, 3)`). Every value was
then cross-checked against `kpi_summary.json`, `cross_sell_summary.json` and the notebook outputs.

One genuine gap was found in the process: `reproduce_all_results.py` references
`M.CROSS_SELL_FREQUENCY`, a constant the compiled module never defined, because the script was
written three days after that `.pyc` was compiled. It is defined now as the same 28-rule
frequency-based baseline that `cross_sell_summary.json` labels
"Frequency-based clusters (unoptimised baseline)".

The script now runs 12 checks and exits 0. Its em dashes were also replaced with ASCII hyphens,
because they rendered as mojibake in the Windows console and in the saved reproduction log.

**2. "10 months" versus "11 months" (resolved 2026-08-14).** Both were defensible (307 days is about
10.1 months elapsed, spanning 11 calendar months) but the project said both in different places. It
is now stated consistently as **11 calendar months, 17 July 2025 to 20 May 2026, both ends partial**,
in the README overview, the README Dataset table, the README Limitations section, notebook 10 and the
dashboard. The Dataset table also now records the 307-day span and the 304 days that had sales, so
the two different day counts are explicit rather than implied.

**3. Stale `__pycache__` directories (resolved 2026-08-14).** `config/__pycache__` and
`dashboard/__pycache__` have been deleted from disk. The config one had become actively misleading:
it held the compiled `metrics.cpython-313.pyc` for a source file that no longer existed. That `.pyc`
had already served its purpose as the recovery source for `config/metrics.py` (see item 1), and
`config/` now contains only real source: `__init__.py`, `db.py` and `metrics.py`.

**4. Notebook 12 now exists (resolved 2026-08-13).** An earlier working note referenced a notebook 12
with a chart24 that was not present on disk or in git history. Both now exist for real:
`notebooks/12_neural_network.ipynb` and `reports/figures/chart24_model_comparison.png`, covering the
MLP neural network comparison described in section 3.

---

**5. Three recurring data-description problems, all resolved 2026-08-14.** These had each been
noticed before and had fallen out of tracking, so they are recorded here with what was actually
wrong, to stop them reappearing:

- **FOOD STAPLES was quoted as "23% of all transactions".** Both circulating numbers were real but
  measured different things. 42.19% is the share of **baskets** containing FOOD STAPLES (91,988 of
  218,037); 23.34% is the share of **line items** (179,081 of 767,180). The root cause was notebook
  03 Chart 2, which plots `value_counts()` (line items) under an axis labelled "Number of
  Transactions". The axis is now labelled "Number of Line Items Sold", and the cell prints both
  measures side by side so they cannot be conflated again. Basket penetration is the correct
  measure for placement, and 42.2% was already used consistently in notebooks 04 and 06 and the
  dashboard.
- **The silhouette gain was described as a "189% improvement".** Silhouette is bounded on [-1, 1]
  and has no meaningful zero, so a ratio between two silhouette scores has no interpretation. It
  is now stated everywhere as **an increase of 0.364, from 0.190 to 0.554**. A comment in the
  notebook 06 code cell and in `config/metrics.py` explains why, so the percentage framing cannot
  be silently reintroduced.
- **The recommender hit rate was quoted against the wrong denominator.** The 28.0% was measured on
  the **19,808 multi-product baskets** inside the 40,959-basket test set, not on all 40,959.
  Single-product baskets are skipped because a one-item basket cannot test a co-purchase
  recommendation.

**6. Notebook 09's co-occurrence heatmap counted line items, not baskets (resolved 2026-08-14).**
Found while checking the item above. Cell 31 built its pivot with `.size()` (line counts) and then
took `pivot.T.dot(pivot)`, which sums nA x nB per basket rather than counting baskets containing
both products. That reported Rato Dal + Kalo Dal as **4,236** where the true basket count is
**3,989**, contradicting notebook 03, the README, `top_pairs.csv` and `config/metrics.py`. The
pivot is now binarised before the dot product and the notebook prints the pair counts. Two other
pairs were corrected at the same time: Sugar + Rato Dal 3,771 to **3,639**, and Wai Wai Chicken +
RARA 1,662 to **1,653**. Note that `precompute_artifacts.py` had always computed these correctly;
only the notebook was wrong.

**7. OPEN: the daily-average denominator is an off-by-one.** Found on 2026-08-14 while re-verifying
every section 4b claim. `DATA_DAYS = 307` is `(last_date - first_date).days`, which is the gap
between the dates, not the number of days covered. The inclusive span is **308** days and only
**304** days have recorded sales. The choice changes two published figures:

| Denominator | Meaning | Daily revenue | Daily customers |
|---|---|---|---|
| 304 | days the store actually traded | Rs 717,810.71 | 717 |
| **307 (current)** | gap between first and last date | **Rs 710,796.28** | **710** |
| 308 | inclusive calendar span | Rs 708,488.50 | 708 |

**This is deliberately left as a decision rather than silently changed**, because `daily_revenue`
and `daily_customers` are quoted in the dashboard, the artifacts and very likely the submitted
dissertation PDF, and changing them without checking that document would create a new inconsistency
rather than remove one.

Recommendation: if the PDF already quotes Rs 710,796, keep 307 and simply define it precisely in the
text as the difference between the first and last trading date. If the PDF does not quote it, switch
to **304**, which is the most meaningful denominator for a daily average because it is the number of
days the store actually traded. Whichever is chosen, `config/metrics.py` is the single place to
change it.

## 9. Verified numbers, one table

Everything an examiner is likely to ask about, with its source.

| Number | Value | Source |
|---|---|---|
| Raw rows | 768,222 | nb01 |
| Cleaned rows | 767,180 | nb02 |
| Transactions | 218,037 | nb03, kpi_summary.json |
| Total revenue | Rs 218,214,456.88 | kpi_summary.json |
| Days of data | 307 | kpi_summary.json |
| Products | 5,681 raw / 5,680 with sales | nb01 / nb03 |
| Categories | 25 | nb02 |
| Mean basket | Rs 1,000.81 | nb03, kpi_summary.json |
| Median basket | Rs 500.00 | nb03 |
| Items per basket | 3.51 mean | nb03 |
| Daily revenue | Rs 710,796.28 | kpi_summary.json |
| Daily customers | 710 | kpi_summary.json |
| Frequent itemsets | 243 (both algorithms) | nb05, nb08 |
| Association rules | 1,228 | nb05, kpi_summary.json |
| Rules with lift above 5 | 48 | nb05, kpi_summary.json |
| Max category lift | 6.81 | nb05, kpi_summary.json |
| Max product lift | 22.41 | nb09, kpi_summary.json |
| Strong rules (lift >= 3) | 360 | nb05, cross_sell_summary.json |
| Network connections | 38 unique | nb05 chart 10 |
| Top product pair | Kalo Dal + Rato Dal, 3,989 times | nb03 chart 8 |
| Frequency clustering silhouette | 0.19 | nb06 |
| Co-occurrence clustering silhouette | 0.554 | nb06, kpi_summary.json |
| Silhouette improvement | +0.364 (0.190 to 0.554) | nb06, nb08 |
| Cross-sell rules captured, current | 28 (8.2%) | cross_sell_summary.json |
| Cross-sell rules captured, optimised | 56 (16.3%) | cross_sell_summary.json |
| Cross-sell improvement | 2.0x | nb07, README |
| Revenue projection at 5% | Rs 1.30 Crore per year | nb07 |
| Recommender validation hit rate | 28.0% on the 19,808 multi-product baskets within the 40,959 unseen test baskets | nb09 |
| Recommender training baskets | 95,570 | nb09 |
| Linear Regression MAE | Rs 3,395,703 | nb10 |
| Prophet MAE | Rs 2,909,633 | nb10 |
| Prophet accuracy gain | 14.3% | nb10 |
| Linear Regression R-squared | -2.377 (explained) | nb10 |
| Classifier accuracy | 61.3% | nb11 |
| Classifier baseline | 49.7% majority class | nb11 |
| Classifier test baskets | 65,412 unseen | nb11 |
| Top classifier feature | COOKING OIL, 0.280 | nb11 |
| Neural network accuracy | 69.05% | nb12 |
| Neural network parameters | 3,843 | nb12 |
| Fully grown tree accuracy | 67.85% (10,231 leaves) | nb12 |
| Model family advantage of MLP | 1.20 points over best tree | nb12 |
| Ceiling on the 25 binary features | 71.67% | nb12 |
| Distinct category patterns | 17,532 | nb12 |
| Rule temporal stability | median 1.011, none below 0.5 | nb05 step 9 |
| OLTP / fact table rows | 767,180 | warehouse |
| Warehouse trading days | 304 (span is 307 days) | warehouse |
| Zone 1 share of revenue | 40.6% from 5 categories | warehouse |
| Warehouse quality checks | 32 of 32 pass | `etl/quality_checks.py` |
| Reproduction checks | 13 of 13 pass across 9 steps, exit 0 | `reproduce_all_results.py` |
| Section 9 sweep | 60 of 60 checkable figures, 6 declared uncheckable | `scripts/verify_thesis_numbers.py` |
| Large baskets share of revenue | 13.7% of trips, 52.1% of revenue | nb03 chart 9 |
| Class A products | 342 (6.0%) for 70% of revenue | nb03 chart 10 |
| Busiest day | Friday, Rs 32.8M | nb03 chart 11 |
| Peak month | September 2025 (Dashain), Rs 23.3M | nb07 |

---

## 10. Machine learning inventory

Eight models, deliberately spanning supervised, unsupervised, pattern-based and neural learning:

| Model | Type | Notebook | Headline result |
|---|---|---|---|
| Apriori | Unsupervised, association | 05 | 243 itemsets, 1,228 rules, max lift 6.81 |
| FP-Growth | Unsupervised, association | 05, 08 | Identical results, validates Apriori |
| K-Means | Unsupervised, clustering | 06 | Silhouette 0.554 on co-occurrence |
| Product recommender | Pattern-based | 09 | 28% hit rate on unseen baskets |
| Linear Regression | Supervised, regression | 10 | MAE Rs 3.40M |
| Prophet | Supervised, time series | 10 | MAE Rs 2.91M, 14.3% better |
| Decision Tree | Supervised, classification | 11 | 61.3% vs 49.7% baseline |
| **MLP neural network** | **Supervised, neural** | **12** | **69.05%, best accuracy in the project** |

---

## 11. Ethics and data governance

- **Primary data**, collected from the student's own family-run store with explicit permission of
  store management, for academic research only. The README explicitly corrects any earlier
  description of it as faculty-provided secondary data.
- **No re-identification risk.** 98% of transactions are cash sales with no identity attached. No
  names, phone numbers, addresses or loyalty IDs are stored or analysed, only basket contents and
  amounts.
- **Confidential files never leave the machine.** Raw Excel, the 114 MB cleaned CSV and the
  dissertation PDF are all gitignored. Only small aggregated artifacts are published.
- **Store identifiers removed** from the repository on 2026-08-12; the store is referred to
  throughout as "the case study store".
- **Honest reporting throughout.** Measured results and projections are labelled differently
  everywhere they appear. The 3/5/8% uplift is always called a projection. The cross-sell before/after
  is always called data-driven, with only its rupee conversion flagged as projection.

---

## 12. Limitations, stated openly

1. Revenue uplift percentages come from retail-industry benchmarks, not a live in-store experiment.
2. 98% anonymous customers make individual-level tracking impossible.
3. Single-store dataset, so generalisation to other Nepali grocery stores is not established.
4. Primary analysis is at category level; product level covers the top 100 only.
5. June 2026 is missing, so no full-year cycle and only one Dashain season.
6. July 2025 is a partial month (starts 17 July), and May 2026 is partial at the other end.
7. The "before" layout is the frequency-based clustering baseline, a reasonable proxy for an
   unoptimised layout rather than a surveyed record of the store's actual shelves.
8. Forecasting rests on 11 monthly data points, well below the roughly 30 needed for stable
   regression, which is exactly why the negative R-squared appears and why Prophet was added.

---

## 13. Future work

**Why the data platform is here at all.** The Postgres warehouse and the Airflow DAG were added on a
supervisor's recommendation, after the analysis itself was complete. It is worth saying plainly why,
because "a one-time historical analysis does not need a scheduler" is a fair challenge.

The analysis answers the research questions from a fixed export. The platform demonstrates that the
same answers can be produced on a **recurring** basis: the store's Point of Sale system keeps
producing data after 20 May 2026, and a shelf layout derived once from eleven months is a snapshot,
not a standing recommendation. Putting the load behind a scheduler, with the placement zones stored
as a dimension attribute and 32 quality checks gating every run, is what turns a one-off study into
something the store could actually keep using as new months arrive. The idempotency work matters for
the same reason: a recurring pipeline that double-counts on a retry is worse than no pipeline.
It also makes the findings queryable rather than trapped in notebook outputs, which is what allows
questions like "what revenue does Zone 1 carry?" to be answered directly.

- Run the pilot protocol from notebook 08 as a live A/B test of old versus new layout.
- Install a loyalty system to enable individual-level analysis.
- Extend product-level mining beyond the top 100 to all 5,680 products.
- Build a real-time cashier-facing recommendation prompt.
- Repeat with a full 12+ months covering two Dashain seasons to materially improve Prophet.

---

## 14. What this project accomplished, in one paragraph

Eleven notebooks and 818 commits turned 768,222 rows of raw POS data into an evidence-based shelf
layout for a real store. Two independent algorithms agreed on 1,228 association rules; those rules
proved stable across two separate time windows; a failed clustering attempt was fixed by reframing
the question rather than tuning the model, raising silhouette by 0.364 from 0.190 to 0.554; the resulting 5-zone layout
was shown to co-locate twice as many strong cross-sell rules as the unoptimised baseline, which is a
measured answer to RQ2 rather than a projection; a product recommender validated at 28 times better
than chance on baskets it had never seen; Prophet outperformed Linear Regression by 14.3% on demand
forecasting and found the Dashain peak by itself; and a Decision Tree independently confirmed the
layout by identifying the same anchor categories through an entirely different method. All of it is
delivered through a dashboard an examiner can run from a clean clone, and every number is honest
about whether it was measured or projected.
