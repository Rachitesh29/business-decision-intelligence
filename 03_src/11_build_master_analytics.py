from pathlib import Path
import sqlite3
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DB_PATH = PROJECT_ROOT / "04_sql" / "business_intelligence.db"
OUTPUT_DIR = PROJECT_ROOT / "01_data" / "power_bi"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# DATABASE CONNECTION
# ============================================================

print("=" * 75)
print("FINAL KPI & MASTER ANALYTICS LAYER")
print("=" * 75)

print(f"\nDatabase: {DB_PATH}")
print(f"Output:   {OUTPUT_DIR}")

conn = sqlite3.connect(DB_PATH)


# ============================================================
# 1. LOAD CORE TABLES
# ============================================================

print("\n" + "=" * 75)
print("LOADING CORE DATA")
print("=" * 75)

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
        customer_city,
        customer_state
    FROM customers
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

reviews = pd.read_sql_query(
    """
    SELECT
        review_id,
        order_id,
        review_score
    FROM reviews
    """,
    conn
)

products = pd.read_sql_query(
    """
    SELECT
        product_id,
        product_category_name
    FROM products
    """,
    conn
)

category_translation = pd.read_sql_query(
    """
    SELECT
        product_category_name,
        product_category_name_english
    FROM category_translation
    """,
    conn
)

sellers = pd.read_sql_query(
    """
    SELECT
        seller_id,
        seller_city,
        seller_state
    FROM sellers
    """,
    conn
)

conn.close()

print(f"Orders:              {orders.shape}")
print(f"Customers:            {customers.shape}")
print(f"Payments:             {payments.shape}")
print(f"Order items:          {order_items.shape}")
print(f"Reviews:              {reviews.shape}")
print(f"Products:             {products.shape}")
print(f"Category translation: {category_translation.shape}")
print(f"Sellers:              {sellers.shape}")


# ============================================================
# 2. DATE PREPARATION
# ============================================================

print("\nPreparing dates...")

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

orders["order_month"] = (
    orders["order_purchase_timestamp"]
    .dt.to_period("M")
    .astype(str)
)


# ============================================================
# 3. ORDER-LEVEL PAYMENT AGGREGATION
# ============================================================

print("\nBuilding order-level payment table...")

order_payments = (
    payments
    .groupby("order_id", as_index=False)
    .agg(
        order_payment_value=("payment_value", "sum")
    )
)


# ============================================================
# 4. ORDER-LEVEL ITEM AGGREGATION
# ============================================================

print("Building order-level item table...")

order_item_metrics = (
    order_items
    .groupby("order_id", as_index=False)
    .agg(
        item_count=("order_item_id", "count"),
        product_count=("product_id", "nunique"),
        seller_count=("seller_id", "nunique"),
        item_sales=("price", "sum"),
        freight_value=("freight_value", "sum")
    )
)


# ============================================================
# 5. ORDER-LEVEL REVIEW AGGREGATION
# ============================================================

print("Building order-level review table...")

order_review_metrics = (
    reviews
    .groupby("order_id", as_index=False)
    .agg(
        review_count=("review_id", "nunique"),
        average_review_score=("review_score", "mean")
    )
)


# ============================================================
# 6. BUILD MASTER ORDER TABLE
# ============================================================

print("\nBuilding master order table...")

master_orders = (
    orders
    .merge(
        customers,
        on="customer_id",
        how="left"
    )
    .merge(
        order_payments,
        on="order_id",
        how="left"
    )
    .merge(
        order_item_metrics,
        on="order_id",
        how="left"
    )
    .merge(
        order_review_metrics,
        on="order_id",
        how="left"
    )
)

master_orders["order_payment_value"] = (
    master_orders["order_payment_value"]
    .fillna(0)
)

master_orders["item_count"] = (
    master_orders["item_count"]
    .fillna(0)
)

master_orders["product_count"] = (
    master_orders["product_count"]
    .fillna(0)
)

master_orders["seller_count"] = (
    master_orders["seller_count"]
    .fillna(0)
)

master_orders["item_sales"] = (
    master_orders["item_sales"]
    .fillna(0)
)

master_orders["freight_value"] = (
    master_orders["freight_value"]
    .fillna(0)
)

master_orders["is_reviewed"] = (
    master_orders["review_count"]
    .fillna(0)
    .gt(0)
)


# ============================================================
# 7. CUSTOMER TYPE
# ============================================================

print("Calculating customer types...")

