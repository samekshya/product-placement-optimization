# Product Placement Optimisation

An end-to-end data platform that turns a single grocery store's till receipts into a shelf layout, and measures how much better that layout is than the one the shop uses today.

No loyalty scheme. No customer identifiers. No analyst. Eleven calendar months of Point-of-Sale data, open-source tools, and every reported number checked by a machine.

```
   CURRENT ARRANGEMENT                    OPTIMISED LAYOUT
   ┌──────────────────┐                   ┌──────────────────┐
   │       5.7%       │  ───────────────▶ │      54.1%       │
   │   22 of 368      │                   │   180 of 368     │
   │   strong rules   │                   │   strong rules   │
   └──────────────────┘                   └──────────────────┘
        measured directly from the association rules
        no assumption about customer response
```

---

## Architecture

Five layers. Each one writes something the next one reads, so the dependency lives in the file system rather than in anyone's head.

```
                          ┌────────────────────────┐
                          │    Point-of-Sale       │
                          │     Excel export       │
                          │  768,222 rows x 14 col │
                          └───────────┬────────────┘
                                      │
┌─────────────────────────────────────▼──────────────────────────────────────┐
│                                 INGEST                                      │
│                                                                             │
│   ┌──────────────┐      ┌──────────────┐      ┌──────────────────────┐      │
│   │   Profile    │      │    Clean     │      │   Category audit     │      │
│   │  1,040 dupes │ ───▶ │  767,180     │ ───▶ │  638 products        │      │
│   │  168k spaces │      │  line items  │      │  remapped            │      │
│   └──────────────┘      └──────────────┘      └──────────────────────┘      │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼──────────────────────────────────────┐
│                                  STORE                                      │
│                                                                             │
│   ┌─────────────────────────┐          ┌──────────────────────────────┐     │
│   │  Transactional layer    │   ───▶   │   Star schema warehouse      │     │
│   │  products               │          │   fact_sales   767,180 rows  │     │
│   │  transactions           │          │   dim_date                   │     │
│   │  transaction_items      │          │   dim_category  (+ zones)    │     │
│   │  PostgreSQL 16          │          │   dim_product                │     │
│   └─────────────────────────┘          │   dim_basket                 │     │
│                                        │   7 views                    │     │
│                                        └──────────────────────────────┘     │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼──────────────────────────────────────┐
│                                 ANALYSE                                     │
│                                                                             │
│   ┌───────────────┐  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐  │
│   │  Association  │  │   Clustering  │  │  Optimiser   │  │  Predictive  │  │
│   │  rules        │  │               │  │              │  │  models      │  │
│   │               │  │  frequency    │  │  greedy      │  │              │  │
│   │  Apriori      │  │    0.190      │  │  200 starts  │  │  tree  61.4% │  │
│   │  FP-Growth    │  │  co-occur     │  │  certified   │  │  MLP   69.2% │  │
│   │  chi-square   │  │    0.493      │  │  optimum     │  │  Prophet     │  │
│   │  Bonferroni   │  │               │  │              │  │  recommender │  │
│   │               │  │  3 clusters   │  │  22 -> 180   │  │              │  │
│   │  1,320 rules  │  │  -> 5 zones   │  │  rules       │  │              │  │
│   │  1,314 pass   │  │               │  │              │  │              │  │
│   └───────────────┘  └───────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼──────────────────────────────────────┐
│                                  SERVE                                      │
│                                                                             │
│   ┌──────────────────────────────┐    ┌──────────────────────────────────┐  │
│   │   Streamlit dashboard        │    │   Layout tool                    │  │
│   │   12 pages                   │    │   FastAPI + React                │  │
│   │   owner mode  /  examiner    │    │   drag, drop, live scoring       │  │
│   └──────────────────────────────┘    └──────────────────────────────────┘  │
│                                                                             │
│              both import the same scoring function, by identity             │
└─────────────────────────────────────────────────────────────────────────────┘

   ════════════════════════════════════════════════════════════════════════
     VERIFIED AT EVERY STAGE
     299 figures re-checked  ·  32 quality checks  ·  26 reproduction checks
     55 tests  ·  one command
   ════════════════════════════════════════════════════════════════════════
```

