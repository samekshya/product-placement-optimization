"""
Explicit product-to-category remapping table from reports/CATEGORY_REMAP_SPEC.md.

DRY RUN. Importing this module has no side effects. Running it prints a report
and writes nothing: no data file, no notebook, no mapping is modified. Applying
the remap is a separate, later decision.

The spec is a manual audit decided 16 August 2026. This module turns its prose
into an explicit rule table so the moves can be counted and checked before any
notebook is re-run.

Rule kinds
----------
NAME  an exact product name, as written in the spec. Matched case-insensitively
      with internal whitespace collapsed. Anything that does not match a real
      product is reported as UNMATCHED, which is the point: the spec was typed
      by hand from a markdown table, so typos are expected.
RE    a regex family, used where the spec says "all X" rather than naming
      products. `exclude` narrows a family that would otherwise reach into
      products the spec assigns elsewhere.

Every rule carries `ref`, the spec section it comes from, so any move can be
traced back to the paragraph that authorised it.

Where the spec used brand shorthand, the full product name is used as the
pattern and the shorthand is recorded in `note`. These are listed in the report
under "shorthand expanded" so each one can be confirmed rather than trusted.

Run:  python analysis/category_remap.py
"""

from __future__ import annotations

import difflib
import importlib.util
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "processed" / "sales_data_cleaned.csv"
AUDIT_SCRIPT = ROOT / "scripts" / "export_category_audit.py"
REVENUE_COL = "total_amount"


# ----------------------------------------------------------------------
# PART 1: renames. Applied before any move, so every rule below names
# categories by their post-rename label.
# ----------------------------------------------------------------------

RENAMES: dict[str, str] = {
    "NAMKEEN AND SNACKS": "SNACKS",
    "FRUITS AND VEGETABLES": "FRESH PRODUCE",
}


# A rule whose source is ANY matches whatever category the product sits in.
# Used for consolidations that cut across the spec's source-by-source layout.
ANY = "*"


@dataclass(frozen=True)
class Rule:
    source: str          # category the product must currently sit in, or ANY
    pattern: str         # exact name, or regex when kind == "RE"
    destination: str
    ref: str             # spec section
    kind: str = "NAME"
    exclude: str = ""    # regex; RE rules only
    note: str = ""       # shorthand expansion or interpretation


def N(source, pattern, destination, ref, note=""):
    return Rule(source, pattern, destination, ref, "NAME", "", note)


def R(source, pattern, destination, ref, exclude="", note=""):
    return Rule(source, pattern, destination, ref, "RE", exclude, note)


# ----------------------------------------------------------------------
# PART 2: out of FOOD STAPLES
# ----------------------------------------------------------------------

FS = "FOOD STAPLES"

# 2.1 spices, seasonings, salt, MSG -> TEA AND SPICES
#
# The spec lists brands then spice words. Matching on the spice word alone is
# enough: these words are specific, and the brand list adds nothing a keyword
# does not already catch. `exclude="pickle"` keeps the spice families out of the
# pickles the spec sends to CANNED AND PACKAGED FOODS in 2.3, so "Paicho Methi
# Pickle 400g" is not claimed by "methi" and "Jomsom Timur Pickle" is not
# claimed by "timur".
SPICE = "TEA AND SPICES"
_PICKLE = r"pickle"

