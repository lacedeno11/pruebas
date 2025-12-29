"""ML model client abstraction with mock and Triton implementations."""

import os
import random
from abc import ABC, abstractmethod
from typing import Any


class BaseModelClient(ABC):
    """Base ML model client interface."""

    @abstractmethod
    async def predict_patterns(
        self,
        image_data: bytes,
        thresholds: dict[str, float],
    ) -> list[dict[str, Any]]:
        """Predict histological patterns from image."""
        pass

    @abstractmethod
    async def predict_mutations(
        self,
        image_data: bytes,
        thresholds: dict[str, float],
    ) -> list[dict[str, Any]]:
        """Predict genetic mutations from image."""
        pass

    @abstractmethod
    async def generate_xai_artifacts(
        self,
        image_data: bytes,
        predictions: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate XAI artifacts (overlays, heatmaps)."""
        pass


class MockModelClient(BaseModelClient):
    """Mock model client for development and testing."""

    PATTERNS = ["lepidic", "acinar", "papillary", "micropapillary", "solid"]
    MUTATIONS = ["EGFR", "KRAS", "TP53"]

    def __init__(self, model_version: str = "mock_v1.0"):
        self.model_version = model_version

    async def predict_patterns(
        self,
        image_data: bytes,
        thresholds: dict[str, float],
    ) -> list[dict[str, Any]]:
        """Generate mock pattern predictions."""
        results = []

        # Use image size as a seed for reproducibility
        random.seed(len(image_data))

        for pattern in self.PATTERNS:
            score = random.uniform(0.3, 0.95)
            threshold = thresholds.get(pattern, 0.55)

            results.append({
                "pattern": pattern,
                "score": round(score, 4),
                "is_conclusive": score >= threshold,
                "threshold": threshold,
                "model_version": self.model_version,
                "area_mm2": round(random.uniform(1, 50), 2) if score >= threshold else None,
            })

        return results

    async def predict_mutations(
        self,
        image_data: bytes,
        thresholds: dict[str, float],
    ) -> list[dict[str, Any]]:
        """Generate mock mutation predictions."""
        results = []

        random.seed(len(image_data) + 1)

        for mutation in self.MUTATIONS:
            score = random.uniform(0.3, 0.9)
            threshold = thresholds.get(mutation, 0.60)

            if score >= threshold:
                status = "POS"
            elif score < (threshold - 0.15):
                status = "NEG"
            else:
                status = "INCONCLUSIVE"

            results.append({
                "mutation": mutation,
                "score": round(score, 4),
                "status": status,
                "threshold": threshold,
                "model_version": self.model_version,
            })

        return results

    async def generate_xai_artifacts(
        self,
        image_data: bytes,
        predictions: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate mock XAI artifacts."""
        artifacts = []

        # Generate overlay for each pattern
        for pattern_result in predictions.get("patterns", []):
            if pattern_result.get("is_conclusive"):
                artifacts.append({
                    "artifact_type": "overlay",
                    "pattern": pattern_result["pattern"],
                    "description": f"Segmentation overlay for {pattern_result['pattern']}",
                    "mock_data": True,
                })

                artifacts.append({
                    "artifact_type": "heatmap",
                    "pattern": pattern_result["pattern"],
                    "description": f"Attention heatmap for {pattern_result['pattern']}",
                    "mock_data": True,
                })

        return artifacts


class TritonModelClient(BaseModelClient):
    """Triton Inference Server client."""

    def __init__(self, triton_url: str, model_name: str = "lung_patterns"):
        self.triton_url = triton_url
        self.model_name = model_name

    async def predict_patterns(
        self,
        image_data: bytes,
        thresholds: dict[str, float],
    ) -> list[dict[str, Any]]:
        """Predict patterns using Triton."""
        # Stub implementation - would use tritonclient
        raise NotImplementedError("Triton integration not yet implemented")

    async def predict_mutations(
        self,
        image_data: bytes,
        thresholds: dict[str, float],
    ) -> list[dict[str, Any]]:
        """Predict mutations using Triton."""
        raise NotImplementedError("Triton integration not yet implemented")

    async def generate_xai_artifacts(
        self,
        image_data: bytes,
        predictions: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate XAI artifacts using Triton."""
        raise NotImplementedError("Triton integration not yet implemented")


def get_model_client(
    backend: str | None = None,
    triton_url: str | None = None,
) -> BaseModelClient:
    """Get model client based on configuration."""
    backend = backend or os.getenv("MODEL_BACKEND", "mock")

    if backend == "mock":
        return MockModelClient()
    elif backend == "triton":
        url = triton_url or os.getenv("TRITON_URL")
        if not url:
            raise ValueError("TRITON_URL required for Triton backend")
        return TritonModelClient(triton_url=url)
    else:
        return MockModelClient()
