"""
recommender_baselines.py

Score the notebook 09 product recommender against popularity and random
baselines, on the same test baskets, and measure its coverage.

    python analysis/recommender_baselines.py

WHY THIS EXISTS
    config/metrics.py carried thirteen REC_* constants under the comment
    "notebook 09 evaluation, measured 2026-08-14". Notebook 09 computes two of
    them (19,808 test baskets and the 28.0 per cent hit rate) and none of the
    other eleven: the baselines, the coverage split and the recommendation
    budget had no producing code and could not be reproduced or checked. This
    module is that code, written on 17 August 2026.

WHAT IT REPRODUCES
    The notebook 09 pipeline exactly, so the model figure is like for like:
    top 100 products by basket count, TransactionEncoder, a 70/30 split at
    random_state=42, apriori at 0.5 per cent support, rules at lift >= 1.0, and
    for a given product the top 5 consequents by lift.

    One quirk of the notebook is reproduced deliberately rather than corrected.
    Its recommender matches a rule when the queried product appears anywhere in
    the antecedent set, without requiring the rule's other antecedents to be in
    the basket. That is a loose match and it inflates coverage slightly, but
    correcting it here would mean this module no longer measured the recommender
    the dissertation describes. It is noted in the report instead.

HOW A BASKET IS SCORED
    A test basket with at least two products is used. Its last product is hidden
    and becomes the target; the rest are the known products. A system hits if the
    target is among what it recommends.

    model                 union of the top 5 consequents for each known product
    popularity, matched   the k most popular products not already in the basket,
                          where k is the number of recommendations the model
                          produced for THAT basket. A baseline cannot win by
                          guessing more often than the model was allowed to.
    popularity, top 5     the 5 most popular products, always, as a deployed
                          popularity widget would behave
    random, matched       k products drawn uniformly from the 100, seeded
    random, top 5         5 products drawn uniformly, seeded

    Popularity is ranked on the TRAINING baskets only, so no test information
    reaches any system.
"""

from __future__ import annotations

import json
import os
import random
import sys
from datetime import datetime

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from sklearn.model_selection import train_test_split

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

SALES_PATH = os.path.join(ROOT, "data", "processed", "sales_data_cleaned.csv")
OUT_MD = os.path.join(ROOT, "reports", "recommender_baselines.md")
OUT_JSON = os.path.join(ROOT, "dashboard", "artifacts",
                        "recommender_baselines_summary.json")

# Notebook 09's parameters, unchanged.
TOP_PRODUCTS = 100
TEST_SIZE = 0.3
SPLIT_SEED = 42
MIN_SUPPORT = 0.005
MIN_LIFT = 1.0
TOP_N_RECS = 5
RANDOM_SEED = 42


def build_rules(train_df):
    itemsets = apriori(train_df, min_support=MIN_SUPPORT, use_colnames=True)
    rules = association_rules(itemsets, metric="lift", min_threshold=MIN_LIFT)
    return rules.sort_values("lift", ascending=False).reset_index(drop=True)


def recs_by_product(rules):
    """product -> its top 5 recommended products by lift.

    Mirrors notebook 09's get_recommendations: every product named anywhere in
    the antecedent set maps to every product in the consequent set, consequents
    are deduplicated on their maximum lift, then the best 5 are kept.
    """
    best: dict[str, dict[str, float]] = {}
    for r in rules.itertuples(index=False):
        lift = float(r.lift)
        for a in r.antecedents:
            slot = best.setdefault(a, {})
            for c in r.consequents:
                if lift > slot.get(c, 0.0):
                    slot[c] = lift
    out = {}
    for a, cons in best.items():
        ranked = sorted(cons.items(), key=lambda kv: -kv[1])[:TOP_N_RECS]
        out[a] = [c for c, _ in ranked]
    return out


