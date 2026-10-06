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

customers = pd.read_sql_query(
    "SELECT * FROM customers",
    conn
)

conn.close()


print("=" * 70)
print("CUSTOMER COHORT & RETENTION ANALYSIS")
print("=" * 70)

print("\nOrders:", orders.shape)
print("Customers:", customers.shape)


# ============================================================
# 2. CONNECT ORDERS TO REAL CUSTOMER ID
# ============================================================

orders_customers = orders.merge(
    customers[
        [
            "customer_id",
            "customer_unique_id"
        ]
    ],
    on="customer_id",
    how="left"
)

print(
    "\nOrders + customer identity:",
    orders_customers.shape
)

print(
    "Unique customers:",
    orders_customers["customer_unique_id"].nunique()
)

print(
    "Missing customer_unique_id:",
    orders_customers["customer_unique_id"].isna().sum()
)


# ============================================================
# 3. KEEP DELIVERED ORDERS ONLY
# ============================================================

delivered_orders = orders_customers[
    orders_customers["order_status"] == "delivered"
].copy()

print(
    "\nDelivered orders:",
    delivered_orders.shape
)


# ============================================================
# 4. PREPARE PURCHASE DATE
# ============================================================

delivered_orders["order_purchase_timestamp"] = pd.to_datetime(
    delivered_orders["order_purchase_timestamp"]
)

delivered_orders["purchase_month"] = (
    delivered_orders["order_purchase_timestamp"]
    .dt.to_period("M")
)


# ============================================================
# 5. DEFINE CUSTOMER COHORT
#
# Cohort month = customer's first DELIVERED purchase month
# ============================================================

customer_first_purchase = (
    delivered_orders
    .groupby("customer_unique_id")["purchase_month"]
    .min()
    .reset_index()
)

customer_first_purchase = customer_first_purchase.rename(
    columns={
        "purchase_month": "cohort_month"
    }
)


# ============================================================
# 6. ATTACH COHORT TO EVERY DELIVERED ORDER
# ============================================================

delivered_orders = delivered_orders.merge(
    customer_first_purchase,
    on="customer_unique_id",
    how="left"
)


# ============================================================
# 7. CALCULATE MONTH DIFFERENCE
# ============================================================

delivered_orders["cohort_year"] = (
    delivered_orders["cohort_month"]
    .dt.year
)

delivered_orders["cohort_month_number"] = (
    delivered_orders["cohort_month"]
    .dt.month
)

delivered_orders["purchase_year"] = (
    delivered_orders["purchase_month"]
    .dt.year
)

delivered_orders["purchase_month_number"] = (
    delivered_orders["purchase_month"]
    .dt.month
)

delivered_orders["months_since_first_purchase"] = (
    (
        delivered_orders["purchase_year"]
        - delivered_orders["cohort_year"]
    ) * 12
    +
    (
        delivered_orders["purchase_month_number"]
        - delivered_orders["cohort_month_number"]
    )
)


# ============================================================
# 8. CUSTOMER-MONTH ACTIVITY
#
# A customer is counted only once per month.
# Multiple orders in the same month do not inflate retention.
# ============================================================

customer_month_activity = (
    delivered_orders[
        [
            "customer_unique_id",
            "cohort_month",
            "purchase_month",
            "months_since_first_purchase"
        ]
    ]
    .drop_duplicates()
)


# ============================================================
# 9. COHORT CUSTOMER COUNTS
# ============================================================

cohort_data = (
    customer_month_activity
    .groupby(
        [
            "cohort_month",
            "months_since_first_purchase"
        ]
    )["customer_unique_id"]
    .nunique()
    .reset_index()
)

cohort_data = cohort_data.rename(
    columns={
        "customer_unique_id": "customers"
    }
)


# ============================================================
# 10. COHORT SIZES
# ============================================================

cohort_sizes = (
    cohort_data[
        cohort_data["months_since_first_purchase"] == 0
    ][
        [
            "cohort_month",
            "customers"
        ]
    ]
    .rename(
        columns={
            "customers": "cohort_size"
        }
    )
)


# ============================================================
# 11. CALCULATE RETENTION
# ============================================================

cohort_data = cohort_data.merge(
    cohort_sizes,
    on="cohort_month",
    how="left"
)

cohort_data["retention_rate"] = (
    cohort_data["customers"]
    / cohort_data["cohort_size"]
    * 100
)


# ============================================================
# 12. DETERMINE OBSERVABLE MONTHS
#
# A cohort can only be evaluated for a month if enough
# calendar time has passed to observe that month.
#
# Example:
# If the dataset ends in August 2018, a July 2018 cohort
# cannot have a valid Month 2 observation.
# ============================================================

latest_purchase_month = delivered_orders[
    "purchase_month"
].max()

cohort_data["latest_observable_month"] = (
    cohort_data["cohort_month"]
    + cohort_data["months_since_first_purchase"]
)

cohort_data["is_observable"] = (
    cohort_data["latest_observable_month"]
    <= latest_purchase_month
)


# Keep only genuinely observable retention periods
observable_cohort_data = cohort_data[
    cohort_data["is_observable"]
].copy()


# ============================================================
# 13. RETENTION MATRIX
# ============================================================

retention_matrix = (
    observable_cohort_data
    .pivot(
        index="cohort_month",
        columns="months_since_first_purchase",
        values="retention_rate"
    )
)


# ============================================================
# 14. CUSTOMER COUNT MATRIX
# ============================================================

