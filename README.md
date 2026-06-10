# Data Analytics and ML Based Product Placement Optimisation
### Baniya Shopping Center, Lamachour-16, Pokhara, Nepal

**Student:** Samikshya Baniya | **ID:** 230360
**Module:** ST6000CEM Final Year Project
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
