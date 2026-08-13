# Progress Report: Everything Completed To Date

**Project:** Data Analytics and ML Based Product Placement Optimisation
**Student:** Samikshya Baniya | **ID:** 230360
**Module:** ST6001CEM Individual Project, Softwarica College / Coventry University
**Report date:** 2026-08-13
**Repository:** branch `main`, 818 commits, working tree has uncommitted work (see section 9)

---

## 0. What this file is, and how it differs from PROJECT_RECORD.md

There are now two documents and they do different jobs. Use whichever fits the question:

| Document | Answers |
|---|---|
| `PROJECT_RECORD.md` | **What the project IS.** Methodology, findings, every verified number, ethics, limitations. The reference document. |
| `PROGRESS_REPORT.md` (this file) | **Where the project STANDS.** What is finished, what is verified and how, what is still open, what state the machine is in right now. |

If you are preparing to explain a result, read the record. If you are deciding what to do next, read this.

---

## 1. Where the project stands right now

The project is **feature complete and fully verified**. It began as twelve analysis notebooks
producing a Streamlit dashboard from CSV files. It now also sits on a working data platform:
a Postgres transactional schema, a star schema warehouse, an Airflow DAG that orchestrates the
whole load, and a dashboard that reads live from that warehouse.

Every headline number in the dissertation still reproduces after the new data layer was put
underneath it. That was checked by tearing the entire stack down to nothing and rebuilding it.

**Nothing is committed to git yet.** All of today's work sits in the working tree awaiting your
review, in line with your rule that you commit manually.

---

## 2. Work completed, in two stages

### Stage 1: the research project (to 2026-08-12, 818 commits)

Twelve notebooks taking 768,222 raw rows of Point of Sale data through audit, cleaning, exploration,
encoding, market basket analysis, clustering, placement simulation, evaluation, product-level
recommendation, demand forecasting and basket classification. Plus a two-mode Streamlit dashboard,
28 figures, an ethics position, and a ten-task viva-hardening pass completed in July.

Full detail is in `PROJECT_RECORD.md` sections 1 to 3.

### Stage 2: today, 2026-08-13

Two pieces of work in one session:

1. `PROJECT_RECORD.md` was written: a complete structured record of the project, replacing reliance
   on `PROJECT_LOG.md`, which is only a flat list of 500 commit messages.
2. A seven-phase build adding a neural network and a full data platform. All seven phases are
   complete and verified.

---

## 3. Component status

| Component | Status | Evidence |
|---|---|---|
| Notebooks 01 to 11 | Complete | Executed clean, outputs preserved |
| Notebook 12, neural network | **New today** | Executed end to end, 31 cells, chart 24 saved |
| Postgres OLTP schema | **New today** | 767,180 line items loaded, 4 assertions pass |
| Star schema warehouse | **New today** | 5 tables, 7 views, reconciles to OLTP at Rs 0.00 |
| Airflow DAG | **New today** | 5 tasks, full run green, re-run inserts 0 rows |
| Data quality checks | **New today** | 32 of 32 pass |
| Dashboard, live Postgres mode | **New today** | 10 of 10 pages render |
| Dashboard, artifact fallback | Working | 10 of 10 pages render with Postgres stopped |
| `reproduce_all_results.py` | **Fixed today** | Was broken, now 12 checks, exit 0 |
| `config/metrics.py` | **Rebuilt today** | Recovered from compiled bytecode |
| README and project record | Updated today | Data platform documented |

---

## 4. What was delivered today, phase by phase

### Phase 1: Neural network (notebook 12)

An MLPClassifier trained on the same 25 binary category features, the same labels and the same
70/30 split as notebook 11 (same `random_state=42`, so literally the same baskets). Both models are
trained in the same run so no numbers are copied between notebooks.

| Model | Accuracy | Size | Share of achievable maximum |
|---|---|---|---|
| Majority baseline | 49.69% | n/a | n/a |
| Decision Tree, depth 5 (notebook 11) | 61.30% | 32 leaves | 85.5% |
| Decision Tree, fully grown | 67.85% | 10,231 leaves | 94.7% |
| **MLP neural network (64-32)** | **69.05%** | 3,843 parameters | **96.3%** |
| Ceiling for these 25 features | 71.67% | n/a | n/a |

**The finding, stated honestly.** The raw gap over notebook 11 is 7.75 points, but **6.55 of those
points are the depth 5 cap**, which was an interpretability choice rather than a limit of decision
trees. Let the tree grow freely and it reaches 67.85%, so the genuine model family advantage is
**1.20 points**. The network is still both more accurate and about a third the size of the fully
grown tree.

