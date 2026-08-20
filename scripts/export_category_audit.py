"""
Export the full product-to-category mapping for manual misclassification review.

Read-only. This script does not modify data/, does not modify any mapping and
does not write anything except reports/category_audit.xlsx.

Source: data/processed/sales_data_cleaned.csv, which already carries the three
columns this audit needs:
    product_group        the original label as entered by store staff
    product_group_clean  the same label stripped/uppercased (notebook 02)
    category             the standardised 25-category label (notebook 02)

Sheets written:
    Summary       one row per category (25)
    All products  one row per product (5,680)
    Mapping       one row per distinct raw product group value (37)
    Review flags  products whose name contains a keyword strongly associated
                  with a different category than the one they sit in
    Keyword rules the rule table behind the Review flags sheet

Run:  python scripts/export_category_audit.py
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "processed" / "sales_data_cleaned.csv"
OUT = ROOT / "reports" / "category_audit.xlsx"
OUT_MD = ROOT / "reports" / "category_audit.md"

REVENUE_COL = "total_amount"  # sums to TOTAL_REVENUE in config/metrics.py


# ----------------------------------------------------------------------
# Keyword rules for the Review flags sheet
# ----------------------------------------------------------------------
#
# Each rule is  keyword -> categories where that keyword is expected.
# A product is flagged when its name contains the keyword as a WHOLE WORD and
# its current category is not in the expected set. The first expected category
# is reported as suggested_category.
#
# Whole-word matching matters: a substring test would match "oil" inside
# "toilet" and flag every toilet cleaner in CLEANING SUPPLIES.
#
# Deliberately excluded as too ambiguous to be evidence of anything:
# "cream" (ice cream / face cream / cream biscuit), "powder" (milk / spice /
# washing / talcum), "gold" and "fresh" (brand words), "mix", "bar", "roll".
#
# Two suppression rules stop the sheet filling with flavour names. Without
# them "BUTTER COOKIES" in BISCUITS AND COOKIES is flagged as dairy, which it
# plainly is not. Both are applied before a flag is written and both are
# listed on the Keyword rules sheet.
#
#   1. ANCHOR suppression. If the name also contains a keyword whose expected
#      category IS the product's current category, the product is anchored
#      where it sits and every other keyword in that name is treated as a
#      flavour or ingredient word. "BUTTER COOKIES" is anchored by "cookies".
#   2. QUALIFIER suppression. Per keyword, words that neutralise it outright.
#      "HAIR OIL" and "MASSAGE OIL" are not cooking oil in any category.

KEYWORD_RULES: dict[str, list[str]] = {
    # cooking oil
    "oil": ["COOKING OIL"],
    "ghee": ["COOKING OIL", "DAIRY PRODUCTS"],
    # staples
    "dal": ["FOOD STAPLES"],
    "daal": ["FOOD STAPLES"],
    "atta": ["FOOD STAPLES"],
    "besan": ["FOOD STAPLES"],
    "maida": ["FOOD STAPLES"],
    "flour": ["FOOD STAPLES"],
    "sugar": ["FOOD STAPLES"],
    "salt": ["FOOD STAPLES"],
    "rice": ["RICE", "FOOD STAPLES"],
    # tea, coffee, spices
    "tea": ["TEA AND SPICES"],
    "coffee": ["TEA AND SPICES"],
    "masala": ["TEA AND SPICES"],
    "jeera": ["TEA AND SPICES"],
    "haldi": ["TEA AND SPICES"],
    "turmeric": ["TEA AND SPICES"],
    # personal care
    "soap": ["PERSONAL CARE", "CLEANING SUPPLIES"],
    "shampoo": ["PERSONAL CARE"],
    "toothpaste": ["PERSONAL CARE"],
    "toothbrush": ["PERSONAL CARE"],
    "razor": ["PERSONAL CARE"],
    "shaving": ["PERSONAL CARE"],
    "lotion": ["PERSONAL CARE"],
    "deodorant": ["PERSONAL CARE"],
    "sanitary": ["PERSONAL CARE"],
    # cleaning
    "detergent": ["CLEANING SUPPLIES"],
    "bleach": ["CLEANING SUPPLIES"],
    "harpic": ["CLEANING SUPPLIES"],
    "phenyl": ["CLEANING SUPPLIES"],
    # dairy
    "milk": ["DAIRY PRODUCTS"],
    "cheese": ["DAIRY PRODUCTS"],
    "butter": ["DAIRY PRODUCTS"],
    "curd": ["DAIRY PRODUCTS"],
    "yoghurt": ["DAIRY PRODUCTS"],
    "yogurt": ["DAIRY PRODUCTS"],
    "paneer": ["DAIRY PRODUCTS"],
    # snacks and sweets
    "biscuit": ["BISCUITS AND COOKIES"],
    "cookies": ["BISCUITS AND COOKIES"],
    "chocolate": ["CONFECTIONERY"],
    "candy": ["CONFECTIONERY"],
    "toffee": ["CONFECTIONERY"],
    "chips": ["SNACKS"],
    # drinks
    "juice": ["SOFT DRINKS AND JUICES"],
    "beer": ["ALCOHOLIC BEVERAGES"],
    "whisky": ["ALCOHOLIC BEVERAGES"],
    "whiskey": ["ALCOHOLIC BEVERAGES"],
    "rum": ["ALCOHOLIC BEVERAGES"],
    "vodka": ["ALCOHOLIC BEVERAGES"],
    "wine": ["ALCOHOLIC BEVERAGES"],
    # other categories
    "noodles": ["NOODLES"],
    "bread": ["BAKERY"],
    "oats": ["BREAKFAST CEREALS"],
    "cornflakes": ["BREAKFAST CEREALS"],
    "diaper": ["BABY CARE"],
    "cigarette": ["CIGARETTE AND TOBACCO"],
    "agarbatti": ["POOJA ITEMS"],
    "dhoop": ["POOJA ITEMS"],
    "incense": ["POOJA ITEMS"],
    "pencil": ["STATIONERY"],
    "eraser": ["STATIONERY"],
    "battery": ["ELECTRICAL SUPPLIES"],
    "bulb": ["ELECTRICAL SUPPLIES"],
    # anchor words: rarely a misplacement on their own, but they pin a product
    # to where it sits and stop every flavour word in the name firing
    "baby": ["BABY CARE"],
    "hair": ["PERSONAL CARE"],
    "crackers": ["BISCUITS AND COOKIES"],
    "wafer": ["BISCUITS AND COOKIES", "CONFECTIONERY"],
    "cake": ["BAKERY"],
}

# keyword -> words that neutralise it wherever they appear in the same name
QUALIFIERS: dict[str, list[str]] = {
    "oil": ["hair", "massage", "masage", "scalp", "body", "skin", "aroma",
            "lamp", "batti"],
    "milk": ["soap", "lotion", "shampoo", "cream bath"],
    "butter": ["body", "shea", "cocoa butter"],
}


def build_flags(products: pd.DataFrame) -> pd.DataFrame:
    """Flag products whose name contains a keyword tied to another category."""
    patterns = {
        kw: re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
        for kw in KEYWORD_RULES
    }

    rows = []
    for name, category in zip(products["product_name"], products["category"]):
        text = str(name)
        hits = [kw for kw in KEYWORD_RULES if patterns[kw].search(text)]
        if not hits:
            continue

        # rule 1: anchored where it sits, so the other keywords are flavour words
        if any(category in KEYWORD_RULES[kw] for kw in hits):
            continue

        lowered = text.lower()
        for kw in hits:
            # rule 2: a qualifier in the same name neutralises this keyword
            if any(q in lowered for q in QUALIFIERS.get(kw, ())):
                continue
            rows.append(
                {
                    "product_name": name,
                    "current_category": category,
                    "suggested_category": KEYWORD_RULES[kw][0],
                    "matched_keyword": kw,
                }
            )

    flags = pd.DataFrame(
        rows,
        columns=[
            "product_name",
            "current_category",
            "suggested_category",
            "matched_keyword",
        ],
    )
    if not flags.empty:
        flags = flags.sort_values(
            ["current_category", "matched_keyword", "product_name"]
        ).reset_index(drop=True)
    return flags


def md_table(df: pd.DataFrame, formatters: dict | None = None) -> str:
    """Render a DataFrame as a GitHub-flavoured markdown table.

    Right-aligns numeric columns and escapes any pipe in a cell so a product
    name containing '|' cannot break the table.
    """
    formatters = formatters or {}
    numeric = {c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])}

    def cell(col, value):
        text = formatters[col](value) if col in formatters else str(value)
        return text.replace("|", "\\|")

    header = "| " + " | ".join(df.columns) + " |"
    rule = "| " + " | ".join(
        "---:" if c in numeric else "---" for c in df.columns
    ) + " |"
    body = [
        "| " + " | ".join(cell(c, v) for c, v in zip(df.columns, row)) + " |"
        for row in df.itertuples(index=False, name=None)
    ]
    return "\n".join([header, rule, *body])


def write_markdown(summary, products, mapping, flags, total_baskets) -> None:
    """Write the whole audit to one markdown file, four headings, one table each."""
    money = lambda v: f"{v:,.2f}"
    qty = lambda v: f"{v:,.2f}" if v % 1 else f"{int(v):,}"

    thin = summary[summary["product_count"] < 10]
    thin_note = (
        ", ".join(f"{r.category} ({r.product_count})" for r in thin.itertuples(index=False))
        if not thin.empty else "none"
    )

    parts = [
        "# Product to category audit",
        "",
        f"Source: `data/processed/sales_data_cleaned.csv` | "
        f"{len(products):,} products | {len(summary)} categories | "
        f"{mapping['raw_product_group'].nunique()} distinct raw product group values | "
        f"{total_baskets:,} baskets | Rs {products['revenue'].sum():,.2f} revenue",
        "",
        "Generated by `scripts/export_category_audit.py`. Read-only: no data and "
        "no mapping was modified. Revenue is `total_amount` (VAT inclusive), which "
        "reconciles to `TOTAL_REVENUE` in `config/metrics.py`.",
        "",
        f"Categories with fewer than 10 products: {thin_note}.",
        "",
        "## Summary",
        "",
        f"One row per category, {len(summary)} rows, sorted by product count descending. "
        "`pct_of_baskets` is the share of the "
        f"{total_baskets:,} baskets containing at least one product from the category; "
        "these do not sum to 100 because a basket holds several categories.",
        "",
        md_table(summary, {"total_revenue": money, "pct_of_baskets": lambda v: f"{v:.2f}"}),
        "",
        "## All products",
        "",
        f"One row per product, {len(products):,} rows, sorted by category then by revenue "
        "descending. `raw_product_group` is the original label as entered by store staff, "
        "shown beside the category it was mapped to.",
        "",
        md_table(products, {"revenue": money, "units_sold": qty}),
        "",
        "## Mapping",
        "",
        f"One row per distinct raw product group value, {len(mapping)} rows, sorted by "
        "product count descending. Every mapping decision in one place. `HEALTH & WELLNESS` "
        "is the only group that does not resolve to a single category: notebook 02 "
        "reassigns its 7 products individually, so both destinations are shown with counts.",
        "",
        md_table(mapping, {}),
        "",
        "## Review flags",
        "",
        f"{len(flags):,} flags across {flags['product_name'].nunique():,} distinct products. "
        "A product is flagged when its name contains a keyword strongly associated with a "
        "category other than the one it sits in. Nothing was changed; these are candidates "
        "for your judgement, and some will be false positives.",
        "",
        md_table(flags, {}),
        "",
        "### Keyword rules used",
        "",
        "Matching is whole-word and case-insensitive. A substring test is not safe here: "
        '"toilet" contains "oil", which would flag every toilet cleaner in CLEANING SUPPLIES.',
        "",
        "| keyword | expected in | flag suppressed when name also contains |",
        "| --- | --- | --- |",
    ]

    for kw, cats in KEYWORD_RULES.items():
        quals = ", ".join(QUALIFIERS.get(kw, ())) or "-"
        parts.append(f"| {kw} | {' or '.join(cats)} | {quals} |")

    parts += [
        "",
        "Two suppression rules stop the sheet filling with flavour names. Without them "
        '"BUTTER COOKIES" in BISCUITS AND COOKIES is flagged as misfiled dairy, which it '
        "plainly is not. A plain keyword test produced 501 flags; these two rules bring it "
        f"to {len(flags):,}.",
        "",
        "1. **Anchor.** If the name also contains a keyword whose expected category *is* the "
        "product's current category, the product is anchored where it sits and every other "
        'keyword in that name is treated as a flavour or ingredient word. "BUTTER COOKIES" '
        'is anchored by "cookies".',
        "2. **Qualifier.** Per keyword, words that neutralise it outright, listed in the "
        'third column above. "HAIR OIL" and "MASSAGE OIL" are not cooking oil in any category.',
        "",
        "Deliberately excluded as too ambiguous to be evidence of anything: "
        '"cream" (ice cream / face cream / cream biscuit), "powder" (milk / spice / washing / '
        'talcum), "gold" and "fresh" (brand words), "mix", "bar", "roll".',
        "",
    ]

    OUT_MD.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    print("Reading", SOURCE.relative_to(ROOT))
    df = pd.read_csv(
        SOURCE,
        usecols=[
            "invoice_no",
            "product_group",
            "product_group_clean",
            "category",
            "product",
            "quantity",
            REVENUE_COL,
        ],
    )
    total_baskets = df["invoice_no"].nunique()
    print(f"  {len(df):,} rows | {total_baskets:,} baskets | "
          f"Rs {df[REVENUE_COL].sum():,.2f} revenue")

    # ---------------- Sheet 2: All products ----------------
    products = (
        df.groupby(["category", "product", "product_group"], as_index=False)
        .agg(units_sold=("quantity", "sum"), revenue=(REVENUE_COL, "sum"))
        .rename(columns={"product": "product_name",
                         "product_group": "raw_product_group"})
    )
    products = products[
        ["category", "product_name", "raw_product_group", "units_sold", "revenue"]
    ].sort_values(["category", "revenue"], ascending=[True, False]).reset_index(drop=True)

    # ---------------- Sheet 1: Summary ----------------
    baskets_per_cat = df.groupby("category")["invoice_no"].nunique()
    summary = (
        products.groupby("category", as_index=False)
        .agg(product_count=("product_name", "count"),
             total_revenue=("revenue", "sum"))
    )
    summary["pct_of_baskets"] = (
        summary["category"].map(baskets_per_cat) / total_baskets * 100
    ).round(2)
    summary = summary.sort_values(
        ["product_count", "total_revenue"], ascending=[False, False]
    ).reset_index(drop=True)

    # ---------------- Sheet 3: Mapping ----------------
    # One row per distinct raw product group. A group that resolves to more
    # than one category (product-level overrides in notebook 02) shows every
    # destination with its product count, so no decision is hidden.
    mapping_rows = []
    for raw, sub in products.groupby("raw_product_group"):
        counts = sub["category"].value_counts()
        if len(counts) == 1:
            mapped = counts.index[0]
        else:
            mapped = "; ".join(f"{c} ({n})" for c, n in counts.items())
        mapping_rows.append(
            {
                "raw_product_group": raw,
                "mapped_category": mapped,
                "product_count": len(sub),
            }
        )
    mapping = (
        pd.DataFrame(mapping_rows)
        .sort_values("product_count", ascending=False)
        .reset_index(drop=True)
    )

    # ---------------- Sheet 4: Review flags ----------------
    flags = build_flags(products)

    rules_sheet = pd.DataFrame(
        [
            {
                "keyword": kw,
                "expected_categories": " or ".join(cats),
                "neutralised_when_name_contains": ", ".join(QUALIFIERS.get(kw, ())),
            }
            for kw, cats in KEYWORD_RULES.items()
        ]
    )

    # ---------------- Write workbook ----------------
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT, engine="openpyxl") as xl:
        summary.to_excel(xl, sheet_name="Summary", index=False)
        products.to_excel(xl, sheet_name="All products", index=False)
        mapping.to_excel(xl, sheet_name="Mapping", index=False)
        flags.to_excel(xl, sheet_name="Review flags", index=False)
        rules_sheet.to_excel(xl, sheet_name="Keyword rules", index=False)

        widths = {
            "Summary": [30, 15, 18, 16],
            "All products": [30, 46, 26, 13, 16],
            "Mapping": [26, 46, 15],
            "Review flags": [46, 30, 30, 18],
            "Keyword rules": [18, 42, 46],
        }
        for sheet, cols in widths.items():
            ws = xl.sheets[sheet]
            ws.freeze_panes = "A2"
            for i, w in enumerate(cols, start=1):
                ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w

        for sheet, money_cols in {
            "Summary": ["C"], "All products": ["E"]
        }.items():
            ws = xl.sheets[sheet]
            for col in money_cols:
                for cell in ws[col][1:]:
                    cell.number_format = "#,##0.00"

    print(f"\nWrote {OUT.relative_to(ROOT)}")
    print(f"  Summary       {len(summary):,} rows")
    print(f"  All products  {len(products):,} rows")
    print(f"  Mapping       {len(mapping):,} rows")
    print(f"  Review flags  {len(flags):,} rows")
    print(f"  Keyword rules {len(rules_sheet):,} rows")

    # ---------------- Same content, one markdown file ----------------
    write_markdown(summary, products, mapping, flags, total_baskets)
    print(f"\nWrote {OUT_MD.relative_to(ROOT)}")
    print(f"  {OUT_MD.stat().st_size / 1024:,.0f} KB, four headings, one table each")

    # ---------------- Terminal report ----------------
    print("\n" + "=" * 62)
    print("RAW PRODUCT GROUP FIELD")
    print("=" * 62)
    print(f"Distinct values in 'product_group' (as entered by staff): "
          f"{df['product_group'].nunique()}")
    print(f"Distinct values after strip/uppercase ('product_group_clean'): "
          f"{df['product_group_clean'].nunique()}")

    print("\n" + "=" * 62)
    print(f"PRODUCTS PER CATEGORY ({len(summary)} categories)")
    print("=" * 62)
    for i, r in enumerate(summary.itertuples(index=False), 1):
        print(f"{i:2d}. {r.category:<28} {r.product_count:>5,} products  "
              f"Rs {r.total_revenue:>16,.2f}  {r.pct_of_baskets:>5.2f}% of baskets")
    print(f"{'':4}{'TOTAL':<28} {summary.product_count.sum():>5,} products")

    print("\n" + "=" * 62)
    print("CATEGORIES WITH FEWER THAN 10 PRODUCTS")
    print("=" * 62)
    thin = summary[summary["product_count"] < 10]
    if thin.empty:
        print("None. Every category has at least 10 products.")
    else:
        for r in thin.itertuples(index=False):
            print(f"  {r.category:<28} {r.product_count:>5,} products")

    print("\n" + "=" * 62)
    print("REVIEW FLAGS BY KEYWORD")
    print("=" * 62)
    if flags.empty:
        print("No products flagged.")
    else:
        for kw, n in flags["matched_keyword"].value_counts().items():
            print(f"  {kw:<14} {n:>4} products")
        print(f"\n  {len(flags):,} flags across "
              f"{flags['product_name'].nunique():,} distinct products")

    print("\nNo data and no mapping was modified. Export only.")


if __name__ == "__main__":
    main()
