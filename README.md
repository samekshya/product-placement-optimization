# Data Analytics and ML Based Product Placement Optimisation
### The case study store, Pokhara, Nepal

**Student:** Samikshya Baniya | **ID:** 230360
**Module:** ST6001CEM Individual Project
**University:** Softwarica College / Coventry University

---

## Project Overview

This project analyses 10 months of real Point of Sale data from a Nepali grocery store to find which products are bought together and recommend how to rearrange shelves to increase sales.

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
| Period | July 2025 to May 2026 (10 months) |
| Unique Transactions | 218,037 shopping trips |
| Unique Products | 5,681 |
| Categories | 25 standardized |

> Data used with permission from store management for academic research purposes only. All customer data is anonymized.

---

## Ethics and Data Use (Objective 5)

**Data provenance and consent.** This study uses **primary data** collected from the
student's own family-run store (Pokhara). The data was
obtained and used **with the explicit permission of store management**, for academic research
only. It is **not faculty-provided / secondary data** — any earlier note describing it that way
is incorrect and is corrected here: the dataset is primary data gathered directly from the store's
Point of Sale system.

**Privacy and anonymisation.** 98% of transactions are cash sales (`CASH A/C`) with no customer
identity attached, so no individual can be re-identified. No names, phone numbers, addresses or
loyalty IDs are stored or analysed — only product-level basket contents and amounts. The raw Excel
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
│   └── 10_demand_forecasting.ipynb
├── dashboard/
│   ├── app.py                  (Streamlit dashboard, loads only artifacts/)
│   ├── precompute_artifacts.py (builds the small artifacts from processed data)
│   └── artifacts/              (small precomputed files committed for the dashboard)
├── reports/
│   └── figures/                (all charts and visualizations)
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
Run from 01_data_audit.ipynb through to 10_demand_forecasting.ipynb.
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

It opens with two modes: **Store Owner** (shelf planner, monthly stock plan, store
performance) and **Examiner** (project overview, association rules, clustering, model
validation, placement zones, ethics). All charts are interactive (hover/zoom) and the
layout works in both light and dark themes.

To rebuild the artifacts after re-running the notebooks (requires the processed CSVs):

```
python dashboard/precompute_artifacts.py
```

---

## Algorithms Used

| Algorithm | Type | Purpose |
|-----------|------|---------|
| Apriori | Unsupervised ML | Find frequent itemsets and association rules |
| FP-Growth | Unsupervised ML | Faster association rule mining for comparison |
| K-Means | Unsupervised ML | Group categories into natural placement zones |

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
frequency-driven layout — a **2.0x** increase, raising captured strong-rule support from
8.2% to 16.3%. This result is measured from the association rules; the rupee uplift above
remains a projection.

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
- Data covers 10 months only, June 2026 is missing for full year analysis

---

## Future Work

- Conduct live A/B test comparing old vs new shelf layout
- Install loyalty card system to track individual customers
- Expand analysis to product level with all 5,681 products
- Build real time recommendation system for cashiers
- Replicate study with full 12 months of data
