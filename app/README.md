# Shelf Layout Tool

An interactive tool for the store owner. Drag the 25 product categories between
the 5 placement zones and watch the cross-sell capture score change.

The score is not a new calculation. It comes from the same function that
produces the figures reported in the dissertation, so the tool and the thesis
cannot disagree.

---

## The shared scoring function

**`analysis/cross_sell.py`** at the repository root holds the single
implementation of the cross-sell capture metric.

It is imported by both:

| Consumer | What it produces |
|---|---|
| `dashboard/precompute_artifacts.py` | `cross_sell_summary.json`, the figures quoted in the dissertation |
| `app/api/service.py` | the live score in this tool |

There is one implementation, not two copies that happen to agree. A test
(`test_uses_the_shared_scoring_module`) asserts the API is calling the shared
function by identity, so reimplementing scoring inside the app would fail the
suite rather than pass silently.

`analysis/zones.py` holds the five zone definitions and their ethics
classification.

### The metric

A strong rule is one with lift >= 3.0. There are 360, with total support
4.9860. A rule is **captured** when every category in it, antecedent and
consequent together, sits inside a single zone, so the products are next to
each other and the cross-sell can physically happen.

    capture rate = support of captured rules / 4.9860

---

## Running it

Both services are part of the project's `docker-compose.yml`.

```
docker compose up -d api web
```

| Service | URL |
|---|---|
| Web interface | http://localhost:5173 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

Ports 5435 (Postgres) and 8082 (Airflow) belong to the analysis pipeline and
are untouched by this app.

To run without Docker:

```
venv/Scripts/python -m uvicorn main:app --port 8000    # from app/api
npm install && npm run dev                             # from app/web
```

---

## Tests

```
docker compose exec api python -m pytest tests/ -v
venv/Scripts/python -m pytest app/api/tests/ -v          # from the repo root
```

The acceptance test pins the tool to the dissertation:

| Layout | Rules | Support | Rate |
|---|---|---|---|
| Existing (frequency clusters) | 28 | 0.411 | 8.2% |
| Proposed (five zones) | 56 | 0.813 | 16.3% |

If either row changes, the scoring logic or a layout definition has moved and
the dissertation is then wrong. That is what the test is for.

---

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Liveness, and whether the artifacts are readable |
| `GET /api/categories` | The 25 categories with basket penetration |
| `GET /api/zones` | The 5 zones with their ethics classification |
| `GET /api/layout/existing` | The frequency-driven baseline assignment |
| `GET /api/layout/proposed` | The five-zone assignment from notebook 07 |
| `GET /api/layout/optimal` | The best computed assignment from `analysis/optimise_zones.py`, read from `zone_optimisation.json` (`?constrained=` and `?capacity_matched=` select the variant) |
| `GET /api/rules/strong` | All 360 rules at lift >= 3.0 |
| `POST /api/layout/score` | Scores any `{category: zone_id}` assignment |

`POST /api/layout/score` returns `rules_captured`, `support_captured`,
`capture_rate`, the captured and uncaptured rules by name, and the ethics split.

---

## Data source

The app reads the committed CSV artifacts in `dashboard/artifacts/`, not the
Postgres warehouse. Three reasons:

1. The association rules are not in the warehouse. It holds transactions.
2. The two files needed total about 146 KB and are committed, so the app runs
   from a clean clone with no database, the same property the Streamlit
   dashboard already has.
3. Fewer moving parts for a marker to set up.

The artifacts are mounted **read only**. The app cannot modify the numbers the
dissertation depends on, and a write attempt fails with
`Read-only file system`.

---

## Ethics classification

Each zone is tagged with one of two labels, argued in section 24.3 of the
dissertation:

| Label | Meaning | Zones |
|---|---|---|
| assists existing intention | Co-locates goods the customer already intends to buy together | Zones 1, 3, 4, 5 |
| creates new intention | Positions impulse categories where customers did not plan to look | Zone 2, near the entrance |

The label appears on each zone header in the interface, not in a tooltip, and
the score summary reports how many captured rules fall into each class.

**A finding worth knowing:** under the proposed layout all 56 captured rules
sit in Zone 1. The entrance zone captures zero. The measured cross-sell benefit
comes entirely from zones that assist an existing intention.

---

## A note on the 13 inert categories

Only 12 of the 25 categories appear in any rule at lift 3.0. The other 13
cannot change the score no matter where they are placed. Their chips are
greyed, flagged "no rules", and carry a tooltip saying so, because a user who
moves several and sees nothing happen would reasonably conclude the tool is
broken.

---

## Layout

```
app/
  api/
    main.py            FastAPI endpoints
    service.py         layout loading and scoring, calls the shared module
    artifacts.py       read only access to dashboard/artifacts
    tests/
      test_acceptance.py
  web/
    src/
      App.jsx          state, history, drag and drop context
      api.js           fetch helpers
      components/
        Chip.jsx           draggable category
        Zone.jsx           droppable zone with ethics tag
        ScoreDisplay.jsx   score, reference markers, lost rules
        UnassignedPool.jsx holding area
```
