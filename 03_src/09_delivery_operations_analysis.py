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
# DATABASE
# ============================================================

print("=" * 70)
print("DELIVERY & OPERATIONS ANALYTICS")
print("=" * 70)

conn = sqlite3.connect(DB_PATH)

orders = pd.read_sql_query(
    """
    SELECT
        order_id,
        customer_id,
        order_status,
        order_purchase_timestamp,
        order_approved_at,
        order_delivered_carrier_date,
        order_delivered_customer_date,
        order_estimated_delivery_date,
        delivery_days,
        is_delivered
    FROM orders
    """,
    conn
)

conn.close()

print("\nOrders:", orders.shape)


# ============================================================
# DATE CONVERSION
# ============================================================

date_columns = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date"
]

for col in date_columns:
    orders[col] = pd.to_datetime(
        orders[col],
        errors="coerce"
    )


# ============================================================
# DELIVERED ORDERS
# ============================================================

delivered = orders[
    orders["order_status"] == "delivered"
].copy()

print("Delivered orders:", len(delivered))


# ============================================================
# 1. CREATE CLEAN DELIVERY VARIANCE
# ============================================================
# Negative = delivered early
# Zero     = delivered on estimated date
# Positive = delivered late
#
# IMPORTANT:
# We deliberately do NOT call negative values "negative delay".
# ============================================================

delivered["delivery_variance_days"] = (
    (
        delivered["order_delivered_customer_date"]
        - delivered["order_estimated_delivery_date"]
    )
    .dt.total_seconds()
    / 86400
)


def classify_delivery(row):
    variance = row["delivery_variance_days"]

    if pd.isna(variance):
        return "Unknown"

    if variance < 0:
        return "Early"

    if variance > 0:
        return "Late"

    return "On Time"


delivered["delivery_performance_clean"] = (
    delivered.apply(
        classify_delivery,
        axis=1
    )
)


# ============================================================
# 2. DELIVERY KPI SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("DELIVERY KPI SUMMARY")
print("=" * 70)

late_count = (
    delivered["delivery_performance_clean"] == "Late"
).sum()

early_count = (
    delivered["delivery_performance_clean"] == "Early"
).sum()

on_time_count = (
    delivered["delivery_performance_clean"] == "On Time"
).sum()

unknown_count = (
    delivered["delivery_performance_clean"] == "Unknown"
).sum()

delivery_kpi = pd.DataFrame(
    {
        "metric": [
            "Total orders",
            "Delivered orders",
            "Non-delivered orders",
            "Delivery rate pct",
            "Average delivery days",
            "Median delivery days",
            "Average delivery variance days",
            "Late orders",
            "Early orders",
            "On-time orders",
            "Unknown performance orders",
            "Late delivery rate pct",
            "Early delivery rate pct",
            "On-time delivery rate pct"
        ],
        "value": [
            len(orders),
            len(delivered),
            len(orders) - len(delivered),
            len(delivered) / len(orders) * 100,
            delivered["delivery_days"].mean(),
            delivered["delivery_days"].median(),
            delivered["delivery_variance_days"].mean(),
            late_count,
            early_count,
            on_time_count,
            unknown_count,
            late_count / len(delivered) * 100,
            early_count / len(delivered) * 100,
            on_time_count / len(delivered) * 100
        ]
    }
)

print(
    delivery_kpi.to_string(index=False)
)


# ============================================================
# 3. DELIVERY PERFORMANCE DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("DELIVERY PERFORMANCE DISTRIBUTION")
print("=" * 70)

performance_distribution = (
    delivered["delivery_performance_clean"]
    .value_counts()
    .rename_axis("delivery_performance")
    .reset_index(name="orders")
)

performance_distribution["percentage"] = (
    performance_distribution["orders"]
    / len(delivered)
    * 100
)

print(
    performance_distribution.to_string(index=False)
)


# ============================================================
# 4. DELIVERY TIME DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("DELIVERY TIME DISTRIBUTION")
print("=" * 70)

delivery_time_summary = (
    delivered["delivery_days"]
    .describe()
    .reset_index()
)

delivery_time_summary.columns = [
    "statistic",
    "delivery_days"
]

print(
    delivery_time_summary.to_string(index=False)
)


# ============================================================
# 5. DELIVERY TIME BUCKETS
# ============================================================

