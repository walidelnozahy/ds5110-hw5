# HW5: Ames Housing quality audit

DS5110, Homework 5. A data-quality audit of the Ames Housing data: validation rules, sentinel
decoding, keys, the missingness mechanism of Lot Frontage, an imputation strategy, and a
leakage-safe evaluation. The write-up is in [`reports/report.md`](reports/report.md).

## How to run

Needs Python 3.14 (tested with 3.14.8) and `make`.

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make all
```

`make all` downloads the raw file into `data/raw/` (only if it is not there yet), cleans it into
`data/processed/`, checks that validation fails on the raw file and passes on the cleaned file,
then runs Parts 5 to 7. Tables go to `reports/results/`, histograms to `reports/figures/`.
`make clean` removes everything the pipeline made, but never the raw file.

| Step | Script | Writes |
| --- | --- | --- |
| Part 1 | `src/download.py` | `data/raw/AmesHousing.txt` (never overwritten) |
| Part 2 | `src/validate.py` | pass / fail with every failure listed |
| Parts 3, 4 | `src/clean.py` | `data/processed/ames_clean.csv`, `reports/results/p3_*`, `p4_keys.md`, `changes.md` |
| Part 5 | `src/missingness.py` | `reports/results/p5_*` |
| Part 6 | `src/impute.py` | `reports/results/p6_*`, `reports/figures/p6_*.png`, `data/processed/ames_imputed.csv` |
| Part 7 | `src/evaluate.py` | `reports/results/p7_*` |

**Reading the cleaned file.** The cleaned CSV keeps the dictionary code `"NA"` ("no garage",
"no pool", ...) as a real category. Read it with `src/clean.py:read_clean`, or with
`pd.read_csv(path, keep_default_na=False, na_values=[""])`. A plain `pd.read_csv(path)` would turn
those categories back into `NaN`.

## Provenance (Part 1)

| Item | Value |
| --- | --- |
| Source URL | https://jse.amstat.org/v19n3/decock/AmesHousing.txt (linked from the article page https://jse.amstat.org/v19n3/decock.pdf) |
| Downloaded on | 2026-11-23 |
| Citation | De Cock, D. (2011). Ames, Iowa: Alternative to the Boston Housing Data as an End of Semester Regression Project. Journal of Statistics Education, 19(3). |
| Data dictionary | https://jse.amstat.org/v19n3/decock/DataDocumentation.txt |
| Terms of use | No license is stated for the file; it is shared through the JSE data archive (© American Statistical Association, https://jse.amstat.org/jse_data_archive.htm) for teaching, so we use it only for non-commercial coursework and cite De Cock (2011). |
| Rows, columns on arrival | 2,930 rows, 82 columns (tab-separated) |
| Original source | Ames, Iowa Assessor's Office (per the dictionary), sales 2006 to 2010 |

`src/download.py` downloads the file once. If `data/raw/AmesHousing.txt` already exists it prints a
message and stops, so the raw copy is never overwritten or edited.

## Features used in Part 7

`NUMERIC_FEATURES` in `src/evaluate.py`, 13 columns:

| Column | Why |
| --- | --- |
| Lot Frontage | the column under test: its fill is what variants A, B and C change |
| Lot Area | size of the land, the main driver of lot value |
| Overall Qual | the strongest single predictor of price in this data |
| Overall Cond | condition is priced separately from quality |
| Year Built | newer houses sell for more |
| Year Remod/Add | a remodel raises value |
| Gr Liv Area | living space above ground, the main size measure |
| 1st Flr SF | footprint of the house |
| Full Bath | bathrooms add value |
| Half Bath | same |
| Bedroom AbvGr | number of bedrooms |
| TotRms AbvGrd | total rooms |
| Fireplaces | a simple amenity count |

All 13 are numeric, and all except Lot Frontage have no missing values after cleaning. Columns
such as Total Bsmt SF or Garage Cars were left out because they have one unknown value each, which
would need a second fill and blur the comparison.

## AI assistance

To be completed by the author: tool, what it was used for, which files.
