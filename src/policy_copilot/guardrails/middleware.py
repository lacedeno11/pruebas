"""
Guardrails Middleware for Policy Validation Copilot

This module provides middleware integration for guardrails enforcement
across the entire system, including FastAPI middleware and LangGraph integration.
"""

import logging
import time
from typing import Any, Callable, Dict, Optional

from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..models.state import PolicyValidationState
from .service import GuardrailsService, GuardrailsConfig

logger = logging.getLogger(__name__)


class GuardrailsMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for guardrails enforcement.
    
    Applies security controls to all HTTP requests and responses
    before they reach the application endpoints.
    """
    
    def __init__(self, app: ASGIApp, guardrails_service: GuardrailsService = None):
        super().__init__(app)
        self.guardrails_service = guardrails_service or GuardrailsService()
        self.excluded_paths = {
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/favicon.ico"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through guardrails before forwarding."""
        start_time = time.time()
        
        # Skip guardrails for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        try:
            # Extract user information from request
            user_id = self._extract_user_id(request)
            user_role = self._extract_user_role(request)
            
            # Apply request-level guardrails
            request_allowed = await self._check_request_guardrails(request, user_id, user_role)
            
            if not request_allowed:
                return Response(
                    content="Request blocked by guardrails",
                    status_code=403,
                    headers={"X-Guardrails-Decision": "BLOCKED"}
                )
            
            # Process request
            response = await call_next(request)
            
            # Apply response-level guardrails
            response = await self._check_response_guardrails(response, user_id, user_role)
            
            # Add guardrails headers
            response.headers["X-Guardrails-Processed"] = "true"
            response.headers["X-Guardrails-Version"] = "1.0.0"
            
            # Log processing time
            processing_time = time.time() - start_time
            response.headers["X-Guardrails-Processing-Time"] = f"{processing_time:.3f}s"
            
            return response
            
        except Exception as e:
            logger.error(f"Guardrails middleware error: {e}")
            return Response(
                content="Internal guardrails error",
                status_code=500,
                headers={"X-Guardrails-Error": "true"}
            )
    
    def _extract_user_id(self, request: Request) -> str:
        """Extract user ID from request."""
        # Check Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # In a real implementation, decode JWT token
            return "extracted_user_id"
        
        # Check custom header
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id
        
        # Fallback to IP address
        return request.client.host if request.client else "unknown"
    
    def _extract_user_role(self, request: Request) -> str:
        """Extract user role from request."""
        # Check custom header
        user_role = request.headers.get("X-User-Role")
        if user_role:
            return user_role
        
        # Check Authorization header for role claims
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # In a real implementation, decode JWT token and extract role
            return "agent"
        
        # Default role
        return "agent"
    
    async def _check_request_guardrails(self, request: Request, user_id: str, user_role: str) -> bool:
        """Apply guardrails to incoming request."""
        try:
            # Check rate limiting
            if hasattr(self.guardrails_service, 'request_counts'):
                current_count = self.guardrails_service.request_counts.get(user_id, 0)
                if current_count >= self.guardrails_service.config.max_requests_per_minute:
                    logger.warning(f"Rate limit exceeded for user {user_id}")
                    return False
            
            # Check RBAC permissions for endpoint
            required_permissions = self._get_endpoint_permissions(request.url.path, request.method)
            access_granted, _ = self.guardrails_service.rbac_service.check_permissions(
                user_role, required_permissions
            )
            
            if not access_granted:
                logger.warning(f"Access denied for user {user_id} with role {user_role}")
                return False
            
            # Check request body for malicious content
            if request.method in ["POST", "PUT", "PATCH"]:
                # In a real implementation, read and validate request body
                pass
            
            return True
            
        except Exception as e:
            logger.error(f"Request guardrails check failed: {e}")
            return False
    
    async def _check_response_guardrails(self, response: Response, user_id: str, user_role: str) -> Response:
        """Apply guardrails to outgoing response."""
        try:
            # Check response headers for sensitive information
            sensitive_headers = ["X-Internal-Token", "X-Debug-Info", "X-Database-Query"]
            for header in sensitive_headers:
                if header in response.headers:
                    del response.headers[header]
            
            # Add security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            
            return response
            
        except Exception as e:
            logger.error(f"Response guardrails check failed: {e}")
            return response
    
    def _get_endpoint_permissions(self, path: str, method: str) -> list:
        """Get required permissions for endpoint."""
        endpoint_permissions = {
            "/api/v1/cases": {
                "GET": ["read_case"],
                "POST": ["write_case"],
                "PUT": ["write_case"],
                "DELETE": ["admin_access"]
            },
            "/api/v1/audit": {
                "GET": ["export_audit"],
                "POST": ["admin_access"]
            },
            "/api/v1/admin": {
                "GET": ["admin_access"],
                "POST": ["admin_access"],
                "PUT": ["admin_access"],
                "DELETE": ["admin_access"]
            }
        }
        
        # Match path patterns
        for endpoint_path, methods in endpoint_permissions.items():
            if path.startswith(endpoint_path):
                return methods.get(method, ["read_case"])
        
        # Default permissions
        return ["read_case"]


