"""Service for integrating with TELCOS API with mock mode support."""

import httpx
import asyncio
from typing import Optional, Dict, Any, List
import os
from backend.services.mock_api_service import MockApiService


class TelcosService:
    """Service for handling TELCOS API calls with mock mode support."""
    
    def __init__(self, base_url: str, api_key: str, mock_mode: bool = False):
        """
        Initialize the TELCOS service.
        
        Args:
            base_url: Base URL for TELCOS API (ignored in mock mode)
            api_key: API key for authentication (ignored in mock mode)
            mock_mode: If True, use MockApiService instead of real API calls
        """
        self.base_url = base_url
        self.api_key = api_key
        self.mock_mode = mock_mode
        
        if mock_mode:
            self.mock_service = MockApiService(latency_ms=500)
        else:
            self.mock_service = None
        
        self.max_retries = 3
        self.backoff_factor = 2
    
    async def fetch_ots(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch OTs from TELCOS API or mock service.
        
        Args:
            limit: Maximum number of OTs to fetch
        
        Returns:
            List of OT dictionaries
        
        Raises:
            Exception: If all retry attempts fail
        """
        if self.mock_mode:
            return await self.mock_service.get_ots(limit=limit)
        
        # Real API call with retries
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/api/telcos/ots",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        params={"limit": limit},
                        timeout=10.0,
                    )
                    response.raise_for_status()
                    return response.json()
            except (httpx.HTTPError, httpx.RequestError) as e:
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    wait_time = self.backoff_factor ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Failed to fetch OTs after {self.max_retries} attempts: {str(e)}")
    
    async def update_ot_status(self, external_id: str, status: str) -> Dict[str, Any]:
        """
        Update OT status in TELCOS API or mock service.
        
        Args:
            external_id: External ID of the OT
            status: New status to set
        
        Returns:
            Response dictionary with success/error information
        
        Raises:
            Exception: If all retry attempts fail
        """
        if self.mock_mode:
            return await self.mock_service.update_status(external_id, status)
        
        # Real API call with retries
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/api/telcos/update_status",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={"external_id": external_id, "status": status},
                        timeout=10.0,
                    )
                    response.raise_for_status()
                    return response.json()
            except (httpx.HTTPError, httpx.RequestError) as e:
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    wait_time = self.backoff_factor ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Failed to update OT status after {self.max_retries} attempts: {str(e)}")
    
    async def verify_documents(self, ot_id: str) -> Dict[str, Any]:
        """
        Verify document count for OT in TelcoDrive API or mock service.
        
        Args:
            ot_id: ID of the OT
        
        Returns:
            Response dictionary with document count and status
        
        Raises:
            Exception: If all retry attempts fail
        """
        if self.mock_mode:
            return await self.mock_service.get_telcodrive_documents(ot_id)
        
        # Real API call with retries
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/api/telcodrive/documents",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        params={"ot_id": ot_id},
                        timeout=10.0,
                    )
                    response.raise_for_status()
                    return response.json()
            except (httpx.HTTPError, httpx.RequestError) as e:
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    wait_time = self.backoff_factor ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Failed to verify documents after {self.max_retries} attempts: {str(e)}")

