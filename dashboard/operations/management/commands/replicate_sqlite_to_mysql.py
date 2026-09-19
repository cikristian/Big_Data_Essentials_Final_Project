import sqlite3
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from operations.views import (
    GMT_PLUS_2,
    MYSQL_EVENT_COLUMNS, PROJECT_ROOT, store_events_in_mysql,
)


class Command(BaseCommand):
    help = "Replicate existing SQLite transport events into the configured MySQL database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=Path,
            default=PROJECT_ROOT / "dashboard" / "db.sqlite3",
            help="SQLite database path (default: dashboard/db.sqlite3).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Number of rows copied per MySQL batch (default: 500).",
        )

    def handle(self, *args, **options):
        if connection.vendor != "mysql":
            raise CommandError(
            "Django is not configured for MySQL. Set MYSQL_* variables or create a project .env first."
            )

        source = options["source"]
        batch_size = options["batch_size"]
        if batch_size < 1:
            raise CommandError("--batch-size must be greater than zero.")
        if not source.is_file():
            raise CommandError(f"SQLite database was not found: {source}")

        with sqlite3.connect(source) as sqlite_database:
            sqlite_database.row_factory = sqlite3.Row
            try:
                rows = sqlite_database.execute(
                    f"SELECT {', '.join(MYSQL_EVENT_COLUMNS)} "
                    "FROM transport_trip_events ORDER BY event_generated_at, trip_id"
                )
            except sqlite3.Error as error:
                raise CommandError(f"Could not read SQLite transport events: {error}") from error

            total = 0
            batch = []
            for row in rows:
                event = dict(row)
                timestamp = datetime.fromisoformat(str(event["event_generated_at"]))
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=GMT_PLUS_2)
                event["event_generated_at"] = timestamp.isoformat(timespec="seconds")
                batch.append(event)

                if len(batch) >= batch_size:
                    total += store_events_in_mysql(batch)
                    batch.clear()

            if batch:
                total += store_events_in_mysql(batch)

        self.stdout.write(
            self.style.SUCCESS(
                f"Replicated {total} SQLite transport events into MySQL."
            )
        )