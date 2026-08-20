"""
make_chart22_crosssell_before_after.py

Renders reports/figures/chart22_crosssell_before_after.png: how many strong
cross-sell rules each layout co-locates, existing against proposed.

Notebook 07 computes this comparison and draws the chart inline. This script
recomputes the same figures from the same input with the same parameters, so
the restyled chart is reproducible rather than transcribed, and so the support
totals it prints can be checked. The notebook prints only the percentages
(5.7% / 54.1% since the 2026-08-17 remap and zone re-derivation); the
absolute support sums are computed there but never shown,
so this script surfaces them.

    python scripts/make_chart22_crosssell_before_after.py

No value is restated by hand. Every number on the chart comes from this run.
"""

import os

import matplotlib.pyplot as plt
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SALES_PATH = os.path.join(ROOT, "data", "processed", "sales_data_cleaned.csv")
FIGURES = os.path.join(ROOT, "reports", "figures")
OUT_PATH = os.path.join(FIGURES, "chart22_crosssell_before_after.png")

LIFT_FLOOR = 3.0
MIN_SUPPORT = 0.01

EXISTING_FILL = "#E2E8F0"
EXISTING_EDGE = "#CBD5E1"
PROPOSED_FILL = "#0F766E"
EXISTING_LABEL_INK = "#475569"
SUPPORT_INK = "#64748B"
SPINE_INK = "#CBD5E1"

# The five zones, re-derived 2026-08-17; same content as analysis/zones.py.
PLACEMENT_ZONES = [
    ["FOOD STAPLES", "CANNED AND PACKAGED FOODS", "CLEANING SUPPLIES", "TEA AND SPICES", "PERSONAL CARE", "COOKING OIL"],
    ["CONFECTIONERY", "SNACKS", "NOODLES", "HOUSEHOLD ITEMS", "POOJA ITEMS"],
    ["BISCUITS AND COOKIES", "BABY CARE", "STATIONERY"],
    ["DAIRY PRODUCTS", "FROZEN FOODS", "FRESH PRODUCE", "BAKERY"],
    ["RICE", "ALCOHOLIC BEVERAGES", "CIGARETTE AND TOBACCO", "SOFT DRINKS AND JUICES", "BREAKFAST CEREALS", "ELECTRICAL SUPPLIES", "PARTY SUPPLIES"],
]

# Counts and percentages printed in notebook 07's stored output, used only to
# confirm this script reproduces it.
# Re-pinned 2026-08-17, twice: first after the audited category remap, then
# after the five zones were re-derived from the post-remap rules. It was
# 28 / 56 / 8.2 / 16.3 before the remap and 22 / 16 / 5.65 / 5.73 in between,
# when the stale hand-built layout briefly lost to the baseline.
NOTEBOOK_EXPECTED = {
    "existing_rules": 22, "proposed_rules": 180,
    "existing_pct": 5.65, "proposed_pct": 54.14,
}


def compute_capture():
    df = pd.read_csv(SALES_PATH)

    basket = (
        df.groupby("invoice_no")["category"]
          .apply(lambda s: pd.Series(1, index=s.unique()))
          .unstack(fill_value=0)
          .astype(bool)
    )
    frequent = apriori(basket, min_support=MIN_SUPPORT, use_colnames=True)
    rules = association_rules(frequent, metric="lift", min_threshold=1.0)

    strong = rules[rules["lift"] >= LIFT_FLOOR].copy()
    strong["cats"] = strong.apply(
        lambda r: set(r["antecedents"]) | set(r["consequents"]), axis=1
    )

    # Existing layout: the frequency K-Means clusters from notebook 06 at k=5.
    cat_matrix = basket.astype(int).T
    freq_scaled = StandardScaler().fit_transform(cat_matrix)
    freq_labels = KMeans(n_clusters=5, random_state=42, n_init=10).fit_predict(freq_scaled)
    existing_groups = [set(basket.columns[freq_labels == c]) for c in range(5)]

    proposed_groups = [set(zone) for zone in PLACEMENT_ZONES]

    def capture(groups):
        """A rule counts as captured when all its categories sit in one group."""
        mask = strong["cats"].apply(lambda c: any(c <= g for g in groups))
        return int(mask.sum()), float(strong.loc[mask, "support"].sum())

    existing = capture(existing_groups)
    proposed = capture(proposed_groups)
    total_support = float(strong["support"].sum())

    return {
        "total_strong": len(strong),
        "total_support": total_support,
        "existing_rules": existing[0],
        "existing_support": existing[1],
        "existing_pct": existing[1] / total_support * 100,
        "proposed_rules": proposed[0],
        "proposed_support": proposed[1],
        "proposed_pct": proposed[1] / total_support * 100,
    }


