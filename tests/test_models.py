"""
Tests for data models.
"""

import pytest
from datetime import datetime

from policy_validation_copilot.models.case import Case, CaseState, CasePriority, Attachment
from policy_validation_copilot.models.evidence import EvidenceItem, EvidencePack, EvidenceType
from policy_validation_copilot.models.checklist import Checklist, ChecklistItem, ChecklistOutcome
from policy_validation_copilot.models.decision import Decision, DecisionStatus, NextAction
from policy_validation_copilot.models.state import PolicyValidationState


class TestCaseModel:
    """Tests for Case model."""

    def test_create_case(self):
        """Test basic case creation."""
        case = Case(
            case_id="CASE-001",
            customer_id="CUST-001",
            insurer_id="INS-001",
            plan_id="PLAN-001",
        )

        assert case.case_id == "CASE-001"
        assert case.customer_id == "CUST-001"
        assert case.state == CaseState.CREATED
        assert case.priority == CasePriority.NORMAL

    def test_case_with_attachments(self):
        """Test case with attachments."""
        attachment = Attachment(
            attachment_id="ATT-001",
            filename="test.pdf",
            content_type="application/pdf",
            storage_path="/tmp/test.pdf",
            checksum="abc123",
            size_bytes=1024,
        )

        case = Case(
            case_id="CASE-002",
            customer_id="CUST-001",
            insurer_id="INS-001",
            plan_id="PLAN-001",
            attachments=[attachment],
        )

        assert len(case.attachments) == 1
        assert case.attachments[0].filename == "test.pdf"


class TestEvidenceModel:
    """Tests for Evidence models."""

    def test_create_evidence_item(self):
        """Test evidence item creation."""
        item = EvidenceItem(
            evidence_id="EV-001",
            doc_id="DOC-001",
            doc_version="1.0",
            checksum="abc123",
            pointer="page:5:line:10",
            relevance_score=0.85,
            confidence_score=0.90,
        )

        assert item.evidence_id == "EV-001"
        assert item.evidence_type == EvidenceType.POLICY_TEXT
        assert item.is_allowlisted is True

    def test_evidence_pack_coverage(self):
        """Test evidence pack coverage calculation."""
        pack = EvidencePack(
            pack_id="PACK-001",
            case_id="CASE-001",
            items=[
                EvidenceItem(
                    evidence_id="EV-001",
                    doc_id="DOC-001",
                    doc_version="1.0",
                    checksum="abc",
                    pointer="page:1",
                    relevance_score=0.9,
                    confidence_score=0.9,
                ),
            ],
            coverage_score=0.85,
        )

        assert pack.has_sufficient_coverage(threshold=0.7)
        assert not pack.has_sufficient_coverage(threshold=0.9)


class TestChecklistModel:
    """Tests for Checklist models."""

    def test_checklist_counts(self):
        """Test checklist count calculations."""
        checklist = Checklist(
            checklist_id="CL-001",
            case_id="CASE-001",
            items=[
                ChecklistItem(
                    item_id="1",
                    rule_id="R-001",
                    rule_version="1.0",
                    description="Test rule 1",
                    category="COVERAGE",
                    outcome=ChecklistOutcome.PASSED,
                ),
                ChecklistItem(
                    item_id="2",
                    rule_id="R-002",
                    rule_version="1.0",
                    description="Test rule 2",
                    category="COVERAGE",
                    outcome=ChecklistOutcome.FAILED,
                    is_blocking=True,
                ),
            ],
        )

        checklist.update_counts()

        assert checklist.total_items == 2
        assert checklist.passed_count == 1
        assert checklist.failed_count == 1
        assert checklist.has_blocking_failures()
        assert not checklist.can_auto_approve()


class TestDecisionModel:
    """Tests for Decision models."""

    def test_create_decision(self):
        """Test decision creation."""
        decision = Decision(
            decision_id="DEC-001",
            case_id="CASE-001",
            status=DecisionStatus.APPROVED,
            status_reason="All checks passed",
            confidence_score=0.90,
            risk_level=0.20,
            thresholds_version="1.0.0",
            explanation_summary="Case approved with high confidence",
        )

        assert decision.is_terminal()
        assert not decision.requires_external_consultation()

    def test_decision_with_next_actions(self):
        """Test decision with next actions."""
        action = NextAction(
            action_id="ACT-001",
            action_type="CLOSE",
            description="Close case",
            target_role="SYSTEM",
        )

        decision = Decision(
            decision_id="DEC-002",
            case_id="CASE-001",
            status=DecisionStatus.OBSERVED,
            status_reason="Approved with observations",
            confidence_score=0.75,
            risk_level=0.35,
            thresholds_version="1.0.0",
            explanation_summary="Case approved with observations",
            next_actions=[action],
        )

        assert len(decision.next_actions) == 1


class TestStateModel:
    """Tests for PolicyValidationState model."""

    def test_create_state(self):
        """Test state creation."""
        case = Case(
            case_id="CASE-001",
            customer_id="CUST-001",
            insurer_id="INS-001",
            plan_id="PLAN-001",
        )

        state = PolicyValidationState(case=case)

        assert state.workflow_status == "INITIALIZED"
        assert not state.hitl_required
        assert len(state.node_executions) == 0

    def test_state_requires_hitl(self):
        """Test HITL requirement detection."""
        case = Case(
            case_id="CASE-001",
            customer_id="CUST-001",
            insurer_id="INS-001",
            plan_id="PLAN-001",
        )

        state = PolicyValidationState(case=case, hitl_required=True)

        assert state.requires_hitl()

    def test_state_summary(self):
        """Test state summary generation."""
        case = Case(
            case_id="CASE-001",
            customer_id="CUST-001",
            insurer_id="INS-001",
            plan_id="PLAN-001",
        )

        state = PolicyValidationState(case=case)
        summary = state.get_summary()

        assert summary["case_id"] == "CASE-001"
        assert summary["workflow_status"] == "INITIALIZED"
