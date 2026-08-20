"""Acceptance test: the app must agree with the dissertation.

These are the central RQ1 figures. If any of them moves, either the scoring
logic or a layout definition has changed, and the dissertation is then wrong.
The test exists so that cannot happen silently.

    existing layout    22 rules, 0.278 support,  5.7 per cent
    proposed layout   180 rules, 2.661 support, 54.1 per cent

    Re-pinned 2026-08-17 after the audited category remap and the re-derivation
    of the five zones from the post-remap rules. The proposed layout is now the
    certified capacity-matched constrained optimum.

Run:
    docker compose exec api python -m pytest tests/ -v
    venv/Scripts/python -m pytest app/api/tests/ -v      (from the repo root)
"""

import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
API_DIR = HERE.parent
REPO_ROOT = API_DIR.parent.parent

# Import the API package whether pytest is run from the repo root or from
# inside the container, where the API lives at /app.
sys.path.insert(0, str(API_DIR))
if (REPO_ROOT / "analysis").is_dir():
    sys.path.insert(0, str(REPO_ROOT))

import service  # noqa: E402
import artifacts  # noqa: E402


# The published figures. Deliberately written as literals rather than read from
# the artifact, so that a regenerated artifact cannot quietly move the target.
EXISTING_RULES = 22
EXISTING_SUPPORT = 0.278
EXISTING_RATE = 5.7

PROPOSED_RULES = 180
PROPOSED_SUPPORT = 2.661
PROPOSED_RATE = 54.1

TOTAL_STRONG_RULES = 368
TOTAL_STRONG_SUPPORT = 4.916


def test_strong_rule_population():
    rules = service.strong_rules()
    assert len(rules) == TOTAL_STRONG_RULES
    assert round(sum(r["support"] for r in rules), 3) == TOTAL_STRONG_SUPPORT
    assert all(r["lift"] >= 3.0 for r in rules)


def test_existing_layout_matches_the_dissertation():
    result = service.score(service.existing_assignment())
    assert result["rules_captured"] == EXISTING_RULES
    assert round(result["support_captured"], 3) == EXISTING_SUPPORT
    assert round(result["capture_rate"], 1) == EXISTING_RATE


def test_proposed_layout_matches_the_dissertation():
    result = service.score(service.proposed_assignment())
    assert result["rules_captured"] == PROPOSED_RULES
    assert round(result["support_captured"], 3) == PROPOSED_SUPPORT
    assert round(result["capture_rate"], 1) == PROPOSED_RATE


def test_proposed_beats_existing():
    """The central RQ1 claim, stated as a test rather than as prose.

    The exact multiple is deliberately no longer asserted. It was "exactly
    twice" before the 2026-08-17 remap and is now 8.2x; pinning a ratio that
    tightly made a finding into a tripwire. The direction and a wide margin are
    what the claim needs.
    """
    existing = service.score(service.existing_assignment())
    proposed = service.score(service.proposed_assignment())
    assert proposed["rules_captured"] > existing["rules_captured"]
    assert proposed["support_captured"] > existing["support_captured"]
    assert proposed["rules_captured"] >= 5 * existing["rules_captured"]


def test_agrees_with_the_committed_artifact():
    """Pins the shared scorer against the file the thesis was written from."""
    summary = artifacts.load_cross_sell_summary()
    existing = service.score(service.existing_assignment())
    proposed = service.score(service.proposed_assignment())

    assert existing["rules_captured"] == summary["current_rules_captured"]
    assert proposed["rules_captured"] == summary["optimised_rules_captured"]
    assert round(existing["support_captured"], 4) == summary["current_support_captured"]
    assert round(proposed["support_captured"], 4) == summary["optimised_support_captured"]
    assert round(existing["capture_rate"], 1) == summary["current_capture_pct"]
    assert round(proposed["capture_rate"], 1) == summary["optimised_capture_pct"]
    assert existing["total_strong_rules"] == summary["total_strong_rules"]


def test_uses_the_shared_scoring_module():
    """The app must not carry its own copy of the metric.

    If someone reimplements scoring inside the app, this fails, and the claim
    that the tool and the thesis share one function stops being true.
    """
    import analysis.cross_sell as shared
    assert service.score_layout is shared.score_layout
    assert service.groups_from_assignment is shared.groups_from_assignment


def test_empty_layout_captures_nothing():
    result = service.score({})
    assert result["rules_captured"] == 0
    assert result["support_captured"] == 0
    assert result["capture_rate"] == 0
    assert len(result["uncaptured_rules"]) == TOTAL_STRONG_RULES


def test_everything_in_one_zone_captures_everything():
    """Sanity bound. One giant zone co-locates every rule by definition."""
    everything = {c["name"]: "zone_1" for c in artifacts.load_categories()}
    result = service.score(everything)
    assert result["rules_captured"] == TOTAL_STRONG_RULES
    assert round(result["capture_rate"], 1) == 100.0


def test_captured_and_uncaptured_partition_the_rules():
    result = service.score(service.proposed_assignment())
    assert (len(result["captured_rules"]) + len(result["uncaptured_rules"])
            == TOTAL_STRONG_RULES)


def test_ethics_split_covers_every_captured_rule():
    """Step 5: every captured rule is classified, none silently dropped."""
    result = service.score(service.proposed_assignment())
    ethics = result["ethics"]
    assert ethics["assists"] + ethics["creates"] == result["rules_captured"]
    assert ethics["assists"] > 0


def test_rules_with_no_strong_association_cannot_change_the_score():
    """The uncovered categories are inert, which the UI tells the user.

    11 of 25 since the 2026-08-17 category remap, which lifted the count of
    rule-bearing categories from 12 to 14.
    """
    base = service.proposed_assignment()
    inert = [c["name"] for c in artifacts.load_categories()
             if not c["appears_in_strong_rules"]]
    assert len(inert) == 11

    moved = dict(base)
    for name in inert:
        moved[name] = "zone_3" if base.get(name) != "zone_3" else "zone_5"

    before = service.score(base)
    after = service.score(moved)
    assert after["rules_captured"] == before["rules_captured"]
    assert round(after["support_captured"], 6) == round(before["support_captured"], 6)
