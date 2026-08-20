"""
make_chart25_silhouette_comparison.py

Renders reports/figures/chart25_silhouette_comparison.png: silhouette
coefficient against number of clusters for BOTH representations used in
notebook 06, on one pair of axes.

Notebook 06 computes two K-Means sweeps over k = 2..10 but only saves a chart
for the first one (chart11_silhouette_scores.png, frequency features). This
script recomputes both sweeps from the same input with the same parameters
(random_state=42, n_init=10) so the chart is reproducible rather than
transcribed, then checks the recomputed values against the numbers printed in
the notebook's stored output before drawing anything.

    python scripts/make_chart25_silhouette_comparison.py

Peak values are taken from the recomputed series, not asserted in advance.
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASKET_PATH = os.path.join(ROOT, "data", "processed", "basket_encoded.csv")
FIGURES = os.path.join(ROOT, "reports", "figures")
OUT_PATH = os.path.join(FIGURES, "chart25_silhouette_comparison.png")

K_RANGE = list(range(2, 11))

FREQ_COLOUR = "#94A3B8"
COOC_COLOUR = "#0F766E"
WEAK_THRESHOLD = 0.25

# Silhouette values printed in notebook 06's stored output, used only to
# (re-pinned 2026-08-17 after the audited category remap)
# confirm this script reproduces the notebook. Frequency values are printed to
# 4 dp there, co-occurrence values to 3 dp.
NOTEBOOK_FREQ = {2: 0.3326, 3: 0.1942, 4: 0.2091, 5: 0.1829, 6: 0.0669,
                 7: 0.1573, 8: 0.1757, 9: 0.1698, 10: 0.1724}
NOTEBOOK_COOC = {2: 0.491, 3: 0.493, 4: 0.438, 5: 0.422, 6: 0.383,
                 7: 0.375, 8: 0.380, 9: 0.375, 10: 0.369}


def silhouette_sweep(scaled):
    """Silhouette coefficient at each k in K_RANGE, notebook 06's parameters."""
    scores = []
    for k in K_RANGE:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(scaled)
        scores.append(silhouette_score(scaled, labels))
    return scores


def compute_series():
    basket_df = pd.read_csv(BASKET_PATH)

    # Representation 1: purchase frequency. Each category is a row, each
    # transaction a feature (notebook 06, step 5).
    category_matrix = basket_df.T
    frequency_scaled = StandardScaler().fit_transform(category_matrix)

    # Representation 2: co-occurrence. Each category is described by how often
    # it shares a basket with every other category, self-pairs zeroed out
    # (notebook 06, step 7).
    basket_numeric = basket_df.astype(int)
    cooccurrence = basket_numeric.T.dot(basket_numeric).values.astype(float)
    np.fill_diagonal(cooccurrence, 0)
    cooccurrence_scaled = StandardScaler().fit_transform(cooccurrence)

    return silhouette_sweep(frequency_scaled), silhouette_sweep(cooccurrence_scaled)


def check_against_notebook(freq, cooc):
    """Warn on any k where this run departs from notebook 06's stored output."""
    drifted = []
    for k, value in zip(K_RANGE, freq):
        if abs(value - NOTEBOOK_FREQ[k]) > 5e-4:
            drifted.append(f"  frequency      k={k}: recomputed {value:.4f}, "
                           f"notebook {NOTEBOOK_FREQ[k]:.4f}")
    for k, value in zip(K_RANGE, cooc):
        if abs(value - NOTEBOOK_COOC[k]) > 5e-4:
            drifted.append(f"  co-occurrence  k={k}: recomputed {value:.4f}, "
                           f"notebook {NOTEBOOK_COOC[k]:.3f}")
    if drifted:
        print("WARNING: recomputed values differ from notebook 06's output:")
        print("\n".join(drifted))
    else:
        print("[PASS] Both series reproduce notebook 06's stored output exactly.")


def annotate_peak(ax, series, colour, offset, ha="left"):
    """Label a series' maximum with its k and value."""
    peak_index = int(np.argmax(series))
    peak_k, peak_value = K_RANGE[peak_index], series[peak_index]
    ax.annotate(
        f"Peak {peak_value:.3f} at k={peak_k}",
        xy=(peak_k, peak_value),
        xytext=(peak_k + offset[0], peak_value + offset[1]),
        color=colour,
        fontsize=11,
        fontweight="bold",
        ha=ha,
        va="center",
        arrowprops=dict(arrowstyle="-", color=colour, linewidth=1.2,
                        shrinkA=0, shrinkB=6),
    )
    return peak_k, peak_value


def render(freq, cooc):
    fig, ax = plt.subplots(figsize=(12, 7))

    ax.axhline(WEAK_THRESHOLD, color="#64748B", linestyle="--", linewidth=1.4,
               zorder=1)
    ax.text(11.35, WEAK_THRESHOLD + 0.012, "weakly separated below this",
            color="#64748B", fontsize=10, va="bottom", ha="right")

    ax.plot(K_RANGE, freq, color=FREQ_COLOUR, linewidth=2, marker="o",
            markersize=8, label="Frequency features", zorder=2)
    ax.plot(K_RANGE, cooc, color=COOC_COLOUR, linewidth=2, marker="o",
            markersize=8, label="Co-occurrence features", zorder=3)

    freq_peak = annotate_peak(ax, freq, FREQ_COLOUR, offset=(0.35, -0.055))
    cooc_peak = annotate_peak(ax, cooc, COOC_COLOUR, offset=(0.5, 0.055))

    ax.set_xlabel("Number of clusters, k", fontsize=12)
    ax.set_ylabel("Silhouette coefficient", fontsize=12)
    ax.set_title("Silhouette by number of clusters, two representations",
                 fontsize=15, pad=16, loc="left")

    ax.set_xlim(1.8, 11.4)
    ax.set_xticks(K_RANGE)
    ax.set_ylim(0, 0.7)
    ax.set_yticks(np.arange(0, 0.71, 0.1))

    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBD5E1")
    ax.spines["bottom"].set_color("#CBD5E1")
    ax.tick_params(colors="#475569", labelsize=11)

    ax.legend(frameon=False, fontsize=11, loc="upper right",
              bbox_to_anchor=(1.0, 1.0))

    fig.tight_layout()
    os.makedirs(FIGURES, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=300)
    plt.close(fig)
    return freq_peak, cooc_peak


def main():
    freq, cooc = compute_series()

    print("Silhouette by k:")
    print(f"  {'k':>3}  {'frequency':>10}  {'co-occurrence':>13}")
    for k, f, c in zip(K_RANGE, freq, cooc):
        print(f"  {k:>3}  {f:>10.4f}  {c:>13.4f}")

    check_against_notebook(freq, cooc)

    freq_peak, cooc_peak = render(freq, cooc)
    print(f"\nFrequency peak:     {freq_peak[1]:.4f} at k={freq_peak[0]}")
    print(f"Co-occurrence peak: {cooc_peak[1]:.4f} at k={cooc_peak[0]}")
    print(f"\nSaved {os.path.relpath(OUT_PATH, ROOT)}")


if __name__ == "__main__":
    main()