def main() -> int:
    if not os.path.exists(SALES_PATH):
        print("ERROR: data/processed/sales_data_cleaned.csv not found.")
        return 1

    print("Reading cleaned transactions ...", flush=True)
    df = pd.read_csv(SALES_PATH, usecols=["invoice_no", "product"])

    top = df.groupby("product")["invoice_no"].nunique().nlargest(TOP_PRODUCTS)
    df_top = df[df["product"].isin(top.index)]
    print(f"  top {TOP_PRODUCTS} products, {df_top['invoice_no'].nunique():,} baskets "
          "containing at least one of them")

    lists = df_top.groupby("invoice_no")["product"].apply(list)
    te = TransactionEncoder()
    basket = pd.DataFrame(te.fit(lists).transform(lists), columns=te.columns_)
    train_df, test_df = train_test_split(
        basket, test_size=TEST_SIZE, random_state=SPLIT_SEED)
    print(f"  train {len(train_df):,} / test {len(test_df):,}")

    print(f"Mining product rules at {MIN_SUPPORT:.1%} support ...", flush=True)
    rules = build_rules(train_df)
    table = recs_by_product(rules)
    print(f"  {len(rules):,} rules, {len(table)} products carry at least one rule")

    # popularity ranked on the training baskets only
    popularity = train_df.sum().sort_values(ascending=False)
    pop_order = list(popularity.index)

    cols = list(basket.columns)
    rng = random.Random(RANDOM_SEED)

    tested = 0
    hits = {"model": 0, "pop_matched": 0, "pop_top5": 0,
            "rand_matched": 0, "rand_top5": 0}
    covered = 0
    covered_hits = {"model": 0, "pop_matched": 0}
    total_recs = 0
    covered_recs = 0

    print("Scoring the test baskets ...", flush=True)
    values = test_df.values
    for row in values:
        bought = [cols[i] for i, v in enumerate(row) if v]
        if len(bought) < 2:
            continue
        target = bought[-1]
        known = bought[:-1]
        known_set = set(known)

        model_recs = set()
        for k in known:
            model_recs.update(table.get(k, ()))
        budget = len(model_recs)

        tested += 1
        total_recs += budget
        is_covered = budget > 0
        if is_covered:
            covered += 1
            covered_recs += budget

        model_hit = target in model_recs
        if model_hit:
            hits["model"] += 1

        pop_pool = [p for p in pop_order if p not in known_set]
        pop_matched = set(pop_pool[:budget])
        pop_top5 = set(pop_pool[:TOP_N_RECS])
        pop_matched_hit = target in pop_matched
        if pop_matched_hit:
            hits["pop_matched"] += 1
        if target in pop_top5:
            hits["pop_top5"] += 1

        rand_pool = [p for p in cols if p not in known_set]
        if budget:
            if budget >= len(rand_pool):
                rand_matched = set(rand_pool)
            else:
                rand_matched = set(rng.sample(rand_pool, budget))
            if target in rand_matched:
                hits["rand_matched"] += 1
        rand_top5 = set(rng.sample(rand_pool, min(TOP_N_RECS, len(rand_pool))))
        if target in rand_top5:
            hits["rand_top5"] += 1

        if is_covered:
            if model_hit:
                covered_hits["model"] += 1
            if pop_matched_hit:
                covered_hits["pop_matched"] += 1

    pct = lambda n: round(n / tested * 100, 2) if tested else 0.0
    cpct = lambda n: round(n / covered * 100, 2) if covered else 0.0

    summary = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "parameters": {
            "top_products": TOP_PRODUCTS, "test_size": TEST_SIZE,
            "split_seed": SPLIT_SEED, "min_support": MIN_SUPPORT,
            "min_lift": MIN_LIFT, "top_n_recs": TOP_N_RECS,
            "random_seed": RANDOM_SEED,
        },
        "split": {"train_baskets": int(len(train_df)),
                  "test_baskets": int(len(test_df))},
        "rules": int(len(rules)),
        "products_with_rules": int(len(table)),
        "test_baskets_scored": tested,
        "model_hits": hits["model"],
        "model_hit_pct": pct(hits["model"]),
        "popularity_matched_pct": pct(hits["pop_matched"]),
        "popularity_top5_pct": pct(hits["pop_top5"]),
        "random_matched_pct": pct(hits["rand_matched"]),
        "random_top5_pct": pct(hits["rand_top5"]),
        "avg_recs_per_basket": round(total_recs / tested, 2) if tested else 0.0,
        "avg_recs_when_covered": round(covered_recs / covered, 2) if covered else 0.0,
        "covered_baskets": covered,
        "uncovered_baskets": tested - covered,
        "covered_model_pct": cpct(covered_hits["model"]),
        "covered_popularity_pct": cpct(covered_hits["pop_matched"]),
    }

    print()
    print("=" * 70)
    print("RECOMMENDER BASELINES")
    print("=" * 70)
    print(f"  train / test baskets          {len(train_df):>8,} / {len(test_df):,}")
    print(f"  product rules                 {len(rules):>8,}")
    print(f"  products carrying a rule      {len(table):>8}")
    print(f"  multi-product test baskets    {tested:>8,}")
    print()
    print(f"  model hit rate                {summary['model_hit_pct']:>8.2f}%  "
          f"({hits['model']:,} hits)")
    print(f"  popularity, matched budget    {summary['popularity_matched_pct']:>8.2f}%")
    print(f"  popularity, unconstrained 5   {summary['popularity_top5_pct']:>8.2f}%")
    print(f"  random, matched budget        {summary['random_matched_pct']:>8.2f}%")
    print(f"  random, unconstrained 5       {summary['random_top5_pct']:>8.2f}%")
    print()
    print(f"  avg recommendations / basket  {summary['avg_recs_per_basket']:>8.2f}")
    print(f"  avg when covered              {summary['avg_recs_when_covered']:>8.2f}")
    print(f"  covered baskets               {summary['covered_baskets']:>8,}")
    print(f"  uncovered baskets             {summary['uncovered_baskets']:>8,}")
    print(f"  model, where covered          {summary['covered_model_pct']:>8.2f}%")
    print(f"  popularity, where covered     {summary['covered_popularity_pct']:>8.2f}%")

    write_report(summary)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(f"\nWrote {os.path.relpath(OUT_MD, ROOT)}")
    print(f"Wrote {os.path.relpath(OUT_JSON, ROOT)}")
    return 0


