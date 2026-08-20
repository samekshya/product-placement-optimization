"""Richer features for the basket value classifier.

Extension of notebooks 11 and 12. Those notebooks predict whether a basket is
Small (under Rs 500), Medium (Rs 500 to 2,000) or Large (over Rs 2,000) from
25 binary category-presence flags. Two baskets holding the same categories
look identical on those flags, so the best any model can do on them is the
majority label of each distinct pattern: 71.67 per cent over 17,532 patterns.
The MLP reached 69.05 per cent, 96.3 per cent of that ceiling. This module
asks how far the ceiling and the models move when the basket is described
more fully.

THE 71.67 PER CENT RESULT IS NOT TOUCHED. It is recomputed here on the same
25 flags as a check that the labels, the split and the seed are the ones
notebooks 11 and 12 used, and the two original models are refit on those
flags so their reported accuracies reproduce in the same run before anything
new is trained. The new numbers are a second, separate result on a different
feature set.

FEATURE SETS
    F0  binary      the 25 category flags (notebooks 11 and 12)
    F1  discrete    F0 plus item count (distinct products), category count,
                    day of week (7 one-hot) and month (11 one-hot)
    F2  full        F1 with each binary flag replaced by the quantity bought
                    in that category (presence is recoverable as quantity > 0)

    Hour of day is not available. Every one of the 768,221 timestamps in the
    raw export is exactly 00:00:00, so the source carries the date only.

THE CEILING, SAME METHOD
    Every basket's feature row is turned into a pattern string; within each
    pattern the majority label is the best any model can do; the ceiling is
    the share of baskets whose label matches their pattern's majority. This is
    computed on all 218,037 baskets, exactly as notebook 12 did. It is an
    in-sample bound: as features become richer, patterns become nearly unique
    and the ceiling drifts toward 100 per cent whether or not the extra detail
    is learnable. The number of distinct patterns and the share that occur
    once are reported beside every ceiling so that drift can be seen.

MODELS, SAME LABELS, SAME SPLIT, SAME SEED
    Decision tree, depth 5, random_state 42, on the raw features.
    MLP, hidden layers 64 and 32, the notebook 12 hyperparameters, random
    state 42. The MLP receives one-hot day and month as they are and the
    numeric columns (quantities and counts) log1p-transformed and standardised
    on the training split, because a network trained with adam cannot use
    raw quantities that run from 0.05 to 1,900 alongside 0/1 inputs. The tree
    needs no scaling and gets none.
    Split: train_test_split(test_size=0.30, random_state=42, stratify=labels)
    over baskets in invoice order, which is the notebook 11 and 12 split.

Run:
    python analysis/basket_features.py

Writes:
    dashboard/artifacts/basket_features_summary.json
    reports/figures/chart26_richer_features.png
"""

import json
import os
import sys
import time

import numpy as np
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

CLEANED_CSV = os.environ.get(
    "PP_CLEANED_CSV", os.path.join(_ROOT, "data", "processed", "sales_data_cleaned.csv")
)
ARTIFACTS_DIR = os.environ.get(
    "PP_ARTIFACTS_DIR", os.path.join(_ROOT, "dashboard", "artifacts")
)
FIGURES_DIR = os.path.join(_ROOT, "reports", "figures")
SUMMARY_ARTIFACT = "basket_features_summary.json"
FIGURE_NAME = "chart26_richer_features.png"

