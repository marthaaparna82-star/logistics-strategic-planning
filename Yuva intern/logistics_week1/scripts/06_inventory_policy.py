"""Calculate indicative safety stock, reorder point, and EOQ per product."""

import csv
import math
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "data" / "orders_clean.csv"
OUTPUT_FILE = ROOT / "outputs" / "inventory_policy.csv"
SERVICE_Z = 1.645
LEAD_TIME_DAYS = 7
ORDERING_COST = 50.0
ANNUAL_HOLDING_RATE = 0.25


def main():
    with INPUT_FILE.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    first_day = min(date.fromisoformat(row["order_date"]) for row in rows)
    last_day = max(date.fromisoformat(row["order_date"]) for row in rows)
    day_count = (last_day - first_day).days + 1
    demand = defaultdict(lambda: [0.0] * day_count)
    cost_sum = defaultdict(float)
    cost_count = defaultdict(int)
    for row in rows:
        product = row["product_id"]
        index = (date.fromisoformat(row["order_date"]) - first_day).days
        demand[product][index] += float(row["quantity"])
        cost_sum[product] += float(row["unit_cost"])
        cost_count[product] += 1

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "product_id", "average_daily_demand", "daily_demand_std",
        "assumed_lead_time_days", "safety_stock_units", "reorder_point_units",
        "annual_demand_estimate", "eoq_units",
    ]
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for product, daily_demand in sorted(demand.items()):
            mean_daily = sum(daily_demand) / len(daily_demand)
            variance = sum((value - mean_daily) ** 2 for value in daily_demand) / max(1, len(daily_demand) - 1)
            std_daily = math.sqrt(variance)
            safety_stock = SERVICE_Z * std_daily * math.sqrt(LEAD_TIME_DAYS)
            reorder_point = mean_daily * LEAD_TIME_DAYS + safety_stock
            annual_demand = mean_daily * 365
            average_unit_cost = cost_sum[product] / cost_count[product]
            holding_cost = average_unit_cost * ANNUAL_HOLDING_RATE
            eoq = math.sqrt(2 * annual_demand * ORDERING_COST / holding_cost) if holding_cost else 0.0
            writer.writerow(
                {
                    "product_id": product,
                    "average_daily_demand": round(mean_daily, 3),
                    "daily_demand_std": round(std_daily, 3),
                    "assumed_lead_time_days": LEAD_TIME_DAYS,
                    "safety_stock_units": round(safety_stock, 3),
                    "reorder_point_units": round(reorder_point, 3),
                    "annual_demand_estimate": round(annual_demand, 2),
                    "eoq_units": round(eoq, 3),
                }
            )
    print(f"Inventory policies calculated for {len(demand)} products.")
    print(f"Assumptions: z={SERVICE_Z}, lead time={LEAD_TIME_DAYS} days, order cost={ORDERING_COST}.")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
