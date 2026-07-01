IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'retail_dw')
    EXEC('CREATE SCHEMA retail_dw');
GO

CREATE TABLE retail_dw.DimDate (
    date_key INT NOT NULL PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    [day] TINYINT NOT NULL,
    [month] TINYINT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    [quarter] TINYINT NOT NULL,
    [year] SMALLINT NOT NULL,
    day_of_week VARCHAR(20) NOT NULL
);
GO

CREATE TABLE retail_dw.DimStore (
    store_key BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    store_id VARCHAR(20) NOT NULL UNIQUE,
    store_name VARCHAR(100) NOT NULL,
    city VARCHAR(80) NOT NULL,
    [state] VARCHAR(20) NOT NULL,
    region VARCHAR(40) NOT NULL,
    opened_date DATE NOT NULL
);
GO

CREATE TABLE retail_dw.DimProduct (
    product_key BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    product_id VARCHAR(20) NOT NULL UNIQUE,
    product_name VARCHAR(120) NOT NULL,
    category VARCHAR(80) NOT NULL,
    brand VARCHAR(80) NOT NULL,
    unit_cost DECIMAL(12, 2) NOT NULL,
    current_price DECIMAL(12, 2) NOT NULL
);
GO

CREATE TABLE retail_dw.DimCustomer (
    customer_key BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    customer_id VARCHAR(20) NOT NULL,
    first_name VARCHAR(80) NOT NULL,
    last_name VARCHAR(80) NOT NULL,
    email VARCHAR(160) NOT NULL,
    city VARCHAR(80) NOT NULL,
    [state] VARCHAR(20) NOT NULL,
    segment VARCHAR(60) NOT NULL,
    loyalty_tier VARCHAR(40) NOT NULL,
    effective_start_date DATE NOT NULL,
    effective_end_date DATE NOT NULL CONSTRAINT df_dim_customer_end DEFAULT ('9999-12-31'),
    is_current BIT NOT NULL CONSTRAINT df_dim_customer_current DEFAULT (1),
    CONSTRAINT uq_dim_customer_version UNIQUE (customer_id, effective_start_date)
);
GO

CREATE TABLE retail_dw.FactSales (
    sales_key BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    transaction_id VARCHAR(40) NOT NULL UNIQUE,
    date_key INT NOT NULL REFERENCES retail_dw.DimDate(date_key),
    customer_key BIGINT NOT NULL REFERENCES retail_dw.DimCustomer(customer_key),
    product_key BIGINT NOT NULL REFERENCES retail_dw.DimProduct(product_key),
    store_key BIGINT NOT NULL REFERENCES retail_dw.DimStore(store_key),
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(12, 2) NOT NULL CHECK (unit_price >= 0),
    discount_amount DECIMAL(12, 2) NOT NULL CHECK (discount_amount >= 0),
    gross_sales DECIMAL(12, 2) NOT NULL,
    net_sales DECIMAL(12, 2) NOT NULL,
    gross_margin DECIMAL(12, 2) NOT NULL,
    payment_method VARCHAR(40) NOT NULL,
    loaded_at DATETIME2 NOT NULL CONSTRAINT df_fact_sales_loaded DEFAULT (SYSUTCDATETIME())
);
GO

CREATE INDEX idx_fact_sales_date ON retail_dw.FactSales(date_key);
CREATE INDEX idx_fact_sales_customer ON retail_dw.FactSales(customer_key);
CREATE INDEX idx_fact_sales_product ON retail_dw.FactSales(product_key);
CREATE INDEX idx_fact_sales_store ON retail_dw.FactSales(store_key);
CREATE INDEX idx_fact_sales_date_store ON retail_dw.FactSales(date_key, store_key);
CREATE INDEX idx_dim_customer_current ON retail_dw.DimCustomer(customer_id, is_current);
CREATE INDEX idx_dim_product_category ON retail_dw.DimProduct(category);
CREATE INDEX idx_dim_store_region ON retail_dw.DimStore(region);
GO
