# FreshKart Logistics Week 1

This project demonstrates strategic planning and logistics data exploration for a fictional online retailer with one warehouse, three regional hubs, and 40 vans.

## Data notice

The Kaggle Olist download endpoint was attempted but returned HTTP 404 without credentials. Therefore, the project uses a **reproducible synthetic dataset**. Its KPIs, charts, cost units, and route coordinates are illustrative—not FreshKart operational facts.

The selected Python 3.14 runtime could not load NumPy because Windows Application Control blocked its compiled extension. No alternate runtime was installed. With the user's approval, the scripts use the Python standard library so the whole workflow can run without external packages. Consequently, demand regression, K-Means, chart rendering, and the `.docx` package use simple local implementations. The route script uses a capacity-feasible nearest-stop heuristic, not Google OR-Tools. See the report for these limits.

## Setup and run

No package installation is required. Run the scripts in order:

```powershell
python scripts\00_generate_synthetic_data.py
python scripts\01_clean_data.py
python scripts\02_kpi_baseline.py
python scripts\03_eda.py
python scripts\04_demand_forecast.py
python scripts\05_clustering.py
python scripts\06_inventory_policy.py
python scripts\07_route_optimization.py
python scripts\08_build_report.py
```

If `python` is not on PATH, replace `python` with the full path to your approved Python executable. Scripts locate the project folder relative to their own file location.

## Key outputs

- `data\orders_synthetic.csv` and `data\orders_clean.csv`
- `outputs\baseline_kpis.json`, charts, forecast metrics, product segments, inventory policies, and sample route plan
- `report\FreshKart_Strategic_Planning_Report.docx`
