"""
Insurer Connector Agent (UC-OP-09)

This module implements the Insurer Connector Agent for the Policy Validation Copilot system,
providing external query preparation, multi-channel support (API/portal/email), response capture/normalization,
evidence persistence, and timeout/retry mechanisms.
"""

from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import logging
import asyncio
import json
import aiohttp
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from dataclasses import dataclass
from enum import Enum
import hashlib
import uuid

from ..state import PolicyValidationState, EvidencePack, EvidenceItem
from ..database import (
    EvidencePackRepository, EvidenceItemRepository, AuditLogRepository,
    get_repository_factory
)
from ..guardrails import create_security_context, evaluate_payload_security

logger = logging.getLogger(__name__)


class CommunicationChannel(str, Enum):
    """Communication channels for insurer interaction"""
    API = "API"
    PORTAL = "PORTAL"
    EMAIL = "EMAIL"
    WEBHOOK = "WEBHOOK"
    FTP = "FTP"
    MANUAL = "MANUAL"


class QueryStatus(str, Enum):
    """Status of external queries"""
    PENDING = "PENDING"
    SENT = "SENT"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class ResponseFormat(str, Enum):
    """Expected response formats"""
    JSON = "JSON"
    XML = "XML"
    PDF = "PDF"
    HTML = "HTML"
    TEXT = "TEXT"
    CSV = "CSV"
    EXCEL = "EXCEL"


@dataclass
class InsurerConfig:
    """Configuration for insurer communication"""
    insurer_id: str
    name: str
    primary_channel: CommunicationChannel
    fallback_channels: List[CommunicationChannel]
    api_config: Optional[Dict[str, Any]] = None
    portal_config: Optional[Dict[str, Any]] = None
    email_config: Optional[Dict[str, Any]] = None
    timeout_seconds: int = 300
    max_retries: int = 3
    retry_delay_seconds: int = 30
    expected_response_format: ResponseFormat = ResponseFormat.JSON
    authentication: Optional[Dict[str, Any]] = None


@dataclass
class ExternalQuery:
    """External query to insurer"""
    query_id: str
    case_id: str
    insurer_id: str
    channel: CommunicationChannel
    query_type: str
    query_data: Dict[str, Any]
    expected_format: ResponseFormat
    timeout_seconds: int
    max_retries: int
    created_at: datetime
    status: QueryStatus = QueryStatus.PENDING
    attempts: int = 0
    last_attempt_at: Optional[datetime] = None
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


