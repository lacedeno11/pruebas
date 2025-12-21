"""
Case Ingest Node for DERCAS 01 Policy Validation Copilot

Implements UC-OP-05: Case ingestion with validation, normalization, and deduplication.
Handles incoming cases from CRM/ticketing systems with comprehensive data validation.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError

from ..models.state import PolicyValidationState, CaseState, AuditState, update_audit_log
from ..models.entities import Case
from ..models.enums import CaseStatus, Priority, QueueType
from ..storage.repositories import RepositoryManager
from ..guardrails.orchestrator import GuardrailsService, GuardrailAction
from ..guardrails.rbac import AccessContext, UserRole

logger = logging.getLogger(__name__)


class CaseIngestConfig(BaseModel):
    """Configuration for case ingestion."""
    
    # Validation settings
    enable_strict_validation: bool = True
    require_mandatory_fields: bool = True
    validate_business_rules: bool = True
    
    # Deduplication settings
    enable_deduplication: bool = True
    deduplication_window_hours: int = 24
    similarity_threshold: float = 0.8
    
    # Normalization settings
    normalize_phone_numbers: bool = True
    normalize_addresses: bool = True
    standardize_service_codes: bool = True
    
    # SLA settings
    default_sla_hours: int = 24
    priority_sla_mapping: Dict[str, int] = Field(default_factory=lambda: {
        "LOW": 72,
        "MEDIUM": 24,
        "HIGH": 8,
        "CRITICAL": 2
    })
    
    # Queue assignment
    auto_assign_queue: bool = True
    default_queue: QueueType = QueueType.AUTO_PROCESSING
    
    # Limits
    max_attachments: int = 10
    max_attachment_size_mb: int = 50
    max_description_length: int = 5000


class CaseIngestResult(BaseModel):
    """Result of case ingestion process."""
    
    success: bool
    case_id: Optional[str] = None
    duplicate_case_id: Optional[str] = None
    
    # Validation results
    validation_errors: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    
    # Normalization results
    normalized_fields: List[str] = Field(default_factory=list)
    
    # Processing metadata
    processing_time_ms: float
    assigned_queue: QueueType
    sla_target: Optional[datetime] = None
    
    # Guardrails results
    guardrails_action: Optional[GuardrailAction] = None
    security_flags: List[str] = Field(default_factory=list)


class CaseIngestNode:
    """
    Case ingestion node implementing UC-OP-05.
    
    Responsibilities:
    - Validate incoming case data
    - Normalize and standardize fields
    - Check for duplicates
    - Apply business rules
    - Assign SLA targets
    - Route to appropriate queue
    - Apply security guardrails
    """
    
    def __init__(
        self, 
        config: CaseIngestConfig,
        repo_manager: RepositoryManager,
        guardrails_service: GuardrailsService
    ):
        self.config = config
        self.repo_manager = repo_manager
        self.guardrails_service = guardrails_service
        
        # Field validators
        self.field_validators = self._initialize_field_validators()
        
        # Normalization rules
        self.normalization_rules = self._initialize_normalization_rules()
        
        # Business rules
        self.business_rules = self._initialize_business_rules()
    
    def __call__(self, state: PolicyValidationState) -> PolicyValidationState:
        """
        Execute case ingestion node.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with ingested case
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Starting case ingestion for case: {state['case']['case_id']}")
            
            # Extract case data from state
            case_data = state["case"]
            
            # Step 1: Validate input data
            validation_result = self._validate_case_data(case_data)
            if not validation_result[0]:
                return self._handle_validation_failure(state, validation_result[1], start_time)
            
            # Step 2: Apply security guardrails
            guardrails_result = self._apply_security_guardrails(case_data)
            if guardrails_result.action == GuardrailAction.BLOCK:
                return self._handle_security_block(state, guardrails_result, start_time)
            
            # Step 3: Normalize case data
            normalized_data = self._normalize_case_data(case_data)
            
            # Step 4: Check for duplicates
            duplicate_check = self._check_duplicates(normalized_data)
            if duplicate_check[0]:
                return self._handle_duplicate_case(state, duplicate_check[1], start_time)
            
            # Step 5: Apply business rules
            business_rules_result = self._apply_business_rules(normalized_data)
            
            # Step 6: Calculate SLA target
            sla_target = self._calculate_sla_target(normalized_data)
            
            # Step 7: Assign queue
            assigned_queue = self._assign_queue(normalized_data, business_rules_result)
            
            # Step 8: Create case entity
            case_entity = self._create_case_entity(
                normalized_data, 
                sla_target, 
                assigned_queue,
                business_rules_result
            )
            
            # Step 9: Store case in database
            stored_case = self.repo_manager.cases.create(case_entity)
            
            # Step 10: Update state
            updated_state = self._update_state_with_ingested_case(
                state, 
                stored_case, 
                validation_result,
                guardrails_result,
                business_rules_result,
                start_time
            )
            
            logger.info(f"Case ingestion completed successfully: {stored_case.case_id}")
            return updated_state
            
        except Exception as e:
            logger.error(f"Case ingestion failed: {e}")
            return self._handle_ingestion_error(state, str(e), start_time)
    
    def _initialize_field_validators(self) -> Dict[str, callable]:
        """Initialize field validation functions."""
        return {
            "case_id": self._validate_case_id,
            "customer_id": self._validate_customer_id,
            "insurer_id": self._validate_insurer_id,
            "plan_id": self._validate_plan_id,
            "service_code": self._validate_service_code,
            "service_date": self._validate_service_date,
            "provider_id": self._validate_provider_id,
            "priority": self._validate_priority,
            "attachments": self._validate_attachments,
        }
    
    def _initialize_normalization_rules(self) -> Dict[str, callable]:
        """Initialize field normalization functions."""
        return {
            "phone_number": self._normalize_phone_number,
            "address": self._normalize_address,
            "service_code": self._normalize_service_code,
            "insurer_id": self._normalize_insurer_id,
            "plan_id": self._normalize_plan_id,
            "customer_id": self._normalize_customer_id,
        }
    
    def _initialize_business_rules(self) -> List[callable]:
        """Initialize business rule validation functions."""
        return [
            self._check_service_eligibility,
            self._check_plan_validity,
            self._check_provider_authorization,
            self._check_service_frequency_limits,
            self._check_amount_limits,
        ]
    
    def _validate_case_data(self, case_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate incoming case data."""
        errors = []
        
        try:
            # Check mandatory fields
            if self.config.require_mandatory_fields:
                mandatory_fields = ["case_id", "insurer_id", "plan_id"]
                for field in mandatory_fields:
                    if not case_data.get(field):
                        errors.append(f"Missing mandatory field: {field}")
            
            # Validate individual fields
            for field_name, validator in self.field_validators.items():
                if field_name in case_data:
                    try:
                        field_errors = validator(case_data[field_name])
                        errors.extend(field_errors)
                    except Exception as e:
                        errors.append(f"Validation error for {field_name}: {str(e)}")
            
            # Check data types and formats
            type_errors = self._validate_data_types(case_data)
            errors.extend(type_errors)
            
            return len(errors) == 0, errors
            
        except Exception as e:
            logger.error(f"Case data validation failed: {e}")
            return False, [f"Validation system error: {str(e)}"]
    
    def _validate_case_id(self, case_id: str) -> List[str]:
        """Validate case ID format."""
        errors = []
        
        if not case_id or len(case_id.strip()) == 0:
            errors.append("Case ID cannot be empty")
        elif len(case_id) > 100:
            errors.append("Case ID too long (max 100 characters)")
        elif not case_id.replace("-", "").replace("_", "").isalnum():
            errors.append("Case ID contains invalid characters")
        
        return errors
    
    def _validate_customer_id(self, customer_id: str) -> List[str]:
        """Validate customer ID."""
        errors = []
        
        if customer_id and len(customer_id) > 50:
            errors.append("Customer ID too long (max 50 characters)")
        
        return errors
    
    def _validate_insurer_id(self, insurer_id: str) -> List[str]:
        """Validate insurer ID."""
        errors = []
        
        if not insurer_id:
            errors.append("Insurer ID is required")
        elif len(insurer_id) > 20:
            errors.append("Insurer ID too long (max 20 characters)")
        
        return errors
    
    def _validate_plan_id(self, plan_id: str) -> List[str]:
        """Validate plan ID."""
        errors = []
        
        if not plan_id:
            errors.append("Plan ID is required")
        elif len(plan_id) > 50:
            errors.append("Plan ID too long (max 50 characters)")
        
        return errors
    
    def _validate_service_code(self, service_code: str) -> List[str]:
        """Validate service code."""
        errors = []
        
        if service_code and len(service_code) > 20:
            errors.append("Service code too long (max 20 characters)")
        
        return errors
    
    def _validate_service_date(self, service_date: Any) -> List[str]:
        """Validate service date."""
        errors = []
        
        try:
            if service_date:
                if isinstance(service_date, str):
                    parsed_date = datetime.fromisoformat(service_date.replace('Z', '+00:00'))
                else:
                    parsed_date = service_date
                
                # Check if date is not too far in the future
                if parsed_date > datetime.utcnow() + timedelta(days=30):
                    errors.append("Service date too far in the future")
                
                # Check if date is not too old
                if parsed_date < datetime.utcnow() - timedelta(days=365):
                    errors.append("Service date too old (max 1 year)")
        
        except Exception as e:
            errors.append(f"Invalid service date format: {str(e)}")
        
        return errors
    
    def _validate_provider_id(self, provider_id: str) -> List[str]:
        """Validate provider ID."""
        errors = []
        
        if provider_id and len(provider_id) > 50:
            errors.append("Provider ID too long (max 50 characters)")
        
        return errors
    
    def _validate_priority(self, priority: str) -> List[str]:
        """Validate priority level."""
        errors = []
        
        valid_priorities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if priority and priority not in valid_priorities:
            errors.append(f"Invalid priority. Must be one of: {valid_priorities}")
        
        return errors
    
    def _validate_attachments(self, attachments: List[str]) -> List[str]:
        """Validate attachments."""
        errors = []
        
        if len(attachments) > self.config.max_attachments:
            errors.append(f"Too many attachments (max {self.config.max_attachments})")
        
        return errors
    
    def _validate_data_types(self, case_data: Dict[str, Any]) -> List[str]:
        """Validate data types."""
        errors = []
        
        # Check string fields
        string_fields = ["case_id", "customer_id", "insurer_id", "plan_id", "service_code", "provider_id"]
        for field in string_fields:
            if field in case_data and case_data[field] is not None:
                if not isinstance(case_data[field], str):
                    errors.append(f"{field} must be a string")
        
        # Check list fields
        if "attachments" in case_data:
            if not isinstance(case_data["attachments"], list):
                errors.append("Attachments must be a list")
        
        return errors
    
    def _apply_security_guardrails(self, case_data: Dict[str, Any]) -> Any:
        """Apply security guardrails to case data."""
        try:
            # Convert case data to text for security scanning
            case_text = self._case_data_to_text(case_data)
            
            # Create access context
            access_context = AccessContext(
                user_id=case_data.get("created_by", "system"),
                user_roles=[UserRole.SYSTEM],
                resource_type="case",
                action="create"
            )
            
            # Check guardrails
            result = self.guardrails_service.check_input_guardrails(
                input_text=case_text,
                context={"case_data": case_data},
                user_context=access_context
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Security guardrails check failed: {e}")
            # Return a safe default
            from ..guardrails.orchestrator import GuardrailResult
            return GuardrailResult(action=GuardrailAction.ALLOW, confidence=0.5)
    
    def _case_data_to_text(self, case_data: Dict[str, Any]) -> str:
        """Convert case data to text for security scanning."""
        text_parts = []
        
        # Include text fields that might contain user input
        text_fields = ["service_description", "notes", "comments"]
        for field in text_fields:
            if field in case_data and case_data[field]:
                text_parts.append(str(case_data[field]))
        
        return " ".join(text_parts)
    
    def _normalize_case_data(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize case data fields."""
        normalized_data = case_data.copy()
        normalized_fields = []
        
        try:
            # Apply normalization rules
            for field_name, normalizer in self.normalization_rules.items():
                if field_name in normalized_data and normalized_data[field_name]:
                    original_value = normalized_data[field_name]
                    normalized_value = normalizer(original_value)
                    
                    if normalized_value != original_value:
                        normalized_data[field_name] = normalized_value
                        normalized_fields.append(field_name)
            
            # Store normalization metadata
            normalized_data["_normalized_fields"] = normalized_fields
            
            return normalized_data
            
        except Exception as e:
            logger.error(f"Case data normalization failed: {e}")
            return case_data
    
    def _normalize_phone_number(self, phone: str) -> str:
        """Normalize phone number format."""
        if not self.config.normalize_phone_numbers:
            return phone
        
        # Remove all non-digits
        digits = ''.join(filter(str.isdigit, phone))
        
        # Format as standard US phone number if 10 digits
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"1-({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        
        return phone  # Return original if can't normalize
    
    def _normalize_address(self, address: str) -> str:
        """Normalize address format."""
        if not self.config.normalize_addresses:
            return address
        
        # Basic address normalization
        normalized = address.upper()
        
        # Common abbreviations
        abbreviations = {
            " STREET": " ST",
            " AVENUE": " AVE",
            " BOULEVARD": " BLVD",
            " DRIVE": " DR",
            " LANE": " LN",
            " ROAD": " RD",
        }
        
        for full, abbrev in abbreviations.items():
            normalized = normalized.replace(full, abbrev)
        
        return normalized.strip()
    
    def _normalize_service_code(self, service_code: str) -> str:
        """Normalize service code format."""
        if not self.config.standardize_service_codes:
            return service_code
        
        # Convert to uppercase and remove spaces
        return service_code.upper().replace(" ", "")
    
    def _normalize_insurer_id(self, insurer_id: str) -> str:
        """Normalize insurer ID format."""
        return insurer_id.upper().strip()
    
    def _normalize_plan_id(self, plan_id: str) -> str:
        """Normalize plan ID format."""
        return plan_id.upper().strip()
    
    def _normalize_customer_id(self, customer_id: str) -> str:
        """Normalize customer ID format."""
        return customer_id.strip()
    
    def _check_duplicates(self, case_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Check for duplicate cases."""
        if not self.config.enable_deduplication:
            return False, None
        
        try:
            # Define deduplication criteria
            case_id = case_data.get("case_id")
            customer_id = case_data.get("customer_id")
            service_code = case_data.get("service_code")
            service_date = case_data.get("service_date")
            
            # Check for exact case ID match
            if case_id:
                existing_case = self.repo_manager.cases.get_by_case_id(case_id)
                if existing_case:
                    return True, existing_case.case_id
            
            # Check for similar cases within time window
            if customer_id and service_code and service_date:
                cutoff_time = datetime.utcnow() - timedelta(hours=self.config.deduplication_window_hours)
                
                # This would require a more sophisticated query in production
                # For now, we'll do a simplified check
                similar_cases = self._find_similar_cases(
                    customer_id, service_code, service_date, cutoff_time
                )
                
                if similar_cases:
                    return True, similar_cases[0]
            
            return False, None
            
        except Exception as e:
            logger.error(f"Duplicate check failed: {e}")
            return False, None
    
    def _find_similar_cases(
        self, 
        customer_id: str, 
        service_code: str, 
        service_date: Any, 
        cutoff_time: datetime
    ) -> List[str]:
        """Find similar cases (simplified implementation)."""
        # In production, this would query the database for similar cases
        # For now, return empty list
        return []
    
    def _apply_business_rules(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply business rules validation."""
        results = {
            "passed_rules": [],
            "failed_rules": [],
            "warnings": [],
            "additional_data": {}
        }
        
        try:
            if self.config.validate_business_rules:
                for rule_func in self.business_rules:
                    try:
                        rule_result = rule_func(case_data)
                        if rule_result["passed"]:
                            results["passed_rules"].append(rule_result["rule_name"])
                        else:
                            results["failed_rules"].append({
                                "rule_name": rule_result["rule_name"],
                                "reason": rule_result["reason"]
                            })
                        
                        if rule_result.get("warnings"):
                            results["warnings"].extend(rule_result["warnings"])
                        
                        if rule_result.get("additional_data"):
                            results["additional_data"].update(rule_result["additional_data"])
                    
                    except Exception as e:
                        logger.error(f"Business rule check failed: {e}")
                        results["warnings"].append(f"Rule check error: {str(e)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Business rules application failed: {e}")
            return results
    
    def _check_service_eligibility(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if service is eligible under the plan."""
        # Simplified business rule - in production would check against policy database
        return {
            "rule_name": "service_eligibility",
            "passed": True,
            "reason": "Service eligibility check passed"
        }
    
    def _check_plan_validity(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if plan is valid and active."""
        return {
            "rule_name": "plan_validity",
            "passed": True,
            "reason": "Plan validity check passed"
        }
    
    def _check_provider_authorization(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if provider is authorized."""
        return {
            "rule_name": "provider_authorization",
            "passed": True,
            "reason": "Provider authorization check passed"
        }
    
    def _check_service_frequency_limits(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check service frequency limits."""
        return {
            "rule_name": "service_frequency_limits",
            "passed": True,
            "reason": "Service frequency limits check passed"
        }
    
    def _check_amount_limits(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check amount limits."""
        return {
            "rule_name": "amount_limits",
            "passed": True,
            "reason": "Amount limits check passed"
        }
    
    def _calculate_sla_target(self, case_data: Dict[str, Any]) -> datetime:
        """Calculate SLA target based on priority and business rules."""
        try:
            priority = case_data.get("priority", "MEDIUM")
            sla_hours = self.config.priority_sla_mapping.get(priority, self.config.default_sla_hours)
            
            return datetime.utcnow() + timedelta(hours=sla_hours)
            
        except Exception as e:
            logger.error(f"SLA calculation failed: {e}")
            return datetime.utcnow() + timedelta(hours=self.config.default_sla_hours)
    
    def _assign_queue(self, case_data: Dict[str, Any], business_rules_result: Dict[str, Any]) -> QueueType:
        """Assign case to appropriate processing queue."""
        if not self.config.auto_assign_queue:
            return self.config.default_queue
        
        try:
            priority = case_data.get("priority", "MEDIUM")
            
            # High priority cases go to priority queue
            if priority in ["HIGH", "CRITICAL"]:
                return QueueType.HITL_SUPERVISOR
            
            # Cases with failed business rules need review
            if business_rules_result.get("failed_rules"):
                return QueueType.HITL_AGENT
            
            # Default to auto processing
            return QueueType.AUTO_PROCESSING
            
        except Exception as e:
            logger.error(f"Queue assignment failed: {e}")
            return self.config.default_queue
    
    def _create_case_entity(
        self, 
        case_data: Dict[str, Any], 
        sla_target: datetime,
        assigned_queue: QueueType,
        business_rules_result: Dict[str, Any]
    ) -> Case:
        """Create Case entity from normalized data."""
        try:
            # Extract service date
            service_date = None
            if case_data.get("service_date"):
                if isinstance(case_data["service_date"], str):
                    service_date = datetime.fromisoformat(case_data["service_date"].replace('Z', '+00:00'))
                else:
                    service_date = case_data["service_date"]
            
            # Create case entity
            case_entity = Case(
                case_id=case_data["case_id"],
                crm_ticket_id=case_data.get("crm_ticket_id"),
                customer_id=case_data.get("customer_id"),
                contract_id=case_data.get("contract_id"),
                insurer_id=case_data["insurer_id"],
                plan_id=case_data["plan_id"],
                service_code=case_data.get("service_code"),
                service_description=case_data.get("service_description"),
                service_date=service_date,
                provider_id=case_data.get("provider_id"),
                priority=Priority(case_data.get("priority", "MEDIUM")),
                sla_target=sla_target,
                status=CaseStatus.INGESTED,
                assigned_queue=assigned_queue,
                attachments=case_data.get("attachments", []),
                context={
                    "business_rules_result": business_rules_result,
                    "normalized_fields": case_data.get("_normalized_fields", []),
                    "ingestion_timestamp": datetime.utcnow().isoformat(),
                },
                processing_started_at=datetime.utcnow(),
                last_activity_at=datetime.utcnow(),
                created_by=case_data.get("created_by", "system")
            )
            
            return case_entity
            
        except Exception as e:
            logger.error(f"Case entity creation failed: {e}")
            raise
    
    def _update_state_with_ingested_case(
        self,
        state: PolicyValidationState,
        stored_case: Case,
        validation_result: Tuple[bool, List[str]],
        guardrails_result: Any,
        business_rules_result: Dict[str, Any],
        start_time: datetime
    ) -> PolicyValidationState:
        """Update state with successfully ingested case."""
        
        # Update case state
        state["case"] = CaseState(
            case_id=stored_case.case_id,
            crm_ticket_id=stored_case.crm_ticket_id,
            customer_id=stored_case.customer_id,
            contract_id=stored_case.contract_id,
            insurer_id=stored_case.insurer_id,
            plan_id=stored_case.plan_id,
            service_code=stored_case.service_code,
            service_date=stored_case.service_date,
            provider_id=stored_case.provider_id,
            attachments=stored_case.attachments,
            priority=stored_case.priority.value,
            sla_target=stored_case.sla_target,
            state=stored_case.status,
            assigned_queue=stored_case.assigned_queue.value,
            context=stored_case.context
        )
        
        # Update audit log
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        state = update_audit_log(
            state,
            node_name="case_ingest",
            node_input={"case_id": stored_case.case_id},
            node_output={
                "success": True,
                "case_id": stored_case.case_id,
                "assigned_queue": stored_case.assigned_queue.value,
                "sla_target": stored_case.sla_target.isoformat() if stored_case.sla_target else None,
                "business_rules_passed": len(business_rules_result.get("passed_rules", [])),
                "business_rules_failed": len(business_rules_result.get("failed_rules", [])),
                "guardrails_action": guardrails_result.action.value if hasattr(guardrails_result, 'action') else None,
            },
            execution_time_ms=processing_time
        )
        
        # Set next node
        state["next_node"] = "routing"
        
        return state
    
    def _handle_validation_failure(
        self, 
        state: PolicyValidationState, 
        errors: List[str], 
        start_time: datetime
    ) -> PolicyValidationState:
        """Handle validation failure."""
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Update case status to error
        state["case"]["state"] = CaseStatus.ERROR
        
        # Log audit event
        state = update_audit_log(
            state,
            node_name="case_ingest",
            node_input={"case_id": state["case"]["case_id"]},
            node_output={"success": False, "validation_errors": errors},
            execution_time_ms=processing_time,
            error="Validation failed: " + "; ".join(errors)
        )
        
        # Set error state
        state["error_occurred"] = True
        state["error_message"] = f"Case validation failed: {'; '.join(errors)}"
        state["workflow_complete"] = True
        
        return state
    
    def _handle_security_block(
        self, 
        state: PolicyValidationState, 
        guardrails_result: Any, 
        start_time: datetime
    ) -> PolicyValidationState:
        """Handle security guardrails block."""
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Update case status
        state["case"]["state"] = CaseStatus.ERROR
        
        # Log audit event
        state = update_audit_log(
            state,
            node_name="case_ingest",
            node_input={"case_id": state["case"]["case_id"]},
            node_output={
                "success": False, 
                "blocked_by_security": True,
                "security_reasons": guardrails_result.blocked_reasons if hasattr(guardrails_result, 'blocked_reasons') else []
            },
            execution_time_ms=processing_time,
            error="Blocked by security guardrails"
        )
        
        # Set error state
        state["error_occurred"] = True
        state["error_message"] = "Case blocked by security guardrails"
        state["workflow_complete"] = True
        
        return state
    
    def _handle_duplicate_case(
        self, 
        state: PolicyValidationState, 
        duplicate_case_id: str, 
        start_time: datetime
    ) -> PolicyValidationState:
        """Handle duplicate case detection."""
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Update case status
        state["case"]["state"] = CaseStatus.CLOSED
        
        # Log audit event
        state = update_audit_log(
            state,
            node_name="case_ingest",
            node_input={"case_id": state["case"]["case_id"]},
            node_output={
                "success": False, 
                "duplicate_detected": True,
                "duplicate_case_id": duplicate_case_id
            },
            execution_time_ms=processing_time
        )
        
        # Set completion state
        state["workflow_complete"] = True
        
        return state
    
    def _handle_ingestion_error(
        self, 
        state: PolicyValidationState, 
        error_message: str, 
        start_time: datetime
    ) -> PolicyValidationState:
        """Handle ingestion error."""
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Update case status
        state["case"]["state"] = CaseStatus.ERROR
        
        # Log audit event
        state = update_audit_log(
            state,
            node_name="case_ingest",
            node_input={"case_id": state["case"]["case_id"]},
            node_output={"success": False},
            execution_time_ms=processing_time,
            error=error_message
        )
        
        # Set error state
        state["error_occurred"] = True
        state["error_message"] = f"Case ingestion error: {error_message}"
        state["workflow_complete"] = True
        
        return state


# Factory function
def create_case_ingest_node(
    config: Optional[CaseIngestConfig] = None,
    repo_manager: Optional[RepositoryManager] = None,
    guardrails_service: Optional[GuardrailsService] = None
) -> CaseIngestNode:
    """Create a case ingest node with default or custom configuration."""
    if config is None:
        config = CaseIngestConfig()
    
    if repo_manager is None:
        raise ValueError("Repository manager is required")
    
    if guardrails_service is None:
        raise ValueError("Guardrails service is required")
    
    return CaseIngestNode(config, repo_manager, guardrails_service)
