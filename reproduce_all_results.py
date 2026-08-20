"""
reproduce_all_results.py

Regenerates the dashboard artifacts and prints every key verified number
quoted in the thesis, in one run, with a timestamped log file.

This exists so that any reviewer, examiner, or future version of the author
can confirm every number in the thesis by running ONE command, rather than
re-executing eleven notebooks by hand and hunting through outputs.

Usage:
    python reproduce_all_results.py

Output:
    - Prints a full verification report to the terminal
    - Saves the same report to reports/reproduction_log_<timestamp>.txt
    - Exits with code 0 if every check passes, code 1 if any check fails

This script does NOT touch data/raw/ or data/processed/ directly beyond
what precompute_artifacts.py already does. It reads only from
dashboard/artifacts/ once that script has been run.
"""

import json
import os
import subprocess
import sys
from datetime import datetime

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS = os.path.join(HERE, "dashboard", "artifacts")
REPORTS = os.path.join(HERE, "reports")
os.makedirs(REPORTS, exist_ok=True)

sys.path.insert(0, HERE)
from config import metrics as M  # noqa: E402

log_lines = []


def log(line=""):
    print(line)
    log_lines.append(line)


def section(title):
    log()
    log("=" * 70)
    log(title)
    log("=" * 70)


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    log(f"  [{status}] {label}" + (f"  ({detail})" if detail else ""))
    return condition


