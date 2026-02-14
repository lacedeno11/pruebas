"""
Mock API Service for PEI Agentic Platform.
Simulates external API calls (TELCOS, TelcoDrive) for development and testing.

When SYSTEM_MODE=MOCK, this service intercepts API calls and returns mock fixture data
instead of making real requests. Includes:
- Configurable latency simulation (default 500ms)
- Chaos testing with configurable failure rates (default 10%)
- Complete fixture data for OTs, crews, and documents
- Singleton pattern for efficient resource usage
"""

import asyncio
import random
import uuid
from functools import lru_cache
from typing import Dict, List, Optional

from app.core.config import get_settings
from app.mock.fixtures import (
    MOCK_CUADRILLAS,
    MOCK_DOCUMENTS,
    MOCK_OTS,
    filter_ots_by_project_type,
    filter_ots_by_status,
    get_document_checklist,
    get_ot_by_external_id,
)


# ============================================================================
# MOCK API SERVICE
# ============================================================================


class MockApiService:
    """
    Singleton service providing mock implementations of external APIs.
    
    Used when SYSTEM_MODE=MOCK to simulate TELCOS and TelcoDrive APIs
    without requiring real API access. Includes latency simulation and
    chaos testing capabilities.
    
    Attributes:
        latency_ms: Milliseconds to simulate for each API call (default 500)
        failure_rate: Probability of simulated failure (0.0-1.0, default 0.1 = 10%)
    
    Example:
        >>> service = MockApiService.get_instance()
        >>> ots = await service.get_ots(filters={"status": "PREPLANIFICADA"})
        >>> len(ots) > 0
        True
    """

    _instance: Optional["MockApiService"] = None
    _initialized: bool = False

    def __init__(self):
        """Initialize MockApiService with configuration from settings."""
        if MockApiService._initialized:
            raise RuntimeError(
                "MockApiService is a singleton. Use get_instance() instead."
            )

        settings = get_settings()
        self.latency_ms = settings.MOCK_API_LATENCY_MS
        self.failure_rate = 0.1  # 10% failure rate for chaos testing
        self.call_count = 0
        self.failure_count = 0

        MockApiService._initialized = True

    @classmethod
    def get_instance(cls) -> "MockApiService":
        """
        Get singleton instance of MockApiService.
        
        Uses @lru_cache pattern to ensure single instance throughout application.
        Thread-safe for async operations.
        
        Returns:
            MockApiService: Singleton instance
            
        Example:
            >>> service = MockApiService.get_instance()
            >>> isinstance(service, MockApiService)
            True
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ========================================================================
    # LATENCY SIMULATION
    # ========================================================================

    async def _simulate_latency(self) -> None:
        """
        Simulate network latency for realistic testing.
        
        Sleeps for MOCK_API_LATENCY_MS milliseconds (default 500ms).
        Uses asyncio.sleep to avoid blocking event loop.
        
        This allows testing UI loading states and timeout handling
        without requiring real network calls.
        
        Example:
            >>> import asyncio
            >>> import time
            >>> start = time.time()
            >>> asyncio.run(service._simulate_latency())
            >>> elapsed = time.time() - start
            >>> elapsed >= 0.5
            True
        """
        await asyncio.sleep(self.latency_ms / 1000.0)

    # ========================================================================
    # CHAOS TESTING
    # ========================================================================

    def _should_fail(self) -> bool:
        """
        Determine if this operation should fail for chaos testing.
        
        Returns True with probability equal to failure_rate.
        Enables testing error handling without modifying real APIs.
        
        Returns:
            bool: True if operation should fail
            
        Example:
            >>> random.seed(42)
            >>> service._should_fail()  # May return True or False based on 10% rate
            False
        """
        return random.random() < self.failure_rate

    # ========================================================================
    # TELCOS API SIMULATION
    # ========================================================================

    async def get_ots(
        self,
        filters: Optional[Dict[str, any]] = None,
    ) -> List[Dict]:
        """
        Simulate TELCOS API GET /ots endpoint.
        
        Returns list of OTs with optional filtering by status and project type.
        Includes 500ms latency simulation for realistic testing.
        
        Args:
            filters: Optional filter dict with keys:
                - status: Filter by OT status (e.g., "PREPLANIFICADA")
                - project_type: Filter by project type (e.g., "PUBLICO")
                - limit: Max results (default all)
                - offset: Pagination offset (default 0)
        
        Returns:
            List[Dict]: List of OT dictionaries matching filters
            
        Raises:
            RuntimeError: If simulated failure occurs (10% chance)
            
        Example:
            >>> service = MockApiService.get_instance()
            >>> ots = await service.get_ots()
            >>> len(ots)
            20
            
            >>> ots = await service.get_ots({"status": "PREPLANIFICADA"})
            >>> all(ot["status"] == "PREPLANIFICADA" for ot in ots)
            True
        """
        self.call_count += 1

        # Simulate latency
        await self._simulate_latency()

        # Simulate failures for chaos testing
        if self._should_fail():
            self.failure_count += 1
            raise RuntimeError("Simulated TELCOS API failure: GET /ots")

        # Start with all OTs
        ots = [ot.copy() for ot in MOCK_OTS]

        # Apply filters if provided
        if filters:
            status = filters.get("status")
            if status:
                ots = filter_ots_by_status(status)

            project_type = filters.get("project_type")
            if project_type:
                ots = filter_ots_by_project_type(project_type)

            # Apply pagination
            limit = filters.get("limit", len(ots))
            offset = filters.get("offset", 0)
            ots = ots[offset : offset + limit]

        return ots

    async def update_ot_status(
        self,
        external_id: str,
        new_status: str,
    ) -> Dict:
        """
        Simulate TELCOS API POST /ots/{id}/status endpoint.
        
        Updates OT status in mock data (no persistence).
        Includes 10% simulated failure rate for chaos testing.
        
        Args:
            external_id: External ID of OT to update (e.g., "OT-2024-001234")
            new_status: New status value (e.g., "PLANIFICADA")
            
        Returns:
            Dict: Response with keys:
                - success: bool, True if update succeeded
                - message: str, result message
                - ot_id: str, UUID of OT (if found)
                - previous_status: str, status before update (if found)
                - new_status: str, status after update (if found)
                
        Raises:
            RuntimeError: If simulated failure occurs (10% chance)
            
        Example:
            >>> response = await service.update_ot_status(
            ...     "OT-2024-001001",
            ...     "PLANIFICADA"
            ... )
            >>> response["success"]
            True
            >>> response["new_status"]
            "PLANIFICADA"
            
            >>> response = await service.update_ot_status(
            ...     "OT-NONEXISTENT",
            ...     "PLANIFICADA"
            ... )
            >>> response["success"]
            False
        """
        self.call_count += 1

        # Simulate latency
        await self._simulate_latency()

        # Simulate failures for chaos testing
        if self._should_fail():
            self.failure_count += 1
            raise RuntimeError(
                f"Simulated TELCOS API failure: POST /ots/{external_id}/status"
            )

        # Find OT by external_id
        ot = get_ot_by_external_id(external_id)

        if not ot:
            return {
                "success": False,
                "message": f"OT with external_id '{external_id}' not found",
            }

        # Update status in mock data
        previous_status = ot["status"]
        ot["status"] = new_status
        ot["updated_at"] = str(asyncio.get_event_loop().time())

        return {
            "success": True,
            "message": f"OT status updated from {previous_status} to {new_status}",
            "ot_id": ot["id"],
            "external_id": external_id,
            "previous_status": previous_status,
            "new_status": new_status,
        }

    # ========================================================================
    # TELCODRIVE API SIMULATION
    # ========================================================================

    async def get_telcodrive_documents(
        self,
        ot_id: str,
    ) -> Dict:
        """
        Simulate TelcoDrive API GET /documents/{ot_id} endpoint.
        
        Returns document checklist for OT (for PUBLIC projects, 29 required docs).
        Uses mock fixture data with random completion status.
        Includes 500ms latency simulation for realistic testing.
        
        Args:
            ot_id: OT ID to get documents for (any valid UUID or "OT-*" external ID)
                  The actual OT is not verified - returns mock documents for all requests
        
        Returns:
            Dict: Response with keys:
                - ot_id: str, the OT ID requested
                - total_documents: int, total required documents (29 for PUBLIC)
                - completed_documents: int, number of completed documents
                - completion_percentage: float, percentage of completion (0-100)
                - documents: List[Dict], list of documents with keys:
                    - name: str, document name
                    - completed: bool, completion status
                    - completed_at: str, timestamp if completed (ISO format)
                
        Example:
            >>> response = await service.get_telcodrive_documents(
            ...     "550e8400-e29b-41d4-a716-446655440000"
            ... )
            >>> response["total_documents"]
            29
            >>> response["completion_percentage"] >= 0
            True
            
            >>> # Generate random documents each call (for testing variety)
            >>> response1 = await service.get_telcodrive_documents("ot1")
            >>> response2 = await service.get_telcodrive_documents("ot1")
            >>> # Different completion statuses due to random generation
        """
        self.call_count += 1

        # Simulate latency
        await self._simulate_latency()

        # Generate random document checklist (80% completion rate)
        checklist = get_document_checklist()

        # Count completed documents
        completed_count = sum(1 for v in checklist.values() if v)
        total_count = len(checklist)
        completion_percentage = (completed_count / total_count) * 100 if total_count > 0 else 0

        # Build response with document details
        documents = [
            {
                "name": doc_name,
                "completed": completed,
                "completed_at": (
                    asyncio.get_event_loop().time()
                    if completed
                    else None
                ),
            }
            for doc_name, completed in checklist.items()
        ]

        return {
            "ot_id": ot_id,
            "total_documents": total_count,
            "completed_documents": completed_count,
            "completion_percentage": round(completion_percentage, 2),
            "documents": documents,
        }

    # ========================================================================
    # CUADRILLA OPERATIONS
    # ========================================================================

    async def get_cuadrillas(
        self,
        filters: Optional[Dict[str, any]] = None,
    ) -> List[Dict]:
        """
        Simulate TELCOS API GET /cuadrillas endpoint.
        
        Returns list of crews with optional filtering by type.
        
        Args:
            filters: Optional filter dict with keys:
                - type: Filter by crew type ("PRINCIPAL" or "RESERVA")
                
        Returns:
            List[Dict]: List of crew dictionaries matching filters
            
        Example:
            >>> cuadrillas = await service.get_cuadrillas()
            >>> len(cuadrillas)
            10
            
            >>> principal = await service.get_cuadrillas({"type": "PRINCIPAL"})
            >>> all(c["type"] == "PRINCIPAL" for c in principal)
            True
        """
        self.call_count += 1

        # Simulate latency
        await self._simulate_latency()

        # Start with all cuadrillas
        cuadrillas = [crew.copy() for crew in MOCK_CUADRILLAS]

        # Apply filters if provided
        if filters:
            crew_type = filters.get("type")
            if crew_type:
                cuadrillas = [c for c in cuadrillas if c["type"] == crew_type]

        return cuadrillas

    # ========================================================================
    # STATISTICS & MONITORING
    # ========================================================================

    async def get_health(self) -> Dict:
        """
        Get mock service health status.
        
        Returns statistics about API calls and failures.
        
        Returns:
            Dict: Health status with keys:
                - status: str, "healthy" or "degraded"
                - call_count: int, total API calls made
                - failure_count: int, simulated failures
                - failure_rate: float, actual failure percentage
                - latency_ms: int, configured latency
                - uptime_seconds: float, seconds since service initialized
                
        Example:
            >>> health = await service.get_health()
            >>> health["status"]
            "healthy"
        """
        actual_failure_rate = (
            (self.failure_count / self.call_count * 100)
            if self.call_count > 0
            else 0
        )

        return {
            "status": "healthy",
            "call_count": self.call_count,
            "failure_count": self.failure_count,
            "failure_rate": round(actual_failure_rate, 2),
            "latency_ms": self.latency_ms,
            "uptime_seconds": asyncio.get_event_loop().time(),
        }

    async def reset_stats(self) -> Dict:
        """
        Reset call and failure counters for testing.
        
        Useful for test isolation and performance measurement.
        
        Returns:
            Dict: Confirmation message
            
        Example:
            >>> await service.reset_stats()
            {"message": "Statistics reset"}
        """
        self.call_count = 0
        self.failure_count = 0
        return {"message": "Statistics reset"}


# ============================================================================
# SINGLETON ACCESS FUNCTION
# ============================================================================

@lru_cache(maxsize=1)
def get_mock_service() -> MockApiService:
    """
    Get singleton instance of MockApiService using lru_cache.
    
    The @lru_cache decorator ensures only one instance is created
    and reused throughout the application lifecycle.
    
    Returns:
        MockApiService: Singleton instance
        
    Example:
        >>> service1 = get_mock_service()
        >>> service2 = get_mock_service()
        >>> service1 is service2
        True
    """
    return MockApiService.get_instance()

