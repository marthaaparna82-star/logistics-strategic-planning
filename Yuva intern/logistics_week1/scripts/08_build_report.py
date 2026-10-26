"""Build a Word-compatible .docx report using only Python's standard library."""

import csv
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
REPORT_FILE = ROOT / "report" / "FreshKart_Strategic_Planning_Report.docx"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
}
for prefix, uri in NS.items():
    if prefix not in ("rel", "ct"):
        ET.register_namespace(prefix, uri)


def tag(prefix, local):
    return f"{{{NS[prefix]}}}{local}"


def read_json(filename):
    with (OUTPUT_DIR / filename).open(encoding="utf-8") as file:
        return json.load(file)


def add_text(body, text, style=None, bold=False, font_size=None):
    paragraph = ET.SubElement(body, tag("w", "p"))
    if style:
        properties = ET.SubElement(paragraph, tag("w", "pPr"))
        ET.SubElement(properties, tag("w", "pStyle"), {tag("w", "val"): style})
    run = ET.SubElement(paragraph, tag("w", "r"))
    if bold or font_size:
        properties = ET.SubElement(run, tag("w", "rPr"))
        if bold:
            ET.SubElement(properties, tag("w", "b"))
        if font_size:
            ET.SubElement(properties, tag("w", "sz"), {tag("w", "val"): str(font_size)})
    value = ET.SubElement(run, tag("w", "t"))
    value.text = str(text)
    if str(text).startswith(" ") or str(text).endswith(" "):
        value.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return paragraph


def heading(body, title, level=1):
    return add_text(body, title, style=f"Heading{level}")


def bullet(body, text):
    return add_text(body, f"• {text}")


def add_table(body, headers, rows):
    table = ET.SubElement(body, tag("w", "tbl"))
    properties = ET.SubElement(table, tag("w", "tblPr"))
    ET.SubElement(properties, tag("w", "tblStyle"), {tag("w", "val"): "TableGrid"})
    borders = ET.SubElement(properties, tag("w", "tblBorders"))
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        ET.SubElement(
            borders,
            tag("w", edge),
            {tag("w", "val"): "single", tag("w", "sz"): "4", tag("w", "color"): "AAB7C4"},
        )
    for row_index, values in enumerate([headers] + list(rows)):
        row = ET.SubElement(table, tag("w", "tr"))
        for text in values:
            cell = ET.SubElement(row, tag("w", "tc"))
            cell_properties = ET.SubElement(cell, tag("w", "tcPr"))
            if row_index == 0:
                shading = ET.SubElement(cell_properties, tag("w", "shd"))
                shading.set(tag("w", "fill"), "DCE6F1")
            paragraph = ET.SubElement(cell, tag("w", "p"))
            run = ET.SubElement(paragraph, tag("w", "r"))
            if row_index == 0:
                ET.SubElement(run, tag("w", "rPr"))
                run_properties = run.find(tag("w", "rPr"))
                ET.SubElement(run_properties, tag("w", "b"))
            value = ET.SubElement(run, tag("w", "t"))
            value.text = str(text)
    return table