customer_order_counts = (
    master_orders
    .groupby("customer_unique_id")
    .agg(
        customer_order_count=("order_id", "nunique")
    )
    .reset_index()
)

master_orders = master_orders.merge(
    customer_order_counts,
    on="customer_unique_id",
    how="left"
)

master_orders["customer_type"] = (
    master_orders["customer_order_count"]
    .apply(
        lambda x: (
            "One-Time Customer"
            if x == 1
            else "Repeat Customer"
        )
    )
)


# ============================================================
# 8. DELIVERY VARIANCE
# ============================================================

print("Calculating delivery variance...")

master_orders["delivery_variance_days"] = (
    (
        master_orders["order_delivered_customer_date"]
        - master_orders["order_estimated_delivery_date"]
    )
    .dt.total_seconds()
    / 86400
)


def classify_delivery(variance):

    if pd.isna(variance):
        return "Unknown"

    if variance < 0:
        return "Early"

    if variance > 0:
        return "Late"

    return "On Time"


master_orders["delivery_performance_clean"] = (
    master_orders["delivery_variance_days"]
    .apply(classify_delivery)
)


# ============================================================
# 9. EXECUTIVE KPI TABLE
# ============================================================

print("\n" + "=" * 75)
print("BUILDING EXECUTIVE KPI TABLE")
print("=" * 75)

delivered_orders = master_orders[
    master_orders["order_status"] == "delivered"
].copy()

total_orders = len(master_orders)

delivered_count = len(delivered_orders)

total_customers = (
    master_orders["customer_unique_id"]
    .nunique()
)

repeat_customers = (
    customer_order_counts[
        customer_order_counts["customer_order_count"] > 1
    ]["customer_unique_id"]
    .nunique()
)

total_payment = master_orders[
    "order_payment_value"
].sum()

orders_with_payment = (
    master_orders["order_payment_value"] > 0
).sum()

aov = (
    total_payment / orders_with_payment
    if orders_with_payment > 0
    else 0
)

repeat_rate = (
    repeat_customers / total_customers * 100
    if total_customers > 0
    else 0
)

delivery_rate = (
    delivered_count / total_orders * 100
    if total_orders > 0
    else 0
)

average_delivery_days = (
    delivered_orders["delivery_days"].mean()
)

median_delivery_days = (
    delivered_orders["delivery_days"].median()
)

late_orders = (
    delivered_orders["delivery_performance_clean"]
    == "Late"
).sum()

early_orders = (
    delivered_orders["delivery_performance_clean"]
    == "Early"
).sum()

on_time_orders = (
    delivered_orders["delivery_performance_clean"]
    == "On Time"
).sum()

late_rate = (
    late_orders / delivered_count * 100
    if delivered_count > 0
    else 0
)

average_review_score = (
    reviews["review_score"].mean()
)

low_rating_count = (
    reviews["review_score"] <= 2
).sum()

high_rating_count = (
    reviews["review_score"] >= 4
).sum()

executive_kpis = pd.DataFrame(
    {
        "metric": [
            "Total Orders",
            "Delivered Orders",
            "Non-Delivered Orders",
            "Delivery Rate %",
            "Total Customers",
            "Repeat Customers",
            "Repeat Customer Rate %",
            "Total Payment Value",
            "Orders With Payment",
            "Average Order Value",
            "Average Delivery Days",
            "Median Delivery Days",
            "Late Delivered Orders",
            "Late Delivery Rate %",
            "Early Delivered Orders",
            "On-Time Delivered Orders",
            "Average Review Score",
            "Low Rating Reviews (1-2)",
            "High Rating Reviews (4-5)"
        ],
        "value": [
            total_orders,
            delivered_count,
            total_orders - delivered_count,
            delivery_rate,
            total_customers,
            repeat_customers,
            repeat_rate,
            total_payment,
            orders_with_payment,
            aov,
            average_delivery_days,
            median_delivery_days,
            late_orders,
            late_rate,
            early_orders,
            on_time_orders,
            average_review_score,
            low_rating_count,
            high_rating_count
        ]
    }
)

print(
    executive_kpis.to_string(index=False)
)


# ============================================================
# 10. MONTHLY BUSINESS PERFORMANCE
# ============================================================

print("\nBuilding monthly business performance...")

monthly_business = (
    master_orders
    .groupby("order_month")
    .agg(
        orders=("order_id", "nunique"),
        customers=("customer_unique_id", "nunique"),
        payment_value=("order_payment_value", "sum"),
        delivered_orders=("is_delivered", "sum")
    )
    .reset_index()
)

