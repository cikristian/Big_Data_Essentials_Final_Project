# Django REST Kafka producer

The endpoint `POST /api/trips/publish/` generates trip events and publishes
them to `kigali-trip-events` (or `KAFKA_TRIP_TOPIC`). The Kafka key is
`route_id`. Kafka hashes that key to choose a partition, so records for a route
remain ordered while different routes can be processed in parallel.

Example after Kafka is running:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/trips/publish/ -ContentType "application/json" -Body '{"count": 10}'
```

The producer waits for broker delivery acknowledgement before returning HTTP
201. It uses `acks=all` and idempotence, preventing duplicate log writes from
producer retries. This does not make the whole pipeline exactly-once: the
custom consumer will intentionally use manual commits for at-least-once
processing, which is easier to observe and defend in this project.
