from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "Kigali_Transport_Delay_Analytics_Report.pdf"

NAVY = colors.HexColor("#0A1628")
NAVY_2 = colors.HexColor("#10233F")
CYAN = colors.HexColor("#42C5E6")
BLUE = colors.HexColor("#087CF0")
ORANGE = colors.HexColor("#F28C36")
MINT = colors.HexColor("#1EB980")
INK = colors.HexColor("#1D2A3A")
MUTED = colors.HexColor("#5F7187")
PALE = colors.HexColor("#F3F7FB")
LINE = colors.HexColor("#D9E3EE")


styles = getSampleStyleSheet()
styles.add(ParagraphStyle("ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=30, leading=35, textColor=NAVY, alignment=TA_LEFT, spaceAfter=12))
styles.add(ParagraphStyle("Subtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=13, leading=19, textColor=MUTED, spaceAfter=10))
styles.add(ParagraphStyle("H1x", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=22, leading=27, textColor=NAVY, spaceBefore=0, spaceAfter=12))
styles.add(ParagraphStyle("H2x", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=BLUE, spaceBefore=10, spaceAfter=7))
styles.add(ParagraphStyle("Bodyx", parent=styles["BodyText"], fontName="Helvetica", fontSize=10.5, leading=16, textColor=INK, spaceAfter=8))
styles.add(ParagraphStyle("Smallx", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.5, leading=12, textColor=MUTED, spaceAfter=5))
styles.add(ParagraphStyle("Callout", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=11, leading=16, textColor=NAVY, backColor=PALE, borderColor=CYAN, borderWidth=1, borderPadding=9, spaceBefore=8, spaceAfter=10))
styles.add(ParagraphStyle("Codex", parent=styles["Code"], fontName="Courier", fontSize=8.2, leading=11, textColor=colors.HexColor("#D8E7F5"), backColor=NAVY, borderPadding=10, spaceBefore=5, spaceAfter=10))
styles.add(ParagraphStyle("TableHead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.white, alignment=TA_LEFT))
styles.add(ParagraphStyle("TableCell", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.4, leading=11, textColor=INK))


def P(value, style="Bodyx"):
    return Paragraph(value, styles[style])


def bullet(items):
    return [P(f"&#8226; {item}", "Bodyx") for item in items]


def table(data, widths):
    formatted = []
    for r, row in enumerate(data):
        formatted.append([P(str(cell), "TableHead" if r == 0 else "TableCell") for cell in row])
    t = Table(formatted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY_2),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def architecture_diagram():
    d = Drawing(500, 210)
    nodes = [(20, 125, 92, 42, "Reference CSV", CYAN), (145, 125, 92, 42, "Generator", BLUE), (270, 125, 92, 42, "Kafka", ORANGE), (395, 125, 92, 42, "MySQL", MINT)]
    for x, y, w, h, label, color in nodes:
        d.add(Rect(x, y, w, h, rx=7, ry=7, fillColor=colors.white, strokeColor=color, strokeWidth=2))
        d.add(String(x + w / 2, y + 23, label, textAnchor="middle", fontName="Helvetica-Bold", fontSize=10, fillColor=NAVY))
    for x in (112, 237, 362):
        d.add(Line(x, 146, x + 30, 146, strokeColor=MUTED, strokeWidth=1.5))
        d.add(Polygon([x + 30, 146, x + 24, 150, x + 24, 142], fillColor=MUTED, strokeColor=MUTED))
    d.add(Rect(145, 35, 92, 42, rx=7, ry=7, fillColor=colors.white, strokeColor=CYAN, strokeWidth=2))
    d.add(String(191, 58, "Django API", textAnchor="middle", fontName="Helvetica-Bold", fontSize=10, fillColor=NAVY))
    d.add(Rect(270, 35, 92, 42, rx=7, ry=7, fillColor=colors.white, strokeColor=ORANGE, strokeWidth=2))
    d.add(String(316, 58, "HDFS + Spark", textAnchor="middle", fontName="Helvetica-Bold", fontSize=10, fillColor=NAVY))
    d.add(Line(316, 125, 316, 77, strokeColor=ORANGE, strokeWidth=1.5))
    d.add(Polygon([316, 77, 312, 84, 320, 84], fillColor=ORANGE, strokeColor=ORANGE))
    d.add(Line(191, 125, 191, 77, strokeColor=CYAN, strokeWidth=1.5))
    d.add(Polygon([191, 77, 187, 84, 195, 84], fillColor=CYAN, strokeColor=CYAN))
    d.add(String(250, 8, "Live operational path", fontName="Helvetica-Oblique", fontSize=8, fillColor=MUTED))
    return d


def lifecycle_diagram():
    d = Drawing(500, 165)
    steps = [(15, "1", "Generate", CYAN), (135, "2", "Publish", BLUE), (255, "3", "Persist", MINT), (375, "4", "Visualize", ORANGE)]
    for i, (x, number, label, color) in enumerate(steps):
        d.add(Rect(x, 65, 90, 54, rx=8, ry=8, fillColor=NAVY_2, strokeColor=color, strokeWidth=2))
        d.add(String(x + 45, 94, number, textAnchor="middle", fontName="Helvetica-Bold", fontSize=18, fillColor=color))
        d.add(String(x + 45, 75, label, textAnchor="middle", fontName="Helvetica-Bold", fontSize=9, fillColor=colors.white))
        if i < 3:
            d.add(Line(x + 90, 92, x + 120, 92, strokeColor=MUTED, strokeWidth=1.5))
            d.add(Polygon([x + 120, 92, x + 114, 96, x + 114, 88], fillColor=MUTED, strokeColor=MUTED))
    d.add(String(250, 30, "Each event keeps its trip_id, route, schedule, location, weather, and delay attributes.", textAnchor="middle", fontSize=8.5, fillColor=MUTED))
    return d


def header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 9 * mm, width, 9 * mm, fill=1, stroke=0)
    canvas.setFillColor(CYAN)
    canvas.rect(0, height - 9 * mm, 12 * mm, 9 * mm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.setFillColor(colors.white)
    canvas.drawString(18 * mm, height - 6.1 * mm, "KIGALI PUBLIC TRANSPORT DELAY ANALYTICS")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(width - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.drawString(18 * mm, 10 * mm, "Big Data Essentials Final Project")
    canvas.restoreState()


doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=20 * mm, bottomMargin=18 * mm)
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
doc.addPageTemplates([PageTemplate(id="report", frames=frame, onPage=header_footer)])

story = []

# Cover
story += [Spacer(1, 25 * mm), P("Kigali Public Transport<br/>Delay Analytics Platform", "ReportTitle"), P("Project Report | Big Data Essentials Final Project", "Subtitle"), Spacer(1, 10 * mm)]
story.append(architecture_diagram())
story += [Spacer(1, 12 * mm), P("A practical big data pipeline for generating transport events, streaming them through Kafka, storing them in MySQL, and supporting delay decisions through a Django dashboard and Spark MLlib.", "Callout"), Spacer(1, 15 * mm), P("Prepared for academic demonstration and local Windows deployment", "Smallx"), PageBreak()]

# Executive summary
story += [P("1. Executive Summary", "H1x"), P("This project implements an end-to-end transport intelligence platform for Kigali. It starts with a historical Rwanda public transport delay dataset and turns its empirical relationships into a continuous stream of synthetic trip events. The events can be generated directly into MySQL or published through Kafka for streaming demonstrations.", "Bodyx"), P("The operational layer is a Django dashboard backed by MySQL. It reports total trips, observed delay rate, active routes, transport mix, recent trip activity, map coordinates, and a feature-based delay risk estimate. A separate HDFS and Spark MLlib path demonstrates how the same data domain can support distributed storage and model training.", "Bodyx"), P("The central design decision is to use MySQL as the single runtime operational source of truth. Historical SQLite records are treated only as a migration source; live dashboard and generator writes go to MySQL.", "Callout"), P("Project objectives", "H2x"), *bullet(["Create realistic synthetic trip events while preserving relationships in the reference data.", "Demonstrate route-keyed Kafka publishing and broker acknowledgement.", "Provide a queryable MySQL operational store for live dashboard metrics.", "Show a Hadoop and Spark MLlib workflow without leaking target variables into model features."]), PageBreak()]

# Problem and scope
story += [P("2. Problem Definition and Scope", "H1x"), P("Urban transport operations generate data across routes, vehicles, schedules, weather conditions, traffic levels, and observed delays. A useful platform must bring these signals together quickly enough for an operator to identify high-risk routes and understand current network conditions.", "Bodyx"), P("The project focuses on the data engineering lifecycle rather than a production dispatch system. It uses synthetic events derived from historical observations, which makes the system safe to demonstrate and repeatable on a local Windows machine.", "Bodyx"), P("Scope boundaries", "H2x"), table([["Included", "Purpose"], ["Synthetic event generation", "Create repeatable live-like records from the seed distribution."], ["Kafka publishing", "Move keyed events through a streaming topic."], ["MySQL persistence", "Support operational queries, replay, and dashboard summaries."], ["Django REST dashboard", "Expose current metrics, map data, and risk estimates."], ["HDFS and Spark MLlib", "Demonstrate historical storage and distributed model training."]], [55 * mm, 108 * mm]), Spacer(1, 7 * mm), P("The system is intentionally modular: generation, transport, storage, web presentation, and model training can be inspected independently while still forming one coherent pipeline.", "Bodyx"), PageBreak()]

# Architecture
story += [P("3. System Architecture", "H1x"), P("The architecture separates the live operational path from the historical analytics path. The live path prioritizes low-latency generation, streaming, and dashboard queries. The analytics path prioritizes durable historical storage and model training.", "Bodyx"), architecture_diagram(), Spacer(1, 6 * mm), table([["Component", "Responsibility", "Implementation"], ["Reference data", "Empirical source distribution", "rwanda_public_transport_delays.csv"], ["Generator", "Samples rows and assigns new event identity", "Python standard library"], ["Producer", "Publishes route-keyed JSON events", "confluent-kafka"], ["Operational store", "Stores live trip events", "MySQL / InnoDB"], ["Dashboard", "Summarizes and visualizes current state", "Django + Django REST Framework"], ["Historical analytics", "Stores training input and model artifacts", "HDFS + Spark MLlib"]], [35 * mm, 68 * mm, 60 * mm]), PageBreak()]

# Data model
story += [P("4. Data Generation and Event Model", "H1x"), P("TripEventGenerator samples a complete source row rather than sampling individual columns independently. This preserves useful relationships such as route and district combinations, weather and precipitation, congestion and delay outcomes, and transport type patterns.", "Bodyx"), lifecycle_diagram(), Spacer(1, 5 * mm), P("An event receives a new SIM-prefixed trip ID, current date and time, scheduled departure and arrival values based on the source duration, and an event_generated_at timestamp in GMT+2. Numeric CSV fields are converted before JSON serialization so Kafka consumers, Spark, and MySQL receive usable numeric types.", "Bodyx"), P("Representative event fields", "H2x"), table([["Group", "Fields"], ["Identity", "trip_id, date, time, event_generated_at"], ["Network", "route_id, vehicle_id, transport_type"], ["Location", "origin/destination station, district, latitude, longitude"], ["Schedule and delay", "scheduled times, actual departure/arrival delay, delayed"], ["Conditions", "weather, temperature, humidity, wind, precipitation"], ["Demand and traffic", "passengers carried, attendance estimate, congestion index, peak hour"]], [43 * mm, 120 * mm]), PageBreak()]

# Streaming
story += [P("5. Streaming and Reliability", "H1x"), P("The Django REST producer publishes each generated event to the configured Kafka topic, normally kigali-trip-events. The route_id is used as the Kafka key. Kafka's keyed partitioning keeps events for one route ordered while allowing independent routes to be processed in parallel.", "Bodyx"), P("The producer is configured with acknowledgements from all in-sync replicas and idempotence enabled. It flushes outstanding messages and returns delivery metadata only after the broker acknowledges the records. This gives the demonstration a visible delivery contract rather than silently assuming that a send succeeded.", "Bodyx"), table([["Choice", "Reason"], ["route_id key", "Preserve per-route ordering and distribute different routes."], ["acks=all", "Wait for the strongest available broker acknowledgement."], ["enable.idempotence=true", "Reduce duplicate writes caused by producer retries."], ["delivery callback", "Collect partition and offset information for the API response."], ["manual consumer commits", "Make at-least-once processing explicit and observable."]], [45 * mm, 118 * mm]), Spacer(1, 8 * mm), P("The project does not claim end-to-end exactly-once semantics. That trade-off is documented so the pipeline's guarantees remain understandable and defensible.", "Callout"), PageBreak()]

# MySQL
story += [P("6. MySQL Operational Storage", "H1x"), P("MySQL is the single runtime database for the dashboard and generated events. The transport_trip_events table is created by the existing persistence helper when needed and uses an InnoDB table with indexes for generated time and route queries.", "Bodyx"), table([["Storage concern", "Implementation"], ["Primary identity", "trip_id VARCHAR(64) PRIMARY KEY"], ["Time fields", "DATE, TIME, and DATETIME columns"], ["Numeric features", "DECIMAL, INT, and TINYINT columns"], ["Query support", "Indexes on event_generated_at and route_id"], ["Repeatable loads", "ON DUPLICATE KEY UPDATE for existing trip IDs"], ["Character set", "utf8mb4"]], [48 * mm, 115 * mm]), P("SQLite-to-MySQL migration", "H2x"), P("The project previously accumulated records while the dashboard used SQLite. A dedicated Django management command reads dashboard/db.sqlite3, normalizes timestamps, and copies rows to MySQL in batches. It can be rerun safely because the MySQL writer uses trip_id as the conflict key.", "Bodyx"), Preformatted(".\\.venv\\Scripts\\python.exe .\\dashboard\\manage.py replicate_sqlite_to_mysql", styles["Codex"]), P("After migration, the application is configured for MySQL-only runtime reads and writes. The old SQLite file is retained only as an archival migration source.", "Callout"), PageBreak()]

# Dashboard
story += [P("7. Django Dashboard and API", "H1x"), P("The dashboard is a Django application with REST endpoints for live data, summary metrics, event generation, and Kafka publishing. The browser refreshes current data on a short interval so a running demonstration visibly changes as new events arrive.", "Bodyx"), table([["Endpoint", "Function"], ["/", "Operational command-center dashboard."], ["/api/dashboard-data/", "Recent events, summary metrics, route and risk information."], ["/api/database-summary/", "Full-table aggregates and recent stored events."], ["/api/data/generate/", "Generate a batch and persist it to MySQL."], ["/api/trips/publish/", "Generate, store, and publish events to Kafka."], ["/api/preview-event/", "Return one non-persisted preview event."]], [55 * mm, 108 * mm]), P("The dashboard combines observed values with an explainable feature-based risk estimate. The estimate uses congestion, precipitation, peak hour, and weather penalties to produce a probability and predicted delay indicator while the Spark model path is being trained or deployed.", "Bodyx"), P("Operational views", "H2x"), *bullet(["KPI cards for stored events, delay rate, predicted delays, and top route.", "Leaflet map markers based on origin coordinates.", "Route volume bars and transport mix breakdown.", "Recent trip activity with route, mode, district, and risk state.", "Database summary showing full-table totals rather than only the latest window."]), PageBreak()]

# ML
story += [P("8. HDFS and Spark MLlib Workflow", "H1x"), P("The historical analytics path stores the reference CSV in HDFS and trains a delay classifier with Spark MLlib. This demonstrates the transition from an operational stream to distributed historical processing.", "Bodyx"), table([["Stage", "Output"], ["HDFS setup", "Project-owned NameNode and DataNode directories."], ["Reference upload", "Historical CSV stored in HDFS."], ["Feature preparation", "Planning and dispatch features assembled without target leakage."], ["Model training", "Spark MLlib pipeline for delay classification."], ["Evaluation", "AUC, accuracy, F1, and row counts."], ["Artifacts", "/models/kigali_delay_classifier and /analytics/model_metrics"]], [45 * mm, 118 * mm]), P("Avoiding target leakage", "H2x"), P("The training job deliberately excludes actual arrival and departure delay fields because those values are only known after a trip has occurred. Including them would make evaluation look stronger while producing a model that could not support planning-time decisions.", "Callout"), Preformatted("$env:HADOOP_CONF_DIR = \"$PWD\\infrastructure\\hadoop-conf\"\nC:\\Spark_set_up\\spark-4.2.0\\bin\\spark-submit.cmd .\\ml\\training\\train_delay_classifier.py", styles["Codex"]), PageBreak()]

# Testing and validation
story += [P("9. Testing and Validation", "H1x"), P("Validation focused on the highest-risk integration boundaries: database selection, event persistence, MySQL compatibility, and the dashboard generation endpoint.", "Bodyx"), table([["Check", "Result"], ["Django system check", "Passed with no reported issues."], ["Python compilation", "Edited settings, views, migration command, and generator compiled successfully."], ["MySQL backend resolution", "Django reported vendor=mysql and the configured database name."], ["Dashboard generation request", "HTTP 201 with database_inserted count returned."], ["Live MySQL row verification", "Generated row count increased after the request."], ["SQLite migration", "Historical rows copied in batches with rerunnable upsert behavior."], ["Unit tests available", "Summary and transport-means aggregation tests in tests/test_summary.py."]], [62 * mm, 101 * mm]), P("A MySQL-specific issue was found and corrected during integration: delayed is reserved in some MySQL contexts and must be quoted in aggregate SQL expressions. This illustrates why database-backed endpoint tests are important even when the generator itself succeeds.", "Bodyx"), PageBreak()]

# Setup
story += [P("10. Installation and Demonstration", "H1x"), P("The project is designed for local Windows development with services started in separate PowerShell terminals.", "Bodyx"), P("1. Install dependencies", "H2x"), Preformatted("python -m venv .venv\n.\\.venv\\Scripts\\Activate.ps1\npip install -r requirements.txt", styles["Codex"]), P("2. Configure MySQL", "H2x"), Preformatted("$env:MYSQL_DATABASE = \"Rwanda_Public_Transport\"\n$env:MYSQL_USER = \"root\"\n$env:MYSQL_PASSWORD = \"your-password\"\n$env:MYSQL_HOST = \"localhost\"\n$env:MYSQL_PORT = \"3306\"", styles["Codex"]), P("3. Start the dashboard", "H2x"), Preformatted(".\\.venv\\Scripts\\python.exe .\\dashboard\\manage.py runserver", styles["Codex"]), P("4. Generate or publish data", "H2x"), Preformatted(".\\.venv\\Scripts\\python.exe .\\generator\\trip_generator.py --rate 5 --count 10 --mysql\nInvoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/trips/publish/ -ContentType \"application/json\" -Body '{\"count\": 10}'", styles["Codex"]), P("The dashboard is then available at http://127.0.0.1:8000/.", "Callout"), PageBreak()]

# Limitations and conclusion
story += [P("11. Limitations and Future Work", "H1x"), P("The current implementation is intentionally educational and locally deployable. Several areas would need hardening for production use.", "Bodyx"), *bullet(["Move credentials and secrets to a managed secret store rather than local environment files.", "Use a production WSGI server, authentication, authorization, and HTTPS for the dashboard.", "Add a dedicated Kafka consumer or Kafka Connect JDBC sink with operational monitoring.", "Add schema versioning and data-quality validation for changing event contracts.", "Measure model performance on a held-out, time-aware validation set and monitor drift.", "Add integration tests that start or mock Kafka and MySQL services in a controlled environment."]), P("Conclusion", "H2x"), P("This project demonstrates a complete, inspectable big data workflow: historical data becomes realistic events; events move through a keyed stream; MySQL provides operational persistence; Django exposes live decisions; and HDFS plus Spark extend the same domain into distributed analytics and machine learning.", "Bodyx"), P("The strongest practical outcome is the clear separation of concerns. Each component has a defined responsibility, a documented interface, and a validation path, making the platform suitable for demonstration, assessment, and future extension.", "Callout"), PageBreak()]

# Appendix
story += [P("12. Appendix: Repository Map", "H1x"), table([["Path", "Role"], ["generator/trip_generator.py", "Reference-driven synthetic event generation and direct MySQL mode."], ["producer/kafka_publisher.py", "Route-keyed Kafka publishing with delivery acknowledgement."], ["dashboard/config/settings.py", "Environment loading and MySQL-only Django database configuration."], ["dashboard/operations/views.py", "Persistence, dashboard APIs, summaries, and risk estimation."], ["dashboard/operations/templates/operations/dashboard.html", "Live operational dashboard UI."], ["dashboard/operations/management/commands/replicate_sqlite_to_mysql.py", "Historical SQLite-to-MySQL migration."], ["ml/training/train_delay_classifier.py", "Spark MLlib training job."], ["infrastructure/", "Kafka, HDFS, and local Windows setup scripts."], ["tests/test_summary.py", "Summary and transport aggregation tests."]], [78 * mm, 85 * mm]), Spacer(1, 10 * mm), P("End of report", "Subtitle")]

doc.build(story)
print(OUTPUT)