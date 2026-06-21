import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Baniya Shopping Center - Product Placement Dashboard",
    page_icon="🛒",
    layout="wide"
)

DATA_PATH = r'D:\softwarica\Sem 6\Individual Project\product-placement-optimization\data\processed\sales_data_cleaned.csv'

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)
    return df

@st.cache_data
def get_product_rules(df):
    top_100 = (
        df.groupby('product')['invoice_no']
        .nunique()
        .sort_values(ascending=False)
        .head(100)
    )
    top_names = top_100.index.tolist()
    df_top = df[df['product'].isin(top_names)]
    baskets = df_top.groupby('invoice_no')['product'].apply(list)
    te = TransactionEncoder()
    te_array = te.fit(baskets).transform(baskets)
    basket_df = pd.DataFrame(te_array, columns=te.columns_)
    train_df, _ = train_test_split(basket_df, test_size=0.3, random_state=42)
    frequent = apriori(train_df, min_support=0.005, use_colnames=True)
    rules = association_rules(frequent, metric="lift", min_threshold=1.0)
    rules = rules.sort_values('lift', ascending=False)
    return rules, top_100

@st.cache_data
def get_category_rules(df):
    baskets = df.groupby('invoice_no')['category'].apply(list)
    te = TransactionEncoder()
    te_array = te.fit(baskets).transform(baskets)
    basket_df = pd.DataFrame(te_array, columns=te.columns_)
    frequent = apriori(basket_df, min_support=0.01, use_colnames=True)
    rules = association_rules(frequent, metric="lift", min_threshold=1.0)
    rules = rules.sort_values('lift', ascending=False)
    return rules

def get_recommendations(product_name, rules_df, top_n=5):
    product_name = product_name.strip()
    recommendations = []
    for _, row in rules_df.iterrows():
        antecedents = [a.strip() for a in list(row['antecedents'])]
        if product_name in antecedents:
            for product in list(row['consequents']):
                recommendations.append({
                    'Product': product,
                    'Confidence': round(row['confidence'], 2),
                    'Lift': round(row['lift'], 2)
                })
    if not recommendations:
        return None
    rec_df = pd.DataFrame(recommendations)
    rec_df = rec_df.groupby('Product').agg({
        'Confidence': 'max',
        'Lift': 'max'
    }).reset_index()
    return rec_df.sort_values('Lift', ascending=False).head(top_n)

df = load_data()
product_rules, top_100_products = get_product_rules(df)
category_rules = get_category_rules(df)

st.title("🛒 Baniya Shopping Center")
st.subheader("Product Placement Optimisation Dashboard")
st.markdown("**Student:** Samikshya Baniya | **ID:** 230360 | **Module:** ST6001CEM Individual Project")
st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Store KPIs",
    "🏆 Top Products",
    "🔗 Category Rules",
    "🎯 Product Recommendations",
    "🗺️ Placement Zones"
])

with tab1:
    st.header("Store Key Performance Indicators")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Transactions", "218,037")
    col2.metric("Average Basket Value", "Rs 1,000.81")
    col3.metric("Daily Revenue", "Rs 710,796")
    col4.metric("Daily Customers", "710")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Total Products", "5,681")
    col6.metric("Categories", "25")
    col7.metric("Association Rules", "1,228")
    col8.metric("Max Lift", "6.81")

    st.divider()
    st.subheader("Revenue Projections from Optimised Placement")

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Conservative 3% Uplift", "Rs 0.78 Crore/year", "Extra annual revenue")
    col_b.metric("Moderate 5% Uplift", "Rs 1.30 Crore/year", "Primary recommendation")
    col_c.metric("Optimistic 8% Uplift", "Rs 2.08 Crore/year", "Best case scenario")

    st.info("The moderate 5% scenario is our primary recommendation based on 48 association rules with lift above 5.0")

with tab2:
    st.header("Top Products and Categories")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top 20 Products by Transactions")
        top20 = top_100_products.head(20).reset_index()
        top20.columns = ['Product', 'Transactions']
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.barh(top20['Product'][::-1], top20['Transactions'][::-1], color='steelblue')
        ax.set_xlabel('Number of Transactions')
        ax.set_title('Top 20 Products by Transaction Count')
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    with col2:
        st.subheader("Top 15 Categories by Transaction Count")
        cat_counts = df.groupby('category')['invoice_no'].nunique().sort_values(ascending=False).head(15)
        fig2, ax2 = plt.subplots(figsize=(8, 8))
        ax2.barh(cat_counts.index[::-1], cat_counts.values[::-1], color='coral')
        ax2.set_xlabel('Number of Transactions')
        ax2.set_title('Top 15 Categories')
        plt.tight_layout()
        st.pyplot(fig2)
        plt.close()

