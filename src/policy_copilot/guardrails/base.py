"""
Base Guardrails Service Interface

This module defines the base interface and common components for all guardrails
in the Policy Validation Copilot system implementing UC-OP-10.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class GuardrailSeverity(str, Enum):
    """Severity levels for guardrail violations"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class GuardrailDecision(str, Enum):
    """Guardrail enforcement decisions"""
    ALLOW = "ALLOW"
    REDACT = "REDACT"
    BLOCK = "BLOCK"
    REQUIRE_HITL = "REQUIRE_HITL"


class GuardrailFlag(BaseModel):
    """Individual guardrail flag with details"""
    flag_type: str = Field(..., description="Type of guardrail flag")
    severity: GuardrailSeverity = Field(..., description="Severity level")
    message: str = Field(..., description="Human-readable description")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional flag details")
    rule_id: Optional[str] = Field(None, description="Rule ID that triggered this flag")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When flag was raised")


class GuardrailRedaction(BaseModel):
    """PII redaction information"""
    field_path: str = Field(..., description="Path to redacted field")
    original_value: str = Field(..., description="Original value (for audit)")
    redacted_value: str = Field(..., description="Redacted value")
    redaction_type: str = Field(..., description="Type of PII detected")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")


class GuardrailContext(BaseModel):
    """Context information for guardrail evaluation"""
    user_id: Optional[str] = Field(None, description="User performing the action")
    user_roles: List[str] = Field(default_factory=list, description="User roles")
    user_permissions: List[str] = Field(default_factory=list, description="User permissions")
    resource_type: str = Field(..., description="Type of resource being accessed")
    resource_id: Optional[str] = Field(None, description="Resource identifier")
    action: str = Field(..., description="Action being performed")
    source_ip: Optional[str] = Field(None, description="Source IP address")
    session_id: Optional[str] = Field(None, description="Session identifier")
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request timestamp")


class GuardrailResult(BaseModel):
    """Result of guardrail evaluation"""
    decision: GuardrailDecision = Field(..., description="Enforcement decision")
    flags: List[GuardrailFlag] = Field(default_factory=list, description="Raised flags")
    redactions: List[GuardrailRedaction] = Field(default_factory=list, description="PII redactions")
    modified_payload: Optional[Dict[str, Any]] = Field(None, description="Modified payload after redactions")
    security_context: Dict[str, Any] = Field(default_factory=dict, description="Security context")
    processing_time_ms: Optional[int] = Field(None, description="Processing time")
    guardrail_version: str = Field(..., description="Version of guardrails applied")


class SecurityEvent(BaseModel):
    """Security event for logging and monitoring"""
    event_type: str = Field(..., description="Type of security event")
    severity: GuardrailSeverity = Field(..., description="Event severity")
    description: str = Field(..., description="Event description")
    context: GuardrailContext = Field(..., description="Event context")
    flags: List[GuardrailFlag] = Field(default_factory=list, description="Associated flags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")


