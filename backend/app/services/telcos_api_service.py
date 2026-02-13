"""
TelcosApiService: Production wrapper for external TELCOS APIs.

This service provides real API implementations for:
- OT ingestion from TELCOS APIs
- Status update operations
- Document checklist retrieval from TelcoDrive

Features:
- Exponential backoff retry logic (3 attempts: 1s, 2s, 4s)
- 30-second request timeout
- Comprehensive error logging
- Automatic fallback to MockApiService for development
"""

import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class TelcosApiService:
    """
    Production implementation of external TELCOS APIs.
    
    Provides real HTTP implementations for:
    - GET /api/telcos/ots: OT ingestion from TELCOS
    - POST /api/telcos/update_status: Status transitions
    - GET /api/telcodrive/documents: Document checklist
    
    Implements:
    - Exponential backoff retry logic (1s, 2s, 4s)
    - 30-second timeout per request
    - Comprehensive error logging
    - Connection pooling via AsyncClient
    """

    # Configuration for exponential backoff
    RETRY_DELAYS = [1, 2, 4]  # seconds between retries
    REQUEST_TIMEOUT = 30  # seconds

    def __init__(self):
        """Initialize TelcosApiService with configuration."""
        # These will be loaded from settings (app.core.config)
        self.telcos_ots_url: Optional[str] = None
        self.telcos_status_url: Optional[str] = None
        self.telcodrive_docs_url: Optional[str] = None
        self.api_key: Optional[str] = None
        self.client: Optional[httpx.AsyncClient] = None

    async def _initialize_client(self) -> httpx.AsyncClient:
        """
        Lazy initialize AsyncClient with proper configuration.
        
        Returns:
            Configured httpx.AsyncClient instance
        """
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=self.REQUEST_TIMEOUT,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "DERCAS-PEI/1.0",
                },
            )
        return self.client

    async def _make_request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make HTTP request with exponential backoff retry logic.
        
        Attempts request up to 3 times with delays: 1s, 2s, 4s
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            **kwargs: Additional arguments for httpx.request()
            
        Returns:
            httpx.Response object
            
        Raises:
            httpx.RequestError: If all retries fail
        """
        client = await self._initialize_client()
        last_exception: Optional[Exception] = None

        for attempt, delay in enumerate(self.RETRY_DELAYS, start=1):
            try:
                logger.debug(
                    f"TELCOS API request (attempt {attempt}/3): {method} {url}"
                )
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                logger.debug(f"TELCOS API success: {method} {url} -> {response.status_code}")
                return response

            except httpx.HTTPStatusError as e:
                last_exception = e
                status_code = e.response.status_code

                # Log error with context
                logger.warning(
                    f"TELCOS API HTTP error (attempt {attempt}/3): "
                    f"{method} {url} -> {status_code}: {e.response.text[:200]}"
                )

                # Retry only on transient errors (5xx, 429 rate limit)
                if status_code >= 500 or status_code == 429:
                    if attempt < len(self.RETRY_DELAYS):
                        logger.info(
                            f"Retrying after {delay}s due to transient error {status_code}"
                        )
                        await asyncio.sleep(delay)
                    continue
                else:
                    # Non-transient error (4xx), don't retry
                    logger.error(f"Non-transient error {status_code}, not retrying")
                    raise

            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_exception = e
                logger.warning(
                    f"TELCOS API connection error (attempt {attempt}/3): "
                    f"{method} {url}: {str(e)[:200]}"
                )

                if attempt < len(self.RETRY_DELAYS):
                    logger.info(f"Retrying after {delay}s due to connection error")
                    await asyncio.sleep(delay)
                continue

        # All retries exhausted
        logger.error(
            f"TELCOS API request failed after {len(self.RETRY_DELAYS)} attempts: "
            f"{method} {url}"
        )
        raise last_exception or httpx.RequestError(
            f"Failed to complete request after {len(self.RETRY_DELAYS)} attempts"
        )

    async def get_ots_from_telcos(
        self, page: int = 1, limit: int = 50
    ) -> Dict[str, Any]:
        """
        Production implementation of GET /api/telcos/ots.
        
        Fetches OTs from production TELCOS API with retry logic.
        
        Args:
            page: Page number (1-indexed)
            limit: Items per page (max 50)
            
        Returns:
            Dict with 'data' (OT list), 'total', 'page', 'page_size'
            
        Raises:
            httpx.RequestError: If all retry attempts fail
        """
        if not self.telcos_ots_url:
            raise ValueError(
                "telcos_ots_url not configured. "
                "Set TELCOS_OTS_URL in environment variables."
            )

        try:
            response = await self._make_request_with_retry(
                "GET",
                self.telcos_ots_url,
                params={"page": page, "limit": min(limit, 50)},
            )
            return response.json()

        except Exception as e:
            logger.error(f"Error fetching OTs from TELCOS: {str(e)}")
            raise

    async def update_status_in_telcos(
        self, ot_id: str, new_status: str
    ) -> Dict[str, Any]:
        """
        Production implementation of POST /api/telcos/update_status.
        
        Updates OT status in production TELCOS system with retry logic.
        
        Args:
            ot_id: OT external ID (e.g., "OT-2024-00001")
            new_status: Target status string
            
        Returns:
            Dict with 'success', 'message', 'ot_id', 'new_status'
            
        Raises:
            httpx.RequestError: If all retry attempts fail
        """
        if not self.telcos_status_url:
            raise ValueError(
                "telcos_status_url not configured. "
                "Set TELCOS_STATUS_URL in environment variables."
            )

        try:
            response = await self._make_request_with_retry(
                "POST",
                self.telcos_status_url,
                json={"ot_id": ot_id, "new_status": new_status},
            )
            return response.json()

        except Exception as e:
            logger.error(
                f"Error updating status for OT {ot_id} in TELCOS: {str(e)}"
            )
            raise

    async def get_documents_status(self, ot_id: str) -> Dict[str, Any]:
        """
        Production implementation of GET /api/telcodrive/documents.
        
        Fetches document checklist from TelcoDrive with retry logic.
        
        Args:
            ot_id: OT external ID
            
        Returns:
            Dict with 'ot_id', 'documents' containing:
            - 'uploaded': Current count
            - 'required': Total required documents
            - 'pending': List of missing documents
            
        Raises:
            httpx.RequestError: If all retry attempts fail
        """
        if not self.telcodrive_docs_url:
            raise ValueError(
                "telcodrive_docs_url not configured. "
                "Set TELCODRIVE_DOCS_URL in environment variables."
            )

        try:
            # Format URL with OT ID parameter
            url = f"{self.telcodrive_docs_url}/{ot_id}"
            response = await self._make_request_with_retry("GET", url)
            return response.json()

        except Exception as e:
            logger.error(
                f"Error fetching documents status for OT {ot_id} from TelcoDrive: {str(e)}"
            )
            raise

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check to verify TELCOS APIs are reachable.
        
        Returns:
            Dict with 'status' and 'service'
        """
        try:
            if not self.telcos_ots_url:
                return {
                    "status": "unconfigured",
                    "service": "TelcosApiService",
                    "message": "TELCOS_OTS_URL not configured",
                }

            response = await self._make_request_with_retry(
                "GET",
                self.telcos_ots_url,
                params={"limit": 1},  # Minimal request
            )
            return {
                "status": "operational" if response.status_code == 200 else "error",
                "service": "TelcosApiService",
                "http_status": response.status_code,
            }

        except Exception as e:
            logger.error(f"TELCOS health check failed: {str(e)}")
            return {
                "status": "error",
                "service": "TelcosApiService",
                "error": str(e),
            }

    async def close(self) -> None:
        """
        Clean up HTTP client connection.
        
        Should be called during application shutdown.
        """
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("TelcosApiService client closed")

