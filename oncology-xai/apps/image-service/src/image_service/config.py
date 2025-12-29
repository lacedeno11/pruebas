"""Configuration for Image Service."""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "image-service"
    version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"
    postgres_dsn: str = "postgresql+asyncpg://oncology:oncology_secret@postgres:5432/oncology_xai"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "oncology-xai"
    max_file_size: int = 500 * 1024 * 1024  # 500MB
    otel_exporter_otlp_endpoint: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
