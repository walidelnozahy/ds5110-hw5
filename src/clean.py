"""Parts 3 and 4: decode true missing values, keep structural "none", check keys.

Usage: python src/clean.py data/raw/AmesHousing.txt data/processed/ames_clean.csv
Writes the cleaned file, and the Part 2 to 4 evidence tables to reports/results/.
"""
import sys
from pathlib import Path

import pandas as pd

RESULTS = Path("reports/results")

# Columns where the dictionary defines "NA" as "none", not "unknown".
# Each value is the dictionary's own wording for the NA code.
NA_MEANS_NONE: dict[str, str] = {
    "Alley": "No alley access",
    "Bsmt Qual": "No Basement",
    "Bsmt Cond": "No Basement",
    "Bsmt Exposure": "No Basement",
    "BsmtFin Type 1": "No Basement",
    "BsmtFin Type 2": "No Basement",
    "Fireplace Qu": "No Fireplace",
    "Garage Type": "No Garage",
    "Garage Finish": "No Garage",
    "Garage Qual": "No Garage",
    "Garage Cond": "No Garage",
    "Pool QC": "No Pool",
    "Fence": "No Fence",
    "Misc Feature": "None",
}

# Category codes in the data that differ from the dictionary (Part 2 failures).
# This is the explicit, logged mapping: data code -> dictionary code.
RECODE: dict[str, dict[str, str]] = {
    "MS Zoning": {"C (all)": "C", "I (all)": "I", "A (agr)": "A"},
    "Neighborhood": {"NAmes": "Names"},           # dictionary spells North Ames "Names"
    "Bldg Type": {"Duplex": "Duplx", "2fmCon": "2FmCon",
                  "Twnhs": "TwnhsI"},             # TwnhsE is used for end units, so Twnhs = inside unit
    "Exterior 2nd": {"CmentBd": "CemntBd", "Wd Shng": "WdShing", "Brk Cmn": "BrkComm"},
    "Sale Type": {"WD ": "WD"},                   # trailing space
}

# Neighborhood codes and full names, copied from the data dictionary (Part 4 lookup).
NEIGHBORHOODS = {
    "Blmngtn": "Bloomington Heights", "Blueste": "Bluestem", "BrDale": "Briardale",
    "BrkSide": "Brookside", "ClearCr": "Clear Creek", "CollgCr": "College Creek",
    "Crawfor": "Crawford", "Edwards": "Edwards", "Gilbert": "Gilbert", "Greens": "Greens",
    "GrnHill": "Green Hills", "IDOTRR": "Iowa DOT and Rail Road", "Landmrk": "Landmark",
    "MeadowV": "Meadow Village", "Mitchel": "Mitchell", "Names": "North Ames",
    "NoRidge": "Northridge", "NPkVill": "Northpark Villa", "NridgHt": "Northridge Heights",
    "NWAmes": "Northwest Ames", "OldTown": "Old Town",
    "SWISU": "South & West of Iowa State University", "Sawyer": "Sawyer",
    "SawyerW": "Sawyer West", "Somerst": "Somerset", "StoneBr": "Stone Brook",
    "Timber": "Timberland", "Veenker": "Veenker",
}

# Numeric columns where 0 means "the house has none of this", with the matching category.
ZERO_MEANS_NONE = {
    "Mas Vnr Area": ("Mas Vnr Type", "None"),
    "Total Bsmt SF": ("Bsmt Qual", "NA"),
    "Garage Area": ("Garage Type", "NA"),
    "Garage Cars": ("Garage Type", "NA"),
    "Fireplaces": ("Fireplace Qu", "NA"),
    "Pool Area": ("Pool QC", "NA"),
    "Misc Val": ("Misc Feature", "NA"),
    "2nd Flr SF": (None, None),
    "Wood Deck SF": (None, None),
    "Open Porch SF": (None, None),
}


def read_clean(path: str) -> pd.DataFrame:
    """Read the cleaned CSV. Only empty cells are NaN; "NA" stays the "none" category."""
    return pd.read_csv(path, keep_default_na=False, na_values=[""])


def load_raw(path: str) -> pd.DataFrame:
    """Load with keep_default_na=False so that "NA" and "None" survive as strings.

    Only an empty cell is a true missing value. In this file an empty cell is the
    only way an unknown value is written (Part 3).
    """
    return pd.read_csv(path, sep="\t", keep_default_na=False, na_values=[""])


def sentinel_tables(path: str) -> None:
    """Part 3: compare the pandas default load with the explicit load. Write three tables."""
    default = pd.read_csv(path, sep="\t")
    explicit = load_raw(path)
    strings = pd.read_csv(path, sep="\t", keep_default_na=False)   # every cell as written

    # Which strings did the default load turn into NaN?
    rows = []
    for col in strings.columns:
        lost = strings.loc[default[col].isna(), col].astype(str).value_counts()
        for value, n in lost.items():
            same = strings[col].astype(str) == value
            kept = "no, NaN (true missing)" if explicit.loc[same, col].isna().all() else "yes, kept as a category"
            rows.append({"column": col, "string in file": repr(value), "rows": n,
                         "kept in explicit load?": kept})
    pd.DataFrame(rows).to_markdown(RESULTS / "p3_default_nan.md", index=False)

    # Columns with the string "NA": what does the dictionary say it means?
    rows = []
    for col in strings.columns:
        n = int((strings[col] == "NA").sum())
        if n:
            meaning = NA_MEANS_NONE.get(col)
            rows.append({"column": col, '"NA" rows': n,
                         "dictionary meaning of NA": meaning or "not defined",
                         "verdict": "none (structural)" if meaning else "unknown"})
    pd.DataFrame(rows).to_markdown(RESULTS / "p3_na_strings.md", index=False)

    # Numeric columns where 0 means "none": does the zero agree with the category?
    rows = []
    for col, (cat, code) in ZERO_MEANS_NONE.items():
        zeros = explicit[col] == 0
        row = {"column": col, "zeros": int(zeros.sum())}
        if cat:
            none_cat = explicit[cat] == code
            row["category says none"] = f"{cat} == {code!r}: {int(none_cat.sum())}"
            row["zero and none agree"] = int((zeros & none_cat).sum())
        rows.append(row)
    pd.DataFrame(rows).to_markdown(RESULTS / "p3_zeros.md", index=False)


