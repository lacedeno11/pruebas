"""
DERCAS-ONCO-XAI V1 - Inference Service Configuration

Configuration management for the AI Inference Service.
"""

import os
from functools import lru_cache
from typing import Dict, List, Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Inference Service configuration settings."""
    
    # Service configuration
    service_name: str = Field(default="inference-service", description="Service name")
    service_version: str = Field(default="1.0.0", description="Service version")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8003, description="Server port")
    
    # Database configuration
    database_url: str = Field(
        default="postgresql+asyncpg://oncology_user:oncology_pass@localhost:5432/oncology_db",
        description="Database connection URL"
    )
    database_pool_size: int = Field(default=20, description="Database connection pool size")
    database_max_overflow: int = Field(default=30, description="Database max overflow connections")
    database_echo: bool = Field(default=False, description="Echo SQL queries")
    
    # Celery configuration
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL"
    )
    celery_task_routes: Dict[str, str] = Field(
        default={
            "inference.tasks.process_image": "inference_queue",
            "inference.tasks.generate_xai": "xai_queue",
            "inference.tasks.validate_results": "validation_queue"
        },
        description="Celery task routing"
    )
    
    # RabbitMQ configuration
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ connection URL"
    )
    
    # Model configuration
    model_backend: str = Field(
        default="mock",
        description="Model backend (mock, triton, torchserve)"
    )
    model_base_path: str = Field(
        default="/models",
        description="Base path for model files"
    )
    triton_server_url: str = Field(
        default="http://localhost:8000",
        description="Triton inference server URL"
    )
    torchserve_url: str = Field(
        default="http://localhost:8080",
        description="TorchServe URL"
    )
    
    # Pattern recognition models
    pattern_models: Dict[str, str] = Field(
        default={
            "lepidic": "pattern_lepidic_v1.0",
            "acinar": "pattern_acinar_v1.0", 
            "papillary": "pattern_papillary_v1.0",
            "micropapillary": "pattern_micropapillary_v1.0",
            "solid": "pattern_solid_v1.0"
        },
        description="Pattern recognition model mapping"
    )
    
    # Genetic mutation models
    mutation_models: Dict[str, str] = Field(
        default={
            "EGFR": "mutation_egfr_v1.0",
            "KRAS": "mutation_kras_v1.0",
            "TP53": "mutation_tp53_v1.0"
        },
        description="Genetic mutation model mapping"
    )
    
    # XAI configuration
    xai_methods: List[str] = Field(
        default=["gradcam", "lime", "shap", "attention"],
        description="Available XAI methods"
    )
    generate_xai_artifacts: bool = Field(
        default=True,
        description="Generate XAI artifacts (heatmaps, attention maps)"
    )
    xai_artifact_formats: List[str] = Field(
        default=["png", "json"],
        description="XAI artifact output formats"
    )
    
    # Clinical guardrails configuration
    confidence_thresholds: Dict[str, float] = Field(
        default={
            "pattern_high": 0.85,
            "pattern_medium": 0.70,
            "pattern_low": 0.50,
            "mutation_high": 0.90,
            "mutation_medium": 0.75,
            "mutation_low": 0.60
        },
        description="Confidence thresholds for clinical decisions"
    )
    
    # HITL (Human-in-the-Loop) configuration
    hitl_enabled: bool = Field(default=True, description="Enable HITL policies")
    hitl_confidence_threshold: float = Field(
        default=0.70,
        description="Confidence threshold for HITL intervention"
    )
    hitl_conflict_threshold: float = Field(
        default=0.15,
        description="Threshold for conflicting predictions requiring HITL"
    )
    require_hitl_for_mutations: bool = Field(
        default=True,
        description="Always require HITL review for mutation predictions"
    )
    
    # Processing configuration
    max_concurrent_jobs: int = Field(
        default=10,
        description="Maximum concurrent processing jobs"
    )
    job_timeout_seconds: int = Field(
        default=1800,  # 30 minutes
        description="Job timeout in seconds"
    )
    retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts for failed jobs"
    )
    
    # Image processing configuration
    supported_formats: List[str] = Field(
        default=["png", "tiff", "tif"],
        description="Supported image formats"
    )
    max_image_size_mb: int = Field(
        default=500,
        description="Maximum image size in MB"
    )
    preprocessing_steps: List[str] = Field(
        default=["normalize", "resize", "augment"],
        description="Image preprocessing steps"
    )
    
    # Storage configuration for results
    result_storage_path: str = Field(
        default="inference_results",
        description="Storage path for inference results"
    )
    artifact_storage_path: str = Field(
        default="xai_artifacts",
        description="Storage path for XAI artifacts"
    )
    result_retention_days: int = Field(
        default=365,
        description="Result retention period in days"
    )
    
    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s",
        description="Log format"
    )
    
    # Performance monitoring
    enable_metrics: bool = Field(default=True, description="Enable performance metrics")
    metrics_port: int = Field(default=9090, description="Metrics server port")
    
    # Mock model configuration (for development)
    mock_processing_delay: float = Field(
        default=2.0,
        description="Mock processing delay in seconds"
    )
    mock_confidence_range: tuple = Field(
        default=(0.60, 0.95),
        description="Mock confidence score range"
    )
    mock_failure_rate: float = Field(
        default=0.05,
        description="Mock failure rate for testing"
    )
    
    class Config:
        env_file = ".env"
        env_prefix = "INFERENCE_SERVICE_"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_database_url() -> str:
    """Get database connection URL."""
    return get_settings().database_url


def get_celery_config() -> dict:
    """Get Celery configuration."""
    settings = get_settings()
    return {
        "broker_url": settings.celery_broker_url,
        "result_backend": settings.celery_result_backend,
        "task_routes": settings.celery_task_routes,
        "task_serializer": "json",
        "accept_content": ["json"],
        "result_serializer": "json",
        "timezone": "UTC",
        "enable_utc": True,
        "task_track_started": True,
        "task_time_limit": settings.job_timeout_seconds,
        "task_soft_time_limit": settings.job_timeout_seconds - 60,
        "worker_prefetch_multiplier": 1,
        "task_acks_late": True,
        "worker_disable_rate_limits": False,
        "task_compression": "gzip",
        "result_compression": "gzip"
    }


def get_model_config() -> dict:
    """Get model configuration."""
    settings = get_settings()
    return {
        "backend": settings.model_backend,
        "base_path": settings.model_base_path,
        "triton_url": settings.triton_server_url,
        "torchserve_url": settings.torchserve_url,
        "pattern_models": settings.pattern_models,
        "mutation_models": settings.mutation_models
    }


def get_clinical_guardrails() -> dict:
    """Get clinical guardrails configuration."""
    settings = get_settings()
    return {
        "confidence_thresholds": settings.confidence_thresholds,
        "hitl_enabled": settings.hitl_enabled,
        "hitl_confidence_threshold": settings.hitl_confidence_threshold,
        "hitl_conflict_threshold": settings.hitl_conflict_threshold,
        "require_hitl_for_mutations": settings.require_hitl_for_mutations
    }


def get_xai_config() -> dict:
    """Get XAI configuration."""
    settings = get_settings()
    return {
        "methods": settings.xai_methods,
        "generate_artifacts": settings.generate_xai_artifacts,
        "artifact_formats": settings.xai_artifact_formats,
        "storage_path": settings.artifact_storage_path
    }


def is_development() -> bool:
    """Check if running in development mode."""
    return get_settings().debug


def is_mock_mode() -> bool:
    """Check if running in mock mode."""
    return get_settings().model_backend == "mock"


def get_supported_patterns() -> List[str]:
    """Get list of supported histological patterns."""
    return list(get_settings().pattern_models.keys())


def get_supported_mutations() -> List[str]:
    """Get list of supported genetic mutations."""
    return list(get_settings().mutation_models.keys())