RANDOM_STATE = 42
TEST_SIZE = 0.30
SEGMENTS = ["Small", "Medium", "Large"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

MLP_PARAMS = dict(
    hidden_layer_sizes=(64, 32), activation="relu", solver="adam", alpha=1e-4,
    batch_size=256, learning_rate_init=1e-3, max_iter=60, early_stopping=True,
    n_iter_no_change=5, validation_fraction=0.1, random_state=RANDOM_STATE,
)


# ----------------------------------------------------------------------
# labels and features
# ----------------------------------------------------------------------

def basket_segment(value):
    if value < 500:
        return "Small"
    if value <= 2000:
        return "Medium"
    return "Large"


def load_lines(cleaned_csv=CLEANED_CSV):
    df = pd.read_csv(cleaned_csv,
                     usecols=["date", "invoice_no", "product", "category",
                              "quantity", "total_amount"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def build_labels(df):
    """Basket value class per invoice, exactly as notebooks 11 and 12."""
    values = df.groupby("invoice_no")["total_amount"].sum()
    return values.apply(basket_segment)


def build_binary(df):
    """F0: the 25 category-presence flags, invoice order (notebook 12 cell 7)."""
    flags = pd.crosstab(df["invoice_no"], df["category"])
    return (flags > 0).astype(int)


def build_feature_sets(df):
    """Returns labels and the three feature frames, all on the same invoice
    index and in the same order, so the split is identical across sets."""
    labels = build_labels(df)
    binary = build_binary(df)
    binary, labels = binary.align(labels, join="inner", axis=0)

    quantity = pd.pivot_table(df, index="invoice_no", columns="category",
                              values="quantity", aggfunc="sum", fill_value=0.0)
    quantity = quantity.reindex(index=binary.index, columns=binary.columns).fillna(0.0)
    quantity.columns = [f"{c} qty" for c in quantity.columns]

    per_basket = df.groupby("invoice_no").agg(
        n_items=("product", "nunique"),
        n_categories=("category", "nunique"),
        date=("date", "first"),
    ).reindex(binary.index)
    dow = pd.get_dummies(pd.Categorical(per_basket["date"].dt.day_name(),
                                        categories=WEEKDAYS)).astype(int)
    dow.index = binary.index
    dow.columns = [f"dow {d}" for d in WEEKDAYS]
    month_labels = per_basket["date"].dt.strftime("%Y-%m")
    months = sorted(month_labels.unique())
    month = pd.get_dummies(pd.Categorical(month_labels, categories=months)).astype(int)
    month.index = binary.index
    month.columns = [f"month {m}" for m in months]

    extras = pd.concat([per_basket[["n_items", "n_categories"]], dow, month], axis=1)
    discrete = pd.concat([binary, extras], axis=1)
    full = pd.concat([quantity, extras], axis=1)
    return labels, {"binary": binary, "discrete": discrete, "full": full}


def split_indices(labels):
    from sklearn.model_selection import train_test_split
    positions = np.arange(len(labels))
    tr, te = train_test_split(positions, test_size=TEST_SIZE,
                              random_state=RANDOM_STATE, stratify=labels)
    return tr, te


# ----------------------------------------------------------------------
# the ceiling, same method as notebook 12
# ----------------------------------------------------------------------

def ceiling(features, labels):
    """Share of baskets whose label is the majority label of their exact
    feature pattern. Notebook 12 cell 23, applied to any feature frame.

    Notebook 12 built the pattern as a string per row; this groups identical
    rows with numpy.unique instead, which is the same partition of baskets
    (exact row equality) and runs in about a second rather than forty. On the
    25 binary flags both give 17,532 patterns and 71.67 per cent.
    """
    arr = np.ascontiguousarray(features.to_numpy(dtype=np.float64))
    _, inverse, counts = np.unique(arr, axis=0, return_inverse=True, return_counts=True)
    inverse = np.asarray(inverse).ravel()
    codes = pd.Categorical(labels.values, categories=SEGMENTS).codes
    table = np.zeros((len(counts), len(SEGMENTS)), dtype=np.int64)
    np.add.at(table, (inverse, codes), 1)
    return {
        "ceiling": float(table.max(axis=1).sum() / len(arr)),
        "distinct_patterns": int(len(counts)),
        "singleton_patterns": int((counts == 1).sum()),
        "singleton_basket_share": float((counts == 1).sum() / len(arr)),
        "n_features": int(features.shape[1]),
    }


def pattern_lookup(features, labels, train_idx, test_idx):
    """The ceiling's out-of-sample twin: predict each test basket with the
    training-majority label of its exact pattern, or the overall training
    majority when the pattern never occurred in training. Shows how much of
    an in-sample ceiling survives contact with unseen baskets."""
    arr = np.ascontiguousarray(features.to_numpy(dtype=np.float64))
    _, inverse = np.unique(arr, axis=0, return_inverse=True)
    inverse = np.asarray(inverse).ravel()
    codes = pd.Categorical(labels.values, categories=SEGMENTS).codes
    table = np.zeros((inverse.max() + 1, len(SEGMENTS)), dtype=np.int64)
    np.add.at(table, (inverse[train_idx], codes[train_idx]), 1)
    seen = table.sum(axis=1) > 0
    majority = int(np.bincount(codes[train_idx]).argmax())
    pred = np.where(seen[inverse[test_idx]], table.argmax(axis=1)[inverse[test_idx]], majority)
    return {
        "test_accuracy": float((pred == codes[test_idx]).mean()),
        "test_baskets_with_unseen_pattern": float((~seen[inverse[test_idx]]).mean()),
    }


# ----------------------------------------------------------------------
# models
# ----------------------------------------------------------------------

def fit_tree(X_train, y_train, X_test, y_test):
    from sklearn.metrics import accuracy_score, confusion_matrix
    from sklearn.tree import DecisionTreeClassifier
    tree = DecisionTreeClassifier(max_depth=5, random_state=RANDOM_STATE)
    tree.fit(X_train, y_train)
    pred = tree.predict(X_test)
    cm = confusion_matrix(y_test, pred, labels=SEGMENTS)
    importances = pd.Series(tree.feature_importances_, index=X_train.columns)
    importances = importances.sort_values(ascending=False)
    return {
        "accuracy": float(accuracy_score(y_test, pred)),
        "leaves": int(tree.get_n_leaves()),
        "recall": {s: float(cm[i, i] / cm[i].sum()) for i, s in enumerate(SEGMENTS)},
        "importances": {k: float(v) for k, v in importances.items() if v > 0},
        "n_features_used": int((importances > 0).sum()),
    }, tree


def _mlp_matrix(frame, numeric_cols, scaler=None):
    """One-hot columns pass through; numeric columns are log1p'd and standardised."""
    from sklearn.preprocessing import StandardScaler
    X = frame.copy().astype(float)
    if numeric_cols:
        X[numeric_cols] = np.log1p(X[numeric_cols])
        if scaler is None:
            scaler = StandardScaler().fit(X[numeric_cols])
        X[numeric_cols] = scaler.transform(X[numeric_cols])
    return X.to_numpy(), scaler


def fit_mlp(X_train, y_train, X_test, y_test, numeric_cols):
    from sklearn.metrics import accuracy_score, confusion_matrix
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import LabelEncoder
    enc = LabelEncoder().fit(SEGMENTS)
    Xtr, scaler = _mlp_matrix(X_train, numeric_cols)
    Xte, _ = _mlp_matrix(X_test, numeric_cols, scaler)
    t0 = time.time()
    mlp = MLPClassifier(**MLP_PARAMS)
    mlp.fit(Xtr, enc.transform(y_train))
    seconds = time.time() - t0
    pred = enc.inverse_transform(mlp.predict(Xte))
    cm = confusion_matrix(y_test, pred, labels=SEGMENTS)
    n_params = int(sum(w.size for w in mlp.coefs_) + sum(b.size for b in mlp.intercepts_))
    return {
        "accuracy": float(accuracy_score(y_test, pred)),
        "parameters": n_params,
        "epochs": int(mlp.n_iter_),
        "recall": {s: float(cm[i, i] / cm[i].sum()) for i, s in enumerate(SEGMENTS)},
        "scaled_columns": len(numeric_cols),
    }, mlp, seconds


def numeric_columns(frame):
    return [c for c in frame.columns
            if not (c.startswith("dow ") or c.startswith("month "))]


# ----------------------------------------------------------------------
# the study
# ----------------------------------------------------------------------

def run(df, log=print):
    labels, sets = build_feature_sets(df)
    tr, te = split_indices(labels)
    y_train, y_test = labels.iloc[tr], labels.iloc[te]
    baseline = float(y_test.value_counts(normalize=True).max())
    log(f"Baskets {len(labels):,}: train {len(tr):,}, test {len(te):,}; "
        f"majority baseline {baseline * 100:.2f}%")

    out = {"feature_sets": {}, "ceilings": {}, "models": {}}
    for name, frame in sets.items():
        cols = list(frame.columns)
        out["feature_sets"][name] = {"n_features": len(cols), "columns": cols}
        c = ceiling(frame, labels)
        c["pattern_lookup"] = pattern_lookup(frame, labels, tr, te)
        out["ceilings"][name] = c
        log(f"  {name:8} {c['n_features']:3} features  ceiling {c['ceiling'] * 100:6.2f}%  "
            f"patterns {c['distinct_patterns']:,} (singletons {c['singleton_basket_share'] * 100:.1f}% of baskets); "
            f"pattern lookup out of sample {c['pattern_lookup']['test_accuracy'] * 100:.2f}% "
            f"with {c['pattern_lookup']['test_baskets_with_unseen_pattern'] * 100:.1f}% unseen")

    for name, frame in sets.items():
        X_train, X_test = frame.iloc[tr], frame.iloc[te]
        t0 = time.time()
        tree_res, _ = fit_tree(X_train, y_train, X_test, y_test)
        mlp_res, _, mlp_seconds = fit_mlp(
            X_train, y_train, X_test, y_test,
            numeric_columns(frame) if name != "binary" else [])
        log(f"  {name:8} fitted in {time.time() - t0:.0f}s "
            f"(MLP {mlp_res['epochs']} epochs, {mlp_seconds:.1f}s)")
        ceil = out["ceilings"][name]["ceiling"]
        for model, res in (("tree_depth5", tree_res), ("mlp", mlp_res)):
            res["share_of_ceiling"] = res["accuracy"] / ceil
            out["models"][f"{name}_{model}"] = res
            log(f"  {name:8} {model:11} accuracy {res['accuracy'] * 100:6.2f}%  "
                f"= {res['share_of_ceiling'] * 100:5.1f}% of the {ceil * 100:.2f}% ceiling")

    imp_new = out["models"]["full_tree_depth5"]["importances"]
    imp_old = out["models"]["binary_tree_depth5"]["importances"]
    ranked_new = list(imp_new)
    out["feature_importance"] = {
        "old_top": list(imp_old)[:5],
        "old_top_values": {k: imp_old[k] for k in list(imp_old)[:5]},
        "new_top": ranked_new[:10],
        "new_top_values": {k: imp_new[k] for k in ranked_new[:10]},
        "cooking_oil_new_rank": (ranked_new.index("COOKING OIL qty") + 1
                                 if "COOKING OIL qty" in ranked_new else None),
        "cooking_oil_new_importance": imp_new.get("COOKING OIL qty", 0.0),
        "rice_new_rank": (ranked_new.index("RICE qty") + 1
                          if "RICE qty" in ranked_new else None),
        "rice_new_importance": imp_new.get("RICE qty", 0.0),
        "new_features_in_top_5": [f for f in ranked_new[:5]
                                  if not f.endswith(" qty")],
        "displaced": ranked_new[0] not in ("COOKING OIL qty", "RICE qty"),
    }
    out["split"] = {"train_baskets": int(len(tr)), "test_baskets": int(len(te)),
                    "test_size": TEST_SIZE, "random_state": RANDOM_STATE,
                    "stratified": True, "majority_baseline": baseline}
    out["labels"] = {s: int((labels == s).sum()) for s in SEGMENTS}
    out["hour_of_day"] = {
        "available": False,
        "why": "every timestamp in the raw export is 00:00:00; the source records the date only",
    }
    return out


# ----------------------------------------------------------------------
# chart
# ----------------------------------------------------------------------

def draw_chart(summary, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ink, muted, grid = "#1f1f1f", "#6b6b6b", "#e6e6e6"
    c_tree, c_mlp, c_ceil = "#2a78d6", "#eb6834", "#8a8a8a"
    m = summary["models"]
    ce = summary["ceilings"]

    fig, axes = plt.subplots(1, 2, figsize=(15, 6.2), gridspec_kw={"width_ratios": [1, 1.15]})

    ax = axes[0]
    sets = [("binary", "25 binary flags\n(notebooks 11 and 12)"),
            ("discrete", "flags + counts\n+ day + month"),
            ("full", "quantities + counts\n+ day + month")]
    x = np.arange(len(sets))
    w = 0.34
    tree_acc = [m[f"{k}_tree_depth5"]["accuracy"] * 100 for k, _ in sets]
    mlp_acc = [m[f"{k}_mlp"]["accuracy"] * 100 for k, _ in sets]
    ceils = [ce[k]["ceiling"] * 100 for k, _ in sets]
    b1 = ax.bar(x - w / 2, tree_acc, w, color=c_tree, label="Decision tree, depth 5")
    b2 = ax.bar(x + w / 2, mlp_acc, w, color=c_mlp, label="MLP 64-32")
    for i, c in enumerate(ceils):
        ax.hlines(c, x[i] - 0.45, x[i] + 0.45, color=c_ceil, linestyle="--", linewidth=1.5)
        ax.text(x[i] - 0.45, c + 0.7, f"ceiling {c:.2f}%", va="bottom", ha="left",
                fontsize=8.5, color=muted)
    for bars in (b1, b2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.6,
                    f"{bar.get_height():.2f}", ha="center", va="bottom", fontsize=9, color=ink)
    ax.axhline(summary["split"]["majority_baseline"] * 100, color=muted, linewidth=1,
               linestyle=":")
    ax.text(-0.45, summary["split"]["majority_baseline"] * 100 + 0.5,
            f"majority baseline {summary['split']['majority_baseline'] * 100:.2f}%",
            fontsize=8.5, color=muted)
    ax.set_xticks(x)
    ax.set_xticklabels([lab for _, lab in sets], fontsize=9.5)
    ax.set_ylim(40, 102)
    ax.set_xlim(-0.6, len(sets) - 0.2)
    ax.set_ylabel("Accuracy on 65,412 unseen test baskets (%)")
    ax.set_title("Accuracy and ceiling by feature set", loc="left", fontsize=11, color=ink)
    ax.legend(loc="upper left", frameon=False, fontsize=9)

    ax = axes[1]
    fi = summary["feature_importance"]
    names = [n for n in fi["new_top"][:10] if fi["new_top_values"][n] >= 0.0005][::-1]
    vals = [fi["new_top_values"][n] for n in names]
    colours = [c_mlp if not n.endswith(" qty") else c_tree for n in names]
    ax.barh([n.replace(" qty", " (quantity)") for n in names], vals, color=colours, height=0.6)
    for i, v in enumerate(vals):
        ax.text(v + 0.004, i, f"{v:.3f}", va="center", fontsize=9, color=ink)
    old = summary["feature_importance"]["old_top_values"]
    ax.set_title("Depth-5 tree on the full feature set: every feature it uses\n"
                 f"(old tree: COOKING OIL {old.get('COOKING OIL', 0):.3f}, "
                 f"RICE {old.get('RICE', 0):.3f})", loc="left", fontsize=11, color=ink)
    ax.set_xlabel("Gini importance")
    ax.set_xlim(0, max(vals) * 1.25)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=c_tree, label="category quantity"),
                       Patch(color=c_mlp, label="new basket-level feature")],
              loc="lower right", frameon=False, fontsize=9)

    for ax in axes:
        ax.grid(axis="y" if ax is axes[0] else "x", color=grid, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.spines["left"].set_color(muted)
        ax.spines["bottom"].set_color(muted)
        ax.tick_params(colors=muted, labelsize=9)
    fig.text(0.01, 0.005,
             "Chart 26. Same labels, same 152,625 / 65,412 split, same seed as notebooks 11 and 12. "
             "Ceilings are the pattern-majority bound; with quantities most patterns are unique, so that bound stops binding.",
             fontsize=8.5, color=muted)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# ----------------------------------------------------------------------
# entry point
# ----------------------------------------------------------------------

def _serialisable(obj):
    if isinstance(obj, dict):
        return {k: _serialisable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialisable(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        return round(float(obj), 6)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def main():
    t0 = time.time()
    df = load_lines()
    print(f"Loaded {len(df):,} line items in {time.time() - t0:.0f}s")
    summary = run(df)
    os.makedirs(FIGURES_DIR, exist_ok=True)
    fig_path = draw_chart(summary, os.path.join(FIGURES_DIR, FIGURE_NAME))
    out_path = os.path.join(ARTIFACTS_DIR, SUMMARY_ARTIFACT)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(_serialisable(summary), fh, indent=2)
    print(f"Wrote {os.path.relpath(out_path, _ROOT)} and {os.path.relpath(fig_path, _ROOT)}")
    fi = summary["feature_importance"]
    print(f"\nNew tree top 5: {fi['new_top'][:5]}")
    print(f"COOKING OIL quantity rank {fi['cooking_oil_new_rank']} "
          f"({fi['cooking_oil_new_importance']:.3f}); RICE quantity rank {fi['rice_new_rank']} "
          f"({fi['rice_new_importance']:.3f}); displaced from the top: {fi['displaced']}")
    print(f"({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