def add_image(body, relationship_id, name, width_px=900, height_px=520):
    width = 5_900_000
    height = int(width * height_px / width_px)
    paragraph = ET.SubElement(body, tag("w", "p"))
    run = ET.SubElement(paragraph, tag("w", "r"))
    drawing = ET.SubElement(run, tag("w", "drawing"))
    inline = ET.SubElement(
        drawing,
        tag("wp", "inline"),
        {"distT": "0", "distB": "0", "distL": "0", "distR": "0"},
    )
    ET.SubElement(inline, tag("wp", "extent"), {"cx": str(width), "cy": str(height)})
    ET.SubElement(inline, tag("wp", "effectExtent"), {"l": "0", "t": "0", "r": "0", "b": "0"})
    ET.SubElement(inline, tag("wp", "docPr"), {"id": str(relationship_id), "name": name})
    frame = ET.SubElement(inline, tag("wp", "cNvGraphicFramePr"))
    ET.SubElement(frame, tag("a", "graphicFrameLocks"), {"noChangeAspect": "1"})
    graphic = ET.SubElement(inline, tag("a", "graphic"))
    graphic_data = ET.SubElement(
        graphic,
        tag("a", "graphicData"),
        {"uri": "http://schemas.openxmlformats.org/drawingml/2006/picture"},
    )
    picture = ET.SubElement(graphic_data, tag("pic", "pic"))
    nonvisual = ET.SubElement(picture, tag("pic", "nvPicPr"))
    ET.SubElement(nonvisual, tag("pic", "cNvPr"), {"id": str(relationship_id), "name": name})
    ET.SubElement(nonvisual, tag("pic", "cNvPicPr"))
    fill = ET.SubElement(picture, tag("pic", "blipFill"))
    ET.SubElement(fill, tag("a", "blip"), {tag("r", "embed"): f"rId{relationship_id}"})
    stretch = ET.SubElement(fill, tag("a", "stretch"))
    ET.SubElement(stretch, tag("a", "fillRect"))
    shape = ET.SubElement(picture, tag("pic", "spPr"))
    transform = ET.SubElement(shape, tag("a", "xfrm"))
    ET.SubElement(transform, tag("a", "off"), {"x": "0", "y": "0"})
    ET.SubElement(transform, tag("a", "ext"), {"cx": str(width), "cy": str(height)})
    geometry = ET.SubElement(shape, tag("a", "prstGeom"), {"prst": "rect"})
    ET.SubElement(geometry, tag("a", "avLst"))


