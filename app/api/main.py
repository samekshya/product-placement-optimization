"""Shelf layout tool API.

Serves the product categories and, from step 2, scores shelf layouts using the
cross-sell capture logic from the existing analysis.

Run locally:
    venv/Scripts/python -m uvicorn main:app --reload --port 8000
Run in Docker:
    docker compose up -d api
"""

import os
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import artifacts
import service

app = FastAPI(
    title="Shelf Layout Tool API",
    description="Cross-sell capture scoring for the product placement study.",
    version="0.1.0",
)

# The browser runs outside the compose network, so it reaches this API on
# localhost even though the web container reaches it as http://api:8000.
# Both loopback spellings are allowed because a browser may use either.
_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("PP_CORS_ORIGINS", _default_origins).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """Liveness probe. Reports whether the artifacts are actually readable,
    because a process that is up but cannot see its data is not healthy."""
    try:
        n_categories = len(artifacts.load_categories())
        n_strong = len(artifacts.load_strong_rules())
    except FileNotFoundError as exc:
        return {"status": "degraded", "detail": str(exc)}
    return {
        "status": "ok",
        "artifacts_dir": str(artifacts.ARTIFACTS_DIR),
        "categories": n_categories,
        "strong_rules": n_strong,
    }


@app.get("/api/categories")
def categories():
    """The 25 product categories with basket penetration.

    appears_in_strong_rules is false for the 13 categories that occur in no
    rule at lift 3.0 or above, which can never affect a layout score. Note the
    distinction: only 5 categories appear in no rule at all, but the strong
    threshold of lift 3.0 excludes a further 8.
    """
    items = artifacts.load_categories()
    return {
        "count": len(items),
        "categories": items,
        "note": (
            "Categories with appears_in_strong_rules = false occur in no rule "
            "at lift 3.0 or above, so moving them between zones cannot change "
            "the cross-sell score."
        ),
    }


@app.get("/api/zones")
def zones():
    """The five physical placement zones with their ethics classification."""
    return {"zones": service.zones_payload()}


@app.get("/api/layout/existing")
def layout_existing():
    """The frequency-driven baseline: what the store approximates today."""
    return {
        "id": "existing",
        "name": "Existing layout",
        "description": "Frequency-based k-means clusters, the unoptimised baseline",
        "assignment": service.existing_assignment(),
    }


@app.get("/api/layout/proposed")
def layout_proposed():
    """The five-zone layout derived in notebook 07."""
    return {
        "id": "proposed",
        "name": "Proposed layout",
        "description": "Five placement zones derived from the association rules",
        "assignment": service.proposed_assignment(),
    }


@app.get("/api/layout/optimal")
def layout_optimal(constrained: bool = True, capacity_matched: bool = False):
    """The best computed assignment (analysis/optimise_zones.py, fixed seed).

    constrained applies the study's stated constraints: dairy and frozen foods
    locked to the cold-storage zone, alcohol and tobacco barred from the
    entrance zone (the section 13.5 boundary).

    Two facts the caller should know. The scoring metric has no notion of
    shelf capacity, so without capacity_matched the optimum is one mega-zone
    holding all 12 rule-bearing categories at 100% capture: the metric's
    ceiling, not a shelf plan. And the constraints cost zero capture, because
    none of the four constrained categories appears in any strong rule.
    capacity_matched=true fixes each zone's size to its size in the proposed
    layout, which makes the answer a usable plan. First call per variant
    computes (seconds); afterwards it is cached.
    """
    result = service.optimal_result(constrained, capacity_matched)
    variant = "constrained" if constrained else "unconstrained"
    if capacity_matched:
        variant += ", capacity-matched"
    return {
        "id": "optimal_" + variant.replace(", ", "_").replace("-", "_"),
        "name": "Best computed layout",
        "description": (
            f"Greedy local search, {result['restarts']} restarts, "
            f"seed {result['seed']} ({variant})"
        ),
        "constrained": constrained,
        "capacity_matched": capacity_matched,
        "assignment": result["assignment"],
        "rules_captured": result["rules_captured"],
        "support_captured": round(result["support_captured"], 4),
        "capture_rate": round(result["capture_rate"], 2),
        "note": (
            "Categories with no strong rule cannot affect the score and stay "
            "at their proposed positions."
        ),
    }


@app.get("/api/rules/strong")
def rules_strong():
    """Every rule at or above the strong threshold of lift 3.0."""
    rules = service.strong_rules()
    return {
        "lift_floor": 3.0,
        "count": len(rules),
        "total_support": round(sum(r["support"] for r in rules), 4),
        "rules": [
            {
                "label": r["label"],
                "antecedents": r["antecedents"],
                "consequents": r["consequents"],
                "support": r["support"],
                "confidence": r["confidence"],
                "lift": r["lift"],
            }
            for r in rules
        ],
    }


class LayoutRequest(BaseModel):
    assignment: Dict[str, str] = Field(
        ...,
        description="Mapping of category name to zone id. Categories left out "
                    "are treated as unplaced and cannot contribute to a score.",
    )


@app.post("/api/layout/score")
def score_layout_endpoint(payload: LayoutRequest):
    """Score any category to zone assignment.

    Uses analysis.cross_sell.score_layout, the same function that produces the
    figures in the dissertation, so the tool cannot disagree with the thesis.
    """
    known = {c["name"] for c in artifacts.load_categories()}
    unknown = sorted(set(payload.assignment) - known)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown categories: {unknown}",
        )
    return service.score(payload.assignment)
