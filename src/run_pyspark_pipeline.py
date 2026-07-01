"""Spark version of the retail sales pipeline.

The main pipeline in src/run_pipeline.py is easier to run locally because it
uses SQLite and Python's standard library. This version keeps the same source
files but writes staging tables through JDBC for a larger warehouse setup.
"""

import os
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def main():
    spark = (
        SparkSession.builder
        .appName("RetailSalesAnalyticsPipeline")
        .getOrCreate()
    )

    raw_path = "data/raw"
    jdbc_url = os.getenv("RETAIL_JDBC_URL", "jdbc:postgresql://localhost:5432/retail_analytics")
    jdbc_props = {
        "user": os.getenv("RETAIL_DB_USER", "retail_user"),
        "password": os.getenv("RETAIL_DB_PASSWORD", ""),
        "driver": os.getenv("RETAIL_JDBC_DRIVER", "org.postgresql.Driver"),
    }

    products = spark.read.option("header", True).csv(f"{raw_path}/products.csv")
    stores = spark.read.option("header", True).csv(f"{raw_path}/stores.csv")
    customers = spark.read.option("header", True).csv(f"{raw_path}/customers_*.csv")
    sales = spark.read.option("header", True).csv(f"{raw_path}/sales_*.csv")

    clean_sales = (
        sales
        .withColumn("quantity", F.col("quantity").cast("int"))
        .withColumn("unit_price", F.col("unit_price").cast("double"))
        .withColumn("discount_amount", F.col("discount_amount").cast("double"))
        .withColumn("sale_date", F.to_date("sale_date"))
        .filter(F.col("quantity") > 0)
        .filter(F.col("unit_price") >= 0)
        .filter(F.col("discount_amount") >= 0)
    )

    fact_sales = (
        clean_sales
        .join(products.select("product_id", "unit_cost"), "product_id")
        .withColumn("date_key", F.date_format("sale_date", "yyyyMMdd").cast("int"))
        .withColumn("gross_sales", F.round(F.col("quantity") * F.col("unit_price"), 2))
        .withColumn("net_sales", F.round(F.col("gross_sales") - F.col("discount_amount"), 2))
        .withColumn(
            "gross_margin",
            F.round(F.col("net_sales") - (F.col("quantity") * F.col("unit_cost").cast("double")), 2),
        )
    )

    products.write.jdbc(jdbc_url, "DimProduct_stage", mode="overwrite", properties=jdbc_props)
    stores.write.jdbc(jdbc_url, "DimStore_stage", mode="overwrite", properties=jdbc_props)
    customers.write.jdbc(jdbc_url, "DimCustomer_snapshot_stage", mode="overwrite", properties=jdbc_props)
    fact_sales.write.jdbc(jdbc_url, "FactSales_stage", mode="overwrite", properties=jdbc_props)

    spark.stop()


if __name__ == "__main__":
    main()
