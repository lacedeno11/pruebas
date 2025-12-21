"""
Guardrails Orchestrator for DERCAS 01 Policy Validation Copilot

Main GuardrailsService that coordinates all guardrail checks including security,
RBAC, PII detection, and source validation. Implements comprehensive logging
and incident reporting for security events.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from .security import SecurityGuardrails, SecurityConfig, SecurityCheckResult, SecurityThreatLevel
from .rbac import RBACService, AccessContext, AccessDecision, Permission, UserRole
from .pii import PIIDetector, PIIConfig, PIIDetection, PIISensitivityLevel
from .source_validation import SourceValidator, SourceValidationConfig, SourceValidationResult, SourceType, ValidationResult
from ..models.enums import GuardrailAction

logger = logging.getLogger(__name__)


class GuardrailCheckType(str, Enum):
    """Types of guardrail checks."""
    SECURITY = "SECURITY"
    ACCESS_CONTROL = "ACCESS_CONTROL"
    PII_PROTECTION = "PII_PROTECTION"
    SOURCE_VALIDATION = "SOURCE_VALIDATION"
    CONTENT_FILTERING = "CONTENT_FILTERING"
    COMPLIANCE = "COMPLIANCE"


class IncidentSeverity(str, Enum):
    """Severity levels for security incidents."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class GuardrailResult(BaseModel):
    """Comprehensive result of all guardrail checks."""
    
    # Overall decision
    action: GuardrailAction
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Individual check results
    security_results: List[SecurityCheckResult] = Field(default_factory=list)
    access_decision: Optional[AccessDecision] = None
    pii_detections: List[PIIDetection] = Field(default_factory=list)
    source_validation: Optional[SourceValidationResult] = None
    
    # Aggregated information
    blocked_reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    redactions_applied: List[str] = Field(default_factory=list)
    
    # Processing metadata
    check_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: Optional[float] = None
    
    # Incident information
    incident_created: bool = False
    incident_id: Optional[str] = None
    incident_severity: Optional[IncidentSeverity] = None


class SecurityIncident(BaseModel):
    """Security incident record."""
    
    incident_id: str = Field(default_factory=lambda: str(uuid4()))
    incident_type: str
    severity: IncidentSeverity
    
    # Incident details
    title: str
    description: str
    affected_resources: List[str] = Field(default_factory=list)
    
    # Context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Evidence
    evidence: Dict[str, Any] = Field(default_factory=dict)
    guardrail_results: Optional[GuardrailResult] = None
    
    # Status
    status: str = "OPEN"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Assignment
    assigned_to: Optional[str] = None
    escalated: bool = False
    
    # Response
    response_actions: List[str] = Field(default_factory=list)
    mitigation_steps: List[str] = Field(default_factory=list)


class GuardrailsConfig(BaseModel):
    """Configuration for the guardrails orchestrator."""
    
    # Component configurations
    security_config: SecurityConfig = Field(default_factory=SecurityConfig)
    pii_config: PIIConfig = Field(default_factory=PIIConfig)
    source_validation_config: SourceValidationConfig = Field(default_factory=SourceValidationConfig)
    
    # Orchestrator settings
    enable_all_checks: bool = True
    fail_fast: bool = False  # Stop on first blocking issue
    
    # Incident management
    enable_incident_reporting: bool = True
    auto_escalate_critical: bool = True
    incident_retention_days: int = 90
    
    # Logging
    log_all_checks: bool = True
    log_pii_detections: bool = True
    log_access_decisions: bool = True
    
    # Performance
    max_processing_time_ms: float = 5000.0
    enable_async_processing: bool = False
    
    # Thresholds for incident creation
    incident_thresholds: Dict[str, Any] = Field(default_factory=lambda: {
        "security_threat_level": SecurityThreatLevel.HIGH,
        "pii_sensitivity_level": PIISensitivityLevel.HIGH,
        "access_denied_count": 3,
        "multiple_violations": 2,
    })


