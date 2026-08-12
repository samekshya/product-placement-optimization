"""
The case study store -- Product Placement Optimisation dashboard.

Runs entirely from small precomputed files in dashboard/artifacts/ (built by
precompute_artifacts.py). No dependency on the confidential 114 MB CSV and no
Apriori at launch, so a marker can run it instantly from a fresh clone:

    pip install -r requirements.txt
    python dashboard/precompute_artifacts.py   # only if rebuilding artifacts
    streamlit run dashboard/app.py
"""

import json
import os
import textwrap
from itertools import combinations

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# PATHS (relative -- works from any clone)
# ============================================================

HERE = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS = os.path.join(HERE, "artifacts")

st.set_page_config(
    page_title="The case study store",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# DESIGN SYSTEM -- one palette, used everywhere
# ============================================================
# Brand: indigo primary, teal accent, amber highlight. Green/red only for deltas.

PRIMARY = "#1E2A4A"    # indigo (headers / primary chart series)
ACCENT = "#0EA5A4"     # teal (accents, secondary series)
HIGHLIGHT = "#F59E0B"  # amber (callouts)
POSITIVE = "#16A34A"   # green delta
NEGATIVE = "#DC2626"    # red delta

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Owner"


def get_theme(dark):
    """Accessible (WCAG AA) light + dark palettes."""
    if dark:
        return {
            "bg": "#0B1120",
            "card": "#131C31",
            "border": "#1F2A44",
            "text": "#E2E8F0",
            "subtext": "#94A3B8",
            "grid": "#1F2A44",
            "header": "#E2E8F0",
            "header2": "#7C9CD6",   # lighter indigo so it reads on dark
            "shadow": "0 1px 3px rgba(0,0,0,0.45)",
            "plot_template": "plotly_dark",
        }
    return {
        "bg": "#F1F5F9",
        "card": "#FFFFFF",
        "border": "#E2E8F0",
        "text": "#0F172A",
        "subtext": "#475569",
        "grid": "#E2E8F0",
        "header": PRIMARY,
        "header2": PRIMARY,
        "shadow": "0 1px 3px rgba(15,23,42,0.08)",
        "plot_template": "plotly_white",
    }


T = get_theme(st.session_state.dark_mode)

# ------------------------------------------------------------
# Single CSS block for the whole app
# ------------------------------------------------------------
st.markdown(
    f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"], [data-testid="stMarkdownContainer"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background-color: {T['bg']}; color: {T['text']}; }}
    [data-testid="stSidebar"] {{ background-color: {T['card']}; border-right: 1px solid {T['border']}; }}
    [data-testid="stSidebar"] label {{ color: {T['text']} !important; }}
    [data-testid="stSidebar"] p {{ color: {T['text']} !important; }}
    [data-testid="stSidebar"] span {{ color: {T['text']} !important; }}
    #MainMenu, footer {{ visibility: hidden; }}
    header[data-testid="stHeader"] {{ background-color: transparent; }}
    hr {{ border-color: {T['border']}; margin: 8px 0 16px 0; }}

    h1 {{ color: {T['header']}; font-weight: 800; letter-spacing: -0.02em; }}
    h2, h3, h4 {{ color: {T['header']}; font-weight: 700; letter-spacing: -0.01em; }}

    /* Native st.metric -> styled as a clean KPI card */
    [data-testid="stMetric"] {{
        background-color: {T['card']};
        border: 1px solid {T['border']};
        border-radius: 12px;
        padding: 16px 18px;
        box-shadow: {T['shadow']};
    }}
    [data-testid="stMetricLabel"] p {{
        font-size: 12px; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.06em; color: {T['subtext']};
    }}
    [data-testid="stMetricValue"] {{ font-size: 26px; font-weight: 800; color: {T['text']}; }}
    [data-testid="stMetricDelta"] {{ font-size: 12px; font-weight: 600; }}

    /* Native bordered container -> matches the metric cards */
    [data-testid="stVerticalBlockBorderWrapper"] {{ box-shadow: {T['shadow']}; }}
    div[data-testid="stVerticalBlockBorderWrapper"] > div {{ border-radius: 12px; }}

    /* Section header + caption */
    .sec-h {{ font-size: 18px; font-weight: 700; color: {T['header']}; margin: 8px 0 2px 0; }}
    .sec-s {{ color: {T['subtext']}; font-size: 13px; margin-bottom: 10px; }}
    .insight {{
        color: {T['subtext']}; font-size: 13px; line-height: 1.6;
        border-left: 3px solid {ACCENT}; padding: 4px 0 4px 12px; margin: 2px 0 18px 0;
    }}

    /* Reusable HTML card (always rendered flush-left via render_html) */
    .ui-card {{
        background-color: {T['card']}; border: 1px solid {T['border']};
        border-radius: 12px; padding: 16px 18px; margin-bottom: 10px;
        box-shadow: {T['shadow']};
    }}
    .ui-card .c-label {{ font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: {T['subtext']}; margin-bottom: 6px; }}
    .ui-card .c-title {{ font-size: 16px; font-weight: 700; color: {T['text']}; }}
    .ui-card .c-sub {{ font-size: 13px; color: {T['subtext']}; line-height: 1.6; }}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# REUSABLE UI HELPERS
# ============================================================


def render_html(html):
    """Render custom HTML safely.

    Streamlit markdown treats any line indented 4+ spaces as a code block, which
    breaks indented HTML and leaks bare </div> tags onto the page. We dedent and
    flatten to a single flush-left string so that never happens.
    """
    cleaned = " ".join(
        line.strip() for line in textwrap.dedent(html).splitlines() if line.strip()
    )
    st.markdown(cleaned, unsafe_allow_html=True)


def kpi_row(items):
    """Render a clean row of native st.metric cards.

    items: list of dicts with keys label, value, and optional delta / delta_color / help.
    """
    cols = st.columns(len(items))
    for col, it in zip(cols, items):
        with col:
            st.metric(
                label=it["label"],
                value=it["value"],
                delta=it.get("delta"),
                delta_color=it.get("delta_color", "normal"),
                help=it.get("help"),
            )


def section(title, sub=None):
    if title:
        st.markdown(f"<div class='sec-h'>{title}</div>", unsafe_allow_html=True)
    if sub:
        st.markdown(f"<div class='sec-s'>{sub}</div>", unsafe_allow_html=True)


def insight(text):
    st.markdown(f"<div class='insight'>{text}</div>", unsafe_allow_html=True)


def info_card(title, body, accent=None):
    """A bordered explanatory card. accent = optional left-border colour."""
    style = f"border-left:4px solid {accent};" if accent else ""
    render_html(
        f"<div class='ui-card' style='{style}'>"
        f"<div class='c-title' style='margin-bottom:6px;'>{title}</div>"
        f"<div class='c-sub'>{body}</div></div>"
    )


def style_fig(fig, height=380, legend=True):
    """Apply the ONE shared Plotly theme to every figure (reads current mode)."""
    fig.update_layout(
        template=T["plot_template"],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=T["text"], size=12),
        margin=dict(l=10, r=10, t=30, b=10),
        height=height,
        colorway=[PRIMARY if not st.session_state.dark_mode else "#7C9CD6", ACCENT, HIGHLIGHT, "#8B5CF6", "#EC4899"],
        showlegend=legend,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=T["subtext"])),
        hoverlabel=dict(font=dict(family="Inter, sans-serif")),
    )
    fig.update_xaxes(gridcolor=T["grid"], zerolinecolor=T["grid"], color=T["subtext"])
    fig.update_yaxes(gridcolor=T["grid"], zerolinecolor=T["grid"], color=T["subtext"])
    return fig


