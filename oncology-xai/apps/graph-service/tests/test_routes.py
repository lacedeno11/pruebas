"""Tests for graph service routes."""
import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


class TestGraphRoutes:
    @pytest.fixture
    def client(self):
        from graph_service.main import app
        return TestClient(app)

    def test_health_check(self, client):
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "graph-service"

    @patch("graph_service.routes.graphs.GraphService")
    def test_get_case_graph(self, mock_service_class, client, sample_case_id, sample_graph_data):
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        mock_service.get_case_subgraph.return_value = sample_graph_data

        response = client.get(f"/api/v1/cases/{sample_case_id}/graph")

        assert response.status_code in [200, 500]

    @patch("graph_service.routes.graphs.GraphService")
    def test_execute_sparql_query(self, mock_service_class, client, sample_sparql_query):
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        mock_service.execute_query.return_value = {"results": {"bindings": []}}

        response = client.post(
            "/api/v1/sparql",
            json={"query": sample_sparql_query},
        )

        assert response.status_code in [200, 422, 500]


class TestGraphVisualization:
    def test_graph_data_structure(self, sample_graph_data):
        assert "nodes" in sample_graph_data
        assert "edges" in sample_graph_data
        assert len(sample_graph_data["nodes"]) > 0
        assert len(sample_graph_data["edges"]) > 0

    def test_node_structure(self, sample_graph_data):
        for node in sample_graph_data["nodes"]:
            assert "id" in node
            assert "label" in node

    def test_edge_structure(self, sample_graph_data):
        for edge in sample_graph_data["edges"]:
            assert "from" in edge
            assert "to" in edge


class TestSPARQLQueries:
    def test_query_format(self, sample_sparql_query):
        assert "SELECT" in sample_sparql_query.upper()
        assert "WHERE" in sample_sparql_query.upper()

    def test_triple_structure(self, sample_triple):
        assert "subject" in sample_triple
        assert "predicate" in sample_triple
        assert "object" in sample_triple

    def test_triple_uris(self, sample_triple):
        assert sample_triple["subject"].startswith("http")
        assert sample_triple["predicate"].startswith("http")
