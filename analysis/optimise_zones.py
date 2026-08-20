"""Computed zone assignment.

Searches for the assignment of the 25 product categories to the 5 placement
zones that maximises captured cross-sell support, and reports how the
hand-built layout from notebook 07 compares with the best assignment the
data allows.

THE OBJECTIVE
    analysis.cross_sell.score_layout, the one function behind the
    dissertation's 28 / 56 capture figures. Nothing in this file scores a
    layout by any other route: every candidate move is evaluated by calling
    score_layout on the rules the move can affect, and every returned result
    is a full score_layout call on the finished assignment.

THE METHOD
    Greedy local search with random restarts.
      * a state is a {category: zone} assignment
      * a move relocates one category to another zone; when zone sizes are
        fixed, a swap of two categories between zones is also a move
      * each pass evaluates every legal move and applies the single best
        improving one; the search stops when no move improves the score
      * restart 0 starts from the hand-built layout so the sequence of moves
        that separates it from the optimum is recorded; every later restart
        starts from a seeded random assignment
      * one master seed generates every restart seed, so the run reproduces
        exactly

    A separate exhaustive routine (exact_optimum) certifies the answer. It
    enumerates every feasible partition of the rule-bearing categories by
    dynamic programming over zones, still scoring blocks with score_layout,
    and returns the true maximum. The local search result is compared against
    it and the comparison is reported, so "best found" can be stated as
    "best possible" only when that is actually true.

WHY NOT COMMUNITY DETECTION ON THE RULE NETWORK
    Community detection optimises modularity, a proxy for the real objective.
    Here the real objective is cheap and exact, only 12 of the 25 categories
    appear in any strong rule so the search space is small, the physical and
    ethical constraints are natural in local search and awkward in graph
    partitioning, and the exhaustive certificate settles optimality outright.
    A proxy objective would add nothing.

TWO FACTS ABOUT THE METRIC WORTH KNOWING BEFORE READING THE NUMBERS
    1. score_layout has no notion of shelf capacity. Without a size limit the
       optimum is one mega-zone holding all 12 rule-bearing categories, which
       captures every rule (100 per cent). That is a property of the metric,
       not a shelf plan, and it is reported as such. The capacity-matched runs
       hold each zone to its size in the hand-built layout (5/6/3/4/7) so the
       answer is a plan the store could actually build.
    2. The 13 categories that appear in no strong rule cannot change the
       score. They keep their hand-built zone unless a size limit forces one
       to yield its slot, and never enter a zone forbidden to them.

CONSTRAINT SETS
    unconstrained   any category may go in any zone
    constrained     DAIRY PRODUCTS and FROZEN FOODS locked to zone_4 (back
                    wall, cold storage); ALCOHOLIC BEVERAGES and CIGARETTE AND
                    TOBACCO barred from zone_2 (entrance), the ethical
                    boundary in section 13.5 of the dissertation

Run the full comparison and write dashboard/artifacts/zone_optimisation.json:

    python analysis/optimise_zones.py
"""

import csv
import json
import os
import random
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from analysis import zones as zone_defs  # noqa: E402
from analysis.cross_sell import (  # noqa: E402
    STRONG_LIFT_FLOOR,
    groups_from_assignment,
    score_layout,
)

# The study's hard constraints, restated as fixed positions on 17 August 2026.
#
# They used to be two locks plus two entrance bans. Both alcohol bans are now
# full locks to the perimeter, which is what section 13.5 actually decided, and
# RICE is locked as a heavy-goods handling constraint. Stating them as positions
# rather than bans matters for the measured cost: a lock consumes a slot in its
# zone, and slots are what the capacity-matched optimum competes for.
LOCKED = {
    "DAIRY PRODUCTS": "zone_4",          # refrigeration
    "FROZEN FOODS": "zone_4",            # refrigeration
    "ALCOHOLIC BEVERAGES": "zone_5",     # section 13.5 ethics
    "CIGARETTE AND TOBACCO": "zone_5",   # section 13.5 ethics
    "RICE": "zone_5",                    # heavy goods handling
}
FORBIDDEN = {}

DEFAULT_RESTARTS = 200
DEFAULT_SEED = 42
_EPS = 1e-9