with tab3:
    st.header("Category Level Association Rules")
    st.write("These rules come from analysing 218,037 baskets at category level.")

    col1, col2, col3 = st.columns(3)
    min_lift = col1.slider("Minimum Lift", 1.0, 7.0, 3.0, 0.1)
    min_conf = col2.slider("Minimum Confidence", 0.0, 1.0, 0.1, 0.05)
    top_n_rules = col3.slider("Number of rules to show", 5, 50, 20)

    filtered = category_rules[
        (category_rules['lift'] >= min_lift) &
        (category_rules['confidence'] >= min_conf)
    ].head(top_n_rules)

    if len(filtered) == 0:
        st.warning("No rules found with these filters. Try lowering the minimum lift or confidence.")
    else:
        display_rules = filtered[['antecedents', 'consequents', 'support', 'confidence', 'lift']].copy()
        display_rules['antecedents'] = display_rules['antecedents'].apply(lambda x: ', '.join(list(x)))
        display_rules['consequents'] = display_rules['consequents'].apply(lambda x: ', '.join(list(x)))
        display_rules.columns = ['If customer buys', 'They also buy', 'Support', 'Confidence', 'Lift']
        display_rules = display_rules.reset_index(drop=True)
        st.dataframe(display_rules, use_container_width=True)
        st.caption(f"Showing {len(filtered)} rules with lift above {min_lift}")

with tab4:
    st.header("Product Recommendation System")
    st.write("Type any product name to see what customers most often buy with it.")

    all_products = sorted(top_100_products.index.tolist())
    selected_product = st.selectbox("Select a product", all_products)

    if selected_product:
        recs = get_recommendations(selected_product, product_rules)
        if recs is None:
            st.warning(f"No recommendations found for {selected_product}. This product may not appear in enough rules.")
        else:
            st.subheader(f"Customers who buy {selected_product} also buy:")
            st.dataframe(recs, use_container_width=True)

            fig, ax = plt.subplots(figsize=(8, 4))
            ax.barh(recs['Product'][::-1], recs['Lift'][::-1], color='steelblue')
            ax.set_xlabel('Lift Score')
            ax.set_title(f'Recommendation Strength for {selected_product}')
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()

            st.info(f"Shelf recommendation: Place {selected_product} next to {recs.iloc[0]['Product']} (lift: {recs.iloc[0]['Lift']})")

    st.divider()
    st.subheader("Model Performance")
    col1, col2, col3 = st.columns(3)
    col1.metric("Training Baskets", "95,570 (70%)")
    col2.metric("Test Baskets", "40,959 (30%)")
    col3.metric("Hit Rate on Unseen Data", "28%")
    st.caption("The model is 28 times better than random guessing across 100 products")

with tab5:
    st.header("Recommended Placement Zones")
    st.write("Based on MBA association rules and co-occurrence clustering.")

    zones = {
        "Zone 1 - CENTER (High Traffic)": {
            "color": "#FF6B6B",
            "categories": ["FOOD STAPLES", "COOKING OIL", "CLEANING SUPPLIES", "TEA AND SPICES", "HOUSEHOLD ITEMS"],
            "reason": "These categories appear in almost every strong association rule. Placing them centrally ensures customers pass other products on the way to them."
        },
        "Zone 2 - ENTRANCE (Impulse Buys)": {
            "color": "#4ECDC4",
            "categories": ["NOODLES", "SOFT DRINKS AND JUICES", "BISCUITS AND COOKIES", "CONFECTIONERY", "NAMKEEN AND SNACKS", "CANNED AND PACKAGED FOODS"],
            "reason": "High frequency impulse purchase categories. Placing near entrance catches customers before they focus on essentials."
        },
        "Zone 3 - SIDE AISLE": {
            "color": "#45B7D1",
            "categories": ["PERSONAL CARE", "BABY CARE", "STATIONERY"],
            "reason": "Destination categories. Customers seeking these will find them without needing central placement."
        },
        "Zone 4 - BACK WALL": {
            "color": "#96CEB4",
            "categories": ["DAIRY PRODUCTS", "FROZEN FOODS", "FRUITS AND VEGETABLES", "BAKERY"],
            "reason": "Require refrigeration or special storage. Placed at back to draw customers through the store."
        },
        "Zone 5 - PERIMETER": {
            "color": "#FFEAA7",
            "categories": ["RICE", "ALCOHOLIC BEVERAGES", "CIGARETTE AND TOBACCO", "POOJA ITEMS", "BREAKFAST CEREALS", "ELECTRICAL SUPPLIES", "PARTY SUPPLIES"],
            "reason": "Low frequency or destination categories. Customers seek these out specifically."
        }
    }

    for zone_name, zone_data in zones.items():
        with st.expander(zone_name, expanded=True):
            st.markdown(f"**Categories:** {', '.join(zone_data['categories'])}")
            st.markdown(f"**Why:** {zone_data['reason']}")

    st.divider()
    st.subheader("Key Product Shelf Recommendations")
    st.write("Based on product level MBA on top 100 products:")

    shelf_recs = [
        ("Rato Dal", "Kalo Dal", "4,236 co-occurrences"),
        ("Sugar", "Rato Dal", "3,771 co-occurrences"),
        ("Wai Wai Chicken", "RARA", "1,662 co-occurrences - place all noodles together"),
        ("Surya", "Shikhar Ice", "lift 22.41 - strongest product pair"),
        ("PRAWN 120gm", "SADA PAPAD", "lift 11.89 - snack combination"),
        ("Mong Khosta", "Rato Dal", "2,284 co-occurrences - place all dal together"),
    ]

    for item1, item2, reason in shelf_recs:
        st.markdown(f"- **{item1}** next to **{item2}** — {reason}")

st.divider()
st.caption("Baniya Shopping Center, Lamachour-16, Pokhara, Nepal | ST6001CEM Individual Project | Samikshya Baniya 230360")