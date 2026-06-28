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
# THEME
# ============================================================

if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "Owner"

if st.session_state.dark_mode:
    bg         = "#0f0f0f"
    card_bg    = "#1a1a1a"
    text       = "#ffffff"
    subtext    = "#888888"
    border     = "#2a2a2a"
    chart_bg   = "#0f0f0f"
    bar_color  = "#3a3a3a"
    annot_col  = "white"
else:
    bg         = "#ffffff"
    card_bg    = "#f8f9fa"
    text       = "#1a1a1a"
    subtext    = "#666666"
    border     = "#e0e0e0"
    chart_bg   = "#ffffff"
    bar_color  = "#d0d0d0"
    annot_col  = "#1a1a1a"

st.markdown(f"""
<style>
    .stApp {{ background-color: {bg}; color: {text}; }}
    [data-testid="stSidebar"] {{ background-color: {card_bg}; border-right: 1px solid {border}; }}
    [data-testid="stMetric"] {{ background-color: {card_bg}; border: 1px solid {border}; border-radius: 8px; padding: 16px; }}
    [data-testid="stMetricValue"] {{ color: {text}; font-size: 28px; font-weight: 700; }}
    [data-testid="stMetricLabel"] {{ color: {subtext}; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }}
    h1, h2, h3 {{ color: {text}; }}
    hr {{ border-color: {border}; }}
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    header[data-testid="stHeader"] {{ background-color: {bg}; }}
    .mode-badge {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 16px;
    }}
    .rec-card {{
        background-color: {card_bg};
        border: 1px solid {border};
        border-left: 4px solid #e63946;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 10px;
    }}
    .action-box {{
        background-color: {card_bg};
        border: 2px solid #e63946;
        border-radius: 8px;
        padding: 20px 24px;
        margin: 16px 0;
    }}
    .month-card {{
        background-color: {card_bg};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }}
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATA PATH
# ============================================================

DATA_PATH = r'D:\softwarica\Sem 6\Individual Project\product-placement-optimization\data\processed\sales_data_cleaned.csv'

# ============================================================
# DATA LOADING
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
    top_100 = df.groupby('product')['invoice_no'].nunique().sort_values(ascending=False).head(100)
    top_names = top_100.index.tolist()
    df_top = df[df['product'].isin(top_names)]
    baskets = df_top.groupby('invoice_no')['product'].apply(list)
    te = TransactionEncoder()
    te_array = te.fit(baskets).transform(baskets)
    basket_df = pd.DataFrame(te_array, columns=te.columns_)
    train_df, _ = train_test_split(basket_df, test_size=0.3, random_state=42)
    frequent = apriori(train_df, min_support=0.005, use_colnames=True)
    rules = association_rules(frequent, metric="lift", min_threshold=1.0)
    return rules.sort_values('lift', ascending=False), top_100

@st.cache_data
def get_category_rules(df):
    baskets = df.groupby('invoice_no')['category'].apply(list)
    te = TransactionEncoder()
    te_array = te.fit(baskets).transform(baskets)
    basket_df = pd.DataFrame(te_array, columns=te.columns_)
    frequent = apriori(basket_df, min_support=0.01, use_colnames=True)
    rules = association_rules(frequent, metric="lift", min_threshold=1.0)
    return rules.sort_values('lift', ascending=False)

def get_recommendations(product_name, rules_df, top_n=5):
    product_name = product_name.strip()
    recs = []
    for _, row in rules_df.iterrows():
        ants = [a.strip() for a in list(row['antecedents'])]
        if product_name in ants:
            for p in list(row['consequents']):
                recs.append({
                    'Product': p,
                    'Support': round(row['support'], 4),
                    'Confidence': round(row['confidence'], 2),
                    'Lift': round(row['lift'], 2)
                })
    if not recs:
        return None
    rec_df = pd.DataFrame(recs)
    rec_df = rec_df.groupby('Product').agg({'Support': 'max', 'Confidence': 'max', 'Lift': 'max'}).reset_index()
    return rec_df.sort_values('Lift', ascending=False).head(top_n)

# ============================================================
# SEASONAL STOCK DATA
# ============================================================

SEASONAL_STOCK = {
    "July": {"season": "Monsoon", "stock_up": ["CLEANING SUPPLIES", "FOOD STAPLES", "COOKING OIL"], "reduce": ["SOFT DRINKS", "PARTY SUPPLIES"], "tip": "Monsoon starts. Customers clean more. Stock extra detergent and floor cleaners."},
    "August": {"season": "Monsoon", "stock_up": ["CLEANING SUPPLIES", "FOOD STAPLES", "NOODLES"], "reduce": ["FROZEN FOODS", "PARTY SUPPLIES"], "tip": "Peak monsoon. NOODLES spike as customers want quick meals during rain."},
    "September": {"season": "Dashain", "stock_up": ["ALCOHOLIC BEVERAGES", "CONFECTIONERY", "FOOD STAPLES", "POOJA ITEMS"], "reduce": ["STATIONERY", "ELECTRICAL SUPPLIES"], "tip": "Dashain month. Highest revenue month in your data at Rs 23.3 million. Stock ALCOHOL 3 weeks early."},
    "October": {"season": "Tihar", "stock_up": ["CONFECTIONERY", "POOJA ITEMS", "ALCOHOLIC BEVERAGES", "FOOD STAPLES"], "reduce": ["FROZEN FOODS"], "tip": "Tihar follows Dashain. Confectionery and sweets peak. Keep POOJA ITEMS well stocked."},
    "November": {"season": "Winter Start", "stock_up": ["TEA AND SPICES", "CIGARETTE AND TOBACCO", "COOKING OIL", "FOOD STAPLES"], "reduce": ["SOFT DRINKS AND JUICES"], "tip": "Winter begins. TEA AND SPICES peak. Cigarette sales consistently top 5 in cold months."},
    "December": {"season": "Winter", "stock_up": ["TEA AND SPICES", "CIGARETTE AND TOBACCO", "FOOD STAPLES", "COOKING OIL"], "reduce": ["SOFT DRINKS AND JUICES", "FROZEN FOODS"], "tip": "Deep winter. Same pattern as November. FOOD STAPLES and TEA are your anchor categories."},
    "January": {"season": "Winter", "stock_up": ["TEA AND SPICES", "CIGARETTE AND TOBACCO", "FOOD STAPLES"], "reduce": ["SOFT DRINKS AND JUICES"], "tip": "Coldest month. Focus on warm beverage categories and essential food staples."},
    "February": {"season": "Spring Start", "stock_up": ["FOOD STAPLES", "PERSONAL CARE", "BISCUITS AND COOKIES"], "reduce": ["CIGARETTE AND TOBACCO"], "tip": "Regular patterns return. Good time to start rearranging shelves before the next festival season."},
    "March": {"season": "Spring", "stock_up": ["FOOD STAPLES", "PERSONAL CARE", "COOKING OIL"], "reduce": [], "tip": "Stable month. No major spikes. Focus on maintaining core category stock levels."},
    "April": {"season": "Spring", "stock_up": ["FOOD STAPLES", "SOFT DRINKS AND JUICES", "PERSONAL CARE"], "reduce": [], "tip": "Temperatures rising. SOFT DRINKS start to increase. Stock up ahead of summer."},
    "May": {"season": "Pre Summer", "stock_up": ["SOFT DRINKS AND JUICES", "FOOD STAPLES", "PERSONAL CARE"], "reduce": [], "tip": "Pre summer spike in cold drinks. SOFT DRINKS AND JUICES will peak in coming months."},
    "June": {"season": "Summer", "stock_up": ["SOFT DRINKS AND JUICES", "FOOD STAPLES", "CLEANING SUPPLIES"], "reduce": [], "tip": "Summer peak for cold drinks. Data for June is incomplete in this dataset so use trend from April and May."},
}

# ============================================================
# LOAD DATA
# ============================================================

with st.spinner("Loading..."):
    df = load_data()
    monthly_revenue = get_monthly_revenue(df)
    product_rules, top_100_products = get_product_rules(df)
    category_rules = get_category_rules(df)

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    # Mode toggle - the most important button
    st.markdown(f"<div style='color: {subtext}; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;'>View Mode</div>", unsafe_allow_html=True)

    current_mode = st.session_state.view_mode
    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("Store Owner", use_container_width=True, type="primary" if current_mode == "Owner" else "secondary"):
            st.session_state.view_mode = "Owner"
            st.rerun()

    with col_b:
        if st.button("Examiner", use_container_width=True, type="primary" if current_mode == "Examiner" else "secondary"):
            st.session_state.view_mode = "Examiner"
            st.rerun()

    st.markdown("---")

    # Dark mode toggle
    mode_label = "Light Mode" if st.session_state.dark_mode else "Dark Mode"
    if st.button(mode_label, use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    st.markdown("---")

    # Navigation changes based on mode
    if st.session_state.view_mode == "Owner":
        st.markdown(f"<div style='color: #e63946; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;'>Store Owner Tools</div>", unsafe_allow_html=True)
        page = st.radio("", ["Shelf Planner", "Monthly Stock Plan", "Store Performance"], label_visibility="collapsed")
    else:
        st.markdown(f"<div style='color: #e63946; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;'>Technical Analysis</div>", unsafe_allow_html=True)
        page = st.radio("", ["Project Overview", "Association Rules", "Clustering Results", "Model Validation", "Placement Zones"], label_visibility="collapsed")

    st.markdown("---")

    st.markdown(f"""
    <div style="color: {subtext}; font-size: 11px; line-height: 1.8;">
        Samikshya Baniya<br>
        ID: 230360<br>
        ST6001CEM<br>
        Coventry University
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# OWNER MODE - PAGE 1: SHELF PLANNER
# ============================================================

if st.session_state.view_mode == "Owner" and page == "Shelf Planner":

    st.title("Shelf Planner")
    st.markdown(f"<div style='color: {subtext}; font-size: 15px; margin-bottom: 24px;'>Type any product to find out what to place next to it on the shelf.</div>", unsafe_allow_html=True)
    st.markdown("---")

    all_products = sorted(top_100_products.index.tolist())
    default_idx = all_products.index('Sugar') if 'Sugar' in all_products else 0
    selected = st.selectbox("Select a product", all_products, index=default_idx)

    if selected:
        recs = get_recommendations(selected, product_rules)

        if recs is None:
            st.warning(f"No shelf recommendations found for {selected}. Try a different product.")
        else:
            # Top action - the most important thing
            top_rec = recs.iloc[0]
            st.markdown(f"""
            <div class="action-box">
                <div style="color: {subtext}; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Shelf Action</div>
                <div style="color: {text}; font-size: 22px; font-weight: 700; margin-bottom: 8px;">
                    Place <span style="color: #e63946;">{selected}</span> next to <span style="color: #e63946;">{top_rec['Product']}</span>
                </div>
                <div style="color: {subtext}; font-size: 14px;">
                    Customers who buy {selected} buy {top_rec['Product']} together {int(top_rec['Confidence'] * 100)}% of the time.
                    This relationship is {top_rec['Lift']}x stronger than random chance.
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"### All products to place near {selected}")

            for _, row in recs.iterrows():
                bar_pct = int((row['Lift'] / recs['Lift'].max()) * 100)
                st.markdown(f"""
                <div class="rec-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="color: {text}; font-size: 16px; font-weight: 600;">{row['Product']}</div>
                        <div style="color: #e63946; font-size: 14px; font-weight: 700;">Bought together {int(row['Confidence'] * 100)}% of the time</div>
                    </div>
                    <div style="color: {subtext}; font-size: 12px; margin-top: 6px;">
                        Lift: {row['Lift']} &nbsp;|&nbsp; Support: {row['Support']} &nbsp;|&nbsp; Confidence: {row['Confidence']}
                    </div>
                    <div style="background-color: {border}; border-radius: 4px; height: 6px; margin-top: 10px;">
                        <div style="background-color: #e63946; height: 6px; border-radius: 4px; width: {bar_pct}%;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### Top Shelf Pairs in the Store")
    st.markdown(f"<div style='color: {subtext}; font-size: 14px; margin-bottom: 16px;'>These are the strongest product pairs from 218,037 real shopping trips. Put these products side by side.</div>", unsafe_allow_html=True)

    top_pairs = [
        ("Rato Dal", "Kalo Dal", "4,236 co-occurrences", "69% of Kalo Dal buyers also buy Rato Dal"),
        ("Sugar", "Rato Dal", "3,771 co-occurrences", "Classic dal bhat cooking combination"),
        ("Wai Wai Chicken", "RARA", "1,662 co-occurrences", "Both noodle brands bought together constantly"),
        ("Surya", "Shikhar Ice", "Lift 22.41", "Strongest product pair, place on same shelf"),
        ("PRAWN 120gm", "SADA PAPAD", "Lift 11.89", "Snack combination, place in same section"),
        ("Mong Khosta", "Rato Dal", "2,284 co-occurrences", "Place all dal varieties together"),
    ]

    for p1, p2, metric, reason in top_pairs:
        st.markdown(f"""
        <div class="month-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="color: {text}; font-size: 15px; font-weight: 600;">
                    <span style="color: #e63946;">{p1}</span> &nbsp;+&nbsp; <span style="color: #e63946;">{p2}</span>
                </div>
                <div style="color: {subtext}; font-size: 12px;">{metric}</div>
            </div>
            <div style="color: {subtext}; font-size: 13px; margin-top: 6px;">{reason}</div>
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# OWNER MODE - PAGE 2: MONTHLY STOCK PLAN
# ============================================================

elif st.session_state.view_mode == "Owner" and page == "Monthly Stock Plan":

    import datetime
    current_month = datetime.datetime.now().strftime("%B")

    st.title("Monthly Stock Plan")
    st.markdown(f"<div style='color: {subtext}; font-size: 15px; margin-bottom: 24px;'>Stock recommendations based on 10 months of real sales data from Baniya Shopping Center.</div>", unsafe_allow_html=True)
    st.markdown("---")

    # Current month recommendation - big and clear
    month_data = SEASONAL_STOCK.get(current_month, SEASONAL_STOCK["June"])

    st.markdown(f"""
    <div class="action-box">
        <div style="color: {subtext}; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">This Month</div>
        <div style="color: {text}; font-size: 28px; font-weight: 800; margin-bottom: 4px;">{current_month} &nbsp; <span style="color: #e63946; font-size: 16px;">{month_data['season']}</span></div>
        <div style="color: {subtext}; font-size: 14px; margin-top: 8px;">{month_data['tip']}</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"### Stock Up Now")
        for cat in month_data['stock_up']:
            st.markdown(f"""
            <div style="background-color: {card_bg}; border: 1px solid {border}; border-left: 4px solid #e63946; border-radius: 6px; padding: 12px 16px; margin-bottom: 8px;">
                <div style="color: #e63946; font-size: 13px; font-weight: 700;">+ {cat}</div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"### Normal Stock")
        if month_data['reduce']:
            for cat in month_data['reduce']:
                st.markdown(f"""
                <div style="background-color: {card_bg}; border: 1px solid {border}; border-left: 4px solid {border}; border-radius: 6px; padding: 12px 16px; margin-bottom: 8px;">
                    <div style="color: {subtext}; font-size: 13px;">= {cat}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='color: {subtext}; font-size: 14px; margin-top: 8px;'>All categories at normal stock levels this month.</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")

    # Month selector for planning ahead
    st.markdown("### Plan Ahead")
    selected_month = st.selectbox("Select a month to plan for", list(SEASONAL_STOCK.keys()))
    plan = SEASONAL_STOCK[selected_month]

    st.markdown(f"""
    <div class="month-card">
        <div style="color: {text}; font-size: 18px; font-weight: 700; margin-bottom: 8px;">{selected_month} &nbsp; <span style="color: #e63946; font-size: 14px;">{plan['season']}</span></div>
        <div style="color: {subtext}; font-size: 14px; margin-bottom: 16px;">{plan['tip']}</div>
        <div style="color: #e63946; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Stock Up</div>
        {"".join([f'<div style="color: {text}; font-size: 14px; margin-bottom: 4px;">+ {cat}</div>' for cat in plan['stock_up']])}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Key rule
    st.markdown(f"""
    <div style="background-color: {card_bg}; border: 1px solid {border}; border-radius: 8px; padding: 20px 24px;">
        <div style="color: {subtext}; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Rule that never changes</div>
        <div style="color: {text}; font-size: 16px; font-weight: 600;">FOOD STAPLES, COOKING OIL and RICE are top 3 every single month without exception.</div>
        <div style="color: {subtext}; font-size: 14px; margin-top: 8px;">Never let these run out of stock regardless of season.</div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# OWNER MODE - PAGE 3: STORE PERFORMANCE
# ============================================================

elif st.session_state.view_mode == "Owner" and page == "Store Performance":

    st.title("Store Performance")
    st.markdown(f"<div style='color: {subtext}; font-size: 15px; margin-bottom: 24px;'>Based on 10 months of real sales data from Baniya Shopping Center, Pokhara.</div>", unsafe_allow_html=True)
    st.markdown("---")

    # The one number that matters
    st.markdown(f"""
    <div class="action-box">
        <div style="color: {subtext}; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Primary KPI</div>
        <div style="color: {text}; font-size: 48px; font-weight: 800;">Rs 1,000.81</div>
        <div style="color: {subtext}; font-size: 14px; margin-top: 4px;">Average basket value across 218,037 transactions</div>
        <div style="color: #e63946; font-size: 14px; font-weight: 600; margin-top: 8px;">Target: increase this by 5% to Rs 1,050.85</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Daily Revenue", "Rs 710,796")
    col2.metric("Daily Customers", "710")
    col3.metric("Total Products", "5,681")

    st.markdown("<br>", unsafe_allow_html=True)

    # Revenue chart
    st.markdown("### Monthly Revenue")

    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor(chart_bg)
    ax.set_facecolor(chart_bg)

    colors = ['#e63946' if 'Sep' in m or 'Oct' in m else bar_color for m in monthly_revenue['month']]
    ax.bar(monthly_revenue['month'], monthly_revenue['revenue'] / 1_000_000, color=colors, width=0.6)
    ax.set_ylabel('Revenue (Rs Million)', color=subtext)
    ax.tick_params(colors=subtext)
    ax.spines['bottom'].set_color(border)
    ax.spines['left'].set_color(border)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xticklabels(monthly_revenue['month'], rotation=45, ha='right', color=subtext, fontsize=9)
    max_idx = monthly_revenue['revenue'].idxmax()
    max_month = monthly_revenue.iloc[max_idx]
    ax.annotate(
        f"Dashain Peak\nRs {max_month['revenue']/1_000_000:.1f}M",
        xy=(max_idx, max_month['revenue'] / 1_000_000),
        xytext=(max_idx + 0.5, max_month['revenue'] / 1_000_000 + 1),
        color='#e63946', fontsize=10, fontweight='bold',
        arrowprops=dict(arrowstyle='->', color='#e63946')
    )
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    st.markdown("<br>", unsafe_allow_html=True)

    # Revenue projections
    st.markdown("### How Much Can You Earn from Rearranging Shelves?")

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Conservative 3%", "Rs 0.78 Crore / year", "Rs 21,370 extra per day")
    col_b.metric("Moderate 5%", "Rs 1.30 Crore / year", "Rs 35,616 extra per day")
    col_c.metric("Optimistic 8%", "Rs 2.08 Crore / year", "Rs 56,986 extra per day")

    st.markdown(f"""
    <div style="background-color: {card_bg}; border: 1px solid {border}; border-radius: 8px; padding: 20px 24px; margin-top: 16px;">
        <div style="color: {subtext}; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">How to start</div>
        <div style="color: {text}; font-size: 15px; font-weight: 600; margin-bottom: 8px;">Start with one shelf change. Measure for 4 weeks. Then expand.</div>
        <div style="color: {subtext}; font-size: 14px;">First move: Place Rato Dal next to Kalo Dal. They are bought together 4,236 times. This is your safest first step.</div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# EXAMINER MODE - PAGE 1: PROJECT OVERVIEW
# ============================================================

elif st.session_state.view_mode == "Examiner" and page == "Project Overview":

    st.title("Project Overview")
    st.markdown(f"<div style='color: {subtext}; font-size: 15px;'>Data Analytics and Machine Learning Based Product Placement Optimisation to Increase Sales in a Nepali Grocery Retail Store</div>", unsafe_allow_html=True)
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Raw Rows", "768,222")
    col2.metric("Clean Rows", "767,180")
    col3.metric("Transactions", "218,037")
    col4.metric("Products", "5,681")

    st.markdown("<br>", unsafe_allow_html=True)

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Categories", "25")
    col6.metric("MBA Rules", "1,228")
    col7.metric("Max Lift (Category)", "6.81")
    col8.metric("Max Lift (Product)", "22.41")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Analysis Pipeline")

    steps = [
        ("01", "Data Audit", "Examined 768,222 raw rows. Found 1,040 duplicates, 168,864 trailing spaces. Confirmed header=7 gives correct row count."),
        ("02", "Data Cleaning", "Removed duplicates and bad rows. Standardised 38 product groups into 25 clean categories. Final: 767,180 rows."),
        ("03", "EDA", "8 charts. FOOD STAPLES in 42.2% of baskets. Average basket Rs 1,000.81. Kalo Dal and Rato Dal co-occur 4,000 times."),
        ("04", "Transaction Encoding", "Converted to basket matrix: 218,037 rows x 25 columns. True/False per category per invoice."),
        ("05", "Market Basket Analysis", "Apriori and FP-Growth both found 243 itemsets and 1,228 rules. Max lift 6.81. 48 rules above lift 5."),
        ("06", "Clustering", "Frequency K-Means: silhouette 0.19. Co-occurrence K-Means: silhouette 0.554 at k=3. 189% improvement."),
        ("07", "Placement Simulation", "5 zones designed. 5% uplift projects Rs 1.30 crore extra revenue per year."),
        ("08", "Evaluation", "Algorithm comparison, 6 limitations, 7 future recommendations."),
        ("09", "ML Recommendation", "Product level MBA on top 100 products. 70/30 train test split. 28% hit rate on unseen data. Max lift 22.41."),
    ]

    for num, title, desc in steps:
        st.markdown(f"""
        <div style="background-color: {card_bg}; border: 1px solid {border}; border-radius: 6px; padding: 16px 20px; margin-bottom: 10px; display: flex; gap: 16px; align-items: flex-start;">
            <div style="color: #e63946; font-size: 20px; font-weight: 800; min-width: 32px;">{num}</div>
            <div>
                <div style="color: {text}; font-size: 15px; font-weight: 600; margin-bottom: 4px;">{title}</div>
                <div style="color: {subtext}; font-size: 13px; line-height: 1.6;">{desc}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# EXAMINER MODE - PAGE 2: ASSOCIATION RULES
# ============================================================

elif st.session_state.view_mode == "Examiner" and page == "Association Rules":

    st.title("Association Rules")
    st.markdown(f"<div style='color: {subtext}; font-size: 15px; margin-bottom: 24px;'>1,228 rules from 218,037 baskets. Apriori and FP-Growth produced identical results, validating the findings.</div>", unsafe_allow_html=True)
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Rules", "1,228")
    col2.metric("Rules with Lift > 5", "48")
    col3.metric("Max Lift (Category)", "6.81")
    col4.metric("Max Lift (Product)", "22.41")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background-color: {card_bg}; border: 1px solid {border}; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px;">
        <div style="color: {subtext}; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">What the three metrics mean</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px;">
            <div>
                <div style="color: #e63946; font-size: 13px; font-weight: 700; margin-bottom: 4px;">Support</div>
                <div style="color: {subtext}; font-size: 13px;">How common is this combination. Support 0.01 means it appears in at least 1% of all 218,037 baskets, so at least 2,180 baskets.</div>
            </div>
            <div>
                <div style="color: #e63946; font-size: 13px; font-weight: 700; margin-bottom: 4px;">Confidence</div>
                <div style="color: {subtext}; font-size: 13px;">If a customer buys A, how likely are they to also buy B. Confidence 0.69 means 69% of the time.</div>
            </div>
            <div>
                <div style="color: #e63946; font-size: 13px; font-weight: 700; margin-bottom: 4px;">Lift</div>
                <div style="color: {subtext}; font-size: 13px;">How much more likely A and B are bought together vs random chance. Lift 6.81 means 6.81x more likely. Lift above 3 is considered strong.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Interactive rule filter
    st.markdown("### Filter Rules")

    col_f1, col_f2 = st.columns(2)
    min_lift = col_f1.slider("Minimum Lift", 1.0, 7.0, 3.0, 0.1)
    min_conf = col_f2.slider("Minimum Confidence", 0.0, 1.0, 0.1, 0.05)

    filtered = category_rules[
        (category_rules['lift'] >= min_lift) &
        (category_rules['confidence'] >= min_conf)
    ].head(30)

    if len(filtered) > 0:
        display = filtered[['antecedents', 'consequents', 'support', 'confidence', 'lift']].copy()
        display['antecedents'] = display['antecedents'].apply(lambda x: ', '.join(list(x)))
        display['consequents'] = display['consequents'].apply(lambda x: ', '.join(list(x)))
        display.columns = ['If customer buys', 'They also buy', 'Support', 'Confidence', 'Lift']
        st.dataframe(display.reset_index(drop=True), use_container_width=True)
        st.caption(f"{len(filtered)} rules shown. Support, Confidence and Lift all displayed together as your examiner recommended.")
    else:
        st.info("No rules at this filter level. Lower the minimum lift.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Scatter plot
    st.markdown("### Rules Scatter Plot")

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(chart_bg)
    ax.set_facecolor(chart_bg)

    scatter = ax.scatter(
        category_rules['support'],
        category_rules['confidence'],
        c=category_rules['lift'],
        cmap='Reds',
        s=80,
        alpha=0.7
    )
    plt.colorbar(scatter, label='Lift', ax=ax)
    ax.set_xlabel('Support', color=subtext)
    ax.set_ylabel('Confidence', color=subtext)
    ax.set_title('Category Association Rules: Support vs Confidence coloured by Lift', color=text)
    ax.tick_params(colors=subtext)
    ax.spines['bottom'].set_color(border)
    ax.spines['left'].set_color(border)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

# ============================================================
# EXAMINER MODE - PAGE 3: CLUSTERING RESULTS
# ============================================================

elif st.session_state.view_mode == "Examiner" and page == "Clustering Results":

    st.title("Clustering Results")
    st.markdown(f"<div style='color: {subtext}; font-size: 15px; margin-bottom: 24px;'>Comparison of frequency based vs co-occurrence based K-Means clustering.</div>", unsafe_allow_html=True)
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    col1.metric("Frequency Clustering", "0.19", "Silhouette at k=5 - weak")
    col2.metric("Co-occurrence Clustering", "0.554", "Silhouette at k=3 - strong")
    col3.metric("Improvement", "189%", "By asking the right question")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background-color: {card_bg}; border: 1px solid {border}; border-radius: 8px; padding: 20px 24px; margin-bottom: 20px;">
        <div style="color: {text}; font-size: 15px; font-weight: 600; margin-bottom: 8px;">Why co-occurrence is better</div>
        <div style="color: {subtext}; font-size: 14px; line-height: 1.8;">
            Frequency clustering asks "how often is this category bought?" FOOD STAPLES at 42.2% dominates and forms its own cluster just because of its size. That is not useful for placement decisions.
            <br><br>
            Co-occurrence clustering asks "how often are these two categories bought together?" This directly answers the placement question: which categories belong next to each other on the shop floor.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Three Placement Clusters at k=3")

    clusters = [
        {
            "name": "Cluster 1 - Daily Essentials",
            "color": "#e63946",
            "categories": ["CLEANING SUPPLIES", "COOKING OIL", "TEA AND SPICES", "BISCUITS AND COOKIES", "DAIRY PRODUCTS", "SOFT DRINKS AND JUICES", "CONFECTIONERY", "HOUSEHOLD ITEMS", "PERSONAL CARE", "NOODLES"],
            "note": "Bought together regularly on typical shopping trips."
        },
        {
            "name": "Cluster 2 - Occasional and Speciality",
            "color": "#457b9d",
            "categories": ["ALCOHOLIC BEVERAGES", "CIGARETTE AND TOBACCO", "BABY CARE", "STATIONERY", "ELECTRICAL SUPPLIES", "POOJA ITEMS", "FROZEN FOODS", "FRUITS AND VEGETABLES", "PARTY SUPPLIES", "NAMKEEN AND SNACKS", "RICE", "BREAKFAST CEREALS", "BAKERY"],
            "note": "Bought on specific occasions or for specific purposes."
        },
        {
            "name": "Cluster 3 - Core Staples",
            "color": "#2a9d8f",
            "categories": ["FOOD STAPLES", "CANNED AND PACKAGED FOODS"],
            "note": "Co-occur so strongly they form their own cluster. Bought together 31,074 times."
        }
    ]

    for cluster in clusters:
        st.markdown(f"""
        <div style="background-color: {card_bg}; border-left: 4px solid {cluster['color']}; border-radius: 6px; padding: 16px 20px; margin-bottom: 12px;">
            <div style="color: {cluster['color']}; font-size: 15px; font-weight: 700; margin-bottom: 8px;">{cluster['name']}</div>
            <div style="color: {text}; font-size: 13px; margin-bottom: 8px;">{', '.join(cluster['categories'])}</div>
            <div style="color: {subtext}; font-size: 13px; font-style: italic;">{cluster['note']}</div>
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# EXAMINER MODE - PAGE 4: MODEL VALIDATION
# ============================================================

elif st.session_state.view_mode == "Examiner" and page == "Model Validation":

    st.title("Model Validation")
    st.markdown(f"<div style='color: {subtext}; font-size: 15px; margin-bottom: 24px;'>Product level ML recommendation system. Trained on top 100 most sold products with 70/30 train test split.</div>", unsafe_allow_html=True)
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Training Baskets", "95,570 (70%)")
    col2.metric("Test Baskets", "40,959 (30%)")
    col3.metric("Hit Rate", "28%")
    col4.metric("vs Random Chance", "28x better")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background-color: {card_bg}; border: 1px solid {border}; border-radius: 8px; padding: 20px 24px; margin-bottom: 20px;">
        <div style="color: {text}; font-size: 15px; font-weight: 600; margin-bottom: 12px;">Why 28% hit rate is good</div>
        <div style="color: {subtext}; font-size: 14px; line-height: 1.8;">
            The model had to pick from 100 possible products. Random guessing would give 1% accuracy.
            Our model gives 28%, which is 28 times better than random chance.
            <br><br>
            The model was trained on 70% of baskets only and tested on 40,959 baskets it had never seen.
            Achieving 28% hit rate on completely unseen data confirms the model learned real patterns,
            not just memorised the training data.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Product Level Rules")
    st.markdown(f"<div style='color: {subtext}; font-size: 14px; margin-bottom: 16px;'>100 rules from top 100 products. Max lift 22.41, much stronger than category level max of 6.81.</div>", unsafe_allow_html=True)

    all_products = sorted(top_100_products.index.tolist())
    default_idx = all_products.index('Sugar') if 'Sugar' in all_products else 0
    selected = st.selectbox("Select a product to see its rules", all_products, index=default_idx)

    if selected:
        recs = get_recommendations(selected, product_rules)
        if recs is None:
            st.info(f"No rules found for {selected}.")
        else:
            st.dataframe(recs, use_container_width=True)
            st.caption("Support, Confidence and Lift shown together. High lift with decent support = strong actionable rule.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Key Product Findings")

    findings = [
        ("Surya + Shikhar Ice", "Lift 22.41", "Strongest pair. 22x more likely to be bought together than random."),
        ("PRAWN + SADA PAPAD", "Lift 11.89", "Strong snack combination. Place in same section."),
        ("Mong Khosta + Aadar Dal", "Lift 10.20", "Dal combination. Place all dal varieties together."),
        ("Rato Dal + Sugar + Kalo Dal", "Lift 7.72", "Classic Nepali dal bhat cooking pattern."),
        ("Wai Wai Chicken + RARA", "Lift 6.94", "Two noodle brands bought together constantly."),
    ]

    for pair, metric, insight in findings:
        st.markdown(f"""
        <div style="background-color: {card_bg}; border: 1px solid {border}; border-radius: 6px; padding: 14px 18px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <div style="color: {text}; font-size: 14px; font-weight: 600; margin-bottom: 4px;">{pair}</div>
                <div style="color: {subtext}; font-size: 13px;">{insight}</div>
            </div>
            <div style="color: #e63946; font-size: 14px; font-weight: 700; white-space: nowrap; margin-left: 16px;">{metric}</div>
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# EXAMINER MODE - PAGE 5: PLACEMENT ZONES
# ============================================================

elif st.session_state.view_mode == "Examiner" and page == "Placement Zones":

    st.title("Placement Zones")
    st.markdown(f"<div style='color: {subtext}; font-size: 15px; margin-bottom: 24px;'>5 zones derived from MBA association rules and co-occurrence clustering (silhouette 0.554 at k=3).</div>", unsafe_allow_html=True)
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    col1.metric("Zones Designed", "5")
    col2.metric("Conservative Uplift", "Rs 0.78 Crore / year")
    col3.metric("Moderate Uplift (5%)", "Rs 1.30 Crore / year")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background-color: {card_bg}; border: 1px solid {border}; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px;">
        <div style="color: {subtext}; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Zone design methodology</div>
        <div style="color: {text}; font-size: 14px; line-height: 1.8;">
            Zones use three factors together. First, MBA rules with high lift AND high support so both relationship strength and customer volume are considered. Second, co-occurrence clustering grouping categories that are bought together. Third, physical constraints including refrigeration requirements for dairy and frozen foods, and customer entry point assumptions.
        </div>
    </div>
    """, unsafe_allow_html=True)

    zones = [
        {"name": "Zone 1 - CENTER", "color": "#e63946", "label": "High Traffic Anchor", "categories": ["FOOD STAPLES", "COOKING OIL", "CLEANING SUPPLIES", "TEA AND SPICES", "HOUSEHOLD ITEMS"], "reason": "CLEANING SUPPLIES connects to 48 rules with lift above 5. FOOD STAPLES appears in 42.2% of all baskets. Central placement forces customers to pass other products."},
        {"name": "Zone 2 - ENTRANCE", "color": "#457b9d", "label": "Impulse Purchase", "categories": ["NOODLES", "SOFT DRINKS AND JUICES", "BISCUITS AND COOKIES", "CONFECTIONERY", "NAMKEEN AND SNACKS", "CANNED AND PACKAGED FOODS"], "reason": "High frequency impulse categories. Entrance placement captures customers before they focus on essentials, increasing unplanned purchases."},
        {"name": "Zone 3 - SIDE AISLE", "color": "#2a9d8f", "label": "Destination", "categories": ["PERSONAL CARE", "BABY CARE", "STATIONERY"], "reason": "Customers seeking these products will find them regardless of placement. Side aisle keeps them out of the main traffic flow."},
        {"name": "Zone 4 - BACK WALL", "color": "#e9c46a", "label": "Cold Storage", "categories": ["DAIRY PRODUCTS", "FROZEN FOODS", "FRUITS AND VEGETABLES", "BAKERY"], "reason": "Physical constraint: refrigeration required. Back placement also draws customers through the store, increasing exposure to other products."},
        {"name": "Zone 5 - PERIMETER", "color": "#6a4c93", "label": "Speciality", "categories": ["RICE", "ALCOHOLIC BEVERAGES", "CIGARETTE AND TOBACCO", "POOJA ITEMS", "BREAKFAST CEREALS", "ELECTRICAL SUPPLIES", "PARTY SUPPLIES"], "reason": "Low frequency or destination categories. Customers buying these seek them out specifically. Perimeter placement reduces main aisle congestion."},
    ]

    for zone in zones:
        st.markdown(f"""
        <div style="background-color: {card_bg}; border-left: 4px solid {zone['color']}; border-radius: 6px; padding: 18px 22px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="color: {zone['color']}; font-size: 15px; font-weight: 700;">{zone['name']}</div>
                <div style="color: {subtext}; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">{zone['label']}</div>
            </div>
            <div style="color: {text}; font-size: 13px; margin-bottom: 8px;">{', '.join(zone['categories'])}</div>
            <div style="color: {subtext}; font-size: 13px; line-height: 1.6; border-top: 1px solid {border}; padding-top: 8px; margin-top: 8px;">{zone['reason']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Visual store map
    st.markdown("### Visual Store Layout")
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor(chart_bg)
    ax.set_facecolor(chart_bg)
    store_zones = [
        (0.1, 0.1, 0.8, 0.8, card_bg, 'STORE BOUNDARY', subtext),
        (0.35, 0.3, 0.3, 0.4, '#e63946', 'ZONE 1\nCENTER\nFood Staples\nCleaning Supplies\nCooking Oil', 'white'),
        (0.05, 0.05, 0.9, 0.15, '#457b9d', 'ZONE 2 - ENTRANCE: Noodles, Soft Drinks, Biscuits, Snacks', 'white'),
        (0.05, 0.25, 0.25, 0.6, '#2a9d8f', 'ZONE 3\nSIDE AISLE\nPersonal Care\nBaby Care\nStationery', 'white'),
        (0.05, 0.75, 0.9, 0.2, '#e9c46a', 'ZONE 4 - BACK WALL: Dairy, Frozen, Fruits, Bakery', '#1a1a1a'),
        (0.7, 0.25, 0.25, 0.45, '#6a4c93', 'ZONE 5\nPERIMETER\nRice\nAlcohol\nCigarettes\nPooja', 'white'),
    ]
    for x, y, w, h, color, label, text_color in store_zones:
        rect = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01", facecolor=color, edgecolor=border, linewidth=2, alpha=0.9)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, label, ha='center', va='center', color=text_color, fontsize=8, fontweight='bold', wrap=True)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.set_title('Recommended Store Layout', color=subtext, fontsize=13, pad=20)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()