def styles_xml():
    root = ET.Element(tag("w", "styles"))
    normal = ET.SubElement(root, tag("w", "style"), {tag("w", "type"): "paragraph", tag("w", "default"): "1", tag("w", "styleId"): "Normal"})
    ET.SubElement(normal, tag("w", "name"), {tag("w", "val"): "Normal"})
    run = ET.SubElement(normal, tag("w", "rPr"))
    ET.SubElement(run, tag("w", "rFonts"), {tag("w", "ascii"): "Calibri", tag("w", "hAnsi"): "Calibri"})
    ET.SubElement(run, tag("w", "sz"), {tag("w", "val"): "20"})
    for level in (1, 2):
        style = ET.SubElement(root, tag("w", "style"), {tag("w", "type"): "paragraph", tag("w", "styleId"): f"Heading{level}"})
        ET.SubElement(style, tag("w", "name"), {tag("w", "val"): f"heading {level}"})
        based = ET.SubElement(style, tag("w", "basedOn"), {tag("w", "val"): "Normal"})
        based.tail = None
        ppr = ET.SubElement(style, tag("w", "pPr"))
        ET.SubElement(ppr, tag("w", "keepNext"))
        rpr = ET.SubElement(style, tag("w", "rPr"))
        ET.SubElement(rpr, tag("w", "b"))
        ET.SubElement(rpr, tag("w", "sz"), {tag("w", "val"): "30" if level == 1 else "24"})
        ET.SubElement(rpr, tag("w", "color"), {tag("w", "val"): "174A6E"})
    title = ET.SubElement(root, tag("w", "style"), {tag("w", "type"): "paragraph", tag("w", "styleId"): "Title"})
    ET.SubElement(title, tag("w", "name"), {tag("w", "val"): "Title"})
    run = ET.SubElement(title, tag("w", "rPr"))
    ET.SubElement(run, tag("w", "b"))
    ET.SubElement(run, tag("w", "sz"), {tag("w", "val"): "36"})
    ET.SubElement(run, tag("w", "color"), {tag("w", "val"): "174A6E"})
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def make_report_xml():
    kpis = read_json("baseline_kpis.json")
    forecast = read_json("forecast_metrics.json")
    clustering = read_json("product_segmentation_metrics.json")
    route = read_json("sample_route_plan.json")
    body = ET.Element(tag("w", "body"))
    add_text(body, "FreshKart Strategic Planning and Data Exploration", style="Title")
    add_text(body, "Week 1 Internship Task | Fictional online retailer")
    add_text(
        body,
        "DATA NOTICE: All order, product, cost, KPI, and chart data in this report are synthetic and reproducible. They are not FreshKart operational measurements.",
        bold=True,
    )

    heading(body, "1. Executive Summary")
    add_text(
        body,
        f"FreshKart is modeled as one warehouse, three regional hubs, and 40 delivery vans. "
        f"The synthetic baseline contains {kpis['order_lines']:,} order lines. It records an "
        f"OTIF rate of {kpis['otif_rate']:.1%}, average delivery lead time of "
        f"{kpis['average_delivery_lead_time_days']:.2f} days, fill rate of {kpis['fill_rate']:.1%}, "
        f"and delivery cost proxy of {kpis['cost_per_delivery']:.2f} synthetic cost units per delivery. "
        "These results demonstrate the workflow, not actual company performance. Replace the sample "
        "with validated order, inventory, finance, and route data before making operating decisions."
    )

    heading(body, "2. Project Definition")
    add_text(body, "Scenario: FreshKart serves online customers from one warehouse through three regional hubs, using a fleet of 40 vans.")
    add_text(body, "Problem statement: stock-outs on popular items, late deliveries, and high delivery cost can reduce service quality and profitability.")
    add_text(body, "Objectives:")
    for item in [
        "Establish a baseline for delivery service, lead time, item fill, and delivery cost.",
        "Explore service and demand by region, shipping mode, month, and product.",
        "Demonstrate forecasting, product segmentation, inventory formulas, and a capacity-aware routing example.",
        "Define an eight-week path from data collection to evaluated decision support.",
    ]:
        bullet(body, item)
    add_text(body, "Scope: synthetic order-line data and an illustrative routing example. No live system, supplier lead-time record, road-network distance, or real cost ledger is connected.")

    heading(body, "3. KPIs")
    add_table(
        body,
        ["KPI", "Formula", "Why it matters", "Synthetic baseline", "Proposed target"],
        [
            ["OTIF rate", "Delivered on/before promise AND fulfilled >= ordered; divided by delivered orders.", "Shows complete orders arriving on time.", f"{kpis['otif_rate']:.1%}", ">=95%; confirm service commitments."],
            ["Average delivery lead time", "Mean(delivery date - order date), in days.", "Tracks speed and supports lead-time planning.", f"{kpis['average_delivery_lead_time_days']:.2f} days", "<=3 days; validate by shipping mode."],
            ["Fill rate", "Total fulfilled quantity / total ordered quantity.", "Highlights unfilled demand and stock-out risk.", f"{kpis['fill_rate']:.1%}", ">=97%; prioritize popular items."],
            ["Cost per delivery", "Delivery cost sum / delivered order count.", "Monitors delivery economics; sample cost is a proxy.", f"{kpis['cost_per_delivery']:.2f} synthetic cost units", "10% below a validated baseline."],
        ],
    )
    add_text(body, "Targets are proposed planning goals, not observed results. Synthetic cost units are not a real currency.")

    heading(body, "4. Background and Data Research")
    add_text(
        body,
        "The Olist Brazilian E-Commerce dataset on Kaggle was considered as a public source. The unauthenticated download attempt returned HTTP 404, so it was not used. This project instead generates a reproducible synthetic order dataset containing order/promised/delivery dates, product, quantity, region, shipping mode, fulfillment, and illustrative cost fields. No external retail records were downloaded."
    )
    add_text(body, "Synthetic records demonstrate methods and test scripts, but cannot establish FreshKart's actual performance, demand, cost, or targets.")

    heading(body, "5. Data Science Methods")
    add_table(
        body,
        ["Method", "Logistics problem addressed", "Implementation and result"],
        [
            ["Regression forecasting", "Estimate demand for replenishment and capacity planning.", f"Weekly lag/rolling-feature least-squares model with time split. WAPE {forecast['regression_wape']:.1%}; last-week naive WAPE {forecast['naive_last_week_wape']:.1%}. Lower is better."],
            ["Classification", "Predict late-delivery or stock-out risk for early intervention.", "Proposed follow-on only. Requires validated risk labels; no classifier was fitted in this task."],
            ["ABC/XYZ and K-Means", "Prioritize item value, demand variability, and similar products.", f"ABC/XYZ product segments and K-Means were generated; selected k={clustering['selected_k']}, silhouette={clustering['silhouette_score']:.3f}."],
            ["Optimization", "Assign delivery stops while respecting vehicle capacity.", f"Capacity-feasible nearest-stop heuristic; sample distance {route['total_distance_units'] / 1000:.2f} coordinate units. OR-Tools could not run under the Windows policy restriction."],
        ],
    )

    heading(body, "6. Strategic Roadmap")
    add_text(body, "The roadmap moves from trustworthy inputs to measured operational decisions. The schedule is indicative; no deployment is claimed.")
    add_table(
        body,
        ["Week", "Stage", "Planned work"],
        [
            ["1", "Data collection", "Connect order, inventory, product, cost, hub, and delivery events; define owners."],
            ["2", "Cleaning", "Validate identifiers, missing values, timestamps, units, and business definitions."],
            ["3", "EDA", "Review demand, late delivery, fill, and cost by region and shipping mode."],
            ["4", "Feature engineering", "Build calendar, lag, rolling-demand, lead-time, and service-risk features."],
            ["5", "Modeling", "Back-test demand forecasting; evaluate a delay-risk classifier with reliable labels."],
            ["6", "Optimization", "Pilot reorder policies and capacity-aware routing with real operating constraints."],
            ["7", "Evaluation", "Compare to baselines; measure service, cost, robustness, and adoption."],
            ["8", "Dashboard", "Publish governed KPI views, alerts, owners, and refresh routines."],
        ],
    )

    heading(body, "7. Code Illustrations")
    heading(body, "Cleaning duplicates", 2)
    add_text(body, 'if row["order_id"] in seen: duplicates += 1; continue')
    heading(body, "Forecast lag and rolling features", 2)
    add_text(body, "features = [1.0, past[-1], past[-2], sum(past) / len(past)]")
    heading(body, "Inventory reorder point", 2)
    add_text(body, "safety_stock = z * daily_std * sqrt(lead_time_days)")
    add_text(body, "reorder_point = average_daily_demand * lead_time_days + safety_stock")
    heading(body, "Capacity-feasible route selection", 2)
    add_text(body, "feasible = [stop for stop in unassigned if load + demand[stop] <= vehicle_capacity]")
    add_text(body, "next_stop = min(feasible, key=distance_from_current_stop)")

    heading(body, "8. Risks and Mitigation")
    for item in [
        "Synthetic-data risk: sample outputs can be mistaken for actuals. Keep labels visible and replace with governed operational data.",
        "Data-quality risk: incomplete or inconsistent timestamps distort service KPIs. Define event semantics and validate input data.",
        "Forecast risk: sparse history, promotions, and seasonality can destabilize estimates. Back-test by time and compare against simple baselines.",
        "Inventory risk: service factor, lead time, order cost, and holding cost are assumptions. Calibrate with supplier and finance records before use.",
        "Routing risk: sample coordinates omit roads, traffic, time windows, driver hours, and hub constraints. Validate these before a routing pilot.",
        "Runtime and method limitation: Windows Application Control blocked NumPy's compiled extension. Standard-library substitutes were used; install/run in an approved environment to use pandas, scikit-learn, and OR-Tools.",
    ]:
        bullet(body, item)

    heading(body, "9. Conclusion and Expected Outcomes")
    add_text(
        body,
        "This project delivers a repeatable starting workflow: data cleaning, a synthetic KPI baseline, exploratory charts, a forecast-versus-naive comparison, product segmentation, inventory calculations, and a capacity-aware route demonstration. With real FreshKart data, the methods can help prioritize replenishment, identify service bottlenecks, compare transport choices, and test lower-cost routes. Benefits must be demonstrated in a controlled pilot against a validated operational baseline."
    )

    heading(body, "10. References")
    for reference in [
        "Kaggle, Brazilian E-Commerce Public Dataset by Olist: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce (considered; download endpoint returned HTTP 404).",
        "Google OR-Tools, Vehicle Routing: https://developers.google.com/optimization/routing (reference for the requested method; not executed here).",
        "scikit-learn, RandomForestRegressor: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html (reference for the originally planned method; standard-library regression used instead).",
        "Local synthetic data generator: scripts/00_generate_synthetic_data.py.",
    ]:
        bullet(body, reference)

    heading(body, "Appendix: Exploratory charts")
    charts = [
        ("Late orders by region", "late_orders_by_region.png"),
        ("Late orders by shipping mode", "late_orders_by_shipping_mode.png"),
        ("Monthly demand trend", "monthly_demand_trend.png"),
        ("Top products by synthetic sales value", "top_products_by_sales.png"),
        ("On-time delivery share by region", "on_time_share_by_region.png"),
        ("Weekly forecast test period", "weekly_demand_forecast.png"),
    ]
    for index, (title, filename) in enumerate(charts, start=1):
        heading(body, title, 2)
        add_image(body, index, filename)

    section = ET.SubElement(body, tag("w", "sectPr"))
    page = ET.SubElement(section, tag("w", "pgSz"), {tag("w", "w"): "12240", tag("w", "h"): "15840"})
    page.set(tag("w", "orient"), "portrait")
    return body


