"""Presentation layer for the five placement zones.

The zone CONTENT (which categories belong to which zone, and each zone's
ethics classification) is the research finding from notebook 07, and it lives
in exactly one place: analysis/zones.py, the same module the shelf layout tool
in app/ reads. This file adds only what a chart needs and the analysis does
not: display names, colours, planogram rectangles and the placement rationale
prose shown on the Placement Zones page.

The merge below reuses the shared category list objects by reference, so
dashboard/tests/test_shared_zones.py can assert identity (`is`), the same way
app/api/tests/test_acceptance.py::test_uses_the_shared_scoring_module pins the
scoring function. Redefining the categories here would fail that test rather
than drift silently.

Display names keep the "Zone 1 - Center" form because that exact string is the
zone_assignment value stored in warehouse.dim_category, and the dashboard
matches warehouse rows to colours by that name.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from analysis import zones as zone_defs  # noqa: E402

# Chart-only attributes, keyed by the shared zone id. Nothing analytical here:
# a colour or a rectangle cannot change a number.
#
# The palette follows the dashboard's colour language: Zone 1 is teal because
# it is where the measured result lives (all 56 captured cross-sell rules sit
# in it), and the other four zones are a neutral slate lightness ramp, since
# they are identity, not signal. "ink" is the label colour that stays legible
# on each fill. Zone identity never rides on colour alone: every zone is
# direct-labelled with its name on the planogram, the bar axis and the cards.
PRESENTATION = {
    "zone_1": {
        "display": "Zone 1 - Center", "color": "#0F766E", "ink": "#FFFFFF",
        "rect": (0.35, 0.30, 0.30, 0.40),
        "reason": "CLEANING SUPPLIES connects to 48 rules with lift above 5. "
                  "FOOD STAPLES appears in 42.2% of all baskets. Central placement "
                  "forces customers to pass other products.",
    },
    "zone_2": {
        "display": "Zone 2 - Entrance", "color": "#1E2A4A", "ink": "#FFFFFF",
        "rect": (0.05, 0.05, 0.90, 0.15),
        "reason": "High frequency impulse categories. Entrance placement captures "
                  "customers before they focus on essentials, increasing unplanned "
                  "purchases.",
    },
    "zone_3": {
        "display": "Zone 3 - Side Aisle", "color": "#4A5A70", "ink": "#FFFFFF",
        "rect": (0.05, 0.25, 0.25, 0.60),
        "reason": "Customers seeking these products will find them regardless of "
                  "placement. Side aisle keeps them out of the main traffic flow.",
    },
    "zone_4": {
        "display": "Zone 4 - Back Wall", "color": "#7C8CA0", "ink": "#1C1917",
        "rect": (0.05, 0.78, 0.90, 0.17),
        "reason": "Physical constraint: refrigeration required. Back placement also "
                  "draws customers through the store, increasing exposure to other "
                  "products.",
    },
    "zone_5": {
        "display": "Zone 5 - Perimeter", "color": "#A6B0BD", "ink": "#1C1917",
        "rect": (0.70, 0.25, 0.25, 0.45),
        "reason": "Low frequency or destination categories. Customers buying these "
                  "seek them out specifically. Perimeter placement reduces main "
                  "aisle congestion.",
    },
}


def _merge():
    zones = []
    for z in zone_defs.ZONES:
        p = PRESENTATION[z["id"]]
        zones.append({
            "id": z["id"],
            "name": p["display"],
            "label": z["role"].title(),
            "ethics": z["ethics"],
            "ethics_label": zone_defs.ETHICS_LABEL[z["ethics"]],
            # The shared list object itself, not a copy: identity is what the
            # test asserts.
            "categories": z["proposed_categories"],
            "color": p["color"],
            "ink": p["ink"],
            "rect": p["rect"],
            "reason": p["reason"],
        })
    return zones


ZONES = _merge()