monthly_business["aov"] = (
    monthly_business["payment_value"]
    / monthly_business["orders"]
)

monthly_business["delivery_rate_pct"] = (
    monthly_business["delivered_orders"]
    / monthly_business["orders"]
    * 100
)


# ============================================================
# 11. MONTHLY DELIVERY PERFORMANCE
# ============================================================

monthly_delivery = (
    delivered_orders
    .groupby("order_month")
    .agg(
        delivered_orders=("order_id", "nunique"),
        average_delivery_days=("delivery_days", "mean"),
        median_delivery_days=("delivery_days", "median"),
        average_delivery_variance_days=(
            "delivery_variance_days",
            "mean"
        ),
        late_orders=(
            "delivery_performance_clean",
            lambda x: (x == "Late").sum()
        ),
        early_orders=(
            "delivery_performance_clean",
            lambda x: (x == "Early").sum()
        ),
        on_time_orders=(
            "delivery_performance_clean",
            lambda x: (x == "On Time").sum()
        )
    )
    .reset_index()
)

monthly_delivery["late_rate_pct"] = (
    monthly_delivery["late_orders"]
    / monthly_delivery["delivered_orders"]
    * 100
)


# ============================================================
# 12. CUSTOMER MASTER TABLE
# ============================================================

print("Building customer master table...")

customer_master = (
    master_orders
    .groupby(
        [
            "customer_unique_id",
            "customer_state",
            "customer_city"
        ],
        as_index=False
    )
    .agg(
        orders=("order_id", "nunique"),
        total_spend=("order_payment_value", "sum"),
        average_order_value=("order_payment_value", "mean"),
        average_review_score=("average_review_score", "mean"),
        first_order_date=(
            "order_purchase_timestamp",
            "min"
        ),
        last_order_date=(
            "order_purchase_timestamp",
            "max"
        )
    )
)

customer_master["customer_type"] = (
    customer_master["orders"]
    .apply(
        lambda x: (
            "One-Time Customer"
            if x == 1
            else "Repeat Customer"
        )
    )
)

customer_master["days_between_first_last_order"] = (
    (
        customer_master["last_order_date"]
        - customer_master["first_order_date"]
    )
    .dt.total_seconds()
    / 86400
)


# ============================================================
# 13. CUSTOMER TYPE SUMMARY
# ============================================================

customer_type_analysis = (
    customer_master
    .groupby("customer_type")
    .agg(
        customers=("customer_unique_id", "nunique"),
        total_orders=("orders", "sum"),
        total_spend=("total_spend", "sum"),
        average_customer_spend=("total_spend", "mean"),
        average_order_value=("average_order_value", "mean"),
        average_review_score=("average_review_score", "mean")
    )
    .reset_index()
)

customer_type_analysis["revenue_contribution_pct"] = (
    customer_type_analysis["total_spend"]
    / customer_type_analysis["total_spend"].sum()
    * 100
)


# ============================================================
# 14. CATEGORY MASTER TABLE
# ============================================================

print("Building category master table...")

category_items = (
    order_items
    .merge(
        products,
        on="product_id",
        how="left"
    )
    .merge(
        category_translation,
        on="product_category_name",
        how="left"
    )
)

# IMPORTANT:
# Keep products with missing categories instead of silently
# dropping their sales. This allows category sales to reconcile
# exactly with the raw order_items table.

category_items["category"] = (
    category_items["product_category_name_english"]
    .fillna(category_items["product_category_name"])
    .fillna("Unknown / Unclassified")
)

category_master = (
    category_items
    .groupby("category", as_index=False)
    .agg(
        items_sold=("order_item_id", "count"),
        orders=("order_id", "nunique"),
        sales=("price", "sum"),
        freight_value=("freight_value", "sum")
    )
)

category_master["average_item_price"] = (
    category_master["sales"]
    / category_master["items_sold"]
)

category_master["freight_to_sales_pct"] = (
    category_master["freight_value"]
    / category_master["sales"]
    * 100
)

category_master["sales_contribution_pct"] = (
    category_master["sales"]
    / category_master["sales"].sum()
    * 100
)

category_master = category_master.sort_values(
    "sales",
    ascending=False
).reset_index(drop=True)


# ============================================================
# 15. CATEGORY REVIEW ANALYSIS
# ============================================================

print("Building category review table...")