customer_count_matrix = (
    observable_cohort_data
    .pivot(
        index="cohort_month",
        columns="months_since_first_purchase",
        values="customers"
    )
)


# ============================================================
# 15. COHORT SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("COHORT SUMMARY")
print("=" * 70)

print(
    "\nNumber of cohorts:",
    retention_matrix.shape[0]
)

print(
    "Latest observable purchase month:",
    latest_purchase_month
)

print(
    "Maximum observable months since first purchase:",
    int(
        observable_cohort_data[
            "months_since_first_purchase"
        ].max()
    )
)


print("\nCohort sizes:")

print(
    cohort_sizes.to_string(
        index=False
    )
)


# ============================================================
# 16. RETENTION MATRIX
# ============================================================

print("\n" + "=" * 70)
print("RETENTION MATRIX (%)")
print("=" * 70)

print(
    retention_matrix.round(2).to_string()
)


# ============================================================
# 17. AVERAGE RETENTION BY MONTH
#
# Only observable cohort periods are included.
# ============================================================

monthly_retention = (
    observable_cohort_data
    .groupby("months_since_first_purchase")
    ["retention_rate"]
    .mean()
    .reset_index()
)

monthly_retention = monthly_retention.rename(
    columns={
        "retention_rate": "average_retention_rate"
    }
)


print("\n" + "=" * 70)
print("AVERAGE RETENTION BY MONTH")
print("=" * 70)

print(
    monthly_retention.round(2).to_string(
        index=False
    )
)


# ============================================================
# 18. REPEAT CUSTOMER ANALYSIS
# ============================================================

customer_order_counts = (
    delivered_orders
    .groupby("customer_unique_id")
    ["order_id"]
    .nunique()
)

total_customers = (
    customer_order_counts.shape[0]
)

repeat_customers = (
    (customer_order_counts > 1).sum()
)

one_time_customers = (
    (customer_order_counts == 1).sum()
)

repeat_customer_rate = (
    repeat_customers
    / total_customers
    * 100
)


print("\n" + "=" * 70)
print("REPEAT CUSTOMER ANALYSIS")
print("=" * 70)

print(
    "\nTotal customers:",
    total_customers
)

print(
    "One-time customers:",
    one_time_customers
)

print(
    "Repeat customers:",
    repeat_customers
)

print(
    "Repeat customer rate:",
    round(
        repeat_customer_rate,
        2
    ),
    "%"
)


# ============================================================
# 19. CUSTOMER ORDER FREQUENCY
# ============================================================

frequency_distribution = (
    customer_order_counts
    .value_counts()
    .sort_index()
    .reset_index()
)

frequency_distribution.columns = [
    "order_frequency",
    "customers"
]


print("\n" + "=" * 70)
print("CUSTOMER ORDER FREQUENCY")
print("=" * 70)

print(
    frequency_distribution.to_string(
        index=False
    )
)


# ============================================================
# 20. SAVE COHORT DETAIL
# ============================================================

COHORT_DETAIL_PATH = (
    r"C:\Users\Rachitesh Sharma\Documents"
    r"\Business-Decision-Intelligence\01_data"
    r"\cohort_analysis_detail.csv"
)

observable_cohort_data.to_csv(
    COHORT_DETAIL_PATH,
    index=False
)


# ============================================================
# 21. SAVE RETENTION MATRIX
# ============================================================

RETENTION_MATRIX_PATH = (
    r"C:\Users\Rachitesh Sharma\Documents"
    r"\Business-Decision-Intelligence\01_data"
    r"\cohort_retention_matrix.csv"
)

retention_matrix.to_csv(
    RETENTION_MATRIX_PATH
)


# ============================================================
# 22. SAVE CUSTOMER COUNT MATRIX
# ============================================================

CUSTOMER_MATRIX_PATH = (
    r"C:\Users\Rachitesh Sharma\Documents"
    r"\Business-Decision-Intelligence\01_data"
    r"\cohort_customer_count_matrix.csv"
)

customer_count_matrix.to_csv(
    CUSTOMER_MATRIX_PATH
)


# ============================================================
# 23. SAVE MONTHLY RETENTION
# ============================================================

MONTHLY_RETENTION_PATH = (
    r"C:\Users\Rachitesh Sharma\Documents"
    r"\Business-Decision-Intelligence\01_data"
    r"\monthly_retention_summary.csv"
)

monthly_retention.to_csv(
    MONTHLY_RETENTION_PATH,
    index=False
)


# ============================================================
# 24. SAVE FREQUENCY DISTRIBUTION
# ============================================================

FREQUENCY_PATH = (
    r"C:\Users\Rachitesh Sharma\Documents"
    r"\Business-Decision-Intelligence\01_data"
    r"\customer_frequency_distribution.csv"
)

frequency_distribution.to_csv(
    FREQUENCY_PATH,
    index=False
)


# ============================================================
# 25. FINAL OUTPUT
# ============================================================

print("\n" + "=" * 70)
print("FILES SAVED")
print("=" * 70)

print("\nCohort detail:")
print(COHORT_DETAIL_PATH)

print("\nRetention matrix:")
print(RETENTION_MATRIX_PATH)

print("\nCustomer count matrix:")
print(CUSTOMER_MATRIX_PATH)

print("\nMonthly retention:")
print(MONTHLY_RETENTION_PATH)

print("\nFrequency distribution:")
print(FREQUENCY_PATH)

print("\n" + "=" * 70)
print("COHORT ANALYSIS COMPLETE")
print("=" * 70)