"""Tests for the computed zone assignment (analysis/optimise_zones.py).

The optimiser's job is to answer one question honestly: what is the best
assignment of categories to zones under score_layout, and how does the
hand-built layout compare. These tests pin the answers, the constraints and
the reproducibility guarantees.

Run:
    venv/Scripts/python -m pytest analysis/tests/ -v      (from the repo root)
"""

import json
import os
import random
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis import cross_sell, optimise_zones as O, zones as Z  # noqa: E402

# The published figures, written as literals on purpose so a regenerated
# artifact cannot quietly move the target.
# Re-pinned 2026-08-17 after the audited category remap and the zone
# re-derivation. The "hand-built" reference IS now the re-derived layout, so it
# equals the capacity-matched CONSTRAINED optimum.
HAND_RULES, HAND_SUPPORT, HAND_RATE = 180, 2.661, 54.1
TOTAL_RULES, TOTAL_SUPPORT = 368, 4.9157
CAPACITY_RULES, CAPACITY_SUPPORT, CAPACITY_RATE = 286, 3.9878, 81.1
CAPACITY_CONSTRAINED_RULES, CAPACITY_CONSTRAINED_SUPPORT = 180, 2.6614
RULES_AFTER_TWO_MOVES = 316


@pytest.fixture(scope="module")
def rules():
    return O.strong_rules_from_artifacts()


@pytest.fixture(scope="module")
def base():
    return Z.proposed_assignment()


@pytest.fixture(scope="module")
def capacities(base):
    caps = {z: 0 for z in Z.ZONE_IDS}
    for z in base.values():
        caps[z] += 1
    return caps


@pytest.fixture(scope="module")
def artifact():
    path = Path(O.default_artifacts_dir()) / O.ARTIFACT_NAME
    if not path.exists():
        pytest.skip("zone_optimisation.json not generated; run analysis/optimise_zones.py")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def test_strong_rule_population(rules):
    assert len(rules) == TOTAL_RULES
    assert round(sum(r["support"] for r in rules), 4) == TOTAL_SUPPORT


def test_hand_built_layout_scores_as_the_dissertation(rules, base):
    r = cross_sell.score_layout(rules, cross_sell.groups_from_assignment(base))
    assert r["rules_captured"] == HAND_RULES
    assert round(r["support_captured"], 3) == HAND_SUPPORT
    assert round(r["capture_rate"], 1) == HAND_RATE


def test_optimiser_uses_the_shared_scorer():
    """No second scorer. The module must score through analysis.cross_sell."""
    assert O.score_layout is cross_sell.score_layout
    assert O.groups_from_assignment is cross_sell.groups_from_assignment


def test_only_fourteen_categories_can_move_the_score(rules):
    rb = O.rule_bearing_categories(rules)
    assert len(rb) == 14
    assert "FOOD STAPLES" in rb and "DAIRY PRODUCTS" in rb


def test_which_constrained_categories_are_rule_bearing(rules):
    """DAIRY PRODUCTS (cold zone) and RICE (heavy goods) both carry strong
    rules, so the locks are no longer free. Their price is pinned by
    test_constraints_cost_rules_once_capacity_is_fixed."""
    rb = O.rule_bearing_categories(rules)
    constrained = set(O.LOCKED) | set(O.FORBIDDEN)
    assert constrained & set(rb) == {"DAIRY PRODUCTS", "RICE"}


def test_unconstrained_optimum_captures_every_rule(rules, base):
    res = O.study_optimum(rules, base, constrained=False, restarts=3, seed=42)
    assert res["rules_captured"] == TOTAL_RULES
    assert round(res["capture_rate"], 1) == 100.0
    assert res["local_search_is_exact"]
    assert res["exact_optimum_rules"] == TOTAL_RULES


def test_constraints_cost_almost_nothing_with_unlimited_zone_sizes(rules):
    """With no capacity limit the locks cost only the 2 rules that would need
    DAIRY PRODUCTS or RICE in the same zone as the anchor cluster.

    Uses the exhaustive certificate rather than study_optimum: the capacity
    optimum is reached by only about a fifth of random restarts, so a handful
    of restarts would make this assertion flaky.
    """
    free = O.exact_optimum(rules, Z.ZONE_IDS)
    bound = O.exact_optimum(rules, Z.ZONE_IDS, locked=O.LOCKED,
                            forbidden=O.FORBIDDEN)
    assert free["rules_captured"] == TOTAL_RULES
    assert free["rules_captured"] - bound["rules_captured"] == 2


def test_constraints_cost_rules_once_capacity_is_fixed(rules, capacities):
    """The finding that replaced "the constraints cost nothing": holding the
    zones to their real sizes, the locks cost 106 of 368 rules, because three
    locked categories occupy slots in the 7-slot perimeter zone."""
    free = O.exact_optimum(rules, Z.ZONE_IDS, capacities=capacities)
    bound = O.exact_optimum(rules, Z.ZONE_IDS, locked=O.LOCKED,
                            forbidden=O.FORBIDDEN, capacities=capacities)
    assert free["rules_captured"] == CAPACITY_RULES
    assert bound["rules_captured"] == CAPACITY_CONSTRAINED_RULES
    assert free["rules_captured"] - bound["rules_captured"] == 106


