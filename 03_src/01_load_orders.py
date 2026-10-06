from pathlib import Path
import pandas as pd

project_root = Path(__file__).resolve().parent.parent
raw_folder = project_root / "01_data" / "raw"

orders = pd.read_csv(raw_folder / "olist_orders_dataset.csv")
customers = pd.read_csv(raw_folder / "olist_customers_dataset.csv")
order_items = pd.read_csv(raw_folder / "olist_order_items_dataset.csv")
payments = pd.read_csv(raw_folder / "olist_order_payments_dataset.csv")
reviews = pd.read_csv(raw_folder / "olist_order_reviews_dataset.csv")
products = pd.read_csv(raw_folder / "olist_products_dataset.csv")
sellers = pd.read_csv(raw_folder / "olist_sellers_dataset.csv")

print("=" * 70)
print("OLIST RELATIONSHIP INTEGRITY CHECK")
print("=" * 70)

checks = [
    ("order_items → orders", order_items["order_id"], orders["order_id"]),
    ("orders → customers", orders["customer_id"], customers["customer_id"]),
    ("order_items → products", order_items["product_id"], products["product_id"]),
    ("order_items → sellers", order_items["seller_id"], sellers["seller_id"]),
    ("payments → orders", payments["order_id"], orders["order_id"]),
    ("reviews → orders", reviews["order_id"], orders["order_id"]),
]

for name, child, parent in checks:
    unmatched = (~child.isin(parent)).sum()

    print(f"\n{name}")
    print(f"Unmatched records: {unmatched:,}")

print("\n" + "=" * 70)
print("CHECK COMPLETE")
print("=" * 70)