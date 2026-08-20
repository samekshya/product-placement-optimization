"""Layout loading and scoring, built on the shared analysis module.

Nothing in this file reimplements the cross-sell metric. It loads layouts,
calls analysis.cross_sell.score_layout, and shapes the result for the UI.
"""

import functools

import artifacts
from analysis import optimise_zones
from analysis import zones as zone_defs
from analysis.cross_sell import (
    STRONG_LIFT_FLOOR,
    groups_from_assignment,
    score_layout,
)


def _rule_label(rule):
    """Human readable rule name, so the UI can name rules rather than count them."""
    ant = ", ".join(sorted(rule["antecedents"]))
    con = ", ".join(sorted(rule["consequents"]))
    return f"{ant} -> {con}"


def strong_rules():
    """The strong rules, in the shape score_layout expects, plus display fields."""
    out = []
    for rule in artifacts.load_strong_rules():
        out.append({
            "cats": rule["antecedents"] | rule["consequents"],
            "support": rule["support"],
            "lift": rule["lift"],
            "confidence": rule["confidence"],
            "antecedents": sorted(rule["antecedents"]),
            "consequents": sorted(rule["consequents"]),
            "label": _rule_label(rule),
        })
    return out


def total_strong_support():
    return float(sum(r["support"] for r in strong_rules()))


def proposed_assignment():
    return zone_defs.proposed_assignment()


def existing_assignment():
    """The frequency-driven baseline, from the committed clustering artifact.

    The five k-means frequency clusters map onto the five physical zones in
    cluster order. The mapping is arbitrary because those clusters carry no
    location meaning: what matters for scoring is only which categories share
    a zone, not which zone they share.
    """
    rows = artifacts.load_cluster_assignments()
    clusters = sorted({int(r["frequency_cluster"]) for r in rows})
    cluster_to_zone = {
        c: zone_defs.ZONE_IDS[i % len(zone_defs.ZONE_IDS)]
        for i, c in enumerate(clusters)
    }
    return {r["category"]: cluster_to_zone[int(r["frequency_cluster"])] for r in rows}


@functools.lru_cache(maxsize=4)
def optimal_result(constrained, capacity_matched=False):
    """The best computed assignment, from the shared optimiser.

    Read from dashboard/artifacts/zone_optimisation.json when it exists, the
    file analysis/optimise_zones.py writes and the verification sweep checks,
    so the tool serves exactly the figures the dissertation reports. If the
    artifact is absent the search runs here instead (deterministic, fixed
    seed), without the exhaustive certificate, and the result is cached.
    """
    stored = artifacts.load_zone_optimisation()
    key = ("capacity_" if capacity_matched else "") + (
        "constrained" if constrained else "unconstrained")
    if stored is not None and key in stored:
        return stored[key]
    rules = [{"cats": r["cats"], "support": r["support"]} for r in strong_rules()]
    return optimise_zones.study_optimum(
        rules,
        proposed_assignment(),
        constrained=constrained,
        capacity_matched=capacity_matched,
        certify=False,
    )


def zones_payload():
    """Zone definitions including the ethics classification for the UI."""
    return [
        {
            "id": z["id"],
            "name": z["name"],
            "location": z["location"],
            "role": z["role"],
            "ethics": z["ethics"],
            "ethics_label": zone_defs.ETHICS_LABEL[z["ethics"]],
            "ethics_explanation": zone_defs.ETHICS_EXPLANATION[z["ethics"]],
        }
        for z in zone_defs.ZONES
    ]


def _capturing_zone(cats, assignment):
    """Which zone holds every category of a captured rule.

    A captured rule sits entirely in one zone by definition, so the zone of any
    one of its categories identifies it.
    """
    for c in cats:
        if c in assignment:
            return assignment[c]
    return None


def score(assignment):
    """Score a {category: zone_id} assignment.

    Returns the figures the dissertation quotes, the captured and uncaptured
    rules by name, and the ethics split of the captured rules.
    """
    rules = strong_rules()
    total = float(sum(r["support"] for r in rules))
    groups = groups_from_assignment(assignment)

    result = score_layout(rules, groups, total)

    captured = []
    ethics_counts = {zone_defs.ASSISTS: 0, zone_defs.CREATES: 0}
    for rule in result["captured"]:
        zone_id = _capturing_zone(rule["cats"], assignment)
        ethics = zone_defs.ethics_of(zone_id)
        ethics_counts[ethics] += 1
        captured.append({
            "label": rule["label"],
            "antecedents": rule["antecedents"],
            "consequents": rule["consequents"],
            "support": rule["support"],
            "lift": rule["lift"],
            "zone_id": zone_id,
            "ethics": ethics,
        })

    uncaptured = [{
        "label": r["label"],
        "antecedents": r["antecedents"],
        "consequents": r["consequents"],
        "support": r["support"],
        "lift": r["lift"],
    } for r in result["uncaptured"]]

    captured.sort(key=lambda r: r["support"], reverse=True)
    uncaptured.sort(key=lambda r: r["support"], reverse=True)

    return {
        "rules_captured": result["rules_captured"],
        "support_captured": round(result["support_captured"], 4),
        "capture_rate": round(result["capture_rate"], 2),
        "total_strong_rules": result["total_rules"],
        "total_strong_support": round(result["total_support"], 4),
        "lift_floor": STRONG_LIFT_FLOOR,
        "ethics": {
            "assists": ethics_counts[zone_defs.ASSISTS],
            "creates": ethics_counts[zone_defs.CREATES],
            "assists_label": zone_defs.ETHICS_LABEL[zone_defs.ASSISTS],
            "creates_label": zone_defs.ETHICS_LABEL[zone_defs.CREATES],
        },
        "captured_rules": captured,
        "uncaptured_rules": uncaptured,
    }
