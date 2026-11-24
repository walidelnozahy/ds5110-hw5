# HW5 report: Ames Housing quality audit

All numbers come from `make all`. Full tables are in `reports/results/`.

## 1 Provenance

2,930 rows and 82 columns on arrival, as expected. Source, date and citation are in the README.

## 2 Validation: failures on the raw file

Validation fails on the raw file and passes on the cleaned file.

| Failure | Rows | What I did |
| --- | ---: | --- |
| Garage Yr Blt = 2207 (after the study period) | 1 | Typo. Set to 2007 (house built 2006, sold 2007) |
| MS Zoning: `C (all)`, `I (all)`, `A (agr)` not in dictionary | 29 | Changed to `C`, `I`, `A` |
| Neighborhood: `NAmes` not in dictionary | 443 | Changed to `Names` (dictionary code) |
| Bldg Type: `Duplex`, `2fmCon`, `Twnhs` not in dictionary | 272 | Changed to `Duplx`, `2FmCon`, `TwnhsI` |
| Exterior 2nd: `CmentBd`, `Wd Shng`, `Brk Cmn` not in dictionary | 229 | Changed to `CemntBd`, `WdShing`, `BrkComm` |
| Sale Type: `"WD "` has an extra space | 2,536 | Removed the space |
| Remodel year before build year | 1 | Set remodel year = build year |
| Remodel year 2 years after the sale | 1 | Set remodel year = build year |
| Garage year after the sale | 1 | Same row as the 2207 typo |
| Has a garage, but quality says "No Garage" | 1 | Set to missing |
| Masonry type and area disagree (e.g. "None" with 344 sq ft) | 10 | Set both to missing |

Every change is listed in `reports/results/changes.md`.

## 3 Sentinels and structural absence

| What the file has | Where | Dictionary meaning | What I did |
| --- | --- | --- | --- |
| `"NA"` | 14 columns: Alley, Pool QC, Fence, Misc Feature, Fireplace Qu, 4 garage and 5 basement columns | "none" (no alley, no pool, no garage, ...) | Kept as a category |
| `"None"` | Mas Vnr Type (1,752 rows) | no masonry veneer | Kept as a category |
| empty cell | Lot Frontage (490), Garage Yr Blt, Mas Vnr, a few others | not defined | Missing (NaN) |

The pandas default turns all three into NaN. That would make 2,917 houses look like they have an
unknown pool quality, when they just have no pool.

Zeros: Garage Area, Total Bsmt SF, Pool Area, Fireplaces and Mas Vnr Area use 0 for "none".
These are true zeros, not sentinels. A house with no garage really has 0 sq ft of garage, and the zeros
match the "NA" rows (for example, 157 zero garage areas = 157 "No Garage").

## 4 Keys and duplicates

- `Order` is unique: it is the row number. `PID` is unique: it is the property ID.
- I use `PID` as the key. Each property sold once here, so it also identifies one sale.
- Exact duplicate rows: 0. Duplicate keys: 0.
- Neighborhood lookup join (28 neighborhoods, `validate="many_to_one"`): 2,930 rows before, 2,930 after.

## 5 Missingness mechanism

**Lot Frontage: 16.7% missing (490 houses).**

| Observed column | With a value | Missing |
| --- | ---: | ---: |
| Lot Area (mean, sq ft) | 9,710 | 12,331 |
| Year Built (mean) | 1971 | 1976 |
| Gr Liv Area (mean) | 1,489 | 1,553 |
| SalePrice (mean) | $180,100 | $184,263 |
| Share missing by Lot Config | Inside 13% | Cul-de-sac 49% |
| Share missing by Lot Shape | Regular 7% | Irregular 33% |

- Mechanism: **MAR**. I reject MCAR because missing values are much more common on big, irregular and
  cul-de-sac lots (chi-square p < 0.001). These columns are observed.
- What the data cannot tell: whether the missing lots have unusual frontage compared with similar lots.
  MAR and MNAR look the same in the data.
- If it were MNAR: the assessor might skip the field when the frontage is very short or hard to measure,
  like a narrow driveway lot. Then the missing value itself causes the gap.

**Mas Vnr Area: 1.1% missing (33 houses).**

- Missing houses are newer (built 1998 vs 1971 on average) and pricier ($225k vs $180k). Many are new
  homes not finished at the time of sale (5.7% of "Partial" sales vs 0.7% of normal sales). Lot shape and
  lot config show no difference.
- Mechanism: **MAR** (depends on build year and sale condition). I reject MCAR.
- What the data cannot tell: whether these houses got a veneer at all.

## 6 Imputation strategy

| Strategy | std before | std after | corr with Lot Area before | after |
| --- | ---: | ---: | ---: | ---: |
| Overall median | 23.4 | 21.3 | 0.49 | 0.36 |
| Median by Neighborhood | 23.4 | 21.7 | 0.49 | 0.39 |

![Overall median](figures/p6_median.png)
![Median by Neighborhood](figures/p6_neighborhood_median.png)

**I choose the median by Neighborhood.** In Part 5, Lot Frontage was MAR: whether it is missing depends on
things we can see, like the lot and where it is. So the fill should use those things. One overall median
gives all 490 houses the same value. The neighborhood median uses location, because lots in the same
neighborhood are usually laid out with similar widths. It keeps more of the spread and more of the link
with Lot Area. It also works inside a pipeline. Its weak point: it ignores lot type, so cul-de-sac lots
get a frontage that is a bit too wide. If the data were MNAR, no fill from other columns would fix that.

## 7 Leakage-safe evaluation

| Variant | Fill | RMSE (log price) |
| --- | --- | ---: |
| A | median per SalePrice quintile, full table | 0.1619257 |
| B | neighborhood median, fitted before CV | 0.1619168 |
| C | neighborhood median inside a Pipeline | 0.1619261 |

- **Correct: C.** The fill is learned from the training folds only.
  **A leaks the target:** the fill uses the sale price. **B leaks test rows:** the test houses helped
  make the medians.
- **A cannot price an unsold house.** You need the sale price to pick its quintile.
- **B vs C differs by only 0.00001.** A median barely moves when 20% of the rows are left out
  (under 1 foot on average). Lot Frontage also adds little once size and quality are in the model.
  The same reason makes A look fine here. With Lot Frontage as the only feature, A's leak shows:
  0.3796 (A) vs 0.3827 (C).

## 8 Summary

- **What I found:** wrong category codes, one typo year, a few impossible dates, and "NA" that means
  "none", not missing. No duplicates. Lot Frontage is missing mostly on irregular lots.
- **What I changed:** only empty cells became missing. I fixed the codes to match the dictionary,
  fixed the impossible years, and set contradicting values to missing. No rows were dropped.
  The raw file is unchanged.
- **What the data cannot tell:** whether the missing values are MAR or MNAR, which value is right in
  the 10 masonry conflicts, and anything about houses that did not sell in 2006 to 2010.
