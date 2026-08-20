# Answers

**Written:** 2026-08-14
**Purpose:** answers to the eleven questions raised on the draft, every one checked against the
repository today rather than from memory, plus a full account of what exists and works right now.

**How to read this.** Each answer states the verdict first, then the evidence, then what has to
change in the dissertation. Where I could not verify something I say so rather than guessing.

**Verification run today, all four commands, all passing:**

```
git rev-list --count HEAD          -> 836
docker ps                          -> pp_postgres, pp_airflow_apiserver,
                                      pp_airflow_scheduler, pp_airflow_dag_processor
                                      all Up 16 hours (healthy)
venv/Scripts/python etl/quality_checks.py       -> ALL 32 QUALITY CHECKS PASSED
venv/Scripts/python reproduce_all_results.py    -> 13 checks, 9 steps, ALL PASSED
                                                   60 of 60 checkable figures match
```

---

# Part 1: The eleven questions

## Q1. How many notebooks? Eleven or twelve?

**Twelve.** Verified on disk.

```
notebooks/01_data_audit.ipynb            notebooks/07_placement_simulation.ipynb
notebooks/02_data_cleaning.ipynb         notebooks/08_evaluation.ipynb
notebooks/03_eda.ipynb                   notebooks/09_ml_recommendation.ipynb
notebooks/04_transaction_encoding.ipynb  notebooks/10_demand_forecasting.ipynb
notebooks/05_market_basket_analysis.ipynb notebooks/11_basket_classifier.ipynb
notebooks/06_clustering.ipynb            notebooks/12_neural_network.ipynb
```

**The current document already says twelve, in both places it matters.** Section 01 says "twelve
sequential notebooks running from raw data audit through ... neural network comparison". Section
21.1 says "The analysis was organised as twelve sequential notebooks". Neither says eleven.

**Where the confusion comes from.** The word "eleven" does appear in the document, but it refers to
**eleven months of data**, not to notebooks. Research Objective 1 reads "To acquire, audit and clean
**eleven months** of real Point of Sale data". If the reviewer's copy is being read quickly, that
line is easy to misread as a notebook count.

**Action:** none in the document, it is already correct. But confirm the reviewer is reading
`SAMIKSHYABANIYAFIANLDOC.docx` and not one of the older files in the folder. See Q11.

---

## Q2. How many commits? Over three hundred, or 818?

**836, as of today.** Neither figure in the question is current.

```
git rev-list --count HEAD   ->  836
first commit: 2026-05-28  "Initial project setup and data audit"
last commit:  2026-08-14  "merge branch 20-remove-em-dash"
```

818 was correct on 2026-08-13 when `PROJECT_RECORD.md` was written. Eighteen commits have landed
since. "Over three hundred" does not appear in any current draft and is badly out of date.

**The current document says "over 800 commits"**, which is true and stays true. That phrasing is
deliberately robust: a number that keeps growing should not be quoted exactly in a document that
gets read weeks later.

**Action:** none. Keep "over 800". Do not change it to 836, because it will be wrong again by
submission.

---

## Q3. Do the Postgres database, star schema, Airflow and Docker still exist and still run?

**Yes. All of it. Verified running right now, not just present on disk.**

```
NAMES                       STATUS                  PORTS
pp_postgres                 Up 16 hours (healthy)   0.0.0.0:5435->5432/tcp
pp_airflow_apiserver        Up 16 hours (healthy)   0.0.0.0:8082->8080/tcp
pp_airflow_scheduler        Up 16 hours (healthy)
pp_airflow_dag_processor    Up 16 hours
pp_airflow_metadata         Up 16 hours (healthy)
pp_airflow_init             Exited (0) 16 hours ago   [expected, it is a one-shot init container]
```

The DAG file is `dags/product_placement_pipeline.py`. The warehouse loader is
`etl/load_warehouse.py`. The schema definitions are in `sql/`. The Docker definition is
`docker-compose.yml` in the project root.

**Stronger than "it exists": the warehouse still holds the right data.** I ran the 32 quality checks
against the live database today and every one passed, including the accuracy group that compares the
warehouse against the thesis figures:

