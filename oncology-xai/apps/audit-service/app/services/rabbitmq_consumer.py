"""RabbitMQ consumer for audit events."""
import asyncio
import json
from typing import Optional
from aio_pika import connect_robust, Message, IncomingMessage
from aio_pika.abc import AbstractRobustConnection, AbstractRobustChannel, AbstractRobustQueue

from app.core.config import settings
from app.core.logger import logger
from app.db.session import AsyncSessionLocal
from app.schemas.audit_event import AuditEventCreate
from app.services.audit_service import AuditService


class RabbitMQConsumer:
    """RabbitMQ consumer for consuming audit events."""

    def __init__(self):
        """Initialize RabbitMQ consumer."""
        self.connection: Optional[AbstractRobustConnection] = None
        self.channel: Optional[AbstractRobustChannel] = None
        self.queue: Optional[AbstractRobustQueue] = None
        self.audit_service = AuditService()

    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        try:
            logger.info(f"Connecting to RabbitMQ at {settings.RABBITMQ_URL}")
            self.connection = await connect_robust(
                settings.RABBITMQ_URL,
                timeout=30
            )
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=settings.RABBITMQ_PREFETCH_COUNT)

            # Declare exchange
            exchange = await self.channel.declare_exchange(
                settings.RABBITMQ_EXCHANGE,
                type=settings.RABBITMQ_EXCHANGE_TYPE,
                durable=True
            )

            # Declare queue
            self.queue = await self.channel.declare_queue(
                settings.RABBITMQ_QUEUE,
                durable=True
            )

            # Bind queue to exchange
            await self.queue.bind(
                exchange=exchange,
                routing_key=settings.RABBITMQ_ROUTING_KEY
            )

            logger.info(
                f"Connected to RabbitMQ. Queue: {settings.RABBITMQ_QUEUE}, "
                f"Exchange: {settings.RABBITMQ_EXCHANGE}, "
                f"Routing Key: {settings.RABBITMQ_ROUTING_KEY}"
            )

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}", exc_info=True)
            raise

    async def process_message(self, message: IncomingMessage) -> None:
        """
        Process incoming audit event message.

        Args:
            message: Incoming RabbitMQ message
        """
        async with message.process():
            try:
                # Parse message body
                body = message.body.decode('utf-8')
                event_data = json.loads(body)

                logger.debug(f"Received event: {event_data.get('action', 'unknown')}")

                # Create audit event schema
                audit_event = AuditEventCreate(**event_data)

                # Store in database
                async with AsyncSessionLocal() as db:
                    await self.audit_service.create_audit_event(db, audit_event)

                logger.info(
                    f"Successfully processed audit event: {event_data.get('action', 'unknown')}",
                    extra={
                        "action": event_data.get("action"),
                        "entity_type": event_data.get("entity_type"),
                        "correlation_id": event_data.get("correlation_id")
                    }
                )

            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode message: {str(e)}", exc_info=True)
                # Message will be rejected and not requeued
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                # Message will be rejected and not requeued
                # In production, you might want to send to a dead letter queue

    async def start_consuming(self) -> None:
        """Start consuming messages from RabbitMQ."""
        if not self.queue:
            raise RuntimeError("Not connected to RabbitMQ. Call connect() first.")

        logger.info("Starting to consume audit events...")
        await self.queue.consume(self.process_message)

    async def close(self) -> None:
        """Close RabbitMQ connection."""
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {str(e)}", exc_info=True)


# Global consumer instance
rabbitmq_consumer = RabbitMQConsumer()


async def start_consumer() -> None:
    """Start the RabbitMQ consumer."""
    try:
        await rabbitmq_consumer.connect()
        await rabbitmq_consumer.start_consuming()
    except Exception as e:
        logger.error(f"Failed to start consumer: {str(e)}", exc_info=True)
        raise


async def stop_consumer() -> None:
    """Stop the RabbitMQ consumer."""
    await rabbitmq_consumer.close()
