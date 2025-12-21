"""
Rules & Checklist Builder Node.

UC-OP-07: Deterministic rule evaluation and checklist construction.
"""

import logging
from typing import Any
from uuid import uuid4
from datetime import datetime

from policy_validation_copilot.models.state import PolicyValidationState
from policy_validation_copilot.models.checklist import (
    Checklist,
    ChecklistItem,
    ChecklistOutcome,
    MissingField,
)
from policy_validation_copilot.models.audit import NodeType
from policy_validation_copilot.nodes.base import node_wrapper

logger = logging.getLogger(__name__)


# Rule definitions (in production, loaded from policy-as-code repository)
VALIDATION_RULES = [
    {
        "rule_id": "RULE-COV-001",
        "rule_version": "1.0.0",
        "description": "Service code must be covered under the plan",
        "category": "COVERAGE",
        "is_blocking": True,
        "required_fields": ["service_code", "plan_id"],
    },
    {
        "rule_id": "RULE-AUTH-001",
        "rule_version": "1.0.0",
        "description": "Prior authorization required for specialized services",
        "category": "AUTHORIZATION",
        "is_blocking": True,
        "required_fields": ["service_code"],
    },
    {
        "rule_id": "RULE-LIM-001",
        "rule_version": "1.0.0",
        "description": "Service within annual limit",
        "category": "LIMIT",
        "is_blocking": False,
        "required_fields": ["service_code", "customer_id"],
    },
    {
        "rule_id": "RULE-EXC-001",
        "rule_version": "1.0.0",
        "description": "Service not in exclusion list",
        "category": "EXCLUSION",
        "is_blocking": True,
        "required_fields": ["service_code", "plan_id"],
    },
    {
        "rule_id": "RULE-PRO-001",
        "rule_version": "1.0.0",
        "description": "Provider in approved network",
        "category": "COVERAGE",
        "is_blocking": False,
        "required_fields": ["provider_id"],
    },
]


@node_wrapper(NodeType.RULES_CHECKLIST, "rules_checklist")
async def rules_checklist_node(state: PolicyValidationState) -> dict[str, Any]:
    """
    Rules and checklist builder node.

    Responsibilities:
    1. Parse evidence pack for rule evaluation
    2. Load applicable rules (policy-as-code)
    3. Apply exceptions if any
    4. Execute deterministic rule evaluation
    5. Build checklist with outcomes and references
    """
    if not state.case:
        raise ValueError("No case available for rule evaluation")
    if not state.evidence_pack:
        raise ValueError("No evidence pack available for rule evaluation")

    case = state.case
    evidence_pack = state.evidence_pack

    # Initialize checklist
    checklist = Checklist(
        checklist_id=str(uuid4()),
        case_id=case.case_id,
        rule_set_version="1.0.0",
    )

    # Track missing fields
    missing_fields: list[MissingField] = []

    # Evaluate each rule
    for rule in VALIDATION_RULES:
        # Check required fields
        fields_present = True
        for field in rule["required_fields"]:
            value = getattr(case, field, None)
            if not value:
                fields_present = False
                missing_fields.append(
                    MissingField(
                        field_name=field,
                        field_path=f"case.{field}",
                        is_critical=rule["is_blocking"],
                        suggested_source="CRM/Customer data",
                    )
                )

        # Determine outcome
        if not fields_present:
            outcome = ChecklistOutcome.MISSING
            evidence_ref = None
            reason = "Required fields missing"
        else:
            # Find supporting evidence
            evidence_ref, evidence_excerpt = _find_supporting_evidence(
                rule, case, evidence_pack
            )

            if evidence_ref:
                # Simulate rule evaluation (in production, execute actual rules)
                outcome, reason = _evaluate_rule(rule, case, evidence_excerpt)
            else:
                outcome = ChecklistOutcome.UNKNOWN
                reason = "No supporting evidence found"

        # Create checklist item
        item = ChecklistItem(
            item_id=str(uuid4()),
            rule_id=rule["rule_id"],
            rule_version=rule["rule_version"],
            description=rule["description"],
            category=rule["category"],
            outcome=outcome,
            outcome_reason=reason,
            evidence_ref=evidence_ref,
            evidence_excerpt=evidence_excerpt if evidence_ref else None,
            is_blocking=rule["is_blocking"],
            evaluated_at=datetime.utcnow(),
        )
        checklist.items.append(item)
        checklist.rule_ids_applied.append(rule["rule_id"])

    # Update checklist counts
    checklist.missing_fields = _deduplicate_missing_fields(missing_fields)
    checklist.update_counts()

    # Add evaluation log
    checklist.evaluation_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "rules_evaluated": len(VALIDATION_RULES),
        "evidence_items_used": len(evidence_pack.items),
        "coverage_score": evidence_pack.coverage_score,
    })

    logger.info(
        f"Case {case.case_id} checklist: "
        f"passed={checklist.passed_count}, "
        f"failed={checklist.failed_count}, "
        f"missing={checklist.missing_count}"
    )

    # Determine if HITL required
    hitl_required = state.hitl_required
    if checklist.has_blocking_failures():
        logger.warning(f"Case {case.case_id} has blocking failures")
        # Not automatically HITL, but cannot auto-approve

    if checklist.missing_count > 0:
        logger.warning(f"Case {case.case_id} has missing data")
        hitl_required = True

    return {
        "checklist": checklist,
        "hitl_required": hitl_required,
    }


