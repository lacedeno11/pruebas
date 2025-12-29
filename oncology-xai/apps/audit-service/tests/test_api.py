"""API endpoint tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.unit
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data


@pytest.mark.unit
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert "docs" in data


@pytest.mark.unit
async def test_list_audit_events_empty(client: AsyncClient):
    """Test listing audit events when database is empty."""
    response = await client.get("/api/v1/audit/events")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert data["total"] == 0
    assert len(data["events"]) == 0


@pytest.mark.unit
async def test_get_audit_event_not_found(client: AsyncClient):
    """Test getting non-existent audit event."""
    response = await client.get("/api/v1/audit/events/non-existent-id")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


@pytest.mark.unit
async def test_list_audit_events_pagination(client: AsyncClient):
    """Test pagination parameters."""
    response = await client.get("/api/v1/audit/events?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 10


@pytest.mark.unit
async def test_list_audit_events_filters(client: AsyncClient):
    """Test filtering parameters."""
    response = await client.get(
        "/api/v1/audit/events"
        "?case_id=test-case"
        "&user_id=test-user"
        "&entity_type=case"
        "&action=created"
        "&status=success"
    )
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
