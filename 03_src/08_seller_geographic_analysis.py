from pathlib import Path
import sqlite3
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DB_PATH = PROJECT_ROOT / "04_sql" / "business_intelligence.db"
OUTPUT_DIR = PROJECT_ROOT / "01_data"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# DATABASE CONNECTION
# ============================================================

print("=" * 70)
print("SELLER & GEOGRAPHIC ANALYTICS")
print("=" * 70)

print(f"\nDatabase: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)


# ============================================================
# 1. LOAD REQUIRED TABLES
# ============================================================

print("\nLoading data...")

orders = pd.read_sql_query(
    """
    SELECT
        order_id,
        customer_id,
        order_status,
        order_purchase_timestamp,
        order_delivered_customer_date,
        order_estimated_delivery_date,
        delivery_days,
        delivery_delay_days,
        delivery_performance,
        is_delivered
    FROM orders
    """,
    conn
)

customers = pd.read_sql_query(
    """
    SELECT
        customer_id,
        customer_unique_id,
        customer_zip_code_prefix,
        customer_city,
        customer_state
    FROM customers
    """,
    conn
)

order_items = pd.read_sql_query(
    """
    SELECT
        order_id,
        order_item_id,
        product_id,
        seller_id,
        price,
        freight_value
    FROM order_items
    """,
    conn
)

sellers = pd.read_sql_query(
    """
    SELECT
        seller_id,
        seller_zip_code_prefix,
        seller_city,
        seller_state
    FROM sellers
    """,
    conn
)

payments = pd.read_sql_query(
    """
    SELECT
        order_id,
        payment_value
    FROM payments
    """,
    conn
)

conn.close()

print(f"Orders:       {orders.shape}")
print(f"Customers:    {customers.shape}")
print(f"Order items:  {order_items.shape}")
print(f"Sellers:      {sellers.shape}")
print(f"Payments:     {payments.shape}")


# ============================================================
# 2. BASIC TYPE CONVERSION
# ============================================================

orders["order_purchase_timestamp"] = pd.to_datetime(
    orders["order_purchase_timestamp"],
    errors="coerce"
)

orders["order_delivered_customer_date"] = pd.to_datetime(
    orders["order_delivered_customer_date"],
    errors="coerce"
)

orders["order_estimated_delivery_date"] = pd.to_datetime(
    orders["order_estimated_delivery_date"],
    errors="coerce"
)

order_items["price"] = pd.to_numeric(
    order_items["price"],
    errors="coerce"
)

order_items["freight_value"] = pd.to_numeric(
    order_items["freight_value"],
    errors="coerce"
)

payments["payment_value"] = pd.to_numeric(
    payments["payment_value"],
    errors="coerce"
)


# ============================================================
# 3. KEEP DELIVERED ORDERS FOR PERFORMANCE ANALYSIS
# ============================================================

delivered_orders = orders[
    orders["order_status"].eq("delivered")
].copy()

print("\nDelivered orders:", len(delivered_orders))


# ============================================================
# 4. DELIVERED ORDER ITEMS
# ============================================================

delivered_order_ids = set(delivered_orders["order_id"])

delivered_items = order_items[
    order_items["order_id"].isin(delivered_order_ids)
].copy()

print("Delivered order items:", len(delivered_items))


# ============================================================
# 5. SELLER PERFORMANCE
# ============================================================

print("\n" + "=" * 70)
print("SELLER PERFORMANCE")
print("=" * 70)

seller_analysis = (
    delivered_items
    .groupby("seller_id")
    .agg(
        items_sold=("order_item_id", "count"),
        unique_orders=("order_id", "nunique"),
        unique_products=("product_id", "nunique"),
        sales=("price", "sum"),
        freight_revenue=("freight_value", "sum")
    )
    .reset_index()
)

seller_analysis["avg_item_price"] = (
    seller_analysis["sales"]
    / seller_analysis["items_sold"]
)

seller_analysis["sales_per_seller_order"] = (
    seller_analysis["sales"]
    / seller_analysis["unique_orders"]
)

seller_analysis["freight_to_sales_pct"] = (
    seller_analysis["freight_revenue"]
    / seller_analysis["sales"]
    * 100
)

seller_analysis = seller_analysis.merge(
    sellers,
    on="seller_id",
    how="left"
)

seller_analysis = seller_analysis.sort_values(
    "sales",
    ascending=False
).reset_index(drop=True)

seller_analysis["sales_rank"] = (
    seller_analysis.index + 1
)

total_seller_sales = seller_analysis["sales"].sum()

seller_analysis["sales_contribution_pct"] = (
    seller_analysis["sales"]
    / total_seller_sales
    * 100
)

print("\nTop 10 sellers by delivered sales:\n")

print(
    seller_analysis[
        [
            "seller_id",
            "seller_state",
            "unique_orders",
            "items_sold",
            "sales",
            "avg_item_price",
            "sales_per_seller_order"
        ]
    ]
    .head(10)
    .to_string(index=False)
)


# ============================================================
# 6. SELLER CONCENTRATION
# ============================================================

print("\n" + "=" * 70)
print("SELLER CONCENTRATION")
print("=" * 70)

top_10_sales_share = (
    seller_analysis
    .head(10)["sales"]
    .sum()
    / total_seller_sales
    * 100
)

top_20_sales_share = (
    seller_analysis
    .head(20)["sales"]
    .sum()
    / total_seller_sales
    * 100
)

top_50_sales_share = (
    seller_analysis
    .head(50)["sales"]
    .sum()
    / total_seller_sales
    * 100
)

concentration_summary = pd.DataFrame(
    {
        "seller_group": [
            "Top 10",
            "Top 20",
            "Top 50"
        ],
        "sales_share_pct": [
            top_10_sales_share,
            top_20_sales_share,
            top_50_sales_share
        ]
    }
)

print("\nSeller sales concentration:\n")
print(concentration_summary.to_string(index=False))


# ============================================================
# 7. CUSTOMER STATE ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("CUSTOMER GEOGRAPHIC ANALYSIS")
print("=" * 70)

delivered_customer_orders = delivered_orders.merge(
    customers[
        [
            "customer_id",
            "customer_unique_id",
            "customer_city",
            "customer_state"
        ]
    ],
    on="customer_id",
    how="left"
)


# ------------------------------------------------------------
# Aggregate payments at ORDER level first
# This prevents multiple payment rows from duplicating sales.
# ------------------------------------------------------------

order_payment_totals = (
    payments
    .groupby("order_id", as_index=False)
    .agg(
        order_payment_value=("payment_value", "sum")
    )
)

delivered_customer_orders = delivered_customer_orders.merge(
    order_payment_totals,
    on="order_id",
    how="left"
)

delivered_customer_orders["order_payment_value"] = (
    delivered_customer_orders["order_payment_value"]
    .fillna(0)
)


customer_state_analysis = (
    delivered_customer_orders
    .groupby("customer_state")
    .agg(
        customers=("customer_unique_id", "nunique"),
        orders=("order_id", "nunique"),
        sales=("order_payment_value", "sum")
    )
    .reset_index()
)

customer_state_analysis["orders_per_customer"] = (
    customer_state_analysis["orders"]
    / customer_state_analysis["customers"]
)

customer_state_analysis["aov"] = (
    customer_state_analysis["sales"]
    / customer_state_analysis["orders"]
)

customer_state_analysis = customer_state_analysis.sort_values(
    "sales",
    ascending=False
).reset_index(drop=True)

customer_state_analysis["sales_contribution_pct"] = (
    customer_state_analysis["sales"]
    / customer_state_analysis["sales"].sum()
    * 100
)

print("\nCustomer state performance:\n")

print(
    customer_state_analysis[
        [
            "customer_state",
            "customers",
            "orders",
            "sales",
            "aov",
            "sales_contribution_pct"
        ]
    ]
    .head(15)
    .to_string(index=False)
)


# ============================================================
# 8. CUSTOMER CITY ANALYSIS
# ============================================================

customer_city_analysis = (
    delivered_customer_orders
    .groupby(
        [
            "customer_state",
            "customer_city"
        ]
    )
    .agg(
        customers=("customer_unique_id", "nunique"),
        orders=("order_id", "nunique"),
        sales=("order_payment_value", "sum")
    )
    .reset_index()
)

customer_city_analysis["aov"] = (
    customer_city_analysis["sales"]
    / customer_city_analysis["orders"]
)

customer_city_analysis = customer_city_analysis.sort_values(
    "sales",
    ascending=False
).reset_index(drop=True)

print("\nTop 20 customer cities by sales:\n")

print(
    customer_city_analysis.head(20).to_string(index=False)
)


# ============================================================
# 9. SELLER STATE ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("SELLER GEOGRAPHIC ANALYSIS")
print("=" * 70)

seller_state_base = delivered_items.merge(
    sellers[
        [
            "seller_id",
            "seller_city",
            "seller_state"
        ]
    ],
    on="seller_id",
    how="left"
)

seller_state_analysis = (
    seller_state_base
    .groupby("seller_state")
    .agg(
        sellers=("seller_id", "nunique"),
        seller_orders=("order_id", "nunique"),
        items_sold=("order_item_id", "count"),
        sales=("price", "sum"),
        freight_value=("freight_value", "sum")
    )
    .reset_index()
)

seller_state_analysis["avg_item_price"] = (
    seller_state_analysis["sales"]
    / seller_state_analysis["items_sold"]
)

seller_state_analysis["sales_per_seller_order"] = (
    seller_state_analysis["sales"]
    / seller_state_analysis["seller_orders"]
)

seller_state_analysis["freight_to_sales_pct"] = (
    seller_state_analysis["freight_value"]
    / seller_state_analysis["sales"]
    * 100
)

seller_state_analysis["sales_contribution_pct"] = (
    seller_state_analysis["sales"]
    / seller_state_analysis["sales"].sum()
    * 100
)

seller_state_analysis = seller_state_analysis.sort_values(
    "sales",
    ascending=False
).reset_index(drop=True)

print("\nSeller state performance:\n")

print(
    seller_state_analysis.to_string(index=False)
)


# ============================================================
# 10. STATE-LEVEL DELIVERY PERFORMANCE
# ============================================================

print("\n" + "=" * 70)
print("STATE-LEVEL DELIVERY PERFORMANCE")
print("=" * 70)

state_delivery_analysis = (
    delivered_customer_orders
    .groupby("customer_state")
    .agg(
        delivered_orders=("order_id", "nunique"),
        avg_delivery_days=("delivery_days", "mean"),
        median_delivery_days=("delivery_days", "median"),
        avg_delivery_delay_days=("delivery_delay_days", "mean"),
        late_orders=(
            "delivery_performance",
            lambda x: (x == "Late").sum()
        ),
        early_orders=(
            "delivery_performance",
            lambda x: (x == "Early").sum()
        ),
        on_time_orders=(
            "delivery_performance",
            lambda x: (x == "On Time").sum()
        )
    )
    .reset_index()
)

state_delivery_analysis["late_rate_pct"] = (
    state_delivery_analysis["late_orders"]
    / state_delivery_analysis["delivered_orders"]
    * 100
)

state_delivery_analysis["early_rate_pct"] = (
    state_delivery_analysis["early_orders"]
    / state_delivery_analysis["delivered_orders"]
    * 100
)

state_delivery_analysis["on_time_rate_pct"] = (
    state_delivery_analysis["on_time_orders"]
    / state_delivery_analysis["delivered_orders"]
    * 100
)

state_delivery_analysis = state_delivery_analysis.sort_values(
    "avg_delivery_days",
    ascending=False
).reset_index(drop=True)

print("\nStates with longest average delivery time:\n")

print(
    state_delivery_analysis[
        [
            "customer_state",
            "delivered_orders",
            "avg_delivery_days",
            "median_delivery_days",
            "late_rate_pct",
            "on_time_rate_pct",
            "early_rate_pct"
        ]
    ]
    .head(15)
    .to_string(index=False)
)


# ============================================================
# 11. TOP STATES BY LATE DELIVERY RATE
# ============================================================

print("\nTop states by late-delivery rate (minimum 100 delivered orders):\n")

late_delivery_states = (
    state_delivery_analysis[
        state_delivery_analysis["delivered_orders"] >= 100
    ]
    .sort_values(
        "late_rate_pct",
        ascending=False
    )
)

print(
    late_delivery_states[
        [
            "customer_state",
            "delivered_orders",
            "avg_delivery_days",
            "late_rate_pct"
        ]
    ]
    .head(15)
    .to_string(index=False)
)


# ============================================================
# 12. SELLER PERFORMANCE BY STATE
# ============================================================

seller_state_city_analysis = (
    seller_state_base
    .groupby(
        [
            "seller_state",
            "seller_city"
        ]
    )
    .agg(
        sellers=("seller_id", "nunique"),
        seller_orders=("order_id", "nunique"),
        items_sold=("order_item_id", "count"),
        sales=("price", "sum"),
        freight_value=("freight_value", "sum")
    )
    .reset_index()
)

seller_state_city_analysis["avg_item_price"] = (
    seller_state_city_analysis["sales"]
    / seller_state_city_analysis["items_sold"]
)

seller_state_city_analysis["sales_contribution_pct"] = (
    seller_state_city_analysis["sales"]
    / seller_state_city_analysis["sales"].sum()
    * 100
)

seller_state_city_analysis = seller_state_city_analysis.sort_values(
    "sales",
    ascending=False
).reset_index(drop=True)


# ============================================================
# 13. SELLER ORDER PARTICIPATION
# ============================================================

seller_order_participation = (
    delivered_items
    .groupby("seller_id")
    .agg(
        unique_orders=("order_id", "nunique"),
        unique_products=("product_id", "nunique"),
        items_sold=("order_item_id", "count")
    )
    .reset_index()
)

seller_order_participation = seller_order_participation.merge(
    sellers,
    on="seller_id",
    how="left"
)

seller_order_participation = seller_order_participation.sort_values(
    "unique_orders",
    ascending=False
).reset_index(drop=True)


# ============================================================
# 14. VALIDATION CHECKS
# ============================================================

print("\n" + "=" * 70)
print("VALIDATION")
print("=" * 70)

print(
    "\nSeller analysis rows:",
    len(seller_analysis)
)

print(
    "Customer state rows:",
    len(customer_state_analysis)
)

print(
    "Seller state rows:",
    len(seller_state_analysis)
)

print(
    "Delivery state rows:",
    len(state_delivery_analysis)
)

print(
    "\nMissing seller IDs:",
    seller_analysis["seller_id"].isna().sum()
)

print(
    "Missing customer states:",
    delivered_customer_orders["customer_state"].isna().sum()
)

print(
    "Missing seller states:",
    seller_state_base["seller_state"].isna().sum()
)

print(
    "\nTotal seller sales:",
    round(seller_analysis["sales"].sum(), 2)
)

print(
    "Total delivered item sales:",
    round(delivered_items["price"].sum(), 2)
)

print(
    "Difference:",
    round(
        seller_analysis["sales"].sum()
        - delivered_items["price"].sum(),
        2
    )
)


# ============================================================
# 15. SAVE POWER BI-READY OUTPUTS
# ============================================================

print("\n" + "=" * 70)
print("SAVING OUTPUTS")
print("=" * 70)

seller_analysis.to_csv(
    OUTPUT_DIR / "seller_analysis.csv",
    index=False
)

concentration_summary.to_csv(
    OUTPUT_DIR / "seller_concentration.csv",
    index=False
)

customer_state_analysis.to_csv(
    OUTPUT_DIR / "customer_state_analysis.csv",
    index=False
)

customer_city_analysis.to_csv(
    OUTPUT_DIR / "customer_city_analysis.csv",
    index=False
)

seller_state_analysis.to_csv(
    OUTPUT_DIR / "seller_state_analysis.csv",
    index=False
)

seller_state_city_analysis.to_csv(
    OUTPUT_DIR / "seller_state_city_analysis.csv",
    index=False
)

state_delivery_analysis.to_csv(
    OUTPUT_DIR / "state_delivery_analysis.csv",
    index=False
)

seller_order_participation.to_csv(
    OUTPUT_DIR / "seller_order_participation.csv",
    index=False
)


# ============================================================
# 16. FINAL SUMMARY
# ============================================================

print("\nSaved files:")

output_files = [
    "seller_analysis.csv",
    "seller_concentration.csv",
    "customer_state_analysis.csv",
    "customer_city_analysis.csv",
    "seller_state_analysis.csv",
    "seller_state_city_analysis.csv",
    "state_delivery_analysis.csv",
    "seller_order_participation.csv"
]

for filename in output_files:
    print(f"  ✓ 01_data/{filename}")


print("\n" + "=" * 70)
print("SELLER & GEOGRAPHIC ANALYTICS COMPLETE")
print("=" * 70)