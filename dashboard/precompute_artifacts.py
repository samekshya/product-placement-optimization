"""
Precompute dashboard artifacts.

The dashboard must run for a marker on a fresh clone WITHOUT the confidential
114 MB cleaned CSV and without rerunning Apriori on every launch. This script
reads the cleaned data ONCE, runs the heavy analytics, and writes small files
to dashboard/artifacts/ that app.py loads instantly.

Run this once (with the processed data present) before publishing:

    python dashboard/precompute_artifacts.py

It reproduces the exact parameters used in notebooks 05 (MBA), 06 (clustering)
and 07 (placement) so every number matches the verified project figures:
    218,037 transactions | 25 categories | mean basket Rs 1000.81
    total revenue Rs 218,214,456.88 | 1,228 category rules | max lift 6.81
    silhouette 0.554 at k=3 | top pair Kalo Dal + Rato Dal ~ 3,989
"""

import datetime
import json
import os

import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# ------------------------------------------------------------------
# Paths (relative to this file, so it works from any clone location)
# ------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
PROCESSED = os.path.join(PROJECT_ROOT, "data", "processed")
CLEANED_CSV = os.path.join(PROCESSED, "sales_data_cleaned.csv")
BASKET_CSV = os.path.join(PROCESSED, "basket_encoded.csv")
ARTIFACTS = os.path.join(HERE, "artifacts")

os.makedirs(ARTIFACTS, exist_ok=True)

# Constants used by the notebooks for the projection maths.
DATA_DAYS = 307  # data covers 307 days (notebook 07)

# The 5 optimised placement zones (notebook 07). Used for the cross-sell
# before/after analysis (RQ2) so the dashboard and notebook agree.
OPTIMISED_ZONES = {
    "Zone 1: Daily Essentials Core": [
        "FOOD STAPLES", "COOKING OIL", "CLEANING SUPPLIES",
        "TEA AND SPICES", "HOUSEHOLD ITEMS",
    ],
    "Zone 2: Snacks and Drinks": [
        "NOODLES", "SOFT DRINKS AND JUICES", "BISCUITS AND COOKIES",
        "CONFECTIONERY", "NAMKEEN AND SNACKS", "CANNED AND PACKAGED FOODS",
    ],
    "Zone 3: Personal and Baby Care": [
        "PERSONAL CARE", "BABY CARE", "STATIONERY",
    ],
    "Zone 4: Dairy and Fresh": [
        "DAIRY PRODUCTS", "FROZEN FOODS", "FRUITS AND VEGETABLES", "BAKERY",
    ],
    "Zone 5: Special Categories": [
        "RICE", "ALCOHOLIC BEVERAGES", "CIGARETTE AND TOBACCO",
        "POOJA ITEMS", "BREAKFAST CEREALS", "ELECTRICAL SUPPLIES",
        "PARTY SUPPLIES",
    ],
}


def log(msg):
    print(f"[precompute] {msg}")


def frozenset_to_str(fs):
    return ", ".join(sorted(list(fs)))


# ==================================================================
# 1. Load source data
# ==================================================================
log("Loading cleaned transactions ...")
df = pd.read_csv(CLEANED_CSV)
df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")

log("Loading category basket matrix ...")
basket_df = pd.read_csv(BASKET_CSV)  # 218,037 x 25 booleans

# ==================================================================
# 2. KPI summary
# ==================================================================
log("Computing KPI summary ...")
basket_values = df.groupby("invoice_no")["total_amount"].sum()
total_revenue = float(df["total_amount"].sum())
total_baskets = int(df["invoice_no"].nunique())
avg_basket = float(basket_values.mean())
median_basket = float(basket_values.median())
n_categories = int(df["category"].nunique())
n_products = int(df["product"].nunique())
daily_revenue = total_revenue / DATA_DAYS
daily_customers = total_baskets / DATA_DAYS

top_category = (
    df.groupby("category")["invoice_no"].nunique().sort_values(ascending=False).index[0]
)

# ==================================================================
# 3. Monthly revenue trend
# ==================================================================
log("Computing monthly revenue ...")
monthly = (
    df.groupby(df["date"].dt.to_period("M"))
    .agg(revenue=("total_amount", "sum"), baskets=("invoice_no", "nunique"))
    .reset_index()
)
monthly["month"] = monthly["date"].astype(str)
monthly["avg_basket"] = monthly["revenue"] / monthly["baskets"]
monthly = monthly[["month", "revenue", "baskets", "avg_basket"]]
monthly.to_csv(os.path.join(ARTIFACTS, "monthly_revenue.csv"), index=False)

