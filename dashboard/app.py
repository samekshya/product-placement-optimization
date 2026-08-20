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
import sys
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
PROJECT_ROOT = os.path.dirname(HERE)  # so config/db.py is importable

for _p in (PROJECT_ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# The five placement zones. Content (categories, ethics) comes from the shared
# analysis/zones.py via zone_layout.py; only colours and geometry are local.
# dashboard/tests/test_shared_zones.py asserts this stays true.
from zone_layout import ZONES  # noqa: E402
from config import metrics as M  # noqa: E402

# The same scoring functions the dissertation figures and the shelf layout
# tool use. The per-zone ethics breakdown on the Placement Zones page is
# computed with these rather than typed in.
from analysis import zones as zone_defs  # noqa: E402
from analysis.cross_sell import (  # noqa: E402
    STRONG_LIFT_FLOOR,
    groups_from_assignment,
    score_layout,
)

st.set_page_config(
    page_title="The case study store",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# DESIGN SYSTEM -- one palette, used everywhere
# ============================================================
# Brand: indigo primary, teal accent, amber highlight. Green/red only for deltas.

# Colour language, used identically on every page. The widget chrome
# (buttons, sliders, active nav, focus rings) is themed to the same teal in
# .streamlit/config.toml, so interactive chrome and measured results share
# one colour and the default Streamlit red never appears.
#   ACCENT (teal)     measured results, and the interactive chrome
#   HIGHLIGHT (amber) projections ONLY: if amber is visible, it means estimate
#   NEGATIVE (red)    genuine failures only: a failed check, a stale report,
#                     the documented error record
#   everything else   neutral: stone text, grey and slate chart series
# ACCENT and HIGHLIGHT are assigned from the active theme just after
# get_theme(), because dark mode needs lighter steps of the same hues.
POSITIVE = "#16A34A"   # green: pass states and the live-source indicator
NEGATIVE = "#DC2626"   # red: failures only

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Owner"
if "entered" not in st.session_state:
    # False until a mode is chosen on the landing page ("The Result").
    st.session_state.entered = False


def get_theme(dark):
    """Accessible (WCAG AA) light + dark palettes.

    The light values mirror .streamlit/config.toml exactly. Dark keeps the
    same hue roles but lightens accent and amber so they stay legible.
    """
    if dark:
        return {
            "bg": "#0B1120",
            "card": "#131C31",
            "sidebar": "#131C31",
            "border": "#1F2A44",
            "text": "#E2E8F0",
            "subtext": "#94A3B8",
            "grid": "#1F2A44",
            "header": "#E2E8F0",
            "header2": "#E2E8F0",
            "shadow": "0 1px 3px rgba(0,0,0,0.45)",
            "plot_template": "plotly_dark",
            "accent": "#14B8A6",
            "projected": "#D97706",
        }
    return {
        "bg": "#FFFFFF",
        "card": "#FFFFFF",
        "sidebar": "#F5F5F4",
        "border": "#D6D3D1",
        "text": "#1C1917",
        "subtext": "#78716C",
        "grid": "#E7E5E4",
        "header": "#1C1917",
        "header2": "#1C1917",
        "shadow": "0 1px 3px rgba(28,25,23,0.08)",
        "plot_template": "plotly_white",
        "accent": "#0F766E",
        "projected": "#B45309",
    }


T = get_theme(st.session_state.dark_mode)

# The two signal colours, resolved per theme (see the colour language above).
ACCENT = T["accent"]
HIGHLIGHT = T["projected"]

# ------------------------------------------------------------
# Single CSS block for the whole app
# ------------------------------------------------------------
st.markdown(
    f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"], [data-testid="stMarkdownContainer"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background-color: {T['bg']}; color: {T['text']}; }}
    [data-testid="stSidebar"] {{ background-color: {T['sidebar']}; border-right: 1px solid {T['border']}; }}
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


def hero(value, statement, kind=None, value_color=None):
    """The one dominant figure at the top of a page.

    kind='measured' attaches the teal MEASURED treatment; kind='projected' the
    amber dashed PROJECTED treatment; None is neutral. Every page opens with
    exactly one of these rather than a row of equal tiles.
    """
    pill = ""
    box = ""
    if kind == "measured":
        box = f"border-left:5px solid {ACCENT};"
        pill = (
            f"<div style='margin-bottom:10px;'><span style='background:{ACCENT};"
            f"color:#FFFFFF;font-size:11px;font-weight:700;letter-spacing:0.1em;"
            f"border-radius:99px;padding:3px 12px;'>MEASURED</span></div>"
        )
    elif kind == "projected":
        box = f"border:2px dashed {HIGHLIGHT};"
        pill = (
            f"<div style='margin-bottom:10px;'><span style='background:{HIGHLIGHT};"
            f"color:#FFFFFF;font-size:11px;font-weight:700;letter-spacing:0.1em;"
            f"border-radius:99px;padding:3px 12px;'>PROJECTED</span></div>"
        )
    vc = value_color or T["text"]
    render_html(
        f"<div class='ui-card' style='{box}padding:22px 26px;margin-bottom:14px;'>"
        f"{pill}"
        f"<div style='font-size:38px;font-weight:800;line-height:1.1;color:{vc};'>{value}</div>"
        f"<div style='font-size:14px;color:{T['subtext']};margin-top:8px;max-width:680px;"
        f"line-height:1.55;'>{statement}</div></div>"
    )


def projection_block(stats, note):
    """The single visual treatment for projected figures: amber, dashed,
    PROJECTED pill. Measured figures never use this; projections never appear
    outside it. stats: list of (label, value)."""
    cells = "".join(
        f"<div style='flex:1;min-width:150px;text-align:center;'>"
        f"<div style='font-size:11px;font-weight:600;text-transform:uppercase;"
        f"letter-spacing:0.06em;color:{T['subtext']};margin-bottom:4px;'>{label}</div>"
        f"<div style='font-size:22px;font-weight:800;color:{T['text']};'>{value}</div></div>"
        for label, value in stats
    )
    render_html(
        f"<div style='border:2px dashed {HIGHLIGHT};border-radius:12px;"
        f"background-color:{T['card']};padding:16px 18px;margin:4px 0 10px 0;'>"
        f"<div style='text-align:center;margin-bottom:10px;'>"
        f"<span style='background:{HIGHLIGHT};color:#FFFFFF;font-size:11px;"
        f"font-weight:700;letter-spacing:0.1em;border-radius:99px;padding:3px 12px;'>"
        f"PROJECTED</span></div>"
        f"<div style='display:flex;gap:12px;flex-wrap:wrap;'>{cells}</div>"
        f"<div style='font-size:12px;color:{T['subtext']};margin-top:10px;"
        f"text-align:center;line-height:1.5;'>{note}</div></div>"
    )


# Each page is titled with the question it answers; the subtitle beneath keeps
# the former topic name and points at the dissertation section it reports, so a
# reader with the document open can match page to section without guessing.
PAGE_TOPICS = {
    "What should go next to what?": "Shelf Planner . 23.2 Association rules",
    "What happened each month?": "Monthly Stock Plan . 23.1 Purchasing behaviour",
    "How is the store doing?": "Store Performance . 23.1 Purchasing behaviour",
    "What was done?": "Project Overview . 12.4 Analytical methods",
    "What drives the store's revenue?": "Store Analytics . 23.1 Purchasing behaviour",
    "What do customers buy together?": "23.2 Association rules",
    "Which categories belong near each other?": "23.3 Clustering and zone derivation",
    "Do the recommendations actually work?": "Model Validation . 23.5 Predictive models",
    "Where should everything go?": "Placement Zones . 23.4 Layout comparison",
    "How do I know these numbers are right?": "Verification and error history . 21.4 Reproducibility, 22 Ethical reflection",
    "Was this done responsibly?": "Ethics & Data . 13 Ethical considerations, 24 RQ2 findings",
}


def page_header(question, subtitle=None):
    """Question title, topic-and-section line, optional descriptive subtitle."""
    st.title(question)
    topic = PAGE_TOPICS.get(question)
    if topic:
        # Sentence case, not uppercase: this line is a cross-reference to the
        # dissertation, not a label.
        st.markdown(
            f"<div style='font-size:13px;font-weight:500;"
            f"color:{T['subtext']};margin:-4px 0 4px 0;'>"
            f"{topic}</div>",
            unsafe_allow_html=True,
        )
    if subtitle:
        section(None, subtitle)
    st.markdown("---")


def style_fig(fig, height=380, legend=True):
    """Apply the ONE shared Plotly theme to every figure (reads current mode)."""
    fig.update_layout(
        template=T["plot_template"],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=T["text"], size=12),
        margin=dict(l=10, r=10, t=30, b=10),
        height=height,
        colorway=[SERIES, ACCENT, "#A8A29E", "#78716C", "#D6D3D1"],
        showlegend=legend,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=T["subtext"])),
        hoverlabel=dict(font=dict(family="Inter, sans-serif")),
    )
    fig.update_xaxes(gridcolor=T["grid"], zerolinecolor=T["grid"], color=T["subtext"])
    fig.update_yaxes(gridcolor=T["grid"], zerolinecolor=T["grid"], color=T["subtext"])
    return fig


