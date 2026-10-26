"""Run product ABC/XYZ segmentation and silhouette-selected K-Means."""

import csv
import json
import math
import random
from collections import defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "data" / "orders_clean.csv"
OUTPUT_DIR = ROOT / "outputs"


def distance(left, right):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def kmeans(points, clusters, seed):
    rng = random.Random(seed + clusters)
    centers = [list(point) for point in rng.sample(points, clusters)]
    labels = [0] * len(points)
    for _ in range(100):
        new_labels = [min(range(clusters), key=lambda index: distance(point, centers[index])) for point in points]
        new_centers = []
        for cluster in range(clusters):
            members = [point for point, label in zip(points, new_labels) if label == cluster]
            if not members:
                new_centers.append(centers[cluster])
            else:
                new_centers.append(
                    [sum(point[column] for point in members) / len(members) for column in range(len(points[0]))]
                )
        if new_labels == labels and new_centers == centers:
            break
        labels, centers = new_labels, new_centers
    return labels


def silhouette(points, labels):
    groups = defaultdict(list)
    for index, label in enumerate(labels):
        groups[label].append(index)
    scores = []
    for index, point in enumerate(points):
        own = groups[labels[index]]
        if len(own) < 2:
            scores.append(0.0)
            continue
        within = sum(distance(point, points[other]) for other in own if other != index) / (len(own) - 1)
        other_averages = [
            sum(distance(point, points[other]) for other in members) / len(members)
            for label, members in groups.items()
            if label != labels[index]
        ]
        outside = min(other_averages)
        scores.append((outside - within) / max(within, outside) if max(within, outside) else 0.0)
    return sum(scores) / len(scores) if scores else 0.0


def main():
    with INPUT_FILE.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    product_sales = defaultdict(float)
    product_cost = defaultdict(float)
    product_cost_count = defaultdict(int)
    monthly = defaultdict(lambda: defaultdict(float))
    for row in rows:
        product = row["product_id"]
        month = date.fromisoformat(row["order_date"]).strftime("%Y-%m")
        quantity = float(row["quantity"])
        product_sales[product] += quantity * float(row["unit_price"])
        product_cost[product] += float(row["unit_cost"])
        product_cost_count[product] += 1
        monthly[product][month] += quantity

    products = sorted(monthly)
    months = sorted({month for values in monthly.values() for month in values})
    sales_rank = sorted(products, key=lambda product: product_sales[product], reverse=True)
    cumulative = 0.0
    abc = {}
    total_sales = sum(product_sales.values())
    for product in sales_rank:
        cumulative += product_sales[product]
        share = cumulative / total_sales if total_sales else 1.0
        abc[product] = "A" if share <= 0.80 else "B" if share <= 0.95 else "C"

    raw_features = {}
    xyz = {}
    for product in products:
        demands = [monthly[product].get(month, 0.0) for month in months]
        average = sum(demands) / len(demands)
        variance = sum((value - average) ** 2 for value in demands) / len(demands)
        cv = math.sqrt(variance) / average if average else 0.0
        xyz[product] = "X" if cv <= 0.50 else "Y" if cv <= 1.00 else "Z"
        raw_features[product] = [math.log(sum(demands) + 1), average, cv]

    columns = list(zip(*(raw_features[product] for product in products)))
    means = [sum(values) / len(values) for values in columns]
    standard_deviations = [
        math.sqrt(sum((value - means[index]) ** 2 for value in columns[index]) / len(products)) or 1.0
        for index in range(len(means))
    ]
    points = [
        [(value - means[column]) / standard_deviations[column] for column, value in enumerate(raw_features[product])]
        for product in products
    ]
    if len(products) < 3:
        raise ValueError("At least three products are needed for silhouette-selected K-Means.")

    scores = []
    best = None
    for clusters in range(2, min(7, len(products))):
        labels = kmeans(points, clusters, 42)
        if len(set(labels)) < 2 or len(set(labels)) >= len(products):
            continue
        score = silhouette(points, labels)
        scores.append((clusters, score, labels))
        if best is None or score > best[1]:
            best = (clusters, score, labels)
    if best is None:
        raise ValueError("Could not find a valid K-Means clustering.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUTPUT_DIR / "product_segmentation.csv").open("w", newline="", encoding="utf-8") as file:
        fields = ["product_id", "sales_value", "abc_class", "xyz_class", "abc_xyz", "average_monthly_demand", "demand_cv", "kmeans_cluster"]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for product, label in zip(products, best[2]):
            writer.writerow(
                {
                    "product_id": product,
                    "sales_value": round(product_sales[product], 2),
                    "abc_class": abc[product],
                    "xyz_class": xyz[product],
                    "abc_xyz": abc[product] + xyz[product],
                    "average_monthly_demand": round(raw_features[product][1], 3),
                    "demand_cv": round(raw_features[product][2], 3),
                    "kmeans_cluster": label,
                }
            )
    with (OUTPUT_DIR / "kmeans_silhouette_scores.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["k", "silhouette_score"])
        writer.writerows((clusters, score) for clusters, score, _ in scores)
    (OUTPUT_DIR / "product_segmentation_metrics.json").write_text(
        json.dumps({"selected_k": best[0], "silhouette_score": best[1]}, indent=2),
        encoding="utf-8",
    )
    print(f"Products segmented: {len(products)}")
    print(f"Selected K-Means k: {best[0]} (silhouette {best[1]:.3f})")
    print(f"Assignments: {OUTPUT_DIR / 'product_segmentation.csv'}")


if __name__ == "__main__":
    main()