@dataclass
class QueryResponse:
    """Response from external query"""
    query_id: str
    status: QueryStatus
    response_data: Optional[Dict[str, Any]]
    raw_response: Optional[str]
    response_format: ResponseFormat
    received_at: datetime
    processing_time_ms: int
    evidence_items: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class APIConnector:
    """API-based communication with insurers"""
    
    def __init__(self, config: InsurerConfig):
        self.config = config
        self.api_config = config.api_config or {}
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
            headers=self._get_default_headers()
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default HTTP headers"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "PolicyCopilot/1.0",
            "Accept": "application/json"
        }
        
        # Add authentication headers
        auth_config = self.config.authentication or {}
        if auth_config.get("type") == "bearer":
            headers["Authorization"] = f"Bearer {auth_config.get('token')}"
        elif auth_config.get("type") == "api_key":
            headers[auth_config.get("header", "X-API-Key")] = auth_config.get("key")
        
        return headers
    
    async def send_query(self, query: ExternalQuery) -> QueryResponse:
        """Send query via API"""
        start_time = datetime.utcnow()
        
        try:
            # Prepare API request
            url = self._build_api_url(query)
            payload = self._prepare_api_payload(query)
            
            # Send request
            async with self.session.post(url, json=payload) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    # Parse response
                    response_data = await self._parse_api_response(response_text, query.expected_format)
                    evidence_items = await self._extract_evidence_from_response(response_data, query)
                    
                    processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                    
                    return QueryResponse(
                        query_id=query.query_id,
                        status=QueryStatus.COMPLETED,
                        response_data=response_data,
                        raw_response=response_text,
                        response_format=query.expected_format,
                        received_at=datetime.utcnow(),
                        processing_time_ms=int(processing_time),
                        evidence_items=evidence_items,
                        metadata={
                            "http_status": response.status,
                            "content_type": response.headers.get("Content-Type"),
                            "response_size": len(response_text)
                        }
                    )
                else:
                    raise Exception(f"API request failed with status {response.status}: {response_text}")
        
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return QueryResponse(
                query_id=query.query_id,
                status=QueryStatus.FAILED,
                response_data=None,
                raw_response=None,
                response_format=query.expected_format,
                received_at=datetime.utcnow(),
                processing_time_ms=int(processing_time),
                evidence_items=[],
                metadata={"error": str(e)}
            )
    
    def _build_api_url(self, query: ExternalQuery) -> str:
        """Build API URL for query"""
        base_url = self.api_config.get("base_url", "")
        endpoint = self.api_config.get("endpoints", {}).get(query.query_type, "/query")
        
        return f"{base_url.rstrip('/')}{endpoint}"
    
    def _prepare_api_payload(self, query: ExternalQuery) -> Dict[str, Any]:
        """Prepare API payload"""
        payload = {
            "query_id": query.query_id,
            "case_id": query.case_id,
            "query_type": query.query_type,
            "timestamp": query.created_at.isoformat(),
            **query.query_data
        }
        
        return payload
    
    async def _parse_api_response(self, response_text: str, expected_format: ResponseFormat) -> Dict[str, Any]:
        """Parse API response based on expected format"""
        
        if expected_format == ResponseFormat.JSON:
            return json.loads(response_text)
        elif expected_format == ResponseFormat.XML:
            # Would use XML parser in production
            return {"raw_xml": response_text}
        elif expected_format == ResponseFormat.TEXT:
            return {"text_content": response_text}
        else:
            return {"raw_content": response_text}
    
    async def _extract_evidence_from_response(
        self, 
        response_data: Dict[str, Any], 
        query: ExternalQuery
    ) -> List[Dict[str, Any]]:
        """Extract evidence items from API response"""
        
        evidence_items = []
        
        # Extract based on response structure (simplified)
        if "evidence" in response_data:
            for item in response_data["evidence"]:
                evidence_item = {
                    "doc_id": f"EXT_{query.insurer_id}_{item.get('id', uuid.uuid4())}",
                    "version": item.get("version", "1.0"),
                    "checksum": hashlib.sha256(str(item).encode()).hexdigest(),
                    "pointer": f"api://{query.insurer_id}/{query.query_type}#{item.get('id')}",
                    "excerpt": item.get("content", str(item)[:500]),
                    "table_ref": item.get("table_ref"),
                    "relevance_score": item.get("relevance", 0.8),
                    "confidence_score": item.get("confidence", 0.7)
                }
                evidence_items.append(evidence_item)
        
        # Fallback: create evidence from entire response
        if not evidence_items and response_data:
            evidence_item = {
                "doc_id": f"EXT_{query.insurer_id}_{query.query_id}",
                "version": "1.0",
                "checksum": hashlib.sha256(str(response_data).encode()).hexdigest(),
                "pointer": f"api://{query.insurer_id}/{query.query_type}",
                "excerpt": str(response_data)[:500],
                "table_ref": None,
                "relevance_score": 0.6,
                "confidence_score": 0.5
            }
            evidence_items.append(evidence_item)
        
        return evidence_items