def decode_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Turn only true missing values into NaN, fix the Part 2 failures. Return a new DataFrame.

    Every change is recorded in reports/results/changes.md.
    """
    df = df.copy()
    log = []

    def fix(mask, col, new, why):
        n = int(mask.sum())
        if n:
            orders = df.loc[mask, "Order"].tolist()
            old = df.loc[mask, col].unique().tolist()
            df.loc[mask, col] = new if not callable(new) else new(df.loc[mask])
            now = df.loc[mask, col].unique().tolist()
            log.append({"column": col, "rows": n, "Order": orders[:10],
                        "was": old[:5], "now": "NaN" if new is None else now[:5], "why": why})

    # 1. "NA" that contradicts its own parent column is unknown, not none.
    #    Order 1357 has a detached garage of 360 sq ft, but Garage Qual/Cond say "No Garage".
    has_garage = df["Garage Type"].notna() & (df["Garage Type"] != "NA")
    for col in ["Garage Finish", "Garage Qual", "Garage Cond"]:
        fix(has_garage & (df[col] == "NA"), col, None,
            "house has a garage, so 'No Garage' is wrong; the true value is unknown")

    # 2. Category codes that differ from the dictionary: explicit mapping, logged.
    for col, mapping in RECODE.items():
        for old, new in mapping.items():
            fix(df[col] == old, col, new, f"data code {old!r} is not in the dictionary; dictionary code is {new!r}")

    # 3. Out-of-range and impossible dates.
    fix(df["Garage Yr Blt"] == 2207, "Garage Yr Blt", 2007,
        "typo: house built 2006, remodelled 2007, sold 2007; 2207 is in the future")
    fix(df["Year Remod/Add"] < df["Year Built"], "Year Remod/Add", lambda r: r["Year Built"],
        "remodel before construction; dictionary: remodel date = construction date if no remodel")
    grace = (df["Sale Condition"] == "Partial").astype(int)
    fix(df["Year Remod/Add"] > df["Yr Sold"] + grace, "Year Remod/Add", lambda r: r["Year Built"],
        "remodel recorded 2 years after the sale; at the time of sale there was no remodel")

    # 4. Masonry veneer type and area disagree: we cannot tell which one is wrong.
    vt, va = df["Mas Vnr Type"], df["Mas Vnr Area"]
    clash = ((vt == "None") & (va > 0)) | (vt.notna() & (vt != "None") & (va == 0))
    for col in ["Mas Vnr Area", "Mas Vnr Type"]:
        fix(clash, col, None, "type and area disagree (e.g. 'None' with 344 sq ft); set both to unknown")

    RESULTS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(log).to_markdown(RESULTS / "changes.md", index=False)
    return df


def check_keys(df: pd.DataFrame) -> None:
    """Assert key uniqueness; print exact and key duplicate counts; run the many_to_one join."""
    rows = [
        {"check": "rows", "value": len(df)},
        {"check": "Order unique", "value": df["Order"].is_unique},
        {"check": "PID unique", "value": df["PID"].is_unique},
        {"check": "exact duplicate rows", "value": int(df.duplicated().sum())},
        {"check": "duplicate rows ignoring Order", "value": int(df.drop(columns="Order").duplicated().sum())},
        {"check": "duplicate Order values", "value": int(df["Order"].duplicated().sum())},
        {"check": "duplicate PID values", "value": int(df["PID"].duplicated().sum())},
    ]
    assert df["Order"].is_unique and df["PID"].is_unique, "key is not unique"

    lookup = pd.DataFrame(list(NEIGHBORHOODS.items()), columns=["Neighborhood", "Neighborhood Name"])
    joined = pd.merge(df, lookup, on="Neighborhood", how="left", validate="many_to_one")
    assert len(joined) == len(df), "the join changed the row count"
    assert joined["Neighborhood Name"].notna().all(), "a Neighborhood code has no full name"
    rows += [
        {"check": "lookup table rows (neighborhoods)", "value": len(lookup)},
        {"check": "rows before join", "value": len(df)},
        {"check": "rows after join", "value": len(joined)},
        {"check": "rows with no full name after join", "value": int(joined["Neighborhood Name"].isna().sum())},
    ]
    table = pd.DataFrame(rows)
    print(table.to_string(index=False))
    table.to_markdown(RESULTS / "p4_keys.md", index=False)


if __name__ == "__main__":
    raw_path, out_path = sys.argv[1], sys.argv[2]
    RESULTS.mkdir(parents=True, exist_ok=True)
    sentinel_tables(raw_path)
    df = decode_missing(load_raw(raw_path))
    check_keys(df)
    df.to_csv(out_path, index=False)
    print(f"Wrote {out_path}: {df.shape[0]} rows, {df.shape[1]} columns")
