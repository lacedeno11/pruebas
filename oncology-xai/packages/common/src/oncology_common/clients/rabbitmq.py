"""RabbitMQ client for event publishing."""

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pika
from pika.adapters.blocking_connection import BlockingChannel

from oncology_common.middleware.correlation import get_correlation_id


class RabbitMQClient:
    """RabbitMQ connection management."""

    def __init__(self, url: str):
        self.url = url
        self._connection: pika.BlockingConnection | None = None
        self._channel: BlockingChannel | None = None

    def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        parameters = pika.URLParameters(self.url)
        self._connection = pika.BlockingConnection(parameters)
        self._channel = self._connection.channel()

    def close(self) -> None:
        """Close connection."""
        if self._channel:
            self._channel.close()
        if self._connection:
            self._connection.close()

    @property
    def channel(self) -> BlockingChannel:
        """Get or create channel."""
        if not self._channel or self._channel.is_closed:
            self.connect()
        return self._channel  # type: ignore

    def declare_exchange(
        self,
        exchange: str,
        exchange_type: str = "topic",
        durable: bool = True,
    ) -> None:
        """Declare an exchange."""
        self.channel.exchange_declare(
            exchange=exchange,
            exchange_type=exchange_type,
            durable=durable,
        )

    def declare_queue(
        self,
        queue: str,
        durable: bool = True,
        arguments: dict | None = None,
    ) -> None:
        """Declare a queue."""
        self.channel.queue_declare(
            queue=queue,
            durable=durable,
            arguments=arguments,
        )

    def bind_queue(self, queue: str, exchange: str, routing_key: str) -> None:
        """Bind a queue to an exchange."""
        self.channel.queue_bind(
            queue=queue,
            exchange=exchange,
            routing_key=routing_key,
        )

    def publish(
        self,
        exchange: str,
        routing_key: str,
        message: dict | str,
        headers: dict | None = None,
    ) -> None:
        """Publish a message to an exchange."""
        if isinstance(message, dict):
            body = json.dumps(message, default=str)
        else:
            body = message

        properties = pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,  # Persistent
            headers=headers or {},
        )

        self.channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=body.encode(),
            properties=properties,
        )


class EventPublisher:
    """High-level event publisher with envelope wrapping."""

    EXCHANGE = "oncology.events"

    def __init__(self, rabbitmq_client: RabbitMQClient, producer: str):
        self.client = rabbitmq_client
        self.producer = producer
        self._setup_exchange()

    def _setup_exchange(self) -> None:
        """Setup the events exchange."""
        self.client.declare_exchange(self.EXCHANGE, "topic")

    def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
        case_id: str | None = None,
        routing_key: str | None = None,
    ) -> str:
        """Publish an event with standard envelope."""
        event_id = f"evt_{uuid4().hex[:16]}"
        correlation_id = get_correlation_id() or f"corr_{uuid4().hex[:16]}"

        envelope = {
            "eventId": event_id,
            "eventType": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlationId": correlation_id,
            "producer": self.producer,
            "caseId": case_id,
            "payload": payload,
        }

        # Use event type as routing key if not specified
        if not routing_key:
            routing_key = event_type.replace(".", "_")

        self.client.publish(
            exchange=self.EXCHANGE,
            routing_key=routing_key,
            message=envelope,
            headers={
                "event_type": event_type,
                "correlation_id": correlation_id,
            },
        )

        return event_id


def create_event_publisher(rabbitmq_url: str, producer: str) -> EventPublisher:
    """Create an event publisher."""
    client = RabbitMQClient(rabbitmq_url)
    client.connect()
    return EventPublisher(client, producer)