RULES: list[Rule] = [
    # --- 2.1 whole and ground spices -------------------------------------
    R(FS, r"\bjeera\b", SPICE, "2.1", _PICKLE),
    R(FS, r"dhaniya|dhania", SPICE, "2.1", _PICKLE),
    R(FS, r"\bmarij\b", SPICE, "2.1", _PICKLE),
    R(FS, r"\bmethi\b", SPICE, "2.1", _PICKLE,
      "also catches BMC/Century kasoori methi, same destination"),
    R(FS, r"lwang|sukmel|lwa/sukm", SPICE, "2.1", _PICKLE,
      "data abbreviates United to 'LWA/SUKM MIX'"),
    R(FS, r"\bsoff\b", SPICE, "2.1", _PICKLE),
    R(FS, r"\bjwano\b", SPICE, "2.1", _PICKLE),
    R(FS, r"\bdalchini\b", SPICE, "2.1", _PICKLE),
    R(FS, r"tej patta", SPICE, "2.1", _PICKLE),
    R(FS, r"\bjaipatri\b", SPICE, "2.1", _PICKLE),
    R(FS, r"\bpipla\b", SPICE, "2.1", _PICKLE),
    R(FS, r"star full", SPICE, "2.1", _PICKLE),
    R(FS, r"\bsaffron\b", SPICE, "2.1", _PICKLE,
      "covers APIS 1gm and 0.5gm and BLG 50gm named in the spec"),
    R(FS, r"\bturmeric\b", SPICE, "2.1", _PICKLE),
    R(FS, r"chill?[iy] powder", SPICE, "2.1", _PICKLE,
      "data spells it 'Chilly Powder' for Battisa, Current and Rara"),
    R(FS, r"cumin powder", SPICE, "2.1", _PICKLE),
    R(FS, r"coriander powder", SPICE, "2.1", _PICKLE),
    R(FS, r"white ?pepper", SPICE, "2.1", _PICKLE,
      "data has 'Current WhitePepper Powder 50gm', no space"),
    R(FS, r"kashmiri mirch", SPICE, "2.1", _PICKLE),
    R(FS, r"\bkhursani\b", SPICE, "2.1", _PICKLE),
    R(FS, r"roghni mirch", SPICE, "2.1", _PICKLE),
    R(FS, r"\bpanchapuran\b", SPICE, "2.1", _PICKLE),
    # No word boundary after "timur": Gaule Timurko Dana runs the words
    # together, and \btimur\b would leave it behind in FOOD STAPLES.
    R(FS, r"timur", SPICE, "2.1", _PICKLE,
      "all timur: dana, dhulo, chop, akabare chop. Pickles excluded, see 2.3"),
    R(FS, r"\bjimbu\b", SPICE, "2.1", _PICKLE),
    R(FS, r"\bsilam\b", SPICE, "2.1", _PICKLE),
    R(FS, r"\bbhango\b", SPICE, "2.1", _PICKLE),
    N(FS, "ROSEMARY 1KG", SPICE, "2.1"),
    N(FS, "OREGANO 1KG", SPICE, "2.1"),
    N(FS, "ST MIX HERBS 60GM", SPICE, "2.1"),
    N(FS, "ST CHILIFLAKES 60GM", SPICE, "2.1",
      "spec wrote 'ST Chiliflakes 60gm'"),
    N(FS, "RED CHILLI FLAKES 1KG", SPICE, "2.1"),
    N(FS, "Pizza Spices Mix 60gm", SPICE, "2.1"),
    N(FS, "Ginger Paste 200g", SPICE, "2.1"),

    # --- 2.1 spice blends and masala -------------------------------------
    # "masala" as a family would also catch Masala Chakku (a knife, 2.8) and
    # Smriti Masala Bhatta, so the blends are named individually.
    N(FS, "BMC BIRYANI MASALA 100g", SPICE, "2.1", "spec wrote 'BMC: Biryani'"),
    N(FS, "BMC Chat Masala 100gm", SPICE, "2.1"),
    N(FS, "BMC Chicken Masala 100gm", SPICE, "2.1"),
    N(FS, "BMC MEAT MASALA 25gm", SPICE, "2.1"),
    N(FS, "BMC Meat Masala 200g", SPICE, "2.1"),
    N(FS, "BMC Momo Masala 100gm", SPICE, "2.1"),
    N(FS, "BMC Curry Powder 100gm", SPICE, "2.1"),
    N(FS, "BMC KASOORI METHI 25g", SPICE, "2.1"),
    N(FS, "Century Garam Masala 100gm", SPICE, "2.1"),
    N(FS, "Century Meat Masala 50gm", SPICE, "2.1"),
    N(FS, "Century MixMasala 80gm", SPICE, "2.1"),
    N(FS, "CURRENT MEAT MASALA 100GM", SPICE, "2.1"),
    N(FS, "Current Chowmein Masala 50gm", SPICE, "2.1"),
    N(FS, "Current WhitePepper Powder 50gm", SPICE, "2.1"),
    N(FS, "Trust Garam Masala 100gm", SPICE, "2.1"),
    N(FS, "UNITED GARAM MASALA 100GM", SPICE, "2.1"),
    N(FS, "Umga Garam Masala 100gm", SPICE, "2.1"),
    N(FS, "Garam Masala 50gm", SPICE, "2.1"),
    N(FS, "Sagar Sabji Masala 80g", SPICE, "2.1"),
    N(FS, "Sagar Sabji Masala 160g", SPICE, "2.1"),
    N(FS, "Sagar Sabji Masala 400g", SPICE, "2.1"),
    N(FS, "Chatpat Masala 100gm", SPICE, "2.1"),
    N(FS, "Chatpat Masala 200gm", SPICE, "2.1"),
    N(FS, "Chatpat Masala 500gm", SPICE, "2.1"),
    N(FS, "Sutkeri Masala 250gm", SPICE, "2.1"),
    N(FS, "Sutkeri Masala 400gm", SPICE, "2.1"),
    N(FS, "Krishma Sutkeri Masala 250gm", SPICE, "2.1"),
    N(FS, "Krishma Sutkeri Masala 500gm", SPICE, "2.1"),
    N(FS, "Rara Mix Masala 400gm", SPICE, "2.1"),
    N(FS, "Goldiee Fish Masala 50g", SPICE, "2.1"),
    N(FS, "Smriti Masala Bhatta", SPICE, "2.1"),
    N(FS, "TATTVA JAGERY MASALA TEA 600GM", SPICE, "2.1"),

    # --- 2.1 salt ---------------------------------------------------------
    # The 2.1 heading says "Salt, all of it" but its list does not include the
    # product literally named SALT, and 2.9 keeps SALT in FOOD STAPLES. The
    # enumerated items move; SALT stays. Flagged in the report.
    N(FS, "Battisa BireNun 500g", SPICE, "2.1"),
    N(FS, "Battisa BireNun 200g (DIKKA)", SPICE, "2.1"),
    N(FS, "Battisa SideNoon 500g", SPICE, "2.1", "spec wrote 'SideNoon 500g'"),
    N(FS, "SAGAR BIRENUN 100GM", SPICE, "2.1"),
    N(FS, "BARARI BLACK SALT 200GM", SPICE, "2.1"),
    N(FS, "BLACK SALT 500GM", SPICE, "2.1"),
    N(FS, "Krishma Black Salt Powder 100gm", SPICE, "2.1"),

    # --- 2.1 MSG and cinnamon --------------------------------------------
    N(FS, "Fufeng Testing 190gm", SPICE, "2.1"),
    N(FS, "Testing 40gm", SPICE, "2.1"),
    N(FS, "LONG STICK", SPICE, "2.1", "Gaule brand, confirmed cinnamon bark"),

    # --- 2.2 nuts, dry fruits and snacks -> SNACKS ------------------------
    N(FS, "BADAM RAMRO", "SNACKS", "2.2"),
    N(FS, "Badam", "SNACKS", "2.2"),
    N(FS, "Trust Almond 500gm", "SNACKS", "2.2"),
    N(FS, "TRUST KAJU 500GM", "SNACKS", "2.2"),
    N(FS, "Krishma Premium Kaju 200gm 210W", "SNACKS", "2.2"),
    N(FS, "TRUST PISTA 500GM", "SNACKS", "2.2"),
    N(FS, "Krishma Mixnut 100gm", "SNACKS", "2.2"),
    N(FS, "Krishma Pre Mixnut 500gm", "SNACKS", "2.2",
      "spec wrote 'Pre Mixnut 500gm', Krishma carried over from the line above"),
    N(FS, "Krishma Mixnut S.P 500gm", "SNACKS", "2.2",
      "spec wrote 'Mixnut S.P 500gm'"),
    N(FS, "Krishma Pre Mix&nut 100gm", "SNACKS", "2.2",
      "spec wrote 'Pre Mix&nut 100gm'"),
    N(FS, "Krishma Pre Mix&nut 200gm", "SNACKS", "2.2",
      "spec wrote 'Pre Mix&nut 200gm'"),
    N(FS, "MIX AND NUT 300GM", "SNACKS", "2.2"),
    N(FS, "TRUST MAGAJ 500GM", "SNACKS", "2.2"),
    N(FS, "Krishma (Magaj) Melon Seeds 100gm", "SNACKS", "2.2"),
    N(FS, "krishma okhar 500gm", "SNACKS", "2.2"),
    N(FS, "Krishma Okhar 300gm", "SNACKS", "2.2"),
    N(FS, "TRUST OKHAR GUDI 150GM", "SNACKS", "2.2"),
    N(FS, "Trust Okhar Gudi 75gm", "SNACKS", "2.2"),
    N(FS, "Krishma Anjir 100gm", "SNACKS", "2.2"),
    N(FS, "Trust Green Kismiss 500gm", "SNACKS", "2.2"),
    N(FS, "Trust Mishri 500g", "SNACKS", "2.2"),
    N(FS, "Trust Cutting Mishri 500g", "SNACKS", "2.2"),
    N(FS, "Krishma Cutting Mishri 400g", "SNACKS", "2.2"),
    N(FS, "Coconut Dry", "SNACKS", "2.2"),
    N(FS, "COCONUT DRY", "SNACKS", "2.2",
      "data has a double space, 'COCONUT  DRY'"),
    N(FS, "Coconut Powder 500gm", "SNACKS", "2.2"),
    N(FS, "TRUST PEANUT 300GM", "SNACKS", "2.2"),
    N(FS, "TRUST PEANUT 200GM", "SNACKS", "2.2"),
    N(FS, "TRUST CHANA 400 GM", "SNACKS", "2.2",
      "spec wrote 'TRUST CHANA 400GM'; data has a space before GM"),
    N(FS, "TRUST CHANA 180 GM", "SNACKS", "2.2",
      "spec wrote 'TRUST CHANA 180GM'; data has a space before GM"),
    N(FS, "Laxmi Roasted Chana 375gm", "SNACKS", "2.2"),
    N(FS, "Laxmi Roasted Chana 175gm", "SNACKS", "2.2"),
    # savoury
    N(FS, "Smriti Dalmot 1kg", "SNACKS", "2.2"),
    N(FS, "Smriti Dalmot 350GM", "SNACKS", "2.2"),
    N(FS, "Smriti Sada Dalmot 500GM", "SNACKS", "2.2",
      "spec wrote 'Sada Dalmot 500GM'"),
    N(FS, "TRUST DALMOTH 320GM", "SNACKS", "2.2"),
    N(FS, "Gyan Bhuja 400g", "SNACKS", "2.2"),
    N(FS, "NIMKIN Small", "SNACKS", "2.2"),
    N(FS, "Krishma Dhumri 180gm", "SNACKS", "2.2"),
    N(FS, "Dhumra 250gm", "SNACKS", "2.2"),
    N(FS, "KRISHMA 3D PAPAD 180GM", "SNACKS", "2.2"),
    N(FS, "TRUST PAPAD", "SNACKS", "2.2"),
    N(FS, "Century Nachoz", "SNACKS", "2.2"),
    N(FS, "Century Panipuri 175gm", "SNACKS", "2.2", "spec wrote 'Century 175gm'"),
    N(FS, "Century Panipuri 350gm", "SNACKS", "2.2", "spec wrote 'Century 350gm'"),
    N(FS, "Krishma PaniPuri 900g", "SNACKS", "2.2", "spec wrote 'Krishma 900g'"),
    N(FS, "BARAHI PANIPURI 400GM", "SNACKS", "2.2", "spec wrote 'BARAHI 400GM'"),
    N(FS, "BERLINO PANIPURI 175GM", "SNACKS", "2.2", "spec wrote 'BERLINO 175GM'"),
    N(FS, "BERLINO PANIPURI 500GM", "SNACKS", "2.2", "spec wrote 'BERLINO 500GM'"),
    N(FS, "Laxmi Special Corn Mix 500gm", "SNACKS", "2.2"),
    N(FS, "Smriti Mix Makai", "SNACKS", "2.2"),
    N(FS, "Smriti Sada Makai", "SNACKS", "2.2"),
    N(FS, "SMRITI SADA BHATTA 350GM", "SNACKS", "2.2"),
    N(FS, "MAKAI CHIURA 250GM", "SNACKS", "2.2"),
    N(FS, "MAKAI CHIURA CHEESE 250GM", "SNACKS", "2.2"),
    N(FS, "MAKAI AMILO PIRO 250GM", "SNACKS", "2.2"),
    N(FS, "Black Chokda 500gm", "SNACKS", "2.2"),
    N(FS, "Dry Khatto", "SNACKS", "2.2"),
    N(FS, "BIKANO ALL IN ONE 260G", "SNACKS", "2.2"),
    # sweets and mouth fresheners
    N(FS, "MITHO TITAURA RS.75", "SNACKS", "2.2"),
    N(FS, "MITHO TITAURA RS.145", "SNACKS", "2.2"),
    N(FS, "Kubindo Sweet", "SNACKS", "2.2"),
    N(FS, "Gudpak 425gm", "SNACKS", "2.2"),
    N(FS, "PASSPASS FRUIT MIX 105G", "SNACKS", "2.2"),
    N(FS, "PASSPASS MAGIC MIX 105G", "SNACKS", "2.2"),
    N(FS, "PASSPASS MINTY MIX 105G", "SNACKS", "2.2"),
    N(FS, "PASSPASS SAUNF DELIGHT MIX 105G", "SNACKS", "2.2"),
    N(FS, "LUVIT CHOCWICH 20PCS WHITE", "SNACKS", "2.2"),
    N(FS, "LUVIT CHOCWICH 20PCS BROWN", "SNACKS", "2.2"),

    # --- 2.3 pickles, sauces, preserved meat -> CANNED -------------------
    N(FS, "Jomsom Timur Pickle", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "Jomsom Timur Pickle 500GM", "CANNED AND PACKAGED FOODS", "2.3",
      "spec wrote 'Timur Pickle 500GM'"),
    N(FS, "Jomsom Garlic Pickle", "CANNED AND PACKAGED FOODS", "2.3",
      "spec wrote 'Garlic Pickle'"),
    N(FS, "Jomsom Garlic Pickle 500GM", "CANNED AND PACKAGED FOODS", "2.3",
      "spec wrote 'Garlic Pickle 500GM'"),
    N(FS, "Century Mix Pickle 400gm", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "Century Mango Pickle 400gm", "CANNED AND PACKAGED FOODS", "2.3",
      "spec wrote 'Mango Pickle 400gm'"),
    N(FS, "CENTURY GARLIC PICKLE 400GM", "CANNED AND PACKAGED FOODS", "2.3",
      "spec wrote 'GARLIC PICKLE 400GM'"),
    N(FS, "PAICHO MIX PICKLE 1kg", "CANNED AND PACKAGED FOODS", "2.3",
      "spec wrote 'MIX PICKLE 1kg'"),
    N(FS, "Paicho Mango Pickle 1kg", "CANNED AND PACKAGED FOODS", "2.3",
      "spec wrote 'Mango Pickle 1kg'"),
    N(FS, "Paicho Gosseberry Pickle 400g", "CANNED AND PACKAGED FOODS", "2.3",
      "spec wrote 'Gosseberry Pickle 400g'"),
    N(FS, "Paicho Lemon Pickle 400gm", "CANNED AND PACKAGED FOODS", "2.3",
      "spec wrote 'Lemon Pickle 400gm'"),
    N(FS, "Paicho Methi Pickle 400g", "CANNED AND PACKAGED FOODS", "2.3",
      "spec wrote 'Methi Pickle 400g'"),
    N(FS, "Paicho Lapsi Pickle 400gm", "CANNED AND PACKAGED FOODS", "2.3",
      "spec wrote 'Lapsi Pickle 400gm'"),
    N(FS, "Paicho Akabare Paste 400gm", "CANNED AND PACKAGED FOODS", "2.3",
      "spec wrote 'Akabare Paste 400gm'"),
    N(FS, "DRUK MANGO PICKLE 400ML", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "Chicken Pickle 30gm", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "CHICKEN PICKLE 350GM", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "CHICKEN PICKLE 500GM", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "BUFF PICKLE 350GM", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "BUFF PICKLE 500GM", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "MUTTON KAAN JIBRO PICKLE 350GM", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "OYSTER SAUCE 4.5LTR", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "Kikkoma Soya Sauce 1L", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "KIKKOMEN SOYA SAUCE 1.9LTR", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "AG SOYA SAUCE 1LTR", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "9PM Schezwan Chutney 250gm", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "NILONS PIZZA SAUCE 250GM", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "DRUK TOMATO CHILLI 500ML", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "CHICKEN KHURAK", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "BUFF KHURAK", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "MUTTON KHURAK", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "MANAKO SUKUTI", "CANNED AND PACKAGED FOODS", "2.3"),
    N(FS, "MANAKO PERUNGO FISH", "CANNED AND PACKAGED FOODS", "2.3"),

    # --- 2.4 rice -> RICE -------------------------------------------------
    N(FS, "Hulas Basmati 1kg", "RICE", "2.4"),
    N(FS, "Hulas Basmati 5kg", "RICE", "2.4"),
    N(FS, "Hulas Basmati 10kg", "RICE", "2.4"),
    N(FS, "Hulas Basmati 20kg", "RICE", "2.4"),
    N(FS, "Sagar Anadi Chamal 1kg", "RICE", "2.4"),
    N(FS, "GAULE ANADI CHAMAL 1KG", "RICE", "2.4"),
    N(FS, "Shiramla Chamal", "RICE", "2.4"),
    N(FS, "JAAU KO CHAMAL 1KG", "RICE", "2.4"),

    # --- 2.5 baby formula -> BABY CARE ------------------------------------
    N(FS, "LACTOGEN 1 400G", "BABY CARE", "2.5"),
    N(FS, "LACTOGEN 2 400G", "BABY CARE", "2.5"),
    N(FS, "LACTOGEN 3 400G", "BABY CARE", "2.5"),
    N(FS, "LACTOGEN 4 400G", "BABY CARE", "2.5"),
    N(FS, "CERL STA1 WHEAPP 300GM", "BABY CARE", "2.5"),
    N(FS, "CERL STA2 WHEAPPCHRY300G", "BABY CARE", "2.5"),
    N(FS, "CERL STA3 WHERIMXDFRT300G", "BABY CARE", "2.5"),
    N(FS, "CERELAC STA4 MU&FRT300G", "BABY CARE", "2.5"),
    N(FS, "CERL STA5GRA&FRTPOSHAN300G", "BABY CARE", "2.5"),

    # --- 2.6 dairy -> DAIRY PRODUCTS --------------------------------------
    # The spec lists four chhurpi entries. Data holds four products whose names
    # differ only by case and spacing, so the set matches even though the
    # spec-to-product pairing is not one to one.
    N(FS, "Local Milk 500ml", "DAIRY PRODUCTS", "2.6"),
    N(FS, "Chhurpi 80gm", "DAIRY PRODUCTS", "2.6"),
    N(FS, "Chhurpi 500gm", "DAIRY PRODUCTS", "2.6"),
    N(FS, "CHHURPI 50GM", "DAIRY PRODUCTS", "2.6"),
    N(FS, "chhurpi 50gm", "DAIRY PRODUCTS", "2.6",
      "data has 'chhurpi  50gm' with a double space"),

    # --- 2.7 fresh produce -> FRESH PRODUCE -------------------------------
    N(FS, "Chicken Egg", "FRESH PRODUCE", "2.7"),
    N(FS, "MS Aloo", "FRESH PRODUCE", "2.7"),

    # --- 2.8 non-food out of FOOD STAPLES ---------------------------------
    N(FS, "RUCHI WHITE PHENYL 500ML", "CLEANING SUPPLIES", "2.8"),
    N(FS, "MatchStick Rs2", "HOUSEHOLD ITEMS", "2.8"),
    N(FS, "CHAKKU RS.100", "HOUSEHOLD ITEMS", "2.8"),
    N(FS, "Masala Chakku", "HOUSEHOLD ITEMS", "2.8"),
    # Correction, confirmed 17 Aug 2026: the spec filed this under 2.8, moves
    # out of FOOD STAPLES, but the product sits in TEA AND SPICES. The other
    # two chakku products are in FOOD STAPLES and stay under 2.8 above.
    N(SPICE, "Chakku", "HOUSEHOLD ITEMS", "2.8",
      "spec placed this in FOOD STAPLES; it is in TEA AND SPICES"),
    N(FS, "KRISHMA FITKARI 100GM", "PERSONAL CARE", "2.8"),
    N(FS, "KRISHMA FITKARI 200GM", "PERSONAL CARE", "2.8"),
    N(FS, "Krishma Fitkari Dhika 100gm", "PERSONAL CARE", "2.8",
      "spec wrote 'Fitkari Dhika 100gm'"),
]


