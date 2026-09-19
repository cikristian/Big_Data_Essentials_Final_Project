import math
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.conf import settings
from django.db import DatabaseError, connection, connections
from django.http import JsonResponse
from django.shortcuts import render

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_DIR = PROJECT_ROOT / "generator"
PRODUCER_DIR = PROJECT_ROOT / "producer"
for directory in (GENERATOR_DIR, PRODUCER_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from trip_generator import TripEventGenerator  # noqa: E402
from kafka_publisher import KafkaPublishError, TripKafkaPublisher  # noqa: E402
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


GMT_PLUS_2 = timezone(timedelta(hours=2), name="GMT+2")


MYSQL_EVENT_COLUMNS = (
    "trip_id", "date", "time", "transport_type", "route_id", "vehicle_id",
    "origin_station", "origin_district", "origin_latitude", "origin_longitude",
    "destination_station", "destination_district", "destination_latitude",
    "destination_longitude", "distance_km", "fare_rwf", "passengers_carried",
    "scheduled_departure", "scheduled_arrival", "actual_departure_delay_min",
    "actual_arrival_delay_min", "weather_condition", "temperature_C",
    "humidity_percent", "wind_speed_kmh", "precipitation_mm", "event_type",
    "event_attendance_est", "traffic_congestion_index", "holiday", "peak_hour",
    "weekday", "season", "delayed", "event_generated_at",
)


def new_preview_event() -> dict:
    """Generate a preview only; Kafka/MySQL integration comes in later stages."""
    return TripEventGenerator(PROJECT_ROOT / "rwanda_public_transport_delays.csv").next_event()


def database_has_events() -> bool:
    """Check whether the event table has any rows to seed or continue from."""
    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='transport_trip_events'"
            )
            if not cursor.fetchone():
                return False
            cursor.execute("SELECT COUNT(*) FROM transport_trip_events")
        else:
            cursor.execute("SHOW TABLES LIKE %s", ["transport_trip_events"])
            if not cursor.fetchone():
                return False
            cursor.execute("SELECT COUNT(*) FROM transport_trip_events")
        return int(cursor.fetchone()[0]) > 0


def seed_database_from_csv(count: int = 250) -> int:
    """Load an initial CSV-based batch into the database before continuing live generation."""
    generator = TripEventGenerator(PROJECT_ROOT / "rwanda_public_transport_delays.csv")
    events = [generator.next_event() for _ in range(max(1, count))]
    return store_events_in_mysql(events)


def keep_delay_rate_in_range(events: list[dict], minimum: float = 20, maximum: float = 78) -> None:
    """Keep the stored delay percentage within the requested range as new events arrive."""
    if not events or not database_has_events():
        return

    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(`delayed`), 0) FROM transport_trip_events")
        existing_total, existing_delayed = cursor.fetchone()

    new_total = int(existing_total) + len(events)
    minimum_delayed = math.ceil(new_total * minimum / 100)
    maximum_delayed = math.floor(new_total * maximum / 100)
    sampled_delayed = sum(int(event.get("delayed", 0) or 0) for event in events)
    lower_needed = max(0, minimum_delayed - int(existing_delayed))
    upper_allowed = maximum_delayed - int(existing_delayed)
    target_delayed = min(max(sampled_delayed, lower_needed), upper_allowed)

    for index, event in enumerate(events):
        event["delayed"] = int(index < target_delayed)