def _find_supporting_evidence(
    rule: dict,
    case: "Case",
    evidence_pack: "EvidencePack",
) -> tuple[str | None, str | None]:
    """Find evidence supporting a rule evaluation."""
    from policy_validation_copilot.models.case import Case
    from policy_validation_copilot.models.evidence import EvidencePack

    # Search for relevant evidence based on rule category
    keywords = {
        "COVERAGE": ["covered", "coverage", "include", "benefit"],
        "AUTHORIZATION": ["authorization", "prior approval", "pre-auth"],
        "LIMIT": ["limit", "maximum", "cap", "annual"],
        "EXCLUSION": ["exclude", "exclusion", "not covered", "exception"],
    }

    category_keywords = keywords.get(rule["category"], [])

    for item in evidence_pack.items:
        if item.excerpt:
            excerpt_lower = item.excerpt.lower()
            for keyword in category_keywords:
                if keyword in excerpt_lower:
                    return item.evidence_id, item.excerpt[:200]

    return None, None


def _evaluate_rule(
    rule: dict,
    case: "Case",
    evidence_excerpt: str | None,
) -> tuple[ChecklistOutcome, str]:
    """Evaluate a rule against case and evidence."""
    from policy_validation_copilot.models.case import Case

    # In production, this would execute actual policy-as-code rules
    # For now, simulate evaluation based on evidence content

    if not evidence_excerpt:
        return ChecklistOutcome.UNKNOWN, "No evidence to evaluate"

    excerpt_lower = evidence_excerpt.lower()

    # Simple keyword-based evaluation
    if rule["category"] == "EXCLUSION":
        if "not covered" in excerpt_lower or "excluded" in excerpt_lower:
            return ChecklistOutcome.FAILED, "Service appears to be excluded"
        return ChecklistOutcome.PASSED, "No exclusion found"

    if "covered" in excerpt_lower or "included" in excerpt_lower:
        return ChecklistOutcome.PASSED, "Evidence supports coverage"

    if "not covered" in excerpt_lower or "excluded" in excerpt_lower:
        return ChecklistOutcome.FAILED, "Evidence indicates no coverage"

    return ChecklistOutcome.UNKNOWN, "Evidence inconclusive"


def _deduplicate_missing_fields(fields: list[MissingField]) -> list[MissingField]:
    """Remove duplicate missing fields."""
    seen = set()
    unique = []
    for field in fields:
        if field.field_name not in seen:
            seen.add(field.field_name)
            unique.append(field)
    return unique
