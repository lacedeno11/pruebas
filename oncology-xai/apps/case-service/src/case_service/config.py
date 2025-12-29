"""Configuration for Case Service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Case Service settings."""

    service_name: str = "case-service"
    version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    postgres_dsn: str = "postgresql+asyncpg://oncology:oncology_secret@postgres:5432/oncology_xai"

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"

    # Observability
    otel_exporter_otlp_endpoint: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