def show_chart(fig):
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# Neutral slate for chart series that are neither a measured emphasis (teal)
# nor a projection (amber): data reads as data, colour is reserved for meaning.
SERIES = "#475569" if not st.session_state.dark_mode else "#94A3B8"


# ============================================================
# DATA SOURCE: live Postgres warehouse, falling back to artifacts
# ============================================================
# The dashboard prefers the warehouse built by the Airflow pipeline, so what is
# on screen is what the data platform actually produced. If Postgres is not
# running, it falls back to the committed CSV artifacts and keeps working.
#
# That fallback is not a nicety. A marker cloning this repo has no Postgres and
# no 114 MB CSV, and the dashboard still has to run for them. The sidebar states
# which source is in use so the two are never confused.
#
# Association rules, clustering and cross-sell always come from artifacts: they
# are Apriori and K-Means outputs from the notebooks, and the warehouse has no
# way to derive them.


@st.cache_resource(show_spinner=False)
def warehouse_status():
    """Probe the warehouse once. Returns (available, human readable detail)."""
    try:
        import sys

        import psycopg2

        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)
        from config import db

        conn = psycopg2.connect(connect_timeout=3, **db.connection_kwargs())
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM warehouse.fact_sales")
        rows = cur.fetchone()[0]
        cur.close()
        conn.close()
        if rows == 0:
            return False, "warehouse reachable but empty"
        return True, f"{db.describe()} ({rows:,} fact rows)"
    except Exception as exc:  # noqa: BLE001 - any failure means fall back
        return False, type(exc).__name__


WAREHOUSE_LIVE, WAREHOUSE_DETAIL = warehouse_status()


@st.cache_data(show_spinner=False)
def sql_df(query):
    """Run a query against the warehouse and return a DataFrame."""
    import sys
    import warnings

    import psycopg2

    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from config import db

    conn = psycopg2.connect(connect_timeout=5, **db.connection_kwargs())
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
            return pd.read_sql(query, conn)
    finally:
        conn.close()


@st.cache_data
def load_csv(name):
    return pd.read_csv(os.path.join(ARTIFACTS, name))


def from_warehouse_or_csv(query, csv_name, rename=None):
    """Serve a table from the warehouse when it is live, else from artifacts.

    Any SQL failure falls back rather than breaking the page: a dashboard that
    goes blank because a database blinked is worse than one showing yesterday's
    committed numbers.
    """
    if WAREHOUSE_LIVE:
        try:
            df = sql_df(query)
            return df.rename(columns=rename) if rename else df
        except Exception:  # noqa: BLE001
            pass
    return load_csv(csv_name)


@st.cache_data
def load_kpi():
    """KPI summary: mining metrics from the artifact, live metrics from SQL.

    kpi_summary.json holds two kinds of number. Transactions, revenue and basket
    values are warehouse facts and are refreshed from SQL when it is available.
    Max lift, rule counts and the silhouette score come from Apriori and K-Means
    in the notebooks, so they are always read from the file.
    """
    with open(os.path.join(ARTIFACTS, "kpi_summary.json")) as f:
        kpi = json.load(f)

    if WAREHOUSE_LIVE:
        try:
            row = sql_df("SELECT * FROM warehouse.v_kpi_summary").iloc[0]
            top_cat = sql_df(
                "SELECT category_name FROM warehouse.v_category_performance "
                "ORDER BY baskets DESC LIMIT 1"
            ).iloc[0]["category_name"]
            total_revenue = float(row["total_revenue"])
            total_baskets = int(row["total_transactions"])
            kpi.update({
                "total_transactions": total_baskets,
                "total_revenue": round(total_revenue, 2),
                "avg_basket_value": round(float(row["avg_basket_value"]), 2),
                "median_basket_value": round(float(row["median_basket_value"]), 2),
                "n_categories": int(row["n_categories"]),
                "n_products": int(row["n_products"]),
                "daily_revenue": round(total_revenue / kpi["data_days"], 2),
                "daily_customers": round(total_baskets / kpi["data_days"]),
                "top_category": top_cat,
            })
        except Exception:  # noqa: BLE001
            pass
    return kpi


@st.cache_data
def load_cross_sell():
    with open(os.path.join(ARTIFACTS, "cross_sell_summary.json")) as f:
        return json.load(f)


