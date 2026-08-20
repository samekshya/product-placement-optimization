# Temporal validation of the category association rules

Generated 2026-08-20 02:18:45 by `analysis/temporal_validation.py`.

Do the rules hold in a period they were not mined from? Rules are mined on the development
window only, then each rule's lift is recomputed on the validation window and compared.

## Windows

| window | dates | baskets |
|---|---|---:|
| development | 2025-07-17 to 2026-01-31 | 141,111 |
| validation | 2026-02-01 to 2026-05-20 | 76,926 |
| **total** | | **218,037** |

## Method

Apriori at 1% minimum support on the development window, then rules at lift >= 1.0, which are notebook 05's thresholds unchanged. For each
rule, `stability = validation lift / development lift`.

Validation lift is recomputed from validation support directly rather than by re-mining the
second window. Re-mining would drop any rule that fell below the support floor there, which
would select for rules that survived and bias the result upward.

## Result

| figure | value |
|---|---:|
| development rules mined | 1,276 |
| rules with a defined validation lift | 1,276 |
| rules with no defined validation lift | 0 |
| **median stability ratio** | **1.016** |
| **minimum stability ratio** | **0.867** |
| maximum stability ratio | 1.156 |
| mean stability ratio | 1.018 |
| **rules below ratio 0.5** | **0** |
| top 20 dev rules with validation lift >= 3.0 | 20 of 20 |
| all dev rules at lift >= 3.0 still >= 3.0 in validation | 334 of 342 |

## Top 20 development rules by lift

| # | antecedents | consequents | dev lift | val lift | ratio |
|---:|---|---|---:|---:|---:|
| 1 | PERSONAL CARE, TEA AND SPICES | CANNED AND PACKAGED FOODS, CLEANING SUPPLIES, FOOD STAPLES | 7.426 | 7.462 | 1.005 |
| 2 | CANNED AND PACKAGED FOODS, CLEANING SUPPLIES, FOOD STAPLES | PERSONAL CARE, TEA AND SPICES | 7.426 | 7.462 | 1.005 |
| 3 | CLEANING SUPPLIES, TEA AND SPICES | CANNED AND PACKAGED FOODS, FOOD STAPLES, PERSONAL CARE | 7.412 | 7.514 | 1.014 |
| 4 | CANNED AND PACKAGED FOODS, FOOD STAPLES, PERSONAL CARE | CLEANING SUPPLIES, TEA AND SPICES | 7.412 | 7.514 | 1.014 |
| 5 | CANNED AND PACKAGED FOODS, CLEANING SUPPLIES | FOOD STAPLES, PERSONAL CARE, TEA AND SPICES | 7.076 | 7.013 | 0.991 |
| 6 | FOOD STAPLES, PERSONAL CARE, TEA AND SPICES | CANNED AND PACKAGED FOODS, CLEANING SUPPLIES | 7.076 | 7.013 | 0.991 |
| 7 | FOOD STAPLES, PERSONAL CARE | CANNED AND PACKAGED FOODS, CLEANING SUPPLIES, TEA AND SPICES | 7.007 | 7.059 | 1.008 |
| 8 | CANNED AND PACKAGED FOODS, CLEANING SUPPLIES, TEA AND SPICES | FOOD STAPLES, PERSONAL CARE | 7.007 | 7.059 | 1.008 |
| 9 | COOKING OIL, PERSONAL CARE | CLEANING SUPPLIES, TEA AND SPICES | 6.911 | 6.986 | 1.011 |
| 10 | CLEANING SUPPLIES, TEA AND SPICES | COOKING OIL, PERSONAL CARE | 6.911 | 6.986 | 1.011 |
| 11 | BISCUITS AND COOKIES, TEA AND SPICES | CANNED AND PACKAGED FOODS, CLEANING SUPPLIES, FOOD STAPLES | 6.517 | 6.509 | 0.999 |
| 12 | CANNED AND PACKAGED FOODS, CLEANING SUPPLIES, FOOD STAPLES | BISCUITS AND COOKIES, TEA AND SPICES | 6.517 | 6.509 | 0.999 |
| 13 | CANNED AND PACKAGED FOODS, COOKING OIL, FOOD STAPLES | CLEANING SUPPLIES, TEA AND SPICES | 6.434 | 6.640 | 1.032 |
| 14 | CLEANING SUPPLIES, TEA AND SPICES | CANNED AND PACKAGED FOODS, COOKING OIL, FOOD STAPLES | 6.434 | 6.640 | 1.032 |
| 15 | CANNED AND PACKAGED FOODS, COOKING OIL | CLEANING SUPPLIES, FOOD STAPLES, TEA AND SPICES | 6.414 | 6.648 | 1.036 |
| 16 | CLEANING SUPPLIES, FOOD STAPLES, TEA AND SPICES | CANNED AND PACKAGED FOODS, COOKING OIL | 6.414 | 6.648 | 1.036 |
| 17 | CLEANING SUPPLIES, FOOD STAPLES | CANNED AND PACKAGED FOODS, PERSONAL CARE, TEA AND SPICES | 6.219 | 6.120 | 0.984 |
| 18 | CANNED AND PACKAGED FOODS, PERSONAL CARE, TEA AND SPICES | CLEANING SUPPLIES, FOOD STAPLES | 6.219 | 6.120 | 0.984 |
| 19 | COOKING OIL, PERSONAL CARE | CLEANING SUPPLIES, FOOD STAPLES | 6.161 | 6.128 | 0.995 |
| 20 | CLEANING SUPPLIES, FOOD STAPLES | COOKING OIL, PERSONAL CARE | 6.161 | 6.128 | 0.995 |

## Ten least stable rules

| antecedents | consequents | dev lift | val lift | ratio |
|---|---|---:|---:|---:|
| COOKING OIL | CANNED AND PACKAGED FOODS, DAIRY PRODUCTS | 1.726 | 1.497 | 0.867 |
| CANNED AND PACKAGED FOODS, DAIRY PRODUCTS | COOKING OIL | 1.726 | 1.497 | 0.867 |
| DAIRY PRODUCTS | COOKING OIL | 1.018 | 0.895 | 0.879 |
| COOKING OIL | DAIRY PRODUCTS | 1.018 | 0.895 | 0.879 |
| COOKING OIL | DAIRY PRODUCTS, TEA AND SPICES | 2.688 | 2.386 | 0.888 |
| DAIRY PRODUCTS, TEA AND SPICES | COOKING OIL | 2.688 | 2.386 | 0.888 |
| DAIRY PRODUCTS | COOKING OIL, TEA AND SPICES | 1.361 | 1.209 | 0.889 |
| COOKING OIL, TEA AND SPICES | DAIRY PRODUCTS | 1.361 | 1.209 | 0.889 |
| COOKING OIL, FOOD STAPLES | DAIRY PRODUCTS | 1.184 | 1.077 | 0.910 |
| DAIRY PRODUCTS | COOKING OIL, FOOD STAPLES | 1.184 | 1.077 | 0.910 |