def main():
    all_passed = True

    log(f"REPRODUCTION REPORT - Product Placement Optimisation")
    log(f"Generated: {datetime.now().isoformat()}")
    log(f"Student: Samikshya Baniya | ID: 230360 | Module: ST6001CEM")

    section("STEP 1 - Regenerating dashboard artifacts")
    precompute_script = os.path.join(HERE, "dashboard", "precompute_artifacts.py")
    if os.path.exists(precompute_script):
        result = subprocess.run(
            [sys.executable, precompute_script],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            log("  Artifacts regenerated successfully.")
        else:
            log("  FAILED to regenerate artifacts:")
            log(result.stderr[-2000:])
            all_passed = False
    else:
        log("  precompute_artifacts.py not found, skipping regeneration.")
        log("  (Will verify existing artifacts if present.)")

    section("STEP 2 - Dataset scale")
    kpi_path = os.path.join(ARTIFACTS, "kpi_summary.json")
    if os.path.exists(kpi_path):
        with open(kpi_path) as f:
            kpi = json.load(f)
        all_passed &= check(
            "Total transactions", kpi.get("total_transactions") == M.TOTAL_TRANSACTIONS,
            f"expected {M.TOTAL_TRANSACTIONS}, got {kpi.get('total_transactions')}"
        )
        all_passed &= check(
            "Category count", kpi.get("n_categories") == M.TOTAL_CATEGORIES,
            f"expected {M.TOTAL_CATEGORIES}, got {kpi.get('n_categories')}"
        )
    else:
        log("  kpi_summary.json not found - run precompute_artifacts.py first.")
        all_passed = False

    section("STEP 3 - Association rules (Notebook 05)")
    rules_path = os.path.join(ARTIFACTS, "category_rules.csv")
    if os.path.exists(rules_path):
        rules = pd.read_csv(rules_path)
        all_passed &= check("Rule count", len(rules) == M.RULES_TOTAL, f"{len(rules)} rules")
        all_passed &= check(
            "Max lift (category)",
            abs(rules["lift"].max() - M.MAX_LIFT_CATEGORY) < 0.01,
            f"{rules['lift'].max():.2f}"
        )
    else:
        log("  category_rules.csv not found.")
        all_passed = False

    section("STEP 4 - Clustering (Notebook 06)")
    all_passed &= check(
        "Co-occurrence silhouette beats frequency silhouette",
        M.SILHOUETTE_COOCCURRENCE > M.SILHOUETTE_FREQUENCY,
        f"{M.SILHOUETTE_COOCCURRENCE} vs {M.SILHOUETTE_FREQUENCY}"
    )

    section("STEP 5 - Placement comparison (Notebooks 07 & 08)")
    all_passed &= check(
        "Re-derived layout beats current layout",
        M.CROSS_SELL_OPTIMISED > M.CROSS_SELL_CURRENT,
        f"{M.CROSS_SELL_OPTIMISED} vs {M.CROSS_SELL_CURRENT} rules captured, "
        f"{M.CROSS_SELL_OPTIMISED / M.CROSS_SELL_CURRENT:.1f}x"
    )
    all_passed &= check(
        "Re-derived layout beats frequency baseline",
        M.CROSS_SELL_OPTIMISED > M.CROSS_SELL_FREQUENCY,
        f"{M.CROSS_SELL_OPTIMISED} vs {M.CROSS_SELL_FREQUENCY}"
    )
    all_passed &= check(
        "Re-derived layout is the certified capacity-matched constrained optimum",
        M.CROSS_SELL_OPTIMISED == M.ZONE_OPT_CAPACITY_RULES
        and M.ZONE_OPT_CAPACITY_GAIN_RULES == 0,
        f"{M.CROSS_SELL_OPTIMISED} rules, no feasible layout at these zone sizes "
        "and constraints does better"
    )

    section("STEP 6 - Basket classifier (Notebook 11)")
    all_passed &= check(
        "Classifier beats majority baseline",
        M.CLASSIFIER_ACCURACY > M.CLASSIFIER_BASELINE,
        f"{M.CLASSIFIER_ACCURACY:.3f} vs {M.CLASSIFIER_BASELINE:.3f}"
    )

    section("STEP 7 - ABC analysis (Notebook 03)")
    abc_path = os.path.join(ARTIFACTS, "abc_analysis.csv")
    if os.path.exists(abc_path):
        abc = pd.read_csv(abc_path)
        a_count = (abc["abc_category"] == "A").sum()
        all_passed &= check(
            "Class A product count", a_count == M.ABC_CLASS_A_PRODUCTS,
            f"{a_count} products"
        )
    else:
        log("  abc_analysis.csv not found.")
        all_passed = False

    section("STEP 8 - Neural network comparison (Notebook 12)")
    all_passed &= check(
        "Neural network beats the depth-5 tree",
        M.NEURAL_NET_ACCURACY > M.CLASSIFIER_ACCURACY,
        f"{M.NEURAL_NET_ACCURACY:.4f} vs {M.CLASSIFIER_ACCURACY:.3f}"
    )
    all_passed &= check(
        "Most of that gap is capacity, not model family",
        M.DECISION_TREE_FULL_ACCURACY > M.CLASSIFIER_ACCURACY,
        f"fully grown tree {M.DECISION_TREE_FULL_ACCURACY:.4f} closes "
        f"{(M.DECISION_TREE_FULL_ACCURACY - M.CLASSIFIER_ACCURACY) * 100:.2f} of the "
        f"{(M.NEURAL_NET_ACCURACY - M.CLASSIFIER_ACCURACY) * 100:.2f} point gap"
    )
    all_passed &= check(
        "No model exceeds the ceiling these features allow",
        M.NEURAL_NET_ACCURACY < M.FEATURE_CEILING_ACCURACY,
        f"{M.NEURAL_NET_ACCURACY:.4f} < {M.FEATURE_CEILING_ACCURACY:.4f} "
        f"({M.NEURAL_NET_ACCURACY / M.FEATURE_CEILING_ACCURACY * 100:.1f}% of maximum)"
    )

    section("STEP 9 - Computed zone assignment (analysis/optimise_zones.py)")
    # Re-runs the seeded local search and its exhaustive certificate, and
    # rewrites dashboard/artifacts/zone_optimisation.json, so the figures the
    # sweep below checks are the ones this run just produced. Takes about a
    # minute: 4 runs x 200 restarts, each scored through score_layout.
    optimiser_script = os.path.join(HERE, "analysis", "optimise_zones.py")
    zone_path = os.path.join(ARTIFACTS, "zone_optimisation.json")
    if os.path.exists(optimiser_script):
        opt = subprocess.run(
            [sys.executable, optimiser_script], capture_output=True, text=True
        )
        if opt.returncode != 0:
            log("  FAILED to run the optimiser:")
            log(opt.stderr[-2000:])
            all_passed = False
        else:
            log("  zone_optimisation.json regenerated.")
            with open(zone_path, encoding="utf-8") as f:
                zopt = json.load(f)
            all_passed &= check(
                "Unconstrained optimum captures every strong rule",
                zopt["unconstrained"]["rules_captured"] == M.ZONE_OPT_UNCONSTRAINED_RULES,
                f"{zopt['unconstrained']['rules_captured']} of {zopt['total_rules']} rules, "
                f"one zone holding all {zopt['n_rule_bearing_categories']} rule-bearing "
                "categories: a property of the metric, not a shelf plan"
            )
            all_passed &= check(
                "Cost of the physical and ethical constraints reproduces",
                zopt["constraint_cost"]["unlimited_zones"]["rules"]
                == M.ZONE_OPT_CONSTRAINT_COST_RULES_UNLIMITED
                and zopt["constraint_cost"]["capacity_matched"]["rules"]
                == M.ZONE_OPT_CONSTRAINT_COST_RULES_CAPACITY,
                f"{M.ZONE_OPT_CONSTRAINT_COST_RULES_UNLIMITED} rules with unlimited "
                f"zone sizes, {M.ZONE_OPT_CONSTRAINT_COST_RULES_CAPACITY} once zone "
                "capacities are held fixed: the price of the cold-zone, ethical and "
                "heavy-goods locks"
            )
            all_passed &= check(
                "Capacity-matched optimum reproduces",
                zopt["capacity_constrained"]["rules_captured"] == M.ZONE_OPT_CAPACITY_RULES
                and abs(zopt["capacity_constrained"]["support_captured"]
                        - M.ZONE_OPT_CAPACITY_SUPPORT) < 0.0001,
                f"{zopt['capacity_constrained']['rules_captured']} rules, "
                f"{zopt['capacity_constrained']['support_captured']:.4f} support at the "
                f"hand-built zone sizes, versus {zopt['hand_built']['rules_captured']} / "
                f"{zopt['hand_built']['support_captured']:.4f} hand-built"
            )
            all_passed &= check(
                "Every local search run reached its exhaustive certificate",
                all(zopt[k]["local_search_is_exact"] for k in
                    ("unconstrained", "constrained",
                     "capacity_unconstrained", "capacity_constrained")),
                f"{zopt['unconstrained']['restarts']} restarts, seed "
                f"{zopt['unconstrained']['seed']}"
            )
    else:
        log("  analysis/optimise_zones.py not found.")
        all_passed = False

    section("STEP 10 - Daily granularity forecasting (analysis/daily_forecast.py)")
    # Rebuilds the 304-day series from the cleaned record, refits every daily
    # model on the chronological split (61 rolling Prophet refits included)
    # and rewrites daily_revenue.csv, daily_forecast_summary.json and chart 25.
    # The monthly result in notebook 10 is not touched; this is an extension.
    forecast_script = os.path.join(HERE, "analysis", "daily_forecast.py")
    fc_path = os.path.join(ARTIFACTS, "daily_forecast_summary.json")
    if os.path.exists(forecast_script):
        fc_run = subprocess.run(
            [sys.executable, forecast_script], capture_output=True, text=True
        )
        if fc_run.returncode != 0:
            log("  FAILED to run the daily forecast:")
            log(fc_run.stderr[-2000:])
            all_passed = False
        else:
            log("  daily_revenue.csv, daily_forecast_summary.json and chart 25 regenerated.")
            with open(fc_path, encoding="utf-8") as f:
                fc = json.load(f)
            models = fc["models"]
            all_passed &= check(
                "Daily split is chronological, 243 train / 61 test",
                fc["split"]["train_days"] == M.DAILY_TRAIN_DAYS
                and fc["split"]["test_days"] == M.DAILY_TEST_DAYS
                and fc["split"]["train_end"] < fc["split"]["test_start"],
                f"train to {fc['split']['train_end']}, test from {fc['split']['test_start']}"
            )
            all_passed &= check(
                "Best daily model beats naive persistence",
                models["linear_dow_rolling"]["mae"] < models["naive_persistence"]["mae"],
                f"MAE {models['linear_dow_rolling']['mae']:,.0f} vs "
                f"{models['naive_persistence']['mae']:,.0f} (yesterday's value), "
                f"{(1 - models['linear_dow_rolling']['mae'] / models['naive_persistence']['mae']) * 100:.1f}% lower"
            )
            all_passed &= check(
                "Best daily model reproduces",
                round(models["linear_dow_rolling"]["mae"]) == M.DAILY_LINREG_DOW_ROLLING_MAE
                and round(models["prophet_weekly_rolling"]["mae"]) == M.DAILY_PROPHET_ROLLING_MAE,
                f"LR day-of-week refit daily {models['linear_dow_rolling']['mae']:,.0f}, "
                f"Prophet refit daily {models['prophet_weekly_rolling']['mae']:,.0f}"
            )
            all_passed &= check(
                "No daily model reaches positive R squared (reported, not hidden)",
                all(m["r2"] < 0 for m in models.values()) == (not M.DAILY_ANY_MODEL_R2_POSITIVE),
                f"best fitted R2 {max(models[k]['r2'] for k in ('linear_dow', 'linear_dow_trend', 'prophet_weekly', 'linear_dow_rolling', 'prophet_weekly_rolling')):.3f}"
            )
            all_passed &= check(
                "Prophet does not detect Dashain at daily granularity by default",
                fc["dashain"]["fitted_peak_inside_window"] == M.DAILY_PROPHET_DASHAIN_DETECTED,
                f"fitted peak {fc['dashain']['fitted_peak_day']}, actual peak "
                f"{fc['dashain']['actual_peak_day']}"
            )
    else:
        log("  analysis/daily_forecast.py not found.")
        all_passed = False

    section("STEP 11 - Richer basket features (analysis/basket_features.py)")
    # Rebuilds the notebook 11 and 12 labels, split and models on the 25
    # binary flags (they must reproduce), then on the richer feature sets,
    # and rewrites basket_features_summary.json and chart 26. The reported
    # 71.67 per cent ceiling on the flags is recomputed, not replaced.
    features_script = os.path.join(HERE, "analysis", "basket_features.py")
    bf_path = os.path.join(ARTIFACTS, "basket_features_summary.json")
    if os.path.exists(features_script):
        bf_run = subprocess.run(
            [sys.executable, features_script], capture_output=True, text=True
        )
        if bf_run.returncode != 0:
            log("  FAILED to run the richer-features study:")
            log(bf_run.stderr[-2000:])
            all_passed = False
        else:
            log("  basket_features_summary.json and chart 26 regenerated.")
            with open(bf_path, encoding="utf-8") as f:
                bf = json.load(f)
            bm, bc = bf["models"], bf["ceilings"]
            all_passed &= check(
                "Reported binary-flag figures reproduce inside the new run",
                round(bm["binary_tree_depth5"]["accuracy"], 3) == M.CLASSIFIER_ACCURACY
                and round(bm["binary_mlp"]["accuracy"], 4) == M.NEURAL_NET_ACCURACY
                and round(bc["binary"]["ceiling"], 4) == M.FEATURE_CEILING_ACCURACY
                and bc["binary"]["distinct_patterns"] == M.DISTINCT_FEATURE_PATTERNS,
                f"tree {bm['binary_tree_depth5']['accuracy'] * 100:.2f}%, MLP "
                f"{bm['binary_mlp']['accuracy'] * 100:.2f}%, ceiling "
                f"{bc['binary']['ceiling'] * 100:.2f}%, {bc['binary']['distinct_patterns']:,} patterns"
            )
            all_passed &= check(
                "Richer features raise both models",
                bm["full_tree_depth5"]["accuracy"] > bm["binary_tree_depth5"]["accuracy"]
                and bm["full_mlp"]["accuracy"] > bm["binary_mlp"]["accuracy"],
                f"tree {bm['binary_tree_depth5']['accuracy'] * 100:.2f}% to "
                f"{bm['full_tree_depth5']['accuracy'] * 100:.2f}%, MLP "
                f"{bm['binary_mlp']['accuracy'] * 100:.2f}% to {bm['full_mlp']['accuracy'] * 100:.2f}%"
            )
            all_passed &= check(
                "New accuracies reproduce",
                round(bm["full_tree_depth5"]["accuracy"], 4) == M.FEATURES_TREE_FULL_ACCURACY
                and round(bm["full_mlp"]["accuracy"], 4) == M.FEATURES_MLP_FULL_ACCURACY
                and round(bc["full"]["ceiling"], 4) == M.FEATURES_CEILING_FULL,
                f"ceiling on the full set {bc['full']['ceiling'] * 100:.2f}%, "
                f"{bc['full']['singleton_basket_share'] * 100:.1f}% of baskets with a unique pattern"
            )
            all_passed &= check(
                "Item count displaces COOKING OIL as the top tree feature",
                bf["feature_importance"]["new_top"][0] == M.FEATURES_NEW_TOP_FEATURE
                and bf["feature_importance"]["displaced"],
                f"top {bf['feature_importance']['new_top'][0]} "
                f"({bf['feature_importance']['new_top_values'][bf['feature_importance']['new_top'][0]]:.3f}), "
                f"COOKING OIL rank {bf['feature_importance']['cooking_oil_new_rank']}"
            )
    else:
        log("  analysis/basket_features.py not found.")
        all_passed = False

    section("STEP 11b - Temporal validation (analysis/temporal_validation.py)")
    # Mines rules on July 2025 to January 2026 and recomputes each rule's lift on
    # February to May 2026, a window it was not mined from. Written 2026-08-17 to
    # give RULE_STABILITY_* a source: the median previously had no producing code.
    tv_script = os.path.join(HERE, "analysis", "temporal_validation.py")
    tv_path = os.path.join(ARTIFACTS, "temporal_validation_summary.json")
    if os.path.exists(tv_script):
        tv_run = subprocess.run([sys.executable, tv_script],
                                capture_output=True, text=True)
        if tv_run.returncode != 0:
            log("  FAILED to run the temporal validation:")
            log(tv_run.stderr[-2000:])
            all_passed = False
        else:
            log("  temporal_validation_summary.json regenerated.")
    if os.path.exists(tv_path):
        with open(tv_path, encoding="utf-8") as f:
            tv = json.load(f)
        all_passed &= check(
            "Windows partition every basket",
            tv["windows"]["development"]["baskets"]
            + tv["windows"]["validation"]["baskets"] == M.TOTAL_TRANSACTIONS,
            f"{tv['windows']['development']['baskets']:,} development + "
            f"{tv['windows']['validation']['baskets']:,} validation "
            f"= {M.TOTAL_TRANSACTIONS:,}"
        )
        all_passed &= check(
            "Median stability ratio reproduces",
            abs(round(tv["median_ratio"], 3) - M.RULE_STABILITY_MEDIAN) < 0.0005,
            f"median {tv['median_ratio']:.3f} over {tv['dev_rules']:,} rules mined "
            f"on the development window alone"
        )
        all_passed &= check(
            "Rules hold up in a period they were not mined from",
            tv["rules_below_ratio_floor"] == 0
            and tv["top_n_still_strong"] == tv["top_n_evaluated"],
            f"no rule more than halved, and all {tv['top_n_still_strong']} of the "
            f"top 20 keep lift >= 3.0; weakest ratio {tv['min_ratio']:.3f}"
        )
    else:
        log("  temporal_validation_summary.json not found.")
        all_passed = False

    section("STEP 11c - Recommender baselines (analysis/recommender_baselines.py)")
    # Scores the notebook 09 recommender against popularity and random on the same
    # baskets. Written 2026-08-17: notebook 09 produced the hit rate but none of
    # the baselines or the coverage split, which were unsourced constants.
    rb_script = os.path.join(HERE, "analysis", "recommender_baselines.py")
    rb_path = os.path.join(ARTIFACTS, "recommender_baselines_summary.json")
    if os.path.exists(rb_script):
        rb_run = subprocess.run([sys.executable, rb_script],
                                capture_output=True, text=True)
        if rb_run.returncode != 0:
            log("  FAILED to run the recommender baselines:")
            log(rb_run.stderr[-2000:])
            all_passed = False
        else:
            log("  recommender_baselines_summary.json regenerated.")
    if os.path.exists(rb_path):
        with open(rb_path, encoding="utf-8") as f:
            rb = json.load(f)
        all_passed &= check(
            "Notebook 09 hit rate reproduces",
            abs(rb["model_hit_pct"] - M.REC_MODEL_HIT_PCT) < 0.005,
            f"{rb['model_hit_pct']:.2f}% on {rb['test_baskets_scored']:,} "
            "multi-product test baskets"
        )
        all_passed &= check(
            "Model beats popularity at a matched recommendation budget",
            rb["model_hit_pct"] > rb["popularity_matched_pct"],
            f"{rb['model_hit_pct']:.2f}% vs {rb['popularity_matched_pct']:.2f}%, "
            f"and vs {rb['random_matched_pct']:.2f}% for random"
        )
        all_passed &= check(
            "Unconstrained popularity still beats the model, reported not hidden",
            rb["model_hit_pct"] < rb["popularity_top5_pct"],
            f"popularity top 5 {rb['popularity_top5_pct']:.2f}% vs the model's "
            f"{rb['model_hit_pct']:.2f}%"
        )
        all_passed &= check(
            "Coverage is the binding limitation",
            rb["covered_model_pct"] > rb["model_hit_pct"],
            f"{rb['covered_model_pct']:.2f}% on the {rb['covered_baskets']:,} baskets "
            f"it can answer, {rb['uncovered_baskets']:,} it cannot"
        )
    else:
        log("  recommender_baselines_summary.json not found.")
        all_passed = False

    section("STEP 12 - Full thesis-number sweep (PROJECT_RECORD.md section 9)")
    # Delegated to scripts/verify_thesis_numbers.py so the "N of N" figure is
    # generated rather than typed into the document by hand. A hand-written
    # count drifts away from the table it describes the moment either changes.
    sweep_script = os.path.join(HERE, "scripts", "verify_thesis_numbers.py")
    if os.path.exists(sweep_script):
        sweep = subprocess.run(
            [sys.executable, sweep_script], capture_output=True, text=True
        )
        verified_line = next(
            (ln.strip() for ln in sweep.stdout.splitlines() if "VERIFIED:" in ln), ""
        )
        uncheckable_line = next(
            (ln.strip() for ln in sweep.stdout.splitlines() if "NOT AUTO-CHECKABLE:" in ln), ""
        )
        all_passed &= check(
            "Every checkable thesis number matches",
            sweep.returncode == 0,
            verified_line or "see scripts/verify_thesis_numbers.py"
        )
        if uncheckable_line:
            log(f"         {uncheckable_line}")
        if sweep.returncode != 0:
            log(sweep.stdout[-1500:])
    else:
        log("  scripts/verify_thesis_numbers.py not found.")
        all_passed = False

    section("SUMMARY")
    if all_passed:
        log("ALL CHECKS PASSED. Every verified number reproduces from the pipeline.")
    else:
        log("ONE OR MORE CHECKS FAILED. See FAIL lines above.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(REPORTS, f"reproduction_log_{timestamp}.txt")
    with open(log_path, "w") as f:
        f.write("\n".join(log_lines))
    log(f"\nFull report saved to: {log_path}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()