"""Create a small synthetic logistics dataset and run a reproducible cleaning workflow.

The Kaggle download was unavailable and this Python environment cannot import
pandas, NumPy, scikit-learn, or python-docx. This script therefore uses only
the Python standard library and labels all generated data as synthetic.
"""

import csv
import json
import math
import random
import re
import statistics
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
REPORT_DIR = ROOT / "report"
RAW_FILE = DATA_DIR / "synthetic_orders_raw.csv"
CLEAN_FILE = OUTPUT_DIR / "orders_preprocessed.csv"
TRAIN_FILE = OUTPUT_DIR / "orders_train_scaled.csv"
TEST_FILE = OUTPUT_DIR / "orders_test_scaled.csv"
SUMMARY_FILE = OUTPUT_DIR / "cleaning_summary.json"
REPORT_FILE = REPORT_DIR / "Week_2_Data_Cleaning_Report.docx"

NUMERIC_COLUMNS = ("sales", "order_quantity", "shipping_cost", "profit")
DATE_COLUMNS = ("order_date", "shipping_date")
TEXT_COLUMNS = ("customer_segment", "region")
RAW_HEADERS = (
    "Order ID",
    "Order Date",
    "Shipping Date",
    "Sales",
    "Order Quantity",
    "Shipping Cost",
    "Profit",
    "Customer Segment",
    "Region",
    "Empty Column",
)


def explain(message):
    """Print why a step matters before carrying it out."""
    print(f"\n{message}")


def normalize_name(name):
    """Convert a heading to lowercase snake_case."""
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def create_synthetic_dataset():
    """Write deterministic fictional order rows with common data-quality problems."""
    rng = random.Random(2026)
    rows = []
    start = date(2025, 1, 1)

    for index in range(500):
        order_date = start + timedelta(days=rng.randrange(365))
        shipping_date = order_date + timedelta(days=rng.randint(1, 8))
        sales = round(rng.lognormvariate(4.1, 0.65), 2)
        if index in (201, 350):
            sales = 5000.0 + index

        row = {
            "Order ID": f"ORD-{index + 1:05d}",
            "Order Date": order_date.isoformat(),
            "Shipping Date": shipping_date.isoformat(),
            "Sales": sales,
            "Order Quantity": rng.randint(1, 12),
            "Shipping Cost": round(rng.uniform(4.0, 120.0), 2),
            "Profit": round(rng.uniform(1.0, 250.0), 2),
            "Customer Segment": rng.choice(
                ("Consumer", "Corporate", "Home Office")
            ),
            "Region": rng.choice(("North", "South", "East", "West")),
            "Empty Column": None,
        }
        rows.append(row)

    # Add missing, invalid, and negative values so the cleaning steps are visible.
    for index in range(13, 300, 29):
        rows[index]["Sales"] = None
    for index in range(16, 240, 37):
        rows[index]["Order Quantity"] = None
    for index in range(21, 260, 41):
        rows[index]["Shipping Cost"] = None
    for index in range(24, 280, 43):
        rows[index]["Profit"] = None
    for index in (31, 121, 211):
        rows[index]["Customer Segment"] = None
    for index in (33, 133, 233):
        rows[index]["Region"] = None

    for index in (8, 28, 48, 68, 88):
        row_date = date.fromisoformat(rows[index]["Order Date"])
        rows[index]["Shipping Date"] = (row_date - timedelta(days=1)).isoformat()
    for index, column, value in (
        (18, "Sales", -10.0),
        (38, "Order Quantity", -2),
        (58, "Shipping Cost", -3.0),
        (78, "Profit", -12.0),
    ):
        rows[index][column] = value
    rows[118]["Order Date"] = "not-a-date"
    rows[138]["Shipping Date"] = None

    # Exact duplicate records let the duplicate-removal step be measured.
    rows.extend(dict(rows[index]) for index in range(1, 11))

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with RAW_FILE.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=RAW_HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def read_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader)


def missing_count(rows, columns=None):
    if not rows:
        return 0
    columns = columns or tuple(rows[0])
    return sum(
        value is None or str(value).strip() == ""
        for row in rows
        for value in (row.get(column) for column in columns)
    )


def duplicate_count(rows, columns=None):
    if not rows:
        return 0
    columns = columns or tuple(rows[0])
    seen = set()
    duplicates = 0
    for row in rows:
        signature = tuple(row.get(column) or "" for column in columns)
        if signature in seen:
            duplicates += 1
        else:
            seen.add(signature)
    return duplicates