# ----------------------------------------------------------------------
# PART 4: out of HOUSEHOLD ITEMS
# ----------------------------------------------------------------------

HH = "HOUSEHOLD ITEMS"
CLEAN = "CLEANING SUPPLIES"

RULES += [
    # --- 4.1 dishwashing --------------------------------------------------
    R(HH, r"^EXO\b", CLEAN, "4.1", note="EXO dishwash and EXO Jali"),
    R(HH, r"P Dishwash Gel", CLEAN, "4.1"),
    R(HH, r"Sunday Dishwash", CLEAN, "4.1"),
    R(HH, r"BRIO DISHWASH", CLEAN, "4.1"),
    R(HH, r"PATANJALI DISHWASH", CLEAN, "4.1"),

    # --- 4.1 laundry ------------------------------------------------------
    R(HH, r"^Patanjali (Detergent|Superior Det) Powder", CLEAN, "4.1",
      note="spec said 'Patanjali Detergent Powder'; the Superior Det Powder "
           "1kg is the same product family and is included"),
    R(HH, r"^SURF (MT|EXL)", CLEAN, "4.1"),
    R(HH, r"\bEzee\b", CLEAN, "4.1", note="Godrej Ezee 1l and EZEE 500GM"),
    R(HH, r"^Comfort", CLEAN, "4.1", note="Fab Con Blue/Pink and COMFORT BLUE"),
    R(HH, r"^Vanish", CLEAN, "4.1"),

    # --- 4.1 floor and surface -------------------------------------------
    R(HH, r"Surya Phynel", CLEAN, "4.1"),
    R(HH, r"Safe Life Phenyl", CLEAN, "4.1"),
    R(HH, r"Black Phynel", CLEAN, "4.1"),
    R(HH, r"PILOT FLOOR CLEANER", CLEAN, "4.1"),
    R(HH, r"^LYS\b", CLEAN, "4.1"),
    R(HH, r"Essence BSC", CLEAN, "4.1"),
    R(HH, r"MR MUSCLE|Mr Muscle", CLEAN, "4.1"),
    R(HH, r"^COLIN\b", CLEAN, "4.1"),
    R(HH, r"C2 KITCHEN CLEANER", CLEAN, "4.1"),
    R(HH, r"Quick Gel Pitambari", CLEAN, "4.1"),

    # --- 4.1 toilet and bathroom -----------------------------------------
    R(HH, r"^DOMEX", CLEAN, "4.1"),
    R(HH, r"^SANIFRESH", CLEAN, "4.1"),
    # Correction, confirmed 17 Aug 2026: the typo is in the data, not the spec.
    N(HH, "S/F Barthroom Cleaner 500ml", CLEAN, "4.1",
      "spec spelled it correctly as 'S/F Bathroom Cleaner'; the data has "
      "'Barthroom'. Data spelling used so the rule matches"),
    R(HH, r"^TOILET CLEANER|^Toilet Cleaner", CLEAN, "4.1",
      note="2pcs, 4pcs, 10PCS"),
    R(HH, r"Urinal Cube", CLEAN, "4.1"),
    R(HH, r"RBI LIQ Sglo", CLEAN, "4.1"),

    # --- 4.1 bleach and drain --------------------------------------------
    R(HH, r"\bbleach\b", CLEAN, "4.1", note="HRP, Kao, RBI, RBL"),
    R(HH, r"^Dranex", CLEAN, "4.1"),

    # --- 4.1 washing machine ---------------------------------------------
    R(HH, r"^WASHING MACHINE", CLEAN, "4.1",
      note="CLEANER, CLEANER 15G, TABLET"),

    # --- 4.1 tools --------------------------------------------------------
    # `scrub` covers the data misspelling "SCRUBER RUMAL". `^SPONGE` is
    # anchored so bath sponges (4.2) and HELIOS shine sponges (shoe care) are
    # not caught by it.
    R(HH, r"scrub", CLEAN, "4.1", exclude=r"Sunday Dishwash",
      note="Scrubber 50gm, SCRUBER RUMAL, Steel Scrubber, STEEL SCRUBBER JALI"),
    R(HH, r"^SPONGE", CLEAN, "4.1", note="sponge block, form pads, pad colour"),
    R(HH, r"Polister Greenpad", CLEAN, "4.1"),
    R(HH, r"\bmop\b", CLEAN, "4.1"),
    R(HH, r"\bwiper\b", CLEAN, "4.1"),
    R(HH, r"CELLING BRUSH|ANCOR BRUSH|PLASTIC BROOM|Tile Brush|Til Brush"
          r"|Cloth Washing Brush|Bottle Brush|FOOT BRUSH", CLEAN, "4.1",
      note="the brush list named in the spec: ceiling, ancor, plastic broom, "
           "tile, til, cloth washing, bottle, foot"),
    R(HH, r"CLEANING RUMAL", CLEAN, "4.1"),
    R(HH, r"KITCHEN RUMAL", CLEAN, "4.1"),
    R(HH, r"MICRO FIBER TOWEL", CLEAN, "4.1"),
    R(HH, r"KITCHEN WIPES", CLEAN, "4.1"),
    R(HH, r"\bgloves\b", CLEAN, "4.1", exclude=r"^BATH",
      note="bath gloves go to PERSONAL CARE, see 4.2"),
    R(HH, r"PET STAIN REMOVER", CLEAN, "4.1"),

    # --- 4.1 air fresheners and deodorisers -------------------------------
    R(HH, r"^AER\b|^Aer\b", CLEAN, "4.1"),
    R(HH, r"^Odonil", CLEAN, "4.1"),
    R(HH, r"^GLADE", CLEAN, "4.1"),
    R(HH, r"^STELLA|^Stella", CLEAN, "4.1"),
    R(HH, r"AIR ?CARE", CLEAN, "4.1", note="AIR CARE, 4PCS AIR CARE, AIRCARE KAPUR"),
    R(HH, r"DILING", CLEAN, "4.1", note="DILING KAPUR and DILING N BALLS"),
    N(HH, "KAPOOR 30GM", CLEAN, "4.1"),
    R(HH, r"Nature Room Spray", CLEAN, "4.1"),
    R(HH, r"LURE ROOM SPRAY", CLEAN, "4.1"),
    R(HH, r"SANATIVE AIR FRESHENER", CLEAN, "4.1"),
    # Both spellings are enumerated rather than guessed at with optional
    # letters: the data has "Naphthalene" and the misspelling "Nepthalene",
    # and a clever pattern silently missed the second.
    R(HH, r"naphthalene|nepthalene|^N BALL|^N/B ", CLEAN, "4.1",
      note="Grapple Naphthalene Balls, Nepthalene Ball, N BALL, N/B"),
    R(HH, r"TRU NATURE", CLEAN, "4.1"),
    R(HH, r"HRP ITC STFISH", CLEAN, "4.1"),

    # --- 4.1 pest control -------------------------------------------------
    # \bHIT\b is required: a substring test matches "WHITE KITCHEN RUMAL".
    R(HH, r"\bHIT\b|^Hit ", CLEAN, "4.1",
      note="sprays, chalk, roach gel, rat cake, rat glue pad"),
    R(HH, r"^BAYGON|^Baygon", CLEAN, "4.1"),
    R(HH, r"GK REDCOIL|GK FLASH ?GOLD|GK FlashGold", CLEAN, "4.1"),
    R(HH, r"Maxo Liquid", CLEAN, "4.1"),
    R(HH, r"^MRT ", CLEAN, "4.1", note="MRT RAT KILL and MRT INST VPR"),
    N(HH, "N-rat", CLEAN, "4.1"),
    N(HH, "Fly Catcher", CLEAN, "4.1"),
    R(HH, r"COCKROACH CHALK POWDER", CLEAN, "4.1"),
    R(HH, r"MOSQUITO BAT", CLEAN, "4.1"),

    # --- 4.1 shoe care ----------------------------------------------------
    R(HH, r"^HELIOS", CLEAN, "4.1"),
    N(HH, "CHEARY BLACK POLISH", CLEAN, "4.1"),
    R(HH, r"Kiwi Liquid Polish", CLEAN, "4.1"),
    R(HH, r"^CHB (WAX|LIQ)", CLEAN, "4.1"),
    N(HH, "Shoe Brush", CLEAN, "4.1"),

    # --- 4.2 -> PERSONAL CARE ---------------------------------------------
    R(HH, r"^BATH|^Bath", "PERSONAL CARE", "4.2",
      note="bath sponges, jalo roll/butterfly, bathstone, tato gloves, "
           "sponge gloves, bathroom sponge long, bath sponj long"),
    N(HH, "COTTON BUDS PACKETS", "PERSONAL CARE", "4.2"),
    N(HH, "COTTON ROLL 400GM GROSS", "PERSONAL CARE", "4.2"),
    N(HH, "VICKS INHALER 0.5ML", "PERSONAL CARE", "4.2"),
    N(HH, "VICKS VAPORUB 10ML", "PERSONAL CARE", "4.2"),
    N(HH, "DRABYAN LIQUID BALM 4ML", "PERSONAL CARE", "4.2"),
    N(HH, "DTT SANITIZER REG 200ML", "PERSONAL CARE", "4.2"),
    N(HH, "PNS ANTI-DANDRUFF 625ML", "PERSONAL CARE", "4.2"),
    R(HH, r"SAFE LIFE NORMAL MASK", "PERSONAL CARE", "4.2",
      note="data appends '(B.W.B)'"),
    R(HH, r"SF SURGICAL MASK", "PERSONAL CARE", "4.2",
      note="data appends '(BW)'"),
    N(HH, "NAILCUTTER MEDIUM", "PERSONAL CARE", "4.2"),
    N(HH, "NAILCUTTER BIG", "PERSONAL CARE", "4.2"),
    N(HH, "NAIL CUTTER", "PERSONAL CARE", "4.2"),
    N(HH, "NAIL FILER STEEL BIG", "PERSONAL CARE", "4.2"),
    N(HH, "SOAP CASE", "PERSONAL CARE", "4.2",
      "data has a trailing space, 'SOAP CASE '"),
    N(HH, "MINICARE SET SMALL", "PERSONAL CARE", "4.2"),
    N(HH, "Floss Toothpick", "PERSONAL CARE", "4.2"),

    # --- 4.3 -> POOJA ITEMS -----------------------------------------------
    R(HH, r"^HOLI PICHKARI", "POOJA ITEMS", "4.3"),
    N(HH, "HOLI COLOR", "POOJA ITEMS", "4.3"),
    N(HH, "HOLI BALLON RS.10", "POOJA ITEMS", "4.3"),
    R(HH, r"^Bhai Masala", "POOJA ITEMS", "4.3"),
    R(HH, r"^TULSI SLIVER POUCH", "POOJA ITEMS", "4.3"),
    R(HH, r"^No\. (7|10) Candle$|^Candles Small$|^Candle_Big$",
      "POOJA ITEMS", "4.3", note="the four candles named in the spec"),

    # --- 4.4 -> STATIONERY ------------------------------------------------
    N(HH, "Adhesive Cartoon Tape 250gm", "STATIONERY", "4.4"),
    N(HH, "Adhesive Tape", "STATIONERY", "4.4"),
    N(HH, "Adhesive Tape Small", "STATIONERY", "4.4"),
    N(HH, "Double Tape", "STATIONERY", "4.4"),
    N(HH, "FEVI KWIK", "STATIONERY", "4.4"),
    N(HH, "Colourful Envelop", "STATIONERY", "4.4"),
    N(HH, "Colourful Long Envelop", "STATIONERY", "4.4"),

    # --- 6.5 -> ELECTRICAL SUPPLIES ---------------------------------------
    R(HH, r"\bbatter(y|ies)\b|\bbulb\b|Everyday Ultima|EvRe Light"
          r"|Chota Power|^Ultra (AA|AAA|LONG|Longer)",
      "ELECTRICAL SUPPLIES", "6.5",
      note="the spec's own match list: battery, bulb, Ultra AA/AAA/C2/D2, "
           "Everyday Ultima, EvRe Light, Chota Power"),
    # The spec's suggested match list above does not cover three products the
    # spec itself names in 6.5: none of them contains "battery". Added as
    # explicit names so its enumeration and its match keys agree.
    N(HH, "Maxell Alkaline D-Size", "ELECTRICAL SUPPLIES", "6.5",
      "named in 6.5 but not caught by the spec's own keyword list"),
    N(HH, "Maxell Super Power ACE (AA2 RED)", "ELECTRICAL SUPPLIES", "6.5",
      "named in 6.5 but not caught by the spec's own keyword list"),
    N(HH, "Maxell Power AA4 RED", "ELECTRICAL SUPPLIES", "6.5",
      "named in 6.5 but not caught by the spec's own keyword list"),
]


