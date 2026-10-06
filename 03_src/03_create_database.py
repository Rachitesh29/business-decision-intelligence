from pathlib import Path
import sqlite3
import pandas as pd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_FOLDER = PROJECT_ROOT / "01_data" / "raw"
SQL_FOLDER = PROJECT_ROOT / "04_sql"

SQL_FOLDER.mkdir(exist_ok=True)

DATABASE_PATH = SQL_FOLDER / "business_intelligence.db"


# ============================================================
# 2. DATASET FILES
# ============================================================

files = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv"
}


# ============================================================
# 3. LOAD DATASETS
# ============================================================

data = {}

print("=" * 70)
print("LOADING DATASETS")
print("=" * 70)

for table_name, file_name in files.items():

    file_path = RAW_FOLDER / file_name

    df = pd.read_csv(file_path)

    # Remove exact duplicate rows
    df = df.drop_duplicates()

    data[table_name] = df

    print(
        f"{table_name:<22} "
        f"rows={df.shape[0]:>8} "
        f"columns={df.shape[1]:>3}"
    )


# ============================================================
# 4. CLEAN ORDERS
# ============================================================

orders = data["orders"].copy()

date_columns = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date"
]

for column in date_columns:
    orders[column] = pd.to_datetime(
        orders[column],
        errors="coerce"
    )


# ============================================================
# 5. CREATE DELIVERY METRICS
# ============================================================

orders["is_delivered"] = (
    orders["order_status"] == "delivered"
)


orders["delivery_days"] = (
    orders["order_delivered_customer_date"]
    - orders["order_purchase_timestamp"]
).dt.total_seconds() / (60 * 60 * 24)


orders["delivery_delay_days"] = (
    orders["order_delivered_customer_date"]
    - orders["order_estimated_delivery_date"]
).dt.total_seconds() / (60 * 60 * 24)


orders["delivery_performance"] = pd.NA

orders.loc[
    orders["delivery_delay_days"] < 0,
    "delivery_performance"
] = "Early"

orders.loc[
    orders["delivery_delay_days"] == 0,
    "delivery_performance"
] = "On Time"

orders.loc[
    orders["delivery_delay_days"] > 0,
    "delivery_performance"
] = "Late"


data["orders"] = orders


# ============================================================
# 6. CONVERT NUMERIC COLUMNS
# ============================================================

numeric_columns = {
    "geolocation": [
        "geolocation_zip_code_prefix",
        "geolocation_lat",
        "geolocation_lng"
    ],

    "order_items": [
        "order_item_id",
        "price",
        "freight_value"
    ],

    "payments": [
        "payment_sequential",
        "payment_installments",
        "payment_value"
    ],

    "reviews": [
        "review_score"
    ],

    "products": [
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm"
    ]
}

for table_name, columns in numeric_columns.items():

    df = data[table_name].copy()

    for column in columns:

        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    data[table_name] = df


# ============================================================
# 7. RELATIONSHIP VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("RELATIONSHIP VALIDATION")
print("=" * 70)

checks = {
    "order_items -> orders": (
        data["order_items"]["order_id"]
        .isin(data["orders"]["order_id"])
    ),

    "orders -> customers": (
        data["orders"]["customer_id"]
        .isin(data["customers"]["customer_id"])
    ),

    "order_items -> products": (
        data["order_items"]["product_id"]
        .isin(data["products"]["product_id"])
    ),

    "order_items -> sellers": (
        data["order_items"]["seller_id"]
        .isin(data["sellers"]["seller_id"])
    ),

    "payments -> orders": (
        data["payments"]["order_id"]
        .isin(data["orders"]["order_id"])
    ),

    "reviews -> orders": (
        data["reviews"]["order_id"]
        .isin(data["orders"]["order_id"])
    )
}

for relationship, check in checks.items():

    unmatched = (~check).sum()

    if unmatched == 0:
        print(f"{relationship:<30} PASS")
    else:
        print(
            f"{relationship:<30} "
            f"FAIL - {unmatched} unmatched"
        )


# ============================================================
# 8. CONNECT TO SQLITE
# ============================================================

print("\n" + "=" * 70)
print("CREATING SQLITE DATABASE")
print("=" * 70)

if DATABASE_PATH.exists():
    DATABASE_PATH.unlink()

connection = sqlite3.connect(DATABASE_PATH)


# ============================================================
# 9. LOAD DATAFRAMES INTO SQL TABLES
# ============================================================

for table_name, df in data.items():

    df.to_sql(
        table_name,
        connection,
        if_exists="replace",
        index=False
    )

    print(
        f"Created table: {table_name:<22} "
        f"rows={len(df):>8}"
    )


# ============================================================
# 10. VERIFY TABLES
# ============================================================

print("\n" + "=" * 70)
print("DATABASE VERIFICATION")
print("=" * 70)

tables = pd.read_sql_query(
    """
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
    """,
    connection
)

print("\nTables created:")
print(tables)


# ============================================================
# 11. VERIFY ONE TABLE
# ============================================================

orders_check = pd.read_sql_query(
    """
    SELECT *
    FROM orders
    LIMIT 5
    """,
    connection
)

print("\nSample rows from orders table:")
print(orders_check)


# ============================================================
# 12. CLOSE DATABASE
# ============================================================

connection.close()


print("\n" + "=" * 70)
print("DATABASE CREATION COMPLETE")
print("=" * 70)

print("\nDatabase created at:")
print(DATABASE_PATH)