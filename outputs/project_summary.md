# Retail Sales Analytics Pipeline

Built deliverables:

- `retail_sales_analytics_pipeline_project.zip`: complete source project with sample data, ETL code, SQL scripts, PySpark reference code, and Power BI guide.
- `retail_sales_warehouse.sqlite`: local demo warehouse with star schema tables.
- `marts/sales_trends.csv`: Power BI-ready sales trend data.
- `marts/customer_segments.csv`: Power BI-ready customer segmentation data.
- `marts/inventory_analysis.csv`: Power BI-ready product and inventory performance data.

Verification results:

- First ETL run loaded 9 valid sales facts.
- 2 invalid sales records were rejected and logged.
- Customer type-2 history created 7 customer dimension rows from 6 natural customers.
- Second ETL run loaded 0 new rows, confirming incremental file tracking works.

Warehouse row counts:

| Table | Rows |
|---|---:|
| FactSales | 9 |
| DimCustomer | 7 |
| DimProduct | 6 |
| DimStore | 4 |
| DimDate | 2 |
| etl_rejections | 2 |
