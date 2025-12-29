"""Configuration for Graph Service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Graph Service settings."""

    service_name: str = "graph-service"
    version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    postgres_dsn: str = "postgresql+asyncpg://oncology:oncology_secret@postgres:5432/oncology_xai"

    # Redis (for Celery)
    redis_url: str = "redis://redis:6379/0"

    # Fuseki SPARQL endpoint
    fuseki_url: str = "http://fuseki:3030"
    fuseki_dataset: str = "oncology"

    # Observability
    otel_exporter_otlp_endpoint: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
