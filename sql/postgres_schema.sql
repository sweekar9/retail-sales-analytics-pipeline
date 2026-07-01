CREATE SCHEMA IF NOT EXISTS retail_dw;
SET search_path TO retail_dw;

CREATE TABLE IF NOT EXISTS DimDate (
    date_key INTEGER PRIMARY KEY,
    full_date DATE UNIQUE NOT NULL,
    day SMALLINT NOT NULL,
    month SMALLINT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    quarter SMALLINT NOT NULL,
    year SMALLINT NOT NULL,
    day_of_week VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS DimStore (
    store_key BIGSERIAL PRIMARY KEY,
    store_id VARCHAR(20) UNIQUE NOT NULL,
    store_name VARCHAR(100) NOT NULL,
    city VARCHAR(80) NOT NULL,
    state VARCHAR(20) NOT NULL,
    region VARCHAR(40) NOT NULL,
    opened_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS DimProduct (
    product_key BIGSERIAL PRIMARY KEY,
    product_id VARCHAR(20) UNIQUE NOT NULL,
    product_name VARCHAR(120) NOT NULL,
    category VARCHAR(80) NOT NULL,
    brand VARCHAR(80) NOT NULL,
    unit_cost NUMERIC(12, 2) NOT NULL,
    current_price NUMERIC(12, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS DimCustomer (
    customer_key BIGSERIAL PRIMARY KEY,
    customer_id VARCHAR(20) NOT NULL,
    first_name VARCHAR(80) NOT NULL,
    last_name VARCHAR(80) NOT NULL,
    email VARCHAR(160) NOT NULL,
    city VARCHAR(80) NOT NULL,
    state VARCHAR(20) NOT NULL,
    segment VARCHAR(60) NOT NULL,
    loyalty_tier VARCHAR(40) NOT NULL,
    effective_start_date DATE NOT NULL,
    effective_end_date DATE NOT NULL DEFAULT DATE '9999-12-31',
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_dim_customer_version UNIQUE (customer_id, effective_start_date)
);

CREATE TABLE IF NOT EXISTS FactSales (
    sales_key BIGSERIAL PRIMARY KEY,
    transaction_id VARCHAR(40) UNIQUE NOT NULL,
    date_key INTEGER NOT NULL REFERENCES DimDate(date_key),
    customer_key BIGINT NOT NULL REFERENCES DimCustomer(customer_key),
    product_key BIGINT NOT NULL REFERENCES DimProduct(product_key),
    store_key BIGINT NOT NULL REFERENCES DimStore(store_key),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
    discount_amount NUMERIC(12, 2) NOT NULL CHECK (discount_amount >= 0),
    gross_sales NUMERIC(12, 2) NOT NULL,
    net_sales NUMERIC(12, 2) NOT NULL,
    gross_margin NUMERIC(12, 2) NOT NULL,
    payment_method VARCHAR(40) NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_sales_date ON FactSales(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_customer ON FactSales(customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_product ON FactSales(product_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_store ON FactSales(store_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_date_store ON FactSales(date_key, store_key);
CREATE INDEX IF NOT EXISTS idx_dim_customer_current ON DimCustomer(customer_id, is_current);
CREATE INDEX IF NOT EXISTS idx_dim_product_category ON DimProduct(category);
CREATE INDEX IF NOT EXISTS idx_dim_store_region ON DimStore(region);
