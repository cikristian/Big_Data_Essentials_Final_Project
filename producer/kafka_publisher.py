"""Reliable, route-keyed publishing of trip events to Apache Kafka."""

from __future__ import annotations

import json
from collections.abc import Iterable

from confluent_kafka import KafkaException, Producer


class KafkaPublishError(RuntimeError):
    """The REST endpoint can return this error when Kafka does not acknowledge."""


class TripKafkaPublisher:
    """Publish trip events with per-route ordering and broker acknowledgements."""

    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        self.topic = topic
        self.producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers,
                "client.id": "kigali-django-producer",
                "acks": "all",
                "enable.idempotence": True,
                "compression.type": "lz4",
                # Match Java Kafka's keyed partitioner for cross-client consistency.
                "partitioner": "murmur2_random",
            }
        )

    def publish_many(self, events: Iterable[dict]) -> list[dict[str, int]]:
        deliveries: list[dict[str, int]] = []
        failures: list[str] = []

        def delivery_callback(error, message) -> None:
            if error is not None:
                failures.append(str(error))
                return
            deliveries.append(
                {"partition": message.partition(), "offset": message.offset()}
            )

        try:
            for event in events:
                self.producer.produce(
                    self.topic,
                    key=event["route_id"].encode("utf-8"),
                    value=json.dumps(event, separators=(",", ":")).encode("utf-8"),
                    on_delivery=delivery_callback,
                )
                self.producer.poll(0)
            outstanding = self.producer.flush(10)
        except (KafkaException, BufferError) as error:
            raise KafkaPublishError(f"Kafka publish failed: {error}") from error

        if outstanding or failures:
            details = "; ".join(failures) or "Kafka delivery timed out"
            raise KafkaPublishError(details)
        return deliveries