def show_chart(fig):
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# Brand colour for chart series that should read in the current theme
SERIES = PRIMARY if not st.session_state.dark_mode else "#7C9CD6"


# ============================================================
# DATA LOADING (artifacts only)
# ============================================================


@st.cache_data
def load_kpi():
    with open(os.path.join(ARTIFACTS, "kpi_summary.json")) as f:
        return json.load(f)


@st.cache_data
def load_cross_sell():
    with open(os.path.join(ARTIFACTS, "cross_sell_summary.json")) as f:
        return json.load(f)


@st.cache_data
def load_csv(name):
    return pd.read_csv(os.path.join(ARTIFACTS, name))


def get_recommendations(product_name, rules_df, top_n=5):
    """Top-N 'also bought' products for a given product, from product rules."""
    product_name = product_name.strip()
    recs = []
    for _, row in rules_df.iterrows():
        ants = [a.strip() for a in str(row["antecedents"]).split(",")]
        if product_name in ants:
            for p in str(row["consequents"]).split(","):
                recs.append(
                    {
                        "Product": p.strip(),
                        "Support": round(row["support"], 4),
                        "Confidence": round(row["confidence"], 2),
                        "Lift": round(row["lift"], 2),
                    }
                )
    if not recs:
        return None
    rec_df = pd.DataFrame(recs)
    rec_df = (
        rec_df.groupby("Product")
        .agg({"Support": "max", "Confidence": "max", "Lift": "max"})
        .reset_index()
    )
    return rec_df.sort_values("Lift", ascending=False).head(top_n)


KPI = load_kpi()
CROSS = load_cross_sell()
monthly_revenue = load_csv("monthly_revenue.csv")
category_dist = load_csv("category_distribution.csv")
basket_hist = load_csv("basket_value_hist.csv")
category_rules = load_csv("category_rules.csv")
product_rules = load_csv("product_rules.csv")
cooc_matrix = load_csv("cooccurrence_matrix.csv").set_index("Unnamed: 0")
cooc_matrix.index.name = "category"
top_pairs = load_csv("top_pairs.csv")
top_products = load_csv("top_products.csv")
cluster_assign = load_csv("cluster_assignments.csv")
abc_analysis = load_csv("abc_analysis.csv")
day_of_week = load_csv("day_of_week.csv")

DAILY_CUSTOMERS = KPI["total_transactions"] / KPI["data_days"]
AVG_BASKET = KPI["avg_basket_value"]


def crore(rs):
    return f"Rs {rs/10_000_000:.2f} Crore"


# ============================================================
# SEASONAL STOCK DATA (owner planning -- unchanged content)
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
# PLACEMENT ZONES (shared by Placement Zones page + planogram)
# ============================================================

