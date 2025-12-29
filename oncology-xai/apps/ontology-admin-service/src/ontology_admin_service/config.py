"""Configuration for Ontology Admin Service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Ontology Admin Service settings."""

    service_name: str = "ontology-admin-service"
    version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    postgres_dsn: str = "postgresql+asyncpg://oncology:oncology_secret@postgres:5432/oncology_xai"

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"

    # Redis (for Celery)
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    # Reasoner configuration
    reasoner_backend: str = "mock"  # mock, owlrl

    # Whitelisted ontology sources
    allowed_ontology_sources: list[str] = ["NCIt", "MONDO", "SO"]

    # Observability
    otel_exporter_otlp_endpoint: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