def _store_events_in_database(events: list[dict], database_alias: str = "default") -> int:
    """Persist generated events directly for dashboard queries and replay."""
    database_connection = connections[database_alias]
    rows = []
    for event in events:
        values = dict(event)
        generated_at = datetime.fromisoformat(values["event_generated_at"])
        values["event_generated_at"] = generated_at.astimezone(GMT_PLUS_2).replace(tzinfo=None)
        rows.append(tuple(values.get(column) for column in MYSQL_EVENT_COLUMNS))

    with database_connection.cursor() as cursor:
        if database_connection.vendor == "sqlite":
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS transport_trip_events (
                    trip_id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    transport_type TEXT NOT NULL,
                    route_id TEXT NOT NULL,
                    vehicle_id TEXT NOT NULL,
                    origin_station TEXT, origin_district TEXT,
                    origin_latitude REAL, origin_longitude REAL,
                    destination_station TEXT, destination_district TEXT,
                    destination_latitude REAL, destination_longitude REAL,
                    distance_km REAL, fare_rwf INTEGER, passengers_carried INTEGER,
                    scheduled_departure TEXT, scheduled_arrival TEXT,
                    actual_departure_delay_min INTEGER, actual_arrival_delay_min INTEGER,
                    weather_condition TEXT, temperature_C REAL,
                    humidity_percent REAL, wind_speed_kmh REAL,
                    precipitation_mm REAL, event_type TEXT,
                    event_attendance_est INTEGER, traffic_congestion_index INTEGER,
                    holiday INTEGER, peak_hour INTEGER, weekday INTEGER,
                    season TEXT, delayed INTEGER NOT NULL,
                    event_generated_at TEXT NOT NULL
                )
                """
            )
            placeholders = ", ".join(["?"] * len(MYSQL_EVENT_COLUMNS))
            sql = f"""
                INSERT OR REPLACE INTO transport_trip_events (
                    trip_id, date, time, transport_type, route_id, vehicle_id,
                    origin_station, origin_district, origin_latitude, origin_longitude,
                    destination_station, destination_district, destination_latitude,
                    destination_longitude, distance_km, fare_rwf, passengers_carried,
                    scheduled_departure, scheduled_arrival, actual_departure_delay_min,
                    actual_arrival_delay_min, weather_condition, temperature_C,
                    humidity_percent, wind_speed_kmh, precipitation_mm, event_type,
                    event_attendance_est, traffic_congestion_index, holiday, peak_hour,
                    weekday, season, delayed, event_generated_at
                ) VALUES ({placeholders})
            """
            cursor.executemany(sql, rows)
            return len(rows)

        quoted_columns = ", ".join(f"`{column}`" for column in MYSQL_EVENT_COLUMNS)
        placeholders = ", ".join(["%s"] * len(MYSQL_EVENT_COLUMNS))
        create_table = """
            CREATE TABLE IF NOT EXISTS transport_trip_events (
                trip_id VARCHAR(64) PRIMARY KEY,
                `date` DATE NOT NULL,
                `time` TIME NOT NULL,
                transport_type VARCHAR(16) NOT NULL,
                route_id VARCHAR(64) NOT NULL,
                vehicle_id VARCHAR(32) NOT NULL,
                origin_station VARCHAR(128), origin_district VARCHAR(64),
                origin_latitude DECIMAL(10,7), origin_longitude DECIMAL(10,7),
                destination_station VARCHAR(128), destination_district VARCHAR(64),
                destination_latitude DECIMAL(10,7), destination_longitude DECIMAL(10,7),
                distance_km DECIMAL(10,2), fare_rwf INT, passengers_carried INT,
                scheduled_departure TIME, scheduled_arrival TIME,
                actual_departure_delay_min INT, actual_arrival_delay_min INT,
                weather_condition VARCHAR(32), temperature_C DECIMAL(6,2),
                humidity_percent DECIMAL(6,2), wind_speed_kmh DECIMAL(6,2),
                precipitation_mm DECIMAL(8,2), event_type VARCHAR(64),
                event_attendance_est INT, traffic_congestion_index INT,
                holiday TINYINT, peak_hour TINYINT, weekday TINYINT,
                season VARCHAR(32), `delayed` TINYINT NOT NULL,
                event_generated_at DATETIME NOT NULL,
                INDEX idx_trip_events_generated_at (event_generated_at),
                INDEX idx_trip_events_route (route_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        cursor.execute(create_table)
        cursor.executemany(
            f"INSERT INTO transport_trip_events ({quoted_columns}) VALUES ({placeholders}) "
            "ON DUPLICATE KEY UPDATE event_generated_at = VALUES(event_generated_at)",
            rows,
        )
    return len(rows)


def store_events_in_mysql(events: list[dict]) -> int:
    """Persist events to the configured MySQL database."""
    return _store_events_in_database(events)


def dashboard(request):
    return render(request, "operations/dashboard.html")


def preview_event(request):
    return JsonResponse(new_preview_event())


def summarize_transport_means(events: list[dict]) -> dict[str, int]:
    """Count events by transport medium for the summary pages."""
    counts = Counter(
        str(item.get("transport_type") or "Unknown")
        for item in events
        if item.get("transport_type")
    )
    return dict(sorted(counts.items()))


def build_summary_from_events(events: list[dict]) -> dict[str, object]:
    """Build a dashboard summary from a list of event dictionaries."""
    if not events:
        return {
            "total_trips": 0,
            "delayed_trips": 0,
            "delay_rate": 0,
            "top_route": "-",
            "transport_counts": {},
            "transport_means": {},
            "highest_risk_route": "-",
            "highest_risk_probability": 0,
            "updated_at": datetime.now(GMT_PLUS_2).isoformat(),
        }

    total_trips = len(events)
    delayed_count = sum(int(item.get("delayed", 0) or 0) for item in events)
    route_counts = Counter(item.get("route_id", "Unknown") for item in events)
    transport_counts = summarize_transport_means(events)
    highest_risk = max(events, key=lambda item: float(item.get("delay_probability", 0) or 0), default={})

    return {
        "total_trips": total_trips,
        "delayed_trips": delayed_count,
        "delay_rate": round((delayed_count / total_trips) * 100, 1) if total_trips else 0,
        "top_route": route_counts.most_common(1)[0][0] if events else "-",
        "transport_counts": dict(transport_counts),
        "transport_means": dict(transport_counts),
        "highest_risk_route": highest_risk.get("route_id", "-"),
        "highest_risk_probability": highest_risk.get("delay_probability", 0),
        "updated_at": datetime.now(GMT_PLUS_2).isoformat(),
    }


def fetch_recent_events(limit: int = 100) -> list[dict]:
    """Return recent trip events from the active database when available."""
    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='transport_trip_events'"
            )
            if not cursor.fetchone():
                return []
            query = f"""
                SELECT trip_id, route_id, transport_type, origin_district,
                    destination_district, origin_latitude, origin_longitude,
                    scheduled_departure, scheduled_arrival,
                    actual_arrival_delay_min, traffic_congestion_index,
                    precipitation_mm, weather_condition, peak_hour, delayed,
                    event_generated_at
                FROM transport_trip_events
                ORDER BY event_generated_at DESC LIMIT {int(limit)}
            """
            cursor.execute(query)
        else:
            cursor.execute("SHOW TABLES LIKE %s", ["transport_trip_events"])
            if not cursor.fetchone():
                return []
            cursor.execute(
                """
                    SELECT trip_id, route_id, transport_type, origin_district,
                        destination_district, origin_latitude, origin_longitude,
                        scheduled_departure, scheduled_arrival,
                        actual_arrival_delay_min, traffic_congestion_index,
                        precipitation_mm, weather_condition, peak_hour, `delayed`,
                        event_generated_at
                    FROM transport_trip_events
                    ORDER BY event_generated_at DESC LIMIT %s
                """,
                [limit],
            )
        names = [column[0] for column in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]


def predict_event_risk(event: dict) -> dict[str, object]:
    """Estimate delay risk from live input features until MLlib scoring is deployed."""
    congestion = float(event.get("traffic_congestion_index") or 0)
    precipitation = float(event.get("precipitation_mm") or 0)
    peak_hour = int(event.get("peak_hour") or 0)
    weather = str(event.get("weather_condition") or "").lower()
    weather_penalty = 0.12 if weather in {"rain", "storm", "fog"} else 0.0
    probability = min(
        0.99,
        max(
            0.01,
            0.08
            + congestion / 180
            + min(precipitation / 100, 0.12)
            + peak_hour * 0.14
            + weather_penalty,
        ),
    )
    return {
        "predicted_delayed": int(probability >= 0.5),
        "delay_probability": round(probability * 100, 1),
        "predicted_delay_min": round(max(0.0, probability * 22 - 2), 1),
        "prediction_source": "Live feature risk estimate",
    }


def dashboard_data(request):
    """Return MySQL sink data when available, otherwise a truthful demo preview."""
    event = new_preview_event()
    events = [event]
    live_events = events
    source = "Generator preview"
    try:
        events = fetch_recent_events(limit=100)
        if events:
            source = "MySQL operational store"
            live_events = fetch_recent_events(limit=1000)
    except DatabaseError:
        # The page remains available while MySQL/Connect is being started.
        pass

    if not events:
        events = [event]

    for event in events:
        event.update(predict_event_risk(event))

    summary = build_summary_from_events(events)
    if source != "Generator preview":
        summary = apply_database_totals(summary)
    summary["active_trips"] = summary["total_trips"] if source != "Generator preview" else len(live_events)
    summary["predicted_delayed_trips"] = sum(int(item["predicted_delayed"]) for item in events)

    return JsonResponse(
        {
            "source": source,
            "events": events,
            "summary": summary,
        }
    )


@api_view(["GET", "POST"])
def generate_random_trip_events(request):
    """Generate random trip events and store them in MySQL."""
    payload = request.data if hasattr(request, "data") and request.data else {}
    count = payload.get("count", request.GET.get("count", 12))

    try:
        count = int(count)
    except (TypeError, ValueError):
        return Response({"detail": "count must be an integer from 1 to 500."}, status=status.HTTP_400_BAD_REQUEST)

    if not 1 <= count <= 500:
        return Response({"detail": "count must be an integer from 1 to 500."}, status=status.HTTP_400_BAD_REQUEST)

    if not database_has_events():
        seeded = seed_database_from_csv(count=max(50, count))
    else:
        seeded = 0

    generator = TripEventGenerator(PROJECT_ROOT / "rwanda_public_transport_delays.csv")
    events = [generator.next_event() for _ in range(count)]
    keep_delay_rate_in_range(events)

    try:
        database_inserted = store_events_in_mysql(events)
    except DatabaseError as error:
        return Response({"detail": f"MySQL insert failed: {error}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(
        {
            "generated": len(events),
            "seeded_from_csv": seeded,
            "database_inserted": database_inserted,
            "message": "CSV-backed data was used as the starting base, then new random trip events were generated and saved to the database.",
        },
        status=status.HTTP_201_CREATED,
    )


def database_summary_page(request):
    """Render the database summary page."""
    return render(request, "operations/summary.html")


def apply_database_totals(summary: dict[str, object]) -> dict[str, object]:
    """Replace recent-window totals with aggregates calculated across the full table."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*), COALESCE(SUM(`delayed`), 0) FROM transport_trip_events"
        )
        total_trips, delayed_trips = cursor.fetchone()
        cursor.execute(
            """
            SELECT route_id, COUNT(*) AS route_total
            FROM transport_trip_events
            GROUP BY route_id
            ORDER BY route_total DESC
            LIMIT 1
            """
        )
        top_route = cursor.fetchone()
        cursor.execute(
            """
            SELECT transport_type, COUNT(*) AS transport_total
            FROM transport_trip_events
            GROUP BY transport_type
            ORDER BY transport_type
            """
        )
        transport_means = {
            str(transport_type or "Unknown"): int(transport_total)
            for transport_type, transport_total in cursor.fetchall()
        }

    summary["total_trips"] = int(total_trips)
    summary["delayed_trips"] = int(delayed_trips)
    summary["delay_rate"] = round((int(delayed_trips) / int(total_trips)) * 100, 1) if total_trips else 0
    summary["top_route"] = top_route[0] if top_route else "-"
    summary["transport_counts"] = transport_means
    summary["transport_means"] = transport_means
    return summary


@api_view(["GET"])
def database_summary_data(request):
    """Return summary metrics computed from the database records."""
    try:
        events = fetch_recent_events(limit=500)
    except DatabaseError:
        return JsonResponse({"source": "Unavailable", "events": [], "summary": build_summary_from_events([])})

    if not events:
        return JsonResponse({"source": "No data in database", "events": [], "summary": build_summary_from_events([])})

    for event in events:
        event.update(predict_event_risk(event))

    summary = build_summary_from_events(events)
    summary = apply_database_totals(summary)
    summary["active_trips"] = len(events)
    summary["predicted_delayed_trips"] = sum(int(item["predicted_delayed"]) for item in events)
    summary["source"] = "MySQL operational store"
    return JsonResponse({"source": "MySQL operational store", "events": events, "summary": summary})


@api_view(["POST"])
def publish_trip_events(request):
    """Generate one or more trips and publish them to the Kafka topic.

    A keyed record is sent without an explicit partition. Kafka's partitioner
    deterministically selects a partition from route_id, preserving per-route
    order while distributing independent routes across partitions.
    """
    count = request.data.get("count", 1)
    if not isinstance(count, int) or not 1 <= count <= 1_000:
        return Response(
            {"detail": "count must be an integer from 1 to 1000."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    generator = TripEventGenerator(PROJECT_ROOT / "rwanda_public_transport_delays.csv")
    events = [generator.next_event() for _ in range(count)]
    try:
        database_inserted = store_events_in_mysql(events)
    except DatabaseError as error:
        return Response(
            {"detail": f"MySQL insert failed: {error}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        publisher = TripKafkaPublisher(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            topic=settings.KAFKA_TRIP_TOPIC,
        )
        delivery_reports = publisher.publish_many(events)
    except KafkaPublishError as error:
        return Response(
            {
                "detail": str(error),
                "topic": settings.KAFKA_TRIP_TOPIC,
                "database_inserted": database_inserted,
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(
        {
            "published": len(delivery_reports),
            "database_inserted": database_inserted,
            "topic": settings.KAFKA_TRIP_TOPIC,
            "deliveries": delivery_reports,
        },
        status=status.HTTP_201_CREATED,
    )
