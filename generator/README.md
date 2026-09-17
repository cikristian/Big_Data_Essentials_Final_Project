# Trip-event generator

This component produces newline-delimited JSON (NDJSON) trip events using
`rwanda_public_transport_delays.csv` as its empirical seed distribution.
Sampling a whole source row preserves useful correlations such as route,
district, weather, congestion, and observed delay. The generator then assigns a
new trip ID and current schedule timestamps, making the output appropriate for
a live Kafka topic.

Run from the project root:

```powershell
.\.venv\Scripts\python.exe .\generator\trip_generator.py --rate 5 --count 10
```

To persist a reproducible test stream:

```powershell
.\.venv\Scripts\python.exe .\generator\trip_generator.py --rate 20 --count 100 --seed 42 --output .\data\sample_events.ndjson
```

`--rate` controls the target records per second. Omit `--count` to run until
you stop it with `Ctrl+C`. The later Django REST producer will import
`TripEventGenerator` rather than duplicate its event logic.
