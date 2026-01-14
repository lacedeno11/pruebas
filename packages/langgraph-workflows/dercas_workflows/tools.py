"""
DERCAS-ONCO-XAI LangGraph Tools

Common tools interfaces and implementations for LangGraph workflows.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ToolResult(BaseModel):
    """Result from tool execution."""
    success: bool
    data: Any = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BaseTool(ABC):
    """Base class for all workflow tools."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass
    
    def validate_inputs(self, **kwargs) -> bool:
        """Validate tool inputs."""
        return True
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)


# =============================================================================
# LLM CLIENT INTERFACE
# =============================================================================

class LLMClient(BaseTool):
    """LLM client interface for text generation and analysis."""
    
    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.1,
        **kwargs
    ) -> ToolResult:
        """Generate text from prompt."""
        pass
    
    @abstractmethod
    async def extract_entities(
        self,
        text: str,
        entity_types: List[str],
        **kwargs
    ) -> ToolResult:
        """Extract entities from text."""
        pass
    
    @abstractmethod
    async def classify_text(
        self,
        text: str,
        categories: List[str],
        **kwargs
    ) -> ToolResult:
        """Classify text into categories."""
        pass


class MockLLMClient(LLMClient):
    """Mock LLM client for testing and development."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("mock_llm", config)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute LLM operation."""
        operation = kwargs.get("operation", "generate")
        
        if operation == "generate":
            return await self.generate_text(kwargs.get("prompt", ""))
        elif operation == "extract":
            return await self.extract_entities(
                kwargs.get("text", ""),
                kwargs.get("entity_types", [])
            )
        elif operation == "classify":
            return await self.classify_text(
                kwargs.get("text", ""),
                kwargs.get("categories", [])
            )
        else:
            return ToolResult(
                success=False,
                error_message=f"Unknown operation: {operation}",
                error_code="INVALID_OPERATION"
            )
    
    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.1,
        **kwargs
    ) -> ToolResult:
        """Mock text generation."""
        # Simple mock response based on prompt content
        if "diagnosis" in prompt.lower():
            response = "Based on the available evidence, this appears to suggest patterns consistent with adenocarcinoma. However, this is a research tool and should not be used for diagnostic purposes. Clinical correlation and further evaluation are required."
        elif "extract" in prompt.lower():
            response = "Extracted entities: lung adenocarcinoma, EGFR mutation, stage IIIA"
        else:
            response = f"Mock response to: {prompt[:50]}..."
        
        return ToolResult(
            success=True,
            data={
                "text": response,
                "tokens_used": len(response.split()),
                "model": "mock-llm-v1"
            }
        )
    
    async def extract_entities(
        self,
        text: str,
        entity_types: List[str],
        **kwargs
    ) -> ToolResult:
        """Mock entity extraction."""
        # Mock entities based on common medical terms
        mock_entities = []
        
        if "lung" in text.lower():
            mock_entities.append({
                "text": "lung adenocarcinoma",
                "type": "DIAGNOSIS",
                "start": text.lower().find("lung"),
                "end": text.lower().find("lung") + 4,
                "confidence": 0.85
            })
        
        if "egfr" in text.lower():
            mock_entities.append({
                "text": "EGFR",
                "type": "GENE",
                "start": text.lower().find("egfr"),
                "end": text.lower().find("egfr") + 4,
                "confidence": 0.92
            })
        
        return ToolResult(
            success=True,
            data={
                "entities": mock_entities,
                "extraction_method": "mock_nlp"
            }
        )
    
    async def classify_text(
        self,
        text: str,
        categories: List[str],
        **kwargs
    ) -> ToolResult:
        """Mock text classification."""
        # Simple mock classification
        scores = {}
        for category in categories:
            if category.lower() in text.lower():
                scores[category] = 0.8
            else:
                scores[category] = 0.2
        
        return ToolResult(
            success=True,
            data={
                "scores": scores,
                "predicted_category": max(scores, key=scores.get) if scores else None
            }
        )


# =============================================================================
# MODEL CLIENT INTERFACE
# =============================================================================

class ModelClient(BaseTool):
    """ML model client interface for inference."""
    
    @abstractmethod
    async def predict_patterns(
        self,
        image_uri: str,
        model_profile: str = "lung_patterns_v3",
        **kwargs
    ) -> ToolResult:
        """Predict histological patterns."""
        pass
    
    @abstractmethod
    async def predict_mutations(
        self,
        image_uri: str,
        model_profile: str = "genetic_mutations_v2",
        **kwargs
    ) -> ToolResult:
        """Predict genetic mutations."""
        pass
    
    @abstractmethod
    async def generate_xai(
        self,
        image_uri: str,
        predictions: Dict[str, Any],
        **kwargs
    ) -> ToolResult:
        """Generate explainable AI artifacts."""
        pass


