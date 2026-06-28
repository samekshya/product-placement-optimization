import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Baniya Shopping Center",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# THEME - light by default, dark optional
# ============================================================

if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

if st.session_state.dark_mode:
    bg          = "#0f0f0f"
    sidebar_bg  = "#1a1a1a"
    card_bg     = "#1a1a1a"
    text        = "#ffffff"
    subtext     = "#888888"
    border      = "#2a2a2a"
    chart_bg    = "#0f0f0f"
    bar_color   = "#3a3a3a"
    annot_color = "white"
else:
    bg          = "#ffffff"
    sidebar_bg  = "#f8f9fa"
    card_bg     = "#f8f9fa"
    text        = "#1a1a1a"
    subtext     = "#666666"
    border      = "#e0e0e0"
    chart_bg    = "#ffffff"
    bar_color   = "#d0d0d0"
    annot_color = "#1a1a1a"

# ============================================================
# CSS STYLING
# ============================================================

st.markdown(f"""
<style>
    .stApp {{
        background-color: {bg};
        color: {text};
    }}
    [data-testid="stSidebar"] {{
        background-color: {sidebar_bg};
        border-right: 1px solid {border};
    }}
    [data-testid="stMetric"] {{
        background-color: {card_bg};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 16px;
    }}
    [data-testid="stMetricValue"] {{
        color: {text};
        font-size: 28px;
        font-weight: 700;
    }}
    [data-testid="stMetricLabel"] {{
        color: {subtext};
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    h1, h2 {{
        color: {text};
        font-weight: 800;
    }}
    h3 {{
        color: {text};
        font-weight: 600;
    }}
    hr {{
        border-color: {border};
    }}
    .insight-box {{
        background-color: {card_bg};
        border-left: 4px solid #e63946;
        padding: 16px 20px;
        border-radius: 4px;
        margin: 12px 0;
    }}
    .insight-box p {{
        margin: 0;
        color: {text};
        font-size: 15px;
    }}
    .insight-title {{
        color: #e63946;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 6px;
    }}
    .rec-card {{
        background-color: {card_bg};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 10px;
    }}
    .rec-product {{
        color: {text};
        font-size: 16px;
        font-weight: 600;
    }}
    .rec-bar-container {{
        background-color: {border};
        border-radius: 4px;
        height: 8px;
        margin-top: 8px;
    }}
    .sidebar-title {{
        color: #e63946;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 16px;
    }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header[data-testid="stHeader"] {{
        background-color: {bg};
    }}
</style>
""", unsafe_allow_html=True)

# ============================================================
# LANGUAGE TRANSLATIONS
# ============================================================

TRANSLATIONS = {
    "English": {
        "title": "Baniya Shopping Center",
        "subtitle": "Product Placement Optimisation System",
        "nav_overview": "Overview",
        "nav_products": "Product Intelligence",
        "nav_recommendations": "Recommendation Engine",
        "nav_zones": "Placement Zones",
        "nav_seasonal": "Seasonal Planning",
        "total_transactions": "Total Transactions",
        "avg_basket": "Avg Basket Value",
        "daily_revenue": "Daily Revenue",
        "daily_customers": "Daily Customers",
        "top_insight": "Top Opportunity",
        "top_insight_text": "Place Rato Dal next to Kalo Dal. They are bought together 4,236 times. This single shelf change could increase basket value immediately.",
        "revenue_chart_title": "Monthly Revenue (Jul 2025 - May 2026)",
        "projection_title": "Revenue Projections from Optimised Placement",
        "conservative": "Conservative 3%",
        "moderate": "Moderate 5% (Recommended)",
        "optimistic": "Optimistic 8%",
    },
    "Nepali": {
        "title": "बनिया शपिङ सेन्टर",
        "subtitle": "उत्पाद राख्ने स्थान अनुकूलन प्रणाली",
        "nav_overview": "सारांश",
        "nav_products": "उत्पाद विश्लेषण",
        "nav_recommendations": "सिफारिस इन्जिन",
        "nav_zones": "राख्ने क्षेत्रहरू",
        "nav_seasonal": "मौसमी योजना",
        "total_transactions": "कुल लेनदेन",
        "avg_basket": "औसत टोकरी मूल्य",
        "daily_revenue": "दैनिक आम्दानी",
        "daily_customers": "दैनिक ग्राहक",
        "top_insight": "शीर्ष अवसर",
        "top_insight_text": "राटो दाल र कालो दाल एकै ठाउँ राख्नुहोस्। यी ४,२३६ पटक सँगै किनिन्छन्।",
        "revenue_chart_title": "मासिक आम्दानी (जुलाई २०२५ - मे २०२६)",
        "projection_title": "अनुकूलित राखाइबाट आम्दानी अनुमान",
        "conservative": "रूढिवादी ३%",
        "moderate": "मध्यम ५% (सिफारिस)",
        "optimistic": "आशावादी ८%",
    }
}