class GuardrailsService:
    """
    Main guardrails orchestrator service.
    
    Coordinates all guardrail checks and provides unified interface for:
    - Security validation (OWASP LLM Top 10)
    - Access control (RBAC)
    - PII protection
    - Source validation
    - Incident management
    - Audit logging
    """
    
    def __init__(self, config: GuardrailsConfig):
        self.config = config
        
        # Initialize component services
        self.security_guardrails = SecurityGuardrails(config.security_config)
        self.rbac_service = RBACService()
        self.pii_detector = PIIDetector(config.pii_config)
        self.source_validator = SourceValidator(config.source_validation_config)
        
        # Incident tracking
        self.incidents: Dict[str, SecurityIncident] = {}
        self.incident_stats = {
            "total_incidents": 0,
            "open_incidents": 0,
            "critical_incidents": 0,
        }
        
        # Performance tracking
        self.check_stats = {
            "total_checks": 0,
            "blocked_checks": 0,
            "avg_processing_time_ms": 0.0,
        }
    
    def check_input_guardrails(
        self,
        input_text: str,
        context: Dict[str, Any],
        user_context: Optional[AccessContext] = None,
        source_info: Optional[Dict[str, Any]] = None
    ) -> GuardrailResult:
        """
        Perform comprehensive guardrail checks on input.
        
        Args:
            input_text: Input text to validate
            context: Additional context for checks
            user_context: User access context for RBAC
            source_info: Source information for validation
            
        Returns:
            GuardrailResult with comprehensive check results
        """
        start_time = datetime.utcnow()
        
        try:
            result = GuardrailResult()
            
            # Security checks
            if self.config.enable_all_checks:
                security_results = self.security_guardrails.check_input_security(input_text, context)
                result.security_results = security_results
                
                # Check for blocking security issues
                if any(sr.is_blocked for sr in security_results):
                    result.action = GuardrailAction.BLOCK
                    result.blocked_reasons.extend([sr.description for sr in security_results if sr.is_blocked])
                    
                    if self.config.fail_fast:
                        return self._finalize_result(result, start_time)
            
            # Access control checks
            if user_context and self.config.enable_all_checks:
                access_decision = self.rbac_service.check_access(user_context)
                result.access_decision = access_decision
                
                if not access_decision.granted:
                    result.action = GuardrailAction.BLOCK
                    result.blocked_reasons.append(f"Access denied: {access_decision.reason}")
                    
                    if self.config.fail_fast:
                        return self._finalize_result(result, start_time)
            
            # PII detection
            if self.config.enable_all_checks:
                pii_detections = self.pii_detector.detect_pii(input_text)
                result.pii_detections = pii_detections
                
                # Apply PII redactions
                if pii_detections:
                    high_sensitivity_pii = [
                        d for d in pii_detections 
                        if d.sensitivity_level in [PIISensitivityLevel.HIGH, PIISensitivityLevel.CRITICAL]
                    ]
                    
                    if high_sensitivity_pii:
                        if result.action != GuardrailAction.BLOCK:
                            result.action = GuardrailAction.REDACT
                        
                        result.redactions_applied.extend([
                            f"{d.pii_type.value}: {d.original_text}" for d in high_sensitivity_pii
                        ])
            
            # Source validation
            if source_info and self.config.enable_all_checks:
                source_validation = self.source_validator.validate_source(
                    source_id=source_info.get('source_id', 'unknown'),
                    source_type=SourceType(source_info.get('source_type', 'UNKNOWN')),
                    source_location=source_info.get('source_location', ''),
                    content=source_info.get('content'),
                    metadata=source_info.get('metadata')
                )
                result.source_validation = source_validation
                
                if source_validation.validation_result == ValidationResult.DENIED:
                    result.action = GuardrailAction.BLOCK
                    result.blocked_reasons.append(f"Source validation failed: {source_validation.source_id}")
                    
                    if self.config.fail_fast:
                        return self._finalize_result(result, start_time)
            
            # Determine final action if not already set
            if result.action is None:
                result.action = self._determine_final_action(result)
            
            # Calculate confidence
            result.confidence = self._calculate_confidence(result)
            
            # Check for incident creation
            if self.config.enable_incident_reporting:
                self._check_incident_creation(result, context, user_context)
            
            return self._finalize_result(result, start_time)
            
        except Exception as e:
            logger.error(f"Guardrails check failed: {e}")
            
            # Create error result
            error_result = GuardrailResult(
                action=GuardrailAction.BLOCK,
                confidence=1.0,
                blocked_reasons=[f"Guardrails system error: {str(e)}"]
            )
            
            return self._finalize_result(error_result, start_time)
    
    def check_output_guardrails(
        self,
        output_text: str,
        context: Dict[str, Any],
        user_context: Optional[AccessContext] = None
    ) -> GuardrailResult:
        """
        Perform guardrail checks on output.
        
        Args:
            output_text: Output text to validate
            context: Additional context for checks
            user_context: User access context
            
        Returns:
            GuardrailResult with check results
        """
        start_time = datetime.utcnow()
        
        try:
            result = GuardrailResult()
            
            # Security checks for output
            security_results = self.security_guardrails.check_output_security(output_text, context)
            result.security_results = security_results
            
            # Check for blocking security issues
            if any(sr.is_blocked for sr in security_results):
                result.action = GuardrailAction.BLOCK
                result.blocked_reasons.extend([sr.description for sr in security_results if sr.is_blocked])
            
            # PII detection in output
            pii_detections = self.pii_detector.detect_pii(output_text)
            result.pii_detections = pii_detections
            
            # Apply PII redactions
            if pii_detections:
                critical_pii = [
                    d for d in pii_detections 
                    if d.sensitivity_level == PIISensitivityLevel.CRITICAL
                ]
                
                if critical_pii:
                    result.action = GuardrailAction.REDACT
                    result.redactions_applied.extend([
                        f"{d.pii_type.value}: {d.original_text}" for d in critical_pii
                    ])
            
            # Determine final action
            if result.action is None:
                result.action = GuardrailAction.ALLOW
            
            # Calculate confidence
            result.confidence = self._calculate_confidence(result)
            
            # Check for incident creation
            if self.config.enable_incident_reporting:
                self._check_incident_creation(result, context, user_context)
            
            return self._finalize_result(result, start_time)
            
        except Exception as e:
            logger.error(f"Output guardrails check failed: {e}")
            
            error_result = GuardrailResult(
                action=GuardrailAction.BLOCK,
                confidence=1.0,
                blocked_reasons=[f"Output guardrails system error: {str(e)}"]
            )
            
            return self._finalize_result(error_result, start_time)
    
    def apply_guardrails(
        self,
        text: str,
        result: GuardrailResult,
        apply_redactions: bool = True
    ) -> str:
        """
        Apply guardrail actions to text.
        
        Args:
            text: Original text
            result: Guardrail check result
            apply_redactions: Whether to apply PII redactions
            
        Returns:
            Modified text with guardrails applied
        """
        try:
            if result.action == GuardrailAction.BLOCK:
                return "[CONTENT BLOCKED BY SECURITY POLICY]"
            
            elif result.action == GuardrailAction.REDACT and apply_redactions:
                # Apply PII masking
                if result.pii_detections:
                    masked_text = self.pii_detector.mask_text(text, result.pii_detections)
                    return masked_text
                
                # Apply security sanitization
                sanitized_text = self.security_guardrails.sanitize_output(text)
                return sanitized_text
            
            elif result.action == GuardrailAction.REQUIRE_HITL:
                return text + "\n\n[NOTE: This content requires human review]"
            
            else:  # ALLOW
                return text
                
        except Exception as e:
            logger.error(f"Failed to apply guardrails: {e}")
            return "[ERROR APPLYING SECURITY CONTROLS]"
    
    def _determine_final_action(self, result: GuardrailResult) -> GuardrailAction:
        """Determine the final guardrail action based on all checks."""
        # If any check resulted in blocking, block
        if result.blocked_reasons:
            return GuardrailAction.BLOCK
        
        # If PII redactions are needed, redact
        if result.redactions_applied:
            return GuardrailAction.REDACT
        
        # If access requires additional conditions, require HITL
        if result.access_decision and result.access_decision.requires_approval:
            return GuardrailAction.REQUIRE_HITL
        
        # Check for warnings that might require HITL
        high_risk_conditions = [
            any(sr.threat_level == SecurityThreatLevel.HIGH for sr in result.security_results),
            any(d.sensitivity_level == PIISensitivityLevel.HIGH for d in result.pii_detections),
            result.source_validation and result.source_validation.requires_manual_review
        ]
        
        if any(high_risk_conditions):
            return GuardrailAction.REQUIRE_HITL
        
        return GuardrailAction.ALLOW
    
    def _calculate_confidence(self, result: GuardrailResult) -> float:
        """Calculate confidence score for the guardrail decision."""
        confidence_scores = []
        
        # Security confidence
        if result.security_results:
            avg_security_confidence = sum(sr.confidence for sr in result.security_results) / len(result.security_results)
            confidence_scores.append(avg_security_confidence)
        
        # Access control confidence
        if result.access_decision:
            # Access decisions are typically high confidence
            confidence_scores.append(0.95)
        
        # PII detection confidence
        if result.pii_detections:
            avg_pii_confidence = sum(d.confidence for d in result.pii_detections) / len(result.pii_detections)
            confidence_scores.append(avg_pii_confidence)
        
        # Source validation confidence
        if result.source_validation:
            confidence_scores.append(result.source_validation.confidence)
        
        # Return average confidence or default
        if confidence_scores:
            return sum(confidence_scores) / len(confidence_scores)
        else:
            return 0.8  # Default confidence
    
    def _check_incident_creation(
        self,
        result: GuardrailResult,
        context: Dict[str, Any],
        user_context: Optional[AccessContext]
    ):
        """Check if an incident should be created based on the results."""
        incident_triggers = []
        
        # High/Critical security threats
        critical_security = [
            sr for sr in result.security_results 
            if sr.threat_level in [SecurityThreatLevel.HIGH, SecurityThreatLevel.CRITICAL]
        ]
        if critical_security:
            incident_triggers.append("critical_security_threat")
        
        # Access denied
        if result.access_decision and not result.access_decision.granted:
            incident_triggers.append("access_denied")
        
        # High sensitivity PII
        critical_pii = [
            d for d in result.pii_detections 
            if d.sensitivity_level == PIISensitivityLevel.CRITICAL
        ]
        if critical_pii:
            incident_triggers.append("critical_pii_detected")
        
        # Source validation failures
        if result.source_validation and result.source_validation.validation_result == ValidationResult.DENIED:
            incident_triggers.append("source_validation_failure")
        
        # Multiple violations
        if len(incident_triggers) >= self.config.incident_thresholds.get("multiple_violations", 2):
            incident_triggers.append("multiple_violations")
        
        # Create incident if triggers exist
        if incident_triggers:
            incident = self._create_incident(result, incident_triggers, context, user_context)
            result.incident_created = True
            result.incident_id = incident.incident_id
            result.incident_severity = incident.severity
    
    def _create_incident(
        self,
        result: GuardrailResult,
        triggers: List[str],
        context: Dict[str, Any],
        user_context: Optional[AccessContext]
    ) -> SecurityIncident:
        """Create a security incident."""
        # Determine severity
        severity = IncidentSeverity.MEDIUM
        
        if any(sr.threat_level == SecurityThreatLevel.CRITICAL for sr in result.security_results):
            severity = IncidentSeverity.CRITICAL
        elif any(sr.threat_level == SecurityThreatLevel.HIGH for sr in result.security_results):
            severity = IncidentSeverity.HIGH
        elif "multiple_violations" in triggers:
            severity = IncidentSeverity.HIGH
        
        # Create incident
        incident = SecurityIncident(
            incident_type="GUARDRAILS_VIOLATION",
            severity=severity,
            title=f"Security guardrails violation: {', '.join(triggers)}",
            description=f"Multiple security violations detected: {triggers}",
            affected_resources=context.get("affected_resources", []),
            user_id=user_context.user_id if user_context else None,
            session_id=user_context.session_id if user_context else None,
            ip_address=user_context.ip_address if user_context else None,
            user_agent=user_context.user_agent if user_context else None,
            evidence={
                "triggers": triggers,
                "context": context,
                "blocked_reasons": result.blocked_reasons,
                "security_issues": [sr.description for sr in result.security_results if sr.is_blocked],
            },
            guardrail_results=result,
            response_actions=self._generate_response_actions(severity, triggers),
            mitigation_steps=self._generate_mitigation_steps(triggers)
        )
        
        # Store incident
        self.incidents[incident.incident_id] = incident
        self.incident_stats["total_incidents"] += 1
        self.incident_stats["open_incidents"] += 1
        
        if severity == IncidentSeverity.CRITICAL:
            self.incident_stats["critical_incidents"] += 1
        
        # Log incident
        logger.critical(f"Security incident created: {incident.incident_id} - {incident.title}")
        
        # Auto-escalate if critical
        if severity == IncidentSeverity.CRITICAL and self.config.auto_escalate_critical:
            self._escalate_incident(incident.incident_id)
        
        return incident
    
    def _generate_response_actions(self, severity: IncidentSeverity, triggers: List[str]) -> List[str]:
        """Generate response actions for an incident."""
        actions = []
        
        if severity == IncidentSeverity.CRITICAL:
            actions.extend([
                "Immediate security team notification",
                "Block user session",
                "Escalate to security manager",
                "Initiate incident response procedure"
            ])
        elif severity == IncidentSeverity.HIGH:
            actions.extend([
                "Security team notification",
                "Review user permissions",
                "Monitor user activity"
            ])
        else:
            actions.extend([
                "Log for review",
                "Monitor for patterns"
            ])
        
        # Trigger-specific actions
        if "access_denied" in triggers:
            actions.append("Review access control policies")
        
        if "critical_pii_detected" in triggers:
            actions.append("Audit data handling procedures")
        
        if "source_validation_failure" in triggers:
            actions.append("Review source allowlists")
        
        return actions
    
    def _generate_mitigation_steps(self, triggers: List[str]) -> List[str]:
        """Generate mitigation steps for an incident."""
        steps = []
        
        if "critical_security_threat" in triggers:
            steps.extend([
                "Update security patterns",
                "Review input validation",
                "Enhance monitoring"
            ])
        
        if "access_denied" in triggers:
            steps.extend([
                "Verify user permissions",
                "Update role definitions",
                "Review access policies"
            ])
        
        if "critical_pii_detected" in triggers:
            steps.extend([
                "Enhance PII detection",
                "Update masking rules",
                "Review data classification"
            ])
        
        if "source_validation_failure" in triggers:
            steps.extend([
                "Update source allowlists",
                "Review source verification",
                "Enhance source monitoring"
            ])
        
        return steps
    
    def _escalate_incident(self, incident_id: str):
        """Escalate an incident."""
        if incident_id in self.incidents:
            incident = self.incidents[incident_id]
            incident.escalated = True
            incident.updated_at = datetime.utcnow()
            
            logger.critical(f"Incident escalated: {incident_id}")
            
            # In production, this would trigger additional notifications
    
    def _finalize_result(self, result: GuardrailResult, start_time: datetime) -> GuardrailResult:
        """Finalize the guardrail result with timing and logging."""
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        result.processing_time_ms = processing_time
        
        # Update statistics
        self.check_stats["total_checks"] += 1
        if result.action in [GuardrailAction.BLOCK, GuardrailAction.REQUIRE_HITL]:
            self.check_stats["blocked_checks"] += 1
        
        # Update average processing time
        total_checks = self.check_stats["total_checks"]
        current_avg = self.check_stats["avg_processing_time_ms"]
        self.check_stats["avg_processing_time_ms"] = (
            (current_avg * (total_checks - 1) + processing_time) / total_checks
        )
        
        # Log the result
        if self.config.log_all_checks:
            self._log_guardrail_result(result)
        
        return result
    
    def _log_guardrail_result(self, result: GuardrailResult):
        """Log guardrail check result."""
        log_data = {
            "check_id": result.check_id,
            "action": result.action.value,
            "confidence": result.confidence,
            "processing_time_ms": result.processing_time_ms,
            "blocked_reasons_count": len(result.blocked_reasons),
            "warnings_count": len(result.warnings),
            "redactions_count": len(result.redactions_applied),
            "incident_created": result.incident_created,
            "timestamp": result.timestamp.isoformat(),
        }
        
        if result.action == GuardrailAction.BLOCK:
            logger.warning(f"Guardrails blocked request: {log_data}")
        elif result.action == GuardrailAction.REQUIRE_HITL:
            logger.info(f"Guardrails require HITL: {log_data}")
        else:
            logger.debug(f"Guardrails check completed: {log_data}")
    
    def get_incident(self, incident_id: str) -> Optional[SecurityIncident]:
        """Get incident by ID."""
        return self.incidents.get(incident_id)
    
    def list_incidents(
        self,
        status: Optional[str] = None,
        severity: Optional[IncidentSeverity] = None,
        limit: Optional[int] = None
    ) -> List[SecurityIncident]:
        """List incidents with optional filtering."""
        incidents = list(self.incidents.values())
        
        if status:
            incidents = [i for i in incidents if i.status == status]
        
        if severity:
            incidents = [i for i in incidents if i.severity == severity]
        
        # Sort by creation time (newest first)
        incidents.sort(key=lambda x: x.created_at, reverse=True)
        
        if limit:
            incidents = incidents[:limit]
        
        return incidents
    
    def resolve_incident(self, incident_id: str, resolution_notes: str) -> bool:
        """Resolve an incident."""
        if incident_id in self.incidents:
            incident = self.incidents[incident_id]
            incident.status = "RESOLVED"
            incident.resolved_at = datetime.utcnow()
            incident.updated_at = datetime.utcnow()
            incident.response_actions.append(f"Resolved: {resolution_notes}")
            
            self.incident_stats["open_incidents"] -= 1
            
            logger.info(f"Incident resolved: {incident_id}")
            return True
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get guardrails service statistics."""
        return {
            "check_stats": self.check_stats,
            "incident_stats": self.incident_stats,
            "component_stats": {
                "security_cache_size": len(getattr(self.security_guardrails, 'request_counts', {})),
                "rbac_cache_size": len(self.rbac_service.access_cache),
                "pii_cache_size": len(self.pii_detector.tokenization_cache),
                "source_validation_cache_size": len(self.source_validator.validation_cache),
            }
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all guardrail components."""
        health_status = {
            "overall_healthy": True,
            "components": {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        try:
            # Check each component
            components = {
                "security": lambda: {"healthy": True, "checks_enabled": len(self.security_guardrails.injection_patterns) > 0},
                "rbac": lambda: {"healthy": True, "roles_configured": len(self.rbac_service.role_definitions) > 0},
                "pii": lambda: {"healthy": True, "patterns_loaded": len(self.pii_detector.detection_patterns) > 0},
                "source_validation": lambda: {"healthy": True, "trusted_sources": len(self.source_validator.trusted_sources) > 0},
            }
            
            for component_name, health_func in components.items():
                try:
                    health_status["components"][component_name] = health_func()
                except Exception as e:
                    health_status["components"][component_name] = {
                        "healthy": False,
                        "error": str(e)
                    }
                    health_status["overall_healthy"] = False
            
        except Exception as e:
            health_status["overall_healthy"] = False
            health_status["error"] = str(e)
        
        return health_status


# Factory function
def create_guardrails_service(config: Optional[GuardrailsConfig] = None) -> GuardrailsService:
    """Create a guardrails service with default or custom configuration."""
    if config is None:
        config = GuardrailsConfig()
    
    return GuardrailsService(config)


# Utility functions
def quick_security_check(text: str, guardrails_service: GuardrailsService) -> bool:
    """Quick security check for text input."""
    result = guardrails_service.check_input_guardrails(text, {})
    return result.action == GuardrailAction.ALLOW


def apply_standard_guardrails(
    text: str,
    user_id: str,
    user_roles: List[UserRole],
    resource_type: str,
    action: str,
    guardrails_service: GuardrailsService
) -> Tuple[str, GuardrailResult]:
    """Apply standard guardrails to text with user context."""
    # Create access context
    access_context = AccessContext(
        user_id=user_id,
        user_roles=user_roles,
        resource_type=resource_type,
        action=action
    )
    
    # Check guardrails
    result = guardrails_service.check_input_guardrails(
        input_text=text,
        context={"resource_type": resource_type, "action": action},
        user_context=access_context
    )
    
    # Apply guardrails
    processed_text = guardrails_service.apply_guardrails(text, result)
    
    return processed_text, result


def check_content_safety(content: str, guardrails_service: GuardrailsService) -> Dict[str, Any]:
    """Check content safety and return detailed analysis."""
    result = guardrails_service.check_input_guardrails(content, {})
    
    return {
        "safe": result.action == GuardrailAction.ALLOW,
        "action": result.action.value,
        "confidence": result.confidence,
        "issues_found": len(result.blocked_reasons) + len(result.warnings),
        "pii_detected": len(result.pii_detections) > 0,
        "security_threats": len(result.security_results) > 0,
        "requires_review": result.action == GuardrailAction.REQUIRE_HITL,
        "incident_created": result.incident_created,
    }