class LangGraphGuardrailsIntegration:
    """
    Integration layer for LangGraph workflow guardrails enforcement.
    
    Provides hooks and decorators for applying guardrails at each
    node in the LangGraph workflow.
    """
    
    def __init__(self, guardrails_service: GuardrailsService = None):
        self.guardrails_service = guardrails_service or GuardrailsService()
    
    def enforce_node_guardrails(self, node_name: str):
        """Decorator for enforcing guardrails on LangGraph nodes."""
        def decorator(func):
            async def wrapper(state: PolicyValidationState, **kwargs):
                logger.info(f"Applying guardrails to node: {node_name}")
                
                try:
                    # Pre-execution guardrails
                    pre_result = self.guardrails_service.enforce_guardrails(
                        state, 
                        user_role=kwargs.get('user_role', 'agent'),
                        user_id=kwargs.get('user_id', 'system')
                    )
                    
                    # Check if execution should be blocked
                    if pre_result.is_blocking():
                        logger.warning(f"Node {node_name} blocked by guardrails: {pre_result.decision}")
                        state.guardrails = pre_result
                        state.stop_workflow(f"Blocked by guardrails in {node_name}")
                        return state
                    
                    # Execute the original function
                    result_state = await func(state, **kwargs)
                    
                    # Post-execution guardrails
                    post_result = self.guardrails_service.enforce_guardrails(
                        result_state,
                        user_role=kwargs.get('user_role', 'agent'),
                        user_id=kwargs.get('user_id', 'system')
                    )
                    
                    # Update state with guardrails result
                    result_state.guardrails = post_result
                    
                    # Check if workflow should be stopped
                    if post_result.requires_hitl():
                        logger.info(f"Node {node_name} requires HITL review")
                        if not result_state.hitl:
                            from ..models.hitl import HITLState
                            result_state.hitl = HITLState(
                                case_id=result_state.case.case_id,
                                required=True,
                                requirement_reason="Guardrails require human review"
                            )
                        result_state.hitl.required = True
                        result_state.hitl.requirement_triggers.append(f"GUARDRAILS_{node_name}")
                    
                    return result_state
                    
                except Exception as e:
                    logger.error(f"Guardrails enforcement failed in node {node_name}: {e}")
                    state.add_error(f"Guardrails error in {node_name}: {e}")
                    return state
            
            return wrapper
        return decorator
    
    def create_guardrails_node(self) -> Callable:
        """Create a dedicated guardrails node for the LangGraph workflow."""
        @self.enforce_node_guardrails("guardrails_enforcement")
        async def guardrails_node(state: PolicyValidationState, **kwargs) -> PolicyValidationState:
            """Dedicated guardrails enforcement node."""
            logger.info(f"Executing guardrails enforcement for case {state.case.case_id}")
            
            # The actual guardrails enforcement is handled by the decorator
            # This node just ensures the state is properly updated
            
            if state.guardrails:
                logger.info(f"Guardrails decision: {state.guardrails.decision}")
                
                # Log security events
                for event in state.guardrails.security_events:
                    logger.warning(f"Security event: {event.event_type} - {event.description}")
                
                # Log PII redactions
                if state.guardrails.redactions:
                    logger.info(f"PII redactions applied: {len(state.guardrails.redactions)}")
                
                # Log source validations
                invalid_sources = state.guardrails.invalid_sources
                if invalid_sources:
                    logger.warning(f"Invalid sources detected: {invalid_sources}")
            
            return state
        
        return guardrails_node
    
    def should_continue_workflow(self, state: PolicyValidationState) -> bool:
        """Determine if workflow should continue based on guardrails."""
        if not state.guardrails:
            return True
        
        # Block if guardrails decision is BLOCK
        if state.guardrails.is_blocking():
            return False
        
        # Continue if ALLOW or REDACT
        if state.guardrails.decision in ["ALLOW", "REDACT"]:
            return True
        
        # For REQUIRE_HITL, continue to HITL node
        if state.guardrails.requires_hitl():
            return True
        
        return True
    
    def get_next_node(self, state: PolicyValidationState) -> str:
        """Determine next node based on guardrails decision."""
        if not state.guardrails:
            return "policy_retrieval"
        
        if state.guardrails.is_blocking():
            return "audit_closure"
        
        if state.guardrails.requires_hitl():
            return "hitl_gate"
        
        return "policy_retrieval"


