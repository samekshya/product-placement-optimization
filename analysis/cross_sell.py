"""Cross-sell capture scoring. Single source of truth.

This module is the ONE implementation of the cross-sell capture metric that
answers RQ1 in the dissertation. It is imported by:

    dashboard/precompute_artifacts.py   produces cross_sell_summary.json,
                                        the figures quoted in the thesis
    app/api/main.py                     serves the interactive shelf tool

Because both call the same function, the tool cannot report a different number
from the dissertation. That is the point of this file existing.

THE METRIC
A strong cross-sell rule is one with lift >= 3.0. A rule is *captured* by a
layout when every category in the rule, antecedent and consequent together,
sits inside a single zone of that layout, so the products are next to each
other and the cross-sell can physically happen. A layout is scored by how many
strong rules it captures and by how much of the total strong-rule support those
captured rules represent.

Verified figures this module reproduces (see cross_sell_summary.json):
    existing frequency-driven layout   22 rules, 0.2778 support,  5.7%
    re-derived five-zone layout       180 rules, 2.6614 support, 54.1%
    out of 368 strong rules totalling 4.9157 support
"""

STRONG_LIFT_FLOOR = 3.0

# The five placement zones, RE-DERIVED 17 August 2026 from the post-remap
# association rules by analysis.optimise_zones, capacity-matched and certified
# against exhaustive enumeration. Membership and the reasoning behind the zone
# sizes live in analysis/zones.py; this dict is the same content keyed by a
# descriptive title. It is the research finding itself, so it lives here rather
# than being duplicated per consumer.
OPTIMISED_ZONES = {
    "Zone 1: Anchor Cluster": [
        "FOOD STAPLES", "CANNED AND PACKAGED FOODS", "CLEANING SUPPLIES",
        "TEA AND SPICES", "PERSONAL CARE", "COOKING OIL",
    ],
    "Zone 2: Impulse at the Entrance": [
        "CONFECTIONERY", "SNACKS", "NOODLES", "HOUSEHOLD ITEMS",
        "POOJA ITEMS",
    ],
    "Zone 3: Destination Side Aisle": [
        "BISCUITS AND COOKIES", "BABY CARE", "STATIONERY",
    ],
    "Zone 4: Dairy and Fresh": [
        "DAIRY PRODUCTS", "FROZEN FOODS", "FRESH PRODUCE", "BAKERY",
    ],
    "Zone 5: Speciality and Restricted": [
        "RICE", "ALCOHOLIC BEVERAGES", "CIGARETTE AND TOBACCO",
        "SOFT DRINKS AND JUICES", "BREAKFAST CEREALS",
        "ELECTRICAL SUPPLIES", "PARTY SUPPLIES",
    ],
}


def captured(cats, groups):
    """True when every category of a rule sits inside one group of the layout.

    cats:   set of category names making up the rule
    groups: sequence of sets, one per zone
    """
    return any(cats <= g for g in groups)


def score_layout(rules, groups, total_support=None):
    """Score a layout by the strong-rule support it co-locates.

    rules:  sequence of mappings, each with
              'cats'    set of category names in the rule
              'support' float
            Anything else on the mapping is carried through untouched, so a
            caller can attach lift or the original text and get it back in the
            captured and uncaptured lists.
    groups: sequence of sets, one per zone.
    total_support: denominator for capture_rate. Summed from rules when omitted.

    Returns a dict. rules_captured and support_captured are the two figures the
    dissertation quotes; capture_rate is the percentage derived from them.
    """
    rules = list(rules)

    if total_support is None:
        total_support = float(sum(r["support"] for r in rules))

    captured_rules = []
    uncaptured_rules = []
    support_captured = 0.0

    for rule in rules:
        if captured(rule["cats"], groups):
            captured_rules.append(rule)
            support_captured += float(rule["support"])
        else:
            uncaptured_rules.append(rule)

    capture_rate = (support_captured / total_support * 100.0) if total_support else 0.0

    return {
        "rules_captured": len(captured_rules),
        "support_captured": support_captured,
        "capture_rate": capture_rate,
        "total_rules": len(rules),
        "total_support": total_support,
        "captured": captured_rules,
        "uncaptured": uncaptured_rules,
    }


def groups_from_assignment(assignment):
    """Turn a {category: zone} mapping into the list of sets score_layout wants.

    Zones with no categories are dropped, since an empty zone cannot contain a
    rule and would only add a useless empty set to every subset test.
    """
    by_zone = {}
    for category, zone in assignment.items():
        by_zone.setdefault(zone, set()).add(category)
    return [cats for cats in by_zone.values() if cats]


def optimised_groups():
    """The proposed five-zone layout as a list of sets."""
    return [set(v) for v in OPTIMISED_ZONES.values()]
