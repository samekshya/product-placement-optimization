"""
make_chart26_category_penetration.py

Renders reports/figures/chart26_category_penetration.png: the share of baskets
containing each of the 25 categories.

This is a new chart, not a restyle of chart2_category_distribution.png. That
chart plots line item counts, which answers "how many units were scanned?"
Placement is decided by how many shopping trips walk past a category, so the
measure here is basket penetration: the pct_of_baskets field computed in
notebook 03 chart 2, never the pct_of_line_items field plotted there.

    python scripts/make_chart26_category_penetration.py

Every number on the chart, including the line-item figure quoted in the
footnote, is computed by this script from the cleaned data.
"""

import os

import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SALES_PATH = os.path.join(ROOT, "data", "processed", "sales_data_cleaned.csv")
FIGURES = os.path.join(ROOT, "reports", "figures")
OUT_PATH = os.path.join(FIGURES, "chart26_category_penetration.png")

TEAL = "#0F766E"
MIST = "#E2E8F0"
LINE_GREY = "#CBD5E1"
INK_MUTED = "#64748B"
INK_FAINT = "#94A3B8"

HIGHLIGHT_TOP = 2


def compute_penetration():
    """Notebook 03 chart 2's two measures, recomputed from the cleaned data."""
    df = pd.read_csv(SALES_PATH, usecols=["category", "invoice_no"])

    total_baskets = df["invoice_no"].nunique()
    total_line_items = len(df)

    baskets = df.groupby("category")["invoice_no"].nunique()
    line_items = df["category"].value_counts()

    summary = pd.DataFrame({
        "baskets": baskets,
        "pct_of_baskets": baskets / total_baskets * 100,
        "line_items": line_items,
        "pct_of_line_items": line_items / total_line_items * 100,
    }).sort_values("pct_of_baskets", ascending=False)

    return summary, total_baskets, total_line_items


def render(summary):
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]

    # Plotted bottom-up so the highest penetration lands at the top of the axis.
    plotted = summary.iloc[::-1]
    names = [c.capitalize() for c in plotted.index]
    values = plotted["pct_of_baskets"].values

    # The top HIGHLIGHT_TOP categories by penetration are the last rows now.
    highlight = [i >= len(values) - HIGHLIGHT_TOP for i in range(len(values))]
    bar_colours = [TEAL if h else MIST for h in highlight]
    label_colours = [TEAL if h else INK_MUTED for h in highlight]

    fig, ax = plt.subplots(figsize=(12, 9))
    fig.subplots_adjust(left=0.26, right=0.97, top=0.86, bottom=0.17)

    # Everything in the left margin - names, title, subtitle, footnote - hangs
    # off this one x so the whole block shares a flush left edge.
    LEFT_EDGE = 0.045

    positions = range(len(values))
    ax.barh(list(positions), values, height=0.72, color=bar_colours, linewidth=0)

    for y, value, colour in zip(positions, values, label_colours):
        ax.text(value + 0.55, y, f"{value:.1f}", va="center", ha="left",
                fontsize=12, color=colour)

    # Category names are drawn as text rather than tick labels so every name
    # starts at the same x, giving a flush left edge.
    ax.set_yticks(list(positions))
    ax.set_yticklabels([])
    ax.tick_params(axis="y", length=0)
    name_x = (LEFT_EDGE - 0.26) / (0.97 - 0.26)  # LEFT_EDGE, in axes coordinates
    for y, name in zip(positions, names):
        ax.text(name_x, y, name, transform=ax.get_yaxis_transform(),
                va="center", ha="left", fontsize=12, color=INK_MUTED)

    fig.text(LEFT_EDGE, 0.955,
             "Category penetration, share of baskets containing each category",
             fontsize=17, fontweight="bold", ha="left", va="bottom")
    fig.text(LEFT_EDGE, 0.918,
             "FOOD STAPLES appears in just under one in three shopping trips",
             fontsize=15, color=INK_MUTED, ha="left", va="bottom")

    ax.set_xlabel("Share of baskets containing the category (%)",
                  fontsize=13, color=INK_MUTED, labelpad=10)
    # Derived from the data rather than fixed at 45, which was sized for the
    # pre-remap peak of 42.2 and left a third of the axis empty afterwards.
    ax.set_xlim(0, max(values) * 1.15)
    ax.set_ylim(-0.8, len(values) - 0.2)

    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(LINE_GREY)
    ax.spines["bottom"].set_color(LINE_GREY)
    ax.tick_params(axis="x", colors=INK_MUTED, labelsize=12)

    # Computed, not transcribed. This footnote previously carried a hardcoded
    # 23.34, which was the pre-remap line-item share and did not survive the
    # audited category remap. Deriving it here means it cannot go stale again.
    top_line_item_pct = summary["pct_of_line_items"].iloc[0]
    fig.text(LEFT_EDGE, 0.025,
             "Penetration counts baskets, not items. The same category accounts for "
             f"{top_line_item_pct:.2f} per cent of line items\nsold, a different measure answering a "
             "different question.",
             fontsize=13, color=INK_FAINT, ha="left", va="bottom", linespacing=1.5)

    os.makedirs(FIGURES, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=300)
    plt.close(fig)


def main():
    summary, total_baskets, total_line_items = compute_penetration()

    print(f"Baskets: {total_baskets:,}   line items: {total_line_items:,}   "
          f"categories: {len(summary)}")
    print(f"\n{'category':<28}{'pct_of_baskets':>16}{'pct_of_line_items':>20}")
    for name, row in summary.iterrows():
        print(f"{name:<28}{row['pct_of_baskets']:>16.4f}{row['pct_of_line_items']:>20.4f}")

    top = summary.head(HIGHLIGHT_TOP)
    print("\nHighlighted (top two by penetration):")
    for name, row in top.iterrows():
        print(f"  {name}: {row['pct_of_baskets']:.4f}% of baskets "
              f"({row['baskets']:,.0f} of {total_baskets:,})")

    staples_line_items = summary.loc["FOOD STAPLES", "pct_of_line_items"]
    print(f"\nFootnote figure, FOOD STAPLES line-item share: {staples_line_items:.4f}%")

    render(summary)
    print(f"\nSaved {os.path.relpath(OUT_PATH, ROOT)}")


if __name__ == "__main__":
    main()
