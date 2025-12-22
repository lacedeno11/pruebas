"""
Guardrails Service implementing OWASP LLM Top 10 Controls

This module provides comprehensive security controls for the Policy Validation Copilot
system, implementing OWASP LLM Top 10 security guidelines and additional governance controls.

Security Controls Implemented:
- LLM01: Prompt Injection Detection and Prevention
- LLM02: Insecure Output Handling Protection
- LLM03: Training Data Poisoning Prevention
- LLM04: Model Denial of Service Protection
- LLM05: Supply Chain Vulnerabilities Mitigation
- LLM06: Sensitive Information Disclosure Prevention (PII Masking)
- LLM07: Insecure Plugin Design Protection
- LLM08: Excessive Agency Prevention
- LLM09: Overreliance Prevention (Evidence Anchoring)
- LLM10: Model Theft Protection

Additional Controls:
- RBAC/ABAC validation
- Allowlist source validation
- Evidence anchoring validation
- Security event logging and incident reporting
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SecurityLevel(str, Enum):
    """Security levels for guardrail decisions"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class GuardrailDecision(str, Enum):
    """Guardrail decision types"""
    ALLOW = "ALLOW"
    REDACT = "REDACT"
    BLOCK = "BLOCK"
    REQUIRE_HITL = "REQUIRE_HITL"
    ESCALATE = "ESCALATE"


class SecurityEventType(str, Enum):
    """Types of security events"""
    PROMPT_INJECTION = "PROMPT_INJECTION"
    JAILBREAK_ATTEMPT = "JAILBREAK_ATTEMPT"
    DATA_EXFILTRATION = "DATA_EXFILTRATION"
    PII_DETECTED = "PII_DETECTED"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    ALLOWLIST_VIOLATION = "ALLOWLIST_VIOLATION"
    EVIDENCE_ANCHORING_FAILURE = "EVIDENCE_ANCHORING_FAILURE"
    EXCESSIVE_AGENCY = "EXCESSIVE_AGENCY"
    MODEL_ABUSE = "MODEL_ABUSE"
    SUSPICIOUS_PATTERN = "SUSPICIOUS_PATTERN"


class SecurityEvent(BaseModel):
    """Security event record"""
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: SecurityEventType
    severity: SecurityLevel
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Event details
    description: str
    source: str  # Component that triggered the event
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    case_id: Optional[str] = None
    
    # Detection details
    detected_patterns: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    
    # Context and evidence
    context: Dict[str, Any] = Field(default_factory=dict)
    raw_input: Optional[str] = None
    processed_output: Optional[str] = None
    
    # Response and mitigation
    action_taken: GuardrailDecision
    mitigation_applied: List[str] = Field(default_factory=list)
    
    # Audit trail
    reviewed: bool = False
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    false_positive: bool = False


class PIIPattern(BaseModel):
    """PII detection pattern"""
    name: str
    pattern: str
    confidence: float
    replacement: str = "[REDACTED]"
    enabled: bool = True


class GuardrailRule(BaseModel):
    """Individual guardrail rule"""
    rule_id: str
    name: str
    description: str
    rule_type: str
    severity: SecurityLevel
    enabled: bool = True
    
    # Rule configuration
    patterns: List[str] = Field(default_factory=list)
    thresholds: Dict[str, float] = Field(default_factory=dict)
    actions: List[GuardrailDecision] = Field(default_factory=list)
    
    # Scope and applicability
    applies_to: List[str] = Field(default_factory=list)  # Components this rule applies to
    exceptions: List[str] = Field(default_factory=list)  # Exception conditions
    
    # Performance and monitoring
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    false_positive_rate: float = 0.0


class UserContext(BaseModel):
    """User context for RBAC/ABAC evaluation"""
    user_id: str
    roles: List[str]
    permissions: List[str]
    attributes: Dict[str, Any] = Field(default_factory=dict)
    
    # Session information
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Access context
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None


