"""
make_chart10_network_graph.py

Renders reports/figures/chart10_network_graph.png: the category relationship
network built from the strong association rules, restyled onto the document
palette.

This is a restyle only. The graph is rebuilt exactly as notebook 05 chart 10
builds it - same input, same FP-Growth parameters, same lift filter, same
spring layout seed - so the node set, the edge set and every node position are
unchanged. What changes is colour, node radius (now degree, previously basket
count), label placement and chrome.

    python scripts/make_chart10_network_graph.py

The rule count, edge count and CLEANING SUPPLIES' degree are recomputed and
checked against the figures quoted in the notebook's write-up.
"""

import os

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import association_rules, fpgrowth

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASKET_PATH = os.path.join(ROOT, "data", "processed", "basket_encoded.csv")
FIGURES = os.path.join(ROOT, "reports", "figures")
OUT_PATH = os.path.join(FIGURES, "chart10_network_graph.png")

TEAL = "#0F766E"
NODE_FILL = "#E2E8F0"
NODE_EDGE = "#CBD5E1"
EDGE_GREY = "#CBD5E1"
INK_DARK = "#1C1917"
INK_MUTED = "#64748B"
INK_FAINT = "#94A3B8"

FOCUS = "CLEANING SUPPLIES"
MIN_SUPPORT = 0.01
LIFT_FLOOR = 3

# Figures quoted in notebook 05's write-up, checked but never used as data.
# Re-pinned 2026-08-17 after the audited category remap (was 360 / 38 / 9).
EXPECTED = {"strong_rules": 368, "edges": 44, "focus_degree": 10}


def build_graph():
    """Notebook 05 chart 10's graph, rebuilt from the same input."""
    basket_df = pd.read_csv(BASKET_PATH)

    frequent = fpgrowth(basket_df, min_support=MIN_SUPPORT, use_colnames=True)
    rules = association_rules(frequent, metric="lift", min_threshold=1.0)
    rules = rules.sort_values("lift", ascending=False)

    G = nx.Graph()
    for cat in basket_df.columns:
        G.add_node(cat)

    network_rules = rules[rules["lift"] > LIFT_FLOOR]
    for _, rule in network_rules.iterrows():
        for a in rule["antecedents"]:
            for c in rule["consequents"]:
                if G.has_edge(a, c):
                    G[a][c]["lift"] = max(G[a][c]["lift"], rule["lift"])
                else:
                    G.add_edge(a, c, lift=rule["lift"])

    return G, len(network_rules)


def check(G, strong_rules):
    actual = {
        "strong_rules": strong_rules,
        "edges": G.number_of_edges(),
        "focus_degree": G.degree(FOCUS),
    }
    drifted = [f"  {k}: recomputed {actual[k]}, write-up {v}"
               for k, v in EXPECTED.items() if actual[k] != v]
    if drifted:
        print("WARNING: recomputed values differ from notebook 05's write-up:")
        print("\n".join(drifted))
    else:
        print("[PASS] Rule count, edge count and "
              f"{FOCUS.lower()} degree match the write-up.")
    return actual


