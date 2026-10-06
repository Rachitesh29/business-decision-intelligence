import sqlite3
import pandas as pd


# ============================================================
# 1. LOAD DATA FROM SQLITE
# ============================================================

DB_PATH = r"C:\Users\Rachitesh Sharma\Documents\Business-Decision-Intelligence\04_sql\business_intelligence.db"

conn = sqlite3.connect(DB_PATH)

orders = pd.read_sql_query("SELECT * FROM orders", conn)
customers = pd.read_sql_query("SELECT * FROM customers", conn)
payments = pd.read_sql_query("SELECT * FROM payments", conn)

conn.close()


print("=" * 60)
print("RFM CUSTOMER ANALYSIS")
print("=" * 60)

print("\nOrders:", orders.shape)
print("Customers:", customers.shape)
print("Payments:", payments.shape)


# ============================================================
# 2. CONNECT ORDERS TO CUSTOMER UNIQUE ID
# ============================================================

orders_customers = orders.merge(
    customers[["customer_id", "customer_unique_id"]],
    on="customer_id",
    how="left"
)

print("\nOrders + customer identity:", orders_customers.shape)

print(
    "Unique customers:",
    orders_customers["customer_unique_id"].nunique()
)

print(
    "Missing customer_unique_id:",
    orders_customers["customer_unique_id"].isna().sum()
)


# ============================================================
# 3. KEEP DELIVERED ORDERS
# ============================================================

delivered_orders = orders_customers[
    orders_customers["order_status"] == "delivered"
].copy()

print("\nDelivered orders:", delivered_orders.shape)


# ============================================================
# 4. PREPARE ORDER DATES
# ============================================================

delivered_orders["order_purchase_timestamp"] = pd.to_datetime(
    delivered_orders["order_purchase_timestamp"]
)

snapshot_date = delivered_orders["order_purchase_timestamp"].max()

print("\nRFM snapshot date:", snapshot_date)


# ============================================================
# 5. AGGREGATE PAYMENTS AT ORDER LEVEL
# ============================================================

order_payments = (
    payments
    .groupby("order_id", as_index=False)["payment_value"]
    .sum()
)

print("\nOrder-level payment table:", order_payments.shape)


# ============================================================
# 6. JOIN PAYMENT VALUE TO DELIVERED ORDERS
# ============================================================

delivered_orders = delivered_orders.merge(
    order_payments,
    on="order_id",
    how="left"
)

delivered_orders["payment_value"] = (
    delivered_orders["payment_value"]
    .fillna(0)
)


# ============================================================
# 7. BUILD RFM TABLE
# ============================================================

rfm = (
    delivered_orders
    .groupby("customer_unique_id")
    .agg(
        last_purchase=("order_purchase_timestamp", "max"),
        frequency=("order_id", "nunique"),
        monetary=("payment_value", "sum")
    )
    .reset_index()
)


# ============================================================
# 8. CALCULATE RECENCY
# ============================================================

rfm["recency"] = (
    snapshot_date - rfm["last_purchase"]
).dt.days


# ============================================================
# 9. REORDER COLUMNS
# ============================================================

rfm = rfm[
    [
        "customer_unique_id",
        "recency",
        "frequency",
        "monetary",
        "last_purchase"
    ]
]


# ============================================================
# 10. BASIC RFM SUMMARY
# ============================================================

print("\n" + "=" * 60)
print("RFM TABLE")
print("=" * 60)

print("\nShape:", rfm.shape)

print("\nFirst 10 customers:")
print(rfm.head(10))

print("\nRFM statistics:")

print(
    rfm[
        ["recency", "frequency", "monetary"]
    ].describe()
)


# ============================================================
# 11. DATA QUALITY CHECKS
# ============================================================

print("\n" + "=" * 60)
print("DATA QUALITY CHECKS")
print("=" * 60)

print("\nMissing RFM values:")

print(
    rfm[
        ["recency", "frequency", "monetary"]
    ].isna().sum()
)

print(
    "\nCustomers with zero monetary value:",
    (rfm["monetary"] == 0).sum()
)

print(
    "Customers with frequency = 1:",
    (rfm["frequency"] == 1).sum()
)

print(
    "Customers with frequency > 1:",
    (rfm["frequency"] > 1).sum()
)


# ============================================================
# 12. RFM SCORING
# ============================================================

print("\n" + "=" * 60)
print("RFM SCORING")
print("=" * 60)


# ------------------------------------------------------------
# RECENCY SCORE
#
# Lower recency = better customer activity.
# Customers are divided into five groups.
# Score 5 = most recent
# Score 1 = least recent
# ------------------------------------------------------------