# ----------------------------------------------------------------------
# PART 5: out of PERSONAL CARE
# ----------------------------------------------------------------------

PC = "PERSONAL CARE"

RULES += [
    N(PC, "H.P WET TISSUE", HH, "5.1"),
    N(PC, "Pre BoxTissue 100S", HH, "5.1"),
    N(PC, "Pre BoxTissue 80S", HH, "5.1"),
    N(PC, "GOLDEN TISSUE", HH, "5.1"),
    N(PC, "Pure Pocket Tissue", HH, "5.1"),
    N(PC, "Johnsoni Baby Cream 50g Milk", "BABY CARE", "5.2"),
    N(PC, "Para Skinpure Extra Virgincno BabyOil 250ml", "BABY CARE", "5.2"),
    N(PC, "Byron BabyBrush", "BABY CARE", "5.2"),
    N(PC, "Wet Wipes", "BABY CARE", "5.2"),
]


# ----------------------------------------------------------------------
# PART 6: other categories
# ----------------------------------------------------------------------

RULES += [
    # 6.1 SNACKS -> NOODLES. Source is the renamed SNACKS category, formerly
    # NAMKEEN AND SNACKS. The three Samyang sauces stay: they are sauces, not
    # noodles, and the spec does not list them.
    N("SNACKS", "Samyang Bulda Chi. Rose 140g", "NOODLES", "6.1"),
    N("SNACKS", "Samyang Bulda Chi. Carbo Topaki 185g", "NOODLES", "6.1",
      "spec wrote 'Carbo Topaki 185g'"),
    N("SNACKS", "Samyang Bulda Chi. Flav Topaki 185g", "NOODLES", "6.1",
      "spec wrote 'Flav Topaki 185g'"),
    N("SNACKS", "SAMYANG HOT RAMYUN CUP", "NOODLES", "6.1"),
    N("SNACKS", "SAMYANG 2X RAMYUN CUP", "NOODLES", "6.1"),
    N("SNACKS", "Samyang Carbo Cup 80g", "NOODLES", "6.1"),
    N("SNACKS", "SAMYANG QUATTRO CHEESE", "NOODLES", "6.1"),
    N("SNACKS", "Samyang Garlic Oil Pasta 100g", "NOODLES", "6.1"),
    N("SNACKS", "Samyang Mushroom Pasta 100g", "NOODLES", "6.1"),
    N("SNACKS", "Nongshim Sea Food Ramyun", "NOODLES", "6.1"),
    N("SNACKS", "NONGSHIM NEOGURI RAMYUN", "NOODLES", "6.1"),
    N("SNACKS", "NongShim Super Spicy cup 68gm", "NOODLES", "6.1"),
    N("SNACKS", "NongShim Super Spicy 120gm", "NOODLES", "6.1"),
    N("SNACKS", "NONGSHIM TOOMBA 137GM", "NOODLES", "6.1"),

    # 6.2 TEA AND SPICES -> FOOD STAPLES. The spec's sixth line, Sagar Chamal
    # Pitho 1kg, is already in FOOD STAPLES and is not a move.
    N(SPICE, "Sagar PhaparPitho 1kg", FS, "6.2"),
    N(SPICE, "Sagar KodoPitho 1kg", FS, "6.2"),
    N(SPICE, "Sagar Beshan 500g", FS, "6.2"),
    N(SPICE, "Sagar Beshan 200g", FS, "6.2"),
    N(SPICE, "Battisa Chamal Pitho 1kg", FS, "6.2"),

    # 6.3 CANNED -> FOOD STAPLES
    N("CANNED AND PACKAGED FOODS", "Umga Roll Mix Dal 1kg", FS, "6.3"),
    N("CANNED AND PACKAGED FOODS", "Urja Masoor Dal Small 1kg", FS, "6.3"),

    # 6.4 CANNED -> SNACKS
    N("CANNED AND PACKAGED FOODS", "BIK MOONG DAL PLAIN 190GM", "SNACKS", "6.4"),
    N("CANNED AND PACKAGED FOODS", "BIKANO MOONG DAL 130G", "SNACKS", "6.4"),
    N("CANNED AND PACKAGED FOODS", "BIKANO MOONG DAL 260G", "SNACKS", "6.4"),
    N("CANNED AND PACKAGED FOODS", "HAL MOONG DAL-360gm", "SNACKS", "6.4",
      "data has a double space, 'HAL MOONG  DAL-360gm'"),
    N("CANNED AND PACKAGED FOODS", "SV MOONG DAL 160GM", "SNACKS", "6.4"),
    N("CANNED AND PACKAGED FOODS", "SV MOONG DAL RS.50", "SNACKS", "6.4",
      "spec wrote 'SV MOONG DAL 160GM, RS.50' on one line"),
]


