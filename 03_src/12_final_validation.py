from pathlib import Path
import sqlite3
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DB_PATH = PROJECT_ROOT / "04_sql" / "business_intelligence.db"
POWER_BI_DIR = PROJECT_ROOT / "01_data" / "power_bi"


print("=" * 75)
print("FINAL PROJECT VALIDATION")
print("=" * 75)

print(f"\nDatabase: {DB_PATH}")
print(f"Power BI: {POWER_BI_DIR}")


# ============================================================
# 1. REQUIRED FILE CHECK
# ============================================================

print("\n" + "=" * 75)
print("1. REQUIRED OUTPUT FILE CHECK")
print("=" * 75)

required_files = [
    "executive_kpis.csv",
    "monthly_business.csv",
    "monthly_delivery.csv",
    "customer_master.csv",
    "customer_type_analysis.csv",
    "category_master.csv",
    "seller_master.csv",
    "customer_state_master.csv",
    "seller_state_master.csv",
    "delivery_state_master.csv",
    "review_master.csv",
    "validation_results.csv",
    "master_orders.csv"
]

file_results = []

for filename in required_files:

    path = POWER_BI_DIR / filename
    exists = path.exists()

    file_results.append(
        {
            "file": filename,
            "exists": exists,
            "size_bytes": path.stat().st_size if exists else 0
        }
    )

    print(f"{'✓' if exists else '✗'} {filename}")


# ============================================================
# 2. LOAD SOURCE DATABASE
# ============================================================

print("\n" + "=" * 75)
print("2. LOADING SOURCE DATABASE")
print("=" * 75)

conn = sqlite3.connect(DB_PATH)

orders = pd.read_sql_query(
    "SELECT * FROM orders",
    conn
)

customers = pd.read_sql_query(
    "SELECT * FROM customers",
    conn
)

order_items = pd.read_sql_query(
    "SELECT * FROM order_items",
    conn
)

payments = pd.read_sql_query(
    "SELECT * FROM payments",
    conn
)

products = pd.read_sql_query(
    "SELECT * FROM products",
    conn
)

reviews = pd.read_sql_query(
    "SELECT * FROM reviews",
    conn
)

sellers = pd.read_sql_query(
    "SELECT * FROM sellers",
    conn
)

conn.close()

print(f"Orders:       {orders.shape}")
print(f"Customers:    {customers.shape}")
print(f"Order items:  {order_items.shape}")
print(f"Payments:     {payments.shape}")
print(f"Products:     {products.shape}")
print(f"Reviews:      {reviews.shape}")
print(f"Sellers:      {sellers.shape}")


# ============================================================
# 3. LOAD POWER BI TABLES
# ============================================================

print("\n" + "=" * 75)
print("3. LOADING POWER BI TABLES")
print("=" * 75)

master_orders = pd.read_csv(
    POWER_BI_DIR / "master_orders.csv"
)

customer_master = pd.read_csv(
    POWER_BI_DIR / "customer_master.csv"
)

category_master = pd.read_csv(
    POWER_BI_DIR / "category_master.csv"
)

seller_master = pd.read_csv(
    POWER_BI_DIR / "seller_master.csv"
)

customer_state_master = pd.read_csv(
    POWER_BI_DIR / "customer_state_master.csv"
)

seller_state_master = pd.read_csv(
    POWER_BI_DIR / "seller_state_master.csv"
)

delivery_state_master = pd.read_csv(
    POWER_BI_DIR / "delivery_state_master.csv"
)

review_master = pd.read_csv(
    POWER_BI_DIR / "review_master.csv"
)

executive_kpis = pd.read_csv(
    POWER_BI_DIR / "executive_kpis.csv"
)

print(f"Master orders:        {master_orders.shape}")
print(f"Customer master:      {customer_master.shape}")
print(f"Category master:      {category_master.shape}")
print(f"Seller master:        {seller_master.shape}")


# ============================================================
# 4. VALIDATION HELPER
# ============================================================

validation_results = []


def add_check(
    check_name,
    actual,
    expected,
    tolerance=0
):

    difference = abs(actual - expected)

    passed = difference <= tolerance

    validation_results.append(
        {
            "check": check_name,
            "actual": actual,
            "expected": expected,
            "difference": difference,
            "status": "PASS" if passed else "FAIL"
        }
    )


# ============================================================
# 5. ROW COUNT VALIDATION
# ============================================================

print("\n" + "=" * 75)
print("4. ROW COUNT VALIDATION")
print("=" * 75)