ZONES = [
    {"name": "Zone 1 - Center", "label": "High Traffic Anchor", "color": "#1E2A4A",
     "categories": ["FOOD STAPLES", "COOKING OIL", "CLEANING SUPPLIES", "TEA AND SPICES", "HOUSEHOLD ITEMS"],
     "reason": "CLEANING SUPPLIES connects to 48 rules with lift above 5. FOOD STAPLES appears in 42.2% of all baskets. Central placement forces customers to pass other products.",
     "rect": (0.35, 0.30, 0.30, 0.40)},
    {"name": "Zone 2 - Entrance", "label": "Impulse Purchase", "color": "#0EA5A4",
     "categories": ["NOODLES", "SOFT DRINKS AND JUICES", "BISCUITS AND COOKIES", "CONFECTIONERY", "NAMKEEN AND SNACKS", "CANNED AND PACKAGED FOODS"],
     "reason": "High frequency impulse categories. Entrance placement captures customers before they focus on essentials, increasing unplanned purchases.",
     "rect": (0.05, 0.05, 0.90, 0.15)},
    {"name": "Zone 3 - Side Aisle", "label": "Destination", "color": "#8B5CF6",
     "categories": ["PERSONAL CARE", "BABY CARE", "STATIONERY"],
     "reason": "Customers seeking these products will find them regardless of placement. Side aisle keeps them out of the main traffic flow.",
     "rect": (0.05, 0.25, 0.25, 0.60)},
    {"name": "Zone 4 - Back Wall", "label": "Cold Storage", "color": "#F59E0B",
     "categories": ["DAIRY PRODUCTS", "FROZEN FOODS", "FRUITS AND VEGETABLES", "BAKERY"],
     "reason": "Physical constraint: refrigeration required. Back placement also draws customers through the store, increasing exposure to other products.",
     "rect": (0.05, 0.78, 0.90, 0.17)},
    {"name": "Zone 5 - Perimeter", "label": "Speciality", "color": "#EC4899",
     "categories": ["RICE", "ALCOHOLIC BEVERAGES", "CIGARETTE AND TOBACCO", "POOJA ITEMS", "BREAKFAST CEREALS", "ELECTRICAL SUPPLIES", "PARTY SUPPLIES"],
     "reason": "Low frequency or destination categories. Customers buying these seek them out specifically. Perimeter placement reduces main aisle congestion.",
     "rect": (0.70, 0.25, 0.25, 0.45)},
]

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(
        f"<div style='font-size:18px;font-weight:800;color:{T['header']};margin-bottom:2px;'>The case study store</div>"
        f"<div style='font-size:12px;color:{T['subtext']};margin-bottom:14px;'>Product Placement Optimisation</div>",
        unsafe_allow_html=True,
    )

    st.markdown(f"<div style='font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:{T['subtext']};margin-bottom:6px;'>View Mode</div>", unsafe_allow_html=True)
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

    if st.session_state.view_mode == "Owner":
        st.markdown(f"<div style='font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:{ACCENT};margin-bottom:6px;'>Store Owner Tools</div>", unsafe_allow_html=True)
        page = st.radio("nav", ["Shelf Planner", "Monthly Stock Plan", "Store Performance"], label_visibility="collapsed")
    else:
        st.markdown(f"<div style='font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:{ACCENT};margin-bottom:6px;'>Technical Analysis</div>", unsafe_allow_html=True)
        page = st.radio("nav", ["Project Overview", "Store Analytics", "Association Rules", "Clustering Results", "Model Validation", "Placement Zones", "Ethics & Data"], label_visibility="collapsed")

    st.markdown("---")

    theme_label = "Switch to Light Mode" if st.session_state.dark_mode else "Switch to Dark Mode"
    if st.button(theme_label, use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
    if st.button("Reset View", use_container_width=True):
        st.session_state.view_mode = "Owner"
        st.session_state.dark_mode = False
        st.rerun()

    st.markdown("---")
    st.caption(
        f"{KPI['total_transactions']:,} transactions · {KPI['n_categories']} categories · "
        f"10 months of real POS data.\n\nSamikshya Baniya · 230360 · ST6001CEM · Coventry University"
    )


# ============================================================
# CHART BUILDERS (one shared theme on every figure)
# ============================================================


def chart_revenue_trend():
    m = monthly_revenue.copy()
    m["rev_m"] = m["revenue"] / 1_000_000
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=m["month"], y=m["rev_m"], mode="lines+markers",
        line=dict(color=SERIES, width=3), marker=dict(size=8),
        hovertemplate="%{x}<br>Rs %{y:.1f}M<extra></extra>", name="Revenue",
    ))
    peak = m.loc[m["rev_m"].idxmax()]
    fig.add_annotation(
        x=peak["month"], y=peak["rev_m"],
        text=f"Dashain peak<br>Rs {peak['rev_m']:.1f}M", showarrow=True,
        arrowhead=2, arrowcolor=HIGHLIGHT, font=dict(color=HIGHLIGHT, size=11),
        ax=0, ay=-40,
    )
    fig.update_yaxes(title_text="Revenue (Rs Million)")
    return style_fig(fig, legend=False)


def chart_category_distribution():
    d = category_dist.head(15).sort_values("pct_of_baskets")
    fig = go.Figure(go.Bar(
        x=d["pct_of_baskets"], y=d["category"], orientation="h",
        marker_color=[HIGHLIGHT if c == "FOOD STAPLES" else SERIES for c in d["category"]],
        hovertemplate="%{y}<br>%{x:.1f}% of baskets<extra></extra>",
    ))
    fig.update_xaxes(title_text="% of baskets containing category")
    return style_fig(fig, height=440, legend=False)


def chart_basket_histogram():
    h = basket_hist.copy()
    centers = (h["bin_left"] + h["bin_right"]) / 2
    fig = go.Figure(go.Bar(
        x=centers, y=h["count"], marker_color=SERIES, width=(h["bin_right"] - h["bin_left"]) * 0.9,
        hovertemplate="Rs %{x:.0f}<br>%{y:,} baskets<extra></extra>",
    ))
    fig.add_vline(x=AVG_BASKET, line_dash="dash", line_color=HIGHLIGHT,
                  annotation_text=f"Mean Rs {AVG_BASKET:.0f}", annotation_font_color=HIGHLIGHT)
    fig.add_vline(x=KPI["median_basket_value"], line_dash="dash", line_color=ACCENT,
                  annotation_text=f"Median Rs {KPI['median_basket_value']:.0f}", annotation_font_color=ACCENT)
    fig.update_xaxes(title_text="Basket value (Rs, capped at 5000 for display)")
    fig.update_yaxes(title_text="Number of baskets")
    return style_fig(fig, legend=False)


def chart_abc_analysis():
    """Stacked bars: share of products vs share of revenue per ABC class."""
    a = abc_analysis
    n_all = len(a)
    rev_all = a["revenue"].sum()
    colors = {"A": SERIES, "B": ACCENT, "C": "#93D3D2"}
    fig = go.Figure()
    for cls in ["A", "B", "C"]:
        sub = a[a["abc_category"] == cls]
        pct_products = len(sub) / n_all * 100
        pct_revenue = sub["revenue"].sum() / rev_all * 100
        fig.add_trace(go.Bar(
            x=["Share of products", "Share of revenue"],
            y=[pct_products, pct_revenue],
            name=f"Class {cls} ({len(sub):,} products)",
            marker_color=colors[cls],
            text=[f"{pct_products:.1f}%", f"{pct_revenue:.1f}%"],
            textposition="inside",
            hovertemplate=f"Class {cls}<br>%{{x}}: %{{y:.1f}}%<extra></extra>",
        ))
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title_text="Percent of total")
    return style_fig(fig, height=400)


def chart_day_of_week():
    d = day_of_week.copy()
    d["rev_m"] = d["revenue"] / 1_000_000
    busiest = d.loc[d["revenue"].idxmax(), "day_name"]
    fig = go.Figure(go.Bar(
        x=d["day_name"], y=d["rev_m"],
        marker_color=[HIGHLIGHT if day == busiest else SERIES for day in d["day_name"]],
        customdata=d[["transaction_count", "avg_basket"]],
        hovertemplate="%{x}<br>Rs %{y:.1f}M revenue<br>%{customdata[0]:,} transactions"
                      "<br>Rs %{customdata[1]:,.0f} average basket<extra></extra>",
    ))
    fig.update_yaxes(title_text="Revenue (Rs Million)")
    return style_fig(fig, legend=False)


