"""
Rules and Checklist Builder Agent (UC-OP-07).

This module implements the Rules and Checklist Builder Agent with evidence parsing,
deterministic rule execution engine, checklist construction, exception rule integration,
missing data detection, and rule evaluation logging.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4
from enum import Enum

from pydantic import BaseModel, Field, validator

from ..models.case import Case
from ..models.evidence import EvidencePack, EvidenceItem
from ..models.checklist import (
    Checklist, ChecklistItem, MissingField, RuleEvaluationLog,
    ChecklistTemplate, ChecklistValidation, ChecklistOutcome
)
from ..models.policy import ExceptionRule, PolicyDocument
from ..models.decision import Decision

logger = logging.getLogger(__name__)


class RuleType(str, Enum):
    """Types of rules in the rule engine."""
    ELIGIBILITY = "ELIGIBILITY"
    COVERAGE = "COVERAGE"
    EXCLUSION = "EXCLUSION"
    AUTHORIZATION = "AUTHORIZATION"
    DOCUMENTATION = "DOCUMENTATION"
    FINANCIAL = "FINANCIAL"
    TEMPORAL = "TEMPORAL"
    GEOGRAPHIC = "GEOGRAPHIC"


class RuleOperator(str, Enum):
    """Operators for rule conditions."""
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


class RuleCondition(BaseModel):
    """Individual rule condition."""
    
    field_name: str = Field(..., description="Field name to evaluate")
    operator: RuleOperator = Field(..., description="Comparison operator")
    expected_value: Any = Field(..., description="Expected value for comparison")
    case_sensitive: bool = Field(default=False, description="Whether comparison is case sensitive")
    
    @validator('field_name')
    def validate_field_name(cls, v):
        if not v or not v.strip():
            raise ValueError("field_name cannot be empty")
        return v.strip()


class PolicyRule(BaseModel):
    """Policy rule definition."""
    
    rule_id: str = Field(..., description="Unique rule identifier")
    rule_name: str = Field(..., description="Human-readable rule name")
    rule_type: RuleType = Field(..., description="Type of rule")
    description: str = Field(..., description="Rule description")
    conditions: List[RuleCondition] = Field(..., description="Rule conditions")
    logical_operator: str = Field(default="AND", description="Logical operator for conditions (AND/OR)")
    priority: int = Field(default=100, ge=1, le=1000, description="Rule priority (1=highest)")
    is_active: bool = Field(default=True, description="Whether rule is active")
    source_policy_id: Optional[str] = Field(None, description="Source policy document ID")
    effective_date: Optional[datetime] = Field(None, description="Rule effective date")
    expiry_date: Optional[datetime] = Field(None, description="Rule expiry date")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional rule metadata")
    
    @validator('logical_operator')
    def validate_logical_operator(cls, v):
        if v.upper() not in ["AND", "OR"]:
            raise ValueError("logical_operator must be 'AND' or 'OR'")
        return v.upper()


class RuleEvaluationResult(BaseModel):
    """Result of rule evaluation."""
    
    rule_id: str
    rule_name: str
    outcome: ChecklistOutcome
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_used: List[str] = Field(default_factory=list)
    missing_data: List[str] = Field(default_factory=list)
    evaluation_details: Dict[str, Any] = Field(default_factory=dict)
    processing_time_ms: float
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class EvidenceParser:
    """Parser for extracting structured data from evidence."""
    
    def __init__(self):
        # Common patterns for data extraction
        self.patterns = {
            "amount": [
                r'\$[\d,]+\.?\d*',
                r'USD\s*[\d,]+\.?\d*',
                r'[\d,]+\.?\d*\s*dollars?'
            ],
            "percentage": [
                r'\d+\.?\d*\s*%',
                r'\d+\.?\d*\s*percent'
            ],
            "date": [
                r'\d{1,2}/\d{1,2}/\d{4}',
                r'\d{4}-\d{2}-\d{2}',
                r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b'
            ],
            "age": [
                r'\b\d{1,3}\s*years?\s*old\b',
                r'\bage\s*:?\s*\d{1,3}\b'
            ],
            "code": [
                r'\b[A-Z]{2,5}\d{2,6}\b',
                r'\b\d{5}-\d{2}\b'
            ]
        }
    
    def parse_evidence_pack(self, evidence_pack: EvidencePack) -> Dict[str, Any]:
        """
        Parse evidence pack to extract structured data.
        
        Args:
            evidence_pack: Evidence pack to parse
            
        Returns:
            Dictionary of extracted structured data
        """
        logger.debug(f"Parsing evidence pack {evidence_pack.pack_id}")
        
        parsed_data = {
            "amounts": [],
            "percentages": [],
            "dates": [],
            "ages": [],
            "codes": [],
            "text_fields": {},
            "metadata": {}
        }
        
        for item in evidence_pack.items:
            item_data = self.parse_evidence_item(item)
            
            # Merge extracted data
            for key in ["amounts", "percentages", "dates", "ages", "codes"]:
                parsed_data[key].extend(item_data.get(key, []))
            
            # Store text content by document
            parsed_data["text_fields"][item.document_id] = item.excerpt
            
            # Merge metadata
            parsed_data["metadata"].update(item.metadata)
        
        # Remove duplicates and sort
        for key in ["amounts", "percentages", "dates", "ages", "codes"]:
            parsed_data[key] = sorted(list(set(parsed_data[key])))
        
        logger.debug(f"Parsed evidence pack: {len(parsed_data['amounts'])} amounts, "
                    f"{len(parsed_data['dates'])} dates, {len(parsed_data['codes'])} codes")
        
        return parsed_data
    
    def parse_evidence_item(self, item: EvidenceItem) -> Dict[str, Any]:
        """
        Parse individual evidence item.
        
        Args:
            item: Evidence item to parse
            
        Returns:
            Dictionary of extracted data
        """
        extracted = {
            "amounts": [],
            "percentages": [],
            "dates": [],
            "ages": [],
            "codes": []
        }
        
        text = item.excerpt
        
        for data_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    extracted[data_type].extend(matches)
        
        return extracted
    
    def extract_field_value(self, text: str, field_name: str) -> Optional[Any]:
        """
        Extract specific field value from text.
        
        Args:
            text: Text to search
            field_name: Field name to extract
            
        Returns:
            Extracted value or None
        """
        # Simple field extraction - can be enhanced with NLP
        field_patterns = {
            "service_code": r'\bservice\s*code\s*:?\s*([A-Z0-9-]+)',
            "diagnosis_code": r'\bdiagnosis\s*code\s*:?\s*([A-Z0-9.-]+)',
            "provider_id": r'\bprovider\s*id\s*:?\s*([A-Z0-9-]+)',
            "member_id": r'\bmember\s*id\s*:?\s*([A-Z0-9-]+)',
            "claim_amount": r'\bclaim\s*amount\s*:?\s*\$?([\d,]+\.?\d*)',
            "copay": r'\bcopay\s*:?\s*\$?([\d,]+\.?\d*)',
            "deductible": r'\bdeductible\s*:?\s*\$?([\d,]+\.?\d*)'
        }
        
        pattern = field_patterns.get(field_name.lower())
        if pattern:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None


class RuleEngine:
    """Deterministic rule execution engine."""
    
    def __init__(self, rules: List[PolicyRule]):
        """
        Initialize rule engine with policy rules.
        
        Args:
            rules: List of policy rules
        """
        self.rules = {rule.rule_id: rule for rule in rules}
        self.active_rules = [rule for rule in rules if rule.is_active]
        self.parser = EvidenceParser()
        
        logger.info(f"RuleEngine initialized with {len(rules)} rules ({len(self.active_rules)} active)")
    
    def evaluate_rules(
        self,
        case: Case,
        evidence_pack: EvidencePack,
        exception_rules: Optional[List[ExceptionRule]] = None
    ) -> List[RuleEvaluationResult]:
        """
        Evaluate all rules against case and evidence.
        
        Args:
            case: Case to evaluate
            evidence_pack: Evidence pack
            exception_rules: Optional exception rules
            
        Returns:
            List of rule evaluation results
        """
        logger.info(f"Evaluating {len(self.active_rules)} rules for case {case.case_id}")
        
        # Parse evidence to extract structured data
        parsed_evidence = self.parser.parse_evidence_pack(evidence_pack)
        
        # Create evaluation context
        context = self._create_evaluation_context(case, parsed_evidence)
        
        # Apply exception rules first
        active_exceptions = self._get_active_exceptions(case, exception_rules or [])
        
        results = []
        
        # Sort rules by priority (highest first)
        sorted_rules = sorted(self.active_rules, key=lambda r: r.priority)
        
        for rule in sorted_rules:
            start_time = datetime.utcnow()
            
            # Check if rule is overridden by exception
            if self._is_rule_overridden(rule, active_exceptions):
                result = RuleEvaluationResult(
                    rule_id=rule.rule_id,
                    rule_name=rule.rule_name,
                    outcome=ChecklistOutcome.EXCEPTION_OVERRIDE,
                    confidence=1.0,
                    evaluation_details={"overridden_by_exception": True},
                    processing_time_ms=0.0
                )
                results.append(result)
                continue
            
            # Evaluate rule
            result = self._evaluate_single_rule(rule, context)
            
            # Calculate processing time
            end_time = datetime.utcnow()
            result.processing_time_ms = (end_time - start_time).total_seconds() * 1000
            
            results.append(result)
        
        logger.info(f"Rule evaluation completed: {len(results)} rules evaluated")
        return results
    
    def _create_evaluation_context(self, case: Case, parsed_evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create evaluation context from case and evidence.
        
        Args:
            case: Case data
            parsed_evidence: Parsed evidence data
            
        Returns:
            Evaluation context dictionary
        """
        context = {
            # Case fields
            "case_id": case.case_id,
            "customer_id": case.customer_id,
            "insurer_id": case.insurer_id,
            "plan_id": case.plan_id,
            "service_code": case.service_code,
            "service_date": case.service_date,
            "provider_id": case.provider_id,
            "priority": case.priority.value if case.priority else None,
            "amount_requested": getattr(case, 'amount_requested', None),
            
            # Parsed evidence
            "evidence_amounts": parsed_evidence.get("amounts", []),
            "evidence_dates": parsed_evidence.get("dates", []),
            "evidence_codes": parsed_evidence.get("codes", []),
            "evidence_percentages": parsed_evidence.get("percentages", []),
            "evidence_text": parsed_evidence.get("text_fields", {}),
            
            # Derived fields
            "service_date_year": case.service_date.year if case.service_date else None,
            "service_date_month": case.service_date.month if case.service_date else None,
            "days_since_service": (datetime.utcnow().date() - case.service_date).days if case.service_date else None,
        }
        
        # Add extracted field values
        for doc_id, text in parsed_evidence.get("text_fields", {}).items():
            for field_name in ["service_code", "diagnosis_code", "provider_id", "member_id", 
                             "claim_amount", "copay", "deductible"]:
                value = self.parser.extract_field_value(text, field_name)
                if value:
                    context[f"extracted_{field_name}"] = value
        
        return context
    
    def _evaluate_single_rule(self, rule: PolicyRule, context: Dict[str, Any]) -> RuleEvaluationResult:
        """
        Evaluate a single rule against context.
        
        Args:
            rule: Rule to evaluate
            context: Evaluation context
            
        Returns:
            Rule evaluation result
        """
        logger.debug(f"Evaluating rule {rule.rule_id}: {rule.rule_name}")
        
        condition_results = []
        evidence_used = []
        missing_data = []
        
        # Evaluate each condition
        for condition in rule.conditions:
            result = self._evaluate_condition(condition, context)
            condition_results.append(result)
            
            if result["evidence_source"]:
                evidence_used.append(result["evidence_source"])
            
            if result["missing_data"]:
                missing_data.extend(result["missing_data"])
        
        # Apply logical operator
        if rule.logical_operator == "AND":
            overall_result = all(r["passed"] for r in condition_results)
        else:  # OR
            overall_result = any(r["passed"] for r in condition_results)
        
        # Determine outcome
        if missing_data:
            outcome = ChecklistOutcome.MISSING_DATA
            confidence = 0.0
        elif overall_result:
            outcome = ChecklistOutcome.PASS
            confidence = min([r["confidence"] for r in condition_results])
        else:
            outcome = ChecklistOutcome.FAIL
            confidence = max([r["confidence"] for r in condition_results])
        
        return RuleEvaluationResult(
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            outcome=outcome,
            confidence=confidence,
            evidence_used=list(set(evidence_used)),
            missing_data=list(set(missing_data)),
            evaluation_details={
                "condition_results": condition_results,
                "logical_operator": rule.logical_operator,
                "rule_type": rule.rule_type.value
            },
            processing_time_ms=0.0  # Will be set by caller
        )
    
    def _evaluate_condition(self, condition: RuleCondition, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a single condition.
        
        Args:
            condition: Condition to evaluate
            context: Evaluation context
            
        Returns:
            Condition evaluation result
        """
        field_name = condition.field_name
        operator = condition.operator
        expected_value = condition.expected_value
        
        # Get actual value from context
        actual_value = context.get(field_name)
        
        result = {
            "passed": False,
            "confidence": 1.0,
            "evidence_source": None,
            "missing_data": []
        }
        
        # Check if field exists
        if actual_value is None:
            result["missing_data"].append(field_name)
            return result
        
        # Determine evidence source
        if field_name.startswith("evidence_"):
            result["evidence_source"] = "evidence_pack"
        elif field_name.startswith("extracted_"):
            result["evidence_source"] = "evidence_extraction"
        else:
            result["evidence_source"] = "case_data"
        
        # Perform comparison based on operator
        try:
            if operator == RuleOperator.EQUALS:
                result["passed"] = self._compare_values(actual_value, expected_value, condition.case_sensitive, "==")
            
            elif operator == RuleOperator.NOT_EQUALS:
                result["passed"] = self._compare_values(actual_value, expected_value, condition.case_sensitive, "!=")
            
            elif operator == RuleOperator.GREATER_THAN:
                result["passed"] = float(actual_value) > float(expected_value)
            
            elif operator == RuleOperator.LESS_THAN:
                result["passed"] = float(actual_value) < float(expected_value)
            
            elif operator == RuleOperator.GREATER_EQUAL:
                result["passed"] = float(actual_value) >= float(expected_value)
            
            elif operator == RuleOperator.LESS_EQUAL:
                result["passed"] = float(actual_value) <= float(expected_value)
            
            elif operator == RuleOperator.CONTAINS:
                result["passed"] = self._string_contains(str(actual_value), str(expected_value), condition.case_sensitive)
            
            elif operator == RuleOperator.NOT_CONTAINS:
                result["passed"] = not self._string_contains(str(actual_value), str(expected_value), condition.case_sensitive)
            
            elif operator == RuleOperator.IN:
                if isinstance(expected_value, list):
                    result["passed"] = actual_value in expected_value
                else:
                    result["passed"] = actual_value == expected_value
            
            elif operator == RuleOperator.NOT_IN:
                if isinstance(expected_value, list):
                    result["passed"] = actual_value not in expected_value
                else:
                    result["passed"] = actual_value != expected_value
            
            elif operator == RuleOperator.REGEX_MATCH:
                result["passed"] = bool(re.search(str(expected_value), str(actual_value), 
                                                re.IGNORECASE if not condition.case_sensitive else 0))
            
            elif operator == RuleOperator.EXISTS:
                result["passed"] = actual_value is not None
            
            elif operator == RuleOperator.NOT_EXISTS:
                result["passed"] = actual_value is None
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Error evaluating condition {field_name} {operator.value} {expected_value}: {e}")
            result["passed"] = False
            result["confidence"] = 0.5
        
        return result
    
    def _compare_values(self, actual: Any, expected: Any, case_sensitive: bool, operator: str) -> bool:
        """Compare two values with case sensitivity option."""
        if isinstance(actual, str) and isinstance(expected, str):
            if not case_sensitive:
                actual = actual.lower()
                expected = expected.lower()
        
        if operator == "==":
            return actual == expected
        elif operator == "!=":
            return actual != expected
        
        return False
    
    def _string_contains(self, text: str, substring: str, case_sensitive: bool) -> bool:
        """Check if text contains substring with case sensitivity option."""
        if not case_sensitive:
            text = text.lower()
            substring = substring.lower()
        
        return substring in text
    
    def _get_active_exceptions(self, case: Case, exception_rules: List[ExceptionRule]) -> List[ExceptionRule]:
        """Get active exception rules for the case."""
        active_exceptions = []
        
        for exception in exception_rules:
            if (exception.status.value == "ACTIVE" and
                exception.is_applicable_to_case(case)):
                active_exceptions.append(exception)
        
        return active_exceptions
    
    def _is_rule_overridden(self, rule: PolicyRule, active_exceptions: List[ExceptionRule]) -> bool:
        """Check if rule is overridden by any active exception."""
        for exception in active_exceptions:
            if rule.rule_id in exception.overridden_rule_ids:
                return True
        
        return False


class ChecklistBuilder:
    """Builder for creating checklists from rule evaluation results."""
    
    def __init__(self):
        self.templates = {}
        logger.info("ChecklistBuilder initialized")
    
    def add_template(self, template: ChecklistTemplate):
        """Add a checklist template."""
        self.templates[template.template_id] = template
        logger.debug(f"Added checklist template: {template.template_id}")
    
    def build_checklist(
        self,
        case: Case,
        rule_results: List[RuleEvaluationResult],
        template_id: Optional[str] = None
    ) -> Checklist:
        """
        Build checklist from rule evaluation results.
        
        Args:
            case: Case context
            rule_results: Rule evaluation results
            template_id: Optional template ID
            
        Returns:
            Constructed checklist
        """
        logger.info(f"Building checklist for case {case.case_id} with {len(rule_results)} rule results")
        
        # Create checklist items from rule results
        checklist_items = []
        missing_fields = []
        rule_evaluation_logs = []
        
        for result in rule_results:
            # Create checklist item
            item = ChecklistItem(
                item_id=f"rule_{result.rule_id}",
                description=result.rule_name,
                outcome=result.outcome,
                evidence_references=result.evidence_used,
                confidence_score=result.confidence,
                evaluation_details=result.evaluation_details,
                evaluated_at=result.evaluated_at
            )
            checklist_items.append(item)
            
            # Track missing data
            for missing_field in result.missing_data:
                missing_field_obj = MissingField(
                    field_name=missing_field,
                    field_type="RULE_EVALUATION",
                    required_for=result.rule_id,
                    description=f"Missing data for rule: {result.rule_name}",
                    suggested_source="evidence_pack"
                )
                missing_fields.append(missing_field_obj)
            
            # Create rule evaluation log
            log = RuleEvaluationLog(
                case_id=case.case_id,
                rule_id=result.rule_id,
                rule_name=result.rule_name,
                outcome=result.outcome,
                confidence_score=result.confidence,
                evidence_used=result.evidence_used,
                missing_data=result.missing_data,
                processing_time_ms=result.processing_time_ms,
                evaluation_details=result.evaluation_details
            )
            rule_evaluation_logs.append(log)
        
        # Calculate overall metrics
        total_items = len(checklist_items)
        passed_items = sum(1 for item in checklist_items if item.outcome == ChecklistOutcome.PASS)
        failed_items = sum(1 for item in checklist_items if item.outcome == ChecklistOutcome.FAIL)
        missing_items = sum(1 for item in checklist_items if item.outcome == ChecklistOutcome.MISSING_DATA)
        exception_items = sum(1 for item in checklist_items if item.outcome == ChecklistOutcome.EXCEPTION_OVERRIDE)
        
        # Determine overall outcome
        if missing_items > 0:
            overall_outcome = ChecklistOutcome.MISSING_DATA
        elif failed_items > 0:
            overall_outcome = ChecklistOutcome.FAIL
        elif exception_items > 0:
            overall_outcome = ChecklistOutcome.EXCEPTION_OVERRIDE
        else:
            overall_outcome = ChecklistOutcome.PASS
        
        # Calculate completion percentage
        completion_percentage = (passed_items + exception_items) / total_items if total_items > 0 else 0.0
        
        # Create checklist
        checklist = Checklist(
            case_id=case.case_id,
            template_id=template_id,
            items=checklist_items,
            total_items=total_items,
            passed_items=passed_items,
            failed_items=failed_items,
            missing_items=missing_items,
            overall_outcome=overall_outcome,
            completion_percentage=completion_percentage,
            missing_fields=missing_fields,
            rule_evaluation_logs=rule_evaluation_logs,
            is_complete=missing_items == 0,
            metadata={
                "rule_count": len(rule_results),
                "exception_overrides": exception_items,
                "evaluation_timestamp": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            f"Checklist built for case {case.case_id}: "
            f"{total_items} items, {passed_items} passed, {failed_items} failed, "
            f"{missing_items} missing, overall={overall_outcome.value}"
        )
        
        return checklist


class RulesAndChecklistBuilderAgent:
    """Rules and Checklist Builder Agent (UC-OP-07)."""
    
    def __init__(
        self,
        policy_rules: List[PolicyRule],
        checklist_templates: Optional[List[ChecklistTemplate]] = None,
        enable_audit_logging: bool = True
    ):
        """
        Initialize the Rules and Checklist Builder Agent.
        
        Args:
            policy_rules: List of policy rules
            checklist_templates: Optional checklist templates
            enable_audit_logging: Whether to enable audit logging
        """
        self.rule_engine = RuleEngine(policy_rules)
        self.checklist_builder = ChecklistBuilder()
        self.enable_audit_logging = enable_audit_logging
        
        # Add templates if provided
        if checklist_templates:
            for template in checklist_templates:
                self.checklist_builder.add_template(template)
        
        logger.info("RulesAndChecklistBuilderAgent initialized")
    
    async def build_checklist(
        self,
        case: Case,
        evidence_pack: EvidencePack,
        exception_rules: Optional[List[ExceptionRule]] = None,
        template_id: Optional[str] = None
    ) -> Checklist:
        """
        Build checklist for a case using rules and evidence.
        
        Args:
            case: Case to build checklist for
            evidence_pack: Evidence pack
            exception_rules: Optional exception rules
            template_id: Optional template ID
            
        Returns:
            Constructed checklist
        """
        start_time = datetime.utcnow()
        logger.info(f"Building checklist for case {case.case_id}")
        
        try:
            # 1. Evaluate rules against case and evidence
            rule_results = self.rule_engine.evaluate_rules(case, evidence_pack, exception_rules)
            
            # 2. Build checklist from rule results
            checklist = self.checklist_builder.build_checklist(case, rule_results, template_id)
            
            # 3. Validate checklist
            validation = await self.validate_checklist(checklist)
            checklist.validation_result = validation
            
            # 4. Log operation if enabled
            if self.enable_audit_logging:
                await self._log_checklist_operation(case, checklist, start_time)
            
            logger.info(f"Checklist building completed for case {case.case_id}")
            return checklist
            
        except Exception as e:
            logger.error(f"Error building checklist for case {case.case_id}: {e}")
            
            # Create minimal checklist with error
            error_checklist = Checklist(
                case_id=case.case_id,
                items=[],
                total_items=0,
                passed_items=0,
                failed_items=0,
                missing_items=0,
                overall_outcome=ChecklistOutcome.FAIL,
                completion_percentage=0.0,
                missing_fields=[],
                rule_evaluation_logs=[],
                is_complete=False,
                metadata={"error": str(e), "build_failed": True}
            )
            
            if self.enable_audit_logging:
                await self._log_checklist_operation(case, error_checklist, start_time, error=str(e))
            
            return error_checklist
    
    async def validate_checklist(self, checklist: Checklist) -> ChecklistValidation:
        """
        Validate checklist for completeness and quality.
        
        Args:
            checklist: Checklist to validate
            
        Returns:
            Validation result
        """
        logger.debug(f"Validating checklist {checklist.checklist_id}")
        
        validation_errors = []
        validation_warnings = []
        quality_score = 1.0
        
        # Check for missing items
        if checklist.total_items == 0:
            validation_errors.append("Checklist has no items")
            quality_score = 0.0
        
        # Check completion percentage
        if checklist.completion_percentage < 0.5:
            validation_warnings.append(f"Low completion percentage: {checklist.completion_percentage:.2f}")
            quality_score -= 0.3
        
        # Check for missing data
        if checklist.missing_items > 0:
            validation_warnings.append(f"{checklist.missing_items} items have missing data")
            quality_score -= 0.2
        
        # Check for failed items
        if checklist.failed_items > 0:
            validation_warnings.append(f"{checklist.failed_items} items failed evaluation")
            quality_score -= 0.1
        
        # Check confidence scores
        low_confidence_items = [
            item for item in checklist.items 
            if item.confidence_score < 0.6
        ]
        
        if low_confidence_items:
            validation_warnings.append(f"{len(low_confidence_items)} items have low confidence")
            quality_score -= 0.1
        
        # Ensure quality score is within bounds
        quality_score = max(0.0, min(1.0, quality_score))
        
        is_valid = len(validation_errors) == 0
        
        return ChecklistValidation(
            checklist_id=checklist.checklist_id,
            is_valid=is_valid,
            quality_score=quality_score,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
            completeness_score=checklist.completion_percentage,
            consistency_score=1.0 - (checklist.failed_items / checklist.total_items) if checklist.total_items > 0 else 1.0,
            recommendations=[
                "Add more rules to improve coverage" if checklist.total_items < 5 else None,
                "Resolve missing data issues" if checklist.missing_items > 0 else None,
                "Review failed rule evaluations" if checklist.failed_items > 0 else None
            ]
        )
    
    async def _log_checklist_operation(
        self,
        case: Case,
        checklist: Checklist,
        start_time: datetime,
        error: Optional[str] = None
    ):
        """
        Log checklist building operation.
        
        Args:
            case: Case context
            checklist: Built checklist
            start_time: Operation start time
            error: Optional error message
        """
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds() * 1000
        
        log_entry = {
            "operation": "build_checklist",
            "case_id": case.case_id,
            "checklist_id": checklist.checklist_id,
            "total_items": checklist.total_items,
            "passed_items": checklist.passed_items,
            "failed_items": checklist.failed_items,
            "missing_items": checklist.missing_items,
            "overall_outcome": checklist.overall_outcome.value,
            "completion_percentage": checklist.completion_percentage,
            "processing_time_ms": processing_time,
            "success": error is None,
            "error_message": error,
            "timestamp": end_time.isoformat()
        }
        
        logger.info(f"Checklist operation logged: {log_entry}")
    
    def add_rule(self, rule: PolicyRule):
        """Add a new rule to the engine."""
        self.rule_engine.rules[rule.rule_id] = rule
        if rule.is_active:
            self.rule_engine.active_rules.append(rule)
        logger.info(f"Added rule: {rule.rule_id}")
    
    def remove_rule(self, rule_id: str):
        """Remove a rule from the engine."""
        if rule_id in self.rule_engine.rules:
            rule = self.rule_engine.rules[rule_id]
            del self.rule_engine.rules[rule_id]
            if rule in self.rule_engine.active_rules:
                self.rule_engine.active_rules.remove(rule)
            logger.info(f"Removed rule: {rule_id}")
    
    def get_rule_metrics(self) -> Dict[str, Any]:
        """Get rule engine metrics."""
        total_rules = len(self.rule_engine.rules)
        active_rules = len(self.rule_engine.active_rules)
        
        rule_types = {}
        for rule in self.rule_engine.rules.values():
            rule_type = rule.rule_type.value
            rule_types[rule_type] = rule_types.get(rule_type, 0) + 1
        
        return {
            "total_rules": total_rules,
            "active_rules": active_rules,
            "inactive_rules": total_rules - active_rules,
            "rules_by_type": rule_types,
            "templates_loaded": len(self.checklist_builder.templates)
        }


# Utility functions for creating and configuring the agent

def create_rules_and_checklist_agent(
    policy_rules: List[PolicyRule],
    checklist_templates: Optional[List[ChecklistTemplate]] = None,
    enable_audit_logging: bool = True
) -> RulesAndChecklistBuilderAgent:
    """
    Create a Rules and Checklist Builder Agent instance.
    
    Args:
        policy_rules: List of policy rules
        checklist_templates: Optional checklist templates
        enable_audit_logging: Whether to enable audit logging
        
    Returns:
        Configured RulesAndChecklistBuilderAgent
    """
    return RulesAndChecklistBuilderAgent(
        policy_rules=policy_rules,
        checklist_templates=checklist_templates,
        enable_audit_logging=enable_audit_logging
    )


def create_sample_rules() -> List[PolicyRule]:
    """Create sample policy rules for testing."""
    return [
        PolicyRule(
            rule_id="ELIG_001",
            rule_name="Member Eligibility Check",
            rule_type=RuleType.ELIGIBILITY,
            description="Verify member is eligible for service",
            conditions=[
                RuleCondition(
                    field_name="customer_id",
                    operator=RuleOperator.EXISTS,
                    expected_value=True
                )
            ],
            priority=10
        ),
        PolicyRule(
            rule_id="COV_001",
            rule_name="Service Coverage Check",
            rule_type=RuleType.COVERAGE,
            description="Verify service is covered under plan",
            conditions=[
                RuleCondition(
                    field_name="service_code",
                    operator=RuleOperator.IN,
                    expected_value=["99213", "99214", "99215"]
                )
            ],
            priority=20
        ),
        PolicyRule(
            rule_id="FIN_001",
            rule_name="Amount Limit Check",
            rule_type=RuleType.FINANCIAL,
            description="Verify amount is within limits",
            conditions=[
                RuleCondition(
                    field_name="amount_requested",
                    operator=RuleOperator.LESS_EQUAL,
                    expected_value=5000.0
                )
            ],
            priority=30
        )
    ]