add_check(
    "Master orders row count",
    len(master_orders),
    len(orders)
)

add_check(
    "Customer master customer count",
    customer_master["customer_unique_id"].nunique(),
    customers["customer_unique_id"].nunique()
)

add_check(
    "Category master category count",
    category_master["category"].nunique(),
    74
)

add_check(
    "Seller master seller count",
    seller_master["seller_id"].nunique(),
    sellers["seller_id"].nunique()
)


# ============================================================
# 6. MASTER ORDER KEY VALIDATION
# ============================================================

print("\n" + "=" * 75)
print("5. MASTER ORDER KEY VALIDATION")
print("=" * 75)

master_order_unique = (
    master_orders["order_id"].nunique()
)

source_order_unique = (
    orders["order_id"].nunique()
)

add_check(
    "Unique order IDs",
    master_order_unique,
    source_order_unique
)

master_order_duplicates = (
    master_orders["order_id"]
    .duplicated()
    .sum()
)

add_check(
    "Duplicate order IDs",
    master_order_duplicates,
    0
)

missing_order_ids = (
    master_orders["order_id"]
    .isna()
    .sum()
)

add_check(
    "Missing master order IDs",
    missing_order_ids,
    0
)


# ============================================================
# 7. CUSTOMER KEY VALIDATION
# ============================================================

print("\n" + "=" * 75)
print("6. CUSTOMER KEY VALIDATION")
print("=" * 75)

missing_customer_ids = (
    master_orders["customer_unique_id"]
    .isna()
    .sum()
)

add_check(
    "Missing customer unique IDs in master orders",
    missing_customer_ids,
    0
)

# IMPORTANT:
# customer_master can contain multiple rows for the same
# customer_unique_id because the table is grouped with
# geographic attributes such as state/city.
#
# Therefore we validate UNIQUE CUSTOMER COUNT rather than
# demanding that every row have a unique customer ID.

customer_master_unique_customers = (
    customer_master["customer_unique_id"]
    .nunique()
)

source_unique_customers = (
    customers["customer_unique_id"]
    .nunique()
)

add_check(
    "Customer master unique customer count",
    customer_master_unique_customers,
    source_unique_customers
)


# ============================================================
# 8. SALES RECONCILIATION
# ============================================================

print("\n" + "=" * 75)
print("7. SALES RECONCILIATION")
print("=" * 75)

source_sales = (
    order_items["price"]
    .sum()
)

category_sales = (
    category_master["sales"]
    .sum()
)

seller_sales = (
    seller_master["sales"]
    .sum()
)

print(
    f"\nSource sales:   {source_sales:,.2f}"
)

print(
    f"Category sales: {category_sales:,.2f}"
)

print(
    f"Seller sales:   {seller_sales:,.2f}"
)

add_check(
    "Category sales reconciliation",
    category_sales,
    source_sales,
    tolerance=0.01
)

add_check(
    "Seller sales reconciliation",
    seller_sales,
    source_sales,
    tolerance=0.01
)


# ============================================================
# 9. PAYMENT RECONCILIATION
# ============================================================

print("\n" + "=" * 75)
print("8. PAYMENT RECONCILIATION")
print("=" * 75)

source_payment_total = (
    payments["payment_value"]
    .sum()
)

master_payment_total = (
    master_orders["order_payment_value"]
    .sum()
)

print(
    f"\nSource payment total:  "
    f"{source_payment_total:,.2f}"
)

print(
    f"Master payment total:  "
    f"{master_payment_total:,.2f}"
)

add_check(
    "Payment total reconciliation",
    master_payment_total,
    source_payment_total,
    tolerance=0.01
)


# ============================================================
# 10. DELIVERY VALIDATION
# ============================================================

print("\n" + "=" * 75)
print("9. DELIVERY VALIDATION")
print("=" * 75)

source_delivered = (
    orders["order_status"]
    == "delivered"
).sum()

master_delivered = (
    master_orders["order_status"]
    == "delivered"
).sum()

add_check(
    "Delivered order count",
    master_delivered,
    source_delivered
)

negative_delivery_days = (
    master_orders["delivery_days"]
    .dropna()
    .lt(0)
    .sum()
)

add_check(
    "Negative delivery durations",
    negative_delivery_days,
    0
)


# ============================================================
# 11. REVIEW VALIDATION
# ============================================================

print("\n" + "=" * 75)
print("10. REVIEW VALIDATION")
print("=" * 75)

source_review_count = (
    reviews["review_score"]
    .notna()
    .sum()
)