def chart_rules_scatter():
    r = category_rules.copy()
    fig = go.Figure(go.Scatter(
        x=r["support"], y=r["confidence"], mode="markers",
        marker=dict(size=9, color=r["lift"], colorscale="Tealgrn", showscale=True,
                    colorbar=dict(title="Lift"), line=dict(width=0)),
        text=[f"{a} &#8594; {c}<br>lift {l:.2f}" for a, c, l in zip(r["antecedents"], r["consequents"], r["lift"])],
        hovertemplate="%{text}<br>support %{x:.3f} | conf %{y:.2f}<extra></extra>",
    ))
    fig.update_xaxes(title_text="Support")
    fig.update_yaxes(title_text="Confidence")
    return style_fig(fig, height=460, legend=False)


def chart_cooccurrence_heatmap():
    fig = go.Figure(go.Heatmap(
        z=cooc_matrix.values, x=cooc_matrix.columns, y=cooc_matrix.index,
        colorscale="Tealgrn", hovertemplate="%{y} + %{x}<br>%{z:,} baskets<extra></extra>",
        colorbar=dict(title="Co-occur"),
    ))
    return style_fig(fig, height=620, legend=False)


def chart_category_network():
    """Category relationship network built from the strong rules (lift >= 3).

    No category-to-category rule reaches lift 3 on its own, so each strong
    multi-category rule is expanded into its category pairs and every pair
    keeps the strongest lift of any rule linking it (the standard rule-network
    rendering). Node size = baskets containing the category; node colour =
    co-occurrence cluster (k=3); edge thickness = lift.
    """
    strong = category_rules[category_rules["lift"] >= 3.0]
    edges = {}
    for _, row in strong.iterrows():
        cats = sorted(
            {a.strip() for a in str(row["antecedents"]).split(",")}
            | {c.strip() for c in str(row["consequents"]).split(",")}
        )
        for a, b in combinations(cats, 2):
            edges[(a, b)] = max(edges.get((a, b), 0.0), float(row["lift"]))

    G = nx.Graph()
    for (a, b), lift in edges.items():
        G.add_edge(a, b, weight=lift)
    pos = nx.spring_layout(G, seed=42, k=1.1)

    baskets = dict(zip(category_dist["category"], category_dist["baskets"]))
    clusters = dict(zip(cluster_assign["category"], cluster_assign["cooccurrence_cluster"]))
    cluster_colors = {0: ACCENT, 1: SERIES, 2: HIGHLIGHT}
    max_baskets = max(baskets.get(n, 1) for n in G.nodes)
    min_lift = min(edges.values())
    lift_span = max(max(edges.values()) - min_lift, 1e-9)

    fig = go.Figure()
    mid_x, mid_y, mid_text = [], [], []
    for (a, b), lift in edges.items():
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1], mode="lines",
            line=dict(width=1 + 5 * (lift - min_lift) / lift_span, color=T["grid"]),
            hoverinfo="skip", showlegend=False,
        ))
        mid_x.append((x0 + x1) / 2)
        mid_y.append((y0 + y1) / 2)
        mid_text.append(f"{a} + {b}<br>strongest rule lift {lift:.2f}")
    fig.add_trace(go.Scatter(
        x=mid_x, y=mid_y, mode="markers", text=mid_text,
        marker=dict(size=12, color="rgba(0,0,0,0)"),
        hovertemplate="%{text}<extra></extra>", showlegend=False,
    ))

    for cid in sorted({clusters.get(n, 0) for n in G.nodes}):
        node_list = [n for n in G.nodes if clusters.get(n, 0) == cid]
        fig.add_trace(go.Scatter(
            x=[pos[n][0] for n in node_list],
            y=[pos[n][1] for n in node_list],
            mode="markers+text",
            text=["<br>".join(textwrap.wrap(n, 16)) for n in node_list],
            textposition="top center",
            textfont=dict(size=10, color=T["text"]),
            marker=dict(
                size=[14 + 30 * (baskets.get(n, 0) / max_baskets) ** 0.5 for n in node_list],
                color=cluster_colors.get(cid, ACCENT),
                line=dict(width=2, color=T["card"]),
            ),
            name=f"Cluster {cid + 1}",
            customdata=[[baskets.get(n, 0), cid + 1] for n in node_list],
            hovertemplate="%{text}<br>%{customdata[0]:,} baskets contain this category<br>Cluster %{customdata[1]}<extra></extra>",
        ))

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return style_fig(fig, height=560)


def chart_recommendations(recs):
    fig = go.Figure(go.Bar(
        x=recs["Lift"], y=recs["Product"], orientation="h", marker_color=ACCENT,
        hovertemplate="%{y}<br>lift %{x:.2f}<extra></extra>",
    ))
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_xaxes(title_text="Lift (relationship strength)")
    return style_fig(fig, height=300, legend=False)


def chart_planogram(highlight=None):
    fig = go.Figure()
    for z in ZONES:
        x, y, w, h = z["rect"]
        is_hl = highlight == z["name"]
        fig.add_shape(type="rect", x0=x, y0=y, x1=x + w, y1=y + h,
                      line=dict(color="white", width=2),
                      fillcolor=z["color"], opacity=1.0 if is_hl else 0.55,
                      layer="below")
        fig.add_trace(go.Scatter(
            x=[x + w / 2], y=[y + h / 2], mode="text",
            text=[f"<b>{z['name'].split(' - ')[0]}</b>"], textfont=dict(color="white", size=12),
            hovertext=[f"<b>{z['name']}</b> ({z['label']})<br>" + "<br>".join(z["categories"])],
            hoverinfo="text", showlegend=False,
        ))
    fig.update_xaxes(visible=False, range=[0, 1])
    fig.update_yaxes(visible=False, range=[0, 1], scaleanchor="x")
    fig.update_layout(annotations=[dict(
        x=0.5, y=1.04, xref="paper", yref="paper", showarrow=False,
        text="Hover a zone to see its categories", font=dict(color=T["subtext"], size=11))])
    return style_fig(fig, height=460, legend=False)


# ============================================================
# OWNER MODE - SHELF PLANNER
# ============================================================

