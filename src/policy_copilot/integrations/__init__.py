"""
Policy Copilot Integrations Package

This package contains integration layer components for external services:
- CRM/Ticketing webhook handlers for case ingestion and status updates
- Object storage interface for document and attachment management
- Knowledge base interface for policy document retrieval and vector search
- Notification service for alerts, updates, and communication
- Queue management for asynchronous processing and task distribution
- Health checks for all external services and dependencies
"""

from .crm_webhooks import (
    CRMWebhookHandler,
    TicketingWebhookHandler,
    WebhookProcessor,
    create_crm_webhook_handler,
    create_ticketing_webhook_handler
)

from .object_storage import (
    ObjectStorageInterface,
    S3StorageAdapter,
    LocalStorageAdapter,
    StorageConfig,
    create_object_storage
)

from .knowledge_base import (
    KnowledgeBaseInterface,
    ChromaDBAdapter,
    PineconeAdapter,
    VectorSearchConfig,
    create_knowledge_base
)

from .notification_service import (
    NotificationService,
    EmailNotificationAdapter,
    SlackNotificationAdapter,
    SMSNotificationAdapter,
    NotificationConfig,
    create_notification_service
)

from .queue_management import (
    QueueManager,
    RedisQueueAdapter,
    RabbitMQAdapter,
    QueueConfig,
    create_queue_manager
)

from .health_checks import (
    HealthCheckManager,
    ServiceHealthCheck,
    HealthStatus,
    create_health_check_manager
)

__all__ = [
    # CRM/Ticketing webhooks
    "CRMWebhookHandler",
    "TicketingWebhookHandler", 
    "WebhookProcessor",
    "create_crm_webhook_handler",
    "create_ticketing_webhook_handler",
    
    # Object storage
    "ObjectStorageInterface",
    "S3StorageAdapter",
    "LocalStorageAdapter",
    "StorageConfig",
    "create_object_storage",
    
    # Knowledge base
    "KnowledgeBaseInterface",
    "ChromaDBAdapter",
    "PineconeAdapter",
    "VectorSearchConfig",
    "create_knowledge_base",
    
    # Notification service
    "NotificationService",
    "EmailNotificationAdapter",
    "SlackNotificationAdapter",
    "SMSNotificationAdapter",
    "NotificationConfig",
    "create_notification_service",
    
    # Queue management
    "QueueManager",
    "RedisQueueAdapter",
    "RabbitMQAdapter",
    "QueueConfig",
    "create_queue_manager",
    
    # Health checks
    "HealthCheckManager",
    "ServiceHealthCheck",
    "HealthStatus",
    "create_health_check_manager"
]

