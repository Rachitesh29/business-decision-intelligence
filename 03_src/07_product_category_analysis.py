import sqlite3
import pandas as pd


# ============================================================
# 1. LOAD DATA FROM SQLITE
# ============================================================

DB_PATH = r"C:\Users\Rachitesh Sharma\Documents\Business-Decision-Intelligence\04_sql\business_intelligence.db"

conn = sqlite3.connect(DB_PATH)

orders = pd.read_sql_query(
    "SELECT * FROM orders",
    conn
)

order_items = pd.read_sql_query(
    "SELECT * FROM order_items",
    conn
)

products = pd.read_sql_query(
    "SELECT * FROM products",
    conn
)

payments = pd.read_sql_query(
    "SELECT * FROM payments",
    conn
)

reviews = pd.read_sql_query(
    "SELECT * FROM reviews",
    conn
)

translation = pd.read_sql_query(
    "SELECT * FROM category_translation",
    conn
)

conn.close()


print("=" * 70)
print("PRODUCT & CATEGORY ANALYSIS")
print("=" * 70)

print("\nOrders:", orders.shape)
print("Order items:", order_items.shape)
print("Products:", products.shape)
print("Payments:", payments.shape)
print("Reviews:", reviews.shape)
print("Category translation:", translation.shape)


# ============================================================
# 2. KEEP DELIVERED ORDERS
# ============================================================

delivered_orders = orders[
    orders["order_status"] == "delivered"
].copy()

print(
    "\nDelivered orders:",
    delivered_orders.shape
)


# ============================================================
# 3. CONNECT ORDER ITEMS TO DELIVERED ORDERS
# ============================================================

delivered_items = order_items.merge(
    delivered_orders[
        [
            "order_id",
            "customer_id",
            "order_purchase_timestamp"
        ]
    ],
    on="order_id",
    how="inner"
)

print(
    "Delivered order items:",
    delivered_items.shape
)


# ============================================================
# 4. ADD PRODUCT INFORMATION
# ============================================================

delivered_items = delivered_items.merge(
    products,
    on="product_id",
    how="left"
)


# ============================================================
# 5. ADD ENGLISH CATEGORY NAMES
# ============================================================

delivered_items = delivered_items.merge(
    translation,
    on="product_category_name",
    how="left"
)

delivered_items["category"] = (
    delivered_items["product_category_name_english"]
    .fillna(
        delivered_items["product_category_name"]
    )
    .fillna("unknown")
)


# ============================================================
# 6. BASIC ITEM-LEVEL VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("DATA VALIDATION")
print("=" * 70)

print(
    "\nMissing product_id:",
    delivered_items["product_id"].isna().sum()
)

print(
    "Missing category:",
    delivered_items["category"].isna().sum()
)

print(
    "Missing price:",
    delivered_items["price"].isna().sum()
)

print(
    "Missing freight:",
    delivered_items["freight_value"].isna().sum()
)


# ============================================================
# 7. CATEGORY PERFORMANCE
# ============================================================

category_analysis = (
    delivered_items
    .groupby("category")
    .agg(
        items_sold=("order_item_id", "count"),
        unique_orders=("order_id", "nunique"),
        unique_products=("product_id", "nunique"),
        sales=("price", "sum"),
        freight=("freight_value", "sum"),
        avg_item_price=("price", "mean"),
        avg_freight_per_item=("freight_value", "mean")
    )
    .reset_index()
)


# ============================================================
# 8. CATEGORY FREIGHT RATE
# ============================================================

category_analysis["freight_to_sales_pct"] = (
    category_analysis["freight"]
    / category_analysis["sales"]
    * 100
)


# ============================================================
# 9. CATEGORY SALES CONTRIBUTION
# ============================================================

total_category_sales = (
    category_analysis["sales"].sum()
)

category_analysis["sales_contribution_pct"] = (
    category_analysis["sales"]
    / total_category_sales
    * 100
)


# ============================================================
# 10. SORT BY SALES
# ============================================================

category_analysis = (
    category_analysis
    .sort_values(
        "sales",
        ascending=False
    )
    .reset_index(drop=True)
)


print("\n" + "=" * 70)
print("CATEGORY PERFORMANCE")
print("=" * 70)

print(
    category_analysis.round(2).to_string(
        index=False
    )
)


# ============================================================
# 11. TOP 10 CATEGORIES BY SALES
# ============================================================

print("\n" + "=" * 70)
print("TOP 10 CATEGORIES BY SALES")
print("=" * 70)

print(
    category_analysis[
        [
            "category",
            "sales",
            "items_sold",
            "unique_orders",
            "avg_item_price"
        ]
    ]
    .head(10)
    .round(2)
    .to_string(index=False)
)


# ============================================================
# 12. TOP 10 CATEGORIES BY ITEM VOLUME
# ============================================================

print("\n" + "=" * 70)
print("TOP 10 CATEGORIES BY ITEM VOLUME")
print("=" * 70)

print(
    category_analysis
    .sort_values(
        "items_sold",
        ascending=False
    )[
        [
            "category",
            "items_sold",
            "sales",
            "avg_item_price"
        ]
    ]
    .head(10)
    .round(2)
    .to_string(index=False)
)


# ============================================================
# 13. HIGHEST AVERAGE ITEM PRICE
#
# Exclude categories with extremely small volume from the
# headline analysis to avoid misleading averages.
# ============================================================

price_analysis = category_analysis[
    category_analysis["items_sold"] >= 100
].copy()

price_analysis = price_analysis.sort_values(
    "avg_item_price",
    ascending=False
)