if st.session_state.view_mode == "Owner" and page == "Shelf Planner":
    st.title("Shelf Planner")
    section(None, "Type any product to find out what to place next to it on the shelf.")
    st.markdown("---")

    all_products = sorted(top_products["product"].tolist())
    default_idx = all_products.index("Sugar") if "Sugar" in all_products else 0
    selected = st.selectbox("Select a product", all_products, index=default_idx)

    if selected:
        recs = get_recommendations(selected, product_rules)
        if recs is None:
            st.warning(f"No shelf recommendations found for {selected}. Try a different product.")
        else:
            top_rec = recs.iloc[0]
            render_html(
                f"<div class='ui-card' style='border-left:4px solid {ACCENT};'>"
                f"<div class='c-label'>Shelf Action</div>"
                f"<div style='font-size:22px;font-weight:700;color:{T['text']};margin:2px 0 6px 0;'>"
                f"Place <span style='color:{ACCENT};'>{selected}</span> next to <span style='color:{ACCENT};'>{top_rec['Product']}</span></div>"
                f"<div class='c-sub'>Customers who buy {selected} also buy {top_rec['Product']} "
                f"{int(top_rec['Confidence']*100)}% of the time -- {top_rec['Lift']}x stronger than random chance.</div></div>"
            )

            section(f"Top products to place near {selected}")
            show_chart(chart_recommendations(recs))
            insight(f"Lift above 3 is a strong pairing. {selected} pairs most strongly with {top_rec['Product']} (lift {top_rec['Lift']}).")
            st.dataframe(recs.reset_index(drop=True), use_container_width=True)

    st.markdown("---")
    section("Top shelf pairs in the store", "Strongest product pairs from 218,037 real shopping trips. Put these side by side.")
    for _, row in top_pairs.head(8).iterrows():
        render_html(
            f"<div class='ui-card' style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<div class='c-title'><span style='color:{ACCENT};'>{row['product_a']}</span> + "
            f"<span style='color:{ACCENT};'>{row['product_b']}</span></div>"
            f"<div class='c-sub'>{int(row['cooccurrences']):,} times bought together</div></div>"
        )

# ============================================================
# OWNER MODE - MONTHLY STOCK PLAN
# ============================================================

elif st.session_state.view_mode == "Owner" and page == "Monthly Stock Plan":
    import datetime
    current_month = datetime.datetime.now().strftime("%B")

    st.title("Monthly Stock Plan")
    section(None, "Stock recommendations based on 10 months of real sales data from the case study store.")
    st.markdown("---")

    month_data = SEASONAL_STOCK.get(current_month, SEASONAL_STOCK["June"])
    render_html(
        f"<div class='ui-card' style='border-left:4px solid {HIGHLIGHT};'>"
        f"<div class='c-label'>This Month</div>"
        f"<div style='font-size:26px;font-weight:800;color:{T['text']};'>{current_month} "
        f"<span style='color:{HIGHLIGHT};font-size:15px;'>{month_data['season']}</span></div>"
        f"<div class='c-sub' style='margin-top:6px;'>{month_data['tip']}</div></div>"
    )

    col1, col2 = st.columns(2)
    with col1:
        section("Stock Up Now")
        for cat in month_data["stock_up"]:
            render_html(
                f"<div class='ui-card' style='border-left:4px solid {ACCENT};padding:12px 16px;'>"
                f"<span style='color:{ACCENT};font-size:13px;font-weight:700;'>+ {cat}</span></div>"
            )
    with col2:
        section("Normal Stock")
        if month_data["reduce"]:
            for cat in month_data["reduce"]:
                render_html(
                    f"<div class='ui-card' style='padding:12px 16px;'>"
                    f"<span style='color:{T['subtext']};font-size:13px;'>= {cat}</span></div>"
                )
        else:
            st.caption("All categories at normal stock levels this month.")

    st.markdown("---")
    section("Plan Ahead")
    selected_month = st.selectbox("Select a month to plan for", list(SEASONAL_STOCK.keys()))
    plan = SEASONAL_STOCK[selected_month]
    stock_list = "".join([f"<div style='color:{T['text']};font-size:14px;margin-bottom:4px;'>+ {cat}</div>" for cat in plan["stock_up"]])
    render_html(
        f"<div class='ui-card'>"
        f"<div style='font-size:18px;font-weight:700;color:{T['text']};margin-bottom:6px;'>{selected_month} "
        f"<span style='color:{HIGHLIGHT};font-size:14px;'>{plan['season']}</span></div>"
        f"<div class='c-sub' style='margin-bottom:12px;'>{plan['tip']}</div>"
        f"<div class='c-label' style='color:{ACCENT};'>Stock Up</div>{stock_list}</div>"
    )
    info_card(
        "Rule that never changes",
        "FOOD STAPLES, COOKING OIL and RICE are top 3 every single month without exception. "
        "Never let these run out of stock regardless of season.",
    )

# ============================================================
# OWNER MODE - STORE PERFORMANCE
# ============================================================

elif st.session_state.view_mode == "Owner" and page == "Store Performance":
    st.title("Store Performance")
    section(None, "Based on 10 months of real sales data from the case study store, Pokhara.")
    st.markdown("---")

    kpi_row([
        {"label": "Avg Basket Value", "value": f"Rs {AVG_BASKET:,.2f}"},
        {"label": "Transactions", "value": f"{KPI['total_transactions']:,}"},
        {"label": "Total Revenue", "value": crore(KPI["total_revenue"])},
        {"label": "Top Category", "value": KPI["top_category"].title()},
    ])
    st.markdown("<br>", unsafe_allow_html=True)
    kpi_row([
        {"label": "Daily Revenue", "value": f"Rs {KPI['daily_revenue']:,.0f}"},
        {"label": "Daily Customers", "value": f"{KPI['daily_customers']:,}"},
        {"label": "Median Basket", "value": f"Rs {KPI['median_basket_value']:,.0f}"},
    ])

    st.markdown("---")
    section("Monthly Revenue", "Ten months of revenue. Dashain (Sep 2025) is the peak.")
    show_chart(chart_revenue_trend())
    insight("September 2025 (Dashain) is the strongest month at Rs 23.3M. Stock festival categories 3 weeks early.")

    col_a, col_b = st.columns(2)
    with col_a:
        section("What Sells Most", "Share of baskets each category appears in.")
        show_chart(chart_category_distribution())
        insight("FOOD STAPLES appears in 42.2% of baskets -- the anchor category.")
    with col_b:
        section("Basket Value Distribution", "How much customers spend per trip.")
        show_chart(chart_basket_histogram())
        insight(f"Mean Rs {AVG_BASKET:.0f} but median only Rs {KPI['median_basket_value']:.0f} -- lifting small baskets is the opportunity.")

    st.markdown("---")
    section("How Much Can You Earn from Rearranging Shelves?", "Drag the slider to see projected extra revenue.")
    uplift = st.slider("Basket-value uplift", 2, 8, 5, 1, format="%d%%")
    extra_daily = AVG_BASKET * (uplift / 100) * DAILY_CUSTOMERS
    extra_annual = extra_daily * 365
    kpi_row([
        {"label": "New Avg Basket", "value": f"Rs {AVG_BASKET*(1+uplift/100):,.2f}", "delta": f"{uplift}%"},
        {"label": "Extra per Day", "value": f"Rs {extra_daily:,.0f}"},
        {"label": "Extra per Year", "value": crore(extra_annual)},
    ])
    st.caption(
        f"PROJECTION, not a measured result. A {uplift}% uplift is a retail-industry benchmark for "
        "placement optimisation, not an outcome of a live experiment in this store."
    )
    insight("First move: place Rato Dal next to Kalo Dal -- bought together 3,989 times. Measure for 4 weeks, then expand.")