def check_against_notebook(m):
    """Warn on any figure that departs from notebook 07's stored output."""
    drifted = []
    for key, expected in NOTEBOOK_EXPECTED.items():
        actual = m[key]
        if abs(actual - expected) > 0.05:
            drifted.append(f"  {key}: recomputed {actual}, notebook {expected}")
    if drifted:
        print("WARNING: recomputed values differ from notebook 07's output:")
        print("\n".join(drifted))
    else:
        print("[PASS] Rule counts and percentages reproduce notebook 07's output.")


def render(m):
    plt.rcParams["font.family"] = "sans-serif"

    fig, ax = plt.subplots(figsize=(10, 7))

    labels = ["Existing layout\n(frequency clusters)",
              "Proposed layout\n(five designed zones)"]
    counts = [m["existing_rules"], m["proposed_rules"]]
    supports = [(m["existing_support"], m["existing_pct"]),
                (m["proposed_support"], m["proposed_pct"])]
    label_inks = [EXISTING_LABEL_INK, PROPOSED_FILL]

    bars = ax.bar(labels, counts, width=0.55,
                  color=[EXISTING_FILL, PROPOSED_FILL],
                  edgecolor=[EXISTING_EDGE, PROPOSED_FILL], linewidth=1)

    # Offsets are in POINTS, not data units. They used to be +6.4 and +2.4 in
    # data units, tuned when the tallest bar was 56 and the axis topped out at
    # 90. Post-remap the proposed layout captures 180, the axis runs to 288,
    # and those same offsets shrank to nothing on screen so the two labels
    # printed on top of each other. Points keep the gap fixed at any scale.
    for bar, count, (support, pct), ink in zip(bars, counts, supports, label_inks):
        centre = bar.get_x() + bar.get_width() / 2
        ax.annotate(f"{count} rules", xy=(centre, bar.get_height()),
                    xytext=(0, 26), textcoords="offset points",
                    ha="center", va="bottom", fontsize=16, fontweight="bold",
                    color=ink)
        ax.annotate(f"{support:.3f} support, {pct:.1f}%",
                    xy=(centre, bar.get_height()),
                    xytext=(0, 8), textcoords="offset points",
                    ha="center", va="bottom", fontsize=13, color=SUPPORT_INK)

    ax.set_title("Cross-sell capture, existing against proposed layout",
                 fontsize=15, fontweight="bold", loc="left", pad=34)
    _delta = m["proposed_rules"] - m["existing_rules"]
    _verdict = (f"{_delta:+d} rules" if _delta else "no change")
    ax.text(0, 1.035,
            f"{m['proposed_rules']} strong rules co-located against "
            f"{m['existing_rules']}, {_verdict}",
            transform=ax.transAxes, fontsize=12.5, color=SUPPORT_INK,
            ha="left", va="bottom")

    ax.set_ylabel("Strong cross-sell rules co-located", fontsize=12)
    ax.set_ylim(0, max(30, max(m["existing_rules"], m["proposed_rules"]) * 1.6))

    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(SPINE_INK)
    ax.spines["bottom"].set_color(SPINE_INK)
    ax.tick_params(colors="#475569", labelsize=11.5)

    fig.tight_layout()
    os.makedirs(FIGURES, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=300)
    plt.close(fig)


def main():
    m = compute_capture()

    print(f"Strong cross-sell rules (lift >= {LIFT_FLOOR:.0f}): {m['total_strong']}")
    print(f"Total strong-rule support:  {m['total_support']:.4f}")
    print(f"Existing layout: {m['existing_rules']} rules, "
          f"{m['existing_support']:.4f} support, {m['existing_pct']:.1f}%")
    print(f"Proposed layout: {m['proposed_rules']} rules, "
          f"{m['proposed_support']:.4f} support, {m['proposed_pct']:.1f}%")

    check_against_notebook(m)

    render(m)
    print(f"\nSaved {os.path.relpath(OUT_PATH, ROOT)}")


if __name__ == "__main__":
    main()
