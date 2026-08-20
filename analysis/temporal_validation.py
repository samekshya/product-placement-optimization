"""
temporal_validation.py

Do the category association rules hold in a period they were not mined from?

    python analysis/temporal_validation.py

WHY THIS EXISTS
    config/metrics.py carried RULE_STABILITY_MEDIAN = 1.011 with the comment
    "notebook 05 Step 9 temporal validation", and PROJECT_RECORD.md described a
    development/validation split in prose. No such step existed in any notebook
    or module: the figure had no producing code and could not be reproduced or
    checked. This module is that code, written from scratch on 17 August 2026.

METHOD
    Split the cleaned transactions by date into two windows that do not overlap:

        development   2025-07-17 to 2026-01-31
        validation    2026-02-01 to 2026-05-20

    Mine association rules on the development window ONLY, with notebook 05's
    thresholds: apriori at 1 per cent minimum support, then rules at lift >= 1.0.
    Then, for every rule found, recompute its lift on the validation baskets and
    take the ratio.

        stability = lift in validation / lift in development

    A ratio near 1.0 means the association is as strong in a period the rule was
    not mined from. A ratio below 0.5 means it more than halved.

    Lift is recomputed from validation support directly rather than by re-mining,
    because re-mining would discard any rule that fell under the support floor in
    the second window and would bias the result towards rules that survived.

    Rules whose antecedent or consequent never appears in the validation window
    have no defined validation lift (division by zero). They are counted and
    excluded from the median rather than being silently treated as zero.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

SALES_PATH = os.path.join(ROOT, "data", "processed", "sales_data_cleaned.csv")
OUT_MD = os.path.join(ROOT, "reports", "temporal_validation.md")
OUT_JSON = os.path.join(ROOT, "dashboard", "artifacts",
                        "temporal_validation_summary.json")

# Notebook 05's thresholds, unchanged.
MIN_SUPPORT = 0.01
MIN_LIFT = 1.0

# The two windows. Boundaries are inclusive.
DEV_START, DEV_END = "2025-07-17", "2026-01-31"
VAL_START, VAL_END = "2026-02-01", "2026-05-20"

STRONG_LIFT = 3.0
TOP_N = 20
RATIO_FLOOR = 0.5


def basket_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """One row per invoice, one boolean column per category."""
    return (
        df.groupby("invoice_no")["category"]
        .apply(lambda s: pd.Series(1, index=s.unique()))
        .unstack(fill_value=0)
        .astype(bool)
    )


def support_of(matrix: pd.DataFrame, items) -> float:
    """Share of baskets containing every item in `items`."""
    cols = list(items)
    missing = [c for c in cols if c not in matrix.columns]
    if missing:
        return 0.0
    return float(matrix[cols].all(axis=1).mean())


def mine(matrix: pd.DataFrame) -> pd.DataFrame:
    """Notebook 05's mining, on whatever window is passed in."""
    itemsets = apriori(matrix, min_support=MIN_SUPPORT, use_colnames=True)
    rules = association_rules(itemsets, metric="lift", min_threshold=MIN_LIFT)
    return rules.sort_values("lift", ascending=False).reset_index(drop=True)


def validate(dev_rules: pd.DataFrame, val: pd.DataFrame) -> pd.DataFrame:
    """Recompute each development rule's lift on the validation baskets."""
    rows = []
    for r in dev_rules.itertuples(index=False):
        a, c = set(r.antecedents), set(r.consequents)
        sa = support_of(val, a)
        sc = support_of(val, c)
        sac = support_of(val, a | c)
        if sa == 0 or sc == 0:
            val_lift = None
        else:
            val_lift = sac / (sa * sc)
        rows.append({
            "antecedents": ", ".join(sorted(a)),
            "consequents": ", ".join(sorted(c)),
            "dev_support": r.support,
            "dev_lift": r.lift,
            "val_support": sac,
            "val_lift": val_lift,
            "ratio": None if val_lift is None else val_lift / r.lift,
        })
    return pd.DataFrame(rows)