def write_report(s):
    L = ["# Product recommender against its baselines", ""]
    L.append(f"Generated {s['generated']} by `analysis/recommender_baselines.py`.")
    L.append("")
    L.append("Notebook 09 reports a hit rate. A hit rate on its own cannot say "
             "whether the recommender\nlearned anything, because a system that "
             "always names the shop's best sellers also scores.\nThis compares "
             "the model against popularity and random on the same baskets, under "
             "the same\nrecommendation budget.")
    L.append("")
    L.append("## Setup")
    L.append("")
    p = s["parameters"]
    L.append(f"Notebook 09's parameters, unchanged: top {p['top_products']} products, "
             f"{int((1 - p['test_size']) * 100)}/{int(p['test_size'] * 100)} split at "
             f"random_state={p['split_seed']}, apriori at {p['min_support']:.1%} "
             f"support,\nrules at lift >= {p['min_lift']}, top {p['top_n_recs']} "
             f"consequents by lift. Random baselines seeded at {p['random_seed']}.")
    L.append("")
    L.append("| | value |")
    L.append("|---|---:|")
    L.append(f"| training baskets | {s['split']['train_baskets']:,} |")
    L.append(f"| test baskets | {s['split']['test_baskets']:,} |")
    L.append(f"| product rules mined | {s['rules']:,} |")
    L.append(f"| products carrying at least one rule | {s['products_with_rules']} "
             f"of {p['top_products']} |")
    L.append(f"| multi-product test baskets scored | {s['test_baskets_scored']:,} |")
    L.append("")
    L.append("## Hit rate against the baselines")
    L.append("")
    L.append("| system | budget | hit rate |")
    L.append("|---|---|---:|")
    L.append(f"| **model (association rules)** | up to 5 per known product "
             f"| **{s['model_hit_pct']:.2f}%** |")
    L.append(f"| popularity | matched to the model | {s['popularity_matched_pct']:.2f}% |")
    L.append(f"| popularity | unconstrained top 5 | {s['popularity_top5_pct']:.2f}% |")
    L.append(f"| random | matched to the model | {s['random_matched_pct']:.2f}% |")
    L.append(f"| random | unconstrained top 5 | {s['random_top5_pct']:.2f}% |")
    L.append("")
    L.append("## Coverage, which is what constrains the headline")
    L.append("")
    L.append("The model can only answer when one of the basket's known products "
             "carries a mined rule.")
    L.append("")
    L.append("| | value |")
    L.append("|---|---:|")
    L.append(f"| average recommendations per basket | {s['avg_recs_per_basket']:.2f} |")
    L.append(f"| average when the model can answer | {s['avg_recs_when_covered']:.2f} |")
    L.append(f"| covered baskets | {s['covered_baskets']:,} |")
    L.append(f"| uncovered baskets | {s['uncovered_baskets']:,} |")
    L.append(f"| **model hit rate where covered** | **{s['covered_model_pct']:.2f}%** |")
    L.append(f"| popularity hit rate where covered | {s['covered_popularity_pct']:.2f}% |")
    L.append("")
    L.append("## Reading this honestly")
    L.append("")
    beats_matched = s["model_hit_pct"] > s["popularity_matched_pct"]
    loses_top5 = s["model_hit_pct"] < s["popularity_top5_pct"]
    L.append(f"- At a matched budget the model {'beats' if beats_matched else 'does NOT beat'} "
             f"popularity, {s['model_hit_pct']:.2f}% against "
             f"{s['popularity_matched_pct']:.2f}%.")
    L.append(f"- Against an unconstrained popularity widget the model "
             f"{'loses' if loses_top5 else 'still wins'}, "
             f"{s['model_hit_pct']:.2f}% against {s['popularity_top5_pct']:.2f}%. "
             "Both are reported\n  because the choice of budget rule changes the "
             "conclusion.")
    L.append(f"- Where the model has coverage it reaches {s['covered_model_pct']:.2f}% "
             f"against popularity's {s['covered_popularity_pct']:.2f}%. Coverage, not "
             "ranking quality,\n  is the binding limitation.")
    L.append("")
    L.append("Notebook 09's recommender matches a rule when the queried product "
             "appears anywhere in the\nantecedent set, without requiring the rule's "
             "other antecedents to be present in the basket.\nThat loose match is "
             "reproduced here deliberately, so this measures the recommender the\n"
             "dissertation describes rather than a corrected one. It inflates "
             "coverage slightly.")
    L.append("")
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
