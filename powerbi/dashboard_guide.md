# Power BI Dashboard Guide

Use the CSV files generated in `outputs/marts` as import sources:

- `sales_trends.csv`
- `customer_segments.csv`
- `inventory_analysis.csv`

## Page 1: Sales Trends

Recommended visuals:

- Line chart: `full_date` by `net_sales`
- Clustered column chart: `region` by `units_sold`
- Card: total `net_sales`
- Card: total `gross_margin`
- Slicer: `region`

Business questions:

- Which regions are driving daily sales?
- Are margins moving with revenue?
- Which regions need closer operational review?

## Page 2: Customer Segmentation

Recommended visuals:

- Bar chart: `segment` by `net_sales`
- Matrix: `segment`, `loyalty_tier`, `customers`, `avg_transaction_value`
- Donut chart: `loyalty_tier` by `customers`

Business questions:

- Which customer segments contribute the most revenue?
- Which loyalty tiers have higher transaction value?
- Did customer segment changes affect sales attribution?

## Page 3: Inventory Analysis

Recommended visuals:

- Bar chart: `product_name` by `units_sold`
- Scatter chart: `net_sales` versus `gross_margin`
- Table: `category`, `product_name`, `units_sold`, `gross_margin`
- Slicer: `category`

Business questions:

- Which products are top sellers?
- Which products sell well but have low margin?
- Which categories need pricing or stocking attention?