def main() -> int:
    if not os.path.exists(SALES_PATH):
        print("ERROR: data/processed/sales_data_cleaned.csv not found. "
              "Run notebooks 01 and 02 first.")
        return 1

    print("Reading cleaned transactions ...", flush=True)
    df = pd.read_csv(SALES_PATH, usecols=["date", "invoice_no", "category"])
    df["date"] = pd.to_datetime(df["date"])

    dev_rows = df[(df["date"] >= DEV_START) & (df["date"] <= DEV_END)]
    val_rows = df[(df["date"] >= VAL_START) & (df["date"] <= VAL_END)]
    covered = len(dev_rows) + len(val_rows)
    if covered != len(df):
        print(f"WARNING: {len(df) - covered:,} line items fall outside both "
              "windows and are excluded.")

    dev = basket_matrix(dev_rows)
    val = basket_matrix(val_rows)
    print(f"  development {DEV_START} to {DEV_END}: {len(dev):,} baskets")
    print(f"  validation  {VAL_START} to {VAL_END}: {len(val):,} baskets")

    print(f"Mining development window at {MIN_SUPPORT:.0%} support ...", flush=True)
    dev_rules = mine(dev)
    print(f"  {len(dev_rules):,} rules")

    print("Recomputing each rule's lift on the validation window ...", flush=True)
    res = validate(dev_rules, val)

    defined = res[res["ratio"].notna()]
    undefined = len(res) - len(defined)
    median_ratio = float(defined["ratio"].median())
    min_ratio = float(defined["ratio"].min())
    max_ratio = float(defined["ratio"].max())
    mean_ratio = float(defined["ratio"].mean())
    below_floor = int((defined["ratio"] < RATIO_FLOOR).sum())

    top = res.head(TOP_N)
    top_defined = top[top["val_lift"].notna()]
    top_strong = int((top_defined["val_lift"] >= STRONG_LIFT).sum())
    top_min_ratio = float(top_defined["ratio"].min())
    top_max_ratio = float(top_defined["ratio"].max())
    top_mean_ratio = float(top_defined["ratio"].mean())

    strong_dev = res[res["dev_lift"] >= STRONG_LIFT]
    strong_dev_defined = strong_dev[strong_dev["val_lift"].notna()]
    strong_still = int((strong_dev_defined["val_lift"] >= STRONG_LIFT).sum())

    print()
    print("=" * 70)
    print("TEMPORAL VALIDATION RESULT")
    print("=" * 70)
    print(f"  development baskets           {len(dev):>10,}")
    print(f"  validation baskets            {len(val):>10,}")
    print(f"  development rules             {len(dev_rules):>10,}")
    print(f"  rules with a defined ratio    {len(defined):>10,}")
    print(f"  rules with no defined ratio   {undefined:>10,}")
    print()
    print(f"  MEDIAN stability ratio        {median_ratio:>10.3f}")
    print(f"  MINIMUM stability ratio       {min_ratio:>10.3f}")
    print(f"  maximum stability ratio       {max_ratio:>10.3f}")
    print(f"  mean stability ratio          {mean_ratio:>10.3f}")
    print(f"  rules below ratio {RATIO_FLOOR}         {below_floor:>10,}")
    print()
    print(f"  top {TOP_N} dev rules with validation lift >= {STRONG_LIFT}: "
          f"{top_strong} of {len(top_defined)}")
    print(f"  top {TOP_N} ratio range        {top_min_ratio:.3f} to {top_max_ratio:.3f} "
          f"(mean {top_mean_ratio:.3f})")
    print(f"  all dev rules at lift >= {STRONG_LIFT} still >= {STRONG_LIFT} in "
          f"validation: {strong_still} of {len(strong_dev_defined)}")

    write_report(
        dev, val, dev_rules, res, defined, undefined,
        median_ratio, min_ratio, max_ratio, mean_ratio, below_floor,
        top, top_defined, top_strong, top_min_ratio, top_max_ratio,
        strong_dev_defined, strong_still,
    )
    print(f"\nWrote {os.path.relpath(OUT_MD, ROOT)}")

    # Artifact, so scripts/verify_thesis_numbers.py can check the constants
    # without re-mining. Same pattern as daily_forecast_summary.json.
    summary = {
        "windows": {
            "development": {"start": DEV_START, "end": DEV_END,
                            "baskets": int(len(dev))},
            "validation": {"start": VAL_START, "end": VAL_END,
                           "baskets": int(len(val))},
        },
        "thresholds": {"min_support": MIN_SUPPORT, "min_lift": MIN_LIFT,
                       "strong_lift": STRONG_LIFT, "ratio_floor": RATIO_FLOOR,
                       "top_n": TOP_N},
        "dev_rules": int(len(dev_rules)),
        "rules_with_defined_ratio": int(len(defined)),
        "rules_without_defined_ratio": int(undefined),
        "median_ratio": round(median_ratio, 4),
        "min_ratio": round(min_ratio, 4),
        "max_ratio": round(max_ratio, 4),
        "mean_ratio": round(mean_ratio, 4),
        "rules_below_ratio_floor": below_floor,
        "top_n_still_strong": top_strong,
        "top_n_evaluated": int(len(top_defined)),
        "top_n_ratio_min": round(top_min_ratio, 4),
        "top_n_ratio_max": round(top_max_ratio, 4),
        "strong_dev_rules": int(len(strong_dev_defined)),
        "strong_dev_rules_still_strong": strong_still,
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(f"Wrote {os.path.relpath(OUT_JSON, ROOT)}")
    return 0


def write_report(dev, val, dev_rules, res, defined, undefined,
                 median_ratio, min_ratio, max_ratio, mean_ratio, below_floor,
                 top, top_defined, top_strong, top_min_ratio, top_max_ratio,
                 strong_dev_defined, strong_still):
    L = []
    L.append("# Temporal validation of the category association rules")
    L.append("")
    L.append(f"Generated {datetime.now():%Y-%m-%d %H:%M:%S} by "
             "`analysis/temporal_validation.py`.")
    L.append("")
    L.append("Do the rules hold in a period they were not mined from? Rules are "
             "mined on the development\nwindow only, then each rule's lift is "
             "recomputed on the validation window and compared.")
    L.append("")
    L.append("## Windows")
    L.append("")
    L.append("| window | dates | baskets |")
    L.append("|---|---|---:|")
    L.append(f"| development | {DEV_START} to {DEV_END} | {len(dev):,} |")
    L.append(f"| validation | {VAL_START} to {VAL_END} | {len(val):,} |")
    L.append(f"| **total** | | **{len(dev) + len(val):,}** |")
    L.append("")
    L.append("## Method")
    L.append("")
    L.append(f"Apriori at {MIN_SUPPORT:.0%} minimum support on the development "
             f"window, then rules at lift >= {MIN_LIFT}, which are notebook 05's "
             "thresholds unchanged. For each\nrule, `stability = validation lift "
             "/ development lift`.")
    L.append("")
    L.append("Validation lift is recomputed from validation support directly "
             "rather than by re-mining the\nsecond window. Re-mining would drop "
             "any rule that fell below the support floor there, which\nwould "
             "select for rules that survived and bias the result upward.")
    L.append("")
    L.append("## Result")
    L.append("")
    L.append("| figure | value |")
    L.append("|---|---:|")
    L.append(f"| development rules mined | {len(dev_rules):,} |")
    L.append(f"| rules with a defined validation lift | {len(defined):,} |")
    L.append(f"| rules with no defined validation lift | {undefined:,} |")
    L.append(f"| **median stability ratio** | **{median_ratio:.3f}** |")
    L.append(f"| **minimum stability ratio** | **{min_ratio:.3f}** |")
    L.append(f"| maximum stability ratio | {max_ratio:.3f} |")
    L.append(f"| mean stability ratio | {mean_ratio:.3f} |")
    L.append(f"| **rules below ratio {RATIO_FLOOR}** | **{below_floor:,}** |")
    L.append(f"| top {TOP_N} dev rules with validation lift >= {STRONG_LIFT} "
             f"| {top_strong} of {len(top_defined)} |")
    L.append(f"| all dev rules at lift >= {STRONG_LIFT} still >= {STRONG_LIFT} "
             f"in validation | {strong_still} of {len(strong_dev_defined)} |")
    L.append("")
    L.append(f"## Top {TOP_N} development rules by lift")
    L.append("")
    L.append("| # | antecedents | consequents | dev lift | val lift | ratio |")
    L.append("|---:|---|---|---:|---:|---:|")
    for i, r in enumerate(top.itertuples(index=False), 1):
        vl = "undefined" if r.val_lift is None else f"{r.val_lift:.3f}"
        rt = "undefined" if r.ratio is None else f"{r.ratio:.3f}"
        L.append(f"| {i} | {r.antecedents} | {r.consequents} | "
                 f"{r.dev_lift:.3f} | {vl} | {rt} |")
    L.append("")
    worst = defined.nsmallest(10, "ratio")
    L.append("## Ten least stable rules")
    L.append("")
    L.append("| antecedents | consequents | dev lift | val lift | ratio |")
    L.append("|---|---|---:|---:|---:|")
    for r in worst.itertuples(index=False):
        L.append(f"| {r.antecedents} | {r.consequents} | {r.dev_lift:.3f} | "
                 f"{r.val_lift:.3f} | {r.ratio:.3f} |")
    L.append("")
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