# ----------------------------------------------------------------------
# RESEARCHER ADDITIONS, confirmed 17 August 2026.
#
# These are NOT in reports/CATEGORY_REMAP_SPEC.md. They came out of the dry
# run's own findings and were then decided. Their refs start with R so they can
# never be mistaken for a spec section, and so the spec file can be updated to
# match later.
#
# R1  the section 5b flags, each resolved individually. The flags this list
#     does NOT contain were resolved as "stays": UMBRELLA BABY, all Till and
#     sesame products, and Gaule Chukamilo. A product that stays needs no rule.
# R2  dalmot consolidation. The spec split one product line across three
#     categories: Smriti Dalmot 1kg and 350GM move to SNACKS under 2.2 while
#     Smriti Dalmot 500GM and 700gm sit in CANNED AND PACKAGED FOODS, and 6.4
#     moves four moong dal namkeen but leaves four more behind. This rule is
#     source-agnostic so the whole line lands in one place.
# ----------------------------------------------------------------------

RULES += [
    # --- R1: section 5b flags resolved --------------------------------------
    N(FS, "Krishma Makhana 70gm", "SNACKS", "R1", "5b flag: fox nuts, a snack"),
    R(HH, r"^TOILET BRUSH", CLEAN, "R1",
      note="5b flag: all four TOILET BRUSH variants, stand included"),
    R(HH, r"^Air ?Freshner ATM", CLEAN, "R1",
      note="5b flag: AIR FRESHNER ATM 70GM and AirFreshner ATM"),
    N(HH, "Rat Glue", CLEAN, "R1", "5b flag: pest control"),
    N(HH, "Car Duster S-94", CLEAN, "R1", "5b flag: cleaning tool"),

    # --- R2: dalmot and moong dal namkeen consolidation ---------------------
    # Deliberately NOT matched: "Mong Dal", "Mong Geda", "Mong Khosta" and
    # "Urja Moong Khosta Dal 1kg" are real lentils. None contains the adjacent
    # string "moong dal", so the pattern cannot reach them. Every match is
    # printed in section 1b for confirmation.
    R(ANY, r"dalmot|dalmoth|moong dal", "SNACKS", "R2",
      note="every dalmot/dalmoth/moong dal namkeen, any source category"),
    N("CANNED AND PACKAGED FOODS", "Hal Moong 1kg", "SNACKS", "R2",
      "named explicitly in the consolidation; a 1kg pack, so confirm it is "
      "namkeen and not a lentil pack"),
]


# ----------------------------------------------------------------------
# STAY lists, used only to detect contradictions. These never move anything.
# A product that a move rule claims while a STAY family also names it is a
# genuine tension in the spec and is reported.
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class Stay:
    source: str
    pattern: str
    ref: str


STAYS: list[Stay] = [
    Stay(FS, r"\bchiura\b", "2.9 chiura (all)"),
    Stay(FS, r"\bmakai\b", "2.9 makai"),
    Stay(FS, r"\bbhatta\b", "2.9 bhatta"),
    Stay(FS, r"^SALT$", "2.9 SALT"),
    Stay(FS, r"\bchana\b", "2.9 chana"),
    Stay(FS, r"\bbesan\b|\bbeshan\b", "2.9 besan"),
    Stay(HH, r"\bballon\b|\bballoon\b", "4.5 balloons"),
    Stay(HH, r"matchstick", "4.5 matchsticks"),
    Stay(HH, r"toothpick|TOOTH PICK", "4.5 toothpicks"),
    Stay(HH, r"kitchen knife|PEELING KNIFE", "4.5 kitchen knives"),
    Stay(PC, r"rose water", "5.3 all rose water"),
]


# ----------------------------------------------------------------------
# What the spec actually said, for every rule whose wording differs from the
# product name it resolves to. This is the confirm-or-correct list: each entry
# is a place where the spec cannot be matched literally and I made a decision.
#
# SPEC_WORDING covers exact-name rules, keyed by the resolved pattern.
# SPEC_FAMILY covers "all X" rules, keyed by the regex.
# A check at the end of main() asserts every noted rule appears in exactly one
# of the two, so these cannot silently drift from the rule table.
# ----------------------------------------------------------------------

SPEC_WORDING: dict[str, str] = {
    # 2.1
    "BMC BIRYANI MASALA 100g": "BMC: Biryani",
    "Battisa SideNoon 500g": "SideNoon 500g",
    "ST CHILIFLAKES 60GM": "ST Chiliflakes 60gm",
    "LONG STICK": "LONG STICK (Gaule brand, confirmed cinnamon bark)",
    # 2.2
    "BARAHI PANIPURI 400GM": "BARAHI 400GM",
    "BERLINO PANIPURI 175GM": "BERLINO 175GM",
    "BERLINO PANIPURI 500GM": "BERLINO 500GM",
    "COCONUT DRY": "COCONUT DRY",
    "Century Panipuri 175gm": "Century 175gm",
    "Century Panipuri 350gm": "Century 350gm",
    "Krishma Mixnut S.P 500gm": "Mixnut S.P 500gm",
    "Krishma PaniPuri 900g": "Krishma 900g",
    "Krishma Pre Mix&nut 100gm": "Pre Mix&nut 100gm",
    "Krishma Pre Mix&nut 200gm": "Pre Mix&nut 200gm",
    "Krishma Pre Mixnut 500gm": "Pre Mixnut 500gm",
    "Smriti Sada Dalmot 500GM": "Sada Dalmot 500GM",
    "TRUST CHANA 180 GM": "TRUST CHANA 180GM",
    "TRUST CHANA 400 GM": "TRUST CHANA 400GM",
    # 2.3
    "CENTURY GARLIC PICKLE 400GM": "GARLIC PICKLE 400GM",
    "Century Mango Pickle 400gm": "Mango Pickle 400gm",
    "Jomsom Garlic Pickle": "Garlic Pickle",
    "Jomsom Garlic Pickle 500GM": "Garlic Pickle 500GM",
    "Jomsom Timur Pickle 500GM": "Timur Pickle 500GM",
    "PAICHO MIX PICKLE 1kg": "MIX PICKLE 1kg",
    "Paicho Akabare Paste 400gm": "Akabare Paste 400gm",
    "Paicho Gosseberry Pickle 400g": "Gosseberry Pickle 400g",
    "Paicho Lapsi Pickle 400gm": "Lapsi Pickle 400gm",
    "Paicho Lemon Pickle 400gm": "Lemon Pickle 400gm",
    "Paicho Mango Pickle 1kg": "Mango Pickle 1kg",
    "Paicho Methi Pickle 400g": "Methi Pickle 400g",
    # 2.6, 2.8
    "chhurpi 50gm": "chhurpi 50gm",
    "Krishma Fitkari Dhika 100gm": "Fitkari Dhika 100gm",
    "Chakku": "Chakku (listed under 2.8, moves out of FOOD STAPLES)",
    # 4.1
    "S/F Barthroom Cleaner 500ml": "S/F Bathroom Cleaner",
    # 4.2
    "SOAP CASE": "SOAP CASE",
    # 6.1
    "Samyang Bulda Chi. Carbo Topaki 185g": "Carbo Topaki 185g",
    "Samyang Bulda Chi. Flav Topaki 185g": "Flav Topaki 185g",
    # 6.4
    "HAL MOONG DAL-360gm": "HAL MOONG DAL-360gm",
    "SV MOONG DAL RS.50": "SV MOONG DAL 160GM, RS.50",
    # 6.5
    "Maxell Alkaline D-Size": "Maxell Alkaline D-Size",
    "Maxell Super Power ACE (AA2 RED)": "Maxell Super Power ACE (AA2 RED)",
    "Maxell Power AA4 RED": "Maxell Power AA4 RED",
}