```
[PASS] Total revenue is Rs 218,214,456.88          218214456.88
[PASS] Average basket value is Rs 1,000.81         1000.81
[PASS] Median basket value is Rs 500.00            500.00
[PASS] Small baskets number 108,349                108,349
[PASS] Medium baskets number 79,868                79,868
[PASS] Large baskets number 29,820                 29,820
[PASS] Large baskets carry 52.1% of revenue        52.1
[PASS] FOOD STAPLES is the top category            FOOD STAPLES
[PASS] Friday is the highest revenue day           Friday
[PASS] September 2025 is the peak month (Dashain)  2025-09
[PASS] Zone 1 carries the largest revenue share    Zone 1 - Center
```

**The paragraph is not a fabrication and section 08's fourth contribution stands.** The specific
claims in section 21.2 that I checked and confirmed:

| Claim in section 21.2 | Verified |
|---|---|
| Normalised schema of three tables | Yes: `oltp.products`, `oltp.transactions`, `oltp.transaction_items` |
| Star schema, four dimensions plus one fact | Yes: `dim_date`, `dim_category`, `dim_product`, `dim_basket`, `fact_sales` |
| Fact table of 767,180 rows | Yes, checked live |
| Seven serving views | Yes, `v_category_performance`, `v_day_of_week`, `v_monthly_revenue`, `v_zone_performance` and three others |
| Placement zone stored on the category dimension | Yes, `dim_category.zone_assignment`, and a check enforces all 5 zones present |
| Five sequential pipeline tasks | Yes, in the DAG |
| Thirty-two quality checks | Yes, see Q4 |

**One caveat worth knowing.** The DAG is unpaused on an `@daily` schedule, so it self-triggers
shortly after `docker compose up -d`. If you see the warehouse repopulate on its own, that is
expected behaviour and not a fault.

**Action:** none. If anything the paragraph undersells it, because it does not mention that the
checks are currently green.

---

## Q4. Are the 32 quality checks and the 13-check reproduction routine still current, and do the counts hold?

**Both counts are exactly right, and both suites pass today.**

**The 32 checks.** Counted directly from the `CHECKS` list in `etl/quality_checks.py`:

| Group | Count | What it catches |
|---|---|---|
| COMPLETENESS | 8 | Did every row arrive, in both the OLTP layer and the warehouse |
| INTEGRITY | 9 | Orphan keys, duplicate invoice numbers, duplicate basket and line pairs, negative amounts and quantities, missing zone assignments, all five zones present |
| CONSISTENCY | 4 | Does the warehouse still reconcile to the OLTP source on row count and on revenue to the paisa |
| ACCURACY | 11 | Do the headline thesis figures still hold |
| **Total** | **32** | |

Live output: `ALL 32 QUALITY CHECKS PASSED.`

**The reproduction routine.** `reproduce_all_results.py` ran today with 13 `[PASS]` lines across 9
steps, and finished with `ALL CHECKS PASSED. Every verified number reproduces from the pipeline.`
Step 9 reported `VERIFIED: 60 of 60 checkable figures match` and
`NOT AUTO-CHECKABLE: 6 figures need a notebook re-run`. A log was written to
`reports/reproduction_log_20260814_155317.txt`.

**One stale number found, and it is in the project record, not the dissertation.**
`PROJECT_RECORD.md` open item 1 says "The script now runs 12 checks and exits 0." It runs **13**.
The record was written when the script had 12 and a thirteenth was added afterwards. **The
dissertation's "thirteen checks across nine stages" is the correct figure.** Section 21.4 is right
and the project record is behind.

**Action:** none in the dissertation. Optionally correct `PROJECT_RECORD.md` item 1 from 12 to 13.

---

## Q5. Was Bonferroni correction run on the chi-square tests?

**Yes, it was run. This is the answer that changes your text, and it changes it in your favour.**

It is in `notebooks/05_market_basket_analysis.ipynb`:

```python
bonferroni_alpha = 0.05 / len(rules)          # 0.05 / 1228 = 4.07e-05
bonferroni_significant = rules[rules['p_value'] < bonferroni_alpha]
```

Markdown cell above it: *"Because 1,228 rules are tested at the same time, the count that survives
the much stricter Bonferroni-corrected threshold (0.05 divided by 1,228) is also reported. This
guards against false positives from multiple testing."*

Recorded output: **`Still significant after Bonferroni correction (p < 4.07e-05): 1,222 of 1,228`**

**So there are two numbers, and both are real:**

| Test | Rules surviving | Threshold |
|---|---|---|
| Chi-square, conventional | 1,226 of 1,228 | p < 0.05 |
| Chi-square, Bonferroni corrected | **1,222 of 1,228** | p < 4.07e-05 |

**What the dissertation currently says.** Section 15 treats multiple comparisons as an unaddressed
limitation: *"the multiple comparisons problem means that with 1,228 rules tested at conventional
significance levels a small number of false positives should be expected."* Section 12.4 reports
only *"Of the 1,228 rules, 1,226 were significant."* Neither mentions that the correction was
actually applied.

**So sections 12 and 15 do not need rewriting because they are wrong. They need rewriting because
they understate what you did.** As written, you raise a methodological objection against your own
work and leave it standing, when the notebook already answers it.

**On the claim that the project record lists it as future work:** I searched the whole repository
and `PROJECT_RECORD.md` does not mention Bonferroni anywhere, in future work or otherwise. The only
mentions of multiple comparisons in prose are in the two draft documents, where they appear as the
unresolved limitation described above. So the record does not contradict the notebook; it is simply
silent, and the notebook is the authority.

**Action, and this is the highest value edit in this whole list:**

- Section 12.4, after the chi-square sentence, add the corrected figure: 1,222 of 1,228 survive a
  Bonferroni-corrected threshold of 0.05 divided by 1,228, which is 4.07e-05.
- Section 15, change the paragraph from "a small number of false positives should be expected" to
  the statement that the multiple comparisons problem was addressed by applying the Bonferroni
  correction, and that 1,222 rules survive it.
- Section 23.2 and the abstract, consider quoting both numbers. "1,226 significant, 1,222 surviving
  Bonferroni correction" is a stronger sentence than either number alone.
- Add a hypothesis-level note to H1: the null is rejected under both the conventional and the
  corrected threshold.

---

## Q6. Where does the one per cent chance baseline for the recommender come from?

**It comes from `notebooks/09_ml_recommendation.ipynb`, and it is a stated analytic baseline, not a
simulation.** Two places in that notebook:

- *"Random guessing across 100 products would give roughly 1% accuracy. The model gives 28%, which
  is about 28 times better than chance, on baskets it never saw during training."*
- *"Random chance baseline: 1% (1 in 100 products)"*

**The reasoning is: the recommender chooses from a candidate set of the 100 most frequently
purchased products, so a uniform random pick has a 1 in 100 chance of being right.** That is
arithmetic, not an experiment. There is no simulated random-guessing run in the notebook.

**I would put it back, but with one qualifier, because there is a real weakness in it.** A uniform
random draw is the weakest possible baseline. Products are not uniformly distributed: the top
products are far more likely to appear in any basket, so a random guesser weighted by product
popularity would beat 1 per cent, possibly by a wide margin. Against that stronger baseline, "28
times chance" would shrink.

**Recommended wording**, which keeps the claim and removes the exposure:

> Uniform random selection from the 100 product candidate set would yield approximately one per
> cent, so the recommender performs approximately twenty-eight times better than uniform chance. A
> popularity weighted random baseline would be higher, and this comparison should be read as against
> uniform selection rather than against the strongest available naive baseline.

**Optional but cheap improvement:** compute the popularity-weighted baseline in notebook 09. It is a
few lines, it makes the claim unimpeachable, and if it comes out at say 3 per cent then "roughly
nine times a popularity weighted baseline" is still a strong result and is a far better sentence to
defend in a viva.

---

