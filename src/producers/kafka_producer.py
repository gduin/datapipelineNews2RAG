"""Kafka producer wrapper using confluent-kafka (idempotent, transactional-ready)."""
from __future__ import annotations

from confluent_kafka import Producer

from src.common.logging import get_logger

logger = get_logger(__name__)


class NewsKafkaProducer:
    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        self._topic = topic
        self._producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers,
                "enable.idempotence": True,
                "acks": "all",
                "compression.type": "zstd",
                "linger.ms": 50,
                "batch.size": 131072,
                "max.in.flight.requests.per.connection": 5,
            }
        )

    async def start(self) -> None:
        logger.info("kafka_producer_started", topic=self._topic)

    async def send(self, value: bytes, key: bytes | None = None) -> None:
        self._producer.produce(self._topic, value=value, key=key, callback=self._on_delivery)
        self._producer.poll(0)

    def _on_delivery(self, err, msg) -> None:  # noqa: ANN001
        if err:
            logger.error("delivery_failed", error=str(err))
        else:
            logger.debug("delivered", partition=msg.partition(), offset=msg.offset())

    async def stop(self) -> None:
        self._producer.flush(30)
        logger.info("kafka_producer_stopped")
