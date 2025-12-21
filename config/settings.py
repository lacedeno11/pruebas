"""
Configuration settings for Policy Validation Copilot.

Thresholds, feature flags, and environment configuration.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class ThresholdSettings(BaseSettings):
    """Decision thresholds for auto-close vs HITL routing."""

    confidence_high: float = Field(default=0.85, description="Min confidence for auto-close")
    confidence_medium: float = Field(default=0.60, description="Medium confidence threshold")
    risk_low: float = Field(default=0.30, description="Max risk for auto-close")
    risk_high: float = Field(default=0.70, description="High risk threshold - force HITL")
    anomaly_high: float = Field(default=0.75, description="Anomaly score triggering HITL")
    coverage_min: float = Field(default=0.70, description="Min coverage score for auto-close")


class MLSettings(BaseSettings):
    """ML service configuration."""

    classify_endpoint: str = Field(default="http://ml-service:8001/classify")
    anomaly_endpoint: str = Field(default="http://ml-service:8001/anomaly")
    eta_endpoint: str = Field(default="http://ml-service:8001/eta")
    timeout_seconds: float = Field(default=30.0)
    fallback_enabled: bool = Field(default=True)


class GuardrailSettings(BaseSettings):
    """Guardrails configuration."""

    pii_masking_enabled: bool = Field(default=True)
    allowlist_sources_only: bool = Field(default=True)
    anti_hallucination_enabled: bool = Field(default=True)
    max_retries_on_block: int = Field(default=2)
    rbac_enabled: bool = Field(default=True)


class StorageSettings(BaseSettings):
    """Storage and database configuration."""

    database_url: str = Field(default="postgresql+asyncpg://localhost:5432/policy_copilot")
    redis_url: str = Field(default="redis://localhost:6379/0")
    object_storage_bucket: str = Field(default="policy-documents")
    vector_index_collection: str = Field(default="policy_embeddings")


class Settings(BaseSettings):
    """Main application settings."""

    app_name: str = Field(default="Policy Validation Copilot")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # Sub-settings
    thresholds: ThresholdSettings = Field(default_factory=ThresholdSettings)
    ml: MLSettings = Field(default_factory=MLSettings)
    guardrails: GuardrailSettings = Field(default_factory=GuardrailSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)

    # SLA defaults (minutes)
    default_sla_minutes: int = Field(default=240)
    priority_sla_multiplier: float = Field(default=0.5)

    class Config:
        env_prefix = "POLICY_COPILOT_"
        env_nested_delimiter = "__"


settings = Settings()
