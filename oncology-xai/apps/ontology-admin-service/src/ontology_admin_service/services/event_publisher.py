"""Event publisher for RabbitMQ events."""

import json
import logging
from typing import Any
from datetime import datetime
from uuid import UUID

import pika

from ontology_admin_service.config import settings

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publisher for ontology events to RabbitMQ."""

    def __init__(self):
        """Initialize event publisher."""
        self.connection = None
        self.channel = None

    def connect(self):
        """Connect to RabbitMQ."""
        if self.connection and self.connection.is_open:
            return

        try:
            parameters = pika.URLParameters(settings.rabbitmq_url)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # Declare exchange
            self.channel.exchange_declare(
                exchange="ontology.events",
                exchange_type="topic",
                durable=True,
            )

            logger.info("Connected to RabbitMQ for event publishing")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    def close(self):
        """Close RabbitMQ connection."""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("Closed RabbitMQ connection")

    def publish_event(self, routing_key: str, event_data: dict[str, Any]):
        """Publish event to RabbitMQ."""
        try:
            self.connect()

            # Add metadata
            event = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": routing_key,
                **event_data,
            }

            self.channel.basic_publish(
                exchange="ontology.events",
                routing_key=routing_key,
                body=json.dumps(event, default=str),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type="application/json",
                ),
            )

            logger.info(f"Published event: {routing_key}")
        except Exception as e:
            logger.error(f"Failed to publish event {routing_key}: {e}")
            raise

    def publish_ontology_published(
        self,
        version_id: UUID,
        source: str,
        version_tag: str,
    ):
        """Publish ontology published event."""
        self.publish_event(
            "ontology.published",
            {
                "version_id": str(version_id),
                "ontology_source": source,
                "version_tag": version_tag,
            },
        )

    def publish_ontology_rolled_back(
        self,
        from_version_id: UUID,
        to_version_id: UUID,
        source: str,
    ):
        """Publish ontology rollback event."""
        self.publish_event(
            "ontology.rolled_back",
            {
                "from_version_id": str(from_version_id),
                "to_version_id": str(to_version_id),
                "ontology_source": source,
            },
        )

    def publish_proposal_created(self, proposal_id: UUID, sources: list[str]):
        """Publish proposal created event."""
        self.publish_event(
            "ontology.proposal.created",
            {
                "proposal_id": str(proposal_id),
                "ontology_sources": sources,
            },
        )

    def publish_proposal_validated(
        self,
        proposal_id: UUID,
        status: str,
        has_errors: bool,
    ):
        """Publish proposal validation completed event."""
        self.publish_event(
            "ontology.proposal.validated",
            {
                "proposal_id": str(proposal_id),
                "status": status,
                "has_errors": has_errors,
            },
        )


# Global event publisher instance
event_publisher = EventPublisher()
