"""
make_chart10_abc_analysis.py

Renders reports/figures/chart10_abc_analysis_adter.png: the ABC Pareto curve of
cumulative revenue by product rank, restyled onto the document palette.

This is a restyle only. The classification logic is copied unchanged from
notebook 03 chart 10 (A = cumulative revenue up to 70%, B = up to 90%, C = the
rest) and recomputed from the same input, so no value is transcribed by hand.
The recomputed class counts are checked against dashboard/artifacts/
abc_analysis.csv before anything is drawn.

    python scripts/make_chart10_abc_analysis.py

The original chart10_abc_analysis.png is left untouched.
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SALES_PATH = os.path.join(ROOT, "data", "processed", "sales_data_cleaned.csv")
ARTIFACT_PATH = os.path.join(ROOT, "dashboard", "artifacts", "abc_analysis.csv")
FIGURES = os.path.join(ROOT, "reports", "figures")
OUT_PATH = os.path.join(FIGURES, "chart10_abc_analysis_adter.png")

TEAL = "#0F766E"
SLATE = "#94A3B8"
MIST = "#E2E8F0"
LINE_GREY = "#CBD5E1"
INK_MUTED = "#64748B"

BAND_ALPHA = 0.15


def compute_abc():
    """Notebook 03 chart 10's classification, recomputed from the source data."""
    df = pd.read_csv(SALES_PATH, usecols=["product", "total_amount"])

    product_revenue = df.groupby("product")["total_amount"].sum().sort_values(ascending=False)
    total_products = len(product_revenue)
    total_revenue = product_revenue.sum()
    cumulative_pct = product_revenue.cumsum() / total_revenue * 100

    def abc_class(pct):
        if pct <= 70:
            return "A"
        elif pct <= 90:
            return "B"
        return "C"

    classes = cumulative_pct.apply(abc_class)

    counts = {c: int((classes == c).sum()) for c in "ABC"}
    revenue_share = {
        c: float(product_revenue[classes == c].sum() / total_revenue * 100) for c in "ABC"
    }

    return {
        "cumulative_pct": cumulative_pct.values,
        "total_products": total_products,
        "counts": counts,
        "assortment_share": {c: counts[c] / total_products * 100 for c in "ABC"},
        "revenue_share": revenue_share,
    }


def check(m):
    """Cross-check the recomputed classification against the stored artifact."""
    problems = []

    total = sum(m["counts"].values())
    if total != m["total_products"]:
        problems.append(f"  class counts sum to {total}, but there are "
                        f"{m['total_products']} products")

    if os.path.exists(ARTIFACT_PATH):
        artifact = pd.read_csv(ARTIFACT_PATH)
        for c in "ABC":
            stored = int((artifact["abc_category"] == c).sum())
            if stored != m["counts"][c]:
                problems.append(f"  class {c}: recomputed {m['counts'][c]}, "
                                f"artifact {stored}")
    else:
        problems.append(f"  artifact not found at {ARTIFACT_PATH}, no cross-check run")

    if problems:
        print("WARNING:")
        print("\n".join(problems))
    else:
        print("[PASS] Class counts sum to the product total and match the stored artifact.")


def render(m):
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]

    counts, assortment = m["counts"], m["assortment_share"]
    a, b = counts["A"], counts["B"]
    total = m["total_products"]

    fig, ax = plt.subplots(figsize=(12, 7))

    # Class bands, drawn first so the curve and reference lines sit on top.
    for start, end, colour in [(0, a, TEAL), (a, a + b, SLATE), (a + b, total, MIST)]:
        ax.axvspan(start, end, color=colour, alpha=BAND_ALPHA, linewidth=0)

    for y in (70, 90):
        ax.axhline(y, color=LINE_GREY, linestyle="--", linewidth=1, zorder=2)

    ranks = np.arange(1, total + 1)
    ax.plot(ranks, m["cumulative_pct"], color=TEAL, linewidth=2.5, solid_capstyle="round",
            zorder=3)

    # Each label is anchored inside its own band and offset vertically so the
    # three never collide. Class A's band is only 6% of the axis width, far
    # narrower than its own caption, so the text runs on past the band edge
    # rather than being centred on it (which is what clipped the y-axis before).
    labels = [
        (55, 34, TEAL, f"{counts['A']:,} products",
         f"{assortment['A']:.1f}% of the assortment, 70% of revenue"),
        (400, 18, INK_MUTED, f"{counts['B']:,} products",
         f"{assortment['B']:.1f}% of the assortment, next 20% of revenue"),
        (2500, 52, SLATE, f"{counts['C']:,} products",
         f"{assortment['C']:.1f}% of the assortment, final 10% of revenue"),
    ]
    for x, y, colour, line1, line2 in labels:
        ax.text(x, y, line1, color=colour, fontsize=15, fontweight="bold",
                ha="left", va="bottom", zorder=4)
        ax.text(x, y - 6.5, line2, color=colour, fontsize=15, fontweight="bold",
                ha="left", va="bottom", zorder=4)

    ax.set_title("Revenue concentration by product",
                 fontsize=17, fontweight="bold", loc="left", pad=36)
    ax.text(0, 1.035,
            "Six per cent of the assortment carries the first seventy per cent of revenue",
            transform=ax.transAxes, fontsize=15, color=INK_MUTED,
            ha="left", va="bottom")

    ax.set_xlabel("Products ranked by revenue", fontsize=13, color=INK_MUTED)
    ax.set_ylabel("Cumulative share of revenue", fontsize=13, color=INK_MUTED)

    ax.set_xlim(0, total)
    ax.set_ylim(0, 105)

    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(LINE_GREY)
    ax.spines["bottom"].set_color(LINE_GREY)
    ax.tick_params(colors=INK_MUTED, labelsize=12)

    fig.tight_layout()
    os.makedirs(FIGURES, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=300)
    plt.close(fig)


def main():
    m = compute_abc()

    print(f"Products with sales: {m['total_products']:,}")
    for c in "ABC":
        print(f"Class {c}: {m['counts'][c]:>5,} products  "
              f"{m['assortment_share'][c]:6.2f}% of assortment  "
              f"{m['revenue_share'][c]:6.2f}% of revenue")

    check(m)

    render(m)
    print(f"\nSaved {os.path.relpath(OUT_PATH, ROOT)}")


if __name__ == "__main__":
    main()