The win is concentrated where it matters commercially: Medium basket recall rises from 0.273 to
0.550 and Large from 0.367 to 0.472, and large baskets are 13.7% of trips but 52.1% of revenue.
The depth 5 tree had been taking the easy route, scoring well by predicting Small (recall 0.931)
and effectively giving up on Medium.

**Verdict recorded in the notebook:** the network wins on accuracy, the Decision Tree wins on
usefulness to this project. Notebook 11 existed to identify which categories drive basket value so
that an independent method could confirm the placement zones, and only the tree states that as
readable rules. The network predicts better and explains nothing.

### Phase 2: PostgreSQL OLTP

`sql/01_create_oltp.sql` and `scripts/load_to_postgres.py`. Loads 767,180 line items in about 17
seconds using `COPY` into staging tables followed by `ON CONFLICT DO NOTHING`.

Three schema decisions came from measuring the data rather than from convention:

1. **`unit` is not on the products table.** 356 products sell in more than one unit, so unit is a
   property of the sale.
2. **Line items need a `line_no`.** 1,587 invoice+product combinations legitimately repeat on the
   same invoice, up to 4 times, so `(transaction_id, product_id)` cannot be the key. `line_no`
   restores a natural key and is what makes reloading idempotent.
3. **Money is stored at NUMERIC scale 6.** See section 6, problem 1.

### Phase 3: Star schema warehouse

`sql/02_create_warehouse.sql` and `etl/load_warehouse.py`. Every step is a set-based
`INSERT ... SELECT` run inside Postgres.

| Table | Rows |
|---|---|
| `dim_date` | 304 trading days |
| `dim_category` | 25 |
| `dim_product` | 5,680 |
| `dim_basket` | 218,037 |
| `fact_sales` | 767,180 |

**What ties the warehouse to your research:** `dim_category.zone_assignment` carries the five
placement zones from notebook 07. Storing the finding as a dimension attribute turns "what revenue
would each zone carry?" into a `GROUP BY`. All 25 categories map to exactly one zone, verified with
no orphans in either direction.

Measured result: **Zone 1, the anchor zone, carries 40.6% of all revenue from 5 of the 25
categories.** That is a quantified justification for putting it at the centre of the store, and the
OLTP layer alone could not have produced it.

### Phase 4: Airflow DAG

`dags/product_placement_pipeline.py`, five tasks in a straight line:

```
load_raw_to_oltp >> oltp_to_warehouse >> run_quality_checks >> update_artifacts >> done
```

Each task wraps a script that also runs standalone, so nothing about the logic is Airflow-specific.

`run_quality_checks` runs 32 checks in four groups: completeness, integrity, consistency and
accuracy. The accuracy group re-verifies the thesis figures, so an ETL change that silently moved
the average basket value fails the pipeline instead of reaching the dashboard unnoticed.

`update_artifacts` refreshes only what the warehouse can derive and leaves the Apriori, K-Means and
cross-sell artifacts alone. `kpi_summary.json` is merged, not replaced: its warehouse fields are
refreshed, its mining fields (max lift, rule counts, silhouette) are preserved.

### Phase 5: Dashboard connected to Postgres

`dashboard/app.py` now prefers the warehouse and falls back to the committed CSV artifacts when
Postgres is not running. The sidebar states which is in use: a green dot with
"Live: Postgres warehouse" plus the row count, or an amber dot with "Static: CSV artifacts" plus
the command to start the database.

The fallback matters: a marker cloning the repository has no Postgres and no 114 MB CSV, and the
dashboard still has to run for them.

The Placement Zones page gains a **Revenue by Placement Zone** chart that appears only in live mode,
because no artifact equivalent exists.

### Phase 6: Reproducibility restored

`config/metrics.py` had been lost from disk and was never committed, so `reproduce_all_results.py`
could not import it. Rather than guess the values, the module was recovered:

1. The stale `config/__pycache__/metrics.cpython-313.pyc` was unmarshalled, giving all 33 constant
   names and their exact literal values.
2. The one computed field was recovered by disassembling its bytecode:
   `SILHOUETTE_INCREASE = round(SILHOUETTE_COOCCURRENCE - SILHOUETTE_FREQUENCY, 3)`.
3. Every value was cross-checked against `kpi_summary.json`, `cross_sell_summary.json` and the
   notebook outputs.

This also exposed a real gap: `reproduce_all_results.py` calls `M.CROSS_SELL_FREQUENCY`, a constant
the compiled module never defined, because the script was written three days after that `.pyc` was
compiled. It is now defined as the same 28-rule frequency baseline that `cross_sell_summary.json`
labels "Frequency-based clusters (unoptimised baseline)".

A STEP 8 was added covering notebook 12, and the script's em dashes were replaced with ASCII because
they rendered as mojibake in the console and in the saved reproduction log.

### Phase 7: End-to-end verification