ARTIFACT_NAME = "zone_optimisation.json"


# ----------------------------------------------------------------------
# inputs
# ----------------------------------------------------------------------

def rule_bearing_categories(rules):
    """Categories that appear in at least one rule: the only movable levers."""
    cats = set()
    for rule in rules:
        cats |= rule["cats"]
    return cats


def default_artifacts_dir():
    return os.environ.get(
        "PP_ARTIFACTS_DIR", os.path.join(_ROOT, "dashboard", "artifacts")
    )


def strong_rules_from_artifacts(artifacts_dir=None):
    """The strong rules (lift >= 3.0) from the committed artifact.

    Uses the stdlib csv module only, so the module also runs inside the API
    container, which has no pandas.
    """
    artifacts_dir = artifacts_dir or default_artifacts_dir()
    path = os.path.join(artifacts_dir, "category_rules.csv")
    rules = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if float(row["lift"]) < STRONG_LIFT_FLOOR:
                continue
            cats = {p.strip() for p in row["antecedents"].split(",")}
            cats |= {p.strip() for p in row["consequents"].split(",")}
            rules.append({"cats": cats, "support": float(row["support"])})
    return rules


# ----------------------------------------------------------------------
# helpers shared by the search and the certificate
# ----------------------------------------------------------------------

def _captured_support(rules, groups):
    """score_layout, reduced to the one number the search maximises."""
    return score_layout(rules, groups, 1.0)["support_captured"]


def _free_capacity(capacities, locked, zone_ids):
    """Slots per zone left for non-locked categories, or None if unlimited."""
    if capacities is None:
        return None
    free = {z: int(capacities.get(z, 0)) for z in zone_ids}
    for c, z in locked.items():
        free[z] -= 1
    if any(v < 0 for v in free.values()):
        raise ValueError("locked categories exceed the capacity of their zone")
    return free


def _fill_indifferent(core, base_assignment, locked, forbidden, zone_ids,
                      capacities):
    """Complete a core assignment with the score-indifferent categories.

    Locked categories go to their locked zone. Every other indifferent
    category keeps its reference zone when that is allowed and has room,
    otherwise it takes the first zone in zone order that is allowed and has
    room. Deterministic: sorted order throughout.
    """
    out = dict(core)
    out.update(locked)
    used = {z: 0 for z in zone_ids}
    for z in out.values():
        used[z] += 1
    for c in sorted(base_assignment):
        if c in out:
            continue
        banned = forbidden.get(c, set())
        preferred = base_assignment[c]
        candidates = [preferred] + [z for z in zone_ids if z != preferred]
        for z in candidates:
            if z in banned:
                continue
            if capacities is not None and used[z] >= capacities.get(z, 0):
                continue
            out[c] = z
            used[z] += 1
            break
        else:
            raise ValueError(f"No feasible zone for {c}")
    return out


# ----------------------------------------------------------------------
# greedy local search with random restarts
# ----------------------------------------------------------------------

