"""The dashboard must not carry its own copy of the zone definitions.

Mirror of app/api/tests/test_acceptance.py::test_uses_the_shared_scoring_module:
that test pins the scoring FUNCTION to analysis/cross_sell.py by identity; this
one pins the zone CONTENT to analysis/zones.py by identity. If someone
reintroduces a hardcoded category list in the dashboard, this fails, and the
claim that the dashboard, the shelf tool and the dissertation share one zone
definition stops being true.

Run:
    venv/Scripts/python -m pytest dashboard/tests/ -v      (from the repo root)
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DASHBOARD = HERE.parent
ROOT = DASHBOARD.parent

for p in (str(ROOT), str(DASHBOARD)):
    if p not in sys.path:
        sys.path.insert(0, p)

import zone_layout  # noqa: E402
from analysis import zones as shared  # noqa: E402


def test_zone_categories_are_the_shared_objects():
    """Identity, not equality: the dashboard must reference the shared lists."""
    assert len(zone_layout.ZONES) == len(shared.ZONES)
    for merged, src in zip(zone_layout.ZONES, shared.ZONES):
        assert merged["id"] == src["id"]
        assert merged["categories"] is src["proposed_categories"]
        assert merged["ethics"] == src["ethics"]


def test_every_shared_zone_has_presentation_and_nothing_else():
    assert set(zone_layout.PRESENTATION) == {z["id"] for z in shared.ZONES}


def test_app_imports_the_shared_zones_and_has_no_local_copy():
    source = (DASHBOARD / "app.py").read_text(encoding="utf-8")
    assert "from zone_layout import ZONES" in source
    # The old hardcoded block listed the zone 1 categories inline. If any zone
    # category list literal reappears in app.py, the copy has come back.
    assert '"FOOD STAPLES", "COOKING OIL"' not in source
    assert "'FOOD STAPLES', 'COOKING OIL'" not in source


def test_zones_cover_all_25_categories_exactly_once():
    seen = []
    for z in zone_layout.ZONES:
        seen.extend(z["categories"])
    assert len(seen) == 25
    assert len(set(seen)) == 25
