# Data Analytics and ML Based Product Placement Optimisation
### Baniya Shopping Center, Lamachour-16, Pokhara, Nepal

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
- Top product pair: Kalo Dal and Rato Dal bought together 4,000 times
- Highest revenue month: September 2025 (Festival/Dashain season) at Rs 23.3 Million
- Recommended store center: Daily Essentials Zone (Food Staples, Cooking Oil, Cleaning Supplies, Tea and Spices, Household Items)

---

## Dataset

| Property | Value |
|----------|-------|
| Source | Real POS data, Baniya Shopping Center Pokhara |
| Raw Size | 768,222 rows, 14 columns |
| After Cleaning | 767,180 rows, 14 columns |
| Period | July 2025 to May 2026 (10 months) |
| Unique Transactions | 218,037 shopping trips |
| Unique Products | 5,681 |
| Categories | 25 standardized |

> Data used with permission from store management for academic research purposes only. All customer data is anonymized.

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
│   ├── 07_placement_simulation.ipynb
│   └── 08_evaluation.ipynb
├── reports/
│   └── figures/                (all charts and visualizations)
└── README.md
---

## How to Run

**Step 1: Clone the repository**
git clone https://github.com/samekshya/product-placement-optimization.git

**Step 2: Create virtual environment**
python -m venv venv
venv\Scripts\activate

**Step 3: Install required libraries**
pip install pandas numpy matplotlib seaborn scikit-learn mlxtend openpyxl

**Step 4: Add the raw data file**
Place sales_data_raw.xlsx inside the data/raw/ folder.
This file is not on GitHub as it contains confidential store data.

**Step 5: Run notebooks in order**
Run from 01_data_audit.ipynb through to 08_evaluation.ipynb.
Each notebook builds on the previous one.

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