def delivery_bucket(days):

    if pd.isna(days):
        return "Unknown"

    if days <= 5:
        return "0-5 days"

    if days <= 10:
        return "6-10 days"

    if days <= 15:
        return "11-15 days"

    if days <= 20:
        return "16-20 days"

    if days <= 30:
        return "21-30 days"

    return "30+ days"


delivered["delivery_time_bucket"] = (
    delivered["delivery_days"]
    .apply(delivery_bucket)
)

bucket_order = [
    "0-5 days",
    "6-10 days",
    "11-15 days",
    "16-20 days",
    "21-30 days",
    "30+ days",
    "Unknown"
]

delivery_bucket_analysis = (
    delivered["delivery_time_bucket"]
    .value_counts()
    .reindex(
        bucket_order,
        fill_value=0
    )
    .rename_axis("delivery_time_bucket")
    .reset_index(name="orders")
)

delivery_bucket_analysis["percentage"] = (
    delivery_bucket_analysis["orders"]
    / len(delivered)
    * 100
)

print("\nDelivery time buckets:\n")

print(
    delivery_bucket_analysis.to_string(index=False)
)


# ============================================================
# 6. MONTHLY DELIVERY PERFORMANCE
# ============================================================

print("\n" + "=" * 70)
print("MONTHLY DELIVERY PERFORMANCE")
print("=" * 70)

delivered["purchase_month"] = (
    delivered["order_purchase_timestamp"]
    .dt.to_period("M")
    .astype(str)
)

monthly_delivery = (
    delivered
    .groupby("purchase_month")
    .agg(
        delivered_orders=("order_id", "nunique"),
        avg_delivery_days=("delivery_days", "mean"),
        median_delivery_days=("delivery_days", "median"),
        avg_delivery_variance_days=(
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
        ),
        unknown_orders=(
            "delivery_performance_clean",
            lambda x: (x == "Unknown").sum()
        )
    )
    .reset_index()
)

monthly_delivery["late_rate_pct"] = (
    monthly_delivery["late_orders"]
    / monthly_delivery["delivered_orders"]
    * 100
)

monthly_delivery["early_rate_pct"] = (
    monthly_delivery["early_orders"]
    / monthly_delivery["delivered_orders"]
    * 100
)

monthly_delivery["on_time_rate_pct"] = (
    monthly_delivery["on_time_orders"]
    / monthly_delivery["delivered_orders"]
    * 100
)

print(
    monthly_delivery.to_string(index=False)
)


# ============================================================
# 7. DELIVERY VARIANCE ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("DELIVERY VARIANCE ANALYSIS")
print("=" * 70)

variance_summary = (
    delivered["delivery_variance_days"]
    .describe()
    .reset_index()
)

variance_summary.columns = [
    "statistic",
    "delivery_variance_days"
]

print(
    variance_summary.to_string(index=False)
)


# ============================================================
# 8. EXTREME DELIVERY CASES
# ============================================================

print("\n" + "=" * 70)
print("EXTREME DELIVERY CASES")
print("=" * 70)

extreme_deliveries = (
    delivered[
        [
            "order_id",
            "order_purchase_timestamp",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
            "delivery_days",
            "delivery_variance_days",
            "delivery_performance_clean"
        ]
    ]
    .sort_values(
        "delivery_days",
        ascending=False
    )
    .head(20)
)

print(
    extreme_deliveries.to_string(index=False)
)


# ============================================================
# 9. VERY LATE ORDERS
# ============================================================

very_late_orders = delivered[
    delivered["delivery_variance_days"] > 30
].copy()

very_late_summary = pd.DataFrame(
    {
        "metric": [
            "Orders more than 30 days late",
            "Percentage of delivered orders"
        ],
        "value": [
            len(very_late_orders),
            len(very_late_orders)
            / len(delivered)
            * 100
        ]
    }
)

print("\nOrders more than 30 days late:\n")

print(
    very_late_summary.to_string(index=False)
)


# ============================================================
# 10. APPROVAL → CARRIER TIME
# ============================================================

delivered["approval_to_carrier_days"] = (
    (
        delivered["order_delivered_carrier_date"]
        - delivered["order_approved_at"]
    )
    .dt.total_seconds()
    / 86400
)

approval_to_carrier = delivered[
    delivered["approval_to_carrier_days"].notna()
].copy()

