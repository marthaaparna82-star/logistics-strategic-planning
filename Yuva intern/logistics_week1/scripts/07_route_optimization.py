"""Demonstrate capacity-aware routing with a deterministic nearest-stop heuristic."""

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = ROOT / "outputs" / "sample_route_plan.json"


def distance(first, second):
    return math.hypot(first[0] - second[0], first[1] - second[1])


def main():
    # Sample coordinates and demands are illustrative rather than observed data.
    coordinates = [
        (0, 0), (2, 3), (5, 4), (1, 7), (6, 8),
        (8, 2), (3, 9), (9, 6), (7, 10),
    ]
    demands = [0, 3, 4, 5, 2, 3, 4, 2, 3]
    capacities = [15, 15]
    unassigned = set(range(1, len(coordinates)))
    routes = []
    total_distance = 0.0
    for vehicle, capacity in enumerate(capacities, start=1):
        route = [0]
        load = 0
        current = 0
        while True:
            feasible = [node for node in unassigned if load + demands[node] <= capacity]
            if not feasible:
                break
            next_stop = min(feasible, key=lambda node: distance(coordinates[current], coordinates[node]))
            total_distance += distance(coordinates[current], coordinates[next_stop])
            route.append(next_stop)
            load += demands[next_stop]
            current = next_stop
            unassigned.remove(next_stop)
        total_distance += distance(coordinates[current], coordinates[0])
        route.append(0)
        routes.append({"vehicle": vehicle, "stops": route, "load": load})
    if unassigned:
        raise ValueError(f"Sample vehicle capacity cannot serve stops: {sorted(unassigned)}")

    result = {
        "data_type": "illustrative sample coordinates and demands",
        "solver": "nearest-stop capacity-feasible heuristic; OR-Tools unavailable in this runtime",
        "total_distance_units": round(total_distance * 1000),
        "routes": routes,
        "vehicle_capacities": capacities,
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Total heuristic route distance: {total_distance:.2f} coordinate units")
    for route in routes:
        print(f"Vehicle {route['vehicle']}: stops {route['stops']}, load {route['load']}/{capacities[route['vehicle'] - 1]}")
    print("Note: a capacity-aware heuristic is used; this is not an OR-Tools solution.")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
