"""
Rules & Checklist Builder Agent (UC-OP-07)

This module implements the Rules & Checklist Builder Agent for the Policy Validation Copilot system,
providing policy-as-code rule engine, checklist evaluation logic, exception handling,
missing field detection, and deterministic rule execution.
"""

from typing import Dict, Any, List, Optional, Tuple, Set, Union
from datetime import datetime, timedelta
import logging
import asyncio
import json
import re
from dataclasses import dataclass
from enum import Enum

from ..state import PolicyValidationState, Checklist, ChecklistItem, ChecklistOutcome
from ..database import (
    PolicyRepository, PolicyExceptionRepository, EvidencePackRepository,
    get_repository_factory
)
from ..guardrails import create_security_context, evaluate_payload_security

logger = logging.getLogger(__name__)


class RuleType(str, Enum):
    """Types of rules in the rule engine"""
    ELIGIBILITY = "ELIGIBILITY"
    COVERAGE = "COVERAGE"
    EXCLUSION = "EXCLUSION"
    LIMITATION = "LIMITATION"
    AUTHORIZATION = "AUTHORIZATION"
    DOCUMENTATION = "DOCUMENTATION"
    VALIDATION = "VALIDATION"


class RuleOperator(str, Enum):
    """Rule evaluation operators"""
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    GREATER_THAN = "GREATER_THAN"
    LESS_THAN = "LESS_THAN"
    GREATER_EQUAL = "GREATER_EQUAL"
    LESS_EQUAL = "LESS_EQUAL"
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"
    IN = "IN"
    NOT_IN = "NOT_IN"
    REGEX_MATCH = "REGEX_MATCH"
    EXISTS = "EXISTS"
    NOT_EXISTS = "NOT_EXISTS"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


@dataclass
class RuleCondition:
    """Individual rule condition"""
    field_path: str
    operator: RuleOperator
    value: Any
    description: str = ""


@dataclass
class Rule:
    """Policy rule definition"""
    rule_id: str
    name: str
    description: str
    rule_type: RuleType
    conditions: List[RuleCondition]
    outcome: ChecklistOutcome
    priority: int = 100
    enabled: bool = True
    evidence_required: bool = True
    error_message: str = ""
    success_message: str = ""
    metadata: Dict[str, Any] = None


@dataclass
class RuleEvaluationResult:
    """Result of rule evaluation"""
    rule_id: str
    outcome: ChecklistOutcome
    passed: bool
    message: str
    evidence_refs: List[str]
    missing_fields: List[str]
    evaluation_details: Dict[str, Any]
    processing_time_ms: int


