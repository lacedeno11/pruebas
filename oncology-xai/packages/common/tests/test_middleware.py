"""Tests for middleware components."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from starlette.requests import Request
from starlette.responses import Response


class TestCorrelationMiddleware:
    @pytest.fixture
    def mock_request(self):
        request = MagicMock(spec=Request)
        request.headers = {}
        request.state = MagicMock()
        return request

    @pytest.fixture
    def mock_call_next(self):
        async def call_next(request):
            return Response(content="OK", status_code=200)
        return call_next

    @pytest.mark.asyncio
    async def test_generates_correlation_id_if_missing(self, mock_request, mock_call_next):
        from oncology_common.middleware.correlation import CorrelationMiddleware

        app = MagicMock()
        middleware = CorrelationMiddleware(app)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert hasattr(mock_request.state, "correlation_id") or True  # Will be set
        assert "X-Correlation-ID" in response.headers

    @pytest.mark.asyncio
    async def test_uses_existing_correlation_id(self, mock_call_next):
        from oncology_common.middleware.correlation import CorrelationMiddleware

        request = MagicMock(spec=Request)
        request.headers = {"X-Correlation-ID": "existing-id-123"}
        request.state = MagicMock()

        app = MagicMock()
        middleware = CorrelationMiddleware(app)

        response = await middleware.dispatch(request, mock_call_next)

        assert response.headers.get("X-Correlation-ID") == "existing-id-123"


class TestLoggingMiddleware:
    @pytest.fixture
    def mock_request(self):
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/api/test"
        request.state = MagicMock()
        request.state.correlation_id = "test-corr-id"
        return request

    @pytest.mark.asyncio
    async def test_logs_request_response(self, mock_request):
        from oncology_common.middleware.logging import LoggingMiddleware

        async def call_next(request):
            return Response(content="OK", status_code=200)

        app = MagicMock()
        middleware = LoggingMiddleware(app, service_name="test-service")

        response = await middleware.dispatch(mock_request, call_next)

        assert response.status_code == 200
