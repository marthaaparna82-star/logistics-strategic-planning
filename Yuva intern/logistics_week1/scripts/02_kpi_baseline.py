"""Calculate baseline logistics KPIs using the cleaned synthetic order lines."""

import csv
import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "data" / "orders_clean.csv"
OUTPUT_FILE = ROOT / "outputs" / "baseline_kpis.json"


def main():
    with INPUT_FILE.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    delivered = [row for row in rows if row["delivery_date"]]
    on_time_in_full = 0
    lead_days = []
    for row in delivered:
        delivered_date = date.fromisoformat(row["delivery_date"])
        order_date = date.fromisoformat(row["order_date"])
        promised_date = date.fromisoformat(row["promised_date"])
        lead_days.append((delivered_date - order_date).days)
        if delivered_date <= promised_date and float(row["fulfilled_quantity"]) >= float(row["quantity"]):
            on_time_in_full += 1

    requested = sum(float(row["quantity"]) for row in rows)
    fulfilled = sum(float(row["fulfilled_quantity"]) for row in rows)
    cost = sum(float(row["delivery_cost"]) for row in delivered)
    unique_deliveries = len({row["order_id"] for row in delivered})
    results = {
        "data_type": "synthetic",
        "order_lines": len(rows),
        "delivered_order_lines": len(delivered),
        "otif_rate": on_time_in_full / len(delivered) if delivered else 0.0,
        "average_delivery_lead_time_days": sum(lead_days) / len(lead_days) if lead_days else 0.0,
        "fill_rate": fulfilled / requested if requested else 0.0,
        "cost_per_delivery": cost / unique_deliveries if unique_deliveries else 0.0,
        "cost_currency": "synthetic cost units; not a real currency",
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("Baseline KPIs (synthetic data)")
    print(f"On-Time In-Full rate: {results['otif_rate']:.1%}")
    print(f"Average delivery lead time: {results['average_delivery_lead_time_days']:.2f} days")
    print(f"Fill rate: {results['fill_rate']:.1%}")
    print(f"Cost per delivery proxy: {results['cost_per_delivery']:.2f} synthetic cost units")
    print(f"Saved KPI results: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