def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        raise ValueError("Percentiles need at least one value.")
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def write_csv(path, rows, columns):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def paragraph(text, style=None, code=False):
    style_xml = f'<w:pStyle w:val="{style}"/>' if style else ""
    font_xml = (
        "<w:rPr><w:rFonts w:ascii=\"Consolas\" w:hAnsi=\"Consolas\"/>"
        "<w:sz w:val=\"18\"/></w:rPr>"
        if code
        else ""
    )
    safe_text = escape(str(text))
    return (
        f"<w:p><w:pPr>{style_xml}</w:pPr>"
        f"<w:r>{font_xml}<w:t xml:space=\"preserve\">{safe_text}</w:t></w:r></w:p>"
    )


def table(rows):
    borders = (
        "<w:tblBorders>"
        "<w:top w:val=\"single\" w:sz=\"4\" w:color=\"808080\"/>"
        "<w:left w:val=\"single\" w:sz=\"4\" w:color=\"808080\"/>"
        "<w:bottom w:val=\"single\" w:sz=\"4\" w:color=\"808080\"/>"
        "<w:right w:val=\"single\" w:sz=\"4\" w:color=\"808080\"/>"
        "<w:insideH w:val=\"single\" w:sz=\"4\" w:color=\"B0B0B0\"/>"
        "<w:insideV w:val=\"single\" w:sz=\"4\" w:color=\"B0B0B0\"/>"
        "</w:tblBorders>"
    )
    result = [
        f"<w:tbl><w:tblPr><w:tblW w:w=\"0\" w:type=\"auto\"/>{borders}</w:tblPr>"
    ]
    for row_index, values in enumerate(rows):
        result.append("<w:tr>")
        for value in values:
            bold = "<w:rPr><w:b/></w:rPr>" if row_index == 0 else ""
            result.append(
                "<w:tc><w:tcPr><w:tcW w:w=\"2200\" w:type=\"dxa\"/></w:tcPr>"
                f"<w:p><w:r>{bold}<w:t xml:space=\"preserve\">{escape(str(value))}"
                "</w:t></w:r></w:p></w:tc>"
            )
        result.append("</w:tr>")
    result.append("</w:tbl>")
    return "".join(result)