approval_carrier_summary = (
    approval_to_carrier["approval_to_carrier_days"]
    .describe()
    .reset_index()
)

approval_carrier_summary.columns = [
    "statistic",
    "approval_to_carrier_days"
]

print("\n" + "=" * 70)
print("APPROVAL TO CARRIER TIME")
print("=" * 70)

print(
    approval_carrier_summary.to_string(index=False)
)


# ============================================================
# 11. FLAG IMPOSSIBLE APPROVAL → CARRIER VALUES
# ============================================================

negative_approval_carrier = (
    approval_to_carrier[
        approval_to_carrier["approval_to_carrier_days"] < 0
    ]
)

print(
    "\nNegative approval-to-carrier durations:",
    len(negative_approval_carrier)
)


# ============================================================
# 12. MONTHLY CARRIER HANDLING
# ============================================================

monthly_carrier_handling = (
    approval_to_carrier
    .assign(
        purchase_month=(
            approval_to_carrier[
                "order_purchase_timestamp"
            ]
            .dt.to_period("M")
            .astype(str)
        )
    )
    .groupby("purchase_month")
    .agg(
        orders=("order_id", "nunique"),
        avg_approval_to_carrier_days=(
            "approval_to_carrier_days",
            "mean"
        ),
        median_approval_to_carrier_days=(
            "approval_to_carrier_days",
            "median"
        )
    )
    .reset_index()
)

print(
    "\nMonthly approval-to-carrier performance:\n"
)

print(
    monthly_carrier_handling.to_string(index=False)
)


# ============================================================
# 13. DELIVERY PERFORMANCE BY WEEKDAY
# ============================================================

delivered["purchase_weekday"] = (
    delivered["order_purchase_timestamp"]
    .dt.day_name()
)

weekday_order = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

weekday_delivery = (
    delivered
    .groupby("purchase_weekday")
    .agg(
        orders=("order_id", "nunique"),
        avg_delivery_days=("delivery_days", "mean"),
        median_delivery_days=("delivery_days", "median"),
        late_orders=(
            "delivery_performance_clean",
            lambda x: (x == "Late").sum()
        )
    )
    .reindex(weekday_order)
    .reset_index()
)

weekday_delivery["late_rate_pct"] = (
    weekday_delivery["late_orders"]
    / weekday_delivery["orders"]
    * 100
)

print("\n" + "=" * 70)
print("DELIVERY PERFORMANCE BY PURCHASE WEEKDAY")
print("=" * 70)

print(
    weekday_delivery.to_string(index=False)
)


# ============================================================
# 14. ORDER STATUS OPERATIONAL SUMMARY
# ============================================================

status_analysis = (
    orders
    .groupby("order_status")
    .agg(
        orders=("order_id", "nunique"),
        avg_delivery_days=("delivery_days", "mean")
    )
    .reset_index()
)

status_analysis["percentage"] = (
    status_analysis["orders"]
    / len(orders)
    * 100
)

status_analysis = status_analysis.sort_values(
    "orders",
    ascending=False
)

print("\n" + "=" * 70)
print("ORDER STATUS OPERATIONAL SUMMARY")
print("=" * 70)

print(
    status_analysis.to_string(index=False)
)


# ============================================================
# 15. NON-DELIVERED ORDERS
# ============================================================

non_delivered = orders[
    orders["order_status"] != "delivered"
].copy()

non_delivered_status = (
    non_delivered["order_status"]
    .value_counts()
    .rename_axis("order_status")
    .reset_index(name="orders")
)

non_delivered_status["percentage_of_non_delivered"] = (
    non_delivered_status["orders"]
    / len(non_delivered)
    * 100
)

print("\n" + "=" * 70)
print("NON-DELIVERED ORDER ANALYSIS")
print("=" * 70)

print(
    non_delivered_status.to_string(index=False)
)


# ============================================================
# 16. MISSING DELIVERY DATE ANALYSIS
# ============================================================

missing_delivery_dates = pd.DataFrame(
    {
        "metric": [
            "Delivered orders",
            "Missing approval date",
            "Missing carrier date",
            "Missing customer delivery date",
            "Missing estimated delivery date"
        ],
        "orders": [
            len(delivered),
            delivered["order_approved_at"].isna().sum(),
            delivered["order_delivered_carrier_date"].isna().sum(),
            delivered[
                "order_delivered_customer_date"
            ].isna().sum(),
            delivered[
                "order_estimated_delivery_date"
            ].isna().sum()
        ]
    }
)