SPEC_FAMILY: dict[str, str] = {
    # 2.1
    r"\bmethi\b": "methi, kasoori methi; BMC Kasoori Methi, Century",
    r"\bsaffron\b": "APIS Saffron 1gm and 0.5gm, BLG Saffron 50gm",
    r"timur": "All timur products: timur ko dana, timur dhulo, timur chop, "
              "akabare timur chop",
    r"chill?[iy] powder": "chilli powder",
    r"lwang|sukmel|lwa/sukm": "lwang, sukmel",
    r"white ?pepper": "white pepper",
    # 4.1
    r"^EXO\b": "all EXO, EXO Jali products",
    r"^Patanjali (Detergent|Superior Det) Powder": "Patanjali Detergent Powder",
    r"\bEzee\b": "Godrej Ezee, EZEE 500GM",
    r"^Comfort": "Comfort Fab Con, Comfort Blue",
    r"^TOILET CLEANER|^Toilet Cleaner": "Toilet Cleaner 2pcs/4pcs/10PCS",
    r"\bbleach\b": "HRP BLEACH 1LTR, Kao Bleach 600ml, RBI Bleach 500ml, "
                   "RBL Bleach 200ml",
    r"^WASHING MACHINE": "WASHING MACHINE CLEANER, CLEANER 15G, TABLET",
    r"scrub": "all scrubbers, steel scrubbers",
    r"^SPONGE": "sponges, sponge pads",
    r"CELLING BRUSH|ANCOR BRUSH|PLASTIC BROOM|Tile Brush|Til Brush"
    r"|Cloth Washing Brush|Bottle Brush|FOOT BRUSH":
        "all brushes (ceiling, ancor, plastic broom, tile, cloth washing, "
        "bottle, foot, til)",
    r"\bgloves\b": "all gloves",
    r"AIR ?CARE": "all AIR CARE and AIRCARE KAPUR",
    r"DILING": "DILING KAPUR, DILING N BALLS",
    r"naphthalene|nepthalene|^N BALL|^N/B ": "all naphthalene balls",
    r"\bHIT\b|^Hit ": "all HIT products (sprays, chalk, roach gel, rat glue "
                      "pad, rat cake)",
    r"^MRT ": "MRT RAT KILL, MRT INST VPR",
    # 4.2
    r"SAFE LIFE NORMAL MASK": "SAFE LIFE NORMAL MASK",
    r"SF SURGICAL MASK": "SF SURGICAL MASK",
    r"^BATH|^Bath": "All bath sponges, BATH JALO ROLL, BATH JALO BUTTERFLY, "
                    "Bathstone Big, BATH TATO GLOVES, BATH SPONGE GLOVES, "
                    "Bathroom Sponge Long, Bath Sponj Long",
    # 4.3
    r"^No\. (7|10) Candle$|^Candles Small$|^Candle_Big$":
        "All candles: No. 7 Candle, No. 10 Candle, Candles Small, Candle_Big",
    # 6.5
    r"\bbatter(y|ies)\b|\bbulb\b|Everyday Ultima|EvRe Light"
    r"|Chota Power|^Ultra (AA|AAA|LONG|Longer)":
        'Match on "battery", "bulb", "Ultra AA/AAA/C2/D2", "Everyday Ultima", '
        '"EvRe Light", "Chota Power"',
}


# ----------------------------------------------------------------------
# Matching engine
# ----------------------------------------------------------------------

_WS = re.compile(r"\s+")


def norm(text: str) -> str:
    """Casefold and collapse internal whitespace."""
    return _WS.sub(" ", str(text)).strip().casefold()


def squash(text: str) -> str:
    """Casefold and remove all whitespace. Used only to spot spacing typos."""
    return _WS.sub("", str(text)).strip().casefold()


@dataclass
class Match:
    product: str
    source: str
    destination: str
    ref: str
    pattern: str
    kind: str
    note: str
    revenue: float = 0.0


@dataclass
class MatchResult:
    matches: list[Match] = field(default_factory=list)
    # (rule, near misses in the source category, (name, category) found elsewhere)
    unmatched: list[tuple[Rule, list[str], tuple[str, str] | None]] = field(
        default_factory=list
    )
    empty_families: list[Rule] = field(default_factory=list)


def apply_rules(products: pd.DataFrame, rules: list[Rule]) -> MatchResult:
    """Match every rule against the product table. Nothing is mutated."""
    out = MatchResult()

    by_source: dict[str, pd.DataFrame] = {
        cat: sub for cat, sub in products.groupby("category")
    }
    norm_index: dict[str, dict[str, list[str]]] = {}
    squash_index: dict[str, dict[str, list[str]]] = {}
    for cat, sub in by_source.items():
        n: dict[str, list[str]] = {}
        s: dict[str, list[str]] = {}
        for name in sub["product_name"]:
            n.setdefault(norm(name), []).append(name)
            s.setdefault(squash(name), []).append(name)
        norm_index[cat] = n
        squash_index[cat] = s

    revenue = dict(zip(products["product_name"], products["revenue"]))
    # global index, so a name that exists in the wrong category can be told
    # apart from a name that does not exist at all
    global_norm: dict[str, tuple[str, str]] = {
        norm(r.product_name): (r.product_name, r.category)
        for r in products.itertuples(index=False)
    }

    cat_of = dict(zip(products["product_name"], products["category"]))
    all_norm: dict[str, list[str]] = {}
    all_squash: dict[str, list[str]] = {}
    for name in products["product_name"]:
        all_norm.setdefault(norm(name), []).append(name)
        all_squash.setdefault(squash(name), []).append(name)

    for rule in rules:
        if rule.source == ANY:
            pool, n_idx, s_idx = products, all_norm, all_squash
        else:
            pool = by_source.get(rule.source)
            n_idx = norm_index.get(rule.source, {})
            s_idx = squash_index.get(rule.source, {})
        if pool is None or pool.empty:
            out.unmatched.append((rule, [], global_norm.get(norm(rule.pattern))))
            continue

        if rule.kind == "NAME":
            hits = n_idx.get(norm(rule.pattern), [])
            if not hits:
                # spacing-only near miss, reported but not applied
                near = s_idx.get(squash(rule.pattern), [])
                if not near:
                    near = difflib.get_close_matches(
                        rule.pattern, list(pool["product_name"]), n=3, cutoff=0.72
                    )
                out.unmatched.append(
                    (rule, near, global_norm.get(norm(rule.pattern)))
                )
                continue
        else:
            pat = re.compile(rule.pattern, re.IGNORECASE)
            exc = re.compile(rule.exclude, re.IGNORECASE) if rule.exclude else None
            hits = [
                name for name in pool["product_name"]
                if pat.search(str(name)) and not (exc and exc.search(str(name)))
            ]
            if not hits:
                out.empty_families.append(rule)
                continue

        for name in hits:
            out.matches.append(
                Match(
                    product=name,
                    source=cat_of[name] if rule.source == ANY else rule.source,
                    destination=rule.destination,
                    ref=rule.ref,
                    pattern=rule.pattern,
                    kind=rule.kind,
                    note=rule.note,
                    revenue=float(revenue.get(name, 0.0)),
                )
            )
    return out


def stay_conflicts(matches: list[Match]) -> list[tuple[Match, Stay]]:
    """Products a move rule claims while a STAY family also names them."""
    found = []
    for m in matches:
        for s in STAYS:
            if s.source != m.source:
                continue
            if re.search(s.pattern, m.product, re.IGNORECASE):
                found.append((m, s))
    return found


@dataclass
class Resolution:
    """The outcome of the whole rule table against a product list."""
    result: MatchResult
    moving: dict[str, Match]        # product -> the move that applies
    conflicting: dict[str, list[Match]]
    duplicated: dict[str, list[Match]]
    noop: dict[str, Match]


def resolve(renamed_products: pd.DataFrame) -> Resolution:
    """Run the rule table and decide, per product, what actually happens.

    `renamed_products` must already have RENAMES applied to its category
    column. This is the single decision point: both the dry-run report and
    apply_remap() call it, so the report can never describe a different
    outcome from the one that gets applied.

    A product whose rules disagree on the destination is NOT moved. The spec
    has to be fixed first; silently picking one destination would hide it.
    """
    result = apply_rules(renamed_products, RULES)

    claims: dict[str, list[Match]] = {}
    for m in result.matches:
        claims.setdefault(m.product, []).append(m)

    conflicting = {p: ms for p, ms in claims.items()
                   if len({m.destination for m in ms}) > 1}
    duplicated = {p: ms for p, ms in claims.items()
                  if len(ms) > 1 and p not in conflicting}

    decided = {p: ms[0] for p, ms in claims.items() if p not in conflicting}
    noop = {p: m for p, m in decided.items() if m.destination == m.source}
    moving = {p: m for p, m in decided.items() if m.destination != m.source}

    return Resolution(result, moving, conflicting, duplicated, noop)


def apply_remap(df: pd.DataFrame,
                product_col: str = "product",
                category_col: str = "category",
                verbose: bool = True) -> pd.DataFrame:
    """Return `df` with PART 1 renames and every confirmed move applied.

    Row-level safe: resolution happens once on the distinct product list, then
    the result is mapped back onto the rows, so this costs one groupby and one
    map regardless of how many hundreds of thousands of rows are passed in.

    The frame is copied; the caller's frame is not mutated.
    """
    out = df.copy()
    before_cats = out[category_col].nunique()
    before_prods = out[product_col].nunique()

    # PART 1 renames first, so rules can name post-rename categories
    out[category_col] = out[category_col].replace(RENAMES)

    products = (
        out.groupby([category_col, product_col], as_index=False)
        .size()
        .rename(columns={category_col: "category", product_col: "product_name"})
    )
    products["revenue"] = 0.0

    res = resolve(products)
    mapping = {p: m.destination for p, m in res.moving.items()}

    out[category_col] = (
        out[product_col].map(mapping).fillna(out[category_col])
    )

    if verbose:
        print(f"Category remap applied from analysis/category_remap.py")
        print(f"  renames                : {len(RENAMES)}")
        print(f"  rules in table         : {len(RULES)}")
        print(f"  products moved         : {len(res.moving):,}")
        print(f"  products unchanged     : {before_prods - len(res.moving):,}")
        print(f"  no-op rules (already there): {len(res.noop)}")
        print(f"  conflicts (NOT moved)  : {len(res.conflicting)}")
        print(f"  unmatched spec names   : {len(res.result.unmatched)}")
        print(f"  categories before      : {before_cats}")
        print(f"  categories after       : {out[category_col].nunique()}")
        print(f"  products before/after  : {before_prods:,} / "
              f"{out[product_col].nunique():,}")
        if res.conflicting:
            raise AssertionError(
                f"{len(res.conflicting)} products have conflicting destinations; "
                "resolve the spec before applying."
            )
        if res.result.unmatched:
            names = ", ".join(r.pattern for r, _, _ in res.result.unmatched)
            raise AssertionError(f"unmatched spec names remain: {names}")
    return out


def load_products() -> pd.DataFrame:
    """Read-only product table: one row per product, with revenue."""
    df = pd.read_csv(
        SOURCE,
        usecols=["invoice_no", "product_group", "category", "product",
                 "quantity", REVENUE_COL],
    )
    products = (
        df.groupby(["category", "product"], as_index=False)
        .agg(units_sold=("quantity", "sum"), revenue=(REVENUE_COL, "sum"))
        .rename(columns={"product": "product_name"})
    )
    return products