## Q7. Are the four measurement errors still four?

**Still four distinct errors. No new ones have been found. But one of the four corrected three
numbers rather than one, and you should know that before you are asked.**

The four, as recorded in `PROJECT_RECORD.md` open items 5 and 6:

| # | Error | Before | After |
|---|---|---|---|
| 1 | Product co-occurrence counted line items, not baskets (notebook 09, cell 31, `.size()` then `pivot.T.dot(pivot)`) | 4,236 | **3,989** |
| 2 | FOOD STAPLES share, line items reported under an axis labelled transactions (notebook 03, chart 2) | 23.34% | **42.19%** |
| 3 | Silhouette gain expressed as a ratio on a bounded scale | "189% improvement" | **+0.364 absolute** |
| 4 | Recommender hit rate quoted against the full test set | 40,959 baskets | **19,808 multi-product baskets** |

**The detail your paragraph does not currently carry.** Error 1 corrected two further product pairs
at the same time, because they came from the same faulty pivot:

- Sugar with Rato Dal: 3,771 corrected to **3,639**
- Wai Wai Chicken with RARA: 1,662 corrected to **1,653**

Also worth knowing: `precompute_artifacts.py` had always computed these correctly. Only the notebook
was wrong, which is why the dashboard never showed the bad figures.

**Whether this changes your paragraph.** Your section 22 claim is that four errors were found and
that every one of them made a result look better than the data supported. Both halves still hold.
All three of the extra pair corrections also moved downward, which strengthens rather than weakens
the point. You can either leave the paragraph at four errors, or add one clause noting that the
first error also corrected two further pair counts in the same direction. I would add the clause.
It costs you eleven words and it removes any chance of an examiner finding it and asking why it was
left out.

**One thing that is not an error but will look like one if you are not ready for it.** There is a
fifth open item, and it is unresolved rather than wrong. See Q11 and the daily denominator.

---

## Q8. Is the restricted products exclusion implemented in code, or is it a stated policy?

**It is a stated policy. There is no code that implements it. The section wording should change.**

I searched every `.py` file in the repository for exclusion logic, filters, restricted lists or any
guard on confectionery, checkout adjacency or shelf height. There is none. The only places those
category names appear are in the zone assignment dictionaries, where CONFECTIONERY is simply listed
as a member of Zone 2 and ALCOHOLIC BEVERAGES and CIGARETTE AND TOBACCO as members of Zone 5.

**The more precise and more honest statement is this.** The three excluded tactics are not filtered
out of the model. They are outside what the model can express at all. The system assigns categories
to zones. It has no concept of shelf height, no concept of checkout adjacency, and no concept of
within-zone position. "No recommendation places confectionery at child height adjacent to the
checkout" is therefore true, but true because the representation has no height dimension, not
because a rule was applied that suppressed it.

That distinction matters, and stating it is stronger than leaving it ambiguous, because an examiner
who asks "show me where in the code" gets a straight answer instead of a search.

**In fairness to what you wrote:** section 13.5 says the exclusions "are documented", which is
accurate. And section 22, where you list the ethical commitments that were implemented rather than
asserted, does **not** claim the exclusions among them. It lists three things, and I verified all
three are genuinely in the code:

| Section 22 claim | Verified |
|---|---|
| Projections labelled as projections in the source and the dashboard | Yes. `dashboard/app.py` lines 949, 1209, 1211, 1308: "PROJECTION, not a measured result", a Basis field reading "Projection" with help text "not a measured result", and a caption stating the rupee uplift is a projection based on a 3 to 8 per cent benchmark |
| The dashboard states which data source it is reading | Yes, warehouse versus committed artifacts, displayed |
| Quality checks verify the headline figures | Yes, the 11 ACCURACY checks |

So section 22 is accurate as written. The risk is only that a reader carries the "implemented rather
than asserted" framing from section 22 backwards into section 13.5 and assumes the exclusions were
coded too.

**Suggested replacement for the final sentence of section 13.5:**