class MockModelClient(ModelClient):
    """Mock model client for testing and development."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("mock_model", config)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute model operation."""
        operation = kwargs.get("operation", "predict_patterns")
        
        if operation == "predict_patterns":
            return await self.predict_patterns(kwargs.get("image_uri", ""))
        elif operation == "predict_mutations":
            return await self.predict_mutations(kwargs.get("image_uri", ""))
        elif operation == "generate_xai":
            return await self.generate_xai(
                kwargs.get("image_uri", ""),
                kwargs.get("predictions", {})
            )
        else:
            return ToolResult(
                success=False,
                error_message=f"Unknown operation: {operation}",
                error_code="INVALID_OPERATION"
            )
    
    async def predict_patterns(
        self,
        image_uri: str,
        model_profile: str = "lung_patterns_v3",
        **kwargs
    ) -> ToolResult:
        """Mock pattern prediction."""
        # Mock pattern scores
        patterns = {
            "lepidic": 0.15,
            "acinar": 0.75,
            "papillary": 0.25,
            "micropapillary": 0.05,
            "solid": 0.35
        }
        
        results = []
        for pattern, score in patterns.items():
            results.append({
                "pattern": pattern,
                "score": score,
                "overlay_uri": f"s3://bucket/overlays/{pattern}_overlay.png",
                "heatmap_uri": f"s3://bucket/heatmaps/{pattern}_heatmap.png",
                "area_mm2": score * 100  # Mock area calculation
            })
        
        return ToolResult(
            success=True,
            data={
                "patterns": results,
                "model_version": "3.2.1",
                "model_profile": model_profile,
                "processing_time_ms": 1250
            }
        )
    
    async def predict_mutations(
        self,
        image_uri: str,
        model_profile: str = "genetic_mutations_v2",
        **kwargs
    ) -> ToolResult:
        """Mock mutation prediction."""
        # Mock mutation scores
        mutations = {
            "EGFR": {"score": 0.65, "status": "INCONCLUSIVE"},
            "KRAS": {"score": 0.82, "status": "POS"},
            "TP53": {"score": 0.45, "status": "NEG"}
        }
        
        results = []
        for mutation, data in mutations.items():
            results.append({
                "mutation": mutation,
                "score": data["score"],
                "status": data["status"],
                "evidence_uri": f"s3://bucket/evidence/{mutation}_evidence.json"
            })
        
        return ToolResult(
            success=True,
            data={
                "mutations": results,
                "model_version": "2.1.0",
                "model_profile": model_profile,
                "processing_time_ms": 850
            }
        )
    
    async def generate_xai(
        self,
        image_uri: str,
        predictions: Dict[str, Any],
        **kwargs
    ) -> ToolResult:
        """Mock XAI generation."""
        artifacts = [
            {
                "type": "gradcam",
                "uri": "s3://bucket/xai/gradcam_overlay.png",
                "hash": "sha256:abc123...",
                "description": "Grad-CAM visualization"
            },
            {
                "type": "saliency",
                "uri": "s3://bucket/xai/saliency_map.png",
                "hash": "sha256:def456...",
                "description": "Saliency map"
            }
        ]
        
        return ToolResult(
            success=True,
            data={
                "artifacts": artifacts,
                "xai_model_version": "1.0.0",
                "processing_time_ms": 500
            }
        )


# =============================================================================
# STORAGE CLIENT INTERFACE
# =============================================================================

class StorageClient(BaseTool):
    """Storage client interface for object storage operations."""
    
    @abstractmethod
    async def upload_file(
        self,
        file_path: str,
        bucket: str,
        key: str,
        **kwargs
    ) -> ToolResult:
        """Upload file to storage."""
        pass
    
    @abstractmethod
    async def download_file(
        self,
        bucket: str,
        key: str,
        local_path: str,
        **kwargs
    ) -> ToolResult:
        """Download file from storage."""
        pass
    
    @abstractmethod
    async def generate_signed_url(
        self,
        bucket: str,
        key: str,
        expiration_seconds: int = 3600,
        **kwargs
    ) -> ToolResult:
        """Generate signed URL for file access."""
        pass


