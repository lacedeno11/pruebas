"""
Mock API module for PEI Agentic Platform.
Provides mock implementations of external APIs (TELCOS, TelcoDrive) for development/testing.

When SYSTEM_MODE=MOCK, all external API calls are intercepted and return fixture data
instead of making real API requests. This enables:
- Development without TELCOS/TelcoDrive access
- Repeatable testing with consistent data
- Chaos testing with simulated failures (10% failure rate)
- Performance testing with configurable latency (500ms default)

Exported components:
- MockApiService: Singleton service providing mock API methods
- MOCK_OTS, MOCK_CUADRILLAS, MOCK_DOCUMENTS: Fixture data
"""

from app.mock.service import MockApiService

__all__ = ["MockApiService"]

