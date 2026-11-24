"""Part 6: at least two strategies for Lot Frontage, and their costs (notebook §5 pattern).

Usage: python src/impute.py data/processed/ames_clean.csv
Writes reports/results/p6_costs.md, reports/figures/p6_*.png and
data/processed/ames_imputed.csv (the chosen strategy).
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")   # draw to files, no window
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.impute import SimpleImputer

from clean import read_clean

RESULTS = Path("reports/results")
FIGURES = Path("reports/figures")
TARGET = "Lot Frontage"
OTHER = "Lot Area"


class GroupMedianImputer(BaseEstimator, TransformerMixin):
    """Fill `col` with the median of its group (default: the house's Neighborhood).

    fit() learns one median per group from the rows it is given, and nothing else.
    transform() only looks those medians up. So inside a Pipeline, cross-validation
    refits the medians on each training fold and the test fold never shapes its own fill.
    A group with no observed value (or unseen in fit) falls back to the overall median.
    The group column is dropped after filling, so the model sees numbers only.
    """

    def __init__(self, col: str = TARGET, group: str = "Neighborhood"):
        self.col = col
        self.group = group

    def fit(self, X: pd.DataFrame, y=None):
        self.medians_ = X.groupby(self.group)[self.col].median()   # NaN for an all-missing group
        self.overall_ = X[self.col].median()
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        fill = X[self.group].map(self.medians_).fillna(self.overall_)
        X[self.col] = X[self.col].fillna(fill)
        return X.drop(columns=self.group)


def cost_table(before: pd.Series, after: pd.Series, other: pd.Series) -> pd.Series:
    """std before/after, correlation with `other` before/after."""
    return pd.Series({
        "std before": before.std(),                 # observed values only
        "std after": after.std(),
        f"corr with {other.name} before": before.corr(other),   # rows where both are present
        f"corr with {other.name} after": after.corr(other),
    })


def histogram(before: pd.Series, after: pd.Series, name: str, path: Path) -> None:
    """Observed values and filled values, stacked, so the fill's shape is visible."""
    filled_only = after[before.isna()]
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.hist([before.dropna(), filled_only], bins=range(0, 210, 5), stacked=True,
            label=[f"observed ({before.notna().sum()})", f"filled ({len(filled_only)})"],
            color=["#9db4c0", "#c0392b"])
    ax.set(title=f"Lot Frontage after {name}", xlabel="Lot Frontage (feet, 200+ not shown)",
           ylabel="houses")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    df = read_clean(sys.argv[1])
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    before = df[TARGET]

    strategies = {
        # Simple fill (notebook §5): one number for every missing house.
        "median": pd.Series(
            SimpleImputer(strategy="median").fit_transform(df[[TARGET]]).ravel(),
            index=df.index, name=TARGET),
        # Uses another column: the median of the house's own Neighborhood.
        "neighborhood median": GroupMedianImputer().fit_transform(df[[TARGET, "Neighborhood"]])[TARGET],
    }

    costs = pd.DataFrame({name: cost_table(before, after, df[OTHER])
                          for name, after in strategies.items()}).T
    costs.insert(0, "distinct fill values", [after[before.isna()].nunique() for after in strategies.values()])
    print(costs.round(3))
    costs.round(3).to_markdown(RESULTS / "p6_costs.md")

    for name, after in strategies.items():
        histogram(before, after, name, FIGURES / f"p6_{name.replace(' ', '_')}.png")

    # Neighborhoods where every Lot Frontage is missing get the overall median.
    groups = df.groupby("Neighborhood")[TARGET]
    empty = groups.count()[groups.count() == 0].index.tolist()
    print("Neighborhoods with no observed Lot Frontage (overall median used):", empty)
    (RESULTS / "p6_fallback.md").write_text(
        f"Neighborhoods with no observed Lot Frontage, filled with the overall median: {empty}\n")

    # The chosen strategy (see report): neighborhood median.
    out = df.copy()
    out[TARGET] = strategies["neighborhood median"]
    out.to_csv("data/processed/ames_imputed.csv", index=False)