def optimise(rules, zone_ids, base_assignment, locked=None, forbidden=None,
             capacities=None, restarts=DEFAULT_RESTARTS, seed=DEFAULT_SEED,
             certify=True):
    """Best assignment found by greedy local search with random restarts.

    rules            [{'cats': set, 'support': float}], the strong rules
    zone_ids         ordered zone identifiers
    base_assignment  reference {category: zone} covering every category: the
                     restart 0 start point and the home of the indifferent
                     categories
    locked           {category: zone} that may never move
    forbidden        {category: {zones it may never occupy}}
    capacities       {zone: max categories} or None for unlimited
    restarts         number of restarts (restart 0 is the reference layout)
    seed             master seed; every restart seed derives from it
    certify          also run exact_optimum and report whether the search
                     reached it

    Returns a dict with the finished assignment, the score_layout figures for
    it, the move trace from the reference layout, restart statistics and,
    when certify is true, the exact optimum for comparison.
    """
    rules = list(rules)
    locked = dict(locked or {})
    forbidden = {c: set(z) for c, z in (forbidden or {}).items()}
    total_support = float(sum(r["support"] for r in rules))
    free_capacity = _free_capacity(capacities, locked, zone_ids)

    movable = sorted(c for c in rule_bearing_categories(rules) if c not in locked)
    allowed = {c: [z for z in zone_ids if z not in forbidden.get(c, ())]
               for c in movable}
    for c in movable:
        if not allowed[c]:
            raise ValueError(f"{c} is forbidden from every zone")
    rules_of = {c: [r for r in rules if c in r["cats"]] for c in movable}
    pair_rules = {}

    def rules_touching(c1, c2):
        key = (c1, c2) if c1 < c2 else (c2, c1)
        if key not in pair_rules:
            seen, out = set(), []
            for r in rules_of[c1] + rules_of[c2]:
                if id(r) not in seen:
                    seen.add(id(r))
                    out.append(r)
            pair_rules[key] = out
        return pair_rules[key]

    # zone -> set of categories that matter to the score (movable + locked)
    def make_sets(core):
        sets = {z: set() for z in zone_ids}
        for c, z in locked.items():
            sets[z].add(c)
        for c, z in core.items():
            sets[z].add(c)
        return sets

    def has_room(sets, z):
        if free_capacity is None:
            return True
        n_movable_here = sum(1 for c in sets[z] if c not in locked)
        return n_movable_here < free_capacity[z]

    def best_move(core, sets):
        """The single best improving move or swap, or None."""
        groups = [sets[z] for z in zone_ids]
        best = (_EPS, None)
        for c in movable:
            here = core[c]
            rel = rules_of[c]
            before = _captured_support(rel, groups)
            for z in allowed[c]:
                if z == here or not has_room(sets, z):
                    continue
                sets[here].discard(c)
                sets[z].add(c)
                gain = _captured_support(rel, groups) - before
                sets[z].discard(c)
                sets[here].add(c)
                if gain > best[0]:
                    best = (gain, ("move", c, here, z))
        if free_capacity is not None:
            for i, c1 in enumerate(movable):
                z1 = core[c1]
                for c2 in movable[i + 1:]:
                    z2 = core[c2]
                    if z1 == z2 or z2 not in allowed[c1] or z1 not in allowed[c2]:
                        continue
                    rel = rules_touching(c1, c2)
                    before = _captured_support(rel, groups)
                    sets[z1].discard(c1)
                    sets[z2].discard(c2)
                    sets[z2].add(c1)
                    sets[z1].add(c2)
                    gain = _captured_support(rel, groups) - before
                    sets[z2].discard(c1)
                    sets[z1].discard(c2)
                    sets[z1].add(c1)
                    sets[z2].add(c2)
                    if gain > best[0]:
                        best = (gain, ("swap", c1, z1, c2, z2))
        return best[1]

    def apply(core, sets, mv):
        if mv[0] == "move":
            _, c, here, z = mv
            core[c] = z
            sets[here].discard(c)
            sets[z].add(c)
        else:
            _, c1, z1, c2, z2 = mv
            core[c1], core[c2] = z2, z1
            sets[z1].discard(c1)
            sets[z2].discard(c2)
            sets[z2].add(c1)
            sets[z1].add(c2)

    def full_score(sets):
        return score_layout(rules, [sets[z] for z in zone_ids], total_support)

    def greedy(core, record=None):
        sets = make_sets(core)
        while True:
            mv = best_move(core, sets)
            if mv is None:
                return core
            if record is not None:
                before = full_score(sets)
            apply(core, sets, mv)
            if record is not None:
                after = full_score(sets)
                entry = {
                    "step": len(record) + 1,
                    "kind": mv[0],
                    "delta_rules": after["rules_captured"] - before["rules_captured"],
                    "delta_support": round(
                        after["support_captured"] - before["support_captured"], 4),
                    "rules_after": after["rules_captured"],
                    "support_after": round(after["support_captured"], 4),
                }
                if mv[0] == "move":
                    entry.update(category=mv[1], from_zone=mv[2], to_zone=mv[3])
                else:
                    entry.update(category=mv[1], from_zone=mv[2],
                                 swapped_with=mv[3], to_zone=mv[4])
                record.append(entry)

    def reference_start():
        core, sets = {}, make_sets({})
        for c in movable:
            z = base_assignment[c]
            if z not in allowed[c] or not has_room(sets, z):
                z = next(zz for zz in allowed[c] if has_room(sets, zz))
            core[c] = z
            sets[z].add(c)
        return core

    def random_start(rng):
        for _attempt in range(1000):
            core, sets = {}, make_sets({})
            order = list(movable)
            rng.shuffle(order)
            ok = True
            for c in order:
                options = [z for z in allowed[c] if has_room(sets, z)]
                if not options:
                    ok = False
                    break
                z = rng.choice(options)
                core[c] = z
                sets[z].add(c)
            if ok:
                return core
        raise ValueError("could not build a feasible random start")

    def tidy(core):
        """Among equal-score optima, prefer the one nearest the reference.

        The search may leave a category away from its reference zone even
        though bringing it back would cost nothing (this happens to every
        rule-bearing category whose rules all sit outside its group). Undo
        every such displacement, by a move when the reference zone has room
        and by a zero-loss swap otherwise, so the reported moves are only the
        ones that earn support. The score is unchanged by construction.
        """
        sets = make_sets(core)
        changed = True
        while changed:
            changed = False
            for c in movable:
                home, here = base_assignment[c], core[c]
                if here == home or home not in allowed[c]:
                    continue
                groups = [sets[z] for z in zone_ids]
                rel = rules_of[c]
                if has_room(sets, home):
                    before = _captured_support(rel, groups)
                    sets[here].discard(c)
                    sets[home].add(c)
                    if _captured_support(rel, groups) >= before - _EPS:
                        core[c] = home
                        changed = True
                        continue
                    sets[home].discard(c)
                    sets[here].add(c)
                    continue
                for c2 in movable:
                    if (core[c2] != home or base_assignment[c2] == home
                            or here not in allowed[c2]):
                        continue
                    rel2 = rules_touching(c, c2)
                    before = _captured_support(rel2, groups)
                    sets[here].discard(c)
                    sets[home].discard(c2)
                    sets[home].add(c)
                    sets[here].add(c2)
                    if _captured_support(rel2, groups) >= before - _EPS:
                        core[c], core[c2] = home, here
                        changed = True
                        break
                    sets[home].discard(c)
                    sets[here].discard(c2)
                    sets[here].add(c)
                    sets[home].add(c2)
        return core

    master = random.Random(seed)
    restart_seeds = [master.getrandbits(32) for _ in range(restarts)]

    best_core, best_support, hits, trace = None, -1.0, 0, []
    for r in range(restarts):
        if r == 0:
            core = greedy(reference_start(), record=trace)
        else:
            core = greedy(random_start(random.Random(restart_seeds[r])))
        support = full_score(make_sets(core))["support_captured"]
        if support > best_support + _EPS:
            best_core, best_support, hits = core, support, 1
        elif abs(support - best_support) <= _EPS:
            hits += 1

    best_core = tidy(best_core)
    assignment = _fill_indifferent(best_core, base_assignment, locked, forbidden,
                                   zone_ids, capacities)
    result = score_layout(rules, groups_from_assignment(assignment), total_support)
    if abs(result["support_captured"] - best_support) > 1e-9:  # pragma: no cover
        raise AssertionError("finished assignment does not score as the search claimed")

    out = {
        "assignment": assignment,
        "rules_captured": result["rules_captured"],
        "support_captured": result["support_captured"],
        "capture_rate": result["capture_rate"],
        "total_rules": result["total_rules"],
        "total_support": result["total_support"],
        "restarts": restarts,
        "seed": seed,
        "restarts_reaching_best": hits,
        "trace_from_reference": trace,
        "movable": movable,
        "locked": dict(locked),
        "forbidden": {c: sorted(z) for c, z in forbidden.items()},
        "capacities": dict(capacities) if capacities is not None else None,
    }
    if certify:
        exact = exact_optimum(rules, zone_ids, locked=locked, forbidden=forbidden,
                              capacities=capacities)
        out["exact_optimum_support"] = exact["support_captured"]
        out["exact_optimum_rules"] = exact["rules_captured"]
        out["local_search_is_exact"] = (
            abs(exact["support_captured"] - result["support_captured"]) <= 1e-9
        )
    return out


