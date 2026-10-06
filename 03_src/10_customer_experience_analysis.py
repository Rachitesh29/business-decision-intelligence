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
print("CUSTOMER EXPERIENCE & REVIEW ANALYTICS")
print("=" * 70)

print(f"\nDatabase: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)


# ============================================================
# 1. LOAD REQUIRED TABLES
# ============================================================

print("\nLoading data...")

reviews = pd.read_sql_query(
    """
    SELECT
        review_id,
        order_id,
        review_score,
        review_comment_title,
        review_comment_message,
        review_creation_date,
        review_answer_timestamp
    FROM reviews
    """,
    conn
)

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

conn.close()

print(f"Reviews:   {reviews.shape}")
print(f"Orders:    {orders.shape}")
print(f"Customers: {customers.shape}")


# ============================================================
# 2. DATE CONVERSION
# ============================================================

date_columns_reviews = [
    "review_creation_date",
    "review_answer_timestamp"
]

for column in date_columns_reviews:
    reviews[column] = pd.to_datetime(
        reviews[column],
        errors="coerce"
    )

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


# ============================================================
# 3. BASIC REVIEW VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("REVIEW DATA VALIDATION")
print("=" * 70)

print(
    "\nUnique review IDs:",
    reviews["review_id"].nunique()
)

print(
    "Unique review order IDs:",
    reviews["order_id"].nunique()
)

print(
    "Missing review scores:",
    reviews["review_score"].isna().sum()
)

print(
    "Missing review titles:",
    reviews["review_comment_title"].isna().sum()
)

print(
    "Missing review messages:",
    reviews["review_comment_message"].isna().sum()
)

print(
    "Invalid review scores:",
    (~reviews["review_score"].isin([1, 2, 3, 4, 5])).sum()
)


# ============================================================
# 4. REVIEW SCORE DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("REVIEW SCORE DISTRIBUTION")
print("=" * 70)

review_score_distribution = (
    reviews["review_score"]
    .value_counts()
    .sort_index()
    .rename_axis("review_score")
    .reset_index(name="reviews")
)

review_score_distribution["percentage"] = (
    review_score_distribution["reviews"]
    / len(reviews)
    * 100
)

print(
    review_score_distribution.to_string(index=False)
)


# ============================================================
# 5. OVERALL REVIEW KPI
# ============================================================

average_review_score = reviews["review_score"].mean()

five_star_count = (
    reviews["review_score"] == 5
).sum()

one_star_count = (
    reviews["review_score"] == 1
).sum()

low_rating_count = (
    reviews["review_score"] <= 2
).sum()

high_rating_count = (
    reviews["review_score"] >= 4
).sum()

review_kpi = pd.DataFrame(
    {
        "metric": [
            "Total reviews",
            "Average review score",
            "Five-star reviews",
            "One-star reviews",
            "Low-rating reviews (1-2)",
            "High-rating reviews (4-5)"
        ],
        "value": [
            len(reviews),
            average_review_score,
            five_star_count,
            one_star_count,
            low_rating_count,
            high_rating_count
        ]
    }
)

print("\nOverall review KPIs:\n")

print(
    review_kpi.to_string(index=False)
)


# ============================================================
# 6. REVIEW SCORE BY DELIVERY PERFORMANCE
# ============================================================

print("\n" + "=" * 70)
print("REVIEW SCORE VS DELIVERY PERFORMANCE")
print("=" * 70)

delivered_orders = orders[
    orders["order_status"] == "delivered"
].copy()

# Use a clean delivery classification directly from dates.
delivered_orders["delivery_variance_days"] = (
    (
        delivered_orders["order_delivered_customer_date"]
        - delivered_orders["order_estimated_delivery_date"]
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


delivered_orders["delivery_performance_clean"] = (
    delivered_orders["delivery_variance_days"]
    .apply(classify_delivery)
)


review_delivery = reviews.merge(
    delivered_orders[
        [
            "order_id",
            "delivery_days",
            "delivery_variance_days",
            "delivery_performance_clean"
        ]
    ],
    on="order_id",
    how="inner"
)

review_by_delivery_performance = (
    review_delivery
    .groupby("delivery_performance_clean")
    .agg(
        reviews=("review_id", "nunique"),
        average_review_score=("review_score", "mean"),
        median_review_score=("review_score", "median"),
        average_delivery_days=("delivery_days", "mean"),
        average_delivery_variance_days=(
            "delivery_variance_days",
            "mean"
        ),
        low_rating_reviews=(
            "review_score",
            lambda x: (x <= 2).sum()
        ),
        high_rating_reviews=(
            "review_score",
            lambda x: (x >= 4).sum()
        )
    )
    .reset_index()
)

review_by_delivery_performance["low_rating_pct"] = (
    review_by_delivery_performance["low_rating_reviews"]
    / review_by_delivery_performance["reviews"]
    * 100
)

review_by_delivery_performance["high_rating_pct"] = (
    review_by_delivery_performance["high_rating_reviews"]
    / review_by_delivery_performance["reviews"]
    * 100
)

print(
    review_by_delivery_performance.to_string(index=False)
)


# ============================================================
# 7. REVIEW SCORE VS DELIVERY TIME BUCKET
# ============================================================

print("\n" + "=" * 70)
print("REVIEW SCORE VS DELIVERY TIME")
print("=" * 70)


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


review_delivery["delivery_time_bucket"] = (
    review_delivery["delivery_days"]
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

review_by_delivery_bucket = (
    review_delivery
    .groupby("delivery_time_bucket")
    .agg(
        reviews=("review_id", "nunique"),
        average_review_score=("review_score", "mean"),
        median_review_score=("review_score", "median"),
        low_rating_reviews=(
            "review_score",
            lambda x: (x <= 2).sum()
        ),
        high_rating_reviews=(
            "review_score",
            lambda x: (x >= 4).sum()
        )
    )
    .reindex(bucket_order)
    .reset_index()
)

review_by_delivery_bucket["low_rating_pct"] = (
    review_by_delivery_bucket["low_rating_reviews"]
    / review_by_delivery_bucket["reviews"]
    * 100
)

review_by_delivery_bucket["high_rating_pct"] = (
    review_by_delivery_bucket["high_rating_reviews"]
    / review_by_delivery_bucket["reviews"]
    * 100
)

print(
    review_by_delivery_bucket.to_string(index=False)
)


# ============================================================
# 8. REVIEW SCORE BY MONTH
# ============================================================

print("\n" + "=" * 70)
print("MONTHLY REVIEW PERFORMANCE")
print("=" * 70)

reviews["review_month"] = (
    reviews["review_creation_date"]
    .dt.to_period("M")
    .astype(str)
)

monthly_reviews = (
    reviews
    .groupby("review_month")
    .agg(
        reviews=("review_id", "nunique"),
        average_review_score=("review_score", "mean"),
        five_star_reviews=(
            "review_score",
            lambda x: (x == 5).sum()
        ),
        one_star_reviews=(
            "review_score",
            lambda x: (x == 1).sum()
        ),
        low_rating_reviews=(
            "review_score",
            lambda x: (x <= 2).sum()
        )
    )
    .reset_index()
)

monthly_reviews["five_star_pct"] = (
    monthly_reviews["five_star_reviews"]
    / monthly_reviews["reviews"]
    * 100
)

monthly_reviews["one_star_pct"] = (
    monthly_reviews["one_star_reviews"]
    / monthly_reviews["reviews"]
    * 100
)

monthly_reviews["low_rating_pct"] = (
    monthly_reviews["low_rating_reviews"]
    / monthly_reviews["reviews"]
    * 100
)

print(
    monthly_reviews.to_string(index=False)
)


# ============================================================
# 9. CUSTOMER STATE REVIEW ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("CUSTOMER STATE REVIEW ANALYSIS")
print("=" * 70)

review_customer_state = reviews.merge(
    orders[
        [
            "order_id",
            "customer_id"
        ]
    ],
    on="order_id",
    how="left"
)

review_customer_state = review_customer_state.merge(
    customers[
        [
            "customer_id",
            "customer_unique_id",
            "customer_state"
        ]
    ],
    on="customer_id",
    how="left"
)

state_review_analysis = (
    review_customer_state
    .groupby("customer_state")
    .agg(
        reviews=("review_id", "nunique"),
        customers=("customer_unique_id", "nunique"),
        average_review_score=("review_score", "mean"),
        median_review_score=("review_score", "median"),
        one_star_reviews=(
            "review_score",
            lambda x: (x == 1).sum()
        ),
        low_rating_reviews=(
            "review_score",
            lambda x: (x <= 2).sum()
        ),
        high_rating_reviews=(
            "review_score",
            lambda x: (x >= 4).sum()
        )
    )
    .reset_index()
)

state_review_analysis["low_rating_pct"] = (
    state_review_analysis["low_rating_reviews"]
    / state_review_analysis["reviews"]
    * 100
)

state_review_analysis["high_rating_pct"] = (
    state_review_analysis["high_rating_reviews"]
    / state_review_analysis["reviews"]
    * 100
)

state_review_analysis = state_review_analysis.sort_values(
    "reviews",
    ascending=False
).reset_index(drop=True)

print(
    state_review_analysis.to_string(index=False)
)


# ============================================================
# 10. REVIEW RESPONSE ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("REVIEW RESPONSE ANALYSIS")
print("=" * 70)

reviews["has_review_answer"] = (
    reviews["review_answer_timestamp"].notna()
)

review_response_analysis = pd.DataFrame(
    {
        "metric": [
            "Total reviews",
            "Reviews with seller response",
            "Reviews without seller response",
            "Response coverage pct"
        ],
        "value": [
            len(reviews),
            reviews["has_review_answer"].sum(),
            (~reviews["has_review_answer"]).sum(),
            reviews["has_review_answer"].mean() * 100
        ]
    }
)

print(
    review_response_analysis.to_string(index=False)
)


# ============================================================
# 11. RESPONSE COVERAGE BY REVIEW SCORE
# ============================================================

response_by_score = (
    reviews
    .groupby("review_score")
    .agg(
        reviews=("review_score", "size"),
        responded_reviews=(
            "has_review_answer",
            "sum"
        )
    )
    .reset_index()
)

response_by_score["response_rate_pct"] = (
    response_by_score["responded_reviews"]
    / response_by_score["reviews"]
    * 100
)

print("\nResponse coverage by review score:\n")

print(
    response_by_score.to_string(index=False)
)


# ============================================================
# 12. REVIEW TEXT AVAILABILITY
# ============================================================

reviews["has_review_title"] = (
    reviews["review_comment_title"]
    .fillna("")
    .str.strip()
    .ne("")
)

reviews["has_review_message"] = (
    reviews["review_comment_message"]
    .fillna("")
    .str.strip()
    .ne("")
)

reviews["has_any_text"] = (
    reviews["has_review_title"]
    | reviews["has_review_message"]
)

review_text_summary = pd.DataFrame(
    {
        "metric": [
            "Total reviews",
            "Reviews with title",
            "Reviews with message",
            "Reviews with any text",
            "Reviews without any text"
        ],
        "value": [
            len(reviews),
            reviews["has_review_title"].sum(),
            reviews["has_review_message"].sum(),
            reviews["has_any_text"].sum(),
            (~reviews["has_any_text"]).sum()
        ]
    }
)

print("\n" + "=" * 70)
print("REVIEW TEXT AVAILABILITY")
print("=" * 70)

print(
    review_text_summary.to_string(index=False)
)


# ============================================================
# 13. TEXT AVAILABILITY BY REVIEW SCORE
# ============================================================

text_by_score = (
    reviews
    .groupby("review_score")
    .agg(
        reviews=("review_id", "nunique"),
        reviews_with_text=("has_any_text", "sum")
    )
    .reset_index()
)

text_by_score["text_availability_pct"] = (
    text_by_score["reviews_with_text"]
    / text_by_score["reviews"]
    * 100
)

print("\nText availability by score:\n")

print(
    text_by_score.to_string(index=False)
)


# ============================================================
# 14. REVIEW SCORE VS DELIVERY CORRELATION
# ============================================================

print("\n" + "=" * 70)
print("DELIVERY / REVIEW CORRELATION")
print("=" * 70)

correlation_data = review_delivery[
    [
        "review_score",
        "delivery_days",
        "delivery_variance_days"
    ]
].dropna()

correlation_summary = pd.DataFrame(
    {
        "relationship": [
            "Review score vs delivery days",
            "Review score vs delivery variance"
        ],
        "correlation": [
            correlation_data[
                "review_score"
            ].corr(
                correlation_data["delivery_days"]
            ),
            correlation_data[
                "review_score"
            ].corr(
                correlation_data["delivery_variance_days"]
            )
        ]
    }
)

print(
    correlation_summary.to_string(index=False)
)


# ============================================================
# 15. EXTREME LOW-RATING DELIVERY CASES
# ============================================================

low_rating_delivery = review_delivery[
    review_delivery["review_score"] <= 2
].copy()

low_rating_delivery_summary = (
    low_rating_delivery
    .groupby("delivery_time_bucket")
    .agg(
        low_rating_reviews=("review_id", "nunique"),
        average_review_score=("review_score", "mean"),
        average_delivery_days=("delivery_days", "mean"),
        average_delivery_variance_days=(
            "delivery_variance_days",
            "mean"
        )
    )
    .reset_index()
)

low_rating_delivery_summary = (
    low_rating_delivery_summary
    .set_index("delivery_time_bucket")
    .reindex(bucket_order)
    .reset_index()
)

print("\n" + "=" * 70)
print("LOW-RATING REVIEWS BY DELIVERY TIME")
print("=" * 70)

print(
    low_rating_delivery_summary.to_string(index=False)
)


# ============================================================
# 16. DATA QUALITY CHECKS
# ============================================================

print("\n" + "=" * 70)
print("DATA QUALITY CHECKS")
print("=" * 70)

invalid_scores = (
    (~reviews["review_score"].isin([1, 2, 3, 4, 5]))
    & reviews["review_score"].notna()
).sum()

missing_scores = (
    reviews["review_score"].isna()
).sum()

review_order_match = reviews["order_id"].isin(
    orders["order_id"]
).sum()

print(
    f"\nInvalid review scores: {invalid_scores}"
)

print(
    f"Missing review scores: {missing_scores}"
)

print(
    f"Reviews matching orders: "
    f"{review_order_match} / {len(reviews)}"
)

print(
    f"Reviews without matching orders: "
    f"{len(reviews) - review_order_match}"
)

print(
    f"Review rows with any text: "
    f"{reviews['has_any_text'].sum()}"
)


# ============================================================
# 17. SAVE OUTPUTS
# ============================================================

print("\n" + "=" * 70)
print("SAVING OUTPUTS")
print("=" * 70)

review_score_distribution.to_csv(
    OUTPUT_DIR / "review_score_distribution.csv",
    index=False
)

review_kpi.to_csv(
    OUTPUT_DIR / "review_kpi.csv",
    index=False
)

review_by_delivery_performance.to_csv(
    OUTPUT_DIR / "review_by_delivery_performance.csv",
    index=False
)

review_by_delivery_bucket.to_csv(
    OUTPUT_DIR / "review_by_delivery_bucket.csv",
    index=False
)

monthly_reviews.to_csv(
    OUTPUT_DIR / "monthly_review_analysis.csv",
    index=False
)

state_review_analysis.to_csv(
    OUTPUT_DIR / "state_review_analysis.csv",
    index=False
)

review_response_analysis.to_csv(
    OUTPUT_DIR / "review_response_analysis.csv",
    index=False
)

response_by_score.to_csv(
    OUTPUT_DIR / "review_response_by_score.csv",
    index=False
)

review_text_summary.to_csv(
    OUTPUT_DIR / "review_text_summary.csv",
    index=False
)

text_by_score.to_csv(
    OUTPUT_DIR / "review_text_by_score.csv",
    index=False
)

correlation_summary.to_csv(
    OUTPUT_DIR / "review_delivery_correlation.csv",
    index=False
)

low_rating_delivery_summary.to_csv(
    OUTPUT_DIR / "low_rating_delivery_analysis.csv",
    index=False
)


# ============================================================
# 18. FINAL SUMMARY
# ============================================================

print("\nSaved files:")

output_files = [
    "review_score_distribution.csv",
    "review_kpi.csv",
    "review_by_delivery_performance.csv",
    "review_by_delivery_bucket.csv",
    "monthly_review_analysis.csv",
    "state_review_analysis.csv",
    "review_response_analysis.csv",
    "review_response_by_score.csv",
    "review_text_summary.csv",
    "review_text_by_score.csv",
    "review_delivery_correlation.csv",
    "low_rating_delivery_analysis.csv"
]

for filename in output_files:
    print(f"  ✓ 01_data/{filename}")


print("\n" + "=" * 70)
print("CUSTOMER EXPERIENCE & REVIEW ANALYTICS COMPLETE")
print("=" * 70)