# ==================================================================
# 4. Category distribution (share of baskets each category appears in)
# ==================================================================
log("Computing category distribution ...")
cat_counts = (
    df.groupby("category")["invoice_no"].nunique().sort_values(ascending=False)
)
cat_dist = cat_counts.reset_index()
cat_dist.columns = ["category", "baskets"]
cat_dist["pct_of_baskets"] = (cat_dist["baskets"] / total_baskets * 100).round(2)
cat_dist.to_csv(os.path.join(ARTIFACTS, "category_distribution.csv"), index=False)

# ==================================================================
# 5. Basket-value distribution (histogram bins, keeps file tiny)
# ==================================================================
log("Computing basket-value histogram ...")
clipped = basket_values.clip(upper=5000)  # long tail trimmed for display only
counts, edges = np.histogram(clipped, bins=40)
hist_df = pd.DataFrame({
    "bin_left": edges[:-1].round(2),
    "bin_right": edges[1:].round(2),
    "count": counts,
})
hist_df.to_csv(os.path.join(ARTIFACTS, "basket_value_hist.csv"), index=False)

# ==================================================================
# 5b. ABC analysis of products (notebook 03 Chart 10)
# ==================================================================
log("Computing ABC analysis ...")
product_revenue = df.groupby("product")["total_amount"].sum().sort_values(ascending=False)
abc_cumulative_pct = product_revenue.cumsum() / product_revenue.sum() * 100


def abc_class(pct):
    if pct <= 70:
        return "A"
    elif pct <= 90:
        return "B"
    return "C"


abc_df = pd.DataFrame({
    "product": product_revenue.index,
    "revenue": product_revenue.values.round(2),
    "cumulative_pct": abc_cumulative_pct.values.round(4),
    "abc_category": abc_cumulative_pct.apply(abc_class).values,
})
abc_df.to_csv(os.path.join(ARTIFACTS, "abc_analysis.csv"), index=False)
abc_counts = abc_df["abc_category"].value_counts()
log(
    f"  -> A: {abc_counts.get('A', 0):,}  B: {abc_counts.get('B', 0):,}  "
    f"C: {abc_counts.get('C', 0):,} products"
)

# ==================================================================
# 5c. Day of week revenue (notebook 03 Chart 11)
# ==================================================================
log("Computing day of week revenue ...")
day_order = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
df["day_name"] = df["date"].dt.day_name()
baskets_by_day = df.groupby("invoice_no").agg(
    basket_value=("total_amount", "sum"),
    day_name=("day_name", "first"),
)
dow_df = pd.DataFrame({
    "day_name": day_order,
    "revenue": df.groupby("day_name")["total_amount"].sum().reindex(day_order).round(2).values,
    "transaction_count": baskets_by_day["day_name"].value_counts().reindex(day_order).values,
    "avg_basket": baskets_by_day.groupby("day_name")["basket_value"].mean().reindex(day_order).round(2).values,
})
dow_df.to_csv(os.path.join(ARTIFACTS, "day_of_week.csv"), index=False)
log(
    f"  -> highest revenue day: {dow_df.loc[dow_df['revenue'].idxmax(), 'day_name']}, "
    f"highest avg basket day: {dow_df.loc[dow_df['avg_basket'].idxmax(), 'day_name']}"
)

# ==================================================================
# 5d. Subcategory summary (notebook 12) -- used by the dashboard
#     Subcategory Analysis page. Keyword rules are kept in sync with
#     notebooks/12_subcategory_analysis.ipynb (first match wins).
# ==================================================================
log("Computing subcategory summary (notebook 12) ...")

from collections import Counter
from itertools import combinations

TOP5_CATEGORIES = ['FOOD STAPLES', 'CANNED AND PACKAGED FOODS', 'TEA AND SPICES',
                   'COOKING OIL', 'CLEANING SUPPLIES']

