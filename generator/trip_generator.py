"""Generate Kigali transport trip events from the reference CSV distribution.

The program writes one JSON object per line (NDJSON), which is convenient for
Kafka producers, Kafka Connect, and command-line inspection.  It deliberately
uses only Python's standard library so it runs cleanly on native Windows.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, TextIO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = PROJECT_ROOT / "rwanda_public_transport_delays.csv"
GMT_PLUS_2 = timezone(timedelta(hours=2), name="GMT+2")
INTEGER_FIELDS = {
    "fare_rwf", "passengers_carried", "actual_departure_delay_min",
    "actual_arrival_delay_min", "event_attendance_est", "traffic_congestion_index",
    "holiday", "peak_hour", "weekday", "delayed",
}
FLOAT_FIELDS = {
    "origin_latitude", "origin_longitude", "destination_latitude",
    "destination_longitude", "distance_km", "temperature_C", "humidity_percent",
    "wind_speed_kmh", "precipitation_mm",
}


def parse_clock(value: str) -> datetime:
    """Parse a source time value into a datetime whose date is irrelevant."""
    return datetime.strptime(value, "%H:%M:%S")


def duration_minutes(start: str, end: str) -> int:
    """Return scheduled trip duration, handling the unlikely midnight rollover."""
    start_time = parse_clock(start)
    end_time = parse_clock(end)
    if end_time < start_time:
        end_time += timedelta(days=1)
    return int((end_time - start_time).total_seconds() // 60)


class TripEventGenerator:
    """Samples seed records and converts them into newly occurring trip events."""

    def __init__(self, csv_path: Path, random_seed: int | None = None) -> None:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            self.seed_rows = list(csv.DictReader(file))
        if not self.seed_rows:
            raise ValueError(f"The seed CSV contains no records: {csv_path}")

        self.random = random.Random(random_seed)
        self.sequence = 0

    def next_event(self, event_time: datetime | None = None) -> dict[str, Any]:
        """Build one event while retaining a sampled record's data relationships."""
        source = self.random.choice(self.seed_rows).copy()
        event_time = event_time or datetime.now(GMT_PLUS_2)
        scheduled_duration = duration_minutes(
            source["scheduled_departure"], source["scheduled_arrival"]
        )
        scheduled_departure = event_time.replace(microsecond=0)
        scheduled_arrival = scheduled_departure + timedelta(minutes=scheduled_duration)

        self.sequence += 1
        source["trip_id"] = (
            f"SIM-{scheduled_departure.strftime('%Y%m%d%H%M%S')}-"
            f"{uuid.uuid4().hex[:12]}"
        )
        source["date"] = scheduled_departure.strftime("%Y-%m-%d")
        source["time"] = scheduled_departure.strftime("%H:%M:%S")
        source["scheduled_departure"] = scheduled_departure.strftime("%H:%M:%S")
        source["scheduled_arrival"] = scheduled_arrival.strftime("%H:%M:%S")
        source["event_generated_at"] = event_time.isoformat(timespec="seconds")
        # csv.DictReader returns strings. Kafka JSON should retain numeric types so
        # Spark can aggregate them and MySQL Connect can map numeric columns.
        for field in INTEGER_FIELDS:
            source[field] = int(source[field])
        for field in FLOAT_FIELDS:
            source[field] = float(source[field])
        return source

    def events(self) -> Iterator[dict[str, Any]]:
        while True:
            yield self.next_event()


def write_events(
    generator: TripEventGenerator,
    destination: TextIO,
    records_per_second: float,
    count: int | None,
) -> None:
    """Write at a target average rate, compensating for serialization time."""
    interval = 1 / records_per_second
    next_deadline = time.monotonic()

    for index, event in enumerate(generator.events(), start=1):
        destination.write(json.dumps(event, separators=(",", ":")) + "\n")
        destination.flush()
        if count is not None and index >= count:
            return

        next_deadline += interval
        remaining = next_deadline - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)
        else:
            # Do not let a slow destination create an ever-growing timing debt.
            next_deadline = time.monotonic()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Seed CSV path")
    parser.add_argument("--rate", type=float, default=5.0, help="Records per second (default: 5)")
    parser.add_argument("--count", type=int, help="Stop after this many records")
    parser.add_argument("--seed", type=int, help="Optional seed for reproducible sampling")
    parser.add_argument(
        "--output", type=Path, help="NDJSON output file; omit to write to standard output"
    )
    parsed = parser.parse_args()
    if parsed.rate <= 0:
        parser.error("--rate must be greater than zero")
    if parsed.count is not None and parsed.count <= 0:
        parser.error("--count must be greater than zero")
    if not parsed.csv.is_file():
        parser.error(f"Seed CSV was not found: {parsed.csv}")
    return parsed


def main() -> None:
    options = arguments()
    event_generator = TripEventGenerator(options.csv, options.seed)
    if options.output:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        with options.output.open("w", encoding="utf-8", newline="") as destination:
            write_events(event_generator, destination, options.rate, options.count)
    else:
        write_events(event_generator, sys.stdout, options.rate, options.count)


if __name__ == "__main__":
    main()