# ============================================================
# DATA PATH
# ============================================================

DATA_PATH = r'D:\softwarica\Sem 6\Individual Project\product-placement-optimization\data\processed\sales_data_cleaned.csv'

# ============================================================
# DATA LOADING FUNCTIONS (cached so they only run once)
# ============================================================

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')
    return df


@st.cache_data
def get_monthly_revenue(df):
    monthly = df.groupby(df['date'].dt.to_period('M'))['total_amount'].sum().reset_index()
    monthly['date'] = monthly['date'].astype(str)
    monthly.columns = ['month', 'revenue']
    return monthly


@st.cache_data
def get_product_rules(df):
    # Find top 100 most sold products
    top_100 = (
        df.groupby('product')['invoice_no']
        .nunique()
        .sort_values(ascending=False)
        .head(100)
    )
    top_names = top_100.index.tolist()

    # Filter data to top 100 products only
    df_top = df[df['product'].isin(top_names)]

    # Group into baskets
    baskets = df_top.groupby('invoice_no')['product'].apply(list)

    # Encode into True/False matrix
    te = TransactionEncoder()
    te_array = te.fit(baskets).transform(baskets)
    basket_df = pd.DataFrame(te_array, columns=te.columns_)

    # 70/30 train test split
    train_df, _ = train_test_split(basket_df, test_size=0.3, random_state=42)

    # Run Apriori on training data only
    frequent = apriori(train_df, min_support=0.005, use_colnames=True)
    rules = association_rules(frequent, metric="lift", min_threshold=1.0)
    rules = rules.sort_values('lift', ascending=False)

    return rules, top_100


@st.cache_data
def get_category_rules(df):
    # Group into category baskets
    baskets = df.groupby('invoice_no')['category'].apply(list)

    # Encode into True/False matrix
    te = TransactionEncoder()
    te_array = te.fit(baskets).transform(baskets)
    basket_df = pd.DataFrame(te_array, columns=te.columns_)

    # Run Apriori on all category data
    frequent = apriori(basket_df, min_support=0.01, use_colnames=True)
    rules = association_rules(frequent, metric="lift", min_threshold=1.0)
    rules = rules.sort_values('lift', ascending=False)

    return rules

# ============================================================
# RECOMMENDATION FUNCTION (the ML model)
# ============================================================