def resolve_labels(fig, ax, texts, pos, radii_pts, names):
    """
    Push labels off every node and off each other.

    Works in display space against the labels' real rendered extents, measured
    once (moving a label only translates its box). Each label starts offset
    radially outward from the centre of the layout, so the dense core pushes
    its labels outward rather than piling them up, and a weak spring keeps each
    label near its own node so nothing drifts far from what it names. Node
    positions are never touched.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    half = {}
    for n, t in zip(names, texts):
        bb = t.get_window_extent(renderer)
        half[n] = np.array([bb.width / 2 + 2, bb.height / 2 + 2])

    px_per_pt = fig.dpi / 72.0
    node_px = {n: np.array(ax.transData.transform(pos[n])) for n in names}
    r_px = {n: radii_pts[n] * px_per_pt for n in names}

    centre = np.mean([node_px[n] for n in names], axis=0)
    anchor = {}
    for n in names:
        direction = node_px[n] - centre
        norm = np.linalg.norm(direction)
        direction = direction / norm if norm > 1e-9 else np.array([0.0, -1.0])
        anchor[n] = node_px[n] + direction * (r_px[n] + half[n][1] + 6)

    label_px = {n: anchor[n].copy() for n in names}
    bounds = ax.get_window_extent()

    def separate(a_pos, a_half, b_pos, b_half):
        """Minimum-translation push that clears two axis-aligned boxes."""
        d = a_pos - b_pos
        need = a_half + b_half
        over = need - np.abs(d)
        if over[0] <= 0 or over[1] <= 0:
            return None
        axis = 0 if over[0] < over[1] else 1
        step = np.zeros(2)
        step[axis] = np.sign(d[axis] if d[axis] != 0 else 1.0) * over[axis]
        return step

    for _ in range(400):
        moved = False
        for i, a in enumerate(names):
            for b in names:
                node_half = np.array([r_px[b] + 3, r_px[b] + 3])
                step = separate(label_px[a], half[a], node_px[b], node_half)
                if step is not None:
                    label_px[a] += step * 0.55
                    moved = True
            for b in names[i + 1:]:
                step = separate(label_px[a], half[a], label_px[b], half[b])
                if step is not None:
                    label_px[a] += step * 0.5
                    label_px[b] -= step * 0.5
                    moved = True
        for n in names:
            label_px[n] += (anchor[n] - label_px[n]) * 0.04
            label_px[n] = np.clip(
                label_px[n],
                [bounds.x0 + half[n][0], bounds.y0 + half[n][1]],
                [bounds.x1 - half[n][0], bounds.y1 - half[n][1]],
            )
        if not moved:
            break

    inv = ax.transData.inverted()
    return {n: np.array(inv.transform(label_px[n])) for n in names}, half, r_px


def render(G):
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]

    # Same layout call as the notebook, so no node moves.
    pos = nx.spring_layout(G, k=0.9, seed=42)
    names = list(G.nodes)
    degrees = {n: G.degree(n) for n in names}

    # Radius scales with the number of connections, so the nine-connection
    # nodes are the largest on the chart.
    radii_pts = {n: 4.5 + degrees[n] * 1.5 for n in names}

    fig, ax = plt.subplots(figsize=(12, 9))
    fig.subplots_adjust(left=0.03, right=0.97, top=0.88, bottom=0.10)

    coords = np.array([pos[n] for n in names])
    pad = 0.16
    xlim = (coords[:, 0].min() - pad, coords[:, 0].max() + pad)
    ylim = (coords[:, 1].min() - pad, coords[:, 1].max() + pad)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")

    lifts = np.array([G[u][v]["lift"] for u, v in G.edges])
    lo, hi = lifts.min(), lifts.max()
    for (u, v), lift in zip(G.edges, lifts):
        alpha = 0.28 + 0.72 * (lift - lo) / (hi - lo) if hi > lo else 1.0
        focus_edge = FOCUS in (u, v)
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color=TEAL if focus_edge else EDGE_GREY,
                linewidth=1, alpha=alpha, solid_capstyle="round",
                zorder=3 if focus_edge else 2)

    for n in names:
        is_focus = n == FOCUS
        ax.scatter(*pos[n], s=np.pi * radii_pts[n] ** 2,
                   facecolor=TEAL if is_focus else NODE_FILL,
                   edgecolor=TEAL if is_focus else NODE_EDGE,
                   linewidth=1, zorder=4)

    texts = []
    for n in names:
        is_focus = n == FOCUS
        texts.append(ax.text(*pos[n], n.capitalize(),
                             fontsize=13 if is_focus else 11,
                             color=INK_DARK if is_focus else INK_MUTED,
                             fontweight="bold" if is_focus else "normal",
                             ha="center", va="center", zorder=6))

    label_pos, half_px, r_px = resolve_labels(fig, ax, texts, pos, radii_pts, names)

    # A hairline connector wherever a label had to travel far enough that which
    # node it names would otherwise be ambiguous.
    for n, t in zip(names, texts):
        t.set_position(label_pos[n])

        node_disp = np.array(ax.transData.transform(pos[n]))
        label_disp = np.array(ax.transData.transform(label_pos[n]))
        gap = np.linalg.norm(label_disp - node_disp) - r_px[n] - half_px[n][1]
        if gap > 4:
            direction = (label_disp - node_disp) / np.linalg.norm(label_disp - node_disp)
            start = ax.transData.inverted().transform(node_disp + direction * r_px[n])
            end = ax.transData.inverted().transform(
                label_disp - direction * (half_px[n][1] + 3))
            ax.plot([start[0], end[0]], [start[1], end[1]],
                    color=TEAL if n == FOCUS else NODE_EDGE,
                    linewidth=0.7, zorder=5)

    fig.text(0.03, 0.955, "Category connections from 368 strong rules",
             fontsize=17, fontweight="bold", ha="left", va="bottom")
    fig.text(0.03, 0.918,
             "Cleaning supplies connects otherwise separate shopping missions",
             fontsize=15, color=INK_MUTED, ha="left", va="bottom")

    fig.text(0.03, 0.025,
             "38 unique category to category connections at lift 3.0 or above. "
             "Node size reflects the\nnumber of connections.",
             fontsize=13, color=INK_FAINT, ha="left", va="bottom", linespacing=1.5)

    os.makedirs(FIGURES, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=300)
    plt.close(fig)


def main():
    G, strong_rules = build_graph()

    print(f"Rules with lift > {LIFT_FLOOR}: {strong_rules}")
    print(f"Network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print("\nDegree ranking:")
    for cat, deg in sorted(G.degree(), key=lambda x: (-x[1], x[0])):
        print(f"  {cat:<28} {deg}")

    check(G, strong_rules)

    render(G)
    print(f"\nSaved {os.path.relpath(OUT_PATH, ROOT)}")


if __name__ == "__main__":
    main()
