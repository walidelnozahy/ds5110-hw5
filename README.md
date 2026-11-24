# HW5: Ames Housing quality audit

The report is in [`reports/report.md`](reports/report.md).

## How to run

Needs Python 3.14.

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make all
```

`make all` downloads the data, cleans it, checks it, and writes the tables and charts to `reports/`.

Note: the cleaned file keeps `"NA"` as a real value ("no garage", "no pool"). Read it with
`keep_default_na=False, na_values=[""]`, or pandas will turn it into missing.

## Provenance (Part 1)

| Item | Value |
| --- | --- |
| Source URL | https://jse.amstat.org/v19n3/decock/AmesHousing.txt |
| Downloaded on | 2026-11-23 |
| Citation | De Cock, D. (2011). Ames, Iowa: Alternative to the Boston Housing Data as an End of Semester Regression Project. Journal of Statistics Education, 19(3). |
| Data dictionary | https://jse.amstat.org/v19n3/decock/DataDocumentation.txt |
| Terms of use | I did not find a license for this data. It is shared on the journal's data archive (https://jse.amstat.org/jse_data_archive.htm), and I use it only for coursework, with the citation above. |
| Rows, columns on arrival | 2,930 rows, 82 columns |

`src/download.py` downloads the file once. If the file is already there, it does not overwrite it.

## Features used in Part 7

13 numeric columns: Lot Frontage, Lot Area, Overall Qual, Overall Cond, Year Built, Year Remod/Add,
Gr Liv Area, 1st Flr SF, Full Bath, Half Bath, Bedroom AbvGr, TotRms AbvGrd, Fireplaces.

Why: they are common drivers of house price (size, quality, age, rooms). Lot Frontage is the column
we test. All the others have no missing values, so the only fill in the model is the one we compare.

## AI assistance

I used Claude (Anthropic) to help write the code, format the tables and draft the report.
I checked every step and ran the pipeline myself.
