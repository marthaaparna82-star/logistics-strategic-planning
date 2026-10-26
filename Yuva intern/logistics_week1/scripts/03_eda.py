"""Create five exploratory PNG charts with standard-library drawing helpers."""

import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from chart_utils import bar_chart, line_chart


ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "data" / "orders_clean.csv"
OUTPUT_DIR = ROOT / "outputs"


def main():
    with INPUT_FILE.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    late_region = Counter()
    late_mode = Counter()
    on_time_region = Counter()
    delivered_region = Counter()
    monthly = Counter()
    product_sales = Counter()

    for row in rows:
        order_date = date.fromisoformat(row["order_date"])
        monthly[order_date.strftime("%Y-%m")] += float(row["quantity"])
        product_sales[row["product_id"]] += float(row["quantity"]) * float(row["unit_price"])
        if not row["delivery_date"]:
            continue
        late = date.fromisoformat(row["delivery_date"]) > date.fromisoformat(row["promised_date"])
        late_region[row["region"]] += int(late)
        late_mode[row["shipping_mode"]] += int(late)
        delivered_region[row["region"]] += 1
        on_time_region[row["region"]] += int(not late)

    regions = sorted(delivered_region)
    modes = sorted({row["shipping_mode"] for row in rows})
    bar_chart(
        OUTPUT_DIR / "late_orders_by_region.png",
        "Late orders by region",
        regions,
        [late_region[name] for name in regions],
    )
    bar_chart(
        OUTPUT_DIR / "late_orders_by_shipping_mode.png",
        "Late orders by shipping mode",
        modes,
        [late_mode[name] for name in modes],
        [(217, 119, 6), (37, 99, 235), (5, 150, 105)],
    )
    month_labels = sorted(monthly)
    line_chart(
        OUTPUT_DIR / "monthly_demand_trend.png",
        "Monthly demand trend",
        {"Demand": [monthly[month] for month in month_labels]},
        month_labels,
    )
    top_products = sorted(product_sales, key=product_sales.get, reverse=True)[:10]
    bar_chart(
        OUTPUT_DIR / "top_products_by_sales.png",
        "Top products by sales value",
        top_products,
        [product_sales[product] for product in top_products],
    )
    bar_chart(
        OUTPUT_DIR / "on_time_share_by_region.png",
        "On-time deliveries by region",
        regions,
        [100 * on_time_region[name] / delivered_region[name] for name in regions],
    )
    print("Saved five charts in outputs/.")


if __name__ == "__main__":
    main()