class GuardrailsEventLogger:
    """
    Security event logging service for guardrails.
    
    Provides structured logging and alerting for security events
    detected by the guardrails system.
    """
    
    def __init__(self, config: GuardrailsConfig = None):
        self.config = config or GuardrailsConfig()
        self.logger = logging.getLogger("guardrails.security")
        
        # Configure security logger
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        case_id: str = None,
        user_id: str = None,
        additional_data: Dict[str, Any] = None
    ) -> None:
        """Log a security event with structured data."""
        event_data = {
            "event_type": event_type,
            "severity": severity,
            "description": description,
            "case_id": case_id,
            "user_id": user_id,
            "timestamp": time.time(),
            "additional_data": additional_data or {}
        }
        
        # Log based on severity
        if severity == "CRITICAL":
            self.logger.critical(f"SECURITY_EVENT: {event_data}")
        elif severity == "HIGH":
            self.logger.error(f"SECURITY_EVENT: {event_data}")
        elif severity == "MEDIUM":
            self.logger.warning(f"SECURITY_EVENT: {event_data}")
        else:
            self.logger.info(f"SECURITY_EVENT: {event_data}")
        
        # Send alerts for critical events
        if self.config.alert_on_critical_events and severity == "CRITICAL":
            self._send_security_alert(event_data)
    
    def _send_security_alert(self, event_data: Dict[str, Any]) -> None:
        """Send security alert for critical events."""
        # In a real implementation, this would send alerts via:
        # - Email notifications
        # - Slack/Teams webhooks
        # - SIEM system integration
        # - SMS alerts for critical events
        
        logger.critical(f"SECURITY_ALERT: Critical security event detected: {event_data}")
    
    def log_pii_detection(
        self,
        pii_type: str,
        field_name: str,
        case_id: str,
        redaction_applied: bool = True
    ) -> None:
        """Log PII detection and redaction."""
        self.log_security_event(
            event_type="PII_DETECTED",
            severity="MEDIUM",
            description=f"PII type {pii_type} detected in field {field_name}",
            case_id=case_id,
            additional_data={
                "pii_type": pii_type,
                "field_name": field_name,
                "redaction_applied": redaction_applied
            }
        )
    
    def log_access_violation(
        self,
        user_id: str,
        user_role: str,
        required_permissions: list,
        case_id: str = None
    ) -> None:
        """Log access control violation."""
        self.log_security_event(
            event_type="ACCESS_VIOLATION",
            severity="HIGH",
            description=f"User {user_id} with role {user_role} lacks permissions: {required_permissions}",
            case_id=case_id,
            user_id=user_id,
            additional_data={
                "user_role": user_role,
                "required_permissions": required_permissions
            }
        )
    
    def log_rate_limit_violation(self, user_id: str, request_count: int, limit: int) -> None:
        """Log rate limiting violation."""
        self.log_security_event(
            event_type="RATE_LIMIT_EXCEEDED",
            severity="HIGH",
            description=f"User {user_id} exceeded rate limit: {request_count}/{limit}",
            user_id=user_id,
            additional_data={
                "request_count": request_count,
                "limit": limit
            }
        )
    
    def log_injection_attempt(
        self,
        injection_type: str,
        patterns: list,
        case_id: str = None,
        user_id: str = None
    ) -> None:
        """Log injection attempt detection."""
        self.log_security_event(
            event_type=f"{injection_type.upper()}_INJECTION",
            severity="CRITICAL",
            description=f"{injection_type} injection attempt detected: {patterns}",
            case_id=case_id,
            user_id=user_id,
            additional_data={
                "injection_type": injection_type,
                "detected_patterns": patterns
            }
        )
    
    def log_hallucination_detection(
        self,
        content_type: str,
        hallucination_risk: float,
        case_id: str
    ) -> None:
        """Log hallucination detection."""
        self.log_security_event(
            event_type="HALLUCINATION_DETECTED",
            severity="HIGH",
            description=f"Hallucination detected in {content_type} with risk {hallucination_risk}",
            case_id=case_id,
            additional_data={
                "content_type": content_type,
                "hallucination_risk": hallucination_risk
            }
        )


# Factory functions for easy instantiation
def create_guardrails_middleware(guardrails_service: GuardrailsService = None) -> GuardrailsMiddleware:
    """Create a guardrails middleware instance."""
    return GuardrailsMiddleware(None, guardrails_service)


def create_langgraph_integration(guardrails_service: GuardrailsService = None) -> LangGraphGuardrailsIntegration:
    """Create a LangGraph guardrails integration instance."""
    return LangGraphGuardrailsIntegration(guardrails_service)


def create_event_logger(config: GuardrailsConfig = None) -> GuardrailsEventLogger:
    """Create a guardrails event logger instance."""
    return GuardrailsEventLogger(config)