# ============================================================
# EXAMINER MODE - PROJECT OVERVIEW
# ============================================================

elif st.session_state.view_mode == "Examiner" and page == "Project Overview":
    st.title("Project Overview")
    section(None, "Data Analytics and Machine Learning Based Product Placement Optimisation to Increase Sales in a Nepali Grocery Retail Store")
    st.markdown("---")

    kpi_row([
        {"label": "Transactions", "value": f"{KPI['total_transactions']:,}"},
        {"label": "Categories", "value": str(KPI["n_categories"])},
        {"label": "Products", "value": "5,681"},
        {"label": "Total Revenue", "value": crore(KPI["total_revenue"])},
    ])
    st.markdown("<br>", unsafe_allow_html=True)
    kpi_row([
        {"label": "MBA Rules", "value": f"{KPI['n_category_rules']:,}"},
        {"label": "Max Lift (Category)", "value": str(KPI["max_lift_category"])},
        {"label": "Max Lift (Product)", "value": str(KPI["max_lift_product"])},
        {"label": "Silhouette (k=3)", "value": str(KPI["cooccurrence_silhouette_k3"])},
    ])

    st.markdown("---")
    section("Analysis Pipeline")
    steps = [
        ("01", "Data Audit", "Examined 768,222 raw rows. Found 1,040 duplicates, 168,864 trailing spaces. Confirmed header=7 gives correct row count."),
        ("02", "Data Cleaning", "Removed duplicates and bad rows. Standardised 38 product groups into 25 clean categories. Final: 767,180 rows."),
        ("03", "EDA", "9 charts. FOOD STAPLES in 42.2% of baskets. Average basket Rs 1,000.81. Kalo Dal and Rato Dal co-occur 3,989 times. Large baskets (13.7% of trips) drive 52.1% of revenue."),
        ("04", "Transaction Encoding", "Converted to basket matrix: 218,037 rows x 25 columns. True/False per category per invoice."),
        ("05", "Market Basket Analysis", "Apriori and FP-Growth both found 1,228 rules. Max lift 6.81. 48 rules above lift 5."),
        ("06", "Clustering", "Frequency K-Means: silhouette 0.19. Co-occurrence K-Means: silhouette 0.554 at k=3. 189% improvement."),
        ("07", "Placement Simulation", "5 zones designed. Cross-sell capture doubles vs current layout. 5% uplift projects Rs 1.30 crore (projection)."),
        ("08", "Evaluation", "Algorithm comparison, 6 limitations, 7 future recommendations."),
        ("09", "ML Recommendation", "Product level MBA on top 100 products. 70/30 train test split. 28% hit rate on unseen data. Max lift 22.41."),
        ("10", "Demand Forecasting", "Prophet detects the Dashain peak automatically. Prophet MAE Rs 2.9M beats Linear Regression MAE Rs 3.4M."),
        ("11", "Basket Classifier", "Decision Tree (depth 5) predicts small/medium/large baskets at 61.3% accuracy vs 49.7% baseline. COOKING OIL and RICE are the strongest predictors of a large basket."),
    ]
    for num, title, desc in steps:
        render_html(
            f"<div class='ui-card' style='display:flex;gap:16px;align-items:flex-start;'>"
            f"<div style='color:{ACCENT};font-size:20px;font-weight:800;min-width:32px;'>{num}</div>"
            f"<div><div class='c-title' style='margin-bottom:4px;'>{title}</div>"
            f"<div class='c-sub'>{desc}</div></div></div>"
        )

# ============================================================
# EXAMINER MODE - STORE ANALYTICS
# ============================================================

elif st.session_state.view_mode == "Examiner" and page == "Store Analytics":
    st.title("Store Analytics")
    section(None, "ABC stock priority and the weekly shopping rhythm, computed from all 218,037 transactions (notebook 03, Charts 10 and 11).")
    st.markdown("---")

    abc_a = abc_analysis[abc_analysis["abc_category"] == "A"]
    abc_c = abc_analysis[abc_analysis["abc_category"] == "C"]
    a_share = len(abc_a) / len(abc_analysis) * 100
    c_share = len(abc_c) / len(abc_analysis) * 100

    section(
        "ABC Analysis of Products",
        "Products ranked by revenue and split into Class A (first 70% of revenue), "
        "Class B (next 20%) and Class C (final 10%).",
    )
    show_chart(chart_abc_analysis())
    insight(
        f"Just {len(abc_a):,} Class A products ({a_share:.1f}% of the range) generate 70% of all revenue, "
        f"so daily stock checks on this small group protect most of the store's income, while the "
        f"{len(abc_c):,} Class C products ({c_share:.1f}% of the range) need only minimal attention."
    )

    st.markdown("---")

    dow = day_of_week
    busiest_day = dow.loc[dow["revenue"].idxmax()]
    biggest_basket_day = dow.loc[dow["avg_basket"].idxmax()]
    quietest_day = dow.loc[dow["revenue"].idxmin()]

    section(
        "Day of Week Revenue",
        "Total revenue per day of the week (Nepali week: Sunday to Friday working days, Saturday holiday). "
        "Hover for transaction counts and average basket values.",
    )
    show_chart(chart_day_of_week())
    insight(
        f"{busiest_day['day_name']} is the busiest day (Rs {busiest_day['revenue']/1e6:.1f}M), "
        f"{biggest_basket_day['day_name']} shoppers buy the largest baskets (Rs {biggest_basket_day['avg_basket']:,.0f} average), "
        f"and {quietest_day['day_name']}, the weekly holiday, is the quietest, so staffing belongs on "
        f"{busiest_day['day_name']} and footfall promotions on {quietest_day['day_name']}."
    )