SUBCATEGORY_KEYWORDS = {
    'FOOD STAPLES': [
        ('Grains and Flour',    ['RICE', 'CHAMAL', 'MAKAI', 'AATA', 'MAIDA', 'SUJI', 'PITHO',
                                 'BHUJA', 'CHIURA', 'CHAKKI', 'BASMATI', 'JEERA MASINO', 'DHAN']),
        ('Seasonings',          ['DALCHINI', 'SALT', 'NUN', 'JEERA', 'METHI', 'JWANO', 'TILL',
                                 'TIL ', 'SOFF', 'PANCHAPURAN', 'DHANIYA', 'TESTING', 'AJINOMOTO', 'MASALA']),
        ('Pulses',              ['DAL', 'DAAL', 'CHANA', 'CHAANA', 'KERAU', 'MONG', 'MASHURO',
                                 'BHATTA', 'BODI', 'RAHAR', 'SIMI']),
        ('Sweeteners',          ['SUGAR', 'SAKKHAR', 'GUD', 'JAGGERY', 'MISHRI', 'CHAKU', 'CHINI']),
        ('Dairy and Eggs',      ['MILK', 'EGG', 'DUDH', 'PANEER', 'GHIU']),
        ('Nuts and Dry Fruits', ['BADAM', 'MIXNUT', 'COCONUT', 'KAJU', 'OKHAR', 'KISMISS',
                                 'CASHEW', 'ALMOND']),
    ],
    'CANNED AND PACKAGED FOODS': [
        ('Noodles and Pasta',         ['CHOWMIN', 'RAMEN', 'RAMYAN', 'MACARONI', 'MACORONI', 'PASTA',
                                       'NOODLE', 'WAI WAI', 'WAIWAI', '2PM', '2 PM', 'SOUP',
                                       'SAMYANG', 'BULDAK']),
        ('Chips and Snacks',          ['LAYS', 'CHIPS', 'CHEESEBALL', 'CHEESE BALL', 'STICKS', 'BHUJA',
                                       'DALMOT', 'FURANDANA', 'KURKURE', 'CURRENT', 'CRAX', 'RINGS',
                                       'JHILINGA', 'PRAWN']),
        ('Papad and Fryums',          ['PAPAD', 'FRYUMS', 'FRYUM']),
        ('Dry Fruits and Nuts',       ['KAJU', 'ALMOND', 'OKHAR', 'KISMISS', 'MIXNUT', 'BADAM',
                                       'ANJEER', 'CHHOKADA', 'DATES']),
        ('Pickles and Sauces',        ['PICKLE', 'ACHAR', 'CHUK', 'SAUCE', 'KETCHUP', 'JAM ', 'HONEY',
                                       'TITAURA', 'VINEGAR', 'MAYONNAISE']),
        ('Health Drinks and Cereals', ['HORLICKS', 'BOURNVITA', 'VIVA', 'OATS', 'CORNFLAKES', 'MUESLI',
                                       'MUSELI', 'CEREAL', 'GLUCOSE', 'COMPLAN']),
        ('Beaten Rice and Flakes',    ['CHIURA', 'FLAKES']),
    ],
    'TEA AND SPICES': [
        ('Tea',                      ['TEA', 'CHIYA', 'TOKLA', 'SAIDEEP', 'SAI DEEP', 'MITTAL', 'SARBADA']),
        ('Coffee',                   ['NES', 'COFFEE', 'MAC ']),
        ('Masala Blends',            ['MASALA']),
        ('Whole Spices',             ['MARIJ', 'SUKMEL', 'LWANG', 'JEERA', 'TILL', 'JWANO', 'METHI',
                                      'SOFF', 'DALCHINI', 'TEJPAT', 'ALAICHI', 'BIRE']),
        ('Spice Powders and Flours', ['CHILLYPOW', 'TUMERIC', 'TURMERIC', 'BESHAN', 'PITHO', 'POWDER',
                                      'HALDI', 'KHURSANI']),
    ],
    'COOKING OIL': [
        ('Sunflower Oil',           ['SUNFLOWER', 'SUNFLOWEER', 'SUNFLOW', 'SUNF ', 'SUNBEAN SUN']),
        ('Mustard Oil',             ['MUSTARD', 'TORI']),
        ('Soybean Oil',             ['SOYABEAN', 'SOYBEAN']),
        ('Ghee and Vanaspati',      ['GHEE', 'DALDA', 'VANASPATI']),
        ('Blended and Health Oils', ['HEALTH', 'CORN', 'SAFFOLA', 'OLIVE', 'RICE BRAN']),
    ],
    'CLEANING SUPPLIES': [
        ('Detergent Powder',          ['RIN ', 'TIDE', 'ARIEL', 'WHEEL', 'SURF', 'XTRAA PLUS', 'HENKO',
                                       'DAZ ', 'DET ']),
        ('Washing Soap Bars',         ['SOAP', 'LUX', 'TIKA', 'DHONI', 'RICH', 'ZOOM', 'AAHA',
                                       'XTRAA NEEM', 'DTT', 'DETTOL', 'LIFEBUOY', 'LB ', 'LIRIL',
                                       'DOVE', 'SANTOOR', 'HANDWASH']),
        ('Dishwash',                  ['VIM', 'EXO', 'DISHWASH', 'PITAMBARI', 'SCOTCH', 'JUNA']),
        ('Toilet and Floor Cleaners', ['HRP', 'HARPIC', 'COLIN', 'LIZOL', 'LYS', 'PHENYL', 'TOILET',
                                       'FLOOR', 'ACID', 'BRUSH', 'BROOM', 'KUCHO', 'MOP']),
    ],
}