The stack was destroyed with `docker compose down -v`, both volumes removed, and rebuilt from
nothing. The Airflow scheduler then rebuilt the entire warehouse **autonomously on its scheduled
run**, before any manual trigger. Results in section 5.

---

## 5. Verification scorecard

Everything below was run after the full teardown and rebuild, not before.

| Check | Result |
|---|---|
| Warehouse data quality checks | **32 of 32 pass** |
| Reproduction script | **13 of 13 pass across 9 steps, exit code 0** |
| Section 9 thesis-number sweep | **60 of 60 checkable figures match**, 6 declared not auto-checkable |
| Airflow full run from an empty database | **5 of 5 tasks green, about 70 seconds** |
| Airflow re-run (idempotency) | **5 of 5 green, 0 rows inserted, no count moved** |
| Dashboard pages, live Postgres mode | **10 of 10 render** |
| Dashboard pages, artifact fallback mode | **10 of 10 render** |
| Warehouse revenue reconciles to OLTP | **difference Rs 0.00** |
| Rule artifacts after regeneration | **identical rule sets, all numeric diffs 0.0** |
| Section 4b claims re-verified against source data | **7 of 8 exact**, 1 discrepancy found and recorded |

The sweep count is produced by `scripts/verify_thesis_numbers.py` rather than typed in by hand. An
earlier version of this report carried "38 of 38" beside a table that had grown to 53 rows, which is
precisely the drift the generated count now prevents.

Selected figures confirmed straight from SQL after the rebuild: total revenue Rs 218,214,456.88,
mean basket Rs 1,000.81, median Rs 500.00, 108,349 Small / 79,868 Medium / 29,820 Large baskets,
Friday the busiest day at Rs 32.8M, September 2025 the peak month, FOOD STAPLES the top category.

---

## 6. Problems found and fixed

These are the ones worth being able to talk about, because each was found by checking rather than
assuming.

**1. A precision bug that would have made the dashboard contradict the notebooks.**
Money was first declared `NUMERIC(14,4)`, the conventional choice. But `total_amount` carries up to
6 decimal places in the source (and `unit_price` up to 7), and **978 baskets sit within Rs 0.1 of
the Rs 500 segment boundary**. Rounding at scale 4 moved 2 baskets from Medium to Small and shifted
total revenue by 1 paisa, so SQL reported 108,351 Small where the notebooks say 108,349. Scale 6
reproduces the notebook figures exactly. An examiner comparing dashboard to notebooks would have
found this.

**2. `reproduce_all_results.py` was broken.** Documented in Phase 6 above. This was the
highest-priority open item in the project record and is now closed.

**3. A referenced constant that never existed.** `M.CROSS_SELL_FREQUENCY`, described above.

**4. Non-deterministic artifact output.** Many products share an identical revenue total, and
without a tiebreaker Postgres could return tied rows in a different order each run, making the
generated ABC artifact churn between pipeline runs for no real reason. Fixed with an explicit
`ORDER BY revenue DESC, product_name`.

**5. A scikit-learn 1.8 incompatibility.** `MLPClassifier` with `early_stopping=True` crashes on
string class labels (it calls `np.isnan` on strings). Fixed by encoding the targets to integers,
which neural networks need anyway.

**6. A chart label collision.** The chart 24 ceiling label overlapped the title because
`invert_yaxis()` had moved the anchor to the top. Found by rendering the PNG and looking at it, not
by reading the code.

**7. Em dashes and stale references.** Removed 9 em dashes from `reproduce_all_results.py` and 3
from `README.md` (they broke the console encoding), and corrected the README run instructions that
still stopped at notebook 10.

**8. FOOD STAPLES was quoted with the wrong denominator (2026-08-14).** "23% of all transactions"
was really the line-item share. The basket share is 42.19%. Root cause was notebook 03 Chart 2
plotting `value_counts()` (line items) under an axis labelled "Number of Transactions". Axis
relabelled and the cell now prints both measures.

**9. Notebook 09's heatmap counted line items, not baskets (2026-08-14).** `pivot.T.dot(pivot)` on
raw counts summed nA x nB per basket, reporting the top pair as 4,236 where the true basket count is
**3,989**. Found while fixing item 8, because it is the same class of error. Pivot is now binarised.
Two other pairs corrected. `precompute_artifacts.py` had always been right; only the notebook was wrong.

**10. A summary count had drifted from the table it described.** "38 of 38 verified numbers" sat
beside a table that had grown to 53 rows. Replaced by `scripts/verify_thesis_numbers.py`, which
generates the count (currently 60 checkable, 6 declared uncheckable) and is wired into
`reproduce_all_results.py` as step 9, so it can never go stale again.

