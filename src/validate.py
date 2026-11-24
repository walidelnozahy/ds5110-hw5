"""Part 2: validation as code. Raise once, listing every failure (notebook §1).

Usage: python src/validate.py <path> [--raw]
  --raw  the file is the tab-separated original; otherwise the cleaned CSV.
Exit code 1 when validation fails.
"""
import sys
import pandas as pd

DICT = "data dictionary (DataDocumentation.txt)"


class ValidationError(Exception):
    pass


# ---------------------------------------------------------------- schema
# Text columns: every Nominal / Ordinal variable in the dictionary that is stored as letters.
TEXT_COLUMNS = [
    "MS Zoning", "Street", "Alley", "Lot Shape", "Land Contour", "Utilities", "Lot Config",
    "Land Slope", "Neighborhood", "Condition 1", "Condition 2", "Bldg Type", "House Style",
    "Roof Style", "Roof Matl", "Exterior 1st", "Exterior 2nd", "Mas Vnr Type", "Exter Qual",
    "Exter Cond", "Foundation", "Bsmt Qual", "Bsmt Cond", "Bsmt Exposure", "BsmtFin Type 1",
    "BsmtFin Type 2", "Heating", "Heating QC", "Central Air", "Electrical", "Kitchen Qual",
    "Functional", "Fireplace Qu", "Garage Type", "Garage Finish", "Garage Qual", "Garage Cond",
    "Paved Drive", "Pool QC", "Fence", "Misc Feature", "Sale Type", "Sale Condition",
]
# Numeric columns: the Discrete / Continuous variables, the two identifiers, and the three
# coded variables stored as numbers (MS SubClass, Overall Qual, Overall Cond).
NUMERIC_COLUMNS = [
    "Order", "PID", "MS SubClass", "Lot Frontage", "Lot Area", "Overall Qual", "Overall Cond",
    "Year Built", "Year Remod/Add", "Mas Vnr Area", "BsmtFin SF 1", "BsmtFin SF 2",
    "Bsmt Unf SF", "Total Bsmt SF", "1st Flr SF", "2nd Flr SF", "Low Qual Fin SF",
    "Gr Liv Area", "Bsmt Full Bath", "Bsmt Half Bath", "Full Bath", "Half Bath",
    "Bedroom AbvGr", "Kitchen AbvGr", "TotRms AbvGrd", "Fireplaces", "Garage Yr Blt",
    "Garage Cars", "Garage Area", "Wood Deck SF", "Open Porch SF", "Enclosed Porch",
    "3Ssn Porch", "Screen Porch", "Pool Area", "Misc Val", "Mo Sold", "Yr Sold", "SalePrice",
]
COLUMNS = set(TEXT_COLUMNS) | set(NUMERIC_COLUMNS)   # 43 + 39 = 82, the dictionary's count

# ---------------------------------------------------------------- ranges
# (low, high), inclusive. NaN is not judged here: missingness is Parts 3 and 5.
# Ames was founded in 1864, so no house in it is older (physical limit).
# The sales run 2006 to 2010, so nothing was built after 2010 (study period).
RANGES = {
    "Year Built":     (1864, 2010),       # physical limit (town founded 1864) + study period end
    "Year Remod/Add": (1864, 2010),       # same
    "Garage Yr Blt":  (1864, 2010),       # same
    "Yr Sold":        (2006, 2010),       # study period, dictionary abstract: "sold in Ames, IA from 2006 to 2010"
    "Mo Sold":        (1, 12),            # physical limit: calendar months, dictionary "Month Sold (MM)"
    "Overall Qual":   (1, 10),            # data dictionary: 10 Very Excellent ... 1 Very Poor
    "Overall Cond":   (1, 10),            # data dictionary: same 1-10 scale
    "Lot Area":       (1, None),          # physical limit: a lot has positive area
    "Lot Frontage":   (1, None),          # physical limit: feet of street, positive when known
    "Gr Liv Area":    (1, None),          # physical limit: a sold house has living area
    "SalePrice":      (1, None),          # physical limit: a sale price is positive
    "Total Bsmt SF":  (0, None),          # physical limit: areas cannot be negative
    "Garage Area":    (0, None),          # physical limit
    "Pool Area":      (0, None),          # physical limit
    "Mas Vnr Area":   (0, None),          # physical limit
    "Garage Cars":    (0, None),          # physical limit: a count
    "Bedroom AbvGr":  (0, None),          # physical limit: a count
}

# ---------------------------------------------------------------- allowed values
# Every set is copied from the data dictionary, code column. "NA" is a dictionary code
# where the dictionary lists it (it means "none", see Part 3).
ALLOWED = {
    "MS SubClass": {20, 30, 40, 45, 50, 60, 70, 75, 80, 85, 90, 120, 150, 160, 180, 190},
    "MS Zoning": {"A", "C", "FV", "I", "RH", "RL", "RP", "RM"},
    "Street": {"Grvl", "Pave"},
    "Alley": {"Grvl", "Pave", "NA"},
    "Lot Config": {"Inside", "Corner", "CulDSac", "FR2", "FR3"},
    "Neighborhood": {
        "Blmngtn", "Blueste", "BrDale", "BrkSide", "ClearCr", "CollgCr", "Crawfor", "Edwards",
        "Gilbert", "Greens", "GrnHill", "IDOTRR", "Landmrk", "MeadowV", "Mitchel", "Names",
        "NoRidge", "NPkVill", "NridgHt", "NWAmes", "OldTown", "SWISU", "Sawyer", "SawyerW",
        "Somerst", "StoneBr", "Timber", "Veenker",
    },
    "Bldg Type": {"1Fam", "2FmCon", "Duplx", "TwnhsE", "TwnhsI"},
    "Exterior 2nd": {
        "AsbShng", "AsphShn", "BrkComm", "BrkFace", "CBlock", "CemntBd", "HdBoard", "ImStucc",
        "MetalSd", "Other", "Plywood", "PreCast", "Stone", "Stucco", "VinylSd", "Wd Sdng", "WdShing",
    },
    "Mas Vnr Type": {"BrkCmn", "BrkFace", "CBlock", "None", "Stone"},
    "Central Air": {"N", "Y"},
    "Garage Type": {"2Types", "Attchd", "Basment", "BuiltIn", "CarPort", "Detchd", "NA"},
    "Pool QC": {"Ex", "Gd", "TA", "Fa", "NA"},
    "Sale Type": {"WD", "CWD", "VWD", "New", "COD", "Con", "ConLw", "ConLI", "ConLD", "Oth"},
}