class EmailConnector:
    """Email-based communication with insurers"""
    
    def __init__(self, config: InsurerConfig):
        self.config = config
        self.email_config = config.email_config or {}
    
    async def send_query(self, query: ExternalQuery) -> QueryResponse:
        """Send query via email"""
        start_time = datetime.utcnow()
        
        try:
            # Prepare email
            subject = self._build_email_subject(query)
            body = self._build_email_body(query)
            
            # Send email
            await self._send_email(
                to_address=self.email_config.get("to_address"),
                subject=subject,
                body=body,
                query_id=query.query_id
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Email queries are typically asynchronous
            return QueryResponse(
                query_id=query.query_id,
                status=QueryStatus.SENT,
                response_data=None,
                raw_response=None,
                response_format=query.expected_format,
                received_at=datetime.utcnow(),
                processing_time_ms=int(processing_time),
                evidence_items=[],
                metadata={
                    "email_sent": True,
                    "to_address": self.email_config.get("to_address"),
                    "subject": subject
                }
            )
        
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return QueryResponse(
                query_id=query.query_id,
                status=QueryStatus.FAILED,
                response_data=None,
                raw_response=None,
                response_format=query.expected_format,
                received_at=datetime.utcnow(),
                processing_time_ms=int(processing_time),
                evidence_items=[],
                metadata={"error": str(e)}
            )
    
    def _build_email_subject(self, query: ExternalQuery) -> str:
        """Build email subject"""
        return f"Policy Query - Case {query.case_id} - {query.query_type}"
    
    def _build_email_body(self, query: ExternalQuery) -> str:
        """Build email body"""
        body = f"""
Dear {self.config.name} Team,

We are requesting information for the following policy validation case:

Case ID: {query.case_id}
Query ID: {query.query_id}
Query Type: {query.query_type}
Date: {query.created_at.strftime('%Y-%m-%d %H:%M:%S')}

Query Details:
{json.dumps(query.query_data, indent=2)}

Please provide the requested information at your earliest convenience.

Best regards,
Policy Validation Team
        """.strip()
        
        return body
    
    async def _send_email(self, to_address: str, subject: str, body: str, query_id: str) -> None:
        """Send email (mock implementation)"""
        
        # In production, would use actual SMTP
        logger.info(f"Email sent for query {query_id} to {to_address}: {subject}")
        
        # Mock email sending
        await asyncio.sleep(0.1)


class PortalConnector:
    """Portal-based communication with insurers"""
    
    def __init__(self, config: InsurerConfig):
        self.config = config
        self.portal_config = config.portal_config or {}
    
    async def send_query(self, query: ExternalQuery) -> QueryResponse:
        """Send query via portal (typically involves web scraping or RPA)"""
        start_time = datetime.utcnow()
        
        try:
            # Portal interaction would involve web automation
            # This is a simplified mock implementation
            
            await asyncio.sleep(2)  # Simulate portal interaction time
            
            # Mock portal response
            mock_response = {
                "status": "submitted",
                "reference_number": f"REF_{query.query_id[:8]}",
                "estimated_response_time": "24-48 hours",
                "portal_url": self.portal_config.get("url", "https://portal.insurer.com")
            }
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return QueryResponse(
                query_id=query.query_id,
                status=QueryStatus.SENT,
                response_data=mock_response,
                raw_response=json.dumps(mock_response),
                response_format=query.expected_format,
                received_at=datetime.utcnow(),
                processing_time_ms=int(processing_time),
                evidence_items=[],
                metadata={
                    "portal_submitted": True,
                    "reference_number": mock_response["reference_number"]
                }
            )
        
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return QueryResponse(
                query_id=query.query_id,
                status=QueryStatus.FAILED,
                response_data=None,
                raw_response=None,
                response_format=query.expected_format,
                received_at=datetime.utcnow(),
                processing_time_ms=int(processing_time),
                evidence_items=[],
                metadata={"error": str(e)}
            )


class InsurerConnectorAgent:
    """
    Insurer Connector Agent implementing UC-OP-09.
    
    Handles external communication with insurers through multiple channels,
    manages query lifecycle, captures responses, and persists evidence.
    """
    
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        self.repo_factory = get_repository_factory()
        
        # Insurer configurations
        self.insurer_configs: Dict[str, InsurerConfig] = {}
        self._initialize_insurer_configs()
        
        # Active queries tracking
        self.active_queries: Dict[str, ExternalQuery] = {}
        
        # Statistics
        self.query_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "timeout_queries": 0,
            "by_channel": {channel.value: 0 for channel in CommunicationChannel}
        }
    
    def _initialize_insurer_configs(self):
        """Initialize insurer configurations"""
        
        # Example insurer configurations
        configs = [
            InsurerConfig(
                insurer_id="INS001",
                name="MegaHealth Insurance",
                primary_channel=CommunicationChannel.API,
                fallback_channels=[CommunicationChannel.EMAIL],
                api_config={
                    "base_url": "https://api.megahealth.com/v1",
                    "endpoints": {
                        "policy_check": "/policy/check",
                        "coverage_inquiry": "/coverage/inquiry",
                        "claim_status": "/claims/status"
                    }
                },
                email_config={
                    "to_address": "api-support@megahealth.com",
                    "from_address": "policy-validation@company.com"
                },
                timeout_seconds=300,
                max_retries=3,
                expected_response_format=ResponseFormat.JSON,
                authentication={
                    "type": "bearer",
                    "token": "mock_bearer_token_123"
                }
            ),
            
            InsurerConfig(
                insurer_id="INS002",
                name="SafeCare Insurance",
                primary_channel=CommunicationChannel.PORTAL,
                fallback_channels=[CommunicationChannel.EMAIL],
                portal_config={
                    "url": "https://portal.safecare.com",
                    "login_url": "https://portal.safecare.com/login",
                    "query_endpoint": "/submit-inquiry"
                },
                email_config={
                    "to_address": "inquiries@safecare.com",
                    "from_address": "policy-validation@company.com"
                },
                timeout_seconds=600,
                max_retries=2,
                expected_response_format=ResponseFormat.HTML
            ),
            
            InsurerConfig(
                insurer_id="INS003",
                name="QuickCare Insurance",
                primary_channel=CommunicationChannel.EMAIL,
                fallback_channels=[],
                email_config={
                    "to_address": "policy-queries@quickcare.com",
                    "from_address": "policy-validation@company.com"
                },
                timeout_seconds=86400,  # 24 hours for email
                max_retries=1,
                expected_response_format=ResponseFormat.TEXT
            )
        ]
        
        for config in configs:
            self.insurer_configs[config.insurer_id] = config
    
    async def query_insurer(
        self, 
        state: PolicyValidationState,
        query_type: str = "policy_check",
        force_channel: Optional[CommunicationChannel] = None
    ) -> PolicyValidationState:
        """
        Main entry point for querying insurers.
        
        Args:
            state: Current policy validation state
            query_type: Type of query to send
            force_channel: Force specific communication channel
            
        Returns:
            Updated state with query results
        """
        start_time = datetime.utcnow()
        
        try:
            # Extract case information
            case = state["case"]
            case_id = case["case_id"]
            insurer_id = case.get("insurer_id")
            
            logger.info(f"Starting insurer query for case {case_id}, insurer {insurer_id}")
            
            # Get insurer configuration
            insurer_config = self.insurer_configs.get(insurer_id)
            if not insurer_config:
                raise Exception(f"No configuration found for insurer {insurer_id}")
            
            # Prepare query
            query = await self._prepare_query(case, query_type, insurer_config, force_channel)
            
            # Execute query with retry logic
            response = await self._execute_query_with_retry(query, insurer_config)
            
            # Process response and update evidence pack
            if response.status == QueryStatus.COMPLETED and response.evidence_items:
                await self._update_evidence_pack(state, response)
            
            # Update state with query information
            if "external_queries" not in state:
                state["external_queries"] = []
            
            state["external_queries"].append({
                "query_id": query.query_id,
                "insurer_id": insurer_id,
                "query_type": query_type,
                "channel": query.channel.value,
                "status": response.status.value,
                "created_at": query.created_at,
                "completed_at": response.received_at,
                "processing_time_ms": response.processing_time_ms,
                "evidence_items_count": len(response.evidence_items)
            })
            
            # Log query audit trail
            await self._log_query_audit(case_id, query, response)
            
            # Update statistics
            await self._update_query_statistics(response)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.info(
                f"Insurer query completed for case {case_id}: "
                f"status={response.status.value}, "
                f"evidence_items={len(response.evidence_items)}, "
                f"time={processing_time}ms"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"Insurer query failed for case {case.get('case_id', 'unknown')}: {e}")
            
            # Add error information to state
            if "external_queries" not in state:
                state["external_queries"] = []
            
            state["external_queries"].append({
                "query_id": str(uuid.uuid4()),
                "insurer_id": case.get("insurer_id"),
                "query_type": query_type,
                "channel": "UNKNOWN",
                "status": "FAILED",
                "created_at": datetime.utcnow(),
                "completed_at": datetime.utcnow(),
                "processing_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                "error_message": str(e),
                "evidence_items_count": 0
            })
            
            raise
    
    async def _prepare_query(
        self,
        case: Dict[str, Any],
        query_type: str,
        insurer_config: InsurerConfig,
        force_channel: Optional[CommunicationChannel] = None
    ) -> ExternalQuery:
        """Prepare external query"""
        
        # Determine communication channel
        channel = force_channel or insurer_config.primary_channel
        
        # Build query data
        query_data = await self._build_query_data(case, query_type)
        
        # Create query
        query = ExternalQuery(
            query_id=str(uuid.uuid4()),
            case_id=case["case_id"],
            insurer_id=insurer_config.insurer_id,
            channel=channel,
            query_type=query_type,
            query_data=query_data,
            expected_format=insurer_config.expected_response_format,
            timeout_seconds=insurer_config.timeout_seconds,
            max_retries=insurer_config.max_retries,
            created_at=datetime.utcnow()
        )
        
        # Track active query
        self.active_queries[query.query_id] = query
        
        return query
    
    async def _build_query_data(self, case: Dict[str, Any], query_type: str) -> Dict[str, Any]:
        """Build query data based on case and query type"""
        
        base_data = {
            "customer_id": case.get("customer_id"),
            "contract_id": case.get("contract_id"),
            "plan_id": case.get("plan_id"),
            "service_code": case.get("service_code"),
            "service_date": case.get("service_date"),
            "service_amount": case.get("service_amount"),
            "provider_id": case.get("provider_id")
        }
        
        # Add query-specific data
        if query_type == "policy_check":
            base_data.update({
                "check_type": "coverage_verification",
                "diagnosis_codes": case.get("diagnosis_codes", []),
                "procedure_codes": case.get("procedure_codes", [])
            })
        elif query_type == "coverage_inquiry":
            base_data.update({
                "inquiry_type": "benefit_verification",
                "service_category": self._categorize_service(case.get("service_code", ""))
            })
        elif query_type == "claim_status":
            base_data.update({
                "claim_number": case.get("claim_number"),
                "status_check": True
            })
        
        return base_data
    
    def _categorize_service(self, service_code: str) -> str:
        """Categorize service code for query"""
        if not service_code:
            return "GENERAL"
        
        service_upper = service_code.upper()
        
        if "EMERGENCY" in service_upper:
            return "EMERGENCY"
        elif "SURGERY" in service_upper:
            return "SURGICAL"
        elif "CONSULTATION" in service_upper:
            return "CONSULTATION"
        elif "DIAGNOSTIC" in service_upper:
            return "DIAGNOSTIC"
        else:
            return "GENERAL"
    
    async def _execute_query_with_retry(
        self, 
        query: ExternalQuery, 
        insurer_config: InsurerConfig
    ) -> QueryResponse:
        """Execute query with retry logic and fallback channels"""
        
        channels_to_try = [query.channel] + insurer_config.fallback_channels
        last_response = None
        
        for channel in channels_to_try:
            query.channel = channel
            
            for attempt in range(query.max_retries + 1):
                query.attempts = attempt + 1
                query.last_attempt_at = datetime.utcnow()
                
                try:
                    # Execute query based on channel
                    response = await self._execute_query_by_channel(query, insurer_config)
                    
                    if response.status in [QueryStatus.COMPLETED, QueryStatus.SENT]:
                        query.status = response.status
                        query.completed_at = response.received_at
                        query.response_data = response.response_data
                        return response
                    
                    last_response = response
                    
                except Exception as e:
                    logger.warning(f"Query attempt {attempt + 1} failed for {query.query_id}: {e}")
                    
                    if attempt < query.max_retries:
                        await asyncio.sleep(insurer_config.retry_delay_seconds)
                    
                    last_response = QueryResponse(
                        query_id=query.query_id,
                        status=QueryStatus.FAILED,
                        response_data=None,
                        raw_response=None,
                        response_format=query.expected_format,
                        received_at=datetime.utcnow(),
                        processing_time_ms=0,
                        evidence_items=[],
                        metadata={"error": str(e), "attempt": attempt + 1}
                    )
        
        # All attempts failed
        query.status = QueryStatus.FAILED
        query.error_message = "All retry attempts exhausted"
        
        return last_response or QueryResponse(
            query_id=query.query_id,
            status=QueryStatus.FAILED,
            response_data=None,
            raw_response=None,
            response_format=query.expected_format,
            received_at=datetime.utcnow(),
            processing_time_ms=0,
            evidence_items=[],
            metadata={"error": "All retry attempts exhausted"}
        )
    
    async def _execute_query_by_channel(
        self, 
        query: ExternalQuery, 
        insurer_config: InsurerConfig
    ) -> QueryResponse:
        """Execute query using specific channel"""
        
        if query.channel == CommunicationChannel.API:
            async with APIConnector(insurer_config) as connector:
                return await connector.send_query(query)
        
        elif query.channel == CommunicationChannel.EMAIL:
            connector = EmailConnector(insurer_config)
            return await connector.send_query(query)
        
        elif query.channel == CommunicationChannel.PORTAL:
            connector = PortalConnector(insurer_config)
            return await connector.send_query(query)
        
        else:
            raise Exception(f"Unsupported communication channel: {query.channel}")
    
    async def _update_evidence_pack(
        self, 
        state: PolicyValidationState, 
        response: QueryResponse
    ) -> None:
        """Update evidence pack with query response"""
        
        if "evidence_pack" not in state:
            state["evidence_pack"] = {
                "items": [],
                "coverage_score": 0.0,
                "conflicts_detected": False,
                "missing_sources": [],
                "retrieval_method": "EXTERNAL_QUERY",
                "retrieval_timestamp": datetime.utcnow()
            }
        
        # Add evidence items from response
        for evidence_item in response.evidence_items:
            state["evidence_pack"]["items"].append(evidence_item)
        
        # Update retrieval metadata
        state["evidence_pack"]["external_query_count"] = state["evidence_pack"].get("external_query_count", 0) + 1
        state["evidence_pack"]["last_external_query"] = response.received_at
    
    async def _log_query_audit(
        self,
        case_id: str,
        query: ExternalQuery,
        response: QueryResponse
    ) -> None:
        """Log query audit trail"""
        
        audit_repo = self.repo_factory.audit_log_repository()
        
        audit_data = {
            "case_id": case_id,
            "event_type": "EXTERNAL_QUERY",
            "event_category": "SYSTEM",
            "event_description": f"External query to {query.insurer_id} via {query.channel.value}",
            "user_id": "SYSTEM",
            "event_data": {
                "query_id": query.query_id,
                "insurer_id": query.insurer_id,
                "query_type": query.query_type,
                "channel": query.channel.value,
                "status": response.status.value,
                "attempts": query.attempts,
                "evidence_items_count": len(response.evidence_items),
                "processing_time_ms": response.processing_time_ms
            },
            "processing_time_ms": response.processing_time_ms
        }
        
        try:
            audit_repo.create(**audit_data)
        except Exception as e:
            logger.error(f"Failed to log query audit: {e}")
    
    async def _update_query_statistics(self, response: QueryResponse) -> None:
        """Update query statistics"""
        
        self.query_stats["total_queries"] += 1
        
        if response.status == QueryStatus.COMPLETED:
            self.query_stats["successful_queries"] += 1
        elif response.status == QueryStatus.FAILED:
            self.query_stats["failed_queries"] += 1
        elif response.status == QueryStatus.TIMEOUT:
            self.query_stats["timeout_queries"] += 1
        
        # Update channel statistics
        query = self.active_queries.get(response.query_id)
        if query:
            self.query_stats["by_channel"][query.channel.value] += 1
    
    async def handle_webhook_response(
        self, 
        insurer_id: str, 
        query_id: str, 
        response_data: Dict[str, Any]
    ) -> bool:
        """Handle webhook response from insurer"""
        
        try:
            # Find the original query
            query = self.active_queries.get(query_id)
            if not query:
                logger.warning(f"Received webhook for unknown query: {query_id}")
                return False
            
            # Process webhook response
            response = QueryResponse(
                query_id=query_id,
                status=QueryStatus.COMPLETED,
                response_data=response_data,
                raw_response=json.dumps(response_data),
                response_format=ResponseFormat.JSON,
                received_at=datetime.utcnow(),
                processing_time_ms=0,
                evidence_items=await self._extract_evidence_from_webhook(response_data, query),
                metadata={"source": "webhook", "insurer_id": insurer_id}
            )
            
            # Update query status
            query.status = QueryStatus.COMPLETED
            query.completed_at = response.received_at
            query.response_data = response_data
            
            # Log webhook receipt
            logger.info(f"Webhook response received for query {query_id} from {insurer_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle webhook response: {e}")
            return False
    
    async def _extract_evidence_from_webhook(
        self, 
        response_data: Dict[str, Any], 
        query: ExternalQuery
    ) -> List[Dict[str, Any]]:
        """Extract evidence from webhook response"""
        
        evidence_items = []
        
        # Extract evidence based on webhook structure
        if "results" in response_data:
            for item in response_data["results"]:
                evidence_item = {
                    "doc_id": f"WEBHOOK_{query.insurer_id}_{item.get('id', uuid.uuid4())}",
                    "version": item.get("version", "1.0"),
                    "checksum": hashlib.sha256(str(item).encode()).hexdigest(),
                    "pointer": f"webhook://{query.insurer_id}/{query.query_type}#{item.get('id')}",
                    "excerpt": item.get("summary", str(item)[:500]),
                    "table_ref": item.get("reference"),
                    "relevance_score": item.get("relevance", 0.8),
                    "confidence_score": item.get("confidence", 0.7)
                }
                evidence_items.append(evidence_item)
        
        return evidence_items
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """Get query statistics"""
        stats = self.query_stats.copy()
        
        if stats["total_queries"] > 0:
            stats["success_rate"] = stats["successful_queries"] / stats["total_queries"]
            stats["failure_rate"] = stats["failed_queries"] / stats["total_queries"]
            stats["timeout_rate"] = stats["timeout_queries"] / stats["total_queries"]
        
        return stats
    
    def get_active_queries(self) -> List[Dict[str, Any]]:
        """Get list of active queries"""
        return [
            {
                "query_id": query.query_id,
                "case_id": query.case_id,
                "insurer_id": query.insurer_id,
                "channel": query.channel.value,
                "status": query.status.value,
                "created_at": query.created_at,
                "attempts": query.attempts
            }
            for query in self.active_queries.values()
        ]
    
    def add_insurer_config(self, config: InsurerConfig) -> None:
        """Add insurer configuration"""
        self.insurer_configs[config.insurer_id] = config
        logger.info(f"Added insurer configuration: {config.insurer_id}")


# Factory function for creating insurer connector agent
def create_insurer_connector_agent(use_mock: bool = False) -> InsurerConnectorAgent:
    """
    Factory function to create insurer connector agent.
    
    Args:
        use_mock: Whether to use mock implementations
        
    Returns:
        Configured insurer connector agent
    """
    return InsurerConnectorAgent(use_mock=use_mock)