category_review = (
    category_items[
        [
            "order_id",
            "category"
        ]
    ]
    .drop_duplicates()
    .merge(
        order_review_metrics[
            [
                "order_id",
                "average_review_score"
            ]
        ],
        on="order_id",
        how="left"
    )
)

category_review_master = (
    category_review
    .dropna(subset=["average_review_score"])
    .groupby("category", as_index=False)
    .agg(
        reviewed_orders=("order_id", "nunique"),
        average_review_score=(
            "average_review_score",
            "mean"
        )
    )
)

category_master = category_master.merge(
    category_review_master,
    on="category",
    how="left"
)


# ============================================================
# 16. SELLER MASTER TABLE
# ============================================================

print("Building seller master table...")

seller_master = (
    order_items
    .groupby("seller_id", as_index=False)
    .agg(
        items_sold=("order_item_id", "count"),
        orders=("order_id", "nunique"),
        sales=("price", "sum"),
        freight_value=("freight_value", "sum")
    )
    .merge(
        sellers,
        on="seller_id",
        how="left"
    )
)

seller_master["average_item_price"] = (
    seller_master["sales"]
    / seller_master["items_sold"]
)

seller_master["sales_contribution_pct"] = (
    seller_master["sales"]
    / seller_master["sales"].sum()
    * 100
)

seller_master = seller_master.sort_values(
    "sales",
    ascending=False
).reset_index(drop=True)


# ============================================================
# 17. CUSTOMER STATE MASTER
# ============================================================

print("Building customer geography table...")

customer_state_master = (
    master_orders
    .groupby("customer_state", as_index=False)
    .agg(
        customers=("customer_unique_id", "nunique"),
        orders=("order_id", "nunique"),
        payment_value=("order_payment_value", "sum")
    )
)

customer_state_master["aov"] = (
    customer_state_master["payment_value"]
    / customer_state_master["orders"]
)

customer_state_master["sales_contribution_pct"] = (
    customer_state_master["payment_value"]
    / customer_state_master["payment_value"].sum()
    * 100
)

customer_state_master = customer_state_master.sort_values(
    "payment_value",
    ascending=False
).reset_index(drop=True)


# ============================================================
# 18. SELLER STATE MASTER
# ============================================================

print("Building seller geography table...")

seller_state_master = (
    order_items
    .merge(
        sellers,
        on="seller_id",
        how="left"
    )
    .groupby("seller_state", as_index=False)
    .agg(
        sellers=("seller_id", "nunique"),
        items_sold=("order_item_id", "count"),
        orders=("order_id", "nunique"),
        sales=("price", "sum"),
        freight_value=("freight_value", "sum")
    )
)

seller_state_master["sales_contribution_pct"] = (
    seller_state_master["sales"]
    / seller_state_master["sales"].sum()
    * 100
)

seller_state_master = seller_state_master.sort_values(
    "sales",
    ascending=False
).reset_index(drop=True)


# ============================================================
# 19. DELIVERY STATE MASTER
# ============================================================

print("Building delivery geography table...")

delivery_state_master = (
    delivered_orders
    .groupby("customer_state", as_index=False)
    .agg(
        delivered_orders=("order_id", "nunique"),
        average_delivery_days=("delivery_days", "mean"),
        median_delivery_days=("delivery_days", "median"),
        average_delivery_variance_days=(
            "delivery_variance_days",
            "mean"
        ),
        late_orders=(
            "delivery_performance_clean",
            lambda x: (x == "Late").sum()
        ),
        early_orders=(
            "delivery_performance_clean",
            lambda x: (x == "Early").sum()
        ),
        on_time_orders=(
            "delivery_performance_clean",
            lambda x: (x == "On Time").sum()
        )
    )
    .reset_index(drop=True)
)

delivery_state_master["late_rate_pct"] = (
    delivery_state_master["late_orders"]
    / delivery_state_master["delivered_orders"]
    * 100
)


# ============================================================
# 20. REVIEW MASTER TABLE
# ============================================================

print("Building review master table...")

review_master = (
    reviews
    .groupby("review_score", as_index=False)
    .agg(
        reviews=("review_id", "nunique")
    )
)

review_master["review_percentage"] = (
    review_master["reviews"]
    / review_master["reviews"].sum()
    * 100
)

review_master["rating_group"] = (
    review_master["review_score"]
    .apply(
        lambda x: (
            "Low Rating"
            if x <= 2
            else "Neutral Rating"
            if x == 3
            else "High Rating"
        )
    )
)