def check_schema(df: pd.DataFrame) -> list[str]:
    """Return a list of schema failures: missing or extra columns, wrong dtype families."""
    errors = []
    missing = sorted(COLUMNS - set(df.columns))
    extra = sorted(set(df.columns) - COLUMNS)
    if missing:
        errors.append(f"schema: missing columns {missing}")
    if extra:
        errors.append(f"schema: unexpected columns {extra}")
    for col in NUMERIC_COLUMNS:
        if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
            errors.append(f"schema: {col} has dtype {df[col].dtype}, expected numeric")
    for col in TEXT_COLUMNS:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            errors.append(f"schema: {col} has dtype {df[col].dtype}, expected text")
    return errors


def check_ranges(df: pd.DataFrame) -> list[str]:
    """Return one message per column with values outside its range. NaN is not judged here."""
    errors = []
    for col, (low, high) in RANGES.items():
        if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
            continue   # schema check already reported it
        s = df[col].dropna()
        bad = s[(s < low) | ((s > high) if high is not None else False)]
        if len(bad):
            shown = sorted(bad.unique())[:5]
            errors.append(f"range: {col}: {len(bad)} values outside [{low}, {high}], e.g. {shown}")
    return errors


def check_allowed(df: pd.DataFrame) -> list[str]:
    """Return one message per categorical column with values not in the dictionary."""
    errors = []
    for col, allowed in ALLOWED.items():
        if col not in df.columns:
            continue
        s = df[col].dropna()
        bad = s[~s.isin(allowed)]
        if len(bad):
            counts = bad.value_counts().to_dict()
            shown = {repr(k): v for k, v in counts.items()}   # repr shows trailing spaces
            errors.append(f"allowed: {col}: {len(bad)} values not in the dictionary {shown}")
    return errors


def check_cross_column(df: pd.DataFrame) -> list[str]:
    """Return failures of rules that involve two or more columns."""
    errors = []

    # 1. Remodel year is not before the build year.
    #    Source: dictionary, Year Remod/Add "same as construction date if no remodeling".
    bad = df[df["Year Remod/Add"] < df["Year Built"]]
    if len(bad):
        errors.append(f"cross: Year Remod/Add < Year Built in {len(bad)} rows, Order {bad['Order'].tolist()}")

    # 2. Nothing is built after the year of sale, except a "Partial" sale, which the dictionary
    #    defines as "Home was not completed when last assessed (associated with New Homes)":
    #    those houses may be finished up to one year after the contract.
    grace = (df["Sale Condition"] == "Partial").astype(int)
    for col in ["Year Built", "Year Remod/Add", "Garage Yr Blt"]:
        bad = df[df[col] > df["Yr Sold"] + grace]
        if len(bad):
            errors.append(f"cross: {col} after Yr Sold in {len(bad)} rows, Order {bad['Order'].tolist()}")

    # 3. A house with a garage has garage details that are not "NA" (no garage).
    #    Source: dictionary, Garage Qual / Cond / Finish code NA = "No Garage".
    has_garage = df["Garage Type"].notna() & (df["Garage Type"] != "NA")
    for col in ["Garage Finish", "Garage Qual", "Garage Cond"]:
        bad = df[has_garage & (df[col] == "NA")]
        if len(bad):
            errors.append(f"cross: Garage Type is a garage but {col} == 'NA' in {len(bad)} rows, Order {bad['Order'].tolist()}")

    # 4. Masonry veneer type "None" goes with area 0, and a real veneer type with area > 0.
    #    Source: dictionary, Mas Vnr Type None = "None"; Mas Vnr Area in square feet.
    vt, va = df["Mas Vnr Type"], df["Mas Vnr Area"]
    bad = df[((vt == "None") & (va > 0)) | (vt.notna() & (vt != "None") & (va == 0))]
    if len(bad):
        errors.append(f"cross: Mas Vnr Type and Mas Vnr Area disagree in {len(bad)} rows, Order {bad['Order'].tolist()}")
    return errors


def validate(df: pd.DataFrame) -> pd.DataFrame:
    errors = check_schema(df) + check_ranges(df) + check_allowed(df) + check_cross_column(df)
    if errors:
        raise ValidationError("\n".join(errors))
    return df


if __name__ == "__main__":
    path = sys.argv[1]
    raw = "--raw" in sys.argv
    df = pd.read_csv(path, sep="\t" if raw else ",", keep_default_na=False, na_values=[""])
    try:
        validate(df)
        print(f"PASS {path}")
    except ValidationError as e:
        print(f"FAIL {path}\n{e}")
        sys.exit(1)