print("\n" + "=" * 70)
print("HIGHEST AVERAGE ITEM PRICE")
print("(Minimum 100 items)")
print("=" * 70)

print(
    price_analysis[
        [
            "category",
            "avg_item_price",
            "items_sold",
            "sales"
        ]
    ]
    .head(10)
    .round(2)
    .to_string(index=False)
)


# ============================================================
# 14. HIGHEST FREIGHT BURDEN
#
# Use a minimum sales threshold so tiny categories don't
# dominate the comparison.
# ============================================================

freight_analysis = category_analysis[
    category_analysis["sales"] >= 10000
].copy()

freight_analysis = freight_analysis.sort_values(
    "freight_to_sales_pct",
    ascending=False
)


print("\n" + "=" * 70)
print("HIGHEST FREIGHT-TO-SALES RATIO")
print("(Minimum sales: 10,000)")
print("=" * 70)

print(
    freight_analysis[
        [
            "category",
            "freight_to_sales_pct",
            "sales",
            "freight",
            "items_sold"
        ]
    ]
    .head(10)
    .round(2)
    .to_string(index=False)
)


# ============================================================
# 15. PRODUCT-LEVEL PERFORMANCE
# ============================================================

product_analysis = (
    delivered_items
    .groupby(
        [
            "product_id",
            "category"
        ]
    )
    .agg(
        items_sold=("order_item_id", "count"),
        unique_orders=("order_id", "nunique"),
        sales=("price", "sum"),
        freight=("freight_value", "sum"),
        avg_price=("price", "mean")
    )
    .reset_index()
)


product_analysis["freight_to_sales_pct"] = (
    product_analysis["freight"]
    / product_analysis["sales"]
    * 100
)


product_analysis = product_analysis.sort_values(
    "sales",
    ascending=False
)


# ============================================================
# 16. TOP PRODUCTS BY SALES
# ============================================================

print("\n" + "=" * 70)
print("TOP 20 PRODUCTS BY SALES")
print("=" * 70)

print(
    product_analysis[
        [
            "product_id",
            "category",
            "items_sold",
            "sales",
            "avg_price"
        ]
    ]
    .head(20)
    .round(2)
    .to_string(index=False)
)


# ============================================================
# 17. CATEGORY REVIEW PERFORMANCE
# ============================================================

reviews_delivered = reviews.merge(
    delivered_orders[
        ["order_id"]
    ],
    on="order_id",
    how="inner"
)


# One order can have multiple review records.
# Average review score is calculated from available reviews.
category_review_items = delivered_items[
    [
        "order_id",
        "product_id",
        "category"
    ]
].drop_duplicates()


category_reviews = category_review_items.merge(
    reviews_delivered[
        [
            "order_id",
            "review_score"
        ]
    ],
    on="order_id",
    how="inner"
)


category_review_analysis = (
    category_reviews
    .groupby("category")
    .agg(
        reviewed_orders=("order_id", "nunique"),
        avg_review_score=("review_score", "mean")
    )
    .reset_index()
)


category_analysis = category_analysis.merge(
    category_review_analysis,
    on="category",
    how="left"
)


# ============================================================
# 18. FINAL CATEGORY TABLE
# ============================================================

category_analysis = category_analysis[
    [
        "category",
        "items_sold",
        "unique_orders",
        "unique_products",
        "sales",
        "freight",
        "avg_item_price",
        "avg_freight_per_item",
        "freight_to_sales_pct",
        "sales_contribution_pct",
        "reviewed_orders",
        "avg_review_score"
    ]
]


print("\n" + "=" * 70)
print("FINAL CATEGORY ANALYTICS")
print("=" * 70)

print(
    category_analysis.round(2).to_string(
        index=False
    )
)


# ============================================================
# 19. SAVE CATEGORY ANALYSIS
# ============================================================

CATEGORY_OUTPUT_PATH = (
    r"C:\Users\Rachitesh Sharma\Documents"
    r"\Business-Decision-Intelligence\01_data"
    r"\category_analysis.csv"
)

category_analysis.to_csv(
    CATEGORY_OUTPUT_PATH,
    index=False
)


# ============================================================
# 20. SAVE PRODUCT ANALYSIS
# ============================================================

PRODUCT_OUTPUT_PATH = (
    r"C:\Users\Rachitesh Sharma\Documents"
    r"\Business-Decision-Intelligence\01_data"
    r"\product_analysis.csv"
)

product_analysis.to_csv(
    PRODUCT_OUTPUT_PATH,
    index=False
)


# ============================================================
# 21. SAVE CATEGORY REVIEW ANALYSIS
# ============================================================

CATEGORY_REVIEW_OUTPUT_PATH = (
    r"C:\Users\Rachitesh Sharma\Documents"
    r"\Business-Decision-Intelligence\01_data"
    r"\category_review_analysis.csv"
)

category_review_analysis.to_csv(
    CATEGORY_REVIEW_OUTPUT_PATH,
    index=False
)


# ============================================================
# 22. FINAL OUTPUT
# ============================================================

print("\n" + "=" * 70)
print("FILES SAVED")
print("=" * 70)

print("\nCategory analysis:")
print(CATEGORY_OUTPUT_PATH)

print("\nProduct analysis:")
print(PRODUCT_OUTPUT_PATH)

print("\nCategory review analysis:")
print(CATEGORY_REVIEW_OUTPUT_PATH)

print("\n" + "=" * 70)
print("PRODUCT & CATEGORY ANALYSIS COMPLETE")
print("=" * 70)