def assign_subcategory(product_name, category):
    name = str(product_name).upper()
    for subcat, keywords in SUBCATEGORY_KEYWORDS[category]:
        for kw in keywords:
            if kw in name:
                return subcat
    return 'Other'


top5_sc = df[df["category"].isin(TOP5_CATEGORIES)].copy()
unique_sc = top5_sc[["category", "product"]].drop_duplicates().copy()
unique_sc["subcategory"] = unique_sc.apply(
    lambda r: assign_subcategory(r["product"], r["category"]), axis=1
)
top5_sc = top5_sc.merge(unique_sc, on=["category", "product"], how="left")

subcat_rows = []
for cat in TOP5_CATEGORIES:
    sub = top5_sc[top5_sc["category"] == cat]
    total_tx = sub["invoice_no"].nunique()
    stats = sub.groupby("subcategory").agg(
        n_products=("product", "nunique"),
        transactions=("invoice_no", "nunique"),
    ).sort_values("transactions", ascending=False)

    # Within-category subcategory co-occurrence (Other excluded: a shelf
    # cannot be arranged around an unnamed residual group).
    named = sub[sub["subcategory"] != "Other"]
    sc_basket = named.groupby(["invoice_no", "subcategory"]).size().unstack(fill_value=0) > 0
    sc_pairs = {}
    for a, b in combinations(sorted(sc_basket.columns), 2):
        sc_pairs[(a, b)] = int((sc_basket[a] & sc_basket[b]).sum())

    for subcat, row in stats.iterrows():
        prods = sub[sub["subcategory"] == subcat]
        example_products = ", ".join(
            prods.groupby("product")["invoice_no"].nunique()
            .sort_values(ascending=False).head(3).index.tolist()
        )
        if subcat == "Other":
            partner, shared, top_pair, top_pair_count = "-", "-", "-", "-"
        else:
            cand = [(p, c) for p, c in sc_pairs.items() if subcat in p]
            best_p, best_c = max(cand, key=lambda x: x[1]) if cand else ((subcat, "-"), 0)
            partner = best_p[1] if best_p[0] == subcat else best_p[0]
            shared = best_c
            # Top product pair inside this subcategory
            pc = Counter()
            for items in prods.groupby("invoice_no")["product"].apply(set):
                if len(items) > 1:
                    items = sorted(items)
                    for i in range(len(items)):
                        for j in range(i + 1, len(items)):
                            pc[(items[i], items[j])] += 1
            if pc:
                (pa, pb), cnt = pc.most_common(1)[0]
                top_pair, top_pair_count = f"{pa} + {pb}", cnt
            else:
                top_pair, top_pair_count = "-", "-"
        subcat_rows.append({
            "category": cat,
            "subcategory": subcat,
            "n_products": int(row["n_products"]),
            "transactions": int(row["transactions"]),
            "share_pct": round(row["transactions"] / total_tx * 100, 1),
            "top_partner_subcategory": partner,
            "shared_baskets": shared,
            "top_product_pair": top_pair,
            "top_pair_count": top_pair_count,
            "example_products": example_products,
        })

subcat_summary_df = pd.DataFrame(subcat_rows)
subcat_summary_df.to_csv(os.path.join(ARTIFACTS, "subcategory_summary.csv"), index=False)
log(
    f"  -> {len(subcat_summary_df)} subcategory rows across {len(TOP5_CATEGORIES)} categories "
    f"({(subcat_summary_df['subcategory'] != 'Other').sum()} named subcategories)"
)

# ==================================================================
# 6. Category association rules (notebook 05 parameters: support 0.01)
# ==================================================================
log("Mining category association rules (Apriori, min_support=0.01) ...")
frequent = apriori(basket_df, min_support=0.01, use_colnames=True)
category_rules = association_rules(frequent, metric="lift", min_threshold=1.0)
category_rules = category_rules.sort_values("lift", ascending=False).reset_index(drop=True)