# ----------------------------------------------------------------------
# exhaustive certificate
# ----------------------------------------------------------------------

def exact_optimum(rules, zone_ids, locked=None, forbidden=None, capacities=None):
    """The true maximum captured support, by exhaustive enumeration.

    Dynamic programming over zones: after zones 1..k have been filled, the
    state is the set of rule-bearing categories already placed and the value
    is the best support captured so far. Zone k+1 takes any block of the
    remaining categories that fits its capacity and its bans. Blocks are
    scored with score_layout, the same function the search uses.

    Only the rule-bearing categories are enumerated, because the others cannot
    change the score. With 12 of them the enumeration is 5 x 3^12 block
    choices, which runs in a few seconds.

    Returns rules_captured and support_captured for the optimum, plus one
    optimal core assignment of the rule-bearing categories.
    """
    rules = list(rules)
    locked = dict(locked or {})
    forbidden = {c: set(z) for c, z in (forbidden or {}).items()}
    total_support = float(sum(r["support"] for r in rules))
    free_capacity = _free_capacity(capacities, locked, zone_ids)

    movable = sorted(c for c in rule_bearing_categories(rules) if c not in locked)
    n = len(movable)
    full = (1 << n) - 1
    forb_mask = {
        z: sum(1 << i for i, c in enumerate(movable) if z in forbidden.get(c, ()))
        for z in zone_ids
    }
    locked_in = {z: {c for c, zz in locked.items() if zz == z} for z in zone_ids}
    popcount = [bin(m).count("1") for m in range(1 << n)]

    cache = {}

    def block_support(mask, z):
        key = (mask, z) if locked_in[z] else (mask, None)
        if key not in cache:
            cats = {movable[i] for i in range(n) if mask >> i & 1} | locked_in[z]
            cache[key] = _captured_support(rules, [cats]) if cats else 0.0
        return cache[key]

    best = {0: 0.0}
    back = []
    for z in zone_ids:
        cap = n if free_capacity is None else free_capacity[z]
        forb = forb_mask[z]
        new, pointer = {}, {}
        for mask, val in best.items():
            rem = full ^ mask
            block = rem
            while True:
                if popcount[block] <= cap and not block & forb:
                    v = val + block_support(block, z)
                    m2 = mask | block
                    if v > new.get(m2, -1.0) + _EPS:
                        new[m2] = v
                        pointer[m2] = (mask, block)
                if block == 0:
                    break
                block = (block - 1) & rem
        best = new
        back.append(pointer)
        if not best:
            raise ValueError("no feasible assignment under these constraints")

    if full not in best:
        raise ValueError("no feasible assignment under these constraints")

    core, mask = {}, full
    for z, pointer in zip(reversed(zone_ids), reversed(back)):
        prev, block = pointer[mask]
        for i in range(n):
            if block >> i & 1:
                core[movable[i]] = z
        mask = prev

    sets = {z: set(locked_in[z]) for z in zone_ids}
    for c, z in core.items():
        sets[z].add(c)
    result = score_layout(rules, [sets[z] for z in zone_ids], total_support)
    if abs(result["support_captured"] - best[full]) > 1e-9:  # pragma: no cover
        raise AssertionError("reconstructed optimum does not score as the DP claimed")
    return {
        "rules_captured": result["rules_captured"],
        "support_captured": result["support_captured"],
        "capture_rate": result["capture_rate"],
        "core_assignment": core,
    }


