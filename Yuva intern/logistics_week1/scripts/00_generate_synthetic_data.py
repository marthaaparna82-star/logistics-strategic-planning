"""Generate reproducible, fictional FreshKart order-line data using only Python's standard library."""

import csv
import random
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = ROOT / "data" / "orders_synthetic.csv"


def weighted_choice(rng, values, weights):
    return rng.choices(values, weights=weights, k=1)[0]


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    products = [f"SKU-{number:03d}" for number in range(1, 31)]
    weights = [2.5 - 2.0 * index / (len(products) - 1) for index in range(len(products))]
    prices = {product: rng.randint(8, 80) for product in products}
    regions = ["North", "South", "East", "West"]
    modes = ["Standard", "Express", "Economy"]
    mode_days = {"Standard": 3, "Express": 2, "Economy": 5}
    region_cost = {"North": 2.0, "South": 3.0, "East": 2.5, "West": 3.5}
    columns = [
        "order_id", "product_id", "order_date", "promised_date", "delivery_date",
        "region", "shipping_mode", "quantity", "fulfilled_quantity", "unit_price",
        "unit_cost", "delivery_cost", "warehouse", "hub", "van_id",
    ]

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        for index in range(2400):
            product = weighted_choice(rng, products, weights)
            region = weighted_choice(rng, regions, [29, 25, 24, 22])
            mode = weighted_choice(rng, modes, [60, 25, 15])
            quantity = rng.randint(1, 5)
            fill_probability = 0.84 if product in products[:6] else 0.96
            fulfilled = sum(rng.random() < fill_probability for _ in range(quantity))
            order_date = date(2025, 1, 1) + timedelta(days=rng.randrange(365))
            promised = order_date + timedelta(days=mode_days[mode])
            delay = weighted_choice(rng, [-1, 0, 0, 1, 2, 4, 6], [8, 18, 18, 22, 18, 10, 6])
            delay += 1 if region in ("South", "West") else 0
            delivered = order_date + timedelta(days=max(1, mode_days[mode] + delay))
            mode_multiplier = {"Standard": 1.0, "Express": 1.45, "Economy": 0.78}[mode]
            cost = round((7.0 + region_cost[region]) * mode_multiplier, 2)
            price = prices[product]
            writer.writerow(
                {
                    "order_id": f"FK-{index + 1:05d}",
                    "product_id": product,
                    "order_date": order_date.isoformat(),
                    "promised_date": promised.isoformat(),
                    "delivery_date": delivered.isoformat(),
                    "region": region,
                    "shipping_mode": mode,
                    "quantity": quantity,
                    "fulfilled_quantity": fulfilled,
                    "unit_price": price,
                    "unit_cost": round(price * 0.60, 2),
                    "delivery_cost": cost,
                    "warehouse": "Central Warehouse",
                    "hub": f"{region} Hub",
                    "van_id": f"VAN-{(index % 40) + 1:02d}",
                }
            )
    print(f"Generated 2,400 synthetic order lines: {OUTPUT_FILE}")
    print("Data is fictional and is not a public retailer dataset.")


if __name__ == "__main__":
    main()