> These exclusions are recorded as a design boundary rather than as an implemented constraint. The
> placement model operates at the level of category to zone assignment and represents neither shelf
> height nor checkout adjacency, so these tactics lie outside what the system can express rather
> than being filtered from what it proposes. The boundary is stated here because a documented limit
> is more informative than an unstated one.

---

## Q9. Is the store anonymous or named in the current document?

**This is the most serious finding in this list, and it needs fixing before anything is submitted.**

**In the document text: anonymous.** I searched the extracted text of
`SAMIKSHYABANIYAFIANLDOC.docx` and the store name does not appear. It is referred to throughout as
the case study store.

**In the repository and in your figures: named.** "BANIYA SHOPPING CENTER" appears in three
notebooks:

| File | Where | What it is |
|---|---|---|
| `notebooks/01_data_audit.ipynb` line 362 | Cell output | The raw POS export header, printed during the audit |
| `notebooks/07_placement_simulation.ipynb` line 375 | **Source code** | `ax.text(7, 9.7, 'BANIYA SHOPPING CENTER - RECOMMENDED LAYOUT', ...)` |
| `notebooks/09_ml_recommendation.ipynb` lines 573, 613 | Source and output | `print("PRODUCT RECOMMENDATIONS - BANIYA SHOPPING CENTER")` |

**And it is baked into the chart.** I opened `reports/figures/chart12_store_planogram.png`. Its
title, in large bold black text across the top of the image, reads:

> **BANIYA SHOPPING CENTER - RECOMMENDED LAYOUT**

That is the planogram. It is the single most important figure in the study, the one that would go
into section 01 as Figure 1.3 and into section 23.4 as the recommended layout.

**Section 13.3 currently states:** *"Identifying references to the store were removed from the
repository, and the business is referred to throughout as the case study store."*

**As of today that sentence is false.** The references were removed from the prose. They were not
removed from the notebooks, and they were not removed from the rendered figure.

This is not a small formatting issue. It is an ethics claim in a dissertation whose second research
question is about responsible practice, and it is contradicted by the project's own headline figure.
If an examiner opens the repository or looks closely at the planogram, the claim fails on inspection.

**Action, in order:**

1. Edit `notebooks/07_placement_simulation.ipynb` line 375 to a neutral title, for example
   "RECOMMENDED STORE LAYOUT" or "CASE STUDY STORE - RECOMMENDED LAYOUT", and re-run the cell to
   regenerate `chart12_store_planogram.png`.
2. Edit `notebooks/09_ml_recommendation.ipynb` lines 573 and 613 the same way, and clear the stored
   cell outputs so the old name is not left in the saved notebook JSON.
3. Notebook 01 is harder, because the name is in the raw POS export header and appears in a saved
   audit output. Either clear that cell's output, or redact the line before saving. Do not modify
   anything under `data/raw/`.
4. Re-run the repository-wide search afterwards to confirm zero hits:
   `grep -ril "baniya shopping" --include=*.py --include=*.ipynb --include=*.md .`
5. Only then is section 13.3 true as written.

**Note there is a second-order issue.** Your own name is Baniya and the store is family operated, so
the store name is also close to a personal identifier. Anonymising the store is doing double duty
here. Worth keeping in mind if you are asked why it matters.

---

## Q10. Is the section 23 draft old, and have any of its numbers changed?

**The numbers have not changed. Not one of them.**

`reproduce_all_results.py` ran today and reported `VERIFIED: 60 of 60 checkable figures match`,
regenerating the derived data files and comparing against the warehouse, the artifacts and
`config/metrics.py`. Every headline figure in section 23 traces back through that sweep. The 32
warehouse checks confirm the same figures from the database side independently.

The specific section 23 results, all confirmed today:

| Section 23 figure | Value | Status |
|---|---|---|
| Total revenue | Rs 218,214,456.88 | unchanged |
| Mean and median basket | Rs 1,000.81 and Rs 500.00 | unchanged |
| Three segments | 108,349 / 79,868 / 29,820 | unchanged |
| Large basket revenue share | 52.07% | unchanged |
| ABC class A | 342 products, 6.0% of assortment | unchanged |
| FOOD STAPLES penetration | 42.19%, 91,988 baskets | unchanged |
| Rules mined | 1,228 from 243 itemsets | unchanged |
| Rules significant | 1,226 | unchanged, plus 1,222 under Bonferroni, see Q5 |
| Max category lift | 6.81 | unchanged |
| Max product lift | 22.41 | unchanged |
| Strongest pair | Kalo Dal with Rato Dal, 3,989 baskets | unchanged, this is the corrected value |
| Silhouette | 0.190 to 0.554, increase 0.364 | unchanged |
| Cross-sell capture | 28 to 56 rules, 8.2% to 16.3% | unchanged |
| Recommender hit rate | 28.0% on 19,808 baskets | unchanged |
| Decision tree | 61.3% against 49.7% baseline | unchanged |
| MLP | 69.05%, ceiling 71.67% | unchanged |
| Gap decomposition | 6.55 points capacity, 1.20 points model family | unchanged |

**So section 23 is not stale on its numbers.** The only change it needs is the Bonferroni addition
from Q5, which adds a figure rather than correcting one.

**What I cannot tell you** is whether the section 23 text the reviewer is holding matches the text
in `SAMIKSHYABANIYAFIANLDOC.docx`. There are four documents in the project root and only one of them
is live. See Q11.

---

## Q11. Anything else that changed that the reviewer does not know about?

Six things.

### 11.1 There are four dissertation files in the folder and only one is current

This is almost certainly the source of the eleven-notebooks and three-hundred-commits confusion.

| File | Modified | Status |
|---|---|---|
| `SAMIKSHYABANIYAFIANLDOC.docx` | 2026-08-14 | **This is the live one. Use only this.** |
| `SAMIKSHYABANIYAFIANLDOC.md` | 2026-08-13 | Superseded markdown draft |
| `SAMIKSHYABANIYAFIANLDOC.pdf` | 2026-08-13 | Export of an older state |
| `Samikshya_Baniya_thesis.md` | 2026-08-13 | Older, shorter draft |

Confirm which file the reviewer has before answering any more version questions. Consider deleting
or archiving the other three so the ambiguity cannot recur.

### 11.2 The document contains no figures at all

The `.docx` has no embedded images whatsoever, while 28 rendered charts sit unused in
`reports/figures/`. Section 01 promises three figures by name and delivers a placeholder. This is
covered in full in `PROMPT_HANDOFF.md` and in the figure plan.

### 11.3 The daily average denominator is an open decision, not a settled number

`DATA_DAYS = 307` is the arithmetic gap between the first and last trading date. The inclusive span
is 308 days and only 304 days recorded sales. The choice moves two published figures:

| Denominator | Meaning | Daily revenue | Daily customers |
|---|---|---|---|
| 304 | days the store actually traded | Rs 717,810.71 | 717 |
| **307, current** | gap between first and last date | **Rs 710,796.28** | **710** |
| 308 | inclusive calendar span | Rs 708,488.50 | 708 |

This feeds the revenue projection, so it is not cosmetic. It was deliberately left as a decision
rather than silently changed. The document already carries a note recommending disclosure in section
25.3 if it is unresolved at submission. Disclosing it is stronger than letting an examiner find it.

### 11.4 The uplift benchmark citation still does not exist

Section 16 carries your own note that the two to eight per cent uplift range must be attributed to a
specific published source, and calls it the single most load-bearing citation in the document
because the Rs 1.30 crore headline depends on it. That citation has not been added. Until it is, the
projection cannot be defended and `chart13_revenue_impact.png` cannot be finalised.

There is also a mismatch worth reconciling: section 16 quotes a two to eight per cent range while
section 23.4 runs scenarios at three, five and eight. Three sits inside the range so it is not a
contradiction, but an examiner may ask why the conservative scenario is not the stated floor.

### 11.5 `PROJECT_LOG.md` is machine generated and contradicts git

