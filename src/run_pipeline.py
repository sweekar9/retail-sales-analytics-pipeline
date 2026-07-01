import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_DIR / "config.json"
HIGH_DATE = "9999-12-31"


def read_config():
    with CONFIG_PATH.open() as file:
        config = json.load(file)
    return {
        key: BASE_DIR / value
        for key, value in config.items()
    }


def read_csv(path):
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def init_database(conn):
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS etl_loaded_files (
            file_name TEXT PRIMARY KEY,
            loaded_at TEXT NOT NULL,
            rows_loaded INTEGER NOT NULL,
            rows_rejected INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS etl_rejections (
            rejection_id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            transaction_id TEXT,
            reason TEXT NOT NULL,
            rejected_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS DimDate (
            date_key INTEGER PRIMARY KEY,
            full_date TEXT UNIQUE NOT NULL,
            day INTEGER NOT NULL,
            month INTEGER NOT NULL,
            month_name TEXT NOT NULL,
            quarter INTEGER NOT NULL,
            year INTEGER NOT NULL,
            day_of_week TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS DimStore (
            store_key INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT UNIQUE NOT NULL,
            store_name TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            region TEXT NOT NULL,
            opened_date TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS DimProduct (
            product_key INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT UNIQUE NOT NULL,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            brand TEXT NOT NULL,
            unit_cost REAL NOT NULL,
            current_price REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS DimCustomer (
            customer_key INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            segment TEXT NOT NULL,
            loyalty_tier TEXT NOT NULL,
            effective_start_date TEXT NOT NULL,
            effective_end_date TEXT NOT NULL,
            is_current INTEGER NOT NULL,
            UNIQUE(customer_id, effective_start_date)
        );

        CREATE TABLE IF NOT EXISTS FactSales (
            sales_key INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE NOT NULL,
            date_key INTEGER NOT NULL,
            customer_key INTEGER NOT NULL,
            product_key INTEGER NOT NULL,
            store_key INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            discount_amount REAL NOT NULL,
            gross_sales REAL NOT NULL,
            net_sales REAL NOT NULL,
            gross_margin REAL NOT NULL,
            payment_method TEXT NOT NULL,
            loaded_at TEXT NOT NULL,
            FOREIGN KEY(date_key) REFERENCES DimDate(date_key),
            FOREIGN KEY(customer_key) REFERENCES DimCustomer(customer_key),
            FOREIGN KEY(product_key) REFERENCES DimProduct(product_key),
            FOREIGN KEY(store_key) REFERENCES DimStore(store_key)
        );

        CREATE INDEX IF NOT EXISTS idx_fact_sales_date ON FactSales(date_key);
        CREATE INDEX IF NOT EXISTS idx_fact_sales_customer ON FactSales(customer_key);
        CREATE INDEX IF NOT EXISTS idx_fact_sales_product ON FactSales(product_key);
        CREATE INDEX IF NOT EXISTS idx_fact_sales_store ON FactSales(store_key);
        CREATE INDEX IF NOT EXISTS idx_dim_customer_natural_current
            ON DimCustomer(customer_id, is_current);
        """
    )


def upsert_static_dimensions(conn, raw_path):
    for row in read_csv(raw_path / "stores.csv"):
        conn.execute(
            """
            INSERT INTO DimStore (store_id, store_name, city, state, region, opened_date)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(store_id) DO UPDATE SET
                store_name = excluded.store_name,
                city = excluded.city,
                state = excluded.state,
                region = excluded.region,
                opened_date = excluded.opened_date
            """,
            (
                row["store_id"],
                row["store_name"],
                row["city"],
                row["state"],
                row["region"],
                row["opened_date"],
            ),
        )

    for row in read_csv(raw_path / "products.csv"):
        conn.execute(
            """
            INSERT INTO DimProduct
                (product_id, product_name, category, brand, unit_cost, current_price)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(product_id) DO UPDATE SET
                product_name = excluded.product_name,
                category = excluded.category,
                brand = excluded.brand,
                unit_cost = excluded.unit_cost,
                current_price = excluded.current_price
            """,
            (
                row["product_id"],
                row["product_name"],
                row["category"],
                row["brand"],
                float(row["unit_cost"]),
                float(row["current_price"]),
            ),
        )


def customer_attributes(row):
    return (
        row["first_name"],
        row["last_name"],
        row["email"],
        row["city"],
        row["state"],
        row["segment"],
        row["loyalty_tier"],
    )


def load_customer_snapshot(conn, path):
    if was_loaded(conn, path.name):
        return (0, 0)

    loaded = 0
    for row in read_csv(path):
        current = conn.execute(
            """
            SELECT customer_key, first_name, last_name, email, city, state, segment, loyalty_tier
            FROM DimCustomer
            WHERE customer_id = ? AND is_current = 1
            """,
            (row["customer_id"],),
        ).fetchone()

        if current is None:
            insert_customer(conn, row)
            loaded += 1
            continue

        existing_attrs = current[1:]
        if existing_attrs != customer_attributes(row):
            previous_end = date_minus_one(row["effective_date"])
            conn.execute(
                """
                UPDATE DimCustomer
                SET effective_end_date = ?, is_current = 0
                WHERE customer_key = ?
                """,
                (previous_end, current[0]),
            )
            insert_customer(conn, row)
            loaded += 1

    mark_loaded(conn, path.name, loaded, 0)
    return (loaded, 0)


def insert_customer(conn, row):
    conn.execute(
        """
        INSERT INTO DimCustomer (
            customer_id, first_name, last_name, email, city, state,
            segment, loyalty_tier, effective_start_date, effective_end_date, is_current
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            row["customer_id"],
            row["first_name"],
            row["last_name"],
            row["email"],
            row["city"],
            row["state"],
            row["segment"],
            row["loyalty_tier"],
            row["effective_date"],
            HIGH_DATE,
        ),
    )


def date_minus_one(date_text):
    date_obj = datetime.strptime(date_text, "%Y-%m-%d").date()
    ordinal = date_obj.toordinal() - 1
    return datetime.fromordinal(ordinal).strftime("%Y-%m-%d")


def ensure_date(conn, sale_date):
    date_obj = datetime.strptime(sale_date, "%Y-%m-%d")
    date_key = int(date_obj.strftime("%Y%m%d"))
    conn.execute(
        """
        INSERT OR IGNORE INTO DimDate
            (date_key, full_date, day, month, month_name, quarter, year, day_of_week)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            date_key,
            sale_date,
            date_obj.day,
            date_obj.month,
            date_obj.strftime("%B"),
            ((date_obj.month - 1) // 3) + 1,
            date_obj.year,
            date_obj.strftime("%A"),
        ),
    )
    return date_key


def lookup_key(conn, table, key_column, natural_column, natural_value):
    row = conn.execute(
        f"SELECT {key_column} FROM {table} WHERE {natural_column} = ?",
        (natural_value,),
    ).fetchone()
    return row[0] if row else None


def lookup_customer_key(conn, customer_id, sale_date):
    row = conn.execute(
        """
        SELECT customer_key
        FROM DimCustomer
        WHERE customer_id = ?
          AND effective_start_date <= ?
          AND effective_end_date >= ?
        ORDER BY effective_start_date DESC
        LIMIT 1
        """,
        (customer_id, sale_date, sale_date),
    ).fetchone()
    return row[0] if row else None


def validate_sale(conn, row):
    required_fields = [
        "transaction_id",
        "sale_date",
        "store_id",
        "customer_id",
        "product_id",
        "quantity",
        "unit_price",
        "discount_amount",
        "payment_method",
    ]
    for field in required_fields:
        if not row.get(field):
            return f"Missing required field: {field}"

    try:
        datetime.strptime(row["sale_date"], "%Y-%m-%d")
        quantity = int(row["quantity"])
        unit_price = float(row["unit_price"])
        discount = float(row["discount_amount"])
    except ValueError:
        return "Invalid numeric or date format"

    if quantity <= 0:
        return "Quantity must be greater than zero"
    if unit_price < 0:
        return "Unit price cannot be negative"
    if discount < 0:
        return "Discount cannot be negative"
    if discount > quantity * unit_price:
        return "Discount cannot exceed gross sales"

    if lookup_key(conn, "DimStore", "store_key", "store_id", row["store_id"]) is None:
        return "Unknown store_id"
    if lookup_key(conn, "DimProduct", "product_key", "product_id", row["product_id"]) is None:
        return "Unknown product_id"
    if lookup_customer_key(conn, row["customer_id"], row["sale_date"]) is None:
        return "Unknown customer_id for sale date"
    return None


def load_sales_file(conn, path):
    if was_loaded(conn, path.name):
        return (0, 0)

    loaded = 0
    rejected = 0
    for row in read_csv(path):
        reason = validate_sale(conn, row)
        if reason:
            reject_sale(conn, path.name, row, reason)
            rejected += 1
            continue

        sale_date = row["sale_date"]
        date_key = ensure_date(conn, sale_date)
        customer_key = lookup_customer_key(conn, row["customer_id"], sale_date)
        product_key = lookup_key(conn, "DimProduct", "product_key", "product_id", row["product_id"])
        store_key = lookup_key(conn, "DimStore", "store_key", "store_id", row["store_id"])
        product = conn.execute(
            "SELECT unit_cost FROM DimProduct WHERE product_key = ?",
            (product_key,),
        ).fetchone()

        quantity = int(row["quantity"])
        unit_price = float(row["unit_price"])
        discount = float(row["discount_amount"])
        gross_sales = quantity * unit_price
        net_sales = gross_sales - discount
        gross_margin = net_sales - (quantity * float(product[0]))

        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO FactSales (
                transaction_id, date_key, customer_key, product_key, store_key,
                quantity, unit_price, discount_amount, gross_sales, net_sales,
                gross_margin, payment_method, loaded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["transaction_id"],
                date_key,
                customer_key,
                product_key,
                store_key,
                quantity,
                unit_price,
                discount,
                round(gross_sales, 2),
                round(net_sales, 2),
                round(gross_margin, 2),
                row["payment_method"],
                utc_now(),
            ),
        )
        loaded += cursor.rowcount

    mark_loaded(conn, path.name, loaded, rejected)
    return (loaded, rejected)


def reject_sale(conn, file_name, row, reason):
    conn.execute(
        """
        INSERT INTO etl_rejections (file_name, transaction_id, reason, rejected_at)
        VALUES (?, ?, ?, ?)
        """,
        (file_name, row.get("transaction_id"), reason, utc_now()),
    )


def was_loaded(conn, file_name):
    row = conn.execute(
        "SELECT 1 FROM etl_loaded_files WHERE file_name = ?",
        (file_name,),
    ).fetchone()
    return row is not None


def mark_loaded(conn, file_name, rows_loaded, rows_rejected):
    conn.execute(
        """
        INSERT INTO etl_loaded_files (file_name, loaded_at, rows_loaded, rows_rejected)
        VALUES (?, ?, ?, ?)
        """,
        (file_name, utc_now(), rows_loaded, rows_rejected),
    )


def utc_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def fetch_dicts(conn, query):
    cursor = conn.execute(query)
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def export_marts(conn, mart_path):
    sales_trends = fetch_dicts(
        conn,
        """
        SELECT
            d.full_date,
            s.region,
            SUM(f.quantity) AS units_sold,
            ROUND(SUM(f.net_sales), 2) AS net_sales,
            ROUND(SUM(f.gross_margin), 2) AS gross_margin
        FROM FactSales f
        JOIN DimDate d ON f.date_key = d.date_key
        JOIN DimStore s ON f.store_key = s.store_key
        GROUP BY d.full_date, s.region
        ORDER BY d.full_date, s.region
        """,
    )
    write_csv(
        mart_path / "sales_trends.csv",
        sales_trends,
        ["full_date", "region", "units_sold", "net_sales", "gross_margin"],
    )

    customer_segments = fetch_dicts(
        conn,
        """
        SELECT
            c.segment,
            c.loyalty_tier,
            COUNT(DISTINCT c.customer_id) AS customers,
            ROUND(SUM(f.net_sales), 2) AS net_sales,
            ROUND(AVG(f.net_sales), 2) AS avg_transaction_value
        FROM FactSales f
        JOIN DimCustomer c ON f.customer_key = c.customer_key
        GROUP BY c.segment, c.loyalty_tier
        ORDER BY net_sales DESC
        """,
    )
    write_csv(
        mart_path / "customer_segments.csv",
        customer_segments,
        ["segment", "loyalty_tier", "customers", "net_sales", "avg_transaction_value"],
    )

    inventory_analysis = fetch_dicts(
        conn,
        """
        SELECT
            p.category,
            p.product_name,
            SUM(f.quantity) AS units_sold,
            ROUND(SUM(f.net_sales), 2) AS net_sales,
            ROUND(SUM(f.gross_margin), 2) AS gross_margin
        FROM FactSales f
        JOIN DimProduct p ON f.product_key = p.product_key
        GROUP BY p.category, p.product_name
        ORDER BY units_sold DESC
        """,
    )
    write_csv(
        mart_path / "inventory_analysis.csv",
        inventory_analysis,
        ["category", "product_name", "units_sold", "net_sales", "gross_margin"],
    )


def run():
    config = read_config()
    config["warehouse_path"].parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(config["warehouse_path"]) as conn:
        init_database(conn)
        upsert_static_dimensions(conn, config["raw_data_path"])

        summary = []
        for path in sorted(config["raw_data_path"].glob("customers_*.csv")):
            loaded, rejected = load_customer_snapshot(conn, path)
            summary.append((path.name, loaded, rejected))

        for path in sorted(config["raw_data_path"].glob("sales_*.csv")):
            loaded, rejected = load_sales_file(conn, path)
            summary.append((path.name, loaded, rejected))

        export_marts(conn, config["mart_output_path"])

        print("ETL run complete")
        for file_name, loaded, rejected in summary:
            print(f"{file_name}: loaded={loaded}, rejected={rejected}")
        print(f"Warehouse: {config['warehouse_path']}")
        print(f"Marts: {config['mart_output_path']}")


if __name__ == "__main__":
    run()
