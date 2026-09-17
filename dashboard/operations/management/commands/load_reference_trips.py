from pathlib import Path

from django.core.management.base import BaseCommand

from operations.views import PROJECT_ROOT, TripEventGenerator, store_events_in_mysql


class Command(BaseCommand):
    help = "Load CSV-derived trip events into the configured MySQL database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=1000,
            help="Number of generated events to insert (default: 1000).",
        )

    def handle(self, *args, **options):
        count = options["count"]
        if count < 1:
            raise ValueError("--count must be greater than zero")

        generator = TripEventGenerator(
            Path(PROJECT_ROOT) / "rwanda_public_transport_delays.csv"
        )
        events = [generator.next_event() for _ in range(count)]
        inserted = store_events_in_mysql(events)
        self.stdout.write(
            self.style.SUCCESS(
                f"Inserted {inserted} CSV-derived events into MySQL database."
            )
        )
