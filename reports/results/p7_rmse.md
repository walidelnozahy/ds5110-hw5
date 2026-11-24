| variant   | fill                                                   | mirrors   | RMSE (log price)   | vs C       |
|:----------|:-------------------------------------------------------|:----------|:-------------------|:-----------|
| A         | median Lot Frontage per SalePrice quintile, full table | 6.1       | 0.1619257          | -0.0000005 |
| B         | neighborhood median, fitted on full table before CV    | 6.2       | 0.1619168          | -0.0000093 |
| C         | neighborhood median inside a Pipeline                  | 6.3       | 0.1619261          | +0.0000000 |