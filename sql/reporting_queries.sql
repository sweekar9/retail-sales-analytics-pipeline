-- Sales trends by date and region
SELECT
    d.full_date,
    s.region,
    SUM(f.quantity) AS units_sold,
    SUM(f.net_sales) AS net_sales,
    SUM(f.gross_margin) AS gross_margin
FROM FactSales f
JOIN DimDate d ON f.date_key = d.date_key
JOIN DimStore s ON f.store_key = s.store_key
GROUP BY d.full_date, s.region
ORDER BY d.full_date, s.region;

-- Customer segmentation
SELECT
    c.segment,
    c.loyalty_tier,
    COUNT(DISTINCT c.customer_id) AS customers,
    SUM(f.net_sales) AS net_sales,
    AVG(f.net_sales) AS avg_transaction_value
FROM FactSales f
JOIN DimCustomer c ON f.customer_key = c.customer_key
GROUP BY c.segment, c.loyalty_tier
ORDER BY net_sales DESC;

-- Inventory and product performance
SELECT
    p.category,
    p.product_name,
    SUM(f.quantity) AS units_sold,
    SUM(f.net_sales) AS net_sales,
    SUM(f.gross_margin) AS gross_margin
FROM FactSales f
JOIN DimProduct p ON f.product_key = p.product_key
GROUP BY p.category, p.product_name
ORDER BY units_sold DESC;