# ============================================================
# 21. DATA QUALITY VALIDATION
# ============================================================

print("\n" + "=" * 75)
print("MASTER DATA VALIDATION")
print("=" * 75)

validation_results = []

validation_results.append(
    {
        "check": "Master orders row count",
        "value": len(master_orders),
        "expected": total_orders,
        "status": "PASS"
        if len(master_orders) == total_orders
        else "FAIL"
    }
)

validation_results.append(
    {
        "check": "Delivered order count",
        "value": len(delivered_orders),
        "expected": delivered_count,
        "status": "PASS"
        if len(delivered_orders) == delivered_count
        else "FAIL"
    }
)

validation_results.append(
    {
        "check": "Customer count",
        "value": customer_master["customer_unique_id"].nunique(),
        "expected": total_customers,
        "status": "PASS"
        if (
            customer_master["customer_unique_id"].nunique()
            == total_customers
        )
        else "FAIL"
    }
)

# Category sales must reconcile with ALL raw order-item sales.
validation_results.append(
    {
        "check": "Category sales reconciliation",
        "value": category_master["sales"].sum(),
        "expected": order_items["price"].sum(),
        "status": "PASS"
        if abs(
            category_master["sales"].sum()
            - order_items["price"].sum()
        ) < 0.01
        else "FAIL"
    }
)

validation_results.append(
    {
        "check": "Seller sales reconciliation",
        "value": seller_master["sales"].sum(),
        "expected": order_items["price"].sum(),
        "status": "PASS"
        if abs(
            seller_master["sales"].sum()
            - order_items["price"].sum()
        ) < 0.01
        else "FAIL"
    }
)

validation_results.append(
    {
        "check": "Customer state payment reconciliation",
        "value": customer_state_master["payment_value"].sum(),
        "expected": master_orders["order_payment_value"].sum(),
        "status": "PASS"
        if abs(
            customer_state_master["payment_value"].sum()
            - master_orders["order_payment_value"].sum()
        ) < 0.01
        else "FAIL"
    }
)

validation_results.append(
    {
        "check": "Missing customer IDs",
        "value": master_orders["customer_unique_id"].isna().sum(),
        "expected": 0,
        "status": "PASS"
        if master_orders["customer_unique_id"].isna().sum() == 0
        else "FAIL"
    }
)

validation_results.append(
    {
        "check": "Missing order IDs",
        "value": master_orders["order_id"].isna().sum(),
        "expected": 0,
        "status": "PASS"
        if master_orders["order_id"].isna().sum() == 0
        else "FAIL"
    }
)

validation_df = pd.DataFrame(validation_results)

print(
    validation_df.to_string(index=False)
)


# ============================================================
# 22. SAVE POWER BI TABLES
# ============================================================

print("\n" + "=" * 75)
print("SAVING POWER BI-READY TABLES")
print("=" * 75)

tables_to_save = {
    "executive_kpis": executive_kpis,
    "monthly_business": monthly_business,
    "monthly_delivery": monthly_delivery,
    "customer_master": customer_master,
    "customer_type_analysis": customer_type_analysis,
    "category_master": category_master,
    "seller_master": seller_master,
    "customer_state_master": customer_state_master,
    "seller_state_master": seller_state_master,
    "delivery_state_master": delivery_state_master,
    "review_master": review_master,
    "validation_results": validation_df,
    "master_orders": master_orders
}

for table_name, dataframe in tables_to_save.items():

    output_path = OUTPUT_DIR / f"{table_name}.csv"

    dataframe.to_csv(
        output_path,
        index=False
    )

    print(
        f"✓ {table_name}.csv "
        f"({dataframe.shape[0]:,} rows × "
        f"{dataframe.shape[1]} columns)"
    )


# ============================================================
# 23. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 75)
print("FINAL MASTER ANALYTICS LAYER COMPLETE")
print("=" * 75)

print("\nPower BI folder:")
print(OUTPUT_DIR)

print("\nTables created:")

for table_name in tables_to_save:
    print(f"  ✓ {table_name}.csv")

print("\nValidation status:")

if (validation_df["status"] == "FAIL").any():

    failed_checks = validation_df[
        validation_df["status"] == "FAIL"
    ]

    print(
        f"⚠ {len(failed_checks)} validation check(s) failed."
    )

    print(
        failed_checks.to_string(index=False)
    )

else:

    print("✓ ALL VALIDATION CHECKS PASSED")

print("\n" + "=" * 75)