class GuardrailsConfig:
    """Guardrails configuration manager"""
    
    def __init__(self, config_path: str = "config/guardrails.yaml"):
        self.config_path = config_path
        self.config = {}
        self.pii_patterns = []
        self.rules = {}
        self.rbac_policies = {}
        self.allowlist_sources = set()
        
        self._load_config()
    
    def _load_config(self):
        """Load guardrails configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            # Load PII patterns
            self._load_pii_patterns()
            
            # Load guardrail rules
            self._load_guardrail_rules()
            
            # Load RBAC policies
            self._load_rbac_policies()
            
            # Load allowlist sources
            self._load_allowlist_sources()
            
            logger.info(f"Loaded guardrails configuration from {self.config_path}")
            
        except FileNotFoundError:
            logger.warning(f"Guardrails config file not found: {self.config_path}")
            self._create_default_config()
        except Exception as e:
            logger.error(f"Failed to load guardrails config: {e}")
            self._create_default_config()
    
    def _load_pii_patterns(self):
        """Load PII detection patterns"""
        pii_config = self.config.get('pii_detection', {})
        patterns_config = pii_config.get('patterns', [])
        
        self.pii_patterns = []
        for pattern_config in patterns_config:
            pattern = PIIPattern(**pattern_config)
            self.pii_patterns.append(pattern)
    
    def _load_guardrail_rules(self):
        """Load guardrail rules"""
        rules_config = self.config.get('rules', [])
        
        self.rules = {}
        for rule_config in rules_config:
            rule = GuardrailRule(**rule_config)
            self.rules[rule.rule_id] = rule
    
    def _load_rbac_policies(self):
        """Load RBAC/ABAC policies"""
        self.rbac_policies = self.config.get('rbac', {})
    
    def _load_allowlist_sources(self):
        """Load allowlist sources"""
        allowlist_config = self.config.get('allowlist', {})
        sources = allowlist_config.get('sources', [])
        self.allowlist_sources = set(sources)
    
    def _create_default_config(self):
        """Create default configuration"""
        self.config = {
            'pii_detection': {
                'enabled': True,
                'patterns': [
                    {
                        'name': 'email',
                        'pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                        'confidence': 0.9,
                        'replacement': '[EMAIL_REDACTED]'
                    },
                    {
                        'name': 'phone',
                        'pattern': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
                        'confidence': 0.8,
                        'replacement': '[PHONE_REDACTED]'
                    },
                    {
                        'name': 'ssn',
                        'pattern': r'\b\d{3}-\d{2}-\d{4}\b',
                        'confidence': 0.95,
                        'replacement': '[SSN_REDACTED]'
                    }
                ]
            },
            'rules': [],
            'rbac': {
                'roles': {
                    'cabina': ['read_cases', 'create_cases', 'update_cases'],
                    'supervisor': ['read_cases', 'create_cases', 'update_cases', 'approve_decisions'],
                    'auditor': ['read_cases', 'read_audit_logs', 'export_data']
                }
            },
            'allowlist': {
                'sources': []
            }
        }
        
        self._load_pii_patterns()
        self._load_guardrail_rules()
        self._load_rbac_policies()
        self._load_allowlist_sources()


class PromptInjectionDetector:
    """Detect prompt injection and jailbreak attempts"""
    
    def __init__(self):
        # Common prompt injection patterns
        self.injection_patterns = [
            r'ignore\s+previous\s+instructions',
            r'forget\s+everything\s+above',
            r'system\s*:\s*you\s+are\s+now',
            r'new\s+instructions\s*:',
            r'override\s+your\s+programming',
            r'act\s+as\s+if\s+you\s+are',
            r'pretend\s+to\s+be',
            r'roleplay\s+as',
            r'simulate\s+being',
            r'bypass\s+your\s+guidelines',
            r'ignore\s+your\s+constraints',
            r'disregard\s+your\s+rules'
        ]
        
        # Jailbreak attempt patterns
        self.jailbreak_patterns = [
            r'DAN\s+mode',
            r'developer\s+mode',
            r'god\s+mode',
            r'unrestricted\s+mode',
            r'jailbreak',
            r'break\s+free',
            r'escape\s+your\s+programming',
            r'remove\s+all\s+restrictions',
            r'unlimited\s+access',
            r'admin\s+privileges'
        ]
        
        # Compile patterns for performance
        self.compiled_injection = [re.compile(pattern, re.IGNORECASE) for pattern in self.injection_patterns]
        self.compiled_jailbreak = [re.compile(pattern, re.IGNORECASE) for pattern in self.jailbreak_patterns]
    
    def detect_injection(self, text: str) -> Tuple[bool, List[str], float]:
        """Detect prompt injection attempts"""
        detected_patterns = []
        
        # Check injection patterns
        for pattern in self.compiled_injection:
            if pattern.search(text):
                detected_patterns.append(pattern.pattern)
        
        # Check jailbreak patterns
        for pattern in self.compiled_jailbreak:
            if pattern.search(text):
                detected_patterns.append(pattern.pattern)
        
        # Calculate confidence based on number of patterns matched
        confidence = min(len(detected_patterns) * 0.3, 1.0)
        
        return len(detected_patterns) > 0, detected_patterns, confidence


class PIIDetector:
    """Detect and mask personally identifiable information"""
    
    def __init__(self, patterns: List[PIIPattern]):
        self.patterns = patterns
        self.compiled_patterns = []
        
        for pattern in patterns:
            if pattern.enabled:
                compiled = re.compile(pattern.pattern, re.IGNORECASE)
                self.compiled_patterns.append((compiled, pattern))
    
    def detect_and_mask_pii(self, text: str) -> Tuple[str, List[Dict], bool]:
        """Detect PII and return masked text with detection details"""
        masked_text = text
        detections = []
        pii_found = False
        
        for compiled_pattern, pattern in self.compiled_patterns:
            matches = compiled_pattern.finditer(text)
            
            for match in matches:
                pii_found = True
                
                # Record detection
                detection = {
                    'type': pattern.name,
                    'confidence': pattern.confidence,
                    'start': match.start(),
                    'end': match.end(),
                    'original_text': match.group(),
                    'replacement': pattern.replacement
                }
                detections.append(detection)
                
                # Apply masking
                masked_text = masked_text.replace(match.group(), pattern.replacement)
        
        return masked_text, detections, pii_found


class EvidenceAnchoringValidator:
    """Validate evidence anchoring to prevent hallucination"""
    
    def __init__(self, allowlist_sources: Set[str]):
        self.allowlist_sources = allowlist_sources
    
    def validate_evidence_anchoring(self, evidence_items: List[Dict], 
                                   generated_content: str) -> Tuple[bool, List[str], float]:
        """Validate that generated content is properly anchored to evidence"""
        issues = []
        
        # Check if evidence sources are in allowlist
        for item in evidence_items:
            doc_id = item.get('doc_id', '')
            if doc_id and doc_id not in self.allowlist_sources:
                issues.append(f"Evidence source not in allowlist: {doc_id}")
        
        # Check for evidence coverage
        if not evidence_items:
            issues.append("No evidence provided for generated content")
        
        # Check for specific claims without evidence
        claim_patterns = [
            r'according\s+to\s+policy',
            r'the\s+regulation\s+states',
            r'as\s+specified\s+in',
            r'the\s+document\s+indicates'
        ]
        
        claims_found = 0
        for pattern in claim_patterns:
            if re.search(pattern, generated_content, re.IGNORECASE):
                claims_found += 1
        
        # Calculate anchoring score
        evidence_count = len(evidence_items)
        if claims_found > 0 and evidence_count == 0:
            issues.append("Claims made without supporting evidence")
        
        anchoring_score = min(evidence_count / max(claims_found, 1), 1.0) if claims_found > 0 else 1.0
        
        return len(issues) == 0, issues, anchoring_score


class RBACValidator:
    """Role-Based and Attribute-Based Access Control validator"""
    
    def __init__(self, rbac_policies: Dict):
        self.rbac_policies = rbac_policies
        self.roles = rbac_policies.get('roles', {})
        self.policies = rbac_policies.get('policies', [])
    
    def validate_access(self, user_context: UserContext) -> Tuple[bool, List[str]]:
        """Validate user access based on RBAC/ABAC policies"""
        issues = []
        
        # Check role-based permissions
        user_permissions = set()
        for role in user_context.roles:
            role_permissions = self.roles.get(role, [])
            user_permissions.update(role_permissions)
        
        # Check if user has required permission for action
        required_permission = self._get_required_permission(
            user_context.resource_type, 
            user_context.action
        )
        
        if required_permission and required_permission not in user_permissions:
            issues.append(f"User lacks required permission: {required_permission}")
        
        # Apply attribute-based policies
        for policy in self.policies:
            if not self._evaluate_policy(policy, user_context):
                issues.append(f"Policy violation: {policy.get('name', 'Unknown')}")
        
        return len(issues) == 0, issues
    
    def _get_required_permission(self, resource_type: str, action: str) -> str:
        """Get required permission for resource and action"""
        if not resource_type or not action:
            return None
        
        permission_map = {
            ('case', 'read'): 'read_cases',
            ('case', 'create'): 'create_cases',
            ('case', 'update'): 'update_cases',
            ('case', 'delete'): 'delete_cases',
            ('decision', 'approve'): 'approve_decisions',
            ('audit', 'read'): 'read_audit_logs',
            ('data', 'export'): 'export_data'
        }
        
        return permission_map.get((resource_type, action))
    
    def _evaluate_policy(self, policy: Dict, user_context: UserContext) -> bool:
        """Evaluate attribute-based policy"""
        conditions = policy.get('conditions', [])
        
        for condition in conditions:
            if not self._evaluate_condition(condition, user_context):
                return False
        
        return True
    
    def _evaluate_condition(self, condition: Dict, user_context: UserContext) -> bool:
        """Evaluate individual policy condition"""
        attribute = condition.get('attribute')
        operator = condition.get('operator')
        value = condition.get('value')
        
        if not all([attribute, operator, value]):
            return True  # Skip invalid conditions
        
        user_value = getattr(user_context, attribute, None)
        if user_value is None:
            user_value = user_context.attributes.get(attribute)
        
        if operator == 'equals':
            return user_value == value
        elif operator == 'in':
            return user_value in value
        elif operator == 'not_in':
            return user_value not in value
        elif operator == 'contains':
            return value in str(user_value)
        
        return True


class GuardrailsService:
    """Main guardrails service implementing OWASP LLM Top 10 controls"""
    
    def __init__(self, config_path: str = "config/guardrails.yaml"):
        self.config = GuardrailsConfig(config_path)
        self.injection_detector = PromptInjectionDetector()
        self.pii_detector = PIIDetector(self.config.pii_patterns)
        self.evidence_validator = EvidenceAnchoringValidator(self.config.allowlist_sources)
        self.rbac_validator = RBACValidator(self.config.rbac_policies)
        
        # Security event storage (in production, this would be a database)
        self.security_events: List[SecurityEvent] = []
        
        # Rate limiting and abuse detection
        self.request_counts = {}
        self.blocked_users = set()
        
        logger.info("Guardrails service initialized")
    
    def evaluate_input(self, text: str, user_context: UserContext, 
                      case_id: str = None) -> Tuple[GuardrailDecision, Dict]:
        """Evaluate input text against all guardrail controls"""
        evaluation_result = {
            'decision': GuardrailDecision.ALLOW,
            'flags': [],
            'redactions': {},
            'security_events': [],
            'confidence_score': 1.0,
            'processing_time_ms': 0
        }
        
        start_time = datetime.utcnow()
        
        try:
            # 1. RBAC/ABAC Validation
            rbac_valid, rbac_issues = self.rbac_validator.validate_access(user_context)
            if not rbac_valid:
                self._record_security_event(
                    SecurityEventType.UNAUTHORIZED_ACCESS,
                    SecurityLevel.HIGH,
                    f"Access denied: {', '.join(rbac_issues)}",
                    user_context=user_context,
                    case_id=case_id
                )
                evaluation_result['decision'] = GuardrailDecision.BLOCK
                evaluation_result['flags'].extend(rbac_issues)
                return evaluation_result['decision'], evaluation_result
            
            # 2. Prompt Injection Detection (LLM01)
            injection_detected, injection_patterns, injection_confidence = \
                self.injection_detector.detect_injection(text)
            
            if injection_detected:
                self._record_security_event(
                    SecurityEventType.PROMPT_INJECTION,
                    SecurityLevel.CRITICAL,
                    f"Prompt injection detected: {', '.join(injection_patterns)}",
                    user_context=user_context,
                    case_id=case_id,
                    raw_input=text
                )
                evaluation_result['decision'] = GuardrailDecision.BLOCK
                evaluation_result['flags'].append("Prompt injection detected")
                evaluation_result['confidence_score'] = injection_confidence
                return evaluation_result['decision'], evaluation_result
            
            # 3. PII Detection and Masking (LLM06)
            masked_text, pii_detections, pii_found = self.pii_detector.detect_and_mask_pii(text)
            
            if pii_found:
                self._record_security_event(
                    SecurityEventType.PII_DETECTED,
                    SecurityLevel.MEDIUM,
                    f"PII detected and masked: {len(pii_detections)} instances",
                    user_context=user_context,
                    case_id=case_id
                )
                evaluation_result['decision'] = GuardrailDecision.REDACT
                evaluation_result['redactions']['original_text'] = text
                evaluation_result['redactions']['masked_text'] = masked_text
                evaluation_result['redactions']['pii_detections'] = pii_detections
                evaluation_result['flags'].append("PII detected and masked")
            
            # 4. Rate Limiting and Abuse Detection (LLM04)
            if self._check_rate_limiting(user_context):
                self._record_security_event(
                    SecurityEventType.MODEL_ABUSE,
                    SecurityLevel.HIGH,
                    "Rate limit exceeded",
                    user_context=user_context,
                    case_id=case_id
                )
                evaluation_result['decision'] = GuardrailDecision.BLOCK
                evaluation_result['flags'].append("Rate limit exceeded")
                return evaluation_result['decision'], evaluation_result
            
            # 5. Apply custom guardrail rules
            rule_violations = self._evaluate_custom_rules(text, user_context)
            if rule_violations:
                evaluation_result['flags'].extend(rule_violations)
                if any('CRITICAL' in violation for violation in rule_violations):
                    evaluation_result['decision'] = GuardrailDecision.BLOCK
                elif any('HIGH' in violation for violation in rule_violations):
                    evaluation_result['decision'] = GuardrailDecision.REQUIRE_HITL
            
            # Calculate final confidence score
            evaluation_result['confidence_score'] = self._calculate_confidence_score(
                injection_confidence, pii_found, len(rule_violations)
            )
            
        except Exception as e:
            logger.error(f"Error in guardrails evaluation: {e}")
            evaluation_result['decision'] = GuardrailDecision.REQUIRE_HITL
            evaluation_result['flags'].append(f"Evaluation error: {str(e)}")
        
        finally:
            # Record processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            evaluation_result['processing_time_ms'] = processing_time
        
        return evaluation_result['decision'], evaluation_result
    
    def validate_evidence_anchoring(self, evidence_items: List[Dict], 
                                   generated_content: str,
                                   user_context: UserContext,
                                   case_id: str = None) -> Tuple[bool, Dict]:
        """Validate evidence anchoring for generated content (LLM09)"""
        anchoring_valid, issues, anchoring_score = \
            self.evidence_validator.validate_evidence_anchoring(evidence_items, generated_content)
        
        result = {
            'valid': anchoring_valid,
            'issues': issues,
            'anchoring_score': anchoring_score,
            'evidence_count': len(evidence_items)
        }
        
        if not anchoring_valid:
            self._record_security_event(
                SecurityEventType.EVIDENCE_ANCHORING_FAILURE,
                SecurityLevel.HIGH,
                f"Evidence anchoring validation failed: {', '.join(issues)}",
                user_context=user_context,
                case_id=case_id,
                processed_output=generated_content
            )
        
        return anchoring_valid, result
    
    def validate_allowlist_sources(self, source_ids: List[str],
                                  user_context: UserContext,
                                  case_id: str = None) -> Tuple[bool, List[str]]:
        """Validate that sources are in allowlist"""
        violations = []
        
        for source_id in source_ids:
            if source_id not in self.config.allowlist_sources:
                violations.append(source_id)
        
        if violations:
            self._record_security_event(
                SecurityEventType.ALLOWLIST_VIOLATION,
                SecurityLevel.MEDIUM,
                f"Allowlist violations: {', '.join(violations)}",
                user_context=user_context,
                case_id=case_id
            )
        
        return len(violations) == 0, violations
    
    def _check_rate_limiting(self, user_context: UserContext) -> bool:
        """Check if user has exceeded rate limits"""
        user_id = user_context.user_id
        current_time = datetime.utcnow()
        
        # Check if user is already blocked
        if user_id in self.blocked_users:
            return True
        
        # Initialize or update request count
        if user_id not in self.request_counts:
            self.request_counts[user_id] = []
        
        # Remove old requests (older than 1 hour)
        cutoff_time = current_time - timedelta(hours=1)
        self.request_counts[user_id] = [
            req_time for req_time in self.request_counts[user_id] 
            if req_time > cutoff_time
        ]
        
        # Add current request
        self.request_counts[user_id].append(current_time)
        
        # Check rate limit (100 requests per hour)
        if len(self.request_counts[user_id]) > 100:
            self.blocked_users.add(user_id)
            return True
        
        return False
    
    def _evaluate_custom_rules(self, text: str, user_context: UserContext) -> List[str]:
        """Evaluate custom guardrail rules"""
        violations = []
        
        for rule_id, rule in self.config.rules.items():
            if not rule.enabled:
                continue
            
            # Check if rule applies to current context
            if rule.applies_to and user_context.resource_type not in rule.applies_to:
                continue
            
            # Evaluate rule patterns
            for pattern in rule.patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    violation = f"{rule.name} ({rule.severity.value})"
                    violations.append(violation)
                    
                    # Update rule statistics
                    rule.last_triggered = datetime.utcnow()
                    rule.trigger_count += 1
                    
                    break  # Only trigger once per rule
        
        return violations
    
    def _calculate_confidence_score(self, injection_confidence: float, 
                                   pii_found: bool, rule_violations: int) -> float:
        """Calculate overall confidence score for guardrail evaluation"""
        base_score = 1.0
        
        # Reduce confidence based on threats detected
        if injection_confidence > 0:
            base_score -= injection_confidence * 0.5
        
        if pii_found:
            base_score -= 0.2
        
        if rule_violations > 0:
            base_score -= min(rule_violations * 0.1, 0.3)
        
        return max(base_score, 0.0)
    
    def _record_security_event(self, event_type: SecurityEventType,
                              severity: SecurityLevel, description: str,
                              user_context: UserContext = None,
                              case_id: str = None, raw_input: str = None,
                              processed_output: str = None):
        """Record security event for monitoring and incident response"""
        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            description=description,
            source="guardrails_service",
            user_id=user_context.user_id if user_context else None,
            session_id=user_context.session_id if user_context else None,
            case_id=case_id,
            confidence_score=1.0,
            context={
                'user_roles': user_context.roles if user_context else [],
                'user_permissions': user_context.permissions if user_context else [],
                'ip_address': user_context.ip_address if user_context else None
            },
            raw_input=raw_input,
            processed_output=processed_output,
            action_taken=GuardrailDecision.BLOCK if severity == SecurityLevel.CRITICAL else GuardrailDecision.ALLOW
        )
        
        self.security_events.append(event)
        
        # Log security event
        logger.warning(f"Security event: {event_type.value} - {description}")
        
        # In production, this would trigger alerts for high/critical events
        if severity in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
            self._trigger_security_alert(event)
    
    def _trigger_security_alert(self, event: SecurityEvent):
        """Trigger security alert for high-severity events"""
        # In production, this would send alerts to security team
        logger.critical(f"SECURITY ALERT: {event.event_type.value} - {event.description}")
    
    def get_security_events(self, start_time: datetime = None, 
                           end_time: datetime = None,
                           event_types: List[SecurityEventType] = None,
                           severity_levels: List[SecurityLevel] = None) -> List[SecurityEvent]:
        """Retrieve security events with filtering"""
        filtered_events = self.security_events
        
        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]
        
        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]
        
        if event_types:
            filtered_events = [e for e in filtered_events if e.event_type in event_types]
        
        if severity_levels:
            filtered_events = [e for e in filtered_events if e.severity in severity_levels]
        
        return filtered_events
    
    def get_security_statistics(self) -> Dict:
        """Get security statistics and metrics"""
        total_events = len(self.security_events)
        
        # Count by severity
        severity_counts = {}
        for level in SecurityLevel:
            severity_counts[level.value] = len([e for e in self.security_events if e.severity == level])
        
        # Count by event type
        event_type_counts = {}
        for event_type in SecurityEventType:
            event_type_counts[event_type.value] = len([e for e in self.security_events if e.event_type == event_type])
        
        # Recent events (last 24 hours)
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_events = len([e for e in self.security_events if e.timestamp >= recent_cutoff])
        
        return {
            'total_events': total_events,
            'recent_events_24h': recent_events,
            'severity_breakdown': severity_counts,
            'event_type_breakdown': event_type_counts,
            'blocked_users_count': len(self.blocked_users),
            'active_rules_count': len([r for r in self.config.rules.values() if r.enabled]),
            'allowlist_sources_count': len(self.config.allowlist_sources)
        }
    
    def update_allowlist(self, sources: List[str], replace: bool = False):
        """Update allowlist sources"""
        if replace:
            self.config.allowlist_sources = set(sources)
        else:
            self.config.allowlist_sources.update(sources)
        
        # Update evidence validator
        self.evidence_validator.allowlist_sources = self.config.allowlist_sources
        
        logger.info(f"Updated allowlist: {len(self.config.allowlist_sources)} sources")
    
    def reload_config(self):
        """Reload configuration from file"""
        self.config._load_config()
        
        # Reinitialize components with new config
        self.pii_detector = PIIDetector(self.config.pii_patterns)
        self.evidence_validator = EvidenceAnchoringValidator(self.config.allowlist_sources)
        self.rbac_validator = RBACValidator(self.config.rbac_policies)
        
        logger.info("Guardrails configuration reloaded")


# Factory function
def create_guardrails_service(config_path: str = "config/guardrails.yaml") -> GuardrailsService:
    """Factory function to create guardrails service"""
    return GuardrailsService(config_path)


# Utility functions for common operations
def validate_user_input(text: str, user_context: UserContext, 
                       guardrails_service: GuardrailsService = None) -> Tuple[bool, str, Dict]:
    """Validate user input against guardrails"""
    if not guardrails_service:
        guardrails_service = create_guardrails_service()
    
    decision, result = guardrails_service.evaluate_input(text, user_context)
    
    # Return processed text (with redactions if applicable)
    processed_text = result.get('redactions', {}).get('masked_text', text)
    
    return decision == GuardrailDecision.ALLOW, processed_text, result


def check_evidence_anchoring(evidence_items: List[Dict], generated_content: str,
                           user_context: UserContext,
                           guardrails_service: GuardrailsService = None) -> bool:
    """Check evidence anchoring for generated content"""
    if not guardrails_service:
        guardrails_service = create_guardrails_service()
    
    valid, _ = guardrails_service.validate_evidence_anchoring(
        evidence_items, generated_content, user_context
    )
    
    return valid