review_master_count = (
    review_master["reviews"]
    .sum()
)

print(
    f"\nSource review rows with scores: "
    f"{source_review_count:,}"
)

print(
    f"Review master unique reviews: "
    f"{review_master_count:,}"
)

source_unique_review_count = (
    reviews["review_id"]
    .nunique()
)

add_check(
    "Unique review count",
    review_master_count,
    source_unique_review_count
)

invalid_review_scores = (
    ~reviews["review_score"]
    .isin([1, 2, 3, 4, 5])
).sum()

add_check(
    "Invalid review scores",
    invalid_review_scores,
    0
)


# ============================================================
# 12. CUSTOMER STATE RECONCILIATION
# ============================================================

print("\n" + "=" * 75)
print("11. CUSTOMER GEOGRAPHY VALIDATION")
print("=" * 75)

state_payment_total = (
    customer_state_master["payment_value"]
    .sum()
)

add_check(
    "Customer state payment reconciliation",
    state_payment_total,
    master_payment_total,
    tolerance=0.01
)


# ============================================================
# 13. SELLER STATE RECONCILIATION
# ============================================================

print("\n" + "=" * 75)
print("12. SELLER GEOGRAPHY VALIDATION")
print("=" * 75)

seller_state_sales = (
    seller_state_master["sales"]
    .sum()
)

add_check(
    "Seller state sales reconciliation",
    seller_state_sales,
    source_sales,
    tolerance=0.01
)


# ============================================================
# 14. CATEGORY DATA QUALITY
# ============================================================

print("\n" + "=" * 75)
print("13. CATEGORY DATA QUALITY")
print("=" * 75)

unknown_category_rows = category_master[
    category_master["category"]
    == "Unknown / Unclassified"
]

unknown_category_sales = (
    unknown_category_rows["sales"]
    .sum()
)

print(
    f"\nUnknown / Unclassified sales: "
    f"{unknown_category_sales:,.2f}"
)

# This category is intentional.
# Missing product categories are retained rather than dropped.


# ============================================================
# 15. MASTER ORDER NULL CHECK
# ============================================================

print("\n" + "=" * 75)
print("14. MASTER ORDER NULL CHECK")
print("=" * 75)

critical_columns = [
    "order_id",
    "customer_unique_id",
    "order_status",
    "order_purchase_timestamp"
]

for column in critical_columns:

    missing_count = (
        master_orders[column]
        .isna()
        .sum()
    )

    add_check(
        f"Missing values: {column}",
        missing_count,
        0
    )


# ============================================================
# 16. POWER BI FILE CHECK
# ============================================================

print("\n" + "=" * 75)
print("15. POWER BI TABLE CHECK")
print("=" * 75)

for filename in required_files:

    exists = (
        POWER_BI_DIR / filename
    ).exists()

    add_check(
        f"Required file exists: {filename}",
        1 if exists else 0,
        1
    )


# ============================================================
# 17. FINAL VALIDATION RESULTS
# ============================================================

final_validation = pd.DataFrame(
    validation_results
)

print("\n" + "=" * 75)
print("FINAL VALIDATION RESULTS")
print("=" * 75)

print(
    final_validation.to_string(index=False)
)


# ============================================================
# 18. SUMMARY
# ============================================================

total_checks = len(final_validation)

passed_checks = (
    final_validation["status"]
    == "PASS"
).sum()

failed_checks = (
    final_validation["status"]
    == "FAIL"
).sum()

print("\n" + "=" * 75)
print("FINAL VALIDATION SUMMARY")
print("=" * 75)

print(
    f"\nTotal checks:  {total_checks}"
)

print(
    f"Passed:        {passed_checks}"
)

print(
    f"Failed:        {failed_checks}"
)


# ============================================================
# 19. SAVE VALIDATION REPORT
# ============================================================

validation_path = (
    POWER_BI_DIR
    / "final_validation_report.csv"
)

final_validation.to_csv(
    validation_path,
    index=False
)

print(
    f"\nValidation report saved to:"
    f"\n{validation_path}"
)


# ============================================================
# 20. FINAL STATUS
# ============================================================

print("\n" + "=" * 75)

if failed_checks == 0:

    print("✓ FINAL VALIDATION PASSED")
    print("✓ DATA IS READY FOR POWER BI")

else:

    print("⚠ FINAL VALIDATION FAILED")
    print("⚠ FIX FAILED CHECKS BEFORE POWER BI")

print("=" * 75)