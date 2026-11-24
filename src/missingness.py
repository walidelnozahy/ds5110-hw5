"""Part 5: evidence about the missingness mechanism (notebook §4.1 pattern).

Usage: python src/missingness.py data/processed/ames_clean.csv
Writes reports/results/p5_*.md.
"""
import sys
from pathlib import Path

import pandas as pd
from scipy import stats

from clean import read_clean

RESULTS = Path("reports/results")

# The two columns with true missing values that we study (after Part 3).
TARGETS = ["Lot Frontage", "Mas Vnr Area"]
# Observed columns to compare against: four numeric, four categorical.
NUMERIC = ["Lot Area", "Gr Liv Area", "Year Built", "SalePrice"]
CATEGORICAL = ["Lot Config", "Lot Shape", "Neighborhood", "Sale Condition"]


def compare_groups(df: pd.DataFrame, col: str, observed_cols: list[str]) -> pd.DataFrame:
    """Compare rows with and without `col` on observed columns. Return a summary table.

    Notebook §4.1: group by df[col].isna() and compare the means. A clear difference
    between the two rows is evidence against MCAR. Welch's t-test puts a p-value on it.
    """
    missing = df[col].isna()
    table = df.groupby(missing)[observed_cols].mean().T            # §4.1 pattern
    table.columns = ["mean, value present", "mean, value missing"]
    table["p-value (Welch t-test)"] = [
        stats.ttest_ind(df.loc[missing, c], df.loc[~missing, c], equal_var=False).pvalue
        for c in observed_cols
    ]
    return table


def compare_categories(df: pd.DataFrame, col: str, cat: str, top: int = 6) -> tuple[pd.DataFrame, float]:
    """Share of `col` missing within each level of a categorical column (levels with 10+ houses), plus a chi-square p-value.

    Under MCAR every level would have about the same share missing.
    """
    missing = df[col].isna()
    table = (df.assign(missing=missing)
               .groupby(cat)["missing"].agg(houses="size", missing="sum", share_missing="mean")
               .sort_values("share_missing", ascending=False))
    p = stats.chi2_contingency(pd.crosstab(df[cat], missing)).pvalue
    return table[table["houses"] >= 10].head(top), p   # tiny groups shown would be noise


if __name__ == "__main__":
    df = read_clean(sys.argv[1])
    RESULTS.mkdir(parents=True, exist_ok=True)

    share = pd.DataFrame({
        "missing": [int(df[c].isna().sum()) for c in TARGETS],
        "share missing": [round(df[c].isna().mean(), 3) for c in TARGETS],
    }, index=TARGETS)
    print(share, "\n")
    share.to_markdown(RESULTS / "p5_share.md")

    for col in TARGETS:
        slug = col.lower().replace(" ", "_")
        num = compare_groups(df, col, NUMERIC)
        shown = num.map("{:.1f}".format)
        shown["p-value (Welch t-test)"] = num["p-value (Welch t-test)"].map("{:.2g}".format)
        print(f"== {col}: numeric comparison\n{shown}\n")
        shown.to_markdown(RESULTS / f"p5_{slug}_numeric.md", disable_numparse=True)
        for cat in CATEGORICAL:
            table, p = compare_categories(df, col, cat)
            table["share_missing"] = table["share_missing"].round(3)
            print(f"== {col} by {cat} (chi-square p = {p:.2g})\n{table}\n")
            with open(RESULTS / f"p5_{slug}_by_{cat.lower().replace(' ', '_')}.md", "w") as f:
                f.write(table.to_markdown() + f"\n\nChi-square test of independence: p = {p:.2g}\n")