# ============================================================
# EXAMINER MODE - ASSOCIATION RULES
# ============================================================

elif st.session_state.view_mode == "Examiner" and page == "Association Rules":
    st.title("Association Rules")
    section(None, f"{KPI['n_category_rules']:,} rules from {KPI['total_transactions']:,} baskets. Apriori and FP-Growth produced identical results, validating the findings.")
    st.markdown("---")

    kpi_row([
        {"label": "Total Rules", "value": f"{KPI['n_category_rules']:,}"},
        {"label": "Rules Lift > 5", "value": str(KPI["rules_lift_above_5"])},
        {"label": "Max Lift (Cat)", "value": str(KPI["max_lift_category"])},
        {"label": "Max Lift (Product)", "value": str(KPI["max_lift_product"])},
    ])

    st.markdown("---")
    section("Filter Rules")
    cf1, cf2 = st.columns(2)
    min_lift = cf1.slider("Minimum Lift", 1.0, 7.0, 3.0, 0.1)
    min_conf = cf2.slider("Minimum Confidence", 0.0, 1.0, 0.1, 0.05)
    filtered = category_rules[(category_rules["lift"] >= min_lift) & (category_rules["confidence"] >= min_conf)].head(30)
    if len(filtered) > 0:
        display = filtered[["antecedents", "consequents", "support", "confidence", "lift"]].copy()
        display.columns = ["If customer buys", "They also buy", "Support", "Confidence", "Lift"]
        st.dataframe(display.reset_index(drop=True), use_container_width=True)
        st.caption(f"{len(filtered)} rules shown. Support, Confidence and Lift displayed together.")
    else:
        st.info("No rules at this filter level. Lower the minimum lift.")

    col_a, col_b = st.columns(2)
    with col_a:
        section("Rules Scatter", "Support vs confidence, coloured by lift.")
        show_chart(chart_rules_scatter())
        insight("Top-right, dark points = common, confident, high-lift rules -- the safest placement bets.")
    with col_b:
        section("Category Co-occurrence", "Times each pair appears in the same basket.")
        show_chart(chart_cooccurrence_heatmap())
        insight("FOOD STAPLES and CANNED AND PACKAGED FOODS co-occur ~31,000 times.")

    st.markdown("---")
    section(
        "Category Relationship Network",
        "Each node is a category, sized by how many baskets contain it and coloured by its k=3 cluster. "
        "An edge links two categories that appear together in a rule with lift above 3; thicker = stronger lift.",
    )
    show_chart(chart_category_network())
    insight(
        "Only 12 of 25 categories carry all 360 strong rules, connected by 40 pairwise links. "
        "CLEANING SUPPLIES sits at the centre of the web, confirming its connector role from notebook 05. "
        "The other 13 categories have no strong-rule ties, so they are free to be placed by other criteria "
        "(refrigeration, destination shopping) without losing cross-sell opportunities."
    )

# ============================================================
# EXAMINER MODE - CLUSTERING RESULTS
# ============================================================

elif st.session_state.view_mode == "Examiner" and page == "Clustering Results":
    st.title("Clustering Results")
    section(None, "Comparison of frequency based vs co-occurrence based K-Means clustering.")
    st.markdown("---")

    kpi_row([
        {"label": "Frequency K-Means", "value": "0.19", "help": "Silhouette at k=5 -- weak"},
        {"label": "Co-occurrence K-Means", "value": str(KPI["cooccurrence_silhouette_k3"]), "help": "Silhouette at k=3 -- strong"},
        {"label": "Improvement", "value": "189%", "delta": "right question asked"},
    ])

    info_card(
        "Why co-occurrence is better",
        "Frequency clustering asks 'how often is this category bought?' FOOD STAPLES at 42.2% dominates and forms "
        "its own cluster just because of its size -- useless for placement. Co-occurrence clustering asks 'how often "
        "are these two categories bought together?' which directly answers which categories belong next to each other.",
    )

    section("Category Co-occurrence Heatmap", "The input to co-occurrence clustering.")
    show_chart(chart_cooccurrence_heatmap())

    section("Three Placement Clusters at k=3")
    cluster_colors = {0: ACCENT, 1: SERIES, 2: HIGHLIGHT}
    for cid in sorted(cluster_assign["cooccurrence_cluster"].unique()):
        cats = cluster_assign[cluster_assign["cooccurrence_cluster"] == cid]["category"].tolist()
        color = cluster_colors.get(cid, ACCENT)
        render_html(
            f"<div class='ui-card' style='border-left:4px solid {color};'>"
            f"<div style='color:{color};font-size:15px;font-weight:700;margin-bottom:8px;'>Cluster {cid+1} ({len(cats)} categories)</div>"
            f"<div class='c-sub' style='color:{T['text']};'>{', '.join(cats)}</div></div>"
        )

# ============================================================
# EXAMINER MODE - MODEL VALIDATION
# ============================================================

elif st.session_state.view_mode == "Examiner" and page == "Model Validation":
    st.title("Model Validation")
    section(None, "Product level ML recommendation system. Trained on top 100 most sold products with 70/30 train test split.")
    st.markdown("---")

    kpi_row([
        {"label": "Training Baskets", "value": "95,570", "help": "70% of baskets"},
        {"label": "Test Baskets", "value": "40,959", "help": "30% held out"},
        {"label": "Hit Rate", "value": "28%"},
        {"label": "vs Random", "value": "28x", "delta": "better than 1% baseline"},
    ])

    info_card(
        "Why 28% hit rate is good",
        "The model picks from 100 possible products. Random guessing would give 1% accuracy; the model gives 28%, "
        "which is 28x better. It was trained on 70% of baskets and tested on 40,959 baskets it had never seen, "
        "confirming it learned real patterns rather than memorising.",
    )

    section("Recommendation Explorer", "Pick a product to see its top-5 'also bought' products with lift.")
    all_products = sorted(top_products["product"].tolist())
    default_idx = all_products.index("Sugar") if "Sugar" in all_products else 0
    selected = st.selectbox("Select a product", all_products, index=default_idx)
    if selected:
        recs = get_recommendations(selected, product_rules)
        if recs is None:
            st.info(f"No rules found for {selected}.")
        else:
            show_chart(chart_recommendations(recs))
            st.dataframe(recs.reset_index(drop=True), use_container_width=True)

