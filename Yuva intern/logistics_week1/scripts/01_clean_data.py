"""Clean order rows, normalize values, and check delivery-date validity."""

import csv
from datetime import date
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "data" / "orders_synthetic.csv"
OUTPUT_FILE = ROOT / "data" / "orders_clean.csv"
DATE_COLUMNS = ("order_date", "promised_date", "delivery_date")
NUMERIC_COLUMNS = ("quantity", "fulfilled_quantity", "unit_price", "unit_cost", "delivery_cost")
TEXT_COLUMNS = ("region", "shipping_mode", "product_id", "warehouse", "hub", "van_id")


def main():
    with INPUT_FILE.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    original_count = len(rows)
    seen = set()
    unique = []
    duplicates = 0
    for row in rows:
        if row["order_id"] in seen:
            duplicates += 1
            continue
        seen.add(row["order_id"])
        unique.append(row)

    numeric_medians = {}
    for column in NUMERIC_COLUMNS:
        valid_values = []
        for row in unique:
            try:
                if row[column]:
                    valid_values.append(float(row[column]))
            except ValueError:
                pass
        numeric_medians[column] = median(valid_values) if valid_values else 0.0

    cleaned = []
    missing_dates = 0
    invalid_delivery_dates = 0
    imputed_numeric_values = 0
    for row in unique:
        try:
            order_date = date.fromisoformat(row["order_date"])
            promised_date = date.fromisoformat(row["promised_date"])
        except (ValueError, TypeError):
            missing_dates += 1
            continue
        row["order_date"] = order_date.isoformat()
        row["promised_date"] = promised_date.isoformat()
        if row["delivery_date"]:
            try:
                delivered = date.fromisoformat(row["delivery_date"])
                if delivered < order_date:
                    row["delivery_date"] = ""
                    invalid_delivery_dates += 1
            except ValueError:
                row["delivery_date"] = ""

        for column in NUMERIC_COLUMNS:
            imputed = not row[column]
            try:
                value = float(row[column]) if row[column] else numeric_medians[column]
            except ValueError:
                value = numeric_medians[column]
                imputed = True
            if imputed:
                imputed_numeric_values += 1
            row[column] = str(value)
        row["fulfilled_quantity"] = str(
            min(float(row["quantity"]), max(0.0, float(row["fulfilled_quantity"])))
        )
        for column in TEXT_COLUMNS:
            row[column] = row[column] or "Unknown"
        cleaned.append(row)

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=cleaned[0].keys())
        writer.writeheader()
        writer.writerows(cleaned)
    print(f"Rows read: {original_count:,}")
    print(f"Duplicate order IDs removed: {duplicates:,}")
    print(f"Rows missing or invalid required dates removed: {missing_dates:,}")
    print(f"Delivery dates before order date set to missing: {invalid_delivery_dates:,}")
    print(f"Missing or invalid numeric values imputed: {imputed_numeric_values:,}")
    print(f"Clean rows saved: {len(cleaned):,} -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