**11. The silhouette gain was framed as a percentage.** "189% improvement" implies the clustering
became nearly three times better. Silhouette is bounded on [-1, 1] with no meaningful zero, so the
ratio is meaningless. Now stated as **+0.364, from 0.190 to 0.554**, in all 10 places it appeared,
with guard comments in the notebook and in `config/metrics.py`.

---

## 7. Current machine state

The stack is **running right now**:

| Container | Status |
|---|---|
| `pp_postgres` | healthy, published on port **5435** |
| `pp_airflow_apiserver` | healthy, UI at **http://localhost:8082** (airflow / airflow) |
| `pp_airflow_scheduler` | healthy |
| `pp_airflow_dag_processor` | running |
| `pp_airflow_metadata` | healthy |

Ports are deliberately non-default because 5432, 5433, 5434, 8080 and 8081 are already used by your
other stacks (Sephora, leapfrog, week6, course).

```
docker compose down       stop everything, keep the data
docker compose up -d      start everything again
docker compose down -v    stop and wipe the data (the pipeline rebuilds it)
```

Note the DAG is unpaused on a daily schedule, so it will trigger itself shortly after the stack
comes up. That is expected, not a fault.

---

## 8. Project inventory

- **12 notebooks** (01 to 12)
- **28 figures** in `reports/figures/`
- **13 dashboard artifacts**
- **2 SQL schema files**, 5 warehouse tables, 7 serving views
- **1 Airflow DAG**, 5 tasks
- **10 dashboard pages** across Store Owner and Examiner modes
- **8 machine learning models**: Apriori, FP-Growth, K-Means, product recommender, Linear
  Regression, Prophet, Decision Tree, MLP neural network

---

## 9. What is left for you

**1. Commit the work.** Nothing has been committed. The working tree currently holds:

*New (untracked):*
```
PROJECT_RECORD.md              PROGRESS_REPORT.md (this file)
docker-compose.yml             notebooks/12_neural_network.ipynb
sql/                           scripts/
etl/                           dags/
config/                        reports/figures/chart24_model_comparison.png
reports/reproduction_log_*.txt (3 files, generated evidence)
```

*Modified:*
```
.gitignore          (added logs/ so Airflow runtime logs are never committed)
README.md           (data platform instructions, structure, algorithms, em dashes)
dashboard/app.py    (live Postgres reads, fallback, source indicator, zone chart)
requirements.txt    (psycopg2-binary)
reproduce_all_results.py  (em dashes, STEP 8)
dashboard/artifacts/category_rules.csv, product_rules.csv
                    (regenerated; verified identical rule sets, only row order differs)
```

Your established pattern is one branch per piece of work. Suggested branches:
`12-neural-network`, `13-postgres-oltp`, `14-warehouse`, `15-airflow`, `16-dashboard-live`.

**2. One open numeric decision (see PROJECT_RECORD section 8, item 7).** The "10 months versus 11
months" wording is now settled everywhere as **11 calendar months (17 July 2025 to 20 May 2026, both
ends partial)**. But re-verification on 2026-08-14 surfaced a related off-by-one that is still open:
`DATA_DAYS = 307` is the arithmetic gap between the first and last dates, while the inclusive span is
**308** days and only **304** days had sales. That denominator sets `daily_revenue` (Rs 710,796.28)
and `daily_customers` (710). I did not change it, because both figures are published in the
dashboard and artifacts and very likely in your submitted PDF, so a silent change would create a new
inconsistency rather than remove one. The three options and a recommendation are in the record.

**3. Optional, if you want it.** The `update_artifacts` task refreshes only warehouse-derived
artifacts. The association rules and clustering artifacts still come from the notebooks, because
Apriori and K-Means genuinely are not warehouse operations. If you ever want the DAG to own those
too, it would need `mlxtend` and `scikit-learn` in the Airflow image and a longer runtime. This is
a deliberate boundary, not an omission, and it is defensible as it stands.

---

## 10. Suggested viva talking points from this work

- **Why the neural network result is more interesting than "the neural network won".** You
  controlled for capacity, found that 6.55 of the 7.75 points were the depth cap, and then computed
  a ceiling showing that both models sit near the limit of what 25 binary features can express.
  That is a stronger answer than any accuracy number.
- **Why the warehouse is specific to your research.** The placement zones are a column in
  `dim_category`, not a note in a notebook, which is why "revenue by zone" is a single query and why
  Zone 1 can be shown to carry 40.6% of revenue.
- **Why the pipeline can be re-run safely.** Natural keys plus `ON CONFLICT DO NOTHING`, and the
  measured evidence that a second run inserts zero rows.
- **How you know the data layer did not change your findings.** 38 verified numbers re-checked
  against a stack rebuilt from nothing.
- **The precision bug.** It demonstrates that you validate rather than assume, and it is a genuinely
  subtle issue that most projects would ship without noticing.
