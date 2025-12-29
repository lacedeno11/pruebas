"""Configuration for EHR Service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """EHR Service settings."""

    service_name: str = "ehr-service"
    version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    postgres_dsn: str = "postgresql+asyncpg://oncology:oncology_secret@postgres:5432/oncology_xai"

    # Redis for Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    # RabbitMQ for events
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"

    # LLM Configuration
    llm_provider: str = "mock"  # mock, openai, anthropic
    openai_api_key: str | None = None

    # Observability
    otel_exporter_otlp_endpoint: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