def test_constraints_are_respected(rules, base):
    res = O.study_optimum(rules, base, constrained=True, capacity_matched=True,
                          restarts=3, seed=42, certify=False)
    a = res["assignment"]
    assert set(a) == set(base)
    for c, z in O.LOCKED.items():
        assert a[c] == z
    for c, banned in O.FORBIDDEN.items():
        assert a[c] not in banned
    counts = {z: 0 for z in Z.ZONE_IDS}
    for z in a.values():
        counts[z] += 1
    for z in Z.ZONE_IDS:
        assert counts[z] == sum(1 for c in base if base[c] == z)


def test_capacity_matched_exact_optimum(rules, capacities):
    """The exhaustive certificate: with the hand-built zone sizes the best
    any layout can do is 286 rules, 3.9878 support, 81.1 per cent."""
    exact = O.exact_optimum(rules, Z.ZONE_IDS, capacities=capacities)
    assert exact["rules_captured"] == CAPACITY_RULES
    assert round(exact["support_captured"], 4) == CAPACITY_SUPPORT
    assert round(exact["capture_rate"], 1) == CAPACITY_RATE
    # Since the 2026-08-17 re-derivation the constrained optimum is strictly
    # worse than the unconstrained one: the locks cost 106 rules.
    exact_c = O.exact_optimum(rules, Z.ZONE_IDS, locked=O.LOCKED,
                              forbidden=O.FORBIDDEN, capacities=capacities)
    assert exact_c["rules_captured"] == CAPACITY_CONSTRAINED_RULES
    assert round(exact_c["support_captured"], 4) == CAPACITY_CONSTRAINED_SUPPORT


def test_capacity_matched_optimum_seven_slot_zone(rules, capacities):
    """The 286-rule optimum puts these seven in the one 7-slot zone. Since
    the 2026-08-17 remap BISCUITS AND COOKIES is in and HOUSEHOLD ITEMS is
    out, relative to the pre-remap core-plus-two."""
    exact = O.exact_optimum(rules, Z.ZONE_IDS, capacities=capacities)
    core = exact["core_assignment"]
    seven = {"FOOD STAPLES", "COOKING OIL", "CLEANING SUPPLIES", "TEA AND SPICES",
             "BISCUITS AND COOKIES", "CANNED AND PACKAGED FOODS", "PERSONAL CARE"}
    zones_of_seven = {core[c] for c in seven}
    assert len(zones_of_seven) == 1
    assert capacities[zones_of_seven.pop()] == 7


def test_local_search_reaches_the_certified_capacity_optimum(rules, base):
    res = O.study_optimum(rules, base, constrained=True, capacity_matched=True,
                          restarts=30, seed=42)
    assert res["local_search_is_exact"]
    assert res["rules_captured"] == CAPACITY_CONSTRAINED_RULES
    assert round(res["support_captured"], 4) == CAPACITY_CONSTRAINED_SUPPORT


def test_no_layout_beats_the_certificate(rules, capacities):
    """The exact optimum is an upper bound on any feasible layout."""
    exact = O.exact_optimum(rules, Z.ZONE_IDS, capacities=capacities)
    rng = random.Random(0)
    cats = sorted(Z.proposed_assignment())
    for _ in range(50):
        slots = [z for z in Z.ZONE_IDS for _ in range(capacities[z])]
        rng.shuffle(slots)
        layout = dict(zip(cats, slots))
        r = cross_sell.score_layout(rules, cross_sell.groups_from_assignment(layout))
        assert r["support_captured"] <= exact["support_captured"] + 1e-9


def test_same_seed_same_answer(rules, base):
    a = O.study_optimum(rules, base, constrained=False, restarts=4, seed=7, certify=False)
    b = O.study_optimum(rules, base, constrained=False, restarts=4, seed=7, certify=False)
    assert a["assignment"] == b["assignment"]
    assert a["support_captured"] == b["support_captured"]


def test_trace_from_hand_built_starts_with_the_two_biggest_moves(rules, base):
    res = O.study_optimum(rules, base, constrained=False, restarts=1, seed=42,
                          certify=False)
    trace = res["trace_from_reference"]
    assert [t["category"] for t in trace[:2]] == [
        "BISCUITS AND COOKIES", "SNACKS"]
    assert trace[0]["delta_rules"] == 106
    assert trace[1]["rules_after"] == RULES_AFTER_TWO_MOVES
    assert trace[-1]["rules_after"] == TOTAL_RULES


def test_artifact_matches_the_certified_optima(rules, artifact, capacities):
    """zone_optimisation.json must carry exactly the certified figures."""
    for key, caps in (("unconstrained", None), ("constrained", None),
                      ("capacity_unconstrained", capacities),
                      ("capacity_constrained", capacities)):
        constrained = key.endswith("constrained") and not key.endswith("unconstrained")
        exact = O.exact_optimum(
            rules, Z.ZONE_IDS,
            locked=O.LOCKED if constrained else None,
            forbidden=O.FORBIDDEN if constrained else None,
            capacities=caps)
        run = artifact[key]
        assert run["rules_captured"] == exact["rules_captured"]
        assert abs(run["support_captured"] - exact["support_captured"]) < 1e-5
        assert run["local_search_is_exact"] is True
        assert run["restarts"] >= 100


def test_artifact_hand_built_and_constraint_cost(artifact):
    hand = artifact["hand_built"]
    assert hand["rules_captured"] == HAND_RULES
    assert round(hand["support_captured"], 3) == HAND_SUPPORT
    assert artifact["constraint_cost"]["unlimited_zones"]["rules"] == 2
    assert artifact["constraint_cost"]["capacity_matched"]["rules"] == 106
