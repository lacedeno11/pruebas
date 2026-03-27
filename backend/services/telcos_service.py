"""TELCOS API Service with fallback to mock API"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import httpx
from backend.config.settings import settings
from .mock_api_service import MockApiService

logger = logging.getLogger(__name__)


class TelcosService:
    """
    Service for interacting with TELCOS and TelcoDrive APIs.
    Switches between real API and mock API based on SYSTEM_MODE setting.
    """

    def __init__(self):
        """Initialize the TELCOS service"""
        self.system_mode = settings.SYSTEM_MODE
        self.api_base_url = settings.TELCOS_API_BASE_URL
        self.api_key = settings.TELCOS_API_KEY
        self.telcodrive_url = settings.TELCODRIVE_API_URL
        self.mock_service = MockApiService()
        self.max_retries = 3
        self.initial_delay = 1  # seconds

    async def fetch_ots(self) -> List[Dict[str, Any]]:
        """
        Fetch all OTs from TELCOS API or mock service.

        Returns:
            List of OT dictionaries

        Raises:
            Exception: If all retry attempts fail
        """
        if self.system_mode == "MOCK":
            logger.info("TelcosService: Using mock API for fetch_ots")
            return await self.mock_service.get_ots()

        logger.info("TelcosService: Fetching OTs from TELCOS API")
        return await self._fetch_with_retry(
            method="GET",
            endpoint="/ots",
        )

    async def update_ot_status(
        self,
        ot_id: str,
        new_status: str,
    ) -> Dict[str, Any]:
        """
        Update OT status in TELCOS API or mock service.

        Args:
            ot_id: OT ID
            new_status: New status to set

        Returns:
            Response dictionary with success status

        Raises:
            Exception: If all retry attempts fail
        """
        if self.system_mode == "MOCK":
            logger.info(
                f"TelcosService: Using mock API for update_ot_status "
                f"(OT: {ot_id}, Status: {new_status})"
            )
            return await self.mock_service.update_status(ot_id, new_status)

        logger.info(
            f"TelcosService: Updating OT {ot_id} to status {new_status} "
            f"in TELCOS API"
        )
        payload = {"status": new_status}
        return await self._fetch_with_retry(
            method="PUT",
            endpoint=f"/ots/{ot_id}",
            json=payload,
        )

    async def get_ot_documents(self, ot_id: str) -> Dict[str, Any]:
        """
        Get document count and list for OT from TelcoDrive API or mock service.

        Args:
            ot_id: OT ID

        Returns:
            Dictionary with document_count and documents list

        Raises:
            Exception: If all retry attempts fail
        """
        if self.system_mode == "MOCK":
            logger.info(
                f"TelcosService: Using mock API for get_ot_documents "
                f"(OT: {ot_id})"
            )
            return await self.mock_service.get_documents(ot_id)

        logger.info(f"TelcosService: Fetching documents for OT {ot_id}")
        return await self._fetch_with_retry(
            method="GET",
            endpoint=f"/documents/{ot_id}",
            base_url=self.telcodrive_url,
        )

    async def _fetch_with_retry(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with exponential backoff retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            json: JSON payload for POST/PUT requests
            base_url: Optional base URL override (for TelcoDrive)

        Returns:
            Response data as dictionary

        Raises:
            Exception: If all retries fail
        """
        url = f"{base_url or self.api_base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        delay = self.initial_delay

        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"TelcosService: Attempt {attempt + 1}/{self.max_retries} "
                    f"{method} {url}"
                )

                async with httpx.AsyncClient(timeout=30.0) as client:
                    if method == "GET":
                        response = await client.get(url, headers=headers)
                    elif method == "POST":
                        response = await client.post(
                            url, headers=headers, json=json
                        )
                    elif method == "PUT":
                        response = await client.put(
                            url, headers=headers, json=json
                        )
                    elif method == "DELETE":
                        response = await client.delete(url, headers=headers)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")

                    # Log response status
                    logger.debug(
                        f"TelcosService: Response status {response.status_code}"
                    )

                    # Check for success status codes
                    if response.status_code in [200, 201, 204]:
                        if response.status_code == 204:
                            return {"success": True}
                        return response.json()

                    # Log error status codes but continue retrying
                    if response.status_code >= 500:
                        logger.warning(
                            f"TelcosService: Server error "
                            f"{response.status_code}, retrying..."
                        )
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(delay)
                            delay *= 2  # Exponential backoff
                        continue

                    # Client errors (4xx) - don't retry
                    logger.error(
                        f"TelcosService: Client error {response.status_code}: "
                        f"{response.text}"
                    )
                    return {
                        "success": False,
                        "error": f"API error: {response.status_code}",
                    }

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.warning(
                    f"TelcosService: Network error on attempt "
                    f"{attempt + 1}/{self.max_retries}: {str(e)}"
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logger.error(
                        f"TelcosService: All {self.max_retries} retry attempts "
                        f"failed for {method} {url}"
                    )
                    return {
                        "success": False,
                        "error": f"Connection failed after {self.max_retries} "
                        f"retries: {str(e)}",
                    }

            except Exception as e:
                logger.error(
                    f"TelcosService: Unexpected error: {str(e)}"
                )
                return {
                    "success": False,
                    "error": f"Unexpected error: {str(e)}",
                }

        # Should not reach here, but return error if we do
        return {
            "success": False,
            "error": f"Failed after {self.max_retries} attempts",
        }

    async def validate_api_connection(self) -> bool:
        """
        Test API connection by fetching a small batch of OTs.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            logger.info(
                f"TelcosService: Testing API connection "
                f"(Mode: {self.system_mode})"
            )

            if self.system_mode == "MOCK":
                # Mock mode is always available
                return True

            # Try to fetch one OT to test connection
            result = await asyncio.wait_for(
                self._fetch_with_retry(
                    method="GET",
                    endpoint="/ots?limit=1",
                ),
                timeout=10.0,
            )

            is_valid = result.get("success") is not False
            logger.info(
                f"TelcosService: API connection test "
                f"{'successful' if is_valid else 'failed'}"
            )
            return is_valid

        except Exception as e:
            logger.error(f"TelcosService: API connection test failed: {str(e)}")
            return False

