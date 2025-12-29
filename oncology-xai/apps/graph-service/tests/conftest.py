"""Pytest configuration for graph-service tests."""
import pytest
from uuid import uuid4


@pytest.fixture
def sample_case_id():
    """Sample case ID."""
    return uuid4()


@pytest.fixture
def sample_sparql_query():
    """Sample SPARQL query."""
    return """
    SELECT ?s ?p ?o WHERE {
        ?s ?p ?o .
    } LIMIT 10
    """


@pytest.fixture
def sample_triple():
    """Sample RDF triple."""
    return {
        "subject": "http://example.org/entity/123",
        "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
        "object": "http://purl.obolibrary.org/obo/NCIT_C3512",
    }


@pytest.fixture
def sample_graph_data():
    """Sample graph visualization data."""
    return {
        "nodes": [
            {"id": "node1", "label": "Adenocarcinoma", "type": "diagnosis"},
            {"id": "node2", "label": "EGFR", "type": "biomarker"},
            {"id": "node3", "label": "Acinar Pattern", "type": "pattern"},
        ],
        "edges": [
            {"from": "node1", "to": "node2", "label": "hasMarker"},
            {"from": "node1", "to": "node3", "label": "hasPattern"},
        ],
    }