def load_audit_keywords():
    """Reuse the original audit's keyword logic rather than restate it."""
    spec = importlib.util.spec_from_file_location("_audit", AUDIT_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ----------------------------------------------------------------------
# Dry-run report
# ----------------------------------------------------------------------

def _rule(title: str, char: str = "=") -> None:
    print("\n" + char * 78)
    print(title)
    print(char * 78)


def main() -> None:
    print("DRY RUN. Nothing is modified. No notebook is run.")
    print(f"Spec:   reports/CATEGORY_REMAP_SPEC.md")
    print(f"Source: {SOURCE.relative_to(ROOT)}")

    products = load_products()
    before = products.groupby("category")["product_name"].count()
    total_before = len(products)

    # PART 1 renames applied first, so rules can name post-rename categories.
    renamed = products.copy()
    renamed["category"] = renamed["category"].replace(RENAMES)

    # Same resolver the notebook uses, so this report describes exactly the
    # outcome apply_remap() produces.
    res = resolve(renamed)
    result = res.result
    moving, conflicting = res.moving, res.conflicting
    duplicated, noop = res.duplicated, res.noop

    # ---------------- 1. every product that would move -------------------
    _rule("1. PRODUCTS THAT WOULD MOVE, GROUPED BY DESTINATION")
    by_dest: dict[str, list[Match]] = {}
    for m in moving.values():
        by_dest.setdefault(m.destination, []).append(m)

    for dest in sorted(by_dest, key=lambda d: -sum(m.revenue for m in by_dest[d])):
        rows = sorted(by_dest[dest], key=lambda m: -m.revenue)
        rev = sum(m.revenue for m in rows)
        print(f"\n-> {dest}   {len(rows)} products   Rs {rev:,.2f}")
        print(f"   {'from':<26} {'product':<44} {'revenue':>14}  ref")
        print("   " + "-" * 92)
        for m in rows:
            print(f"   {m.source:<26} {m.product[:44]:<44} "
                  f"{m.revenue:>14,.2f}  {m.ref}")

    # ---------------- 1b. dalmot consolidation audit ----------------------
    _rule("1b. DALMOT AND MOONG DAL CONSOLIDATION, CONFIRM NONE ARE LENTILS", "-")
    dal_moved = sorted(
        [m for m in moving.values() if m.ref == "R2"],
        key=lambda m: (m.source, -m.revenue),
    )
    dal_noop = sorted(
        [m for m in noop.values() if m.ref == "R2"], key=lambda m: m.product
    )
    also = sorted(
        [m for m in moving.values()
         if m.ref != "R2" and re.search(
             r"dalmot|dalmoth|moong dal", m.product, re.IGNORECASE)],
        key=lambda m: (m.ref, m.product),
    )
    print(f"\n  MOVED to SNACKS by the R2 consolidation ({len(dal_moved)}):")
    print(f"    {'product':<32} {'from':<28} {'revenue':>13}")
    print("    " + "-" * 75)
    for m in dal_moved:
        print(f"    {m.product[:32]:<32} {m.source:<28} {m.revenue:>13,.2f}")
    print(f"    {'':32} {'':28} {sum(m.revenue for m in dal_moved):>13,.2f}")

    if also:
        print(f"\n  Already moving to SNACKS under a spec rule, so R2 only "
              f"confirms them ({len(also)}):")
        for m in also:
            print(f"    {m.product[:38]:<38} {m.source:<28} [{m.ref}]")

    if dal_noop:
        print(f"\n  Already in SNACKS, no move needed ({len(dal_noop)}):")
        for m in dal_noop:
            print(f"    {m.product}")

    kept = renamed[
        renamed["product_name"].str.contains(
            r"\bmo?ong\b|\bdal\b|daal", case=False, regex=True, na=False)
        & ~renamed["product_name"].isin(moving.keys())
    ]
    already = kept[kept["category"] == "SNACKS"]
    kept = kept[kept["category"] != "SNACKS"]
    print(f"\n  NOT moved, read as real lentils ({len(kept)}). Check nothing "
          "here is a namkeen:")
    for r in kept.sort_values("product_name").itertuples(index=False):
        print(f"    {r.product_name[:38]:<38} {r.category}")
    if len(already):
        print(f"\n  Also unmoved but already in SNACKS, so correct as they are "
              f"({len(already)}):")
        for r in already.sort_values("product_name").itertuples(index=False):
            print(f"    {r.product_name}")

    # per spec section, against the spec's own estimate
    SPEC_EST = {
        "2.1": "~155", "2.2": "~58", "2.3": "~31", "2.4": "8", "2.5": "9",
        "2.6": "5", "2.7": "2", "2.8": "8", "4.1": "~230", "4.2": "~22",
        "4.3": "~20", "4.4": "7", "5.1": "5", "5.2": "4", "6.1": "14",
        "6.2": "6", "6.3": "2", "6.4": "6", "6.5": "17",
    }
    per_ref: dict[str, int] = {}
    for m in moving.values():
        per_ref[m.ref] = per_ref.get(m.ref, 0) + 1
    print("\n  Per spec section, actual against the spec's own estimate:")
    print(f"    {'ref':<6} {'actual':>7} {'spec est':>9}   note")
    print("    " + "-" * 62)
    for ref in sorted(set(per_ref) | set(SPEC_EST)):
        actual = per_ref.get(ref, 0)
        est = SPEC_EST.get(ref, "-")
        digits = est.lstrip("~")
        note = ""
        if digits.isdigit() and actual != int(digits):
            note = f"{actual - int(digits):+d} vs estimate"
        print(f"    {ref:<6} {actual:>7} {est:>9}   {note}")

    # ---------------- 2. before and after, all 25 -------------------------
    _rule("2. PRODUCT COUNT BEFORE AND AFTER, ALL 25 CATEGORIES")
    after = dict(before)
    # apply renames to the after view
    for old, new in RENAMES.items():
        if old in after:
            after[new] = after.pop(old)
    for m in moving.values():
        after[m.source] = after.get(m.source, 0) - 1
        after[m.destination] = after.get(m.destination, 0) + 1

    display_before = {}
    for cat, n in before.items():
        display_before[RENAMES.get(cat, cat)] = n

    print(f"{'category':<28} {'before':>7} {'after':>7} {'delta':>7}   spec target")
    print("-" * 78)
    spec_target = {
        "PERSONAL CARE": "~1,250", "CANNED AND PACKAGED FOODS": "~715",
        "HOUSEHOLD ITEMS": "~285", "CLEANING SUPPLIES": "~580",
        "CONFECTIONERY": "452", "FOOD STAPLES": "~165", "TEA AND SPICES": "~405",
        "BISCUITS AND COOKIES": "305", "BABY CARE": "~220",
        "SOFT DRINKS AND JUICES": "191", "BREAKFAST CEREALS": "143",
        "SNACKS": "~135", "ALCOHOLIC BEVERAGES": "102", "POOJA ITEMS": "~115",
        "STATIONERY": "~96", "DAIRY PRODUCTS": "~94", "FROZEN FOODS": "94",
        "COOKING OIL": "84", "RICE": "~84", "NOODLES": "~81", "BAKERY": "39",
        "ELECTRICAL SUPPLIES": "~35", "CIGARETTE AND TOBACCO": "17",
        "PARTY SUPPLIES": "16", "FRESH PRODUCE": "13",
    }
    for cat in sorted(after, key=lambda c: -after[c]):
        b = display_before.get(cat, 0)
        a = after[cat]
        d = a - b
        flag = "" if d == 0 else f"{d:+d}"
        print(f"{cat:<28} {b:>7,} {a:>7,} {flag:>7}   {spec_target.get(cat, '-'):>7}")
    print("-" * 78)
    print(f"{'TOTAL':<28} {sum(display_before.values()):>7,} "
          f"{sum(after.values()):>7,}")

    # ---------------- 3. unmatched ----------------------------------------
    _rule("3. UNMATCHED: SPEC NAMES WITH NO PRODUCT IN THE DATA")
    if not result.unmatched:
        print("None. Every exact name in the spec matched a product.")
    else:
        for r, near, elsewhere in result.unmatched:
            print(f"\n  [{r.ref}] {r.source} -> {r.destination}")
            print(f"      spec name : {r.pattern!r}")
            if elsewhere:
                print(f"      WRONG SOURCE: this product exists, but sits in "
                      f"{elsewhere[1]},\n                    not "
                      f"{r.source}. Not a typo. The rule's source is wrong.")
            elif near:
                for cand in near:
                    print(f"      near miss : {cand!r}")
            else:
                print("      near miss : none found in this category")

    if result.empty_families:
        print("\n  Family rules that matched nothing:")
        for r in result.empty_families:
            print(f"    [{r.ref}] {r.source} -> {r.destination}  /{r.pattern}/")

    # ---------------- 3b. shorthand, as a confirm-or-correct table --------
    all_noted = sorted(
        {(m.ref, m.pattern, m.kind) for m in result.matches if m.note},
        key=lambda t: (t[0], t[1]),
    )
    resolved: dict[tuple[str, str], list[str]] = {}
    for m in result.matches:
        if m.note:
            resolved.setdefault((m.ref, m.pattern), []).append(m.product)

    # Spec-derived interpretations only. R-refs are researcher additions from
    # 17 Aug 2026 and are reported separately, so this table stays a record of
    # decisions taken against the spec text.
    noted = [t for t in all_noted if t[0][0].isdigit()]
    added = [t for t in all_noted if not t[0][0].isdigit()]

    exact = [t for t in noted if t[2] == "NAME"]
    family = [t for t in noted if t[2] == "RE"]

    missing = [
        (ref, pat, kind) for ref, pat, kind in noted
        if (kind == "NAME" and pat not in SPEC_WORDING)
        or (kind == "RE" and pat not in SPEC_FAMILY)
    ]

    _rule(f"3b. SHORTHAND AND INTERPRETATION, ALL {len(noted)} ITEMS", "-")
    print("Every place the spec cannot be matched literally and I made a "
          "decision.\nConfirm or correct each. 'current category' is where the "
          "product sits today.")

    print(f"\nTABLE A. Exact names, spec wording differs from the product name "
          f"({len(exact)})")
    print(f"\n  {'#':>3} {'ref':<5} {'you wrote':<34} {'resolved to':<38} "
          f"{'current category':<26} to")
    print("  " + "-" * 132)
    for i, (ref, pat, _) in enumerate(exact, 1):
        wrote = SPEC_WORDING.get(pat, "?? NOT RECORDED")
        hits = resolved.get((ref, pat), [])
        src = next((m.source for m in result.matches
                    if m.ref == ref and m.pattern == pat), "?")
        dst = next((m.destination for m in result.matches
                    if m.ref == ref and m.pattern == pat), "?")
        shown = hits[0] if len(hits) == 1 else f"{hits[0]}  (+{len(hits)-1} more)"
        same = "  [same text, whitespace or case only]" if norm(wrote) == norm(shown) else ""
        print(f"  {i:>3} {ref:<5} {wrote[:34]:<34} {shown[:38]:<38} "
              f"{src:<26} {dst}{same}")

    print(f"\nTABLE B. Family rules, spec said \"all X\" and I chose the pattern "
          f"({len(family)})")
    for i, (ref, pat, _) in enumerate(family, len(exact) + 1):
        wrote = SPEC_FAMILY.get(pat, "?? NOT RECORDED")
        hits = sorted(resolved.get((ref, pat), []))
        src = next((m.source for m in result.matches
                    if m.ref == ref and m.pattern == pat), "?")
        dst = next((m.destination for m in result.matches
                    if m.ref == ref and m.pattern == pat), "?")
        print(f"\n  {i:>3} [{ref}] {src} -> {dst}")
        print(f"      you wrote : {wrote}")
        print(f"      pattern   : /{pat}/")
        print(f"      matched   : {len(hits)} products")
        for h in hits:
            print(f"                  {h}")

    if missing:
        print(f"\n  WARNING: {len(missing)} noted rules are absent from "
              "SPEC_WORDING/SPEC_FAMILY:")
        for ref, pat, kind in missing:
            print(f"    [{ref}] {kind} /{pat}/")
    else:
        print(f"\n  Coverage check: all {len(noted)} spec-derived noted rules "
              "have their spec wording recorded.")

    print(f"\nTABLE C. Researcher additions, 17 Aug 2026, NOT in the spec file "
          f"({len(added)})")
    print(f"\n  {'ref':<5} {'rule':<40} {'matched':>8}   current -> to")
    print("  " + "-" * 92)
    for ref, pat, kind in added:
        hits = sorted(resolved.get((ref, pat), []))
        dst = next((m.destination for m in result.matches
                    if m.ref == ref and m.pattern == pat), "?")
        srcs = sorted({m.source for m in result.matches
                       if m.ref == ref and m.pattern == pat})
        label = pat if kind == "NAME" else f"/{pat}/"
        print(f"  {ref:<5} {label[:40]:<40} {len(hits):>8}   "
              f"{', '.join(srcs)} -> {dst}")

    # ---------------- 4. ambiguous ----------------------------------------
    _rule("4. AMBIGUOUS: PRODUCTS MATCHING MORE THAN ONE RULE")
    if conflicting:
        print(f"\n  CONFLICTING destinations ({len(conflicting)}). "
              "NOT MOVED pending your decision:")
        for p, ms in sorted(conflicting.items()):
            print(f"\n    {p}   (currently {ms[0].source})")
            for m in ms:
                print(f"      -> {m.destination:<28} [{m.ref}] /{m.pattern}/")
    else:
        print("\n  No product is sent to two different destinations.")

    if duplicated:
        print(f"\n  Same destination, matched more than once ({len(duplicated)}). "
              "Harmless overlap:")
        for p, ms in sorted(duplicated.items())[:40]:
            refs = ", ".join(sorted({f"{m.ref}:/{m.pattern}/" for m in ms}))
            print(f"    {p:<46} -> {ms[0].destination:<26} {refs}")
        if len(duplicated) > 40:
            print(f"    ... and {len(duplicated) - 40} more")

    conflicts = stay_conflicts(list(moving.values()))
    if conflicts:
        print(f"\n  Contradicts a STAYS list ({len(conflicts)}). A move rule "
              "claims these, but a\n  'stays' paragraph also names them:")
        for m, s in conflicts:
            print(f"    {m.product:<46} -> {m.destination:<24} "
                  f"[move {m.ref}] vs [{s.ref}]")

    if noop:
        print(f"\n  No-op rules, destination equals current category ({len(noop)}):")
        for p, m in sorted(noop.items()):
            print(f"    {p:<46} already in {m.destination}  [{m.ref}]")

    # ---------------- 5. unclaimed ----------------------------------------
    _rule("5. UNCLAIMED: STILL IN FOOD STAPLES OR HOUSEHOLD ITEMS AFTER THE MOVES")
    audit = load_audit_keywords()
    stayers = renamed[~renamed["product_name"].isin(moving.keys())]
    stayers = stayers[stayers["category"].isin([FS, HH])]
    n_fs = int((stayers["category"] == FS).sum())
    n_hh = int((stayers["category"] == HH).sum())
    print(f"\n  {len(stayers):,} products were already there and stay "
          f"({n_fs} in {FS}, {n_hh} in {HH}).")
    print(f"  Part 2's after counts are higher ({after[FS]} and {after[HH]}) "
          "because they also include\n  products moving IN from other "
          "categories, which are deliberate placements.")
    print("\n  5a. Audit keyword logic: KEYWORD_RULES, QUALIFIERS and build_flags")
    print("      from scripts/export_category_audit.py, imported unchanged.")

    flags = audit.build_flags(
        stayers.rename(columns={"category": "category"})[
            ["product_name", "category"]
        ]
    )
    if flags.empty:
        print("\n  No remaining product trips an audit keyword.")
    else:
        print(f"\n  {len(flags)} flags across "
              f"{flags['product_name'].nunique()} products:\n")
        print(f"  {'product':<46} {'now in':<18} {'suggests':<24} keyword")
        print("  " + "-" * 96)
        for r in flags.itertuples(index=False):
            print(f"  {r.product_name[:46]:<46} {r.current_category:<18} "
                  f"{r.suggested_category:<24} {r.matched_keyword}")

    # 5b. The audit's keyword list was written against the ORIGINAL categories.
    # It has no term for most of what this remap leaves behind: no "brush", no
    # "freshener", no "polish", no "nut", no "cleaner". That is why 5a is thin,
    # and it is a limitation of the audit vocabulary, not evidence the remap is
    # complete. EXTRA_KEYWORDS below extends it to the concepts this remap
    # introduced. These are my additions, not the audit's, and are listed in
    # full so each can be judged. Same whole-word matching as the audit.
    EXTRA_KEYWORDS: dict[str, list[tuple[str, str]]] = {
        HH: [
            (r"brush", CLEAN), (r"cleaner", CLEAN), (r"freshn?ere?|freshener", CLEAN),
            (r"polish", CLEAN), (r"\brat\b", CLEAN), (r"mosquito", CLEAN),
            (r"kapur|kapoor", CLEAN), (r"duster", CLEAN), (r"broom", CLEAN),
            (r"\bwipes?\b", CLEAN), (r"scrubber", CLEAN),
            (r"\bmask\b", "PERSONAL CARE"), (r"sanitizer", "PERSONAL CARE"),
        ],
        FS: [
            (r"makhana", "SNACKS"), (r"\bkaju\b", "SNACKS"),
            (r"\bbadam\b", "SNACKS"), (r"\bokhar\b", "SNACKS"),
            (r"mishri", "SNACKS"), (r"kismiss", "SNACKS"),
            (r"peanut", "SNACKS"), (r"titaura", "SNACKS"),
            (r"dalmot", "SNACKS"), (r"papad", "SNACKS"),
            (r"panipuri", "SNACKS"), (r"chokda", "SNACKS"),
            (r"\btill\b", SPICE), (r"chukamilo", SPICE), (r"herbs", SPICE),
        ],
    }
    print("\n  5b. The audit vocabulary predates this remap and has no term for "
          "brushes, cleaners,\n      fresheners, polish or nuts, which is why 5a "
          "is thin. These extra keywords are\n      mine, not the audit's, and "
          "are listed so you can judge them:")
    for cat, pairs in EXTRA_KEYWORDS.items():
        for pat, dest in pairs:
            print(f"        {cat:<16} /{pat}/ -> {dest}")

    extra_hits = []
    for r in stayers.itertuples(index=False):
        for pat, dest in EXTRA_KEYWORDS.get(r.category, []):
            if re.search(pat, str(r.product_name), re.IGNORECASE):
                extra_hits.append((r.category, r.product_name, pat, dest,
                                   float(r.revenue)))
                break

    print(f"\n      {len(extra_hits)} products left behind that these keywords "
          "flag:")
    if extra_hits:
        print(f"\n  {'product (would stay)':<42} {'now in':<17} "
              f"{'suggests':<24} keyword")
        print("  " + "-" * 100)
        for cat, name, pat, dest, _ in sorted(
            extra_hits, key=lambda s: (s[0], -s[4])
        ):
            print(f"  {name[:42]:<42} {cat:<17} {dest:<24} /{pat}/")

    # ---------------- 6. totals -------------------------------------------
    _rule("6. TOTALS")
    n_move = len(moving)
    n_stay = total_before - n_move
    print(f"  products moving        {n_move:>6,}")
    print(f"  products staying       {n_stay:>6,}")
    print(f"  held back (conflicts)  {len(conflicting):>6,}")
    print(f"  total products         {total_before:>6,}   "
          f"{'OK, 5,680' if total_before == 5680 else 'MISMATCH, expected 5,680'}")
    print(f"  categories before      {len(display_before):>6,}")
    print(f"  categories after       {len(after):>6,}   "
          f"{'OK, 25' if len(after) == 25 else 'MISMATCH, expected 25'}")
    empty_after = [c for c, n in after.items() if n == 0]
    print(f"  categories left empty  {len(empty_after):>6,}"
          + (f"   {empty_after}" if empty_after else ""))
    print(f"  smallest category      {min(after.values()):>6,}   "
          f"({min(after, key=after.get)})")
    print(f"\n  revenue moving         Rs {sum(m.revenue for m in moving.values()):,.2f}")
    print(f"  revenue total          Rs {products['revenue'].sum():,.2f}   "
          "unchanged by definition, categories do not affect revenue")

    print("\nDRY RUN complete. No file was written. No notebook was run.")


if __name__ == "__main__":
    main()