def make_report(summary):
    """Write a minimal valid Word Open XML document using only the standard library."""
    before = summary["before"]
    after = summary["after"]
    content = [
        paragraph("Week 2: Data Cleaning and Preprocessing", "Title"),
        paragraph(
            "Dataset note: Kaggle's public DataCo download endpoint returned HTTP "
            "404 during this run. The file used here is a fictional, reproducible "
            "synthetic dataset created by this script. It is not the Kaggle dataset."
        ),
        paragraph(
            "Environment note: NumPy was blocked by Windows Application Control. "
            "Therefore pandas, scikit-learn's StandardScaler, and python-docx could "
            "not be used. The executed script uses Python's standard library for "
            "equivalent calculations; it does not claim to use those packages."
        ),
        paragraph("Step 1 — Look at the data", "Heading1"),
        paragraph(
            "Why: Checking the size, missing cells, duplicate rows, and column "
            "types shows where cleaning is needed before analysis."
        ),
        paragraph(
            "Code: rows = read_rows(RAW_FILE); print(len(rows), len(rows[0]))",
            code=True,
        ),
        paragraph(
            f"Result: {before['rows']} rows and {before['columns']} columns; "
            f"{before['missing_values']} missing cells and "
            f"{before['duplicate_rows']} duplicate rows. Raw CSV fields are read "
            "as text, so dates and numeric columns need conversion."
        ),
        paragraph("Step 2 — Clean names, dates, duplicates, and wrong rows", "Heading1"),
        paragraph(
            "Why: Consistent names and valid dates make filtering and grouping "
            "reliable. Duplicate records can inflate order counts. A shipment "
            "cannot happen before its order, and negative quantities/costs/sales "
            "are invalid in this exercise."
        ),
        paragraph(
            "Code: name = normalize_name(raw_name); "
            "ship_date = date.fromisoformat(row['shipping_date'])",
            code=True,
        ),
        paragraph(
            f"Result: removed {summary['removed_duplicates']} duplicate rows, "
            f"{summary['removed_invalid_dates']} rows with missing or invalid "
            f"dates, {summary['removed_bad_shipping_dates']} rows shipped before "
            f"the order, and {summary['removed_negative_rows']} rows with negative "
            "numeric values."
        ),
        paragraph("Step 3 — Handle missing values", "Heading1"),
        paragraph(
            "Why: Entirely empty fields add no information. Median filling keeps "
            "numeric records available without being pulled strongly by extremes. "
            "'Unknown' keeps rows with missing text instead of deleting them."
        ),
        paragraph(
            "Code: median_value = statistics.median(train_values); "
            "row[column] = 'Unknown'",
            code=True,
        ),
        paragraph(
            f"Result: dropped {summary['dropped_empty_columns']} empty column(s); "
            f"filled {summary['numeric_imputations']} numeric value(s) with "
            f"training medians and {summary['text_imputations']} text value(s) "
            "with 'Unknown'. The train/test split happens before these values "
            "are learned to prevent test-data leakage."
        ),
        paragraph("Step 4 — Find and cap outliers", "Heading1"),
        paragraph(
            "Why: IQR fences identify unusually low or high values. Capping "
            "extreme values reduces their influence while retaining the rows. "
            "The percentile limits are learned from the training data only."
        ),
        paragraph(
            "Code: low_fence = q1 - 1.5 * (q3 - q1); "
            "high_fence = q3 + 1.5 * (q3 - q1)",
            code=True,
        ),
        paragraph(
            f"Result: found {summary['iqr_outlier_values']} IQR outlier value(s) "
            f"and capped {summary['capped_values']} value(s) to training-set "
            "1st/99th percentile limits."
        ),
        paragraph("Step 5 — Scale numbers after the train/test split", "Heading1"),
        paragraph(
            "Why: Scaling numeric inputs helps many models compare features on "
            "similar ranges. Fitting the mean and standard deviation on training "
            "rows only avoids information leaking from the test set."
        ),
        paragraph(
            "Code: z = (value - train_mean) / train_population_std",
            code=True,
        ),
        paragraph(
            f"Result: {summary['train_rows']} training rows and "
            f"{summary['test_rows']} test rows. The script applies the same "
            "training means and population standard deviations to the test rows. "
            "This is the StandardScaler formula, implemented with the standard "
            "library because scikit-learn could not run here."
        ),
        paragraph("Step 6 — Before and after", "Heading1"),
        table(
            [
                ("Measure", "Before cleaning", "After preprocessing"),
                ("Rows", before["rows"], after["rows"]),
                ("Missing values", before["missing_values"], after["missing_values"]),
                ("Duplicate rows", before["duplicate_rows"], after["duplicate_rows"]),
            ]
        ),
        paragraph(
            "The after table describes the retained, imputed, and preprocessed "
            "records. The row count falls when duplicate or invalid records are "
            "removed; missing cells and exact duplicate rows are zero afterward."
        ),
        paragraph("Reflection", "Heading1"),
        paragraph(
            "Data quality matters in logistics because order dates, quantities, "
            "and shipping costs drive delivery-time, demand, and cost decisions. "
            "Bad records can make late-delivery rates or inventory plans look "
            "better or worse than reality. Cleaning improves trust, but the "
            "synthetic-data and environment limits mean these results should not "
            "be treated as evidence about a real company or the Kaggle dataset."
        ),
        paragraph(
            "Files: synthetic_orders_raw.csv contains the fictional source data; "
            "orders_preprocessed.csv and the train/test CSVs contain the "
            "preprocessed results."
        ),
    ]
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(content)
        + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="900" w:right="900" w:bottom="900" w:left="900" '
        'w:header="450" w:footer="450" w:gutter="0"/></w:sectPr>'
        "</w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(REPORT_FILE, "w", zipfile.ZIP_DEFLATED) as document:
        document.writestr("[Content_Types].xml", content_types)
        document.writestr("_rels/.rels", root_rels)
        document.writestr("word/document.xml", document_xml)


