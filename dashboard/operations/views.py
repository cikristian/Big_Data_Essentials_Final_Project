import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.db import DatabaseError, connection
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


def store_events_in_mysql(events: list[dict]) -> int:
    """Persist generated events directly for dashboard queries and replay."""
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
    rows = []
    for event in events:
        values = dict(event)
        generated_at = datetime.fromisoformat(values["event_generated_at"])
        values["event_generated_at"] = generated_at.astimezone(timezone.utc).replace(tzinfo=None)
        rows.append(tuple(values.get(column) for column in MYSQL_EVENT_COLUMNS))
    with connection.cursor() as cursor:
        cursor.execute(create_table)
        cursor.executemany(
            f"INSERT INTO transport_trip_events ({quoted_columns}) VALUES ({placeholders}) "
            "ON DUPLICATE KEY UPDATE event_generated_at = VALUES(event_generated_at)",
            rows,
        )
    return len(rows)


def dashboard(request):
    return render(request, "operations/dashboard.html")


def preview_event(request):
    return JsonResponse(new_preview_event())


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
    source = "Generator preview"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE %s", ["transport_trip_events"])
            if cursor.fetchone():
                cursor.execute(
                          """SELECT trip_id, route_id, transport_type, origin_district,
                              destination_district, origin_latitude, origin_longitude,
                              actual_arrival_delay_min, traffic_congestion_index,
                              precipitation_mm, weather_condition, peak_hour, `delayed`
                       FROM transport_trip_events
                       ORDER BY event_generated_at DESC LIMIT 100"""
                )
                names = [column[0] for column in cursor.description]
                events = [dict(zip(names, row)) for row in cursor.fetchall()]
                if events:
                    source = "MySQL operational store"
    except DatabaseError:
        # The page remains available while MySQL/Connect is being started.
        pass

    for event in events:
        event.update(predict_event_risk(event))

    delayed_count = sum(int(item.get("delayed", 0)) for item in events)
    predicted_count = sum(int(item["predicted_delayed"]) for item in events)
    route_counts = Counter(item.get("route_id", "Unknown") for item in events)
    transport_counts = Counter(item.get("transport_type", "Unknown") for item in events)
    highest_risk = max(events, key=lambda item: item["delay_probability"], default={})
    return JsonResponse(
        {
            "source": source,
            "events": events,
            "summary": {
                "active_trips": len(events),
                "delayed_trips": delayed_count,
                "delay_rate": round((delayed_count / len(events)) * 100, 1),
                "predicted_delayed_trips": predicted_count,
                "top_route": route_counts.most_common(1)[0][0] if events else "-",
                "transport_counts": dict(transport_counts),
                "highest_risk_route": highest_risk.get("route_id", "-"),
                "highest_risk_probability": highest_risk.get("delay_probability", 0),
            },
        }
    )


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
