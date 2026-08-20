"""Read-only access to the committed analysis artifacts.

The app never recomputes the analysis. It reads what the notebooks and
precompute_artifacts.py already produced, so the tool and the dissertation
cannot drift apart.

Artifact location is resolved from PP_ARTIFACTS_DIR when set (Docker mounts it
at /data/artifacts), otherwise from the repository layout, so the same code runs
in a container and from a local shell.
"""

import csv
import functools
import json
import os
from pathlib import Path

def _default_artifacts_dir():
    """Repo relative artifacts path, used only when PP_ARTIFACTS_DIR is unset.

    Guarded on purpose. Running from the repo this file is at
    app/api/artifacts.py and parents[2] is the repo root, but in the container
    it is at /app/artifacts.py, which has no grandparent, and an unguarded
    parents[2] raises IndexError at import time before the environment variable
    is ever consulted.
    """
    here = Path(__file__).resolve()
    try:
        return here.parents[2] / "dashboard" / "artifacts"
    except IndexError:
        return Path("/data/artifacts")


ARTIFACTS_DIR = Path(os.environ.get("PP_ARTIFACTS_DIR") or _default_artifacts_dir())

STRONG_LIFT_FLOOR = 3.0


def artifact_path(name):
    return ARTIFACTS_DIR / name


def _read_csv(name):
    path = artifact_path(name)
    if not path.exists():
        raise FileNotFoundError(
            f"Artifact not found: {path}. Set PP_ARTIFACTS_DIR or run "
            f"python dashboard/precompute_artifacts.py to build the artifacts."
        )
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _read_json(name):
    path = artifact_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Artifact not found: {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def parse_itemset(value):
    """Turn a stored antecedent or consequent back into a set of categories.

    precompute_artifacts.py writes these with:
        ", ".join(sorted(list(frozenset)))
    so splitting on the comma is the exact inverse.

    This function exists as its own named thing because the obvious shortcut is
    wrong in a way that fails silently. In the pipeline the values are real
    frozensets, so set(value) yields the categories. Applied to the stored
    string, set(value) yields a set of individual CHARACTERS, and every
    downstream subset test then quietly returns the wrong answer instead of
    raising.
    """
    return {part.strip() for part in value.split(",") if part.strip()}


@functools.lru_cache(maxsize=1)
def load_zone_optimisation():
    """The computed zone assignment comparison written by
    analysis/optimise_zones.py (zone_optimisation.json). Returns None when the
    artifact has not been generated, so callers can fall back to computing."""
    path = artifact_path("zone_optimisation.json")
    if not path.exists():
        return None
    return _read_json("zone_optimisation.json")


@functools.lru_cache(maxsize=1)
def load_rules():
    """All mined category rules, with itemsets parsed into sets."""
    rows = []
    for row in _read_csv("category_rules.csv"):
        rows.append({
            "antecedents": parse_itemset(row["antecedents"]),
            "consequents": parse_itemset(row["consequents"]),
            "support": float(row["support"]),
            "confidence": float(row["confidence"]),
            "lift": float(row["lift"]),
        })
    return rows


@functools.lru_cache(maxsize=1)
def load_strong_rules():
    """Rules at or above the strong cross-sell threshold of lift 3.0."""
    return [r for r in load_rules() if r["lift"] >= STRONG_LIFT_FLOOR]


@functools.lru_cache(maxsize=1)
def load_category_stats():
    """Basket penetration per category.

    Revenue share is deliberately absent: it is not in the committed artifacts,
    only in the warehouse view warehouse.v_category_performance. Serving it here
    would make the app depend on a running database, which would break the
    clean clone case the dashboard already supports.
    """
    stats = {}
    for row in _read_csv("category_distribution.csv"):
        stats[row["category"]] = {
            "baskets": int(row["baskets"]),
            "basket_penetration_pct": float(row["pct_of_baskets"]),
        }
    return stats


@functools.lru_cache(maxsize=1)
def load_categories():
    """The 25 categories, with penetration and whether any strong rule uses them.

    The rule flag matters for the UI: 13 of the 25 categories appear in no
    STRONG rule, so moving them between zones can never change the score.
    Without saying so, the tool looks broken when the owner moves one and
    nothing happens. (Only 5 appear in no rule at any lift; the strong
    threshold of 3.0 excludes 8 more.)
    """
    stats = load_category_stats()
    in_strong = set()
    for rule in load_strong_rules():
        in_strong |= rule["antecedents"] | rule["consequents"]

    names = sorted({row["category"] for row in _read_csv("cluster_assignments.csv")})
    out = []
    for name in names:
        s = stats.get(name, {})
        out.append({
            "name": name,
            "baskets": s.get("baskets"),
            "basket_penetration_pct": s.get("basket_penetration_pct"),
            "appears_in_strong_rules": name in in_strong,
        })
    return out


@functools.lru_cache(maxsize=1)
def load_cluster_assignments():
    """The k-means cluster assignments, used for the existing baseline layout."""
    return _read_csv("cluster_assignments.csv")


@functools.lru_cache(maxsize=1)
def load_cross_sell_summary():
    """The committed cross-sell figures, used to pin the scorer against drift."""
    return _read_json("cross_sell_summary.json")