class PolicyAsCodeEngine:
    """
    Policy-as-code rule engine for deterministic rule execution.
    
    Provides a declarative way to define and execute policy rules
    with support for complex conditions and evidence validation.
    """
    
    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self.rule_sets: Dict[str, List[str]] = {}
        self.evaluation_cache: Dict[str, RuleEvaluationResult] = {}
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default policy rules"""
        
        # Eligibility rules
        self.register_rule(Rule(
            rule_id="ELIG_001",
            name="Customer Active Status",
            description="Customer must have active status",
            rule_type=RuleType.ELIGIBILITY,
            conditions=[
                RuleCondition("case.customer_status", RuleOperator.EQUALS, "ACTIVE", "Customer status check")
            ],
            outcome=ChecklistOutcome.PASS,
            error_message="Customer status is not active",
            success_message="Customer has active status"
        ))
        
        self.register_rule(Rule(
            rule_id="ELIG_002",
            name="Plan Coverage Active",
            description="Insurance plan must be active and not expired",
            rule_type=RuleType.ELIGIBILITY,
            conditions=[
                RuleCondition("case.plan_status", RuleOperator.EQUALS, "ACTIVE", "Plan status check"),
                RuleCondition("case.plan_expiry_date", RuleOperator.GREATER_THAN, "TODAY", "Plan expiry check")
            ],
            outcome=ChecklistOutcome.PASS,
            error_message="Insurance plan is not active or has expired",
            success_message="Insurance plan is active and valid"
        ))
        
        # Coverage rules
        self.register_rule(Rule(
            rule_id="COV_001",
            name="Service Code Coverage",
            description="Service code must be covered under the plan",
            rule_type=RuleType.COVERAGE,
            conditions=[
                RuleCondition("evidence_pack.coverage_confirmed", RuleOperator.EQUALS, True, "Coverage confirmation")
            ],
            outcome=ChecklistOutcome.PASS,
            error_message="Service code is not covered under the current plan",
            success_message="Service code is covered under the plan"
        ))
        
        self.register_rule(Rule(
            rule_id="COV_002",
            name="Amount Within Limits",
            description="Service amount must be within plan limits",
            rule_type=RuleType.COVERAGE,
            conditions=[
                RuleCondition("case.service_amount", RuleOperator.LESS_EQUAL, "plan.max_amount", "Amount limit check")
            ],
            outcome=ChecklistOutcome.PASS,
            error_message="Service amount exceeds plan limits",
            success_message="Service amount is within plan limits"
        ))
        
        # Exclusion rules
        self.register_rule(Rule(
            rule_id="EXC_001",
            name="Pre-existing Condition Check",
            description="Service must not be related to excluded pre-existing conditions",
            rule_type=RuleType.EXCLUSION,
            conditions=[
                RuleCondition("case.diagnosis_codes", RuleOperator.NOT_IN, "plan.excluded_conditions", "Pre-existing check")
            ],
            outcome=ChecklistOutcome.PASS,
            error_message="Service is related to excluded pre-existing condition",
            success_message="No excluded pre-existing conditions found"
        ))
        
        # Documentation rules
        self.register_rule(Rule(
            rule_id="DOC_001",
            name="Required Documentation",
            description="All required documentation must be present",
            rule_type=RuleType.DOCUMENTATION,
            conditions=[
                RuleCondition("case.attachments", RuleOperator.EXISTS, None, "Attachments present"),
                RuleCondition("evidence_pack.items", RuleOperator.EXISTS, None, "Evidence items present")
            ],
            outcome=ChecklistOutcome.PASS,
            error_message="Required documentation is missing",
            success_message="All required documentation is present"
        ))
        
        # Authorization rules
        self.register_rule(Rule(
            rule_id="AUTH_001",
            name="Prior Authorization Check",
            description="Check if prior authorization is required and obtained",
            rule_type=RuleType.AUTHORIZATION,
            conditions=[
                RuleCondition("case.prior_auth_required", RuleOperator.EQUALS, False, "Prior auth not required"),
                RuleCondition("case.prior_auth_obtained", RuleOperator.EQUALS, True, "Prior auth obtained")
            ],
            outcome=ChecklistOutcome.PASS,
            error_message="Prior authorization required but not obtained",
            success_message="Prior authorization requirements met"
        ))
        
        # Create rule sets
        self.rule_sets["STANDARD_MEDICAL"] = ["ELIG_001", "ELIG_002", "COV_001", "COV_002", "DOC_001"]
        self.rule_sets["HIGH_COST_PROCEDURE"] = ["ELIG_001", "ELIG_002", "COV_001", "COV_002", "AUTH_001", "DOC_001"]
        self.rule_sets["EMERGENCY_CARE"] = ["ELIG_001", "ELIG_002", "COV_001", "DOC_001"]
    
    def register_rule(self, rule: Rule) -> None:
        """Register a rule with the engine"""
        self.rules[rule.rule_id] = rule
        logger.info(f"Registered rule: {rule.rule_id} - {rule.name}")
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get rule by ID"""
        return self.rules.get(rule_id)
    
    def get_rules_by_type(self, rule_type: RuleType) -> List[Rule]:
        """Get all rules of a specific type"""
        return [rule for rule in self.rules.values() if rule.rule_type == rule_type and rule.enabled]
    
    def get_rule_set(self, rule_set_name: str) -> List[Rule]:
        """Get rules in a rule set"""
        rule_ids = self.rule_sets.get(rule_set_name, [])
        return [self.rules[rule_id] for rule_id in rule_ids if rule_id in self.rules and self.rules[rule_id].enabled]
    
    async def evaluate_rule(
        self, 
        rule: Rule, 
        context: Dict[str, Any],
        evidence_pack: Dict[str, Any] = None
    ) -> RuleEvaluationResult:
        """Evaluate a single rule against context"""
        
        start_time = datetime.utcnow()
        
        try:
            # Check cache first
            cache_key = f"{rule.rule_id}:{hash(str(context))}"
            if cache_key in self.evaluation_cache:
                return self.evaluation_cache[cache_key]
            
            # Evaluate all conditions
            condition_results = []
            missing_fields = []
            evidence_refs = []
            
            for condition in rule.conditions:
                result = await self._evaluate_condition(condition, context, evidence_pack)
                condition_results.append(result)
                
                if result["missing_field"]:
                    missing_fields.append(result["missing_field"])
                
                if result["evidence_ref"]:
                    evidence_refs.append(result["evidence_ref"])
            
            # Determine overall rule outcome
            passed = all(result["passed"] for result in condition_results)
            
            # Determine checklist outcome
            if passed:
                outcome = rule.outcome
                message = rule.success_message or f"Rule {rule.rule_id} passed"
            else:
                outcome = ChecklistOutcome.FAIL
                message = rule.error_message or f"Rule {rule.rule_id} failed"
            
            # Handle missing fields
            if missing_fields:
                outcome = ChecklistOutcome.MISSING
                message = f"Missing required fields: {', '.join(missing_fields)}"
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Create result
            result = RuleEvaluationResult(
                rule_id=rule.rule_id,
                outcome=outcome,
                passed=passed,
                message=message,
                evidence_refs=evidence_refs,
                missing_fields=missing_fields,
                evaluation_details={
                    "rule_name": rule.name,
                    "rule_type": rule.rule_type.value,
                    "condition_results": condition_results,
                    "conditions_passed": sum(1 for r in condition_results if r["passed"]),
                    "total_conditions": len(condition_results)
                },
                processing_time_ms=int(processing_time)
            )
            
            # Cache result
            self.evaluation_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Rule evaluation failed for {rule.rule_id}: {e}")
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                outcome=ChecklistOutcome.UNKNOWN,
                passed=False,
                message=f"Rule evaluation error: {str(e)}",
                evidence_refs=[],
                missing_fields=[],
                evaluation_details={"error": str(e)},
                processing_time_ms=int(processing_time)
            )
    
    async def _evaluate_condition(
        self, 
        condition: RuleCondition, 
        context: Dict[str, Any],
        evidence_pack: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Evaluate a single condition"""
        
        try:
            # Get field value from context
            field_value = self._get_field_value(condition.field_path, context, evidence_pack)
            
            # Handle missing field
            if field_value is None and condition.operator not in [RuleOperator.NOT_EXISTS, RuleOperator.EXISTS]:
                return {
                    "passed": False,
                    "missing_field": condition.field_path,
                    "evidence_ref": None,
                    "details": f"Field {condition.field_path} is missing"
                }
            
            # Evaluate condition based on operator
            passed = self._apply_operator(condition.operator, field_value, condition.value, context)
            
            # Find evidence reference
            evidence_ref = self._find_evidence_reference(condition.field_path, evidence_pack)
            
            return {
                "passed": passed,
                "missing_field": None,
                "evidence_ref": evidence_ref,
                "details": f"{condition.field_path} {condition.operator.value} {condition.value} = {passed}"
            }
            
        except Exception as e:
            logger.error(f"Condition evaluation failed: {e}")
            return {
                "passed": False,
                "missing_field": None,
                "evidence_ref": None,
                "details": f"Evaluation error: {str(e)}"
            }
    
    def _get_field_value(self, field_path: str, context: Dict[str, Any], evidence_pack: Dict[str, Any] = None) -> Any:
        """Get field value from context using dot notation"""
        
        # Handle special values
        if field_path == "TODAY":
            return datetime.utcnow().date()
        
        # Split path and navigate
        parts = field_path.split('.')
        current = context
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                index = int(part)
                current = current[index] if 0 <= index < len(current) else None
            else:
                return None
            
            if current is None:
                break
        
        return current
    
    def _apply_operator(self, operator: RuleOperator, field_value: Any, condition_value: Any, context: Dict[str, Any]) -> bool:
        """Apply operator to compare field value with condition value"""
        
        try:
            if operator == RuleOperator.EQUALS:
                return field_value == condition_value
            
            elif operator == RuleOperator.NOT_EQUALS:
                return field_value != condition_value
            
            elif operator == RuleOperator.GREATER_THAN:
                return self._compare_values(field_value, condition_value, context) > 0
            
            elif operator == RuleOperator.LESS_THAN:
                return self._compare_values(field_value, condition_value, context) < 0
            
            elif operator == RuleOperator.GREATER_EQUAL:
                return self._compare_values(field_value, condition_value, context) >= 0
            
            elif operator == RuleOperator.LESS_EQUAL:
                return self._compare_values(field_value, condition_value, context) <= 0
            
            elif operator == RuleOperator.CONTAINS:
                return condition_value in str(field_value) if field_value else False
            
            elif operator == RuleOperator.NOT_CONTAINS:
                return condition_value not in str(field_value) if field_value else True
            
            elif operator == RuleOperator.IN:
                return field_value in condition_value if isinstance(condition_value, (list, tuple, set)) else False
            
            elif operator == RuleOperator.NOT_IN:
                return field_value not in condition_value if isinstance(condition_value, (list, tuple, set)) else True
            
            elif operator == RuleOperator.REGEX_MATCH:
                return bool(re.match(condition_value, str(field_value))) if field_value else False
            
            elif operator == RuleOperator.EXISTS:
                return field_value is not None
            
            elif operator == RuleOperator.NOT_EXISTS:
                return field_value is None
            
            else:
                logger.warning(f"Unknown operator: {operator}")
                return False
                
        except Exception as e:
            logger.error(f"Operator application failed: {e}")
            return False
    
    def _compare_values(self, value1: Any, value2: Any, context: Dict[str, Any]) -> int:
        """Compare two values, handling special cases"""
        
        # Handle date comparisons
        if isinstance(value1, (datetime, str)) and value2 == "TODAY":
            if isinstance(value1, str):
                try:
                    value1 = datetime.fromisoformat(value1.replace('Z', '+00:00')).date()
                except:
                    return 0
            elif isinstance(value1, datetime):
                value1 = value1.date()
            
            today = datetime.utcnow().date()
            
            if value1 > today:
                return 1
            elif value1 < today:
                return -1
            else:
                return 0
        
        # Handle reference values (e.g., "plan.max_amount")
        if isinstance(value2, str) and '.' in value2:
            resolved_value = self._get_field_value(value2, context)
            if resolved_value is not None:
                value2 = resolved_value
        
        # Numeric comparison
        try:
            if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
                return (value1 > value2) - (value1 < value2)
        except:
            pass
        
        # String comparison
        try:
            str1, str2 = str(value1), str(value2)
            return (str1 > str2) - (str1 < str2)
        except:
            return 0
    
    def _find_evidence_reference(self, field_path: str, evidence_pack: Dict[str, Any] = None) -> Optional[str]:
        """Find evidence reference for a field"""
        
        if not evidence_pack or not evidence_pack.get("items"):
            return None
        
        # Look for evidence items that might support this field
        for item in evidence_pack["items"]:
            excerpt = item.get("excerpt", "").lower()
            
            # Simple heuristic - look for field-related keywords in excerpt
            if any(keyword in excerpt for keyword in field_path.split('.')):
                return f"{item.get('doc_id')}#{item.get('pointer')}"
        
        return None


class RulesChecklistAgent:
    """
    Rules & Checklist Builder Agent implementing UC-OP-07.
    
    Provides policy-as-code rule engine, checklist evaluation logic,
    exception handling, missing field detection, and deterministic rule execution.
    """
    
    def __init__(self, use_mock: bool = False):
        self.rule_engine = PolicyAsCodeEngine()
        self.repo_factory = get_repository_factory()
        self.use_mock = use_mock
        
        # Configuration
        self.max_concurrent_rules = 10
        self.rule_timeout_seconds = 30
        self.cache_enabled = True
        
        # Statistics
        self.evaluation_stats = {
            "total_evaluations": 0,
            "passed_rules": 0,
            "failed_rules": 0,
            "missing_field_rules": 0,
            "error_rules": 0
        }
    
    async def build_checklist(
        self, 
        state: PolicyValidationState,
        rule_set_name: str = None
    ) -> PolicyValidationState:
        """
        Main entry point for checklist building and rule evaluation.
        
        Args:
            state: Current policy validation state
            rule_set_name: Optional specific rule set to evaluate
            
        Returns:
            Updated state with checklist
        """
        start_time = datetime.utcnow()
        
        try:
            # Extract context from state
            case = state["case"]
            evidence_pack = state.get("evidence_pack", {})
            ml_results = state.get("ml", {})
            
            case_id = case["case_id"]
            
            logger.info(f"Starting checklist building for case {case_id}")
            
            # Determine rule set to use
            if not rule_set_name:
                rule_set_name = await self._determine_rule_set(case, ml_results)
            
            # Get rules to evaluate
            rules = self.rule_engine.get_rule_set(rule_set_name)
            
            if not rules:
                logger.warning(f"No rules found for rule set: {rule_set_name}")
                rules = self.rule_engine.get_rules_by_type(RuleType.ELIGIBILITY)
            
            # Apply policy exceptions before evaluation
            rules = await self._apply_policy_exceptions(rules, case)
            
            # Build evaluation context
            context = await self._build_evaluation_context(state)
            
            # Evaluate rules
            rule_results = await self._evaluate_rules(rules, context, evidence_pack)
            
            # Build checklist from results
            checklist = await self._build_checklist_from_results(rule_results, rule_set_name)
            
            # Detect missing fields
            missing_fields = await self._detect_missing_fields(rule_results, context)
            
            # Update checklist with missing fields
            checklist["missing_fields"] = missing_fields
            
            # Calculate completion percentage
            checklist["completion_percentage"] = self._calculate_completion_percentage(checklist)
            
            # Update state
            state["checklist"] = checklist
            
            # Update statistics
            await self._update_statistics(rule_results)
            
            # Log evaluation metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            await self._log_evaluation_metrics(
                case_id, len(rules), len(rule_results), 
                checklist["completion_percentage"], processing_time
            )
            
            logger.info(
                f"Checklist building completed for case {case_id}: "
                f"{len(rule_results)} rules evaluated, "
                f"{checklist['completion_percentage']:.1f}% complete"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"Checklist building failed for case {case.get('case_id', 'unknown')}: {e}")
            
            # Create empty checklist on failure
            state["checklist"] = {
                "items": [],
                "missing_fields": [],
                "rule_ids_applied": [],
                "completion_percentage": 0.0,
                "evaluation_timestamp": datetime.utcnow(),
                "rule_set_used": rule_set_name or "UNKNOWN"
            }
            
            raise
    
    async def _determine_rule_set(self, case: Dict[str, Any], ml_results: Dict[str, Any]) -> str:
        """Determine appropriate rule set based on case and ML results"""
        
        # Use ML classification if available
        classification = ml_results.get("classification", {})
        request_type = classification.get("request_type", "")
        
        if request_type == "EMERGENCY_CARE":
            return "EMERGENCY_CARE"
        
        # Check service amount for high-cost procedures
        service_amount = case.get("service_amount", 0.0)
        if service_amount > 5000:
            return "HIGH_COST_PROCEDURE"
        
        # Check service code patterns
        service_code = case.get("service_code", "").upper()
        if any(keyword in service_code for keyword in ["SURGERY", "OPERATION", "PROCEDURE"]):
            return "HIGH_COST_PROCEDURE"
        
        # Default to standard medical
        return "STANDARD_MEDICAL"
    
    async def _apply_policy_exceptions(self, rules: List[Rule], case: Dict[str, Any]) -> List[Rule]:
        """Apply policy exceptions to modify rules (RB-03)"""
        
        # Get active policy exceptions
        exception_repo = self.repo_factory.policy_exception_repository()
        active_exceptions = exception_repo.get_active_exceptions()
        
        if not active_exceptions:
            return rules
        
        modified_rules = []
        
        for rule in rules:
            # Check if any exception applies to this rule and case
            applicable_exceptions = []
            
            for exception in active_exceptions:
                if self._exception_applies_to_rule(exception, rule, case):
                    applicable_exceptions.append(exception)
            
            if applicable_exceptions:
                # Apply exception modifications
                modified_rule = await self._apply_exception_to_rule(rule, applicable_exceptions)
                modified_rules.append(modified_rule)
                
                # Log exception usage
                for exception in applicable_exceptions:
                    exception_repo.increment_usage(exception.exception_id)
                    logger.info(
                        f"Applied policy exception {exception.exception_id} "
                        f"to rule {rule.rule_id}"
                    )
            else:
                modified_rules.append(rule)
        
        return modified_rules
    
    def _exception_applies_to_rule(self, exception: Any, rule: Rule, case: Dict[str, Any]) -> bool:
        """Check if policy exception applies to rule and case"""
        
        scope_criteria = exception.scope_criteria or {}
        
        # Check rule criteria
        if "rule_ids" in scope_criteria:
            if rule.rule_id not in scope_criteria["rule_ids"]:
                return False
        
        if "rule_types" in scope_criteria:
            if rule.rule_type.value not in scope_criteria["rule_types"]:
                return False
        
        # Check case criteria (reuse logic from policy retrieval)
        if "service_codes" in scope_criteria:
            if case.get("service_code") not in scope_criteria["service_codes"]:
                return False
        
        if "insurer_ids" in scope_criteria:
            if case.get("insurer_id") not in scope_criteria["insurer_ids"]:
                return False
        
        return True
    
    async def _apply_exception_to_rule(self, rule: Rule, exceptions: List[Any]) -> Rule:
        """Apply exception modifications to a rule"""
        
        # Create modified rule copy
        modified_rule = Rule(
            rule_id=rule.rule_id,
            name=rule.name,
            description=rule.description,
            rule_type=rule.rule_type,
            conditions=rule.conditions.copy(),
            outcome=rule.outcome,
            priority=rule.priority,
            enabled=rule.enabled,
            evidence_required=rule.evidence_required,
            error_message=rule.error_message,
            success_message=rule.success_message,
            metadata=rule.metadata.copy() if rule.metadata else {}
        )
        
        # Apply overrides from exceptions
        for exception in exceptions:
            override_rules = exception.override_rules or {}
            
            # Override outcome
            if "outcome" in override_rules:
                outcome_str = override_rules["outcome"]
                if outcome_str in [e.value for e in ChecklistOutcome]:
                    modified_rule.outcome = ChecklistOutcome(outcome_str)
            
            # Override enabled status
            if "enabled" in override_rules:
                modified_rule.enabled = override_rules["enabled"]
            
            # Override messages
            if "error_message" in override_rules:
                modified_rule.error_message = override_rules["error_message"]
            
            if "success_message" in override_rules:
                modified_rule.success_message = override_rules["success_message"]
            
            # Add exception metadata
            if not modified_rule.metadata:
                modified_rule.metadata = {}
            modified_rule.metadata["applied_exceptions"] = modified_rule.metadata.get("applied_exceptions", [])
            modified_rule.metadata["applied_exceptions"].append(exception.exception_id)
        
        return modified_rule
    
    async def _build_evaluation_context(self, state: PolicyValidationState) -> Dict[str, Any]:
        """Build evaluation context from state"""
        
        context = {
            "case": state["case"],
            "evidence_pack": state.get("evidence_pack", {}),
            "ml": state.get("ml", {}),
            "guardrails": state.get("guardrails", {}),
            "timestamp": datetime.utcnow()
        }
        
        # Add derived fields
        case = state["case"]
        
        # Add plan information (would be fetched from database in real implementation)
        context["plan"] = await self._get_plan_information(case.get("plan_id"))
        
        # Add customer information
        context["customer"] = await self._get_customer_information(case.get("customer_id"))
        
        return context
    
    async def _get_plan_information(self, plan_id: str) -> Dict[str, Any]:
        """Get plan information (mock implementation)"""
        
        # Mock plan data
        plan_data = {
            "plan_id": plan_id,
            "status": "ACTIVE",
            "max_amount": 10000.0,
            "excluded_conditions": ["Z87.891", "Z87.892"],  # Example ICD codes
            "coverage_types": ["MEDICAL", "EMERGENCY", "DIAGNOSTIC"],
            "prior_auth_required_services": ["SURGERY", "MRI", "CT_SCAN"]
        }
        
        return plan_data
    
    async def _get_customer_information(self, customer_id: str) -> Dict[str, Any]:
        """Get customer information (mock implementation)"""
        
        # Mock customer data
        customer_data = {
            "customer_id": customer_id,
            "status": "ACTIVE",
            "age": 35,
            "pre_existing_conditions": [],
            "prior_authorizations": []
        }
        
        return customer_data
    
    async def _evaluate_rules(
        self, 
        rules: List[Rule], 
        context: Dict[str, Any], 
        evidence_pack: Dict[str, Any]
    ) -> List[RuleEvaluationResult]:
        """Evaluate all rules concurrently"""
        
        # Create evaluation tasks
        tasks = []
        for rule in rules:
            if rule.enabled:
                task = asyncio.create_task(
                    self.rule_engine.evaluate_rule(rule, context, evidence_pack)
                )
                tasks.append(task)
        
        # Execute with concurrency limit
        semaphore = asyncio.Semaphore(self.max_concurrent_rules)
        
        async def evaluate_with_semaphore(task):
            async with semaphore:
                try:
                    return await asyncio.wait_for(task, timeout=self.rule_timeout_seconds)
                except asyncio.TimeoutError:
                    logger.warning(f"Rule evaluation timed out")
                    return RuleEvaluationResult(
                        rule_id="TIMEOUT",
                        outcome=ChecklistOutcome.UNKNOWN,
                        passed=False,
                        message="Rule evaluation timed out",
                        evidence_refs=[],
                        missing_fields=[],
                        evaluation_details={"timeout": True},
                        processing_time_ms=self.rule_timeout_seconds * 1000
                    )
        
        # Wait for all evaluations
        results = await asyncio.gather(
            *[evaluate_with_semaphore(task) for task in tasks],
            return_exceptions=True
        )
        
        # Filter out exceptions and return valid results
        valid_results = []
        for result in results:
            if isinstance(result, RuleEvaluationResult):
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Rule evaluation exception: {result}")
        
        return valid_results
    
    async def _build_checklist_from_results(
        self, 
        rule_results: List[RuleEvaluationResult], 
        rule_set_name: str
    ) -> Checklist:
        """Build checklist from rule evaluation results"""
        
        checklist_items = []
        rule_ids_applied = []
        
        for result in rule_results:
            # Create checklist item
            checklist_item = {
                "rule_id": result.rule_id,
                "outcome": result.outcome,
                "message": result.message,
                "evidence_ref": result.evidence_refs[0] if result.evidence_refs else None,
                "evaluation_details": result.evaluation_details
            }
            
            checklist_items.append(checklist_item)
            rule_ids_applied.append(result.rule_id)
        
        # Create checklist
        checklist = {
            "items": checklist_items,
            "missing_fields": [],  # Will be populated separately
            "rule_ids_applied": rule_ids_applied,
            "completion_percentage": 0.0,  # Will be calculated separately
            "evaluation_timestamp": datetime.utcnow(),
            "rule_set_used": rule_set_name
        }
        
        return checklist
    
    async def _detect_missing_fields(
        self, 
        rule_results: List[RuleEvaluationResult], 
        context: Dict[str, Any]
    ) -> List[str]:
        """Detect missing fields from rule evaluation results"""
        
        missing_fields = set()
        
        for result in rule_results:
            missing_fields.update(result.missing_fields)
        
        return list(missing_fields)
    
    def _calculate_completion_percentage(self, checklist: Checklist) -> float:
        """Calculate checklist completion percentage"""
        
        items = checklist["items"]
        if not items:
            return 0.0
        
        # Count completed items (PASS or FAIL, not MISSING or UNKNOWN)
        completed_items = sum(
            1 for item in items 
            if item["outcome"] in [ChecklistOutcome.PASS, ChecklistOutcome.FAIL]
        )
        
        return (completed_items / len(items)) * 100.0
    
    async def _update_statistics(self, rule_results: List[RuleEvaluationResult]) -> None:
        """Update evaluation statistics"""
        
        self.evaluation_stats["total_evaluations"] += len(rule_results)
        
        for result in rule_results:
            if result.outcome == ChecklistOutcome.PASS:
                self.evaluation_stats["passed_rules"] += 1
            elif result.outcome == ChecklistOutcome.FAIL:
                self.evaluation_stats["failed_rules"] += 1
            elif result.outcome == ChecklistOutcome.MISSING:
                self.evaluation_stats["missing_field_rules"] += 1
            elif result.outcome == ChecklistOutcome.UNKNOWN:
                self.evaluation_stats["error_rules"] += 1
    
    async def _log_evaluation_metrics(
        self,
        case_id: str,
        total_rules: int,
        evaluated_rules: int,
        completion_percentage: float,
        processing_time_ms: int
    ) -> None:
        """Log evaluation metrics for monitoring"""
        
        logger.info(
            f"Checklist evaluation metrics for case {case_id}: "
            f"rules={total_rules}, evaluated={evaluated_rules}, "
            f"completion={completion_percentage:.1f}%, time={processing_time_ms}ms"
        )
        
        # TODO: Send metrics to monitoring system
        # await self.metrics_client.record_evaluation_metrics(...)
    
    def get_evaluation_statistics(self) -> Dict[str, Any]:
        """Get evaluation statistics"""
        return self.evaluation_stats.copy()
    
    def clear_cache(self) -> None:
        """Clear evaluation cache"""
        self.rule_engine.evaluation_cache.clear()
        logger.info("Rule evaluation cache cleared")


# Factory function for creating rules & checklist agent
def create_rules_checklist_agent(use_mock: bool = False) -> RulesChecklistAgent:
    """
    Factory function to create rules & checklist agent.
    
    Args:
        use_mock: Whether to use mock implementations
        
    Returns:
        Configured rules & checklist agent
    """
    return RulesChecklistAgent(use_mock=use_mock)