print("\n" + "=" * 70)
print("MISSING DELIVERY DATE CHECK")
print("=" * 70)

print(
    missing_delivery_dates.to_string(index=False)
)


# ============================================================
# 17. DATA QUALITY VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("DATA QUALITY VALIDATION")
print("=" * 70)

negative_delivery_days = (
    delivered["delivery_days"] < 0
).sum()

negative_variance_count = (
    delivered["delivery_variance_days"] < 0
).sum()

positive_variance_count = (
    delivered["delivery_variance_days"] > 0
).sum()

zero_variance_count = (
    delivered["delivery_variance_days"] == 0
).sum()

missing_variance_count = (
    delivered["delivery_variance_days"].isna()
).sum()

negative_approval_carrier_count = (
    delivered["approval_to_carrier_days"] < 0
).sum()

print(
    f"\nNegative delivery durations: "
    f"{negative_delivery_days}"
)

print(
    f"Early delivery records: "
    f"{negative_variance_count}"
)

print(
    f"Late delivery records: "
    f"{positive_variance_count}"
)

print(
    f"Exactly on estimated date: "
    f"{zero_variance_count}"
)

print(
    f"Missing delivery variance: "
    f"{missing_variance_count}"
)

print(
    f"Negative approval-to-carrier durations: "
    f"{negative_approval_carrier_count}"
)


# ============================================================
# 18. SAVE OUTPUTS
# ============================================================

print("\n" + "=" * 70)
print("SAVING OUTPUTS")
print("=" * 70)

delivery_kpi.to_csv(
    OUTPUT_DIR / "delivery_kpi.csv",
    index=False
)

performance_distribution.to_csv(
    OUTPUT_DIR / "delivery_performance_distribution.csv",
    index=False
)

delivery_time_summary.to_csv(
    OUTPUT_DIR / "delivery_time_summary.csv",
    index=False
)

delivery_bucket_analysis.to_csv(
    OUTPUT_DIR / "delivery_time_buckets.csv",
    index=False
)

monthly_delivery.to_csv(
    OUTPUT_DIR / "monthly_delivery_analysis.csv",
    index=False
)

variance_summary.to_csv(
    OUTPUT_DIR / "delivery_variance_summary.csv",
    index=False
)

extreme_deliveries.to_csv(
    OUTPUT_DIR / "extreme_delivery_orders.csv",
    index=False
)

very_late_summary.to_csv(
    OUTPUT_DIR / "very_late_orders_summary.csv",
    index=False
)

approval_carrier_summary.to_csv(
    OUTPUT_DIR / "approval_to_carrier_summary.csv",
    index=False
)

monthly_carrier_handling.to_csv(
    OUTPUT_DIR / "monthly_carrier_handling.csv",
    index=False
)

weekday_delivery.to_csv(
    OUTPUT_DIR / "weekday_delivery_analysis.csv",
    index=False
)

status_analysis.to_csv(
    OUTPUT_DIR / "order_status_operational_analysis.csv",
    index=False
)

non_delivered_status.to_csv(
    OUTPUT_DIR / "non_delivered_orders_analysis.csv",
    index=False
)

missing_delivery_dates.to_csv(
    OUTPUT_DIR / "missing_delivery_dates.csv",
    index=False
)


# ============================================================
# 19. FINAL SUMMARY
# ============================================================

print("\nSaved files:")

output_files = [
    "delivery_kpi.csv",
    "delivery_performance_distribution.csv",
    "delivery_time_summary.csv",
    "delivery_time_buckets.csv",
    "monthly_delivery_analysis.csv",
    "delivery_variance_summary.csv",
    "extreme_delivery_orders.csv",
    "very_late_orders_summary.csv",
    "approval_to_carrier_summary.csv",
    "monthly_carrier_handling.csv",
    "weekday_delivery_analysis.csv",
    "order_status_operational_analysis.csv",
    "non_delivered_orders_analysis.csv",
    "missing_delivery_dates.csv"
]

for filename in output_files:
    print(f"  ✓ 01_data/{filename}")


print("\n" + "=" * 70)
print("DELIVERY & OPERATIONS ANALYTICS COMPLETE")
print("=" * 70)