rfm["recency_score"] = pd.qcut(
    rfm["recency"].rank(method="first"),
    q=5,
    labels=[5, 4, 3, 2, 1]
).astype(int)


# ------------------------------------------------------------
# MONETARY SCORE
#
# Higher monetary value = better.
# Score 5 = highest spending group
# Score 1 = lowest spending group
# ------------------------------------------------------------

rfm["monetary_score"] = pd.qcut(
    rfm["monetary"].rank(method="first"),
    q=5,
    labels=[1, 2, 3, 4, 5]
).astype(int)


# ------------------------------------------------------------
# FREQUENCY SCORE
#
# Frequency is extremely concentrated:
# most customers have exactly one order.
#
# Therefore we use business-defined bands instead
# of forcing frequency into five equal-sized groups.
# ------------------------------------------------------------

def frequency_score(frequency):

    if frequency == 1:
        return 1

    elif frequency == 2:
        return 2

    elif frequency == 3:
        return 3

    elif frequency <= 5:
        return 4

    else:
        return 5


rfm["frequency_score"] = rfm["frequency"].apply(
    frequency_score
)


# ============================================================
# 13. COMBINED RFM SCORE
# ============================================================

rfm["rfm_score"] = (
    rfm["recency_score"].astype(str)
    + rfm["frequency_score"].astype(str)
    + rfm["monetary_score"].astype(str)
)

rfm["rfm_total"] = (
    rfm["recency_score"]
    + rfm["frequency_score"]
    + rfm["monetary_score"]
)


print("\nRFM score distribution:")

print(
    rfm["rfm_total"]
    .value_counts()
    .sort_index()
)


# ============================================================
# 14. CUSTOMER SEGMENTATION
# ============================================================

def assign_segment(row):

    r = row["recency_score"]
    m = row["monetary_score"]
    frequency = row["frequency"]

    # Recent + repeat + high spending
    if r >= 4 and frequency >= 2 and m >= 4:
        return "Champions"

    # Recent + repeat customers
    elif r >= 4 and frequency >= 2:
        return "Loyal Customers"

    # Recent one-time customers
    elif r >= 4 and frequency == 1:
        return "Recent One-Time Customers"

    # Old but repeat customers
    elif r <= 2 and frequency >= 2:
        return "At Risk - Repeat Customers"

    # Old + high spending
    elif r <= 2 and m >= 4:
        return "At Risk - High Value"

    # Old + low spending
    elif r <= 2:
        return "Lost / Inactive"

    # Middle recency + high spending
    elif m >= 4:
        return "High Value"

    # Remaining customers
    else:
        return "Potential Customers"


rfm["customer_segment"] = rfm.apply(
    assign_segment,
    axis=1
)


# ============================================================
# 15. SEGMENT SUMMARY
# ============================================================

segment_summary = (
    rfm
    .groupby("customer_segment")
    .agg(
        customers=("customer_unique_id", "count"),
        avg_recency=("recency", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
        total_revenue=("monetary", "sum")
    )
    .reset_index()
    .sort_values(
        "total_revenue",
        ascending=False
    )
)

segment_summary["customer_percentage"] = (
    segment_summary["customers"]
    / len(rfm)
    * 100
)


# ============================================================
# 16. PRINT SEGMENT RESULTS
# ============================================================

print("\n" + "=" * 60)
print("CUSTOMER SEGMENTS")
print("=" * 60)

print("\nCustomer count by segment:")

print(
    rfm["customer_segment"]
    .value_counts()
)


print("\nSegment summary:")

print(
    segment_summary.to_string(
        index=False
    )
)


# ============================================================
# 17. SAVE RFM DATASET
# ============================================================

OUTPUT_PATH = (
    r"C:\Users\Rachitesh Sharma\Documents"
    r"\Business-Decision-Intelligence\01_data"
    r"\rfm_customer_analysis.csv"
)

rfm.to_csv(
    OUTPUT_PATH,
    index=False
)


# ============================================================
# 18. SAVE SEGMENT SUMMARY
# ============================================================

SEGMENT_OUTPUT_PATH = (
    r"C:\Users\Rachitesh Sharma\Documents"
    r"\Business-Decision-Intelligence\01_data"
    r"\rfm_segment_summary.csv"
)

segment_summary.to_csv(
    SEGMENT_OUTPUT_PATH,
    index=False
)


print("\nRFM analysis saved to:")
print(OUTPUT_PATH)

print("\nSegment summary saved to:")
print(SEGMENT_OUTPUT_PATH)


print("\n" + "=" * 60)
print("RFM ANALYSIS COMPLETE")
print("=" * 60)