def get_recommendations(product_name, rules_df, top_n=5):
    """
    Takes a product name.
    Searches all association rules for that product on the left side.
    Returns top N products from the right side, ranked by lift.
    Shows support, confidence and lift together for full picture.
    """
    product_name = product_name.strip()
    recommendations = []

    for _, row in rules_df.iterrows():
        antecedents = [a.strip() for a in list(row['antecedents'])]

        if product_name in antecedents:
            for product in list(row['consequents']):
                recommendations.append({
                    'Product': product,
                    'Support': round(row['support'], 4),
                    'Confidence': round(row['confidence'], 2),
                    'Lift': round(row['lift'], 2)
                })

    if not recommendations:
        return None

    rec_df = pd.DataFrame(recommendations)
    rec_df = rec_df.groupby('Product').agg({
        'Support': 'max',
        'Confidence': 'max',
        'Lift': 'max'
    }).reset_index()

    return rec_df.sort_values('Lift', ascending=False).head(top_n)

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    # Language selector
    lang = st.selectbox("Language / भाषा", ["English", "Nepali"])
    T = TRANSLATIONS[lang]

    st.markdown("---")

    # Dark/Light mode toggle
    mode_label = "Switch to Light Mode" if st.session_state.dark_mode else "Switch to Dark Mode"
    if st.button(mode_label):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    st.markdown("---")

    # Navigation
    st.markdown(f'<div class="sidebar-title">Navigation</div>', unsafe_allow_html=True)

    page = st.radio(
        "",
        [
            T["nav_overview"],
            T["nav_products"],
            T["nav_recommendations"],
            T["nav_zones"],
            T["nav_seasonal"]
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Student info
    st.markdown(f"""
    <div style="color: {subtext}; font-size: 11px; line-height: 1.8;">
        <div style="margin-bottom: 4px;">STUDENT</div>
        Samikshya Baniya<br>
        ID: 230360<br>
        ST6001CEM<br>
        Coventry University
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# LOAD DATA
# ============================================================

with st.spinner("Loading data..."):
    df = load_data()
    monthly_revenue = get_monthly_revenue(df)
    product_rules, top_100_products = get_product_rules(df)
    category_rules = get_category_rules(df)

# ============================================================
# PAGE 1 - OVERVIEW
# ============================================================

if page == T["nav_overview"]:

    st.title(T["title"])
    st.markdown(f"#### {T['subtitle']}")
    st.markdown("---")

    # Top insight box
    st.markdown(f"""
    <div class="insight-box">
        <div class="insight-title">{T['top_insight']}</div>
        <p>{T['top_insight_text']}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # KPI cards - row 1
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(T["total_transactions"], "218,037")
    col2.metric(T["avg_basket"], "Rs 1,000.81")
    col3.metric(T["daily_revenue"], "Rs 710,796")
    col4.metric(T["daily_customers"], "710")

    st.markdown("<br>", unsafe_allow_html=True)

    # KPI cards - row 2
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Total Products", "5,681")
    col6.metric("Categories", "25")
    col7.metric("Association Rules", "1,228")
    col8.metric("Max Lift (Product Level)", "22.41")

    st.markdown("<br>", unsafe_allow_html=True)

    # Monthly revenue bar chart
    st.markdown(f"### {T['revenue_chart_title']}")

    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor(chart_bg)
    ax.set_facecolor(chart_bg)

    # Highlight Sep and Oct in red for Dashain
    colors = ['#e63946' if 'Sep' in m or 'Oct' in m else bar_color for m in monthly_revenue['month']]
    ax.bar(monthly_revenue['month'], monthly_revenue['revenue'] / 1_000_000, color=colors, width=0.6)

    ax.set_ylabel('Revenue (Rs Million)', color=subtext, fontsize=11)
    ax.tick_params(colors=subtext)
    ax.spines['bottom'].set_color(border)
    ax.spines['left'].set_color(border)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xticklabels(monthly_revenue['month'], rotation=45, ha='right', color=subtext, fontsize=9)

    # Annotate the Dashain peak
    max_idx = monthly_revenue['revenue'].idxmax()
    max_month = monthly_revenue.iloc[max_idx]
    ax.annotate(
        f"Dashain Peak\nRs {max_month['revenue']/1_000_000:.1f}M",
        xy=(max_idx, max_month['revenue'] / 1_000_000),
        xytext=(max_idx + 0.5, max_month['revenue'] / 1_000_000 + 1),
        color='#e63946',
        fontsize=10,
        fontweight='bold',
        arrowprops=dict(arrowstyle='->', color='#e63946')
    )

    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    st.markdown("<br>", unsafe_allow_html=True)

    # Revenue projections
    st.markdown(f"### {T['projection_title']}")

    col_a, col_b, col_c = st.columns(3)
    col_a.metric(T["conservative"], "Rs 0.78 Crore / year", "Rs 21,370 / day")
    col_b.metric(T["moderate"], "Rs 1.30 Crore / year", "Rs 35,616 / day")
    col_c.metric(T["optimistic"], "Rs 2.08 Crore / year", "Rs 56,986 / day")

    st.markdown(f"""
    <div class="insight-box" style="margin-top: 16px;">
        <div class="insight-title">Why 5% is Realistic</div>
        <p>48 of your 1,228 association rules have lift above 5.0. Maximum lift is 22.41 at product level. These are exceptionally strong patterns. A 5% uplift from acting on them is conservative, not optimistic.</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# PAGE 2 - PRODUCT INTELLIGENCE
# ============================================================

elif page == T["nav_products"]:

    st.title("Product Intelligence")
    st.markdown("---")

    col1, col2 = st.columns(2)

    # Top 20 products bar chart
    with col1:
        st.markdown("### Top 20 Products by Transactions")
        top20 = top_100_products.head(20).reset_index()
        top20.columns = ['Product', 'Transactions']

        fig, ax = plt.subplots(figsize=(8, 9))
        fig.patch.set_facecolor(chart_bg)
        ax.set_facecolor(chart_bg)

        # Highlight top 3 in red
        colors = ['#e63946' if i < 3 else bar_color for i in range(len(top20))]
        ax.barh(top20['Product'][::-1], top20['Transactions'][::-1], color=colors[::-1], height=0.6)
        ax.set_xlabel('Transactions', color=subtext)
        ax.tick_params(colors=subtext, labelsize=9)
        ax.spines['bottom'].set_color(border)
        ax.spines['left'].set_color(border)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    # Top 15 categories bar chart
    with col2:
        st.markdown("### Top 15 Categories by Transactions")
        cat_counts = df.groupby('category')['invoice_no'].nunique().sort_values(ascending=False).head(15)

        fig2, ax2 = plt.subplots(figsize=(8, 9))
        fig2.patch.set_facecolor(chart_bg)
        ax2.set_facecolor(chart_bg)

        # Highlight top 3 in red
        colors2 = ['#e63946' if i < 3 else bar_color for i in range(len(cat_counts))]
        ax2.barh(cat_counts.index[::-1], cat_counts.values[::-1], color=colors2[::-1], height=0.6)
        ax2.set_xlabel('Transactions', color=subtext)
        ax2.tick_params(colors=subtext, labelsize=9)
        ax2.spines['bottom'].set_color(border)
        ax2.spines['left'].set_color(border)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig2)
        plt.close()

    st.markdown("<br>", unsafe_allow_html=True)

    # Co-occurrence heatmap
    st.markdown("### Product Co-occurrence Heatmap (Top 20 Products)")
    st.markdown("Darker red means bought together more often. Use this to decide shelf arrangement.")

    top_20 = top_100_products.head(20).index.tolist()
    df_top20 = df[df['product'].isin(top_20)]
    pivot = df_top20.groupby(['invoice_no', 'product']).size().unstack(fill_value=0)
    pivot = pivot.reindex(columns=top_20, fill_value=0)
    cooc = pivot.T.dot(pivot)
    cooc_array = cooc.values.copy()
    np.fill_diagonal(cooc_array, 0)
    cooc_fixed = pd.DataFrame(cooc_array, index=cooc.index, columns=cooc.columns)

    fig3, ax3 = plt.subplots(figsize=(14, 11))
    fig3.patch.set_facecolor(chart_bg)
    ax3.set_facecolor(chart_bg)

    sns.heatmap(
        cooc_fixed,
        cmap='Reds',
        ax=ax3,
        linewidths=0.3,
        linecolor=border,
        annot=True,
        fmt='g',
        annot_kws={'size': 8, 'color': annot_color},
        cbar_kws={'shrink': 0.8}
    )
    ax3.tick_params(colors=subtext, labelsize=8)
    ax3.set_xticklabels(ax3.get_xticklabels(), rotation=45, ha='right', color=subtext)
    ax3.set_yticklabels(ax3.get_yticklabels(), rotation=0, color=subtext)
    plt.tight_layout()
    st.pyplot(fig3)
    plt.close()

# ============================================================
# PAGE 3 - RECOMMENDATION ENGINE
# ============================================================

elif page == T["nav_recommendations"]:

    st.title("Recommendation Engine")
    st.markdown("Trained on 95,570 baskets. Validated on 40,959 unseen baskets. Hit rate: 28%.")
    st.markdown("---")

    # Model performance metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Training Baskets", "95,570")
    col2.metric("Test Baskets", "40,959")
    col3.metric("Hit Rate", "28%", "28x better than random")

    st.markdown("<br>", unsafe_allow_html=True)

    # Product selector - defaults to Sugar
    all_products = sorted(top_100_products.index.tolist())
    default_idx = all_products.index('Sugar') if 'Sugar' in all_products else 0
    selected = st.selectbox(
        "Select a product to get shelf placement recommendations",
        all_products,
        index=default_idx
    )

    if selected:
        recs = get_recommendations(selected, product_rules)

        if recs is None:
            st.warning(f"No recommendations found for {selected}.")
        else:
            st.markdown(f"### Customers who buy {selected} also buy:")
            st.markdown("<br>", unsafe_allow_html=True)

            max_lift = recs['Lift'].max()

            # Show each recommendation as a card with lift bar
            for _, row in recs.iterrows():
                bar_pct = int((row['Lift'] / max_lift) * 100)
                st.markdown(f"""
                <div class="rec-card">
                    <div class="rec-product">{row['Product']}</div>
                    <div style="color: {subtext}; font-size: 13px; margin-top: 4px;">
                        Lift: <span style="color: #e63946; font-weight: 700;">{row['Lift']}</span>
                        &nbsp;&nbsp;|&nbsp;&nbsp;
                        Confidence: <span style="color: {text};">{row['Confidence']}</span>
                        &nbsp;&nbsp;|&nbsp;&nbsp;
                        Support: <span style="color: {subtext};">{row['Support']}</span>
                    </div>
                    <div class="rec-bar-container">
                        <div style="background-color: #e63946; height: 8px; border-radius: 4px; width: {bar_pct}%;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Shelf placement action box
            st.markdown(f"""
            <div class="insight-box">
                <div class="insight-title">Shelf Placement Action</div>
                <p>Place <strong>{selected}</strong> directly next to <strong>{recs.iloc[0]['Product']}</strong> on the same shelf. Lift of {recs.iloc[0]['Lift']} means customers are {recs.iloc[0]['Lift']}x more likely to buy both together.</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Category level rules table with slider filter
    st.markdown("### Category Level Rules")
    st.markdown("Filter by minimum lift to see which categories belong together. Support, confidence and lift are all shown.")

    min_lift = st.slider("Minimum Lift", 1.0, 7.0, 4.0, 0.1)
    filtered = category_rules[category_rules['lift'] >= min_lift].head(20)

    if len(filtered) > 0:
        display = filtered[['antecedents', 'consequents', 'support', 'confidence', 'lift']].copy()
        display['antecedents'] = display['antecedents'].apply(lambda x: ', '.join(list(x)))
        display['consequents'] = display['consequents'].apply(lambda x: ', '.join(list(x)))
        display.columns = ['If customer buys', 'They also buy', 'Support', 'Confidence', 'Lift']
        st.dataframe(display.reset_index(drop=True), use_container_width=True)
    else:
        st.info("No rules found at this lift level. Lower the minimum lift.")

# ============================================================
# PAGE 4 - PLACEMENT ZONES
# ============================================================

elif page == T["nav_zones"]:

    st.title("Placement Zones")
    st.markdown("5 zones designed from MBA association rules and co-occurrence clustering (silhouette 0.554 at k=3).")
    st.markdown("---")

    # How zones were decided
    st.markdown(f"""
    <div style="background-color: {card_bg}; border: 1px solid {border}; border-radius: 6px; padding: 16px 20px; margin-bottom: 20px;">
        <div style="color: {subtext}; font-size: 12px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;">How zones were decided</div>
        <div style="color: {text}; font-size: 14px; line-height: 1.8;">
            Zones are based on three factors working together. First, association rules showing which categories have high lift AND high support, meaning both a strong relationship and high customer volume. Second, co-occurrence clustering grouping categories bought together into natural zones. Third, physical constraints like refrigeration requirements and customer entry points that limit where certain categories can go regardless of what the data says.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Zone definitions
    zones = [
        {
            "name": "Zone 1 - CENTER",
            "color": "#e63946",
            "label": "High Traffic Anchor Zone",
            "categories": ["FOOD STAPLES", "COOKING OIL", "CLEANING SUPPLIES", "TEA AND SPICES", "HOUSEHOLD ITEMS"],
            "reason": "These categories appear in almost every strong association rule. CLEANING SUPPLIES alone connects to 48 rules with lift above 5. Placing them centrally forces customers to pass other products on the way.",
            "products": ["Sugar", "Rato Dal", "Kalo Dal", "SALT", "Chana"]
        },
        {
            "name": "Zone 2 - ENTRANCE",
            "color": "#457b9d",
            "label": "Impulse Purchase Zone",
            "categories": ["NOODLES", "SOFT DRINKS AND JUICES", "BISCUITS AND COOKIES", "CONFECTIONERY", "NAMKEEN AND SNACKS", "CANNED AND PACKAGED FOODS"],
            "reason": "High frequency impulse categories. Catching customers at the entrance before they focus on essentials increases unplanned purchases.",
            "products": ["WAI WAI CHICKEN", "RARA", "COKE FANTA SPRITE 1.5L", "BADAM RAMRO"]
        },
        {
            "name": "Zone 3 - SIDE AISLE",
            "color": "#2a9d8f",
            "label": "Personal and Household Zone",
            "categories": ["PERSONAL CARE", "BABY CARE", "STATIONERY"],
            "reason": "Destination categories. Customers seeking these will find them without central placement. Side aisle keeps them out of the main traffic flow.",
            "products": ["PATANJALI SOAP", "LUV POUCH DAHI 500ML"]
        },
        {
            "name": "Zone 4 - BACK WALL",
            "color": "#e9c46a",
            "label": "Fresh and Cold Zone",
            "categories": ["DAIRY PRODUCTS", "FROZEN FOODS", "FRUITS AND VEGETABLES", "BAKERY"],
            "reason": "Require refrigeration. Placed at back to draw customers through the entire store, increasing exposure to other products.",
            "products": ["Local Milk 500ml"]
        },
        {
            "name": "Zone 5 - PERIMETER",
            "color": "#6a4c93",
            "label": "Destination and Speciality Zone",
            "categories": ["RICE", "ALCOHOLIC BEVERAGES", "CIGARETTE AND TOBACCO", "POOJA ITEMS", "BREAKFAST CEREALS", "ELECTRICAL SUPPLIES", "PARTY SUPPLIES"],
            "reason": "Low frequency or specialist categories. Customers buying these know what they want and will seek them out.",
            "products": ["Khukuri FT", "Makai", "GHARANA MAIDA 1KG"]
        }
    ]

    # Render each zone as a card
    for zone in zones:
        st.markdown(f"""
        <div style="
            background-color: {card_bg};
            border-left: 4px solid {zone['color']};
            border-radius: 6px;
            padding: 20px 24px;
            margin-bottom: 16px;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="color: {zone['color']}; font-size: 16px; font-weight: 700;">{zone['name']}</div>
                <div style="color: {subtext}; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">{zone['label']}</div>
            </div>
            <div style="color: {text}; font-size: 14px; margin-bottom: 8px;">
                <span style="color: {subtext};">Categories: </span>{', '.join(zone['categories'])}
            </div>
            <div style="color: {subtext}; font-size: 13px; margin-bottom: 8px;">
                <span style="color: {subtext};">Key Products: </span>{', '.join(zone['products'])}
            </div>
            <div style="color: {subtext}; font-size: 13px; line-height: 1.6; border-top: 1px solid {border}; padding-top: 10px; margin-top: 8px;">
                {zone['reason']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Visual store layout map
    st.markdown("### Visual Store Layout")

    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor(chart_bg)
    ax.set_facecolor(chart_bg)

    store_zones = [
        (0.1,  0.1,  0.8,  0.8,  card_bg,   'STORE BOUNDARY',                                          subtext),
        (0.35, 0.3,  0.3,  0.4,  '#e63946', 'ZONE 1\nCENTER\nFood Staples\nCleaning Supplies\nCooking Oil', 'white'),
        (0.05, 0.05, 0.9,  0.15, '#457b9d', 'ZONE 2 - ENTRANCE: Noodles, Soft Drinks, Biscuits, Snacks', 'white'),
        (0.05, 0.25, 0.25, 0.6,  '#2a9d8f', 'ZONE 3\nSIDE AISLE\nPersonal Care\nBaby Care\nStationery', 'white'),
        (0.05, 0.75, 0.9,  0.2,  '#e9c46a', 'ZONE 4 - BACK WALL: Dairy, Frozen, Fruits, Bakery',        '#1a1a1a'),
        (0.7,  0.25, 0.25, 0.45, '#6a4c93', 'ZONE 5\nPERIMETER\nRice\nAlcohol\nCigarettes\nPooja',      'white'),
    ]

    for x, y, w, h, color, label, text_color in store_zones:
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.01",
            facecolor=color,
            edgecolor=border,
            linewidth=2,
            alpha=0.9
        )
        ax.add_patch(rect)
        ax.text(
            x + w/2, y + h/2, label,
            ha='center', va='center',
            color=text_color,
            fontsize=8,
            fontweight='bold',
            wrap=True
        )

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.set_title('Recommended Store Layout', color=subtext, fontsize=13, pad=20)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

# ============================================================
# PAGE 5 - SEASONAL PLANNING
# ============================================================

elif page == T["nav_seasonal"]:

    st.title("Seasonal Planning")
    st.markdown("Stock recommendations by month based on 10 months of real sales data.")
    st.markdown("---")

    # Monthly revenue line chart
    st.markdown("### Monthly Revenue Trend")

    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor(chart_bg)
    ax.set_facecolor(chart_bg)

    ax.plot(
        range(len(monthly_revenue)),
        monthly_revenue['revenue'] / 1_000_000,
        color='#e63946',
        linewidth=2.5,
        marker='o',
        markersize=6,
        markerfacecolor='#e63946',
        markeredgecolor=chart_bg,
        markeredgewidth=2
    )

    ax.fill_between(
        range(len(monthly_revenue)),
        monthly_revenue['revenue'] / 1_000_000,
        alpha=0.1,
        color='#e63946'
    )

    ax.set_xticks(range(len(monthly_revenue)))
    ax.set_xticklabels(monthly_revenue['month'], rotation=45, ha='right', color=subtext, fontsize=9)
    ax.set_ylabel('Revenue (Rs Million)', color=subtext)
    ax.tick_params(colors=subtext)
    ax.spines['bottom'].set_color(border)
    ax.spines['left'].set_color(border)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', color=border, linestyle='--', alpha=0.5)

    # Annotate Dashain peak
    max_idx = monthly_revenue['revenue'].idxmax()
    ax.annotate(
        'Dashain Peak',
        xy=(max_idx, monthly_revenue['revenue'].max() / 1_000_000),
        xytext=(max_idx - 1.5, monthly_revenue['revenue'].max() / 1_000_000 - 2),
        color='#e63946',
        fontsize=10,
        fontweight='bold',
        arrowprops=dict(arrowstyle='->', color='#e63946')
    )

    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    st.markdown("<br>", unsafe_allow_html=True)

    # Season cards
    st.markdown("### Stock Recommendations by Season")

    seasons = [
        {
            "season": "Monsoon (Jul - Sep)",
            "color": "#457b9d",
            "insight": "CLEANING SUPPLIES rises significantly. Stock extra detergent, floor cleaners, and disinfectants. Customers clean more during monsoon.",
            "stock_up": ["CLEANING SUPPLIES", "FOOD STAPLES", "COOKING OIL"],
            "stock_normal": ["ALCOHOLIC BEVERAGES", "SOFT DRINKS"]
        },
        {
            "season": "Festival Season (Sep - Oct)",
            "color": "#e63946",
            "insight": "September 2025 was the highest revenue month at Rs 23.3 million due to Dashain. Stock ALCOHOLIC BEVERAGES 3 weeks before Dashain. Confectionery and gift items spike.",
            "stock_up": ["ALCOHOLIC BEVERAGES", "CONFECTIONERY", "FOOD STAPLES", "POOJA ITEMS"],
            "stock_normal": ["STATIONERY", "ELECTRICAL SUPPLIES"]
        },
        {
            "season": "Winter (Nov - Jan)",
            "color": "#6a4c93",
            "insight": "CIGARETTE AND TOBACCO consistently top 5 in winter months. TEA AND SPICES peaks. Customers buy more warm beverages and comfort food.",
            "stock_up": ["CIGARETTE AND TOBACCO", "TEA AND SPICES", "COOKING OIL", "FOOD STAPLES"],
            "stock_normal": ["SOFT DRINKS AND JUICES", "FROZEN FOODS"]
        },
        {
            "season": "Spring (Feb - Apr)",
            "color": "#2a9d8f",
            "insight": "Regular buying patterns return. No major spikes. Good time to rearrange shelves and implement placement recommendations without disrupting peak season sales.",
            "stock_up": ["FOOD STAPLES", "PERSONAL CARE", "BISCUITS AND COOKIES"],
            "stock_normal": ["ALCOHOLIC BEVERAGES", "POOJA ITEMS"]
        }
    ]

    for s in seasons:
        st.markdown(f"""
        <div style="
            background-color: {card_bg};
            border-left: 4px solid {s['color']};
            border-radius: 6px;
            padding: 20px 24px;
            margin-bottom: 16px;
        ">
            <div style="color: {s['color']}; font-size: 15px; font-weight: 700; margin-bottom: 10px;">{s['season']}</div>
            <div style="color: {text}; font-size: 14px; margin-bottom: 12px; line-height: 1.6;">{s['insight']}</div>
            <div style="display: flex; gap: 40px;">
                <div>
                    <div style="color: {subtext}; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px;">Stock Up</div>
                    {"".join([f'<div style="color: #e63946; font-size: 13px; margin-bottom: 3px;">+ {cat}</div>' for cat in s['stock_up']])}
                </div>
                <div>
                    <div style="color: {subtext}; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px;">Normal Stock</div>
                    {"".join([f'<div style="color: {subtext}; font-size: 13px; margin-bottom: 3px;">= {cat}</div>' for cat in s['stock_normal']])}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Controlled testing implementation guide
    st.markdown(f"""
    <div style="background-color: {card_bg}; border: 1px solid {border}; border-radius: 6px; padding: 20px 24px; margin-bottom: 16px;">
        <div style="color: #e63946; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;">Recommended Implementation Approach</div>
        <div style="color: {text}; font-size: 14px; line-height: 1.8; margin-bottom: 16px;">Do not rearrange the whole store at once. Use a controlled step by step approach:</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <div style="background-color: {bg}; border: 1px solid {border}; border-radius: 4px; padding: 12px;">
                <div style="color: #e63946; font-size: 11px; font-weight: 700; margin-bottom: 6px;">STEP 1 - Week 1 to 4</div>
                <div style="color: {text}; font-size: 13px;">Place Rato Dal next to Kalo Dal. Measure basket value daily. This is your highest confidence change with 4,236 co-occurrences.</div>
            </div>
            <div style="background-color: {bg}; border: 1px solid {border}; border-radius: 4px; padding: 12px;">
                <div style="color: #e63946; font-size: 11px; font-weight: 700; margin-bottom: 6px;">STEP 2 - Week 5 to 8</div>
                <div style="color: {text}; font-size: 13px;">If basket value increased, move CLEANING SUPPLIES to the center zone. Measure again. This is your strongest category level rule.</div>
            </div>
            <div style="background-color: {bg}; border: 1px solid {border}; border-radius: 4px; padding: 12px;">
                <div style="color: #e63946; font-size: 11px; font-weight: 700; margin-bottom: 6px;">STEP 3 - Week 9 to 12</div>
                <div style="color: {text}; font-size: 13px;">Rearrange the entrance zone with impulse items. Noodles, soft drinks, biscuits placed near the door to catch customers first.</div>
            </div>
            <div style="background-color: {bg}; border: 1px solid {border}; border-radius: 4px; padding: 12px;">
                <div style="color: #e63946; font-size: 11px; font-weight: 700; margin-bottom: 6px;">STEP 4 - Week 13 onwards</div>
                <div style="color: {text}; font-size: 13px;">Full zone implementation based on evidence gathered from Steps 1 to 3. By now you have real data proving the approach works.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Final key insight
    st.markdown(f"""
    <div class="insight-box">
        <div class="insight-title">Key Seasonal Insight</div>
        <p>FOOD STAPLES, COOKING OIL and RICE are top 3 every single month without exception. These are your guaranteed sellers regardless of season. Never let these run out of stock.</p>
    </div>
    """, unsafe_allow_html=True)