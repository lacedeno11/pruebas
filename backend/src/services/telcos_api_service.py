"""
Telcos API Service for PEI Platform (SYSTEM_MODE=PROD).

This service integrates with the real Telcos API for production deployments.
Includes error handling, retry logic with exponential backoff, and comprehensive logging.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)


class TelcosApiService:
    """
    Production API service for real Telcos API integration.

    This service communicates with the actual Telcos API to:
    - Fetch OT (work order) data
    - Update OT statuses
    - Retrieve TelcoDrive document information

    Features:
    - Async HTTP calls using httpx
    - Retry logic with exponential backoff (3 attempts)
    - Configurable timeout (30 seconds)
    - Comprehensive error handling and logging
    - Request/response logging for debugging
    """

    # API Configuration
    DEFAULT_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3
    RETRY_BACKOFF_FACTOR = 2  # exponential backoff: 1s, 2s, 4s

    def __init__(self, base_url: str | None = None):
        """
        Initialize the Telcos API service.

        Args:
            base_url (str, optional): Base URL for Telcos API. If not provided,
                uses URL from settings or raises error.
        """
        self.base_url = base_url or getattr(
            settings, "telcos_api_base_url", "https://api.telcos.example.com"
        )
        self.timeout = self.DEFAULT_TIMEOUT
        logger.info(f"TelcosApiService initialized with base_url: {self.base_url}")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Make an HTTP request with retry logic and error handling.

        Args:
            method (str): HTTP method (GET, POST, PATCH, etc.)
            endpoint (str): API endpoint (relative path)
            **kwargs: Additional arguments to pass to httpx.AsyncClient

        Returns:
            dict: Parsed JSON response

        Raises:
            httpx.HTTPError: If all retry attempts fail
            ValueError: If response is not valid JSON
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        last_exception = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.debug(
                    f"API Request (Attempt {attempt}/{self.MAX_RETRIES}): "
                    f"{method} {url}"
                )

                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    headers=self._get_headers(),
                ) as client:
                    response = await client.request(method, url, **kwargs)
                    response.raise_for_status()

                    result = response.json()
                    logger.info(
                        f"API Response: {method} {url} - Status {response.status_code}"
                    )
                    return result

            except httpx.ConnectError as e:
                last_exception = e
                logger.warning(
                    f"API Connection Error (Attempt {attempt}/{self.MAX_RETRIES}): {str(e)}"
                )
                if attempt < self.MAX_RETRIES:
                    backoff_time = self.RETRY_BACKOFF_FACTOR ** (attempt - 1)
                    logger.info(f"Retrying in {backoff_time} seconds...")
                    await asyncio.sleep(backoff_time)

            except httpx.HTTPStatusError as e:
                last_exception = e
                logger.warning(
                    f"API HTTP Error (Attempt {attempt}/{self.MAX_RETRIES}): "
                    f"{e.response.status_code} - {str(e)}"
                )
                # Don't retry on 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    raise
                # Retry on 5xx errors (server errors)
                if attempt < self.MAX_RETRIES:
                    backoff_time = self.RETRY_BACKOFF_FACTOR ** (attempt - 1)
                    logger.info(f"Retrying in {backoff_time} seconds...")
                    await asyncio.sleep(backoff_time)

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(
                    f"API Timeout (Attempt {attempt}/{self.MAX_RETRIES}): {str(e)}"
                )
                if attempt < self.MAX_RETRIES:
                    backoff_time = self.RETRY_BACKOFF_FACTOR ** (attempt - 1)
                    logger.info(f"Retrying in {backoff_time} seconds...")
                    await asyncio.sleep(backoff_time)

            except Exception as e:
                last_exception = e
                logger.error(
                    f"API Unexpected Error (Attempt {attempt}/{self.MAX_RETRIES}): "
                    f"{type(e).__name__}: {str(e)}"
                )
                if attempt < self.MAX_RETRIES:
                    backoff_time = self.RETRY_BACKOFF_FACTOR ** (attempt - 1)
                    await asyncio.sleep(backoff_time)

        # All retries failed
        error_msg = (
            f"Failed to complete API request after {self.MAX_RETRIES} attempts: {str(last_exception)}"
        )
        logger.error(f"API Request Failed: {method} {url} - {error_msg}")
        raise last_exception or RuntimeError(error_msg)

    def _get_headers(self) -> dict[str, str]:
        """
        Get standard HTTP headers for API requests.

        Includes authentication and content-type headers.

        Returns:
            dict: HTTP headers
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "PEIAgentPlatform/1.0",
        }

        # Add authentication if available
        if hasattr(settings, "telcos_api_token"):
            headers["Authorization"] = f"Bearer {settings.telcos_api_token}"

        return headers

    async def get_ots(self) -> list[dict[str, Any]]:
        """
        Fetch OTs from the Telcos API.

        Makes a GET request to /api/ots endpoint and returns the list of
        work orders. The API response should match the format of MockApiService
        for compatibility with agents.

        Returns:
            list[dict]: List of OT dictionaries with keys:
                - external_id (str): Unique ID from Telcos system
                - cliente_id (str): Client identifier
                - login_id (str): Login identifier
                - lat (float): Latitude
                - long (float): Longitude
                - project_type (str): PUBLICO, PRIVADO, or TERCERIZADO
                - status (str): OT status

        Raises:
            httpx.HTTPError: If API request fails after retries
        """
        try:
            response = await self._make_request("GET", "/api/ots")
            ots = response.get("data", []) if isinstance(response, dict) else response

            logger.info(f"Fetched {len(ots)} OTs from Telcos API")
            return ots

        except Exception as e:
            logger.error(f"Error fetching OTs from Telcos API: {str(e)}")
            raise

    async def update_status(
        self, ot_external_id: str, new_status: str
    ) -> dict[str, Any]:
        """
        Update the status of an OT in the Telcos API.

        Makes a PATCH request to /api/ots/{ot_id}/status endpoint to update
        the work order status.

        Args:
            ot_external_id (str): The external ID of the OT to update
            new_status (str): The new status to set (PREPLANIFICADA, PLANIFICADA, etc.)

        Returns:
            dict: Response with keys:
                - success (bool): True if update succeeded
                - data (dict): Updated OT data
                - error (str, optional): Error message if unsuccessful

        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            endpoint = f"/api/ots/{ot_external_id}/status"
            response = await self._make_request(
                "PATCH",
                endpoint,
                json={"status": new_status},
            )

            logger.info(f"Updated OT {ot_external_id} to status {new_status}")
            return {
                "success": True,
                "data": response,
            }

        except Exception as e:
            logger.error(
                f"Error updating OT {ot_external_id} status: {str(e)}"
            )
            return {
                "success": False,
                "error": str(e),
            }

    async def get_telcodrive_documents(
        self, ot_external_id: str
    ) -> dict[str, Any]:
        """
        Get TelcoDrive documents for an OT.

        Makes a GET request to /api/telcodrive/{ot_id}/documents endpoint to
        retrieve associated documents. This is critical for PUBLICO projects
        which must have 29 documents before moving to FINALIZADA status.

        Args:
            ot_external_id (str): The external ID of the OT

        Returns:
            dict: Response with keys:
                - success (bool): Always True for successful response
                - document_count (int): Number of documents
                - documents (list): List of document metadata
                - ot_external_id (str): The queried OT ID

        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            endpoint = f"/api/telcodrive/{ot_external_id}/documents"
            response = await self._make_request("GET", endpoint)

            document_count = len(response.get("documents", []))
            logger.info(
                f"Retrieved {document_count} TelcoDrive documents for OT {ot_external_id}"
            )

            return {
                "success": True,
                "document_count": document_count,
                "documents": response.get("documents", []),
                "ot_external_id": ot_external_id,
            }

        except Exception as e:
            logger.error(
                f"Error retrieving TelcoDrive documents for OT {ot_external_id}: {str(e)}"
            )
            return {
                "success": False,
                "document_count": 0,
                "documents": [],
                "error": str(e),
            }

    async def get_ot_details(self, ot_external_id: str) -> dict[str, Any]:
        """
        Get detailed information for a specific OT.

        Args:
            ot_external_id (str): The external ID of the OT

        Returns:
            dict: OT details or error response
        """
        try:
            endpoint = f"/api/ots/{ot_external_id}"
            response = await self._make_request("GET", endpoint)

            return {
                "success": True,
                "data": response,
            }

        except Exception as e:
            logger.error(f"Error retrieving OT details for {ot_external_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    async def health_check(self) -> dict[str, Any]:
        """
        Check the health status of the Telcos API.

        Makes a GET request to /health endpoint to verify API connectivity.

        Returns:
            dict: Health status response
        """
        try:
            response = await self._make_request("GET", "/health")
            logger.info("Telcos API health check passed")
            return response

        except Exception as e:
            logger.error(f"Telcos API health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }

