from pathlib import Path
import sqlite3
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DB_PATH = PROJECT_ROOT / "04_sql" / "business_intelligence.db"


print("=" * 75)
print("CATEGORY SALES RECONCILIATION DIAGNOSTIC")
print("=" * 75)

print(f"\nDatabase: {DB_PATH}")


# ============================================================
# LOAD DATA
# ============================================================

conn = sqlite3.connect(DB_PATH)

order_items = pd.read_sql_query(
    """
    SELECT
        order_id,
        order_item_id,
        product_id,
        price,
        freight_value
    FROM order_items
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

translation = pd.read_sql_query(
    """
    SELECT
        product_category_name,
        product_category_name_english
    FROM category_translation
    """,
    conn
)

conn.close()


# ============================================================
# 1. RAW SALES BASELINE
# ============================================================

print("\n" + "=" * 75)
print("1. RAW SALES BASELINE")
print("=" * 75)

raw_sales = order_items["price"].sum()

print(f"\nRaw order_items rows: {len(order_items):,}")
print(f"Raw order_items sales: {raw_sales:,.2f}")


# ============================================================
# 2. CHECK PRODUCT MATCHING
# ============================================================

print("\n" + "=" * 75)
print("2. PRODUCT MATCHING")
print("=" * 75)

items_with_product = order_items.merge(
    products,
    on="product_id",
    how="left",
    indicator=True
)

missing_product = (
    items_with_product["_merge"] == "left_only"
)

missing_product_sales = (
    items_with_product.loc[
        missing_product,
        "price"
    ].sum()
)

print(
    f"\nItems without matching product: "
    f"{missing_product.sum():,}"
)

print(
    f"Sales from unmatched products: "
    f"{missing_product_sales:,.2f}"
)


# ============================================================
# 3. CHECK MISSING PRODUCT CATEGORIES
# ============================================================

print("\n" + "=" * 75)
print("3. PRODUCT CATEGORY CHECK")
print("=" * 75)

missing_category = (
    items_with_product["product_category_name"]
    .isna()
)

missing_category_sales = (
    items_with_product.loc[
        missing_category,
        "price"
    ].sum()
)

print(
    f"\nItems with missing category: "
    f"{missing_category.sum():,}"
)

print(
    f"Sales from missing categories: "
    f"{missing_category_sales:,.2f}"
)


# ============================================================
# 4. CATEGORY TRANSLATION MATCH
# ============================================================

print("\n" + "=" * 75)
print("4. CATEGORY TRANSLATION CHECK")
print("=" * 75)

items_with_category = items_with_product.merge(
    translation,
    on="product_category_name",
    how="left",
    indicator="translation_match"
)

missing_translation = (
    items_with_category["translation_match"]
    == "left_only"
)

missing_translation_sales = (
    items_with_category.loc[
        missing_translation,
        "price"
    ].sum()
)

print(
    f"\nItems without translation match: "
    f"{missing_translation.sum():,}"
)

print(
    f"Sales from untranslated categories: "
    f"{missing_translation_sales:,.2f}"
)


# ============================================================
# 5. CHECK FINAL CATEGORY FIELD
# ============================================================

items_with_category["final_category"] = (
    items_with_category[
        "product_category_name_english"
    ]
    .fillna(
        items_with_category[
            "product_category_name"
        ]
    )
)

missing_final_category = (
    items_with_category["final_category"]
    .isna()
)

missing_final_sales = (
    items_with_category.loc[
        missing_final_category,
        "price"
    ].sum()
)

print("\n" + "=" * 75)
print("5. FINAL CATEGORY CHECK")
print("=" * 75)

print(
    f"\nItems without final category: "
    f"{missing_final_category.sum():,}"
)

print(
    f"Sales without final category: "
    f"{missing_final_sales:,.2f}"
)


# ============================================================
# 6. CATEGORY SALES TOTAL
# ============================================================

category_sales = (
    items_with_category
    .groupby("final_category", as_index=False)
    .agg(
        items_sold=("order_item_id", "count"),
        sales=("price", "sum")
    )
)

category_sales_total = category_sales["sales"].sum()

print("\n" + "=" * 75)
print("6. CATEGORY SALES RECONCILIATION")
print("=" * 75)

print(
    f"\nRaw sales:       {raw_sales:,.2f}"
)

print(
    f"Category sales:  {category_sales_total:,.2f}"
)

print(
    f"Difference:      {raw_sales - category_sales_total:,.2f}"
)


# ============================================================
# 7. CHECK DUPLICATION AFTER PRODUCT JOIN
# ============================================================

print("\n" + "=" * 75)
print("7. DUPLICATION CHECK")
print("=" * 75)

raw_item_rows = len(order_items)

joined_item_rows = len(items_with_product)

print(
    f"\nRaw item rows:    {raw_item_rows:,}"
)

print(
    f"After product join:{joined_item_rows:,}"
)

print(
    f"Difference:       "
    f"{joined_item_rows - raw_item_rows:,}"
)


# ============================================================
# 8. CHECK DUPLICATION AFTER TRANSLATION JOIN
# ============================================================

translated_item_rows = len(items_with_category)

print(
    f"\nAfter translation join: "
    f"{translated_item_rows:,}"
)

print(
    f"Difference from raw: "
    f"{translated_item_rows - raw_item_rows:,}"
)


# ============================================================
# 9. FIND DUPLICATE PRODUCT IDS
# ============================================================

print("\n" + "=" * 75)
print("9. PRODUCT ID DUPLICATION")
print("=" * 75)

duplicate_product_ids = (
    products["product_id"]
    .duplicated(keep=False)
)

print(
    f"\nDuplicated product IDs: "
    f"{products.loc[duplicate_product_ids, 'product_id'].nunique():,}"
)

print(
    f"Rows involved: "
    f"{duplicate_product_ids.sum():,}"
)


# ============================================================
# 10. FIND DUPLICATE TRANSLATION KEYS
# ============================================================

duplicate_translation_keys = (
    translation["product_category_name"]
    .duplicated(keep=False)
)

print(
    f"\nDuplicated translation keys: "
    f"{translation.loc[
        duplicate_translation_keys,
        'product_category_name'
    ].nunique():,}"
)

print(
    f"Rows involved: "
    f"{duplicate_translation_keys.sum():,}"
)


# ============================================================
# 11. PRODUCT CATEGORY SALES DETAIL
# ============================================================

print("\n" + "=" * 75)
print("11. CATEGORY DETAIL")
print("=" * 75)

category_sales = category_sales.sort_values(
    "sales",
    ascending=False
)

print(
    category_sales.head(15).to_string(index=False)
)


# ============================================================
# 12. FINAL DIAGNOSTIC SUMMARY
# ============================================================

print("\n" + "=" * 75)
print("DIAGNOSTIC SUMMARY")
print("=" * 75)

print(
    f"""
Raw sales:
    {raw_sales:,.2f}

Sales after category assignment:
    {category_sales_total:,.2f}

Sales difference:
    {raw_sales - category_sales_total:,.2f}

Unmatched product rows:
    {missing_product.sum():,}

Sales from unmatched products:
    {missing_product_sales:,.2f}

Missing category rows:
    {missing_category.sum():,}

Sales from missing categories:
    {missing_category_sales:,.2f}

Missing translation rows:
    {missing_translation.sum():,}

Sales from untranslated categories:
    {missing_translation_sales:,.2f}

Missing final category rows:
    {missing_final_category.sum():,}

Sales without final category:
    {missing_final_sales:,.2f}

Product join row difference:
    {joined_item_rows - raw_item_rows:,}

Translation join row difference:
    {translated_item_rows - raw_item_rows:,}
"""
)

print("=" * 75)
print("DIAGNOSTIC COMPLETE")
print("=" * 75)