def write_docx():
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    body = make_report_xml()
    document = ET.Element(tag("w", "document"))
    document.append(body)
    document_xml = ET.tostring(document, encoding="utf-8", xml_declaration=True)

    relationships = ET.Element(tag("rel", "Relationships"))
    ET.SubElement(
        relationships,
        tag("rel", "Relationship"),
        {
            "Id": "rIdStyles",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles",
            "Target": "styles.xml",
        },
    )
    chart_names = [
        "late_orders_by_region.png",
        "late_orders_by_shipping_mode.png",
        "monthly_demand_trend.png",
        "top_products_by_sales.png",
        "on_time_share_by_region.png",
        "weekly_demand_forecast.png",
    ]
    for index, filename in enumerate(chart_names, start=1):
        ET.SubElement(
            relationships,
            tag("rel", "Relationship"),
            {
                "Id": f"rId{index}",
                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                "Target": f"media/{filename}",
            },
        )

    content_types = ET.Element(tag("ct", "Types"))
    ET.SubElement(content_types, tag("ct", "Default"), {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
    ET.SubElement(content_types, tag("ct", "Default"), {"Extension": "xml", "ContentType": "application/xml"})
    ET.SubElement(content_types, tag("ct", "Default"), {"Extension": "png", "ContentType": "image/png"})
    ET.SubElement(
        content_types,
        tag("ct", "Override"),
        {"PartName": "/word/document.xml", "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"},
    )
    ET.SubElement(
        content_types,
        tag("ct", "Override"),
        {"PartName": "/word/styles.xml", "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"},
    )

    package_relationships = ET.Element(tag("rel", "Relationships"))
    ET.SubElement(
        package_relationships,
        tag("rel", "Relationship"),
        {
            "Id": "rId1",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
            "Target": "word/document.xml",
        },
    )

    with zipfile.ZipFile(REPORT_FILE, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", ET.tostring(content_types, encoding="utf-8", xml_declaration=True))
        package.writestr("_rels/.rels", ET.tostring(package_relationships, encoding="utf-8", xml_declaration=True))
        package.writestr("word/document.xml", document_xml)
        package.writestr("word/styles.xml", styles_xml())
        package.writestr("word/_rels/document.xml.rels", ET.tostring(relationships, encoding="utf-8", xml_declaration=True))
        for filename in chart_names:
            package.write(OUTPUT_DIR / filename, f"word/media/{filename}")
    return REPORT_FILE


if __name__ == "__main__":
    print(f"Report created: {write_docx()}")