rules_out = category_rules[["antecedents", "consequents", "support", "confidence", "lift"]].copy()
rules_out["antecedents"] = rules_out["antecedents"].apply(frozenset_to_str)
rules_out["consequents"] = rules_out["consequents"].apply(frozenset_to_str)
rules_out.to_csv(os.path.join(ARTIFACTS, "category_rules.csv"), index=False)
log(f"  -> {len(rules_out):,} category rules, max lift {category_rules['lift'].max():.2f}")

# ==================================================================
# 7. Category co-occurrence matrix (notebook 06)
# ==================================================================
log("Computing category co-occurrence matrix ...")
basket_numeric = basket_df.astype(int)
cooccurrence = basket_numeric.T.dot(basket_numeric)
cooccurrence.to_csv(os.path.join(ARTIFACTS, "cooccurrence_matrix.csv"))

# ==================================================================
# 8. Clustering (notebook 06): frequency k=5 vs co-occurrence k=3
# ==================================================================
log("Reproducing clustering (frequency k=5 and co-occurrence k=3) ...")
category_matrix = basket_df.T
freq_scaled = StandardScaler().fit_transform(category_matrix)
freq_labels = KMeans(n_clusters=5, random_state=42, n_init=10).fit_predict(freq_scaled)

cooc_array = cooccurrence.values.astype(float).copy()
np.fill_diagonal(cooc_array, 0)
cooc_scaled = StandardScaler().fit_transform(cooc_array)
cooc_labels = KMeans(n_clusters=3, random_state=42, n_init=10).fit_predict(cooc_scaled)
cooc_sil = silhouette_score(cooc_scaled, cooc_labels)

cluster_assign = pd.DataFrame({
    "category": basket_df.columns,
    "frequency_cluster": freq_labels,
    "cooccurrence_cluster": cooc_labels,
})
cluster_assign.to_csv(os.path.join(ARTIFACTS, "cluster_assignments.csv"), index=False)
log(f"  -> co-occurrence silhouette at k=3: {cooc_sil:.3f}")

# ==================================================================
# 9. Top product pairs (co-occurrence on raw product baskets)
# ==================================================================
log("Computing top product pairs ...")
top_100 = (
    df.groupby("product")["invoice_no"].nunique().sort_values(ascending=False).head(100)
)
top_names = top_100.index.tolist()
df_top = df[df["product"].isin(top_names)]
prod_baskets = df_top.groupby("invoice_no")["product"].apply(set)

from collections import Counter
pair_counts = Counter()
for items in prod_baskets:
    items = sorted(items)
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            pair_counts[(items[i], items[j])] += 1

top_pairs = pd.DataFrame(
    [(a, b, c) for (a, b), c in pair_counts.most_common(50)],
    columns=["product_a", "product_b", "cooccurrences"],
)
top_pairs.to_csv(os.path.join(ARTIFACTS, "top_pairs.csv"), index=False)
kalo = pair_counts.get(("Kalo Dal", "Rato Dal"), 0) or pair_counts.get(("Rato Dal", "Kalo Dal"), 0)
log(f"  -> Kalo Dal + Rato Dal co-occurrences: {kalo:,}")

# ==================================================================
# 10. Product-level association rules (notebook 09: top 100, 70/30 split)
# ==================================================================
log("Mining product-level rules (top 100 products, 70/30 split) ...")
te = TransactionEncoder()
te_array = te.fit(df_top.groupby("invoice_no")["product"].apply(list)).transform(
    df_top.groupby("invoice_no")["product"].apply(list)
)
prod_basket_df = pd.DataFrame(te_array, columns=te.columns_)
train_df, _ = train_test_split(prod_basket_df, test_size=0.3, random_state=42)
prod_frequent = apriori(train_df, min_support=0.005, use_colnames=True)
product_rules = association_rules(prod_frequent, metric="lift", min_threshold=1.0)
product_rules = product_rules.sort_values("lift", ascending=False).reset_index(drop=True)

prod_rules_out = product_rules[["antecedents", "consequents", "support", "confidence", "lift"]].copy()
prod_rules_out["antecedents"] = prod_rules_out["antecedents"].apply(frozenset_to_str)
prod_rules_out["consequents"] = prod_rules_out["consequents"].apply(frozenset_to_str)
prod_rules_out.to_csv(os.path.join(ARTIFACTS, "product_rules.csv"), index=False)