# ----------------------------------------------------------------------
# the study's runs
# ----------------------------------------------------------------------

def study_optimum(rules, base_assignment, constrained, capacity_matched=False,
                  restarts=DEFAULT_RESTARTS, seed=DEFAULT_SEED, certify=True):
    """The optimiser under the study's own constraint sets.

    constrained       apply the cold-chain locks and the section 13.5 boundary
    capacity_matched  additionally hold each zone to its size in the reference
                      assignment, so the answer is a buildable shelf plan
                      rather than the degenerate mega-zone
    """
    capacities = None
    if capacity_matched:
        capacities = {z: 0 for z in zone_defs.ZONE_IDS}
        for z in base_assignment.values():
            capacities[z] += 1
    return optimise(
        rules,
        zone_defs.ZONE_IDS,
        base_assignment,
        locked=LOCKED if constrained else None,
        forbidden=FORBIDDEN if constrained else None,
        capacities=capacities,
        restarts=restarts,
        seed=seed,
        certify=certify,
    )


def compare(rules=None, base_assignment=None, restarts=DEFAULT_RESTARTS,
            seed=DEFAULT_SEED, certify=True):
    """The full comparison the dissertation reports.

    Five layouts scored by the same function on the same 360 rules:
        hand_built                 the notebook 07 layout, unchanged
        unconstrained              best assignment, no constraints at all
        constrained                best assignment under the study's physical
                                   and ethical constraints
        capacity_unconstrained     best assignment with zone sizes fixed to
                                   the hand-built 5/6/3/4/7, no other rule
        capacity_constrained       zone sizes fixed AND the study's constraints
    plus the deltas against the hand-built layout and the constraint costs.
    """
    rules = list(rules if rules is not None else strong_rules_from_artifacts())
    base = dict(base_assignment or zone_defs.proposed_assignment())
    total = float(sum(r["support"] for r in rules))

    hand = score_layout(rules, groups_from_assignment(base), total)
    hand_built = {
        "assignment": base,
        "rules_captured": hand["rules_captured"],
        "support_captured": hand["support_captured"],
        "capture_rate": hand["capture_rate"],
        "groups": _groups_of(base, zone_defs.ZONE_IDS),
    }

    runs = {
        "unconstrained": study_optimum(rules, base, False, False, restarts, seed, certify),
        "constrained": study_optimum(rules, base, True, False, restarts, seed, certify),
        "capacity_unconstrained": study_optimum(rules, base, False, True, restarts, seed, certify),
        "capacity_constrained": study_optimum(rules, base, True, True, restarts, seed, certify),
    }

    def delta(run):
        return {
            "rules": run["rules_captured"] - hand["rules_captured"],
            "support": round(run["support_captured"] - hand["support_captured"], 4),
            "capture_rate_points": round(run["capture_rate"] - hand["capture_rate"], 1),
        }

    for run in runs.values():
        run["delta_vs_hand_built"] = delta(run)
        run["moves_vs_hand_built"] = sorted(
            [{"category": c, "from_zone": base[c], "to_zone": run["assignment"][c]}
             for c in base if run["assignment"][c] != base[c]],
            key=lambda m: m["category"],
        )
        run["groups"] = _groups_of(run["assignment"], zone_defs.ZONE_IDS)

    def cost(free, bound):
        return {
            "rules": free["rules_captured"] - bound["rules_captured"],
            "support": round(free["support_captured"] - bound["support_captured"], 4),
            "capture_rate_points": round(free["capture_rate"] - bound["capture_rate"], 1),
        }

    rb = sorted(rule_bearing_categories(rules))
    return {
        "method": (
            f"greedy local search with random restarts ({restarts} restarts, "
            f"master seed {seed}), objective analysis.cross_sell.score_layout, "
            "certified against exhaustive enumeration"
        ),
        "total_rules": hand["total_rules"],
        "total_support": round(total, 4),
        "rule_bearing_categories": rb,
        "n_rule_bearing_categories": len(rb),
        "n_inert_categories": len(base) - len(rb),
        "constraints": {
            "locked": dict(LOCKED),
            "forbidden": {c: sorted(z) for c, z in FORBIDDEN.items()},
            "constrained_categories_in_strong_rules": sorted(
                c for c in list(LOCKED) + list(FORBIDDEN) if c in rb
            ),
        },
        "capacities": {z: sum(1 for c in base if base[c] == z)
                       for z in zone_defs.ZONE_IDS},
        "hand_built": hand_built,
        **runs,
        "constraint_cost": {
            "unlimited_zones": cost(runs["unconstrained"], runs["constrained"]),
            "capacity_matched": cost(runs["capacity_unconstrained"],
                                     runs["capacity_constrained"]),
        },
    }


def _groups_of(assignment, zone_ids):
    return {z: sorted(c for c, zz in assignment.items() if zz == z) for z in zone_ids}


def _serialisable(obj):
    if isinstance(obj, dict):
        return {k: _serialisable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialisable(v) for v in obj]
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, float):
        return round(obj, 6)
    return obj


def write_artifact(comparison, artifacts_dir=None):
    path = os.path.join(artifacts_dir or default_artifacts_dir(), ARTIFACT_NAME)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(_serialisable(comparison), fh, indent=2)
    return path


# ----------------------------------------------------------------------
# command line report
# ----------------------------------------------------------------------

def _print_report(cmp):  # pragma: no cover - presentation only
    hand = cmp["hand_built"]
    print(f"Strong rules: {cmp['total_rules']}, total support {cmp['total_support']:.4f}")
    print(f"Rule-bearing categories: {cmp['n_rule_bearing_categories']} of "
          f"{cmp['n_rule_bearing_categories'] + cmp['n_inert_categories']}")
    print(f"Method: {cmp['method']}")
    print()
    print(f"{'layout':32} {'rules':>6} {'support':>9} {'rate':>7}   delta vs hand-built")
    print("-" * 90)
    print(f"{'hand-built (notebook 07)':32} {hand['rules_captured']:>6} "
          f"{hand['support_captured']:>9.4f} {hand['capture_rate']:>6.1f}%   reference")
    for key in ("unconstrained", "constrained", "capacity_unconstrained",
                "capacity_constrained"):
        r = cmp[key]
        d = r["delta_vs_hand_built"]
        print(f"{key.replace('_', ' '):32} {r['rules_captured']:>6} "
              f"{r['support_captured']:>9.4f} {r['capture_rate']:>6.1f}%   "
              f"{d['rules']:+d} rules, {d['support']:+.4f} support, "
              f"{d['capture_rate_points']:+.1f} pts")
        cert = ""
        if "exact_optimum_support" in r:
            cert = (" (matches the exhaustive optimum)" if r["local_search_is_exact"]
                    else f" (exhaustive optimum is {r['exact_optimum_support']:.4f}, "
                         "search fell short)")
        print(f"{'':32} best reached by {r['restarts_reaching_best']} of "
              f"{r['restarts']} restarts{cert}")
    print()
    cc = cmp["constraint_cost"]
    print("Price of the constraints (unconstrained minus constrained):")
    print(f"  unlimited zone sizes : {cc['unlimited_zones']['rules']:+d} rules, "
          f"{cc['unlimited_zones']['support']:+.4f} support")
    print(f"  capacity-matched     : {cc['capacity_matched']['rules']:+d} rules, "
          f"{cc['capacity_matched']['support']:+.4f} support")
    print(f"  constrained categories that appear in any strong rule: "
          f"{cmp['constraints']['constrained_categories_in_strong_rules'] or 'none'}")
    print()
    print("Greedy path from the hand-built layout (restart 0), unconstrained:")
    for step in cmp["unconstrained"]["trace_from_reference"]:
        print(f"  {step['step']:>2}. {step['category']}: {step['from_zone']} -> "
              f"{step['to_zone']}  {step['delta_rules']:+d} rules, "
              f"{step['delta_support']:+.4f} support  (now {step['rules_after']} rules, "
              f"{step['support_after']:.4f})")
    print()
    print("Greedy path from the hand-built layout (restart 0), capacity-matched constrained:")
    for step in cmp["capacity_constrained"]["trace_from_reference"]:
        extra = f" (swapped with {step['swapped_with']})" if step["kind"] == "swap" else ""
        print(f"  {step['step']:>2}. {step['category']}: {step['from_zone']} -> "
              f"{step['to_zone']}{extra}  {step['delta_rules']:+d} rules, "
              f"{step['delta_support']:+.4f} support  (now {step['rules_after']} rules, "
              f"{step['support_after']:.4f})")
    print()
    print("Capacity-matched constrained optimum, zone by zone:")
    for z, cats in cmp["capacity_constrained"]["groups"].items():
        rb = [c for c in cats if c in cmp["rule_bearing_categories"]]
        print(f"  {z} ({len(cats)}): {', '.join(cats)}")
        print(f"      rule-bearing: {', '.join(rb) if rb else 'none'}")


if __name__ == "__main__":  # pragma: no cover
    import time
    t0 = time.time()
    comparison = compare()
    _print_report(comparison)
    if "--dry-run" not in sys.argv:
        out_path = write_artifact(comparison)
        print(f"\nWrote {os.path.relpath(out_path, _ROOT)}")
    print(f"({time.time() - t0:.1f}s)")
