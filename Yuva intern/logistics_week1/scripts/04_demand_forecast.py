"""Fit a small lag-feature regression and compare it with a naive baseline."""

import csv
import json
import math
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from chart_utils import line_chart


ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "data" / "orders_clean.csv"
OUTPUT_DIR = ROOT / "outputs"


def solve(matrix, vector):
    """Solve a small square system with Gaussian elimination and pivoting."""
    augmented = [row[:] + [target] for row, target in zip(matrix, vector)]
    size = len(vector)
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("Regression feature matrix is singular.")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(augmented[row], augmented[column])
            ]
    return [augmented[row][-1] for row in range(size)]


def wape(actual, predicted):
    denominator = sum(abs(value) for value in actual)
    return sum(abs(a - p) for a, p in zip(actual, predicted)) / denominator if denominator else 0.0


def main():
    with INPUT_FILE.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    weekly = Counter()
    for row in rows:
        order_date = date.fromisoformat(row["order_date"])
        monday = order_date - timedelta(days=order_date.weekday())
        weekly[monday] += float(row["quantity"])

    first = min(weekly)
    last = max(weekly)
    timeline = []
    current = first
    while current <= last:
        timeline.append((current, weekly[current]))
        current += timedelta(days=7)

    samples = []
    for index in range(4, len(timeline)):
        past = [timeline[position][1] for position in range(index - 4, index)]
        samples.append(
            (
                [1.0, past[-1], past[-2], sum(past) / len(past)],
                timeline[index][1],
                timeline[index][0],
                past[-1],
            )
        )
    split = int(len(samples) * 0.8)
    if split < 2 or len(samples) - split < 1:
        raise ValueError("Not enough weekly history for a time-based train/test split.")
    training, testing = samples[:split], samples[split:]

    feature_count = len(training[0][0])
    matrix = [[0.0] * feature_count for _ in range(feature_count)]
    vector = [0.0] * feature_count
    for features, target, _, _ in training:
        for row_index in range(feature_count):
            vector[row_index] += features[row_index] * target
            for column in range(feature_count):
                matrix[row_index][column] += features[row_index] * features[column]
    for index in range(1, feature_count):
        matrix[index][index] += 1e-8
    coefficients = solve(matrix, vector)
    predicted = [
        max(0.0, sum(weight * value for weight, value in zip(coefficients, features)))
        for features, _, _, _ in testing
    ]
    actual = [sample[1] for sample in testing]
    naive = [sample[3] for sample in testing]
    model_wape = wape(actual, predicted)
    naive_wape = wape(actual, naive)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = {
        "frequency": "weekly",
        "method": "ordinary least squares with lag_1, lag_2, rolling_mean_4",
        "train_periods": len(training),
        "test_periods": len(testing),
        "regression_wape": model_wape,
        "naive_last_week_wape": naive_wape,
        "lower_wape_is_better": True,
    }
    (OUTPUT_DIR / "forecast_metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    with (OUTPUT_DIR / "forecast_test_predictions.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["week", "actual", "regression", "naive"])
        writer.writerows(
            (sample[2].isoformat(), sample[1], prediction, sample[3])
            for sample, prediction in zip(testing, predicted)
        )
    labels = [sample[2].strftime("%m-%d") for sample in testing]
    line_chart(
        OUTPUT_DIR / "weekly_demand_forecast.png",
        "Weekly demand forecast",
        {"Actual": actual, "Regression": predicted, "Naive": naive},
        labels,
    )
    print(f"Time split: {len(training)} training weeks, {len(testing)} test weeks")
    print(f"Regression WAPE: {model_wape:.1%}")
    print(f"Naive last-week WAPE: {naive_wape:.1%}")
    print(f"Saved forecast results and chart in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