# Product list (with basket counts) for the recommendation explorer dropdown.
top_100.reset_index().rename(
    columns={"product": "product", "invoice_no": "baskets"}
).to_csv(os.path.join(ARTIFACTS, "top_products.csv"), index=False)
log(f"  -> {len(prod_rules_out):,} product rules, max lift {product_rules['lift'].max():.2f}")

# ==================================================================
# 11. Cross-sell before/after (RQ2 / Objective 4) -- data driven
# ==================================================================
# A strong cross-sell rule (lift >= 3) is "captured" by a layout when every
# category in the rule sits in the same group, i.e. the products are placed
# next to each other so the cross-sell can actually happen. We compare the
# CURRENT layout (frequency k=5 clusters -- the unoptimised grouping that the
# project shows is driven by popularity, not co-purchase) against the
# OPTIMISED 5-zone layout, and report how much more strong-rule support each
# captures. This is a data-driven before/after, NOT the Rs projection.
log("Computing cross-sell before/after (lift >= 3) ...")

LIFT_FLOOR = 3.0
strong = category_rules[category_rules["lift"] >= LIFT_FLOOR].copy()
strong["cats"] = strong.apply(
    lambda r: set(r["antecedents"]) | set(r["consequents"]), axis=1
)

current_groups = [
    set(cluster_assign[cluster_assign["frequency_cluster"] == c]["category"])
    for c in sorted(cluster_assign["frequency_cluster"].unique())
]
optimised_groups = [set(v) for v in OPTIMISED_ZONES.values()]


def captured(cats, groups):
    return any(cats <= g for g in groups)


def score_layout(groups):
    mask = strong["cats"].apply(lambda c: captured(c, groups))
    return int(mask.sum()), float(strong.loc[mask, "support"].sum())


cur_n, cur_support = score_layout(current_groups)
opt_n, opt_support = score_layout(optimised_groups)
total_strong = len(strong)
total_strong_support = float(strong["support"].sum())

cross_sell = {
    "lift_floor": LIFT_FLOOR,
    "total_strong_rules": total_strong,
    "total_strong_support": round(total_strong_support, 4),
    "current_layout": "Frequency-based clusters (unoptimised baseline)",
    "optimised_layout": "5 designed placement zones",
    "current_rules_captured": cur_n,
    "optimised_rules_captured": opt_n,
    "rules_captured_delta": opt_n - cur_n,
    "current_support_captured": round(cur_support, 4),
    "optimised_support_captured": round(opt_support, 4),
    "support_captured_delta": round(opt_support - cur_support, 4),
    "current_capture_pct": round(cur_support / total_strong_support * 100, 1) if total_strong_support else 0,
    "optimised_capture_pct": round(opt_support / total_strong_support * 100, 1) if total_strong_support else 0,
}
with open(os.path.join(ARTIFACTS, "cross_sell_summary.json"), "w") as f:
    json.dump(cross_sell, f, indent=2)
log(
    f"  -> strong rules captured: current {cur_n} -> optimised {opt_n} "
    f"(+{opt_n - cur_n})"
)

# ==================================================================
# 12. KPI summary JSON (written last so it can include rule counts)
# ==================================================================
kpi = {
    "generated_at": datetime.datetime.now().strftime("%d %b %Y, %H:%M"),
    "total_transactions": total_baskets,
    "total_revenue": round(total_revenue, 2),
    "avg_basket_value": round(avg_basket, 2),
    "median_basket_value": round(median_basket, 2),
    "n_categories": n_categories,
    "n_products": n_products,
    "daily_revenue": round(daily_revenue, 2),
    "daily_customers": round(daily_customers),
    "top_category": top_category,
    "n_category_rules": int(len(category_rules)),
    "max_lift_category": round(float(category_rules["lift"].max()), 2),
    "max_lift_product": round(float(product_rules["lift"].max()), 2),
    "rules_lift_above_5": int((category_rules["lift"] > 5).sum()),
    "cooccurrence_silhouette_k3": round(float(cooc_sil), 3),
    "data_days": DATA_DAYS,
}
with open(os.path.join(ARTIFACTS, "kpi_summary.json"), "w") as f:
    json.dump(kpi, f, indent=2)

log("Done. Artifacts written to dashboard/artifacts/")
for name in sorted(os.listdir(ARTIFACTS)):
    size = os.path.getsize(os.path.join(ARTIFACTS, name))
    log(f"  {name:<28} {size/1024:8.1f} KB")
