"""
keyword_wordcloud.py

Makes the keyword word cloud image for the dissertation.

Install first, once:
    pip install wordcloud matplotlib

Then run:
    python keyword_wordcloud.py

It writes keyword_wordcloud.png next to this script.
Insert that PNG into the document under the abstract.

To change the words, edit the KEYWORDS dictionary below.
The number next to each phrase is its size. Bigger number, bigger text.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from wordcloud import WordCloud

# --------------------------------------------------------------------------
# The words, and how big each one should be.
#
# 10 = biggest, the core of the study
#  8 = major themes
#  6 = supporting methods
#  4 = smaller details
#
# Multi-word phrases stay together because of generate_from_frequencies
# further down. Do not switch to the generate() method, because that
# splits every phrase into single words.
# --------------------------------------------------------------------------

KEYWORDS = {
    # The core
    "Market basket analysis": 10,
    "Association rule mining": 10,
    "Product placement optimisation": 9,

    # Major themes
    "Shelf space allocation": 8,
    "Independent grocery retail": 8,
    "Cross-sell capture": 8,
    "Choice architecture": 7,
    "Nepali grocery retail": 7,

    # Methods
    "Apriori algorithm": 6,
    "FP-Growth": 6,
    "Co-occurrence clustering": 6,
    "Statistical validation": 6,
    "Transaction-level POS data": 6,
    "Bonferroni correction": 5,

    # Supporting
    "Silhouette coefficient": 5,
    "Basket segmentation": 5,
    "Behavioural economics": 5,
    "Retail analytics": 5,
    "Planogram design": 4,
    "Measured versus projected": 4,
    "Reproducible research": 4,
    "Consumer autonomy": 4,
}

# --------------------------------------------------------------------------
# Look and feel. These match the proposal word cloud.
# --------------------------------------------------------------------------

WIDTH = 1600           # pixels
HEIGHT = 900           # pixels, 16 by 9 landscape
BACKGROUND = "white"
COLOURMAP = "viridis"  # try "cividis", "plasma" or "mako" for other looks
OUTPUT = "keyword_wordcloud.png"
DPI = 200


def main():
    cloud = WordCloud(
        width=WIDTH,
        height=HEIGHT,
        background_color=BACKGROUND,
        colormap=COLOURMAP,
        prefer_horizontal=1.0,   # keeps every phrase horizontal and readable
        collocations=False,      # stops the library inventing its own phrases
        margin=12,
        max_font_size=110,
        min_font_size=14,
        relative_scaling=0.6,    # how strongly the weights affect size
        random_state=7,         # same layout every run, so reruns match
    )

    cloud.generate_from_frequencies(KEYWORDS)

    fig, ax = plt.subplots(figsize=(WIDTH / DPI, HEIGHT / DPI), dpi=DPI)
    ax.imshow(cloud, interpolation="bilinear")
    ax.axis("off")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    out = Path(__file__).parent / OUTPUT
    fig.savefig(out, dpi=DPI, bbox_inches="tight", pad_inches=0.1,
                facecolor=BACKGROUND)
    plt.close(fig)

    print(f"Saved: {out}")
    print(f"Size:  {WIDTH} by {HEIGHT} pixels")
    print(f"Words: {len(KEYWORDS)}")
    print()
    print("Insert this PNG into the document under the abstract.")
    print("If the layout looks cramped, change random_state to another")
    print("number and run it again until you like the arrangement.")


if __name__ == "__main__":
    main()