class MockStorageClient(StorageClient):
    """Mock storage client for testing and development."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("mock_storage", config)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute storage operation."""
        operation = kwargs.get("operation", "upload")
        
        if operation == "upload":
            return await self.upload_file(
                kwargs.get("file_path", ""),
                kwargs.get("bucket", ""),
                kwargs.get("key", "")
            )
        elif operation == "download":
            return await self.download_file(
                kwargs.get("bucket", ""),
                kwargs.get("key", ""),
                kwargs.get("local_path", "")
            )
        elif operation == "signed_url":
            return await self.generate_signed_url(
                kwargs.get("bucket", ""),
                kwargs.get("key", ""),
                kwargs.get("expiration_seconds", 3600)
            )
        else:
            return ToolResult(
                success=False,
                error_message=f"Unknown operation: {operation}",
                error_code="INVALID_OPERATION"
            )
    
    async def upload_file(
        self,
        file_path: str,
        bucket: str,
        key: str,
        **kwargs
    ) -> ToolResult:
        """Mock file upload."""
        return ToolResult(
            success=True,
            data={
                "uri": f"s3://{bucket}/{key}",
                "etag": "mock-etag-123",
                "size_bytes": 1024000
            }
        )
    
    async def download_file(
        self,
        bucket: str,
        key: str,
        local_path: str,
        **kwargs
    ) -> ToolResult:
        """Mock file download."""
        return ToolResult(
            success=True,
            data={
                "local_path": local_path,
                "size_bytes": 1024000
            }
        )
    
    async def generate_signed_url(
        self,
        bucket: str,
        key: str,
        expiration_seconds: int = 3600,
        **kwargs
    ) -> ToolResult:
        """Mock signed URL generation."""
        return ToolResult(
            success=True,
            data={
                "signed_url": f"https://mock-storage.com/{bucket}/{key}?signature=mock",
                "expires_in_seconds": expiration_seconds
            }
        )


# =============================================================================
# SPARQL CLIENT INTERFACE
# =============================================================================