Measured: all 500 entries are spaced exactly 7.106 hours apart, standard deviation 0.0001. The same
57 commit messages repeat roughly nine times to pad the file to 500 lines. Its date range of
2026-03-06 to 2026-08-01 does not match git, which runs 2026-05-28 to 2026-08-14, so the log claims
work began about twelve weeks before the first commit exists. It records 500 entries against 836
real commits.

Anyone who opens that file and runs `git log` sees the mismatch immediately, and it casts doubt on
836 genuine commits that deserve none. This is the highest integrity risk in the repository and it
is your decision how to handle it. It can be regenerated from real history with
`git log --format='- %ad: %s' --date=format:'%Y-%m-%d %H:%M:%S' --reverse`, or deleted, since
`PROJECT_RECORD.md` supersedes it. I have not touched it.

### 11.6 Small drift in the project record

`PROJECT_RECORD.md` says the reproduction script runs 12 checks. It runs 13. It also records 818
commits, which was true when written and is now 836. The dissertation is correct on both counts.
This is normal drift in a document that is not itself tested, and it is exactly the failure mode
section 21.4 describes.

---

# Part 2: Everything that exists, in full

Verified present and working on 2026-08-14.

## 2.1 The twelve notebooks

| # | Notebook | What it does | Key output |
|---|---|---|---|
| 01 | `01_data_audit.ipynb` | Audits the raw export without modifying it. Found the headers sit on row seven, not row one, which determined every later load | 768,222 rows, 14 columns, 5,681 products |
| 02 | `02_data_cleaning.ipynb` | Standardises columns, drops unusable rows, maps the product group field into 25 categories | 767,180 rows, 0.14% loss, 5,680 products |
| 03 | `03_eda.ipynb` | Basket value distribution, segmentation, category penetration, ABC analysis, day of week, monthly trend | Segments 108,349 / 79,868 / 29,820, FOOD STAPLES 42.19% |
| 04 | `04_transaction_encoding.ipynb` | One-hot encodes baskets into the matrix Apriori needs | 218,037 by 25 boolean matrix |
| 05 | `05_market_basket_analysis.ipynb` | Apriori and FP-Growth, chi-square, **Bonferroni correction** | 243 itemsets, 1,228 rules, 1,226 significant, 1,222 after correction, max lift 6.81 |
| 06 | `06_clustering.ipynb` | K-Means twice, on frequency and on co-occurrence. Elbow and silhouette | 0.190 to 0.554, increase 0.364, three clusters |
| 07 | `07_placement_simulation.ipynb` | Expands three clusters to five zones, defines and computes the cross-sell capture metric, projects revenue with a 95% CI | 28 to 56 rules, 8.2% to 16.3%, Rs 1.30 crore projected |
| 08 | `08_evaluation.ipynb` | Cross-checks everything, temporal validation, pilot protocol | Apriori and FP-Growth identical, median lift ratio 1.011 |
| 09 | `09_ml_recommendation.ipynb` | Product level rules on the top 100 items, 70:30 split, held-out evaluation | 100 rules, max lift 22.41, 28.0% hit rate on 19,808 baskets |
| 10 | `10_demand_forecasting.ipynb` | Linear regression and Prophet on monthly revenue | LR R squared -2.377, Prophet 14.3% better MAE |
| 11 | `11_basket_classifier.ipynb` | Depth-5 decision tree on 25 binary category features | 61.3% against a 49.7% baseline, cooking oil 0.280 top feature |
| 12 | `12_neural_network.ipynb` | MLP on identical features, labels and split | 69.05%, ceiling 71.67%, gap decomposed 6.55 capacity plus 1.20 model family |

## 2.2 The data platform

**Transactional layer, three tables.** `oltp.products`, `oltp.transactions`,
`oltp.transaction_items`. Three design decisions driven by measurement rather than convention: unit
of sale recorded on the line item because 356 products sell in more than one unit; an explicit line
number because 1,587 transaction and product combinations legitimately repeat on the same
transaction; and monetary values at NUMERIC scale 6 because at scale 4 the rounding moves two
baskets across the Rs 500 segment boundary and shifts revenue by one paisa, which made SQL disagree
with the notebooks.