def main():
    """Run each stage, show measured results, and save a Word report."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    explain(
        "Step 1: I will inspect the file size, missing cells, duplicate rows, "
        "and raw column types so the cleaning work is based on observed problems."
    )
    create_synthetic_dataset()
    raw_rows = read_rows(RAW_FILE)
    raw_columns = tuple(raw_rows[0])
    before = {
        "rows": len(raw_rows),
        "columns": len(raw_columns),
        "missing_values": missing_count(raw_rows),
        "duplicate_rows": duplicate_count(raw_rows),
        "data_types": {column: "text (CSV input)" for column in raw_columns},
    }
    print(f"Data source: synthetic; Kaggle download returned HTTP 404.")
    print(
        f"Shape: {before['rows']} rows x {before['columns']} columns; "
        f"missing cells: {before['missing_values']}; "
        f"duplicate rows: {before['duplicate_rows']}"
    )
    print(f"Raw column types: {before['data_types']}")

    explain(
        "Step 2: I will normalize headings, parse dates, remove repeated rows, "
        "and reject invalid dates, early shipments, and rows with negative numbers."
    )
    normalized_rows = [
        {normalize_name(key): value for key, value in row.items()}
        for row in raw_rows
    ]
    normalized_columns = tuple(normalize_name(name) for name in raw_columns)
    unique_rows = []
    seen = set()
    removed_duplicates = 0
    for row in normalized_rows:
        signature = tuple(row.get(column) or "" for column in normalized_columns)
        if signature in seen:
            removed_duplicates += 1
            continue
        seen.add(signature)
        unique_rows.append(row)

    valid_dates = []
    removed_invalid_dates = 0
    removed_bad_shipping_dates = 0
    for row in unique_rows:
        try:
            order_date = datetime.strptime(row["order_date"], "%Y-%m-%d").date()
            shipping_date = datetime.strptime(
                row["shipping_date"], "%Y-%m-%d"
            ).date()
        except (TypeError, ValueError):
            removed_invalid_dates += 1
            continue
        if shipping_date < order_date:
            removed_bad_shipping_dates += 1
            continue
        row["order_date"] = order_date.isoformat()
        row["shipping_date"] = shipping_date.isoformat()
        for column in NUMERIC_COLUMNS:
            value = row[column]
            row[column] = None if value is None or value == "" else float(value)
        valid_dates.append(row)

    cleaned_rows = []
    removed_negative_rows = 0
    for row in valid_dates:
        if any(
            row[column] is not None and row[column] < 0
            for column in NUMERIC_COLUMNS
        ):
            removed_negative_rows += 1
            continue
        cleaned_rows.append(row)

    columns = list(normalized_columns)
    empty_columns = [
        column
        for column in columns
        if all(
            row.get(column) is None or str(row.get(column)).strip() == ""
            for row in cleaned_rows
        )
    ]
    for column in empty_columns:
        columns.remove(column)
        for row in cleaned_rows:
            row.pop(column, None)

    print(f"Duplicate rows removed: {removed_duplicates}")
    print(f"Rows with invalid/missing dates removed: {removed_invalid_dates}")
    print(f"Rows with shipping date before order date removed: {removed_bad_shipping_dates}")
    print(f"Rows with negative numeric values removed: {removed_negative_rows}")
    print(f"Entirely empty columns dropped: {empty_columns}")

    explain(
        "Step 3: I will split the valid rows before learning medians, fill numeric "
        "gaps from training medians, and replace missing text with 'Unknown'. "
        "This keeps test data out of fitted preprocessing values."
    )
    rng = random.Random(42)
    row_order = list(range(len(cleaned_rows)))
    rng.shuffle(row_order)
    test_count = max(1, int(len(row_order) * 0.2 + 0.5))
    test_indices = set(row_order[:test_count])
    train_rows = [dict(row) for i, row in enumerate(cleaned_rows) if i not in test_indices]
    test_rows = [dict(row) for i, row in enumerate(cleaned_rows) if i in test_indices]
    numeric_imputations = 0
    text_imputations = 0

    for column in NUMERIC_COLUMNS:
        training_values = [
            row[column] for row in train_rows if row[column] is not None
        ]
        if not training_values:
            raise ValueError(f"No training values available for {column}.")
        fill_value = statistics.median(training_values)
        for row in train_rows + test_rows:
            if row[column] is None:
                row[column] = fill_value
                numeric_imputations += 1

    for row in train_rows + test_rows:
        for column in TEXT_COLUMNS:
            if row[column] is None or not str(row[column]).strip():
                row[column] = "Unknown"
                text_imputations += 1

    print(f"Numeric values filled with training medians: {numeric_imputations}")
    print(f"Text values filled with 'Unknown': {text_imputations}")
    print(f"Training rows: {len(train_rows)}; test rows: {len(test_rows)}")

    explain(
        "Step 4: I will find training-set outliers using 1.5 times the IQR, then "
        "cap values outside the training 1st and 99th percentiles. The same "
        "limits will be used for both splits."
    )
    iqr_outlier_values = 0
    capped_values = 0
    cap_limits = {}
    for column in NUMERIC_COLUMNS:
        training_values = [row[column] for row in train_rows]
        q1 = percentile(training_values, 0.25)
        q3 = percentile(training_values, 0.75)
        iqr = q3 - q1
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr
        lower_cap = percentile(training_values, 0.01)
        upper_cap = percentile(training_values, 0.99)
        cap_limits[column] = [lower_cap, upper_cap]
        for row in train_rows + test_rows:
            value = row[column]
            if value < lower_fence or value > upper_fence:
                iqr_outlier_values += 1
            if value < lower_cap:
                row[column] = lower_cap
                capped_values += 1
            elif value > upper_cap:
                row[column] = upper_cap
                capped_values += 1

    print(f"IQR outlier values found: {iqr_outlier_values}")
    print(f"Values capped to training 1st/99th percentiles: {capped_values}")

    explain(
        "Step 5: I will calculate each feature's mean and population standard "
        "deviation from training rows only, then apply those same values to the "
        "test rows. This is the StandardScaler formula, implemented here without "
        "scikit-learn because it cannot import in this environment."
    )
    scaler_parameters = {}
    for column in NUMERIC_COLUMNS:
        values = [row[column] for row in train_rows]
        mean = statistics.mean(values)
        standard_deviation = math.sqrt(
            sum((value - mean) ** 2 for value in values) / len(values)
        )
        if standard_deviation == 0:
            standard_deviation = 1.0
        scaler_parameters[column] = {
            "training_mean": mean,
            "training_population_std": standard_deviation,
        }
        for row in train_rows + test_rows:
            row[column] = (row[column] - mean) / standard_deviation

    columns.append("split")
    for row in train_rows:
        row["split"] = "train"
    for row in test_rows:
        row["split"] = "test"
    processed_rows = train_rows + test_rows
    write_csv(CLEAN_FILE, processed_rows, columns)
    write_csv(
        TRAIN_FILE,
        [{column: row[column] for column in columns[:-1]} for row in train_rows],
        columns[:-1],
    )
    write_csv(
        TEST_FILE,
        [{column: row[column] for column in columns[:-1]} for row in test_rows],
        columns[:-1],
    )

    after = {
        "rows": len(processed_rows),
        "missing_values": missing_count(processed_rows, columns),
        "duplicate_rows": duplicate_count(processed_rows, columns),
    }
    summary = {
        "data_source": "synthetic, fictional; Kaggle endpoint returned HTTP 404",
        "runtime_note": (
            "Executed with Python standard library. NumPy was blocked by Windows "
            "Application Control; pandas, scikit-learn, and python-docx were not used."
        ),
        "before": before,
        "after": after,
        "removed_duplicates": removed_duplicates,
        "removed_invalid_dates": removed_invalid_dates,
        "removed_bad_shipping_dates": removed_bad_shipping_dates,
        "removed_negative_rows": removed_negative_rows,
        "dropped_empty_columns": len(empty_columns),
        "numeric_imputations": numeric_imputations,
        "text_imputations": text_imputations,
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "iqr_outlier_values": iqr_outlier_values,
        "capped_values": capped_values,
        "cap_limits": cap_limits,
        "scaler_parameters": scaler_parameters,
    }

    explain(
        "Step 6: I will compare the raw and processed row, missing-value, and "
        "duplicate counts so the overall cleaning effect is easy to check."
    )
    print("Measure          Before      After")
    print(f"Rows              {before['rows']:>6}      {after['rows']:>6}")
    print(
        f"Missing values    {before['missing_values']:>6}      "
        f"{after['missing_values']:>6}"
    )
    print(
        f"Duplicate rows    {before['duplicate_rows']:>6}      "
        f"{after['duplicate_rows']:>6}"
    )

    with SUMMARY_FILE.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)
    make_report(summary)
    print(f"\nSynthetic source data: {RAW_FILE}")
    print(f"Processed data: {CLEAN_FILE}")
    print(f"Scaled train/test files: {TRAIN_FILE}, {TEST_FILE}")
    print(f"Word report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