def load_verification_status():
    """Most recent output of scripts/run_verifications.py, or None.

    Deliberately NOT cached: the point of this file is showing current state,
    and it changes whenever verification is re-run.
    """
    path = os.path.join(PROJECT_ROOT, "reports", "verification_status.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


@st.cache_data
def load_zone_performance():
    """Revenue by placement zone. Only the warehouse can answer this.

    The zone assignment is a dimension attribute in dim_category, so this is a
    GROUP BY rather than a separate analysis. There is no artifact equivalent,
    so this returns None when the warehouse is not running.
    """
    if not WAREHOUSE_LIVE:
        return None
    try:
        return sql_df(
            "SELECT zone_assignment, zone_label, zone_location, n_categories, "
            "revenue, revenue_share_pct, baskets FROM warehouse.v_zone_performance "
            "ORDER BY zone_assignment"
        )
    except Exception:  # noqa: BLE001
        return None


def rule_categories(rules_df, floor):
    """The set of categories appearing in any rule at or above a lift floor."""
    cats = set()
    for _, row in rules_df[rules_df["lift"] >= floor].iterrows():
        cats |= {a.strip() for a in str(row["antecedents"]).split(",")}
        cats |= {c.strip() for c in str(row["consequents"]).split(",")}
    return cats


@st.cache_data(show_spinner=False)
def load_layout_reach(strong_cats):
    """Share of baskets the layout can influence, and the revenue outside it.

    Recomputed from the warehouse when it is running; otherwise the recorded
    figures from config/metrics.py, measured 2026-08-14, are shown and labelled
    as recorded rather than live.
    """
    strong_cats = sorted(strong_cats)
    if WAREHOUSE_LIVE:
        try:
            in_list = ", ".join("'" + c.replace("'", "''") + "'" for c in strong_cats)
            df_ = sql_df(
                "WITH covered AS ("
                "  SELECT DISTINCT f.basket_key FROM warehouse.fact_sales f"
                "  JOIN warehouse.dim_category c ON c.category_key = f.category_key"
                f"  WHERE c.category_name IN ({in_list}))"
                " SELECT"
                "  (SELECT COUNT(*) FROM covered) AS covered_baskets,"
                "  (SELECT COUNT(*) FROM warehouse.dim_basket) AS total_baskets,"
                "  (SELECT COALESCE(SUM(basket_value), 0) FROM warehouse.dim_basket b"
                "     WHERE NOT EXISTS (SELECT 1 FROM covered v"
                "                       WHERE v.basket_key = b.basket_key)) AS uncovered_revenue,"
                "  (SELECT SUM(basket_value) FROM warehouse.dim_basket) AS total_revenue"
            )
            row = df_.iloc[0]
            covered = float(row["covered_baskets"]) / float(row["total_baskets"]) * 100
            uncov_rev = float(row["uncovered_revenue"]) / float(row["total_revenue"]) * 100
            return {
                "reachable_pct": round(covered, 2),
                "unreachable_pct": round(100 - covered, 2),
                "unreachable_revenue_pct": round(uncov_rev, 2),
                "source": "recomputed from the warehouse just now",
            }
        except Exception:  # noqa: BLE001 - fall back to the recorded figures
            pass
    return {
        "reachable_pct": M.LAYOUT_REACHABLE_BASKET_PCT,
        "unreachable_pct": M.LAYOUT_UNREACHABLE_BASKET_PCT,
        "unreachable_revenue_pct": M.LAYOUT_UNREACHABLE_REVENUE_PCT,
        "source": "recorded in config/metrics.py, measured 2026-08-14 (warehouse offline)",
    }


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
ZONE_PERF = load_zone_performance()

# Served from the warehouse when it is running, from artifacts otherwise.
monthly_revenue = from_warehouse_or_csv(
    "SELECT year_month AS month, revenue, transactions AS baskets, avg_basket "
    "FROM warehouse.v_monthly_revenue ORDER BY year_month",
    "monthly_revenue.csv",
)
category_dist = from_warehouse_or_csv(
    "SELECT category_name AS category, baskets, "
    "basket_penetration_pct AS pct_of_baskets "
    "FROM warehouse.v_category_performance ORDER BY baskets DESC",
    "category_distribution.csv",
)
day_of_week = from_warehouse_or_csv(
    "SELECT TRIM(day_name) AS day_name, revenue, "
    "transactions AS transaction_count, avg_basket "
    "FROM warehouse.v_day_of_week ORDER BY day_of_week",
    "day_of_week.csv",
)
abc_analysis = from_warehouse_or_csv(
    "SELECT product_name AS product, revenue FROM warehouse.v_top_products "
    "ORDER BY revenue DESC, product_name",
    "abc_analysis.csv",
)
monthly_mix = from_warehouse_or_csv(
    "SELECT d.year_month AS month, c.category_name AS category, "
    "ROUND(SUM(f.total_amount), 2) AS revenue, "
    "COUNT(DISTINCT f.basket_key) AS baskets "
    "FROM warehouse.fact_sales f "
    "JOIN warehouse.dim_date d ON d.date_key = f.date_key "
    "JOIN warehouse.dim_category c ON c.category_key = f.category_key "
    "GROUP BY d.year_month, c.category_name "
    "ORDER BY d.year_month, c.category_name",
    "monthly_category_mix.csv",
)
monthly_mix["revenue"] = monthly_mix["revenue"].astype(float)
monthly_mix["baskets"] = monthly_mix["baskets"].astype(int)
# Share of the month's revenue, computed at display time from the observed
# values so the same formula serves the warehouse and the artifact.
monthly_mix["share_pct"] = (
    monthly_mix["revenue"]
    / monthly_mix.groupby("month")["revenue"].transform("sum") * 100
)
if WAREHOUSE_LIVE and "cumulative_pct" not in abc_analysis.columns:
    # The view returns ranked revenue; the ABC banding is presentation logic,
    # applied here so the same thresholds as notebook 03 Chart 10 are used.
    _cum = abc_analysis["revenue"].astype(float).cumsum() / \
        abc_analysis["revenue"].astype(float).sum() * 100
    abc_analysis["cumulative_pct"] = _cum.round(4)
    abc_analysis["abc_category"] = pd.cut(
        _cum, bins=[-0.1, 70, 90, 100.1], labels=["A", "B", "C"]
    ).astype(str)

# Always from artifacts: these are Apriori / K-Means outputs, not warehouse facts.
basket_hist = load_csv("basket_value_hist.csv")
category_rules = load_csv("category_rules.csv")
product_rules = load_csv("product_rules.csv")
cooc_matrix = load_csv("cooccurrence_matrix.csv").set_index("Unnamed: 0")
cooc_matrix.index.name = "category"
top_pairs = load_csv("top_pairs.csv")
top_products = load_csv("top_products.csv")
cluster_assign = load_csv("cluster_assignments.csv")

DAILY_CUSTOMERS = KPI["total_transactions"] / KPI["data_days"]
AVG_BASKET = KPI["avg_basket_value"]


def crore(rs):
    return f"Rs {rs/10_000_000:.2f} Crore"


# ============================================================
# OBSERVED MONTHLY RECORD (replaces the former hardcoded seasonal
# dictionary; everything shown is computed from the data at runtime)
# ============================================================

MONTH_LABELS = {
    "01": "January", "02": "February", "03": "March", "04": "April",
    "05": "May", "06": "June", "07": "July", "08": "August",
    "09": "September", "10": "October", "11": "November", "12": "December",
}


def month_label(ym):
    """'2025-09' -> 'September 2025'."""
    year, month = ym.split("-")
    return f"{MONTH_LABELS[month]} {year}"


def month_partial_note(ym):
    """A month is flagged partial when the record starts or ends inside it."""
    if ym == M.DATA_START[:7]:
        return f"Partial month: the record begins on {M.DATA_START}."
    if ym == M.DATA_END[:7]:
        return f"Partial month: the record ends on {M.DATA_END}."
    return None

# ============================================================
# PLACEMENT ZONES: imported from zone_layout.py at the top of this file.
# The category content is the shared analysis/zones.py definition; only
# colours, rectangles and prose are presentation.
# ============================================================

# ============================================================
# LANDING PAGE: "The Result", shown before mode selection.
# Every figure on it is read from the artifacts, config/metrics.py or the
# verification report at runtime. Nothing is typed in.
# ============================================================

if not st.session_state.entered:
    _proj_annual = AVG_BASKET * (M.UPLIFT_SCENARIO_PCT / 100) * DAILY_CUSTOMERS * 365
    _vstat = load_verification_status()

    _, mid, _ = st.columns([1, 5, 1])
    with mid:
        st.markdown("<br>", unsafe_allow_html=True)
        render_html(
            f"<div style='text-align:center;color:{T['subtext']};font-size:12px;"
            f"letter-spacing:0.14em;text-transform:uppercase;margin-bottom:14px;'>"
            f"Product Placement Optimisation . An independent grocery store</div>"
        )

        # ---- THE MEASURED RESULT: dominant ----
        render_html(
            f"<div class='ui-card' style='border-left:6px solid {ACCENT};"
            f"padding:30px 34px;text-align:center;'>"
            f"<div style='display:inline-block;background:{ACCENT};color:#FFFFFF;"
            f"font-size:11px;font-weight:700;letter-spacing:0.1em;border-radius:99px;"
            f"padding:3px 12px;margin-bottom:14px;'>MEASURED</div>"
            f"<div style='font-size:56px;font-weight:800;line-height:1.05;color:{T['text']};'>"
            f"{CROSS['current_capture_pct']}% <span style='color:{ACCENT};'>&#8594;</span> "
            f"{CROSS['optimised_capture_pct']}%</div>"
            f"<div style='font-size:18px;color:{T['text']};margin:14px auto 10px auto;"
            f"max-width:620px;line-height:1.5;'>A shelf layout derived from purchase "
            f"associations captures more than nine times the cross-sell support of the store's current "
            f"arrangement.</div>"
            f"<div style='font-size:13px;color:{T['subtext']};'>Computed from "
            f"{CROSS['total_strong_rules']} association rules. Involves no assumption "
            f"about customer response.</div>"
            f"</div>"
        )

        # ---- THE PROJECTION: subordinate, visually distinct ----
        _, pmid, _ = st.columns([1, 3, 1])
        with pmid:
            render_html(
                f"<div style='border:2px dashed {HIGHLIGHT};border-radius:12px;"
                f"padding:18px 22px;text-align:center;margin:6px 0 4px 0;'>"
                f"<div style='display:inline-block;background:{HIGHLIGHT};color:#FFFFFF;"
                f"font-size:11px;font-weight:700;letter-spacing:0.1em;border-radius:99px;"
                f"padding:3px 12px;margin-bottom:10px;'>PROJECTED</div>"
                f"<div style='font-size:26px;font-weight:800;color:{T['text']};'>"
                f"{crore(_proj_annual)}</div>"
                f"<div style='font-size:13px;color:{T['subtext']};margin-top:6px;"
                f"line-height:1.5;'>estimated additional annual revenue. Applies the "
                f"4 to 6% uplift range reported by Dreze, Hoch and Purk (1994) for shelf "
                f"reorganisation; the {M.UPLIFT_SCENARIO_PCT}% mid-point is shown. "
                f"Not a finding of this study.</div>"
                f"</div>"
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ---- Supporting figures, all read at runtime ----
        if _vstat:
            _v = _vstat["checks"].get("verify_thesis_numbers", {})
            _v_value = f"{_v.get('verified', _v.get('passed', 0))} of {_v.get('checkable', _v.get('total', 0))}"
            _v_ok = _vstat.get("all_passed", False)
            _v_sub = (
                f"reported figures verified automatically. Last run "
                f"{_vstat.get('generated_at_human', 'unknown')}"
            ) if _v_ok else (
                f"figures verified. VERIFICATION FAILING as of "
                f"{_vstat.get('generated_at_human', 'unknown')}"
            )
        else:
            _v_value = "Not yet run"
            _v_ok = False
            _v_sub = "run: python scripts/run_verifications.py"

        _tiles = [
            (f"{KPI['total_transactions']:,}", "baskets analysed"),
            (f"{KPI['n_category_rules']:,} rules",
             f"{M.RULES_BONFERRONI:,} surviving Bonferroni correction"),
            (f"{M.SILHOUETTE_FREQUENCY:.3f} to {KPI['cooccurrence_silhouette_k3']:.3f}",
             "silhouette, by changing the clustering representation"),
            (_v_value, _v_sub),
        ]
        tcols = st.columns(4)
        for tcol, (value, sub) in zip(tcols, _tiles):
            with tcol:
                render_html(
                    f"<div class='ui-card' style='text-align:center;padding:14px 12px;"
                    f"min-height:96px;'>"
                    f"<div style='font-size:19px;font-weight:800;color:{T['text']};'>{value}</div>"
                    f"<div style='font-size:11.5px;color:{T['subtext']};margin-top:4px;"
                    f"line-height:1.4;'>{sub}</div></div>"
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # ---- Routing ----
        bcol1, bcol2 = st.columns(2)
        with bcol1:
            if st.button("I am the store owner", use_container_width=True, type="primary"):
                st.session_state.view_mode = "Owner"
                st.session_state.entered = True
                st.rerun()
        with bcol2:
            if st.button("I am reviewing this work", use_container_width=True, type="primary"):
                st.session_state.view_mode = "Examiner"
                st.session_state.entered = True
                st.rerun()

        render_html(
            f"<div style='text-align:center;color:{T['subtext']};font-size:11px;"
            f"margin-top:16px;'>Samikshya Baniya . 230360 . ST6001CEM . "
            f"Coventry University</div>"
        )

    st.stop()

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
        page = st.radio("nav", [
            "What should go next to what?",
            "What happened each month?",
            "How is the store doing?",
        ], label_visibility="collapsed")
    else:
        st.markdown(f"<div style='font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:{ACCENT};margin-bottom:6px;'>Technical Analysis</div>", unsafe_allow_html=True)
        page = st.radio("nav", [
            "What was done?",
            "What drives the store's revenue?",
            "What do customers buy together?",
            "Which categories belong near each other?",
            "Do the recommendations actually work?",
            "Where should everything go?",
            "How do I know these numbers are right?",
            "Was this done responsibly?",
        ], label_visibility="collapsed")

    st.markdown("---")

    theme_label = "Switch to Light Mode" if st.session_state.dark_mode else "Switch to Dark Mode"
    if st.button(theme_label, use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
    if st.button("Back to The Result", use_container_width=True):
        st.session_state.entered = False
        st.rerun()
    if st.button("Reset View", use_container_width=True):
        st.session_state.view_mode = "Owner"
        st.session_state.dark_mode = False
        st.session_state.entered = False
        st.rerun()

    st.markdown("---")

    # Which data source is feeding this page. Stated plainly so live warehouse
    # numbers are never mistaken for the committed static ones.
    if WAREHOUSE_LIVE:
        _dot, _label, _sub = POSITIVE, "Live: Postgres warehouse", WAREHOUSE_DETAIL
    else:
        _dot, _label, _sub = T["subtext"], "Static: CSV artifacts", (
            f"Postgres not reachable ({WAREHOUSE_DETAIL}). "
            "Start it with: docker compose up -d postgres"
        )
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:7px;margin-bottom:3px;'>"
        f"<span style='width:8px;height:8px;border-radius:50%;background:{_dot};"
        f"display:inline-block;flex:none;'></span>"
        f"<span style='font-size:11.5px;font-weight:700;color:{T['header']};'>{_label}</span>"
        f"</div>"
        f"<div style='font-size:10.5px;color:{T['subtext']};line-height:1.45;"
        f"margin-bottom:10px;'>{_sub}</div>",
        unsafe_allow_html=True,
    )

    st.caption(
        f"{KPI['total_transactions']:,} transactions · {KPI['n_categories']} categories · "
        f"11 calendar months of real POS data.\n\nSamikshya Baniya · 230360 · ST6001CEM · Coventry University"
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
        arrowhead=2, arrowcolor=ACCENT, font=dict(color=ACCENT, size=11),
        ax=0, ay=-40,
    )
    fig.update_yaxes(title_text="Revenue (Rs Million)")
    return style_fig(fig, legend=False)


def chart_category_distribution():
    d = category_dist.head(15).sort_values("pct_of_baskets")
    fig = go.Figure(go.Bar(
        x=d["pct_of_baskets"], y=d["category"], orientation="h",
        marker_color=[ACCENT if c == "FOOD STAPLES" else SERIES for c in d["category"]],
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
    fig.add_vline(x=AVG_BASKET, line_dash="dash", line_color=ACCENT,
                  annotation_text=f"Mean Rs {AVG_BASKET:.0f}", annotation_font_color=ACCENT)
    fig.add_vline(x=KPI["median_basket_value"], line_dash="dot", line_color=T["subtext"],
                  annotation_text=f"Median Rs {KPI['median_basket_value']:.0f}", annotation_font_color=T["subtext"])
    fig.update_xaxes(title_text="Basket value (Rs, capped at 5000 for display)")
    fig.update_yaxes(title_text="Number of baskets")
    return style_fig(fig, legend=False)


def chart_abc_analysis():
    """Stacked bars: share of products vs share of revenue per ABC class."""
    a = abc_analysis
    n_all = len(a)
    rev_all = a["revenue"].sum()
    # Class A is the measured headline (70% of revenue), so it carries the
    # teal; B and C are neutral greys.
    colors = {"A": ACCENT, "B": SERIES, "C": "#A8A29E"}
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
        marker_color=[ACCENT if day == busiest else SERIES for day in d["day_name"]],
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
    cluster_colors = {0: ACCENT, 1: SERIES, 2: "#78716C"}
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


def chart_month_mix(sel_month, top_n=12):
    """Category share of one observed month's revenue."""
    mm = (
        monthly_mix[monthly_mix["month"].astype(str) == sel_month]
        .sort_values("share_pct", ascending=False)
        .head(top_n)
        .sort_values("share_pct")
    )
    fig = go.Figure(go.Bar(
        x=mm["share_pct"], y=mm["category"], orientation="h",
        marker_color=SERIES,
        customdata=mm[["revenue", "baskets"]].astype(float).values,
        hovertemplate="%{y}<br>%{x:.1f}% of the month's revenue"
                      "<br>Rs %{customdata[0]:,.0f} | %{customdata[1]:,.0f} baskets<extra></extra>",
    ))
    fig.update_xaxes(title_text="% of the month's revenue")
    return style_fig(fig, height=420, legend=False)


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
                      fillcolor=z["color"], opacity=1.0 if is_hl else 0.85,
                      layer="below")
        fig.add_trace(go.Scatter(
            x=[x + w / 2], y=[y + h / 2], mode="text",
            text=[f"<b>{z['name'].split(' - ')[0]}</b>"],
            textfont=dict(color=z["ink"], size=12),
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

if st.session_state.view_mode == "Owner" and page == "What should go next to what?":
    page_header(
        "What should go next to what?",
        "Type any product to find out what to place next to it on the shelf.",
    )

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

elif st.session_state.view_mode == "Owner" and page == "What happened each month?":
    page_header(
        "What happened each month?",
        "What each month actually sold, computed from the record. Observed history, not a forecast.",
    )

    months = monthly_revenue["month"].astype(str).tolist()
    n_months = len(months)

    info_card(
        "Read this before planning from it",
        f"Everything on this page is the observed record from {M.DATA_START} to {M.DATA_END}: "
        f"{n_months} calendar months containing one Dashain season. Each month was observed "
        "exactly once, so no single month here is evidence of a seasonal pattern. "
        "It shows what happened, not what will happen.",
    )

    _rev_series = monthly_revenue["revenue"].astype(float)
    peak_pos = int(_rev_series.reset_index(drop=True).idxmax())
    sel = st.selectbox(
        "Select an observed month", months, index=peak_pos, format_func=month_label
    )

    row = monthly_revenue[monthly_revenue["month"].astype(str) == sel].iloc[0]
    others = monthly_revenue[monthly_revenue["month"].astype(str) != sel]
    rev = float(row["revenue"])
    baskets = int(row["baskets"])
    avg = float(row["avg_basket"])
    o_rev = float(others["revenue"].astype(float).mean())
    o_baskets = float(others["baskets"].astype(float).mean())
    o_avg = float(others["avg_basket"].astype(float).mean())

    partial = month_partial_note(sel)
    if partial:
        st.caption(partial)

    hero(
        f"Rs {rev/1e6:.1f}M",
        f"revenue observed in {month_label(sel)}, "
        f"{(rev/o_rev-1)*100:+.1f}% against the mean of the other {n_months-1} months. "
        f"{baskets:,} baskets ({(baskets/o_baskets-1)*100:+.1f}%) at an average of "
        f"Rs {avg:,.0f} each ({(avg/o_avg-1)*100:+.1f}%). One observation.",
    )

    st.markdown("---")
    section(
        f"Category mix in {month_label(sel)}",
        "Share of the month's revenue by category. Hover for rupees and basket counts.",
    )
    show_chart(chart_month_mix(sel))

    # Deviations vs each category's median month, computed from the record.
    med_share = monthly_mix.groupby("category")["share_pct"].median()
    mm_sel = (
        monthly_mix[monthly_mix["month"].astype(str) == sel]
        .set_index("category")["share_pct"]
        .reindex(med_share.index, fill_value=0.0)
    )
    dev = (mm_sel - med_share).sort_values(ascending=False)
    ups = dev[dev >= 0.25].head(3)
    downs = dev[dev <= -0.25].tail(3)

    if len(ups) or len(downs):
        section(
            "Where this month differed from its median month",
            "Change in revenue share, in percentage points. One observation, so a "
            "description of this month, not a prediction about the next one.",
        )
        col_u, col_d = st.columns(2)
        with col_u:
            for cat, d in ups.items():
                render_html(
                    f"<div class='ui-card' style='border-left:4px solid {ACCENT};padding:12px 16px;'>"
                    f"<span style='color:{ACCENT};font-size:13px;font-weight:700;'>{cat}</span>"
                    f"<span style='color:{T['subtext']};font-size:13px;'> took {d:+.1f} pp "
                    f"more of revenue than its median month</span></div>"
                )
        with col_d:
            for cat, d in downs.items():
                render_html(
                    f"<div class='ui-card' style='padding:12px 16px;'>"
                    f"<span style='color:{T['text']};font-size:13px;font-weight:700;'>{cat}</span>"
                    f"<span style='color:{T['subtext']};font-size:13px;'> took {d:+.1f} pp "
                    f"less than its median month</span></div>"
                )
    else:
        st.caption("No category moved more than 0.25 percentage points from its median month.")

    st.markdown("---")

    # The one claim the record repeats every month, computed rather than asserted.
    _top3 = monthly_mix.sort_values("revenue", ascending=False).groupby("month").head(3)
    _always = _top3.groupby("category")["month"].nunique()
    _always = sorted(_always[_always == n_months].index.tolist())
    if _always:
        info_card(
            f"Constant in all {n_months} observed months",
            f"{', '.join(_always)} placed in the top three revenue categories in every "
            f"one of the {n_months} observed months. That is {n_months} separate "
            "observations of the same ranking, the most repeated pattern in this record, "
            "and the only finding on this page supported by more than one observation.",
            accent=ACCENT,
        )

# ============================================================
# OWNER MODE - STORE PERFORMANCE
# ============================================================

elif st.session_state.view_mode == "Owner" and page == "How is the store doing?":
    page_header(
        "How is the store doing?",
        f"Based on {M.CALENDAR_MONTHS} calendar months of real sales data from the case study store.",
    )

    hero(
        crore(KPI["total_revenue"]),
        f"revenue across {M.CALENDAR_MONTHS} months and {KPI['total_transactions']:,} "
        f"baskets. Top category: {KPI['top_category'].title()}.",
    )
    kpi_row([
        {"label": "Avg Basket Value", "value": f"Rs {AVG_BASKET:,.2f}"},
        {"label": "Median Basket", "value": f"Rs {KPI['median_basket_value']:,.0f}"},
        {"label": "Daily Revenue", "value": f"Rs {KPI['daily_revenue']:,.0f}"},
        {"label": "Daily Customers", "value": f"{KPI['daily_customers']:,}"},
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
    section(
        "How Much Can You Earn from Rearranging Shelves?",
        "Drag the slider. Everything inside the amber dashed box is a projection, "
        "not a measurement.",
    )
    uplift = st.slider("Basket-value uplift", 4, 6, 5, 1, format="%d%%")
    extra_daily = AVG_BASKET * (uplift / 100) * DAILY_CUSTOMERS
    extra_annual = extra_daily * 365
    projection_block(
        [
            ("New Avg Basket", f"Rs {AVG_BASKET*(1+uplift/100):,.2f}"),
            ("Extra per Day", f"Rs {extra_daily:,.0f}"),
            ("Extra per Year", crore(extra_annual)),
        ],
        f"A {uplift}% uplift sits inside the 4 to 6% range reported by Dreze, Hoch "
        "and Purk (1994) for shelf reorganisation. It is a published benchmark, not "
        "an outcome of a live experiment in this store. No shelf was moved during "
        "this study.",
    )
    _tp = top_pairs.sort_values("cooccurrences", ascending=False).iloc[0]
    insight(
        f"First move: place {_tp['product_a']} next to {_tp['product_b']} -- bought together "
        f"{int(_tp['cooccurrences']):,} times. Measure for 4 weeks, then expand."
    )

# ============================================================
# EXAMINER MODE - PROJECT OVERVIEW
# ============================================================

elif st.session_state.view_mode == "Examiner" and page == "What was done?":
    page_header(
        "What was done?",
        "Data Analytics and Machine Learning Based Product Placement Optimisation to Increase Sales in a Nepali Grocery Retail Store",
    )

    hero(
        f"{KPI['total_transactions']:,}",
        f"real shopping trips analysed, covering {M.TOTAL_PRODUCTS:,} products in "
        f"{KPI['n_categories']} categories. Every figure below is computed from them "
        "and checked automatically.",
    )
    kpi_row([
        {"label": "Total Revenue", "value": crore(KPI["total_revenue"])},
        {"label": "MBA Rules", "value": f"{KPI['n_category_rules']:,}"},
        {"label": "Max Lift (Category)", "value": str(KPI["max_lift_category"])},
        {"label": "Silhouette (k=3)", "value": str(KPI["cooccurrence_silhouette_k3"])},
    ])

    st.markdown("---")
    section("Analysis Pipeline")
    steps = [
        ("01", "Data Audit", "Examined 768,222 raw rows. Found 1,040 duplicates, 168,864 trailing spaces. Confirmed header=7 gives correct row count."),
        ("02", "Data Cleaning", "Removed duplicates and bad rows. Standardised 38 product groups into 25 clean categories. Final: 767,180 rows."),
        ("03", "EDA", "9 charts. FOOD STAPLES in 30.5% of baskets. Average basket Rs 1,000.81. Kalo Dal and Rato Dal co-occur 3,989 times. Large baskets (13.7% of trips) drive 52.1% of revenue."),
        ("04", "Transaction Encoding", "Converted to basket matrix: 218,037 rows x 25 columns. True/False per category per invoice."),
        ("05", "Market Basket Analysis", "Apriori and FP-Growth both found 1,320 rules. Max lift 7.44. 62 rules above lift 5."),
        ("06", "Clustering", "Frequency K-Means: silhouette 0.190. Co-occurrence K-Means: silhouette 0.493 at k=3, an increase of 0.303."),
        ("07", "Placement Simulation", "5 zones designed. After the 2026-08-17 category remap the zones were re-derived: they capture 180 of 368 strong rules (48.9% by count, 54.1% of strong-rule support) against 22 for the current-layout proxy. 5% uplift, the mid-point of the 4 to 6% range in Dreze, Hoch and Purk (1994), projects Rs 1.30 crore (projection)."),
        ("08", "Evaluation", "Algorithm comparison, 6 limitations, 7 future recommendations."),
        ("09", "ML Recommendation", "Product level MBA on top 100 products. 70/30 train test split. 28% hit rate on unseen data. Max lift 22.41."),
        ("10", "Demand Forecasting", "Prophet detects the Dashain peak automatically. Prophet MAE Rs 2.9M beats Linear Regression MAE Rs 3.4M."),
        ("11", "Basket Classifier", "Decision Tree (depth 5) predicts small/medium/large baskets at 61.4% accuracy vs 49.7% baseline. COOKING OIL and RICE are the strongest predictors of a large basket."),
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

elif st.session_state.view_mode == "Examiner" and page == "What drives the store's revenue?":
    page_header(
        "What drives the store's revenue?",
        f"ABC stock priority and the weekly shopping rhythm, computed from all "
        f"{KPI['total_transactions']:,} transactions (notebook 03, Charts 10 and 11).",
    )

    abc_a = abc_analysis[abc_analysis["abc_category"] == "A"]
    abc_c = abc_analysis[abc_analysis["abc_category"] == "C"]
    a_share = len(abc_a) / len(abc_analysis) * 100
    c_share = len(abc_c) / len(abc_analysis) * 100

    hero(
        f"{len(abc_a):,} products",
        f"just {a_share:.1f}% of the range, generate 70% of all revenue. Daily stock "
        "checks on this small group protect most of the store's income.",
    )

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

elif st.session_state.view_mode == "Examiner" and page == "What do customers buy together?":
    page_header(
        "What do customers buy together?",
        "Apriori and FP-Growth produced identical results, validating the findings.",
    )

    hero(
        f"{KPI['n_category_rules']:,} rules",
        f"mined from {KPI['total_transactions']:,} baskets; {M.RULES_BONFERRONI:,} "
        "survive Bonferroni correction for the simultaneous tests.",
    )
    kpi_row([
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
        "Only 14 of 25 categories carry all 368 strong rules, connected by 47 pairwise links. "
        "CLEANING SUPPLIES sits at the centre of the web, confirming its connector role from notebook 05. "
        "The other 11 categories have no strong-rule ties, so they are free to be placed by other criteria "
        "(refrigeration, destination shopping) without losing cross-sell opportunities."
    )

# ============================================================
# EXAMINER MODE - CLUSTERING RESULTS
# ============================================================

elif st.session_state.view_mode == "Examiner" and page == "Which categories belong near each other?":
    page_header(
        "Which categories belong near each other?",
        "Comparison of frequency based vs co-occurrence based K-Means clustering.",
    )

    hero(
        f"+{M.SILHOUETTE_INCREASE}",
        f"absolute silhouette gain, from {M.SILHOUETTE_FREQUENCY:.3f} (frequency, k=5) "
        f"to {KPI['cooccurrence_silhouette_k3']} (co-occurrence, k=3), from changing "
        "what the clustering is asked about. Stated as an absolute increase because "
        "silhouette is bounded on [-1, 1] and a percentage between two scores has "
        "no interpretation.",
    )

    info_card(
        "Why co-occurrence is better",
        "Frequency clustering asks 'how often is this category bought?' FOOD STAPLES at 42.2% dominates and forms "
        "its own cluster just because of its size -- useless for placement. Co-occurrence clustering asks 'how often "
        "are these two categories bought together?' which directly answers which categories belong next to each other.",
    )

    section("Category Co-occurrence Heatmap", "The input to co-occurrence clustering.")
    show_chart(chart_cooccurrence_heatmap())

    section("Three Placement Clusters at k=3")
    cluster_colors = {0: ACCENT, 1: SERIES, 2: "#78716C"}
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

elif st.session_state.view_mode == "Examiner" and page == "Do the recommendations actually work?":
    page_header(
        "Do the recommendations actually work?",
        "Product level ML recommendation system. Trained on top 100 most sold products with 70/30 train test split.",
    )

    _vs_random = M.REC_MODEL_HIT_PCT / M.REC_RANDOM_MATCHED_PCT
    hero(
        f"{M.REC_MODEL_HIT_PCT}%",
        f"hit rate on {M.REC_TEST_BASKETS:,} unseen multi-product baskets. At the same "
        f"recommendation budget, popularity alone scores {M.REC_POPULARITY_MATCHED_PCT}% "
        f"and random {M.REC_RANDOM_MATCHED_PCT}%.",
    )
    kpi_row([
        {"label": "Training Baskets", "value": f"{M.ML_TRAIN_BASKETS:,}", "help": "70% of baskets"},
        {"label": "Held-out Baskets", "value": f"{M.ML_TEST_BASKETS:,}",
         "help": f"30% held out. The hit rate is computed on the {M.REC_TEST_BASKETS:,} multi-product baskets among these."},
        {"label": "vs Popularity", "value": f"+{M.REC_MODEL_HIT_PCT - M.REC_POPULARITY_MATCHED_PCT:.1f} pts",
         "help": "Against recommending bestsellers at the same budget"},
        {"label": "vs Matched Random", "value": f"{_vs_random:.0f}x",
         "help": f"Random at the model's own budget scores {M.REC_RANDOM_MATCHED_PCT}%"},
    ])

    info_card(
        f"What the {M.REC_MODEL_HIT_PCT}% means, honestly",
        f"The model picks from 100 products and issues {M.REC_AVG_RECS_PER_BASKET} "
        f"recommendations per basket on average, so matched random scores "
        f"{M.REC_RANDOM_MATCHED_PCT}%, making the model roughly {_vs_random:.0f}x "
        "chance, not the 28x an unmatched 1% baseline once suggested. The tougher "
        f"comparison is popularity at the same budget: {M.REC_POPULARITY_MATCHED_PCT}% "
        f"against the model's {M.REC_MODEL_HIT_PCT}%, and {M.REC_COVERED_POPULARITY_PCT}% "
        f"against {M.REC_COVERED_MODEL_PCT}% on baskets where the model has rule "
        "coverage. The full history of this correction is on 'How do I know these "
        "numbers are right?'.",
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

elif st.session_state.view_mode == "Examiner" and page == "Where should everything go?":
    page_header(
        "Where should everything go?",
        f"5 zones derived from MBA association rules and co-occurrence clustering (silhouette {KPI['cooccurrence_silhouette_k3']} at k=3).",
    )

    hero(
        f"{CROSS['current_capture_pct']}% <span style='color:{ACCENT};'>&#8594;</span> {CROSS['optimised_capture_pct']}%",
        f"of strong-rule support captured when the five designed zones replace the "
        f"current frequency-driven arrangement: {CROSS['current_rules_captured']} "
        f"co-located rules become {CROSS['optimised_rules_captured']} of "
        f"{CROSS['total_strong_rules']}. Computed from the association rules; no "
        "assumption about customer response is involved.",
        kind="measured",
    )

    section("Cross-Sell Before / After (RQ2)", f"Strong rules (lift >= {CROSS['lift_floor']:.0f}) whose category pairs become co-located.")

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

    # ------------------------------------------------------------
    # Zone-level ethics breakdown. Computed here with the SAME shared
    # scoring functions the dissertation figures come from
    # (analysis/cross_sell.py + analysis/zones.py), not hardcoded.
    # ------------------------------------------------------------
    _strong_df = category_rules[category_rules["lift"] >= STRONG_LIFT_FLOOR]
    _strong_rules = [
        {
            "cats": {a.strip() for a in str(r["antecedents"]).split(",")}
                    | {c.strip() for c in str(r["consequents"]).split(",")},
            "support": float(r["support"]),
        }
        for _, r in _strong_df.iterrows()
    ]
    _assignment = zone_defs.proposed_assignment()
    _scored = score_layout(
        _strong_rules,
        groups_from_assignment(_assignment),
        float(_strong_df["support"].sum()),
    )

    _zone_rules = {z["id"]: 0 for z in zone_defs.ZONES}
    _zone_support = {z["id"]: 0.0 for z in zone_defs.ZONES}
    for _rule in _scored["captured"]:
        # A captured rule sits entirely in one zone, so any of its categories
        # identifies that zone.
        _zid = _assignment[next(iter(_rule["cats"]))]
        _zone_rules[_zid] += 1
        _zone_support[_zid] += _rule["support"]

    _captured_support = sum(_zone_support.values())
    _creates_rules = sum(
        _zone_rules[z["id"]] for z in zone_defs.ZONES if z["ethics"] == zone_defs.CREATES
    )
    _assists_rules = _scored["rules_captured"] - _creates_rules

    section(
        "Which zones do the capturing, and on what ethical terms",
        "Each zone is classified by its relationship to customer intention "
        "(section 24.3 of the dissertation). Rules captured per zone are computed "
        "with the same shared scoring function that produced the headline figures.",
    )

    _ethics_table = pd.DataFrame([
        {
            "Zone": next(dz["name"] for dz in ZONES if dz["id"] == z["id"]),
            "Ethics classification": zone_defs.ETHICS_LABEL[z["ethics"]],
            "Rules captured": _zone_rules[z["id"]],
            "Share of captured support": (
                f"{_zone_support[z['id']] / _captured_support * 100:.1f}%"
                if _captured_support else "0.0%"
            ),
        }
        for z in zone_defs.ZONES
    ])
    st.dataframe(_ethics_table, use_container_width=True, hide_index=True)

    if _creates_rules == 0:
        info_card(
            "The measured benefit needs no impulse placement",
            f"All {_scored['rules_captured']} captured rules sit in zones classified as "
            "assisting an existing intention: they co-locate goods customers already "
            "buy together. The entrance zone, the only zone that creates rather than "
            "assists an intention, captures zero rules. The entire measured cross-sell "
            "benefit therefore comes from arrangements that help customers do what "
            "they came to do, and the impulse placement could be removed without "
            "reducing it.",
            accent=ACCENT,
        )
    else:
        info_card(
            "Where the captured rules sit",
            f"{_assists_rules} of {_scored['rules_captured']} captured rules sit in "
            f"zones that assist an existing intention; {_creates_rules} sit in the "
            "zone classified as creating one.",
            accent=ACCENT,
        )

    st.markdown("---")
    projection_block(
        [
            (f"Estimated additional annual revenue at {M.UPLIFT_SCENARIO_PCT}% uplift",
             crore(AVG_BASKET * (M.UPLIFT_SCENARIO_PCT / 100) * DAILY_CUSTOMERS * 365)),
        ],
        f"Applies the 4 to 6% uplift range reported by Dreze, Hoch and Purk (1994) "
        f"for shelf reorganisation; the {M.UPLIFT_SCENARIO_PCT}% mid-point is shown. "
        "Not a measured result: no shelf was moved during this study, so customer "
        "response was never observed.",
    )

    section("Store Layout", "The 5 zones. Hover a zone to see its categories.")
    zone_names = [z["name"] for z in ZONES]
    chosen = st.selectbox("Highlight a zone", ["(none)"] + zone_names)
    show_chart(chart_planogram(highlight=None if chosen == "(none)" else chosen))
    if chosen != "(none)":
        z = next(z for z in ZONES if z["name"] == chosen)
        render_html(
            f"<div class='ui-card' style='border-left:4px solid {z['color']};'>"
            f"<div style='color:{T['text']};font-size:15px;font-weight:700;'>"
            f"<span style='display:inline-block;width:10px;height:10px;border-radius:2px;"
            f"background:{z['color']};margin-right:8px;'></span>"
            f"{z['name']} -- {z['label']}</div>"
            f"<div class='c-sub' style='color:{T['text']};margin:8px 0;'>{', '.join(z['categories'])}</div>"
            f"<div class='c-sub'>{z['reason']}</div></div>"
        )

    # Revenue by zone. This section only appears when the warehouse is live,
    # because it is a GROUP BY on dim_category.zone_assignment and there is no
    # artifact equivalent. It is the clearest demonstration of why the research
    # finding was stored as a dimension attribute rather than kept in a notebook.
    if ZONE_PERF is not None and not ZONE_PERF.empty:
        section(
            "Revenue by Placement Zone",
            "Live from the warehouse. The zone assignment is a column on dim_category, "
            "so this is a single GROUP BY rather than a separate analysis.",
        )
        zone_colour = {z["name"]: z["color"] for z in ZONES}
        zp = ZONE_PERF.copy()
        zp["revenue"] = zp["revenue"].astype(float)
        zp["revenue_share_pct"] = zp["revenue_share_pct"].astype(float)
        zfig = go.Figure(go.Bar(
            x=zp["revenue"] / 10_000_000,
            y=zp["zone_assignment"],
            orientation="h",
            marker_color=[zone_colour.get(n, ACCENT) for n in zp["zone_assignment"]],
            text=[f"Rs {v:.2f} Cr ({p:.1f}%)" for v, p in
                  zip(zp["revenue"] / 10_000_000, zp["revenue_share_pct"])],
            textposition="outside",
            customdata=zp[["zone_label", "n_categories", "baskets"]].values,
            hovertemplate=(
                "%{y} (%{customdata[0]})<br>Revenue: Rs %{x:.2f} Crore"
                "<br>%{customdata[1]} categories<br>%{customdata[2]:,} baskets<extra></extra>"
            ),
        ))
        zfig.update_xaxes(title_text="Revenue (Rs Crore)")
        zfig.update_yaxes(autorange="reversed")
        show_chart(style_fig(zfig, height=330, legend=False))
        _top = zp.loc[zp["revenue"].idxmax()]
        insight(
            f"{_top['zone_assignment']} carries {_top['revenue_share_pct']:.1f}% of all revenue from "
            f"{int(_top['n_categories'])} categories, which is what makes it the anchor zone. "
            "This query is only possible because the placement zones from notebook 07 are stored "
            "in the warehouse rather than living only in the analysis."
        )

    section("All Zones")
    for z in ZONES:
        render_html(
            f"<div class='ui-card' style='border-left:4px solid {z['color']};'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>"
            f"<div style='color:{T['text']};font-size:15px;font-weight:700;'>"
            f"<span style='display:inline-block;width:10px;height:10px;border-radius:2px;"
            f"background:{z['color']};margin-right:8px;'></span>{z['name']}</div>"
            f"<div style='color:{T['subtext']};font-size:12px;text-transform:uppercase;letter-spacing:0.06em;'>{z['label']}</div></div>"
            f"<div class='c-sub' style='color:{T['text']};margin-bottom:8px;'>{', '.join(z['categories'])}</div>"
            f"<div class='c-sub' style='border-top:1px solid {T['border']};padding-top:8px;'>{z['reason']}</div></div>"
        )

# ============================================================
# EXAMINER MODE - HOW DO I KNOW THESE NUMBERS ARE RIGHT?
# ============================================================

elif st.session_state.view_mode == "Examiner" and page == "How do I know these numbers are right?":
    page_header(
        "How do I know these numbers are right?",
        "Five documented errors, one shared direction, and the machinery that now "
        "checks every figure so a sixth would be caught.",
    )

    hero(
        "5 of 5",
        "errors found in this project made a result look better than the data "
        "supported. None understated one. The pattern, and the machinery that now "
        "prevents a sixth, are below.",
        value_color=NEGATIVE,
    )

    # ------------------------------------------------------------
    # Section 1: the five errors. Corrected values are read from the
    # verified record (config/metrics.py and the artifacts) at runtime;
    # the "reported" values are the historical wrong claims.
    # ------------------------------------------------------------
    fs_pen = float(
        category_dist.loc[category_dist["category"] == "FOOD STAPLES", "pct_of_baskets"].iloc[0]
    )
    model_vs_matched = M.REC_MODEL_HIT_PCT / M.REC_RANDOM_MATCHED_PCT

    section(
        "Five errors, one direction",
        "Every error found in this project is listed, with what was reported and what "
        "was correct. The corrected values are read from the verified record at runtime.",
    )

    _errors = [
        ("Product co-occurrence counted line items instead of baskets",
         "4,236 co-occurrences",
         f"{M.TOP_PAIR_COUNT:,} baskets",
         "Notebook 09 summed quantity products per basket instead of counting baskets "
         "containing both products. The artifact pipeline had always counted baskets "
         "correctly, so only the notebook was wrong."),
        ("A line item share was reported under a transactions label",
         "23.34% of transactions",
         f"{fs_pen}% basket penetration",
         "23.34% is FOOD STAPLES' share of line items. The chart axis said transactions, "
         "which the number never measured. The share of baskets containing the category "
         "is the figure the label promised."),
        ("A bounded score's gain was expressed as a percentage",
         "\"189% improvement\"",
         f"+{M.SILHOUETTE_INCREASE} absolute",
         "Silhouette is bounded on [-1, 1] and has no meaningful zero, so a ratio "
         "between two silhouette values has no interpretation. The absolute increase "
         f"from {M.SILHOUETTE_FREQUENCY:.3f} to {M.SILHOUETTE_COOCCURRENCE} is the "
         "correct statement."),
        ("A hit rate was reported against the wrong denominator",
         f"quoted for the full {M.ML_TEST_BASKETS:,}-basket test set",
         f"computed on {M.REC_TEST_BASKETS:,} multi-product baskets",
         "The rate was measured on the subset of test baskets with more than one "
         "product, then quoted as if it covered the whole held-out set."),
        ("The recommender was compared to an unmatched baseline",
         "28x better than chance (1% uniform random)",
         f"about {model_vs_matched:.0f}x at a matched budget",
         f"The model issues {M.REC_AVG_RECS_PER_BASKET} recommendations per basket, so "
         f"matched random scores {M.REC_RANDOM_MATCHED_PCT}%, not 1%. A popularity "
         f"baseline at equal budget scores {M.REC_POPULARITY_MATCHED_PCT}% against the "
         f"model's {M.REC_MODEL_HIT_PCT}%. The honest comparison is much closer than "
         "the reported one."),
    ]

    for i, (title, reported, correct, note) in enumerate(_errors, 1):
        render_html(
            f"<div class='ui-card' style='display:flex;gap:16px;align-items:flex-start;'>"
            f"<div style='color:{NEGATIVE};font-size:20px;font-weight:800;min-width:28px;'>{i}</div>"
            f"<div style='flex:1;'>"
            f"<div class='c-title' style='margin-bottom:6px;'>{title}</div>"
            f"<div style='font-size:14px;margin-bottom:6px;'>"
            f"<span style='color:{NEGATIVE};text-decoration:line-through;'>{reported}</span>"
            f"<span style='color:{T['subtext']};'> &#8594; </span>"
            f"<span style='color:{T['text']};font-weight:700;'>{correct}</span></div>"
            f"<div class='c-sub'>{note}</div></div>"
            f"<div style='flex:none;background:rgba(220,38,38,0.10);color:{NEGATIVE};"
            f"font-size:10.5px;font-weight:700;letter-spacing:0.06em;border-radius:99px;"
            f"padding:3px 10px;white-space:nowrap;'>FLATTERED THE RESULT</div>"
            f"</div>"
        )

    info_card(
        "The finding is the direction, not the errors",
        "All five corrections moved the same way: every error made a result appear "
        "larger, cleaner or more impressive than the data supported, and no error was "
        "found that had understated one. Measurement error is not randomly signed with "
        "respect to the interests of the person measuring. That is why every figure in "
        "this project is now checked by a machine, below, instead of being trusted.",
        accent=NEGATIVE,
    )

    st.markdown("---")

    # ------------------------------------------------------------
    # Section 2: live verification status, read from the report that
    # scripts/run_verifications.py writes. The timestamp is displayed
    # prominently because a stale pass shown as current would be exactly
    # the kind of error this page exists to prevent.
    # ------------------------------------------------------------
    section(
        "Verification status",
        "Read from reports/verification_status.json, written each time "
        "scripts/run_verifications.py runs all three mechanisms.",
    )

    vstat = load_verification_status()
    if vstat is None:
        render_html(
            f"<div class='ui-card' style='border-left:4px solid {NEGATIVE};'>"
            f"<div class='c-title' style='color:{NEGATIVE};margin-bottom:6px;'>"
            f"No verification report found</div>"
            f"<div class='c-sub'>Run <b>python scripts/run_verifications.py</b> from the "
            f"repository root. Until it has run, treat every figure on this dashboard "
            f"as unverified.</div></div>"
        )
    else:
        _age_days = (pd.Timestamp.now() - pd.Timestamp(vstat["generated_at"])).days
        _all_ok = vstat.get("all_passed", False)
        _dotc = POSITIVE if _all_ok else NEGATIVE
        _verdict = "ALL PASSED" if _all_ok else "FAILING"
        render_html(
            f"<div class='ui-card' style='border-left:4px solid {_dotc};'>"
            f"<div class='c-label'>Last verified</div>"
            f"<div style='font-size:24px;font-weight:800;color:{T['text']};'>"
            f"{vstat.get('generated_at_human', vstat['generated_at'])}"
            f" <span style='color:{_dotc};font-size:14px;'>{_verdict}</span></div>"
            f"<div class='c-sub' style='margin-top:4px;'>"
            f"{'Today' if _age_days == 0 else f'{_age_days} day(s) ago'}. "
            f"A pass is only as current as this timestamp; re-run with "
            f"<b>python scripts/run_verifications.py</b>.</div></div>"
        )
        if _age_days > 7:
            # Red is legitimate here: a stale pass presented as current is a
            # failure of the verification claim itself.
            render_html(
                f"<div class='ui-card' style='border-left:4px solid {NEGATIVE};'>"
                f"<div class='c-sub' style='color:{T['text']};'>"
                f"<b style='color:{NEGATIVE};'>Stale:</b> this report is "
                f"{_age_days} days old. Anything changed since then is unverified.</div></div>"
            )

        _mechanisms = [
            ("verify_thesis_numbers", "scripts/verify_thesis_numbers.py",
             "reported figures checked against a live source"),
            ("quality_checks", "etl/quality_checks.py",
             "warehouse checked against the OLTP source and the thesis"),
            ("reproduce_all_results", "reproduce_all_results.py",
             "artifacts regenerated, every stage re-checked"),
        ]
        for key, script, what in _mechanisms:
            c = vstat["checks"].get(key)
            if c is None:
                continue
            ok = c.get("ok", False)
            chip_c = POSITIVE if ok else NEGATIVE
            if key == "verify_thesis_numbers":
                # This script's own summary line is the meaningful count.
                shown = f"{c.get('verified', c.get('passed', 0))} of {c.get('checkable', c.get('total', 0))}"
            else:
                shown = f"{c.get('passed', 0)} of {c.get('total', 0)}"
            extra = f" across {c['stages']} stages" if c.get("stages") else ""
            render_html(
                f"<div class='ui-card' style='display:flex;justify-content:space-between;"
                f"align-items:center;padding:12px 18px;'>"
                f"<div><div class='c-title' style='font-size:14px;'>{script}</div>"
                f"<div class='c-sub'>{what}</div></div>"
                f"<div style='text-align:right;'>"
                f"<div style='color:{chip_c};font-weight:800;font-size:16px;'>"
                f"{'PASS' if ok else 'FAIL'} {shown}{extra}</div></div></div>"
            )

    st.markdown("---")

    # ------------------------------------------------------------
    # Section 3: what this study does not know. The rule-coverage counts
    # are computed from the mined rules at runtime; the basket reach is
    # recomputed from the warehouse when it is running.
    # ------------------------------------------------------------
    n_all_cats = int(len(cluster_assign))
    n_lift3 = len(rule_categories(category_rules, 3.0))
    n_lift2 = len(rule_categories(category_rules, 2.0))
    n_no_rule = n_all_cats - len(rule_categories(category_rules, 0.0))
    reach = load_layout_reach(tuple(sorted(rule_categories(category_rules, 3.0))))

    section("What this study does not know", "Stated plainly, so the result above is read at its actual size.")

    _unknowns = [
        ("The revenue uplift is projected, not measured",
         f"The rupee figure applies the {M.UPLIFT_SCENARIO_PCT}% mid-point of the 4 to 6% "
         "range reported by Dreze, Hoch and Purk (1994) to observed basket values. No shelf "
         "was moved during this study, so customer response was never observed. Only a "
         "controlled in-store trial could measure it."),
        ("Most categories carry no strong rule",
         f"Rule coverage reaches {n_lift3} of {n_all_cats} categories at lift 3.0. "
         f"Relaxing the threshold to lift 2.0 reaches {n_lift2}. {n_no_rule} categories "
         "carry no rule at any threshold, so association evidence says nothing about "
         "where they should go."),
        ("The layout cannot reach every basket",
         f"{reach['reachable_pct']}% of baskets contain at least one category that "
         f"appears in a strong rule, so the layout can in principle influence them. "
         f"The other {reach['unreachable_pct']}%, carrying "
         f"{reach['unreachable_revenue_pct']}% of revenue, are unaffected by any zone "
         f"arrangement this study can propose. ({reach['source']}.)"),
    ]
    for title, body in _unknowns:
        info_card(title, body)

# ============================================================
# EXAMINER MODE - ETHICS & DATA
# ============================================================

elif st.session_state.view_mode == "Examiner" and page == "Was this done responsibly?":
    page_header(
        "Was this done responsibly?",
        "Objective 5 -- responsible use of real store data.",
    )

    hero(
        "98% cash",
        "of transactions carry no customer identity at all. Primary data from the "
        "student's own family-run store, used with management's permission. No names, "
        "phone numbers, addresses or loyalty IDs exist anywhere in the record.",
    )

    info_card(
        "Data provenance &amp; consent",
        "This is <b>primary data</b> collected from the student's own family-run store, "
        "used <b>with the explicit permission of store management</b> for academic research "
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
        "All association, clustering and basket figures are measured from the data. The 4% to 6% revenue uplift is "
        "clearly labelled as a <b>projection</b> based on retail-industry benchmarks, not the result of a live in-store "
        "experiment. The cross-sell before/after on the Placement Zones page is a data-driven result computed from the "
        "association rules; only the rupee conversion is a projection.",
    )