class SPARQLClient(BaseTool):
    """SPARQL client interface for triple store operations."""
    
    @abstractmethod
    async def query(
        self,
        sparql_query: str,
        graph_uri: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """Execute SPARQL query."""
        pass
    
    @abstractmethod
    async def update(
        self,
        sparql_update: str,
        graph_uri: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """Execute SPARQL update."""
        pass
    
    @abstractmethod
    async def load_ontology(
        self,
        ontology_uri: str,
        graph_uri: str,
        **kwargs
    ) -> ToolResult:
        """Load ontology into graph."""
        pass


class MockSPARQLClient(SPARQLClient):
    """Mock SPARQL client for testing and development."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("mock_sparql", config)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute SPARQL operation."""
        operation = kwargs.get("operation", "query")
        
        if operation == "query":
            return await self.query(kwargs.get("sparql_query", ""))
        elif operation == "update":
            return await self.update(kwargs.get("sparql_update", ""))
        elif operation == "load_ontology":
            return await self.load_ontology(
                kwargs.get("ontology_uri", ""),
                kwargs.get("graph_uri", "")
            )
        else:
            return ToolResult(
                success=False,
                error_message=f"Unknown operation: {operation}",
                error_code="INVALID_OPERATION"
            )
    
    async def query(
        self,
        sparql_query: str,
        graph_uri: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """Mock SPARQL query."""
        # Mock results based on query content
        if "SELECT" in sparql_query.upper():
            results = [
                {
                    "concept": "http://purl.obolibrary.org/obo/NCIT_C2926",
                    "label": "Lung Adenocarcinoma",
                    "definition": "A non-small cell lung carcinoma..."
                }
            ]
        else:
            results = []
        
        return ToolResult(
            success=True,
            data={
                "results": results,
                "query_time_ms": 45,
                "graph_uri": graph_uri
            }
        )
    
    async def update(
        self,
        sparql_update: str,
        graph_uri: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """Mock SPARQL update."""
        return ToolResult(
            success=True,
            data={
                "triples_modified": 5,
                "update_time_ms": 120,
                "graph_uri": graph_uri
            }
        )
    
    async def load_ontology(
        self,
        ontology_uri: str,
        graph_uri: str,
        **kwargs
    ) -> ToolResult:
        """Mock ontology loading."""
        return ToolResult(
            success=True,
            data={
                "triples_loaded": 15000,
                "load_time_ms": 2500,
                "ontology_uri": ontology_uri,
                "graph_uri": graph_uri
            }
        )


# =============================================================================
# REASONER CLIENT INTERFACE
# =============================================================================

class ReasonerClient(BaseTool):
    """Reasoner client interface for ontology reasoning."""
    
    @abstractmethod
    async def check_consistency(
        self,
        graph_uri: str,
        **kwargs
    ) -> ToolResult:
        """Check ontology consistency."""
        pass
    
    @abstractmethod
    async def infer_triples(
        self,
        graph_uri: str,
        **kwargs
    ) -> ToolResult:
        """Infer new triples."""
        pass
    
    @abstractmethod
    async def classify_ontology(
        self,
        graph_uri: str,
        **kwargs
    ) -> ToolResult:
        """Classify ontology."""
        pass


class MockReasonerClient(ReasonerClient):
    """Mock reasoner client for testing and development."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("mock_reasoner", config)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute reasoner operation."""
        operation = kwargs.get("operation", "check_consistency")
        
        if operation == "check_consistency":
            return await self.check_consistency(kwargs.get("graph_uri", ""))
        elif operation == "infer_triples":
            return await self.infer_triples(kwargs.get("graph_uri", ""))
        elif operation == "classify_ontology":
            return await self.classify_ontology(kwargs.get("graph_uri", ""))
        else:
            return ToolResult(
                success=False,
                error_message=f"Unknown operation: {operation}",
                error_code="INVALID_OPERATION"
            )
    
    async def check_consistency(
        self,
        graph_uri: str,
        **kwargs
    ) -> ToolResult:
        """Mock consistency check."""
        return ToolResult(
            success=True,
            data={
                "consistent": True,
                "inconsistencies": [],
                "reasoning_time_ms": 500,
                "graph_uri": graph_uri
            }
        )
    
    async def infer_triples(
        self,
        graph_uri: str,
        **kwargs
    ) -> ToolResult:
        """Mock triple inference."""
        return ToolResult(
            success=True,
            data={
                "inferred_triples": 25,
                "reasoning_time_ms": 1200,
                "graph_uri": graph_uri
            }
        )
    
    async def classify_ontology(
        self,
        graph_uri: str,
        **kwargs
    ) -> ToolResult:
        """Mock ontology classification."""
        return ToolResult(
            success=True,
            data={
                "classes_classified": 150,
                "classification_time_ms": 800,
                "graph_uri": graph_uri
            }
        )


# =============================================================================
# AUDIT LOGGER INTERFACE
# =============================================================================

class AuditLogger(BaseTool):
    """Audit logger interface for compliance tracking."""
    
    @abstractmethod
    async def log_event(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        status: str,
        details: Dict[str, Any],
        **kwargs
    ) -> ToolResult:
        """Log audit event."""
        pass


class MockAuditLogger(AuditLogger):
    """Mock audit logger for testing and development."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("mock_audit", config)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute audit logging."""
        return await self.log_event(
            kwargs.get("entity_type", ""),
            kwargs.get("entity_id", ""),
            kwargs.get("action", ""),
            kwargs.get("status", ""),
            kwargs.get("details", {})
        )
    
    async def log_event(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        status: str,
        details: Dict[str, Any],
        **kwargs
    ) -> ToolResult:
        """Mock audit event logging."""
        return ToolResult(
            success=True,
            data={
                "audit_event_id": f"audit_{UUID.uuid4()}",
                "logged_at": "2024-01-01T12:00:00Z"
            }
        )


# =============================================================================
# POLICY ENGINE INTERFACE
# =============================================================================

class PolicyEngine(BaseTool):
    """Policy engine interface for guardrails and HITL policies."""
    
    @abstractmethod
    async def evaluate_policy(
        self,
        policy_name: str,
        context: Dict[str, Any],
        **kwargs
    ) -> ToolResult:
        """Evaluate policy against context."""
        pass
    
    @abstractmethod
    async def check_guardrails(
        self,
        content: str,
        content_type: str = "text",
        **kwargs
    ) -> ToolResult:
        """Check content against clinical guardrails."""
        pass


class MockPolicyEngine(PolicyEngine):
    """Mock policy engine for testing and development."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("mock_policy", config)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute policy evaluation."""
        operation = kwargs.get("operation", "evaluate_policy")
        
        if operation == "evaluate_policy":
            return await self.evaluate_policy(
                kwargs.get("policy_name", ""),
                kwargs.get("context", {})
            )
        elif operation == "check_guardrails":
            return await self.check_guardrails(
                kwargs.get("content", ""),
                kwargs.get("content_type", "text")
            )
        else:
            return ToolResult(
                success=False,
                error_message=f"Unknown operation: {operation}",
                error_code="INVALID_OPERATION"
            )
    
    async def evaluate_policy(
        self,
        policy_name: str,
        context: Dict[str, Any],
        **kwargs
    ) -> ToolResult:
        """Mock policy evaluation."""
        # Simple mock policy evaluation
        if "low_confidence" in policy_name:
            # Check if any scores are below threshold
            scores = context.get("scores", {})
            threshold = context.get("threshold", 0.7)
            
            low_confidence = any(score < threshold for score in scores.values())
            
            return ToolResult(
                success=True,
                data={
                    "policy_result": "REVIEW_REQUIRED" if low_confidence else "APPROVED",
                    "requires_hitl": low_confidence,
                    "details": {"low_confidence_items": [k for k, v in scores.items() if v < threshold]}
                }
            )
        
        return ToolResult(
            success=True,
            data={
                "policy_result": "APPROVED",
                "requires_hitl": False
            }
        )
    
    async def check_guardrails(
        self,
        content: str,
        content_type: str = "text",
        **kwargs
    ) -> ToolResult:
        """Mock guardrails check."""
        violations = []
        
        # Check for definitive diagnosis language
        definitive_terms = ["diagnosed with", "has been diagnosed", "confirms diagnosis"]
        for term in definitive_terms:
            if term in content.lower():
                violations.append(f"Definitive diagnosis language: '{term}'")
        
        # Check for required disclaimers
        required_terms = ["limitation", "research use", "clinical correlation"]
        has_disclaimer = any(term in content.lower() for term in required_terms)
        
        if not has_disclaimer:
            violations.append("Missing required clinical disclaimer")
        
        return ToolResult(
            success=True,
            data={
                "guardrails_passed": len(violations) == 0,
                "violations": violations,
                "content_type": content_type
            }
        )


# =============================================================================
# TOOL REGISTRY
# =============================================================================

class ToolRegistry:
    """Registry for managing workflow tools."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tool_configs: Dict[str, Dict[str, Any]] = {}
    
    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    def configure_tool(self, name: str, config: Dict[str, Any]) -> None:
        """Configure a tool."""
        self._tool_configs[name] = config
        if name in self._tools:
            self._tools[name].config.update(config)
    
    def create_mock_tools(self) -> None:
        """Create and register mock tools for development."""
        self.register_tool(MockLLMClient())
        self.register_tool(MockModelClient())
        self.register_tool(MockStorageClient())
        self.register_tool(MockSPARQLClient())
        self.register_tool(MockReasonerClient())
        self.register_tool(MockAuditLogger())
        self.register_tool(MockPolicyEngine())


# Global tool registry
_global_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get global tool registry."""
    return _global_registry


def register_tool(tool: BaseTool) -> None:
    """Register a tool in the global registry."""
    _global_registry.register_tool(tool)


def get_tool(name: str) -> Optional[BaseTool]:
    """Get tool from global registry."""
    return _global_registry.get_tool(name)


def setup_mock_tools() -> None:
    """Setup mock tools for development."""
    _global_registry.create_mock_tools()


# Tool factory functions
def create_llm_client(provider: str = "mock", config: Optional[Dict[str, Any]] = None) -> LLMClient:
    """Create LLM client based on provider."""
    if provider == "mock":
        return MockLLMClient(config)
    # Add other providers (OpenAI, Anthropic) here
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def create_model_client(backend: str = "mock", config: Optional[Dict[str, Any]] = None) -> ModelClient:
    """Create model client based on backend."""
    if backend == "mock":
        return MockModelClient(config)
    # Add other backends (Triton, TorchServe) here
    else:
        raise ValueError(f"Unknown model backend: {backend}")


def create_storage_client(backend: str = "mock", config: Optional[Dict[str, Any]] = None) -> StorageClient:
    """Create storage client based on backend."""
    if backend == "mock":
        return MockStorageClient(config)
    # Add other backends (MinIO, S3) here
    else:
        raise ValueError(f"Unknown storage backend: {backend}")


def create_sparql_client(backend: str = "mock", config: Optional[Dict[str, Any]] = None) -> SPARQLClient:
    """Create SPARQL client based on backend."""
    if backend == "mock":
        return MockSPARQLClient(config)
    # Add other backends (Fuseki, Virtuoso) here
    else:
        raise ValueError(f"Unknown SPARQL backend: {backend}")


def create_reasoner_client(backend: str = "mock", config: Optional[Dict[str, Any]] = None) -> ReasonerClient:
    """Create reasoner client based on backend."""
    if backend == "mock":
        return MockReasonerClient(config)
    # Add other backends (OWL-RL, Pellet) here
    else:
        raise ValueError(f"Unknown reasoner backend: {backend}")
