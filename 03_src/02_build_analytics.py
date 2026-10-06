import pandas as pd
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
raw_folder = project_root / "01_data" / "raw"

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

data = {}

for name, filename in files.items():

    print("\n" + "=" * 70)
    print(f"{name.upper()}")
    print("=" * 70)

    df = pd.read_csv(raw_folder / filename)
    data[name] = df

    print("\nSHAPE")
    print(df.shape)

    print("\nCOLUMNS")
    print(df.columns)

    print("\nDATA TYPES")
    print(df.dtypes)

    print("\nMISSING VALUES")
    print(df.isnull().sum())

    print("\nDUPLICATE ROWS")
    print(df.duplicated().sum())