Orchestrated by Apache Airflow. Five tasks, about 29 seconds per run, **idempotent**: a second run against a loaded database inserts zero rows.

---

## The layers in detail

### Ingest

Reads the raw export and changes nothing on the first pass, recording every defect: 1,040 duplicate rows, 168,864 values with trailing whitespace, headers sitting in the eighth row under the shop letterhead, 38 inconsistent product group labels.

Then cleans to 767,180 line items, a loss of 0.14 per cent.

Then the part that mattered most. An audit of all 5,680 products against their raw labels found two of the 38 groups were catch-alls, used by staff for anything without an obvious home. **638 products were in the wrong category.** Correcting them changed every headline figure in the project.

The 32 automated quality checks could not have caught it. They verify completeness, referential integrity and consistency. None can tell whether a product belongs in its category, because that needs someone to read the product name and know what it is.

### Store

Two layers rather than one. A normalised transactional layer mirroring how a till records a sale, then a star schema derived from it entirely with set-based SQL inside the database.

Placement zones are stored as a column on the category dimension, which turns "how much revenue does the anchor zone carry" into a single GROUP BY rather than a separate analysis. The answer is a single number, and it comes back as a share rather than an amount.

Monetary values are stored at NUMERIC scale six rather than four. At scale four the rounding moved two baskets across a segmentation boundary and shifted the revenue total by the smallest possible unit, which was enough to make the SQL layer disagree with the notebooks.

### Analyse

Fourteen notebooks in execution order, plus shared modules that the applications import directly.

**Association rules.** Apriori and FP-Growth run independently produced identical output: 261 frequent itemsets, 1,320 rules, same lift values. Agreement between two algorithms that search in completely different ways means the patterns are properties of the data, not artefacts of method.

Every rule was chi-square tested. 1,318 pass conventionally. Because 1,320 tests ran at once, a Bonferroni correction was applied, and 1,314 still survive. 368 rules reach a lift of 3 or above.

**Rule stability.** Rules mined on the first seven months were re-scored on the last four. Median lift ratio 1.016 across 1,276 rules. No rule fell below half its original strength.

**Clustering.** Clustering categories by purchase frequency reached a silhouette of 0.190, which is a failure and is reported as one. The algorithm was grouping by volume. Clustering the same categories with the same algorithm by co-occurrence reached 0.493. The representation was the problem.

**The optimiser.** Three clusters were expanded into five zones under real shelf capacities and three placement constraints. The assignment is the output of a greedy search with 200 random restarts, certified as the true maximum by exhaustive enumeration. It is not a hand-built layout that happened to score well.

### Serve

A dashboard with a landing page and eleven others, split into an owner view and an examiner view. It reads precomputed artefacts, never the live database, so demonstrating it never exposes transaction records.

A drag-and-drop layout tool that scores any arrangement live.

Both call `analysis/cross_sell.py`. A test asserts they are the same object in memory, not two implementations that happen to agree.

---

## The finding that was not expected

All 180 captured rules fall inside one zone.

The entrance impulse zone, the only one classified as creating an intention rather than serving one, captures **zero**. The entire measured benefit comes from helping customers do what they already came to do.

And the ethical position has a price.

| Constraint | Rules captured | Cost |
|---|---|---|
| None, capacity ceiling | 286 | — |
| Cold chain only | 286 | 0 |
| Alcohol and tobacco to the perimeter | 180 | **-106** |
| Heavy goods only | 182 | -104 |
| All three together | 180 | **-106** |

Costs are not additive, because all three restrictions compete for the same perimeter slots. The mechanism is **capacity competition, not adjacency**: with unlimited zone sizes the same restrictions cost only two rules.

106 of 368 strong rules is 37 per cent of the reachable ceiling. Most placement work treats responsible constraints as free. A principle that costs nothing is not evidence of anything. This one cost something and was adopted anyway.

---

## What this does not claim

Stated plainly, so the result above is read at its actual size.

**The revenue figure is projected.** A published uplift range from Drèze, Hoch and Purk (1994) is applied to the store's measured average basket. No shelf was moved. Customer response was never observed. Absolute revenue figures are not published here.

**The baseline is a proxy.** The 22-rule current layout is a frequency-driven arrangement standing in for the store's real layout, which was never available in digital form.

**Most categories carry nothing.** 14 of 25 carry a strong rule. Five carry none at any threshold. 10.2 per cent of baskets, holding 9.91 per cent of revenue, are beyond the reach of any zone arrangement here.

**Forecasting failed.** No daily model reached a positive R squared; the best was -0.015. Usable as a weekday planning rule at roughly 11 per cent error, useless as a forecast.

**A simple baseline beats the recommender.** Unconstrained popularity reaches 34.81 per cent against the model's 28.04. The model wins only at a matched recommendation budget, where popularity scores 23.74. The limitation is coverage, not ranking: 28 of 100 products carry a mined rule.

**The neural network's win is capacity, not architecture.** MLP 69.17 per cent against a depth-5 tree at 61.38. But a fully grown tree reaches 67.67 and closes most of the gap, using 11,906 leaves against the network's 3,843 parameters. The parameter efficiency is the finding, not the accuracy.

---

## Verification

Five measurement errors were found during development. **Every one made a result look better than the data supported.** None understated anything.

Measurement error is not randomly signed with respect to the interests of the person measuring. So verification stopped being a habit and became a script.

```bash
python scripts/run_verifications.py
```

```
  scripts/verify_thesis_numbers.py     299 of 299 figures
  etl/quality_checks.py                 32 of 32 checks
  reproduce_all_results.py              26 of 26 across 12 stages
  pytest                                55 tests, 5 files
```

Five figures are declared not automatically checkable and listed rather than hidden.

---

## The shared-function guarantee

```python
# app/api/tests/test_acceptance.py
assert service.score_layout is shared.score_layout
assert service.groups_from_assignment is shared.groups_from_assignment
```

Asserted by identity, not equality. If anyone reimplements the metric inside the application, the test fails rather than passing silently.

---

## Quick start

```bash
git clone <repo-url>
cd product-placement-optimization

python -m venv venv
venv\Scripts\activate           # Windows
source venv/bin/activate        # macOS / Linux
pip install -r requirements.txt

docker compose up -d
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:8501 |
| Layout tool | http://localhost:5173 |
| Airflow | http://localhost:8082 |
| API docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5435 |

Verify every reported figure yourself:

```bash
python scripts/run_verifications.py
pytest
```

---

## Project structure

```
analysis/          Shared modules. cross_sell.py holds the single scoring
                   implementation. zones.py holds the zone definitions.
                   Both are imported, never copied.
app/               Layout tool. FastAPI backend, React frontend.
config/            Verified constants and database configuration.
dags/              Airflow pipeline definition.
dashboard/         Streamlit dashboard and precomputed artefacts.
data/              Raw export (gitignored) and cleaned output.
etl/               Warehouse loader and the 32 quality checks.
notebooks/         14 notebooks, 01 to 14, in execution order.
reports/           Figures, category audit, verification status.
scripts/           Loaders, chart generators, verification suite.
sql/               Transactional and warehouse schema definitions.
```

---

## Stack

| Layer | Tools |
|---|---|
| Ingest | pandas, NumPy, openpyxl |
| Store | PostgreSQL 16, SQL |
| Orchestrate | Apache Airflow 3.3.0 |
| Mine | mlxtend (Apriori, FP-Growth), SciPy |
| Model | scikit-learn, Prophet |
| Serve | Streamlit, FastAPI, React, Vite |
| Run | Docker Compose |
| Verify | pytest, custom verification suite |

---

## Privacy

98 per cent of transactions are cash with no customer identity attached. No names, phone numbers, addresses or loyalty IDs exist anywhere in the record.

Data that was never collected cannot be re-identified. That is a stronger guarantee than anonymisation, and it was inherited rather than designed.

The raw file is not distributed. The dashboard ships only small aggregated artefacts.

---

## Future work

- **Run the pilot.** One shelf moved, attachment rate measured before and after, four weeks. This is the step that would turn the central projection into a measurement.
- **Collect a second festival cycle.** One more year makes seasonality testable rather than descriptive.
- **Trial in other stores.** A single case cannot settle whether these patterns generalise.
- **Capture subcategory codes at the till.** Would allow the full zone, category and shelf hierarchy to be computed rather than partly judged.
- **Relax the capacity multiset.** Ask what shelf sizes the rules would choose, rather than fixing them from the shop as it stands.