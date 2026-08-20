"""The five physical placement zones, and their ethical classification.

The zones are positions in the store, not category groupings. A *layout* is an
assignment of categories to these positions, which is why the same five zones
serve both the existing frequency-driven layout and the proposed one.

Zone names and locations match the planogram in notebook 07 and the dashboard.

ETHICS CLASSIFICATION
Section 24.3 of the dissertation argues that placement decisions divide by their
relationship to customer intention:

  assists   co-locating complementary goods lowers the effort of acting on an
            intention the customer already holds. Placing dal varieties together
            serves someone who came for dal.

  creates   positioning impulse categories where customers did not plan to look
            aims to produce an intention that did not exist on entry. This is
            defensible for ordinary low cost groceries with no deceptive
            mechanism, but it is not ethically identical to the first case and
            the interface says so rather than blurring them.

Only the entrance zone is classified as creating intention, because only it is
positioned to intercept customers before they reach what they came for.
"""

ASSISTS = "assists"
CREATES = "creates"

ETHICS_LABEL = {
    ASSISTS: "assists existing intention",
    CREATES: "creates new intention",
}

ETHICS_EXPLANATION = {
    ASSISTS: (
        "Co-locates goods the customer already intends to buy together, "
        "lowering the effort of acting on an existing intention."
    ),
    CREATES: (
        "Positions impulse categories where customers did not plan to look, "
        "aiming to create an intention that did not exist on entry."
    ),
}

# Ordered. The proposed categories are the RE-DERIVED assignment of 17 August
# 2026, not the hand-built one from notebook 07.
#
# WHY THIS WAS RE-DERIVED
# The audited category remap (reports/CATEGORY_REMAP_SPEC.md) changed the strong
# rule set from 360 rules to 368 and moved which categories carry them, so the
# hand-built layout was no longer derived from the rules it claimed to follow:
# it captured 16 strong rules against 22 for the frequency-driven baseline it
# was supposed to beat. Section 23.3 states the zones are derived from the
# association rules, so they were re-derived rather than left stale.
#
# HOW
# analysis.optimise_zones.exact_optimum, capacity-matched, under the three hard
# constraints below, certified against exhaustive enumeration. The result
# captures 180 of 368 strong rules, 2.6614 support, 54.1 per cent: 11.3x the
# hand-built layout and 8.2x the frequency baseline.
#
#   zone 4  DAIRY PRODUCTS, FROZEN FOODS         refrigeration
#   zone 5  ALCOHOLIC BEVERAGES, CIGARETTE AND TOBACCO   section 13.5 ethics
#   zone 5  RICE                                  heavy goods handling
#
# ZONE SIZES
# 6 / 5 / 3 / 4 / 7. The capacity multiset is unchanged from the hand-built
# 5 / 6 / 3 / 4 / 7, so the metric still cannot be gamed by pooling categories
# into one zone, but the centre now holds six rather than five. That swap was
# necessary, not cosmetic: the anchor cluster the rules identify is six
# categories, and with three categories locked into zone 5 the only position
# able to hold six was the centre. Scoring is identical either way.
#
# Rule-bearing placements are the optimiser's. Categories appearing in no
# strong rule cannot change the score, so they were left in the zone they
# already occupied wherever capacity allowed; only SOFT DRINKS AND JUICES had
# to move, from the entrance to the perimeter, because the entrance zone filled.
ZONES = [
    {
        "id": "zone_1",
        "name": "Zone 1: Store Centre",
        "location": "Store centre",
        "role": "Anchor cluster",
        "ethics": ASSISTS,
        # The six categories the strong rules bind together most tightly. Every
        # one of the 180 captured rules is captured here.
        "proposed_categories": [
            "FOOD STAPLES", "CANNED AND PACKAGED FOODS", "CLEANING SUPPLIES",
            "TEA AND SPICES", "PERSONAL CARE", "COOKING OIL",
        ],
    },
    {
        "id": "zone_2",
        "name": "Zone 2: Near Entrance",
        "location": "Near entrance",
        "role": "Impulse purchase",
        "ethics": CREATES,
        "proposed_categories": [
            "CONFECTIONERY", "SNACKS", "NOODLES", "HOUSEHOLD ITEMS",
            "POOJA ITEMS",
        ],
    },
    {
        "id": "zone_3",
        "name": "Zone 3: Side Aisle",
        "location": "Side aisle",
        "role": "Destination",
        "ethics": ASSISTS,
        "proposed_categories": [
            "BISCUITS AND COOKIES", "BABY CARE", "STATIONERY",
        ],
    },
    {
        "id": "zone_4",
        "name": "Zone 4: Back Wall",
        "location": "Back wall",
        "role": "Cold storage",
        "ethics": ASSISTS,
        "proposed_categories": [
            "DAIRY PRODUCTS", "FROZEN FOODS", "FRESH PRODUCE", "BAKERY",
        ],
    },
    {
        "id": "zone_5",
        "name": "Zone 5: Perimeter",
        "location": "Perimeter",
        "role": "Speciality and restricted",
        "ethics": ASSISTS,
        "proposed_categories": [
            "RICE", "ALCOHOLIC BEVERAGES", "CIGARETTE AND TOBACCO",
            "SOFT DRINKS AND JUICES", "BREAKFAST CEREALS",
            "ELECTRICAL SUPPLIES", "PARTY SUPPLIES",
        ],
    },
]

ZONE_IDS = [z["id"] for z in ZONES]
ZONE_BY_ID = {z["id"]: z for z in ZONES}


def proposed_assignment():
    """{category: zone_id} for the five-zone layout derived in notebook 07."""
    return {
        category: zone["id"]
        for zone in ZONES
        for category in zone["proposed_categories"]
    }


def ethics_of(zone_id):
    zone = ZONE_BY_ID.get(zone_id)
    return zone["ethics"] if zone else ASSISTS