# ============================================================
# EXAMINER MODE - PLACEMENT ZONES
# ============================================================

elif st.session_state.view_mode == "Examiner" and page == "Placement Zones":
    st.title("Placement Zones")
    section(None, f"5 zones derived from MBA association rules and co-occurrence clustering (silhouette {KPI['cooccurrence_silhouette_k3']} at k=3).")
    st.markdown("---")

    section("Cross-Sell Before / After (RQ2)", f"Strong rules (lift >= {CROSS['lift_floor']:.0f}) whose category pairs become co-located.")
    kpi_row([
        {"label": "Current Layout", "value": f"{CROSS['current_rules_captured']} rules", "help": f"{CROSS['current_capture_pct']}% of strong support"},
        {"label": "Optimised Layout", "value": f"{CROSS['optimised_rules_captured']} rules", "delta": f"{CROSS['optimised_capture_pct']}% of strong support"},
        {"label": "Improvement", "value": f"+{CROSS['rules_captured_delta']} rules", "delta": f"{CROSS['optimised_rules_captured']/max(CROSS['current_rules_captured'],1):.1f}x more captured"},
    ])

    bfig = go.Figure(go.Bar(
        x=["Current layout", "Optimised layout"],
        y=[CROSS["current_rules_captured"], CROSS["optimised_rules_captured"]],
        marker_color=[T["subtext"], ACCENT],
        text=[CROSS["current_rules_captured"], CROSS["optimised_rules_captured"]],
        textposition="outside",
        hovertemplate="%{x}<br>%{y} strong rules co-located<extra></extra>",
    ))
    bfig.update_yaxes(title_text="Strong cross-sell rules co-located")
    show_chart(style_fig(bfig, height=320, legend=False))
    insight(
        f"Data-driven result: the optimised 5-zone layout co-locates {CROSS['optimised_rules_captured']} strong cross-sell "
        f"rules vs {CROSS['current_rules_captured']} in the current frequency-driven layout -- a {CROSS['rules_captured_delta']}-rule "
        f"gain ({CROSS['optimised_capture_pct']}% vs {CROSS['current_capture_pct']}% of strong-rule support captured). "
        "This is measured from the association rules; the rupee figure below is a separate projection."
    )

    st.markdown("---")
    kpi_row([
        {"label": "Zones Designed", "value": "5"},
        {"label": "Moderate Uplift (5%)", "value": crore(AVG_BASKET * 0.05 * DAILY_CUSTOMERS * 365)},
        {"label": "Basis", "value": "Projection", "help": "not a measured result"},
    ])
    st.caption("The rupee uplift is a PROJECTION based on a 3-8% retail benchmark, not a live-experiment result.")

    section("Store Layout", "The 5 zones. Hover a zone to see its categories.")
    zone_names = [z["name"] for z in ZONES]
    chosen = st.selectbox("Highlight a zone", ["(none)"] + zone_names)
    show_chart(chart_planogram(highlight=None if chosen == "(none)" else chosen))
    if chosen != "(none)":
        z = next(z for z in ZONES if z["name"] == chosen)
        render_html(
            f"<div class='ui-card' style='border-left:4px solid {z['color']};'>"
            f"<div style='color:{z['color']};font-size:15px;font-weight:700;'>{z['name']} -- {z['label']}</div>"
            f"<div class='c-sub' style='color:{T['text']};margin:8px 0;'>{', '.join(z['categories'])}</div>"
            f"<div class='c-sub'>{z['reason']}</div></div>"
        )

    section("All Zones")
    for z in ZONES:
        render_html(
            f"<div class='ui-card' style='border-left:4px solid {z['color']};'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>"
            f"<div style='color:{z['color']};font-size:15px;font-weight:700;'>{z['name']}</div>"
            f"<div style='color:{T['subtext']};font-size:12px;text-transform:uppercase;letter-spacing:0.06em;'>{z['label']}</div></div>"
            f"<div class='c-sub' style='color:{T['text']};margin-bottom:8px;'>{', '.join(z['categories'])}</div>"
            f"<div class='c-sub' style='border-top:1px solid {T['border']};padding-top:8px;'>{z['reason']}</div></div>"
        )

# ============================================================
# EXAMINER MODE - ETHICS & DATA
# ============================================================

elif st.session_state.view_mode == "Examiner" and page == "Ethics & Data":
    st.title("Ethics & Data")
    section(None, "Objective 5 -- responsible use of real store data.")
    st.markdown("---")

    kpi_row([
        {"label": "Data Source", "value": "Primary"},
        {"label": "Cash (anonymous)", "value": "98%"},
        {"label": "Personal Data", "value": "None"},
    ])

    info_card(
        "Data provenance &amp; consent",
        "This is <b>primary data</b> collected from the student's own family-run store "
        "(Pokhara), used <b>with the explicit permission of store management</b> for academic research "
        "only. It was <b>not provided by faculty</b>; the earlier methodology note describing it as faculty-provided "
        "was incorrect and is superseded by this statement.",
    )
    info_card(
        "Privacy &amp; anonymisation",
        "98% of transactions are cash (\"CASH A/C\") with no customer identity attached, so no individual can be "
        "re-identified. No names, phone numbers, addresses or loyalty IDs are stored or analysed. Only product-level "
        "basket contents and amounts are used. The raw Excel file and the 114 MB cleaned CSV are kept out of version "
        "control (gitignored); the dashboard ships only small aggregated artifacts.",
    )
    info_card(
        "Honest reporting",
        "All association, clustering and basket figures are measured from the data. The 3% / 5% / 8% revenue uplift is "
        "clearly labelled as a <b>projection</b> based on retail-industry benchmarks, not the result of a live in-store "
        "experiment. The cross-sell before/after on the Placement Zones page is a data-driven result computed from the "
        "association rules; only the rupee conversion is a projection.",
    )
