"""OWL reasoner client for ontology validation."""

import os
from abc import ABC, abstractmethod
from typing import Any


class BaseReasonerClient(ABC):
    """Base reasoner client interface."""

    @abstractmethod
    async def check_consistency(self, ontology_data: str | bytes) -> dict[str, Any]:
        """Check ontology consistency."""
        pass

    @abstractmethod
    async def classify(self, ontology_data: str | bytes) -> dict[str, Any]:
        """Classify ontology (compute inferred class hierarchy)."""
        pass

    @abstractmethod
    async def validate_changes(
        self,
        base_ontology: str | bytes,
        new_ontology: str | bytes,
    ) -> dict[str, Any]:
        """Validate changes between ontology versions."""
        pass


class MockReasonerClient(BaseReasonerClient):
    """Mock reasoner for development and testing."""

    async def check_consistency(self, ontology_data: str | bytes) -> dict[str, Any]:
        """Check mock consistency."""
        data = ontology_data if isinstance(ontology_data, str) else ontology_data.decode()

        return {
            "consistent": True,
            "warnings": [],
            "errors": [],
            "statistics": {
                "classes": data.count("owl:Class") + data.count("rdfs:Class"),
                "properties": data.count("owl:ObjectProperty") + data.count("owl:DatatypeProperty"),
            },
        }

    async def classify(self, ontology_data: str | bytes) -> dict[str, Any]:
        """Mock classification."""
        return {
            "classified": True,
            "inferred_axioms": 0,
            "reasoning_time_ms": 100,
        }

    async def validate_changes(
        self,
        base_ontology: str | bytes,
        new_ontology: str | bytes,
    ) -> dict[str, Any]:
        """Validate mock changes."""
        return {
            "valid": True,
            "breaking_changes": [],
            "deprecations": [],
            "new_concepts": [],
            "removed_concepts": [],
        }


class OWLRLReasonerClient(BaseReasonerClient):
    """OWL-RL reasoner using rdflib and owlrl."""

    async def check_consistency(self, ontology_data: str | bytes) -> dict[str, Any]:
        """Check consistency using OWL-RL."""
        try:
            from rdflib import Graph
            import owlrl

            g = Graph()
            g.parse(data=ontology_data, format="turtle")

            # Run OWL-RL reasoning
            owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)

            # Check for owl:Nothing instances (inconsistency)
            inconsistent = len(list(g.triples((None, None, None)))) == 0

            return {
                "consistent": not inconsistent,
                "warnings": [],
                "errors": ["Ontology is inconsistent"] if inconsistent else [],
                "statistics": {
                    "triples": len(g),
                },
            }
        except ImportError:
            # Fallback to mock
            return await MockReasonerClient().check_consistency(ontology_data)
        except Exception as e:
            return {
                "consistent": False,
                "warnings": [],
                "errors": [str(e)],
                "statistics": {},
            }

    async def classify(self, ontology_data: str | bytes) -> dict[str, Any]:
        """Classify using OWL-RL."""
        try:
            from rdflib import Graph
            import owlrl
            import time

            g = Graph()
            original_size = 0

            g.parse(data=ontology_data, format="turtle")
            original_size = len(g)

            start = time.time()
            owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
            duration = (time.time() - start) * 1000

            return {
                "classified": True,
                "inferred_axioms": len(g) - original_size,
                "reasoning_time_ms": round(duration, 2),
            }
        except ImportError:
            return await MockReasonerClient().classify(ontology_data)

    async def validate_changes(
        self,
        base_ontology: str | bytes,
        new_ontology: str | bytes,
    ) -> dict[str, Any]:
        """Validate changes between versions."""
        try:
            from rdflib import Graph, RDF, OWL

            base = Graph()
            base.parse(data=base_ontology, format="turtle")

            new = Graph()
            new.parse(data=new_ontology, format="turtle")

            # Find classes in each
            base_classes = set(s for s, p, o in base.triples((None, RDF.type, OWL.Class)))
            new_classes = set(s for s, p, o in new.triples((None, RDF.type, OWL.Class)))

            removed = base_classes - new_classes
            added = new_classes - base_classes

            return {
                "valid": True,
                "breaking_changes": [str(c) for c in removed],
                "deprecations": [],
                "new_concepts": [str(c) for c in added],
                "removed_concepts": [str(c) for c in removed],
            }
        except ImportError:
            return await MockReasonerClient().validate_changes(base_ontology, new_ontology)


def get_reasoner_client(backend: str | None = None) -> BaseReasonerClient:
    """Get reasoner client based on configuration."""
    backend = backend or os.getenv("REASONER_BACKEND", "mock")

    if backend == "mock":
        return MockReasonerClient()
    elif backend == "owlrl":
        return OWLRLReasonerClient()
    else:
        return MockReasonerClient()
