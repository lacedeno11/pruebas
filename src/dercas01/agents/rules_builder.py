"""
Rules and Checklist Builder Agent for DERCAS 01 Policy Validation Copilot

Implements UC-OP-07: Rules and checklist builder with deterministic policy-as-code
execution and rule evaluation for policy validation decisions.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from ..models.state import PolicyValidationState, ChecklistState, update_audit_log
from ..models.entities import ChecklistItem, Checklist, ExceptionRule, PolicyDocument
from ..models.enums import CaseStatus, ChecklistOutcome, ExceptionStatus
from ..storage.repositories import RepositoryManager
from ..services.rules_engine import RulesEngine, RuleEvaluationResult, RuleContext

logger = logging.getLogger(__name__)


class RulesBuilderConfig(BaseModel):
    """Configuration for rules and checklist builder."""
    
    # Rule evaluation settings
    enable_deterministic_rules: bool = True
    enable_exception_rules: bool = True
    strict_rule_evaluation: bool = True
    
    # Checklist settings
    require_all_rules_pass: bool = False
    min_pass_percentage: float = 0.8
    include_rule_explanations: bool = True
    
    # Exception handling
    apply_active_exceptions: bool = True
    exception_priority_order: List[str] = Field(default_factory=lambda: [
        "customer_specific", "contract_specific", "plan_specific", "general"
    ])
    
    # Rule sources
    policy_rule_weight: float = 1.0
    exception_rule_weight: float = 1.5  # Exceptions override policies
    regulatory_rule_weight: float = 2.0  # Regulatory rules have highest priority
    
    # Performance settings
    max_evaluation_time_seconds: float = 30.0
    enable_rule_caching: bool = True
    cache_ttl_minutes: int = 60
    
    # Quality settings
    require_evidence_citations: bool = True
    min_confidence_threshold: float = 0.7
    validate_rule_logic: bool = True


class RuleEvaluationContext(BaseModel):
    """Context for rule evaluation."""
    
    case_data: Dict[str, Any]
    evidence_pack: Dict[str, Any]
    applicable_policies: List[Dict[str, Any]] = Field(default_factory=list)
    active_exceptions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Evaluation metadata
    evaluation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    rule_set_version: str = "1.0.0"
    evaluator_id: str = "rules_builder_agent"


class ChecklistBuilderResult(BaseModel):
    """Result of checklist building process."""
    
    success: bool
    checklist_id: Optional[str] = None
    
    # Evaluation metrics
    total_rules: int = 0
    passed_rules: int = 0
    failed_rules: int = 0
    missing_rules: int = 0
    
    # Quality indicators
    overall_outcome: ChecklistOutcome = ChecklistOutcome.UNKNOWN
    confidence_score: float = 0.0
    missing_fields: List[str] = Field(default_factory=list)
    
    # Rule application
    policy_rules_applied: int = 0
    exception_rules_applied: int = 0
    regulatory_rules_applied: int = 0
    
    # Processing metadata
    evaluation_time_ms: float = 0.0
    rules_cached: int = 0
    
    # Error information
    error_message: Optional[str] = None
    evaluation_warnings: List[str] = Field(default_factory=list)


class RulesChecklistBuilderAgent:
    """
    Rules and checklist builder agent implementing UC-OP-07.
    
    Responsibilities:
    - Load applicable policy rules
    - Apply active exception rules
    - Execute deterministic rule evaluation
    - Build comprehensive checklist
    - Calculate confidence scores
    - Provide rule explanations
    - Handle rule conflicts and priorities
    """
    
    def __init__(
        self,
        config: RulesBuilderConfig,
        repo_manager: RepositoryManager,
        rules_engine: RulesEngine
    ):
        self.config = config
        self.repo_manager = repo_manager
        self.rules_engine = rules_engine
        
        # Rule processors
        self.rule_processors = self._initialize_rule_processors()
        
        # Rule validators
        self.rule_validators = self._initialize_rule_validators()
        
        # Conflict resolvers
        self.conflict_resolvers = self._initialize_conflict_resolvers()
        
        # Rule cache
        self.rule_cache: Dict[str, Any] = {}
    
    def __call__(self, state: PolicyValidationState) -> PolicyValidationState:
        """
        Execute rules and checklist builder agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with checklist
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Starting rules evaluation for case: {state['case']['case_id']}")
            
            # Step 1: Create evaluation context
            evaluation_context = self._create_evaluation_context(state)
            
            # Step 2: Load applicable policy rules
            policy_rules = self._load_policy_rules(evaluation_context)
            
            # Step 3: Load active exception rules
            exception_rules = self._load_exception_rules(evaluation_context)
            
            # Step 4: Resolve rule conflicts and priorities
            resolved_rules = self._resolve_rule_conflicts(policy_rules, exception_rules)
            
            # Step 5: Execute rule evaluation
            evaluation_results = self._execute_rule_evaluation(resolved_rules, evaluation_context)
            
            # Step 6: Build checklist items
            checklist_items = self._build_checklist_items(evaluation_results, evaluation_context)
            
            # Step 7: Calculate overall outcome and confidence
            overall_outcome, confidence_score = self._calculate_overall_outcome(checklist_items)
            
            # Step 8: Identify missing fields and requirements
            missing_fields = self._identify_missing_fields(checklist_items, evaluation_context)
            
            # Step 9: Create checklist entity
            checklist_entity = self._create_checklist_entity(
                state["case"]["case_id"],
                checklist_items,
                missing_fields,
                resolved_rules,
                evaluation_context,
                overall_outcome,
                confidence_score
            )
            
            # Step 10: Store checklist
            stored_checklist = self.repo_manager.checklists.create(checklist_entity)
            
            # Step 11: Update state
            updated_state = self._update_state_with_checklist(
                state,
                stored_checklist,
                ChecklistBuilderResult(
                    success=True,
                    checklist_id=str(stored_checklist.id),
                    total_rules=len(resolved_rules),
                    passed_rules=len([r for r in evaluation_results if r.outcome == ChecklistOutcome.PASS]),
                    failed_rules=len([r for r in evaluation_results if r.outcome == ChecklistOutcome.FAIL]),
                    missing_rules=len([r for r in evaluation_results if r.outcome == ChecklistOutcome.MISSING]),
                    overall_outcome=overall_outcome,
                    confidence_score=confidence_score,
                    missing_fields=missing_fields,
                    policy_rules_applied=len(policy_rules),
                    exception_rules_applied=len(exception_rules),
                    evaluation_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                ),
                start_time
            )
            
            logger.info(f"Rules evaluation completed successfully: {stored_checklist.id}")
            return updated_state
            
        except Exception as e:
            logger.error(f"Rules evaluation failed: {e}")
            return self._handle_evaluation_error(state, str(e), start_time)
    
    def _initialize_rule_processors(self) -> Dict[str, callable]:
        """Initialize rule processing functions."""
        return {
            "policy": self._process_policy_rule,
            "exception": self._process_exception_rule,
            "regulatory": self._process_regulatory_rule,
            "business": self._process_business_rule,
        }
    
    def _initialize_rule_validators(self) -> List[callable]:
        """Initialize rule validation functions."""
        return [
            self._validate_rule_syntax,
            self._validate_rule_logic,
            self._validate_rule_evidence,
            self._validate_rule_scope,
        ]
    
    def _initialize_conflict_resolvers(self) -> Dict[str, callable]:
        """Initialize conflict resolution functions."""
        return {
            "priority": self._resolve_by_priority,
            "specificity": self._resolve_by_specificity,
            "temporal": self._resolve_by_temporal_order,
            "evidence": self._resolve_by_evidence_strength,
        }
    
    def _create_evaluation_context(self, state: PolicyValidationState) -> RuleEvaluationContext:
        """Create evaluation context from state."""
        try:
            return RuleEvaluationContext(
                case_data=state["case"],
                evidence_pack=state["evidence_pack"],
                evaluation_timestamp=datetime.utcnow(),
                rule_set_version=self.config.__dict__.get("rule_set_version", "1.0.0")
            )
            
        except Exception as e:
            logger.error(f"Failed to create evaluation context: {e}")
            raise
    
    def _load_policy_rules(self, context: RuleEvaluationContext) -> List[Dict[str, Any]]:
        """Load applicable policy rules from evidence pack."""
        policy_rules = []
        
        try:
            if not self.config.enable_deterministic_rules:
                return policy_rules
            
            # Extract rules from evidence pack items
            evidence_items = context.evidence_pack.get("items", [])
            
            for item in evidence_items:
                try:
                    # Extract policy rules from evidence
                    extracted_rules = self._extract_policy_rules_from_evidence(item, context)
                    policy_rules.extend(extracted_rules)
                    
                except Exception as e:
                    logger.warning(f"Failed to extract rules from evidence item: {e}")
            
            # Load additional policy rules from database
            db_policy_rules = self._load_policy_rules_from_database(context)
            policy_rules.extend(db_policy_rules)
            
            logger.info(f"Loaded {len(policy_rules)} policy rules")
            return policy_rules
            
        except Exception as e:
            logger.error(f"Failed to load policy rules: {e}")
            return []
    
    def _extract_policy_rules_from_evidence(self, evidence_item: Dict[str, Any], context: RuleEvaluationContext) -> List[Dict[str, Any]]:
        """Extract policy rules from evidence item."""
        rules = []
        
        try:
            excerpt = evidence_item.get("excerpt", "")
            doc_id = evidence_item.get("doc_id", "")
            
            # Look for rule-like patterns in the excerpt
            rule_patterns = [
                r"must\s+(.+)",
                r"shall\s+(.+)",
                r"required\s+(.+)",
                r"prohibited\s+(.+)",
                r"excluded\s+(.+)",
                r"covered\s+(.+)",
                r"eligible\s+(.+)",
            ]
            
            import re
            for pattern in rule_patterns:
                matches = re.finditer(pattern, excerpt, re.IGNORECASE)
                for match in matches:
                    rule_text = match.group(1).strip()
                    
                    rule = {
                        "rule_id": f"{doc_id}_{hash(rule_text) % 10000}",
                        "rule_type": "policy",
                        "rule_text": rule_text,
                        "source_document": doc_id,
                        "source_excerpt": excerpt,
                        "evidence_reference": evidence_item.get("pointer", ""),
                        "confidence": evidence_item.get("confidence_score", 0.8),
                        "weight": self.config.policy_rule_weight,
                        "extracted_pattern": pattern,
                    }
                    
                    rules.append(rule)
            
        except Exception as e:
            logger.warning(f"Rule extraction failed: {e}")
        
        return rules
    
    def _load_policy_rules_from_database(self, context: RuleEvaluationContext) -> List[Dict[str, Any]]:
        """Load policy rules from database."""
        rules = []
        
        try:
            # This would load pre-defined policy rules from the database
            # For now, return empty list as rules are extracted from evidence
            pass
            
        except Exception as e:
            logger.error(f"Failed to load policy rules from database: {e}")
        
        return rules
    
    def _load_exception_rules(self, context: RuleEvaluationContext) -> List[Dict[str, Any]]:
        """Load active exception rules."""
        exception_rules = []
        
        try:
            if not self.config.enable_exception_rules:
                return exception_rules
            
            case_data = context.case_data
            
            # Load applicable exception rules
            applicable_exceptions = self.repo_manager.exceptions.find_applicable_exceptions(
                insurer_id=case_data.get("insurer_id"),
                customer_id=case_data.get("customer_id"),
                contract_id=case_data.get("contract_id"),
                plan_id=case_data.get("plan_id"),
                service_code=case_data.get("service_code")
            )
            
            # Convert to rule format
            for exception in applicable_exceptions:
                rule = {
                    "rule_id": exception.rule_id,
                    "rule_type": "exception",
                    "rule_text": exception.rule_description,
                    "rule_logic": exception.rule_logic,
                    "source_document": f"exception_{exception.rule_id}",
                    "confidence": 1.0,  # Exception rules have high confidence
                    "weight": self.config.exception_rule_weight,
                    "scope": {
                        "customer_id": exception.customer_id,
                        "contract_id": exception.contract_id,
                        "plan_id": exception.plan_id,
                        "service_codes": exception.service_codes,
                    },
                    "effective_date": exception.effective_date,
                    "expiration_date": exception.expiration_date,
                    "status": exception.status,
                }
                
                exception_rules.append(rule)
            
            logger.info(f"Loaded {len(exception_rules)} exception rules")
            return exception_rules
            
        except Exception as e:
            logger.error(f"Failed to load exception rules: {e}")
            return []
    
    def _resolve_rule_conflicts(self, policy_rules: List[Dict[str, Any]], exception_rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve conflicts between policy and exception rules."""
        try:
            all_rules = policy_rules + exception_rules
            
            if not all_rules:
                return []
            
            # Group rules by topic/subject
            rule_groups = self._group_rules_by_topic(all_rules)
            
            # Resolve conflicts within each group
            resolved_rules = []
            for topic, rules in rule_groups.items():
                if len(rules) > 1:
                    # Multiple rules for same topic - resolve conflicts
                    resolved = self._resolve_rule_group_conflicts(rules)
                    resolved_rules.extend(resolved)
                else:
                    resolved_rules.extend(rules)
            
            # Sort by priority and weight
            resolved_rules.sort(key=lambda r: (r.get("weight", 1.0), r.get("confidence", 0.5)), reverse=True)
            
            logger.info(f"Resolved {len(resolved_rules)} rules from {len(all_rules)} total rules")
            return resolved_rules
            
        except Exception as e:
            logger.error(f"Rule conflict resolution failed: {e}")
            return policy_rules + exception_rules
    
    def _group_rules_by_topic(self, rules: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group rules by topic or subject matter."""
        groups = {}
        
        for rule in rules:
            # Simple topic extraction based on keywords
            rule_text = rule.get("rule_text", "").lower()
            
            # Determine topic
            topic = "general"
            if any(word in rule_text for word in ["coverage", "covered", "benefit"]):
                topic = "coverage"
            elif any(word in rule_text for word in ["eligible", "eligibility"]):
                topic = "eligibility"
            elif any(word in rule_text for word in ["limit", "maximum", "minimum"]):
                topic = "limits"
            elif any(word in rule_text for word in ["excluded", "exclusion", "prohibited"]):
                topic = "exclusions"
            elif any(word in rule_text for word in ["prior", "authorization", "approval"]):
                topic = "authorization"
            
            if topic not in groups:
                groups[topic] = []
            groups[topic].append(rule)
        
        return groups
    
    def _resolve_rule_group_conflicts(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve conflicts within a group of rules."""
        if len(rules) <= 1:
            return rules
        
        # Apply conflict resolution strategies
        for resolver_name, resolver_func in self.conflict_resolvers.items():
            try:
                resolved = resolver_func(rules)
                if resolved:
                    return resolved
            except Exception as e:
                logger.warning(f"Conflict resolver {resolver_name} failed: {e}")
        
        # Fallback: return highest weight rule
        return [max(rules, key=lambda r: r.get("weight", 1.0))]
    
    def _resolve_by_priority(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve conflicts by rule priority (exceptions > policies)."""
        # Exception rules have higher priority
        exception_rules = [r for r in rules if r.get("rule_type") == "exception"]
        if exception_rules:
            return exception_rules
        
        # Return policy rules if no exceptions
        return [r for r in rules if r.get("rule_type") == "policy"]
    
    def _resolve_by_specificity(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve conflicts by rule specificity."""
        # More specific rules (with scope) take precedence
        specific_rules = [r for r in rules if r.get("scope")]
        if specific_rules:
            return specific_rules
        
        return rules
    
    def _resolve_by_temporal_order(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve conflicts by temporal order (newer rules win)."""
        # Sort by effective date (newer first)
        sorted_rules = sorted(
            rules,
            key=lambda r: r.get("effective_date", datetime.min),
            reverse=True
        )
        
        return [sorted_rules[0]] if sorted_rules else []
    
    def _resolve_by_evidence_strength(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve conflicts by evidence strength."""
        # Return rule with highest confidence
        best_rule = max(rules, key=lambda r: r.get("confidence", 0.0))
        return [best_rule]
    
    def _execute_rule_evaluation(self, rules: List[Dict[str, Any]], context: RuleEvaluationContext) -> List[RuleEvaluationResult]:
        """Execute rule evaluation using the rules engine."""
        evaluation_results = []
        
        try:
            for rule in rules:
                try:
                    # Create rule context
                    rule_context = RuleContext(
                        case_data=context.case_data,
                        evidence_pack=context.evidence_pack,
                        rule_metadata=rule
                    )
                    
                    # Execute rule evaluation
                    result = self.rules_engine.evaluate_rule(rule, rule_context)
                    evaluation_results.append(result)
                    
                except Exception as e:
                    logger.error(f"Rule evaluation failed for rule {rule.get('rule_id')}: {e}")
                    
                    # Create failed result
                    failed_result = RuleEvaluationResult(
                        rule_id=rule.get("rule_id", "unknown"),
                        outcome=ChecklistOutcome.UNKNOWN,
                        confidence=0.0,
                        evidence_references=[],
                        explanation=f"Evaluation error: {str(e)}",
                        error_message=str(e)
                    )
                    evaluation_results.append(failed_result)
            
            logger.info(f"Evaluated {len(evaluation_results)} rules")
            return evaluation_results
            
        except Exception as e:
            logger.error(f"Rule evaluation execution failed: {e}")
            return []
    
    def _build_checklist_items(self, evaluation_results: List[RuleEvaluationResult], context: RuleEvaluationContext) -> List[ChecklistItem]:
        """Build checklist items from evaluation results."""
        checklist_items = []
        
        try:
            for result in evaluation_results:
                try:
                    # Create checklist item
                    checklist_item = ChecklistItem(
                        rule_id=result.rule_id,
                        rule_description=result.explanation or f"Rule {result.rule_id}",
                        outcome=result.outcome,
                        evidence_ref=", ".join(result.evidence_references) if result.evidence_references else None,
                        confidence=result.confidence,
                        notes=result.error_message if result.error_message else None
                    )
                    
                    checklist_items.append(checklist_item)
                    
                except Exception as e:
                    logger.error(f"Failed to create checklist item: {e}")
            
            logger.info(f"Created {len(checklist_items)} checklist items")
            return checklist_items
            
        except Exception as e:
            logger.error(f"Checklist item creation failed: {e}")
            return []
    
    def _calculate_overall_outcome(self, checklist_items: List[ChecklistItem]) -> Tuple[ChecklistOutcome, float]:
        """Calculate overall outcome and confidence score."""
        try:
            if not checklist_items:
                return ChecklistOutcome.UNKNOWN, 0.0
            
            # Count outcomes
            pass_count = sum(1 for item in checklist_items if item.outcome == ChecklistOutcome.PASS)
            fail_count = sum(1 for item in checklist_items if item.outcome == ChecklistOutcome.FAIL)
            missing_count = sum(1 for item in checklist_items if item.outcome == ChecklistOutcome.MISSING)
            total_count = len(checklist_items)
            
            # Calculate pass percentage
            pass_percentage = pass_count / total_count if total_count > 0 else 0.0
            
            # Determine overall outcome
            if self.config.require_all_rules_pass:
                if fail_count > 0 or missing_count > 0:
                    overall_outcome = ChecklistOutcome.FAIL
                else:
                    overall_outcome = ChecklistOutcome.PASS
            else:
                if pass_percentage >= self.config.min_pass_percentage:
                    overall_outcome = ChecklistOutcome.PASS
                elif fail_count > 0:
                    overall_outcome = ChecklistOutcome.FAIL
                else:
                    overall_outcome = ChecklistOutcome.MISSING
            
            # Calculate confidence score
            confidence_scores = [item.confidence for item in checklist_items if item.confidence > 0]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            # Adjust confidence based on outcome distribution
            outcome_confidence = pass_percentage if overall_outcome == ChecklistOutcome.PASS else (1.0 - pass_percentage)
            final_confidence = (avg_confidence + outcome_confidence) / 2.0
            
            return overall_outcome, min(final_confidence, 1.0)
            
        except Exception as e:
            logger.error(f"Overall outcome calculation failed: {e}")
            return ChecklistOutcome.UNKNOWN, 0.0
    
    def _identify_missing_fields(self, checklist_items: List[ChecklistItem], context: RuleEvaluationContext) -> List[str]:
        """Identify missing fields required for complete evaluation."""
        missing_fields = []
        
        try:
            # Check for missing case data fields
            case_data = context.case_data
            required_fields = ["service_code", "service_date", "provider_id", "insurer_id", "plan_id"]
            
            for field in required_fields:
                if not case_data.get(field):
                    missing_fields.append(field)
            
            # Check for missing evidence
            evidence_items = context.evidence_pack.get("items", [])
            if not evidence_items:
                missing_fields.append("policy_evidence")
            
            # Check for failed/missing checklist items
            missing_items = [item for item in checklist_items if item.outcome == ChecklistOutcome.MISSING]
            for item in missing_items:
                missing_fields.append(f"rule_evidence_{item.rule_id}")
            
            return list(set(missing_fields))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Missing fields identification failed: {e}")
            return []
    
    def _create_checklist_entity(
        self,
        case_id: str,
        checklist_items: List[ChecklistItem],
        missing_fields: List[str],
        resolved_rules: List[Dict[str, Any]],
        context: RuleEvaluationContext,
        overall_outcome: ChecklistOutcome,
        confidence_score: float
    ) -> Checklist:
        """Create Checklist entity."""
        try:
            # Convert checklist items to dict format
            items_dict = [item.dict() for item in checklist_items]
            
            # Get rule IDs applied
            rule_ids_applied = [rule.get("rule_id") for rule in resolved_rules]
            
            # Calculate summary metrics
            total_items = len(checklist_items)
            passed_items = sum(1 for item in checklist_items if item.outcome == ChecklistOutcome.PASS)
            failed_items = sum(1 for item in checklist_items if item.outcome == ChecklistOutcome.FAIL)
            missing_items = sum(1 for item in checklist_items if item.outcome == ChecklistOutcome.MISSING)
            
            # Create evaluation log
            evaluation_log = {
                "evaluation_context": context.dict(),
                "rules_applied": len(resolved_rules),
                "policy_rules": len([r for r in resolved_rules if r.get("rule_type") == "policy"]),
                "exception_rules": len([r for r in resolved_rules if r.get("rule_type") == "exception"]),
                "overall_outcome": overall_outcome.value,
                "confidence_score": confidence_score,
            }
            
            # Create checklist entity
            checklist_entity = Checklist(
                case_id=case_id,
                items=items_dict,
                missing_fields=missing_fields,
                rule_ids_applied=rule_ids_applied,
                evaluation_timestamp=context.evaluation_timestamp,
                rule_set_version=context.rule_set_version,
                evaluation_log=evaluation_log,
                total_items=total_items,
                passed_items=passed_items,
                failed_items=failed_items,
                missing_items=missing_items
            )
            
            return checklist_entity
            
        except Exception as e:
            logger.error(f"Checklist entity creation failed: {e}")
            raise
    
    def _update_state_with_checklist(
        self,
        state: PolicyValidationState,
        checklist: Checklist,
        result: ChecklistBuilderResult,
        start_time: datetime
    ) -> PolicyValidationState:
        """Update state with checklist."""
        
        # Update checklist state
        state["checklist"] = ChecklistState(
            items=checklist.items,
            missing_fields=checklist.missing_fields,
            rule_ids_applied=checklist.rule_ids_applied,
            total_items=checklist.total_items,
            passed_items=checklist.passed_items,
            failed_items=checklist.failed_items,
            missing_items=checklist.missing_items,
            evaluation_timestamp=checklist.evaluation_timestamp,
            rule_set_version=checklist.rule_set_version
        )
        
        # Update case status
        state["case"]["state"] = CaseStatus.BUILDING_CHECKLIST
        
        # Update audit log
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        state = update_audit_log(
            state,
            node_name="rules_builder",
            node_input={
                "case_id": state["case"]["case_id"],
                "evidence_items": len(state["evidence_pack"]["items"])
            },
            node_output={
                "success": result.success,
                "checklist_id": result.checklist_id,
                "total_rules": result.total_rules,
                "passed_rules": result.passed_rules,
                "failed_rules": result.failed_rules,
                "missing_rules": result.missing_rules,
                "overall_outcome": result.overall_outcome.value,
                "confidence_score": result.confidence_score,
                "policy_rules_applied": result.policy_rules_applied,
                "exception_rules_applied": result.exception_rules_applied
            },
            execution_time_ms=processing_time
        )
        
        # Set next node
        state["next_node"] = "decision_orchestrator"
        
        return state
    
    def _handle_evaluation_error(
        self,
        state: PolicyValidationState,
        error_message: str,
        start_time: datetime
    ) -> PolicyValidationState:
        """Handle rules evaluation error."""
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Update case status
        state["case"]["state"] = CaseStatus.ERROR
        
        # Create empty checklist
        state["checklist"] = ChecklistState(
            items=[],
            missing_fields=["evaluation_error"],
            rule_ids_applied=[],
            total_items=0,
            passed_items=0,
            failed_items=0,
            missing_items=0,
            evaluation_timestamp=datetime.utcnow()
        )
        
        # Log audit event
        state = update_audit_log(
            state,
            node_name="rules_builder",
            node_input={"case_id": state["case"]["case_id"]},
            node_output={"success": False},
            execution_time_ms=processing_time,
            error=error_message
        )
        
        # Set error state
        state["error_occurred"] = True
        state["error_message"] = f"Rules evaluation error: {error_message}"
        
        # Try to continue with empty checklist
        state["next_node"] = "decision_orchestrator"
        
        return state
    
    # Validation methods
    def _validate_rule_syntax(self, rule: Dict[str, Any]) -> bool:
        """Validate rule syntax."""
        required_fields = ["rule_id", "rule_type", "rule_text"]
        return all(field in rule for field in required_fields)
    
    def _validate_rule_logic(self, rule: Dict[str, Any]) -> bool:
        """Validate rule logic."""
        if self.config.validate_rule_logic:
            # Basic validation - in production would be more sophisticated
            rule_text = rule.get("rule_text", "")
            return len(rule_text.strip()) > 0
        return True
    
    def _validate_rule_evidence(self, rule: Dict[str, Any]) -> bool:
        """Validate rule evidence."""
        if self.config.require_evidence_citations:
            return bool(rule.get("evidence_reference") or rule.get("source_document"))
        return True
    
    def _validate_rule_scope(self, rule: Dict[str, Any]) -> bool:
        """Validate rule scope."""
        # All rules are considered valid for scope
        return True
    
    # Processing methods
    def _process_policy_rule(self, rule: Dict[str, Any], context: RuleEvaluationContext) -> Dict[str, Any]:
        """Process policy rule."""
        rule["processed"] = True
        rule["processor"] = "policy"
        return rule
    
    def _process_exception_rule(self, rule: Dict[str, Any], context: RuleEvaluationContext) -> Dict[str, Any]:
        """Process exception rule."""
        rule["processed"] = True
        rule["processor"] = "exception"
        return rule
    
    def _process_regulatory_rule(self, rule: Dict[str, Any], context: RuleEvaluationContext) -> Dict[str, Any]:
        """Process regulatory rule."""
        rule["processed"] = True
        rule["processor"] = "regulatory"
        return rule
    
    def _process_business_rule(self, rule: Dict[str, Any], context: RuleEvaluationContext) -> Dict[str, Any]:
        """Process business rule."""
        rule["processed"] = True
        rule["processor"] = "business"
        return rule


# Factory function
def create_rules_checklist_builder_agent(
    config: Optional[RulesBuilderConfig] = None,
    repo_manager: Optional[RepositoryManager] = None,
    rules_engine: Optional[RulesEngine] = None
) -> RulesChecklistBuilderAgent:
    """Create a rules checklist builder agent with default or custom configuration."""
    if config is None:
        config = RulesBuilderConfig()
    
    if repo_manager is None:
        raise ValueError("Repository manager is required")
    
    if rules_engine is None:
        raise ValueError("Rules engine is required")
    
    return RulesChecklistBuilderAgent(config, repo_manager, rules_engine)
