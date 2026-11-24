"""Part 7: variants A, B, C with the given model (notebook §6.1 to §6.3).

Usage: python src/evaluate.py data/processed/ames_clean.csv
Writes reports/results/p7_rmse.md.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold, cross_val_score
from sklearn.pipeline import make_pipeline

from clean import read_clean
from impute import GroupMedianImputer

RESULTS = Path("reports/results")

# 13 numeric columns, including "Lot Frontage". Reasons are in README.md.
# All except Lot Frontage are complete after cleaning, so the only fill is the one under test.
NUMERIC_FEATURES: list[str] = [
    "Lot Frontage", "Lot Area", "Overall Qual", "Overall Cond", "Year Built", "Year Remod/Add",
    "Gr Liv Area", "1st Flr SF", "Full Bath", "Half Bath", "Bedroom AbvGr", "TotRms AbvGrd",
    "Fireplaces",
]
CV = KFold(n_splits=5, shuffle=True, random_state=5110)


def rmse(estimator, X: pd.DataFrame, y: pd.Series) -> float:
    return -cross_val_score(estimator, X, y, cv=CV, scoring="neg_root_mean_squared_error").mean()


if __name__ == "__main__":
    df = read_clean(sys.argv[1])
    y = np.log(df["SalePrice"])
    X = df[NUMERIC_FEATURES]
    assert X.drop(columns="Lot Frontage").notna().all().all(), "a feature other than Lot Frontage has NaN"
    model = LinearRegression()

    # A (§6.1, target leakage): median Lot Frontage within each SalePrice quintile, full table.
    quintile = pd.qcut(df["SalePrice"], 5, labels=False)
    X_a = X.copy()
    X_a["Lot Frontage"] = X["Lot Frontage"].fillna(X.groupby(quintile)["Lot Frontage"].transform("median"))

    # B (§6.2, train/test contamination): neighborhood medians learned from all 2,930 rows,
    # then cross-validated. Test-fold houses helped make their own fill.
    with_group = df[NUMERIC_FEATURES + ["Neighborhood"]]
    X_b = GroupMedianImputer().fit_transform(with_group)

    # C (§6.3, honest): the imputer inside a Pipeline, refitted on each training fold.
    pipe = make_pipeline(GroupMedianImputer(), LinearRegression())

    results = pd.DataFrame({
        "variant": ["A", "B", "C"],
        "fill": ["median Lot Frontage per SalePrice quintile, full table",
                 "neighborhood median, fitted on full table before CV",
                 "neighborhood median inside a Pipeline"],
        "mirrors": ["6.1", "6.2", "6.3"],
        "RMSE (log price)": [rmse(model, X_a, y), rmse(model, X_b, y), rmse(pipe, with_group, y)],
    })
    results["vs C"] = results["RMSE (log price)"] - results["RMSE (log price)"].iloc[2]
    pd.set_option("display.float_format", "{:.7f}".format)
    print(results.to_string(index=False))
    shown = results.copy()
    for c in ["RMSE (log price)", "vs C"]:
        shown[c] = shown[c].map("{:+.7f}".format if c == "vs C" else "{:.7f}".format)
    shown.to_markdown(RESULTS / "p7_rmse.md", index=False, disable_numparse=True)

    # Why is B so close to C? How much do the medians move between folds?
    full = GroupMedianImputer().fit(with_group).medians_
    rows = []
    for k, (train, _) in enumerate(CV.split(with_group)):
        fold = GroupMedianImputer().fit(with_group.iloc[train]).medians_.reindex(full.index)
        change = (fold - full).abs().dropna()        # skip groups with no observed value
        rows.append({"fold": k + 1, "neighborhoods whose median changed": int((change > 0).sum()),
                     "largest change (feet)": float(change.max()),
                     "mean change (feet)": round(float(change.mean()), 2)})
    drift = pd.DataFrame(rows)
    print(drift.to_string(index=False))
    drift.to_markdown(RESULTS / "p7_median_drift.md", index=False)

    # Does A leak at all? With Lot Frontage as the only feature, the target-based fill shows.
    solo = pd.DataFrame({
        "variant": ["A", "C"],
        "RMSE, Lot Frontage as the only feature": [
            rmse(model, X_a[["Lot Frontage"]], y),
            rmse(make_pipeline(GroupMedianImputer(), LinearRegression()),
                 with_group[["Lot Frontage", "Neighborhood"]], y),
        ],
    })
    print(solo.to_string(index=False))
    solo.to_markdown(RESULTS / "p7_solo.md", index=False, floatfmt=".4f")