class BaseGuardrail(ABC):
    """
    Abstract base class for all guardrails.
    
    Provides common functionality for security enforcement,
    logging, and monitoring.
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.enabled = True
        self.severity_threshold = GuardrailSeverity.LOW
        
    @abstractmethod
    async def evaluate(self, payload: Dict[str, Any], context: GuardrailContext) -> GuardrailResult:
        """
        Evaluate payload against guardrail rules.
        
        Args:
            payload: Data payload to evaluate
            context: Security context
            
        Returns:
            Guardrail evaluation result
        """
        pass
    
    @abstractmethod
    def get_rule_ids(self) -> List[str]:
        """
        Get list of rule IDs implemented by this guardrail.
        
        Returns:
            List of rule identifiers
        """
        pass
    
    def is_enabled(self) -> bool:
        """Check if guardrail is enabled"""
        return self.enabled
    
    def enable(self) -> None:
        """Enable guardrail"""
        self.enabled = True
        logger.info(f"Guardrail {self.name} enabled")
    
    def disable(self) -> None:
        """Disable guardrail"""
        self.enabled = False
        logger.warning(f"Guardrail {self.name} disabled")
    
    def set_severity_threshold(self, threshold: GuardrailSeverity) -> None:
        """Set minimum severity threshold for enforcement"""
        self.severity_threshold = threshold
        logger.info(f"Guardrail {self.name} severity threshold set to {threshold}")
    
    async def _create_flag(
        self, 
        flag_type: str, 
        severity: GuardrailSeverity, 
        message: str,
        details: Dict[str, Any] = None,
        rule_id: str = None
    ) -> GuardrailFlag:
        """Create a guardrail flag"""
        return GuardrailFlag(
            flag_type=flag_type,
            severity=severity,
            message=message,
            details=details or {},
            rule_id=rule_id
        )
    
    async def _create_redaction(
        self,
        field_path: str,
        original_value: str,
        redacted_value: str,
        redaction_type: str,
        confidence: float
    ) -> GuardrailRedaction:
        """Create a PII redaction"""
        return GuardrailRedaction(
            field_path=field_path,
            original_value=original_value,
            redacted_value=redacted_value,
            redaction_type=redaction_type,
            confidence=confidence
        )
    
    async def _log_security_event(
        self,
        event_type: str,
        severity: GuardrailSeverity,
        description: str,
        context: GuardrailContext,
        flags: List[GuardrailFlag] = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """Log security event"""
        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            description=description,
            context=context,
            flags=flags or [],
            metadata=metadata or {}
        )
        
        # Log to security logger
        security_logger = logging.getLogger("security")
        security_logger.warning(f"Security Event: {event.event_type} - {event.description}")
        
        # TODO: Send to security monitoring system
        # await self._send_to_security_monitoring(event)


class GuardrailEngine:
    """
    Main guardrail engine that orchestrates all security checks.
    
    Implements UC-OP-10 with comprehensive security enforcement.
    """
    
    def __init__(self):
        self._guardrails: List[BaseGuardrail] = []
        self._rule_registry: Dict[str, BaseGuardrail] = {}
        self.version = "1.0.0"
        
    def register_guardrail(self, guardrail: BaseGuardrail) -> None:
        """
        Register a guardrail with the engine.
        
        Args:
            guardrail: Guardrail instance to register
        """
        self._guardrails.append(guardrail)
        
        # Register rule IDs
        for rule_id in guardrail.get_rule_ids():
            self._rule_registry[rule_id] = guardrail
        
        logger.info(f"Registered guardrail: {guardrail.name} v{guardrail.version}")
    
    def get_guardrail_by_rule(self, rule_id: str) -> Optional[BaseGuardrail]:
        """Get guardrail that implements a specific rule"""
        return self._rule_registry.get(rule_id)
    
    def list_guardrails(self) -> List[BaseGuardrail]:
        """Get list of all registered guardrails"""
        return self._guardrails.copy()
    
    def list_rules(self) -> List[str]:
        """Get list of all registered rule IDs"""
        return list(self._rule_registry.keys())
    
    async def evaluate_all(
        self, 
        payload: Dict[str, Any], 
        context: GuardrailContext
    ) -> GuardrailResult:
        """
        Evaluate payload against all enabled guardrails.
        
        Args:
            payload: Data payload to evaluate
            context: Security context
            
        Returns:
            Consolidated guardrail result
        """
        start_time = datetime.utcnow()
        
        all_flags = []
        all_redactions = []
        final_decision = GuardrailDecision.ALLOW
        modified_payload = payload.copy()
        security_context = {}
        
        # Evaluate each guardrail
        for guardrail in self._guardrails:
            if not guardrail.is_enabled():
                continue
                
            try:
                result = await guardrail.evaluate(modified_payload, context)
                
                # Collect flags
                all_flags.extend(result.flags)
                
                # Collect redactions and apply them
                all_redactions.extend(result.redactions)
                if result.modified_payload:
                    modified_payload = result.modified_payload
                
                # Update security context
                security_context.update(result.security_context)
                
                # Determine most restrictive decision
                if result.decision == GuardrailDecision.BLOCK:
                    final_decision = GuardrailDecision.BLOCK
                elif result.decision == GuardrailDecision.REQUIRE_HITL and final_decision != GuardrailDecision.BLOCK:
                    final_decision = GuardrailDecision.REQUIRE_HITL
                elif result.decision == GuardrailDecision.REDACT and final_decision == GuardrailDecision.ALLOW:
                    final_decision = GuardrailDecision.REDACT
                
            except Exception as e:
                # Log guardrail failure but continue
                logger.error(f"Guardrail {guardrail.name} failed: {str(e)}")
                
                # Create failure flag
                failure_flag = await guardrail._create_flag(
                    flag_type="GUARDRAIL_FAILURE",
                    severity=GuardrailSeverity.HIGH,
                    message=f"Guardrail {guardrail.name} failed to evaluate",
                    details={"error": str(e)}
                )
                all_flags.append(failure_flag)
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Create consolidated result
        result = GuardrailResult(
            decision=final_decision,
            flags=all_flags,
            redactions=all_redactions,
            modified_payload=modified_payload if all_redactions else None,
            security_context=security_context,
            processing_time_ms=int(processing_time),
            guardrail_version=self.version
        )
        
        # Log security events for high-severity flags
        await self._log_high_severity_events(result, context)
        
        return result
    
    async def _log_high_severity_events(
        self, 
        result: GuardrailResult, 
        context: GuardrailContext
    ) -> None:
        """Log security events for high-severity flags"""
        high_severity_flags = [
            flag for flag in result.flags 
            if flag.severity in [GuardrailSeverity.HIGH, GuardrailSeverity.CRITICAL]
        ]
        
        if high_severity_flags:
            security_logger = logging.getLogger("security")
            security_logger.warning(
                f"High-severity guardrail violations detected: "
                f"{len(high_severity_flags)} flags, decision: {result.decision}"
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all guardrails"""
        health_status = {
            "engine_version": self.version,
            "total_guardrails": len(self._guardrails),
            "enabled_guardrails": len([g for g in self._guardrails if g.is_enabled()]),
            "total_rules": len(self._rule_registry),
            "guardrails": {}
        }
        
        for guardrail in self._guardrails:
            health_status["guardrails"][guardrail.name] = {
                "enabled": guardrail.is_enabled(),
                "version": guardrail.version,
                "rules": guardrail.get_rule_ids()
            }
        
        return health_status


# Global guardrail engine instance
guardrail_engine = GuardrailEngine()