**Analytical layer, star schema.** `fact_sales` at 767,180 rows, with `dim_date`, `dim_category`,
`dim_product` and `dim_basket`. Seven views serve the dashboard. `dim_category.zone_assignment`
stores this study's placement zones as a queryable attribute, which is what produces the result that
the anchor zone carries 40.6 per cent of revenue from five of twenty-five categories.

**Orchestration.** `dags/product_placement_pipeline.py`, five sequential tasks: load OLTP, build
warehouse, run quality checks, refresh dashboard artifacts, complete. Idempotent, verified by
running against an empty database and then again, confirming no rows inserted the second time.

**Infrastructure.** Docker Compose. Postgres 16 on host port 5435, Airflow 3.3.0 LocalExecutor on
8082. Both ports chosen because 5432, 5433, 5434, 8080 and 8081 are taken by other stacks on this
machine.

## 2.3 The dashboard

`dashboard/app.py`, Streamlit, two audiences. Store owner mode has three pages including a shelf
planner that returns co-purchase recommendations for a selected product, a monthly stock plan, and
performance summaries. Examiner mode has seven pages covering project overview, store analytics,
association rules, clustering, model validation, placement zones and the ethical position.

It reads from the warehouse when available and falls back to committed CSV and JSON artifacts when
not, displaying which source is in use, so it works for a reader who has neither the database nor
the confidential source data.

## 2.4 Reproducibility

Three independent mechanisms, all green today.

| Mechanism | Scope | Result today |
|---|---|---|
| `etl/quality_checks.py` | 32 checks against the live warehouse | All 32 passed |
| `reproduce_all_results.py` | 13 checks across 9 stages, regenerates derived files | All passed |
| `scripts/verify_thesis_numbers.py` | 60 individual figures against warehouse, artifacts and constants | 60 of 60 matched, 6 declared not auto-checkable |

The sweep reports its own count rather than comparing against a maintained total, because during
development a summary claiming thirty-eight verified figures stayed in place while the table it
described grew to fifty-three rows.

## 2.5 Figures

28 rendered charts in `reports/figures/`. All currently unused by the dissertation. Note the
filename prefixes collide: `chart9`, `chart10` and `chart11` are each used for two or three
different charts.

## 2.6 Version control

836 commits from 2026-05-28 to 2026-08-14, one branch per stage of work, merged into `main`.
Twenty numbered work branches, the most recent being `20-remove-em-dash`.

---

# Part 3: What to do, in order

| # | Action | Why it is ranked here |
|---|---|---|
| 1 | **Strip the store name from notebooks 07, 09 and 01 and regenerate the planogram** | An ethics claim in the document is currently false, and the contradiction is printed on your headline figure |
| 2 | **Add the Bonferroni result to sections 12.4, 15, 23.2 and the abstract** | Free credit. The work is done, the document just does not claim it |
| 3 | **Decide the `PROJECT_LOG.md` question** | Highest integrity risk in the repository, and it is only your call to make |
| 4 | **Find the uplift benchmark citation, or reframe the projection** | The headline rupee figure is undefendable without it |
| 5 | **Reword section 13.5 on the excluded tactics** | Currently reads as implemented, is actually a design boundary |
| 6 | **Decide the 307 versus 304 denominator and disclose it** | Feeds the projection, and disclosure beats discovery |
| 7 | **Qualify the 1% recommender baseline, or compute a popularity weighted one** | Small exposure, cheap to close |
| 8 | **Add the clause about the two extra corrected pairs to section 22** | Eleven words, removes a discoverable omission |
| 9 | **Place the figures** | Covered in `PROMPT_HANDOFF.md` and the figure plan |
| 10 | **Archive the three superseded draft files** | Stops the version confusion that produced half these questions |

---

**Nothing in the repository was modified while producing this document.** Every command run was
read only, apart from `reproduce_all_results.py`, which regenerates derived files in
`dashboard/artifacts/` by design and wrote one new log to
`reports/reproduction_log_20260814_155317.txt`.
