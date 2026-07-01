# Test Results

The pipeline was run from the repository root with:

```bash
python3 src/run_pipeline.py
```

Current warehouse counts:

| Table | Rows |
|---|---:|
| FactSales | 9 |
| DimCustomer | 7 |
| DimProduct | 6 |
| DimStore | 4 |
| DimDate | 2 |
| etl_rejections | 2 |

Notes:

- The first full run loaded 9 valid sales transactions.
- Two invalid transactions were written to `etl_rejections`.
- Customer history produced 7 dimension rows from 6 source customers because one customer changed segment and loyalty tier.
- Running the same files again loads 0 new rows because file-level incremental tracking is enabled.
