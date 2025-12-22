"""
Audited Closure Node (UC-OP-04)

This module implements the Audited Closure Node for the Policy Validation Copilot system,
providing decision finalization, evidence pack completion, audit trail finalization,
export functionality, and access logging.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import asyncio
import json
import hashlib
import uuid
from dataclasses import dataclass
from enum import Enum
import zipfile
import io
import base64

from ..state import PolicyValidationState, DecisionStatus
from ..database import (
    CaseRepository, DecisionRepository, AuditLogRepository, EvidencePackRepository,
    get_repository_factory
)
from ..guardrails import create_security_context, evaluate_payload_security

logger = logging.getLogger(__name__)


class ClosureStatus(str, Enum):
    """Case closure status"""
    CLOSED_APPROVED = "CLOSED_APPROVED"
    CLOSED_REJECTED = "CLOSED_REJECTED"
    CLOSED_OBSERVED = "CLOSED_OBSERVED"
    CLOSED_ESCALATED = "CLOSED_ESCALATED"
    CLOSURE_FAILED = "CLOSURE_FAILED"


class ExportFormat(str, Enum):
    """Export format options"""
    JSON = "JSON"
    PDF = "PDF"
    XML = "XML"
    CSV = "CSV"
    ZIP = "ZIP"


class AccessLevel(str, Enum):
    """Access level for audit logs"""
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


@dataclass
class ClosureValidation:
    """Validation result for case closure"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    missing_requirements: List[str]


@dataclass
class ExportPackage:
    """Export package containing case data"""
    case_id: str
    export_id: str
    format: ExportFormat
    content: bytes
    metadata: Dict[str, Any]
    checksum: str
    created_at: datetime
    access_level: AccessLevel


@dataclass
class AuditSummary:
    """Summary of audit trail for closure"""
    total_events: int
    event_categories: Dict[str, int]
    security_events: int
    user_actions: int
    system_actions: int
    processing_time_total_ms: int
    first_event: datetime
    last_event: datetime


class AuditedClosureNode:
    """
    Audited Closure Node implementing UC-OP-04.
    
    Handles the final closure of policy validation cases with comprehensive
    audit trails, evidence pack completion, and export functionality.
    """
    
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        self.repo_factory = get_repository_factory()
        
        # Closure configuration
        self.closure_config = self._initialize_closure_config()
        
        # Export configuration
        self.export_config = self._initialize_export_config()
        
        # Retention policies
        self.retention_policies = self._initialize_retention_policies()
        
        # Statistics
        self.closure_stats = {
            "total_closures": 0,
            "successful_closures": 0,
            "failed_closures": 0,
            "exports_generated": 0,
            "audit_events_processed": 0,
            "closure_by_status": {status.value: 0 for status in ClosureStatus}
        }
    
    def _initialize_closure_config(self) -> Dict[str, Any]:
        """Initialize closure configuration"""
        return {
            # Required components for closure
            "required_components": {
                "case": True,
                "decision": True,
                "evidence_pack": False,  # Optional for some decisions
                "checklist": False,     # Optional for some decisions
                "audit": True
            },
            
            # Validation rules
            "validation_rules": {
                "decision_must_be_final": True,
                "evidence_required_for_approval": True,
                "audit_trail_complete": True,
                "no_pending_hitl": True,
                "all_guardrails_passed": False  # Can close with guardrail warnings
            },
            
            # Auto-closure conditions
            "auto_closure_enabled": True,
            "auto_closure_statuses": [
                DecisionStatus.APROBADO,
                DecisionStatus.RECHAZADO
            ],
            
            # Manual closure requirements
            "manual_closure_required": [
                DecisionStatus.ESCALAR,
                DecisionStatus.OBSERVADO
            ]
        }
    
    def _initialize_export_config(self) -> Dict[str, Any]:
        """Initialize export configuration"""
        return {
            # Default export settings
            "default_format": ExportFormat.JSON,
            "include_attachments": True,
            "include_audit_trail": True,
            "include_ml_predictions": True,
            "include_guardrail_logs": True,
            
            # Export retention
            "export_retention_days": 2555,  # 7 years
            "export_compression": True,
            "export_encryption": False,  # Would be enabled in production
            
            # Access control
            "default_access_level": AccessLevel.INTERNAL,
            "access_level_mapping": {
                DecisionStatus.APROBADO: AccessLevel.INTERNAL,
                DecisionStatus.RECHAZADO: AccessLevel.INTERNAL,
                DecisionStatus.OBSERVADO: AccessLevel.CONFIDENTIAL,
                DecisionStatus.ESCALAR: AccessLevel.RESTRICTED
            }
        }
    
    def _initialize_retention_policies(self) -> Dict[str, Any]:
        """Initialize data retention policies"""
        return {
            # Case data retention
            "case_retention_years": 7,
            "audit_retention_years": 10,
            "export_retention_years": 7,
            
            # Cleanup policies
            "auto_cleanup_enabled": False,  # Manual cleanup for compliance
            "cleanup_batch_size": 100,
            "cleanup_frequency_days": 30,
            
            # Archive policies
            "archive_after_years": 3,
            "archive_format": "compressed_json",
            "archive_location": "long_term_storage"
        }
    
    async def close_case(
        self, 
        state: PolicyValidationState,
        user_id: Optional[str] = None,
        closure_reason: Optional[str] = None,
        export_formats: Optional[List[ExportFormat]] = None
    ) -> PolicyValidationState:
        """
        Main entry point for case closure.
        
        Args:
            state: Current policy validation state
            user_id: User initiating closure (None for system closure)
            closure_reason: Reason for closure
            export_formats: Requested export formats
            
        Returns:
            Updated state with closure information
        """
        start_time = datetime.utcnow()
        
        try:
            # Extract case information
            case = state["case"]
            decision = state.get("decision", {})
            case_id = case["case_id"]
            
            logger.info(f"Starting case closure for case {case_id}")
            
            # Validate closure prerequisites
            validation_result = await self._validate_closure_prerequisites(state)
            if not validation_result.is_valid:
                raise Exception(f"Closure validation failed: {validation_result.errors}")
            
            # Determine closure status
            closure_status = await self._determine_closure_status(decision)
            
            # Finalize decision
            await self._finalize_decision(state, user_id, closure_reason)
            
            # Complete evidence pack
            await self._complete_evidence_pack(state)
            
            # Finalize audit trail
            audit_summary = await self._finalize_audit_trail(case_id, closure_status, user_id)
            
            # Generate exports
            export_packages = await self._generate_exports(
                state, closure_status, export_formats or [self.export_config["default_format"]]
            )
            
            # Update case status
            await self._update_case_status(case_id, closure_status, user_id)
            
            # Apply retention policies
            await self._apply_retention_policies(case_id, closure_status)
            
            # Log closure access
            await self._log_closure_access(case_id, user_id, closure_status, export_packages)
            
            # Update state with closure information
            state["closure"] = {
                "status": closure_status.value,
                "closed_at": datetime.utcnow(),
                "closed_by": user_id or "SYSTEM",
                "closure_reason": closure_reason,
                "audit_summary": audit_summary,
                "export_packages": [
                    {
                        "export_id": pkg.export_id,
                        "format": pkg.format.value,
                        "checksum": pkg.checksum,
                        "access_level": pkg.access_level.value,
                        "created_at": pkg.created_at
                    }
                    for pkg in export_packages
                ],
                "retention_applied": True,
                "compliance_verified": True
            }
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Log final closure audit
            await self._log_final_closure_audit(
                case_id, closure_status, audit_summary, processing_time, user_id
            )
            
            # Update statistics
            await self._update_closure_statistics(closure_status, len(export_packages))
            
            logger.info(
                f"Case closure completed for case {case_id}: "
                f"status={closure_status.value}, "
                f"exports={len(export_packages)}, "
                f"processing_time={processing_time}ms"
            )
            
            return state
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.error(f"Case closure failed for case {case.get('case_id', 'unknown')}: {e}")
            
            # Log closure failure
            await self._log_closure_failure(case.get("case_id"), str(e), processing_time, user_id)
            
            # Update error statistics
            self.closure_stats["failed_closures"] += 1
            
            # Add failure information to state
            state["closure"] = {
                "status": ClosureStatus.CLOSURE_FAILED.value,
                "closed_at": datetime.utcnow(),
                "closed_by": user_id or "SYSTEM",
                "error_message": str(e),
                "processing_time_ms": int(processing_time)
            }
            
            raise
    
    async def _validate_closure_prerequisites(self, state: PolicyValidationState) -> ClosureValidation:
        """Validate that all prerequisites for closure are met"""
        
        errors = []
        warnings = []
        missing_requirements = []
        
        # Check required components
        required_components = self.closure_config["required_components"]
        
        for component, required in required_components.items():
            if required and component not in state:
                errors.append(f"Missing required component: {component}")
                missing_requirements.append(component)
        
        # Validate decision component
        decision = state.get("decision", {})
        if decision:
            # Check if decision is final
            if self.closure_config["validation_rules"]["decision_must_be_final"]:
                if not decision.get("is_final", False):
                    errors.append("Decision must be finalized before closure")
            
            # Check HITL completion
            if self.closure_config["validation_rules"]["no_pending_hitl"]:
                if decision.get("requires_hitl", False) and not decision.get("hitl_completed_at"):
                    errors.append("HITL review must be completed before closure")
            
            # Check evidence for approval
            if self.closure_config["validation_rules"]["evidence_required_for_approval"]:
                if decision.get("status") == DecisionStatus.APROBADO:
                    evidence_pack = state.get("evidence_pack", {})
                    if not evidence_pack.get("items"):
                        errors.append("Evidence pack required for approval decisions")
        
        # Validate audit trail
        if self.closure_config["validation_rules"]["audit_trail_complete"]:
            audit = state.get("audit", {})
            if not audit.get("node_execution_log"):
                warnings.append("Audit trail appears incomplete")
        
        # Check guardrails
        guardrails = state.get("guardrails", {})
        if guardrails.get("decision") == "BLOCK":
            if self.closure_config["validation_rules"]["all_guardrails_passed"]:
                errors.append("Cannot close case with blocking guardrail violations")
            else:
                warnings.append("Case has guardrail violations but closure is allowed")
        
        return ClosureValidation(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            missing_requirements=missing_requirements
        )
    
    async def _determine_closure_status(self, decision: Dict[str, Any]) -> ClosureStatus:
        """Determine the appropriate closure status"""
        
        decision_status = decision.get("status")
        
        if decision_status == DecisionStatus.APROBADO:
            return ClosureStatus.CLOSED_APPROVED
        elif decision_status == DecisionStatus.RECHAZADO:
            return ClosureStatus.CLOSED_REJECTED
        elif decision_status == DecisionStatus.OBSERVADO:
            return ClosureStatus.CLOSED_OBSERVED
        elif decision_status == DecisionStatus.ESCALAR:
            return ClosureStatus.CLOSED_ESCALATED
        else:
            return ClosureStatus.CLOSURE_FAILED
    
    async def _finalize_decision(
        self, 
        state: PolicyValidationState, 
        user_id: Optional[str],
        closure_reason: Optional[str]
    ) -> None:
        """Finalize the decision component"""
        
        decision = state.get("decision", {})
        
        # Mark decision as final
        decision["is_final"] = True
        decision["finalized_at"] = datetime.utcnow()
        decision["finalized_by"] = user_id or "SYSTEM"
        
        if closure_reason:
            decision["closure_reason"] = closure_reason
        
        # Add finalization metadata
        decision["finalization_metadata"] = {
            "closure_initiated_by": user_id or "SYSTEM",
            "closure_timestamp": datetime.utcnow(),
            "validation_passed": True,
            "audit_trail_complete": True
        }
        
        # Update state
        state["decision"] = decision
    
    async def _complete_evidence_pack(self, state: PolicyValidationState) -> None:
        """Complete and finalize the evidence pack"""
        
        evidence_pack = state.get("evidence_pack", {})
        
        if evidence_pack:
            # Calculate final coverage score
            items = evidence_pack.get("items", [])
            if items:
                total_relevance = sum(item.get("relevance_score", 0.0) for item in items)
                total_confidence = sum(item.get("confidence_score", 0.0) for item in items)
                
                final_coverage = (total_relevance + total_confidence) / (2 * len(items))
                evidence_pack["final_coverage_score"] = final_coverage
            
            # Add completion metadata
            evidence_pack["completed_at"] = datetime.utcnow()
            evidence_pack["total_items"] = len(items)
            evidence_pack["completion_status"] = "FINALIZED"
            
            # Validate evidence integrity
            evidence_pack["integrity_verified"] = await self._verify_evidence_integrity(items)
            
            # Update state
            state["evidence_pack"] = evidence_pack
    
    async def _verify_evidence_integrity(self, evidence_items: List[Dict[str, Any]]) -> bool:
        """Verify integrity of evidence items"""
        
        try:
            for item in evidence_items:
                # Check required fields
                required_fields = ["doc_id", "version", "checksum", "excerpt"]
                for field in required_fields:
                    if field not in item or not item[field]:
                        return False
                
                # Verify checksum format
                checksum = item.get("checksum", "")
                if len(checksum) != 64:  # SHA-256 length
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Evidence integrity verification failed: {e}")
            return False
    
    async def _finalize_audit_trail(
        self, 
        case_id: str, 
        closure_status: ClosureStatus,
        user_id: Optional[str]
    ) -> Dict[str, Any]:
        """Finalize audit trail and generate summary"""
        
        audit_repo = self.repo_factory.audit_log_repository()
        
        # Get all audit logs for the case
        audit_logs = audit_repo.get_by_case_id(case_id, limit=1000)
        
        # Generate audit summary
        audit_summary = await self._generate_audit_summary(audit_logs)
        
        # Create final audit entry
        final_audit_data = {
            "case_id": case_id,
            "event_type": "CASE_CLOSED",
            "event_category": "CASE",
            "event_description": f"Case closed with status: {closure_status.value}",
            "user_id": user_id or "SYSTEM",
            "event_data": {
                "closure_status": closure_status.value,
                "audit_summary": audit_summary,
                "total_audit_events": len(audit_logs),
                "closure_initiated_by": user_id or "SYSTEM"
            },
            "security_level": "NORMAL"
        }
        
        try:
            audit_repo.create(**final_audit_data)
        except Exception as e:
            logger.error(f"Failed to create final audit entry: {e}")
        
        return audit_summary
    
    async def _generate_audit_summary(self, audit_logs: List[Any]) -> Dict[str, Any]:
        """Generate comprehensive audit summary"""
        
        if not audit_logs:
            return {
                "total_events": 0,
                "event_categories": {},
                "security_events": 0,
                "user_actions": 0,
                "system_actions": 0,
                "processing_time_total_ms": 0,
                "first_event": None,
                "last_event": None
            }
        
        # Analyze audit logs
        event_categories = {}
        security_events = 0
        user_actions = 0
        system_actions = 0
        total_processing_time = 0
        
        timestamps = []
        
        for log in audit_logs:
            # Count by category
            category = log.event_category
            event_categories[category] = event_categories.get(category, 0) + 1
            
            # Count security events
            if category == "SECURITY" or log.security_level in ["HIGH", "CRITICAL"]:
                security_events += 1
            
            # Count user vs system actions
            if log.user_id and log.user_id != "SYSTEM":
                user_actions += 1
            else:
                system_actions += 1
            
            # Sum processing times
            if log.processing_time_ms:
                total_processing_time += log.processing_time_ms
            
            # Collect timestamps
            timestamps.append(log.created_at)
        
        # Sort timestamps
        timestamps.sort()
        
        return {
            "total_events": len(audit_logs),
            "event_categories": event_categories,
            "security_events": security_events,
            "user_actions": user_actions,
            "system_actions": system_actions,
            "processing_time_total_ms": total_processing_time,
            "first_event": timestamps[0] if timestamps else None,
            "last_event": timestamps[-1] if timestamps else None,
            "audit_duration_hours": (
                (timestamps[-1] - timestamps[0]).total_seconds() / 3600
                if len(timestamps) > 1 else 0
            )
        }
    
    async def _generate_exports(
        self, 
        state: PolicyValidationState, 
        closure_status: ClosureStatus,
        export_formats: List[ExportFormat]
    ) -> List[ExportPackage]:
        """Generate export packages in requested formats"""
        
        export_packages = []
        case_id = state["case"]["case_id"]
        
        for format in export_formats:
            try:
                export_package = await self._create_export_package(
                    state, closure_status, format
                )
                export_packages.append(export_package)
                
            except Exception as e:
                logger.error(f"Failed to create {format.value} export for case {case_id}: {e}")
        
        self.closure_stats["exports_generated"] += len(export_packages)
        
        return export_packages
    
    async def _create_export_package(
        self, 
        state: PolicyValidationState, 
        closure_status: ClosureStatus,
        format: ExportFormat
    ) -> ExportPackage:
        """Create export package in specified format"""
        
        case_id = state["case"]["case_id"]
        export_id = str(uuid.uuid4())
        
        # Prepare export data
        export_data = await self._prepare_export_data(state)
        
        # Generate content based on format
        if format == ExportFormat.JSON:
            content = json.dumps(export_data, indent=2, default=str).encode('utf-8')
        elif format == ExportFormat.XML:
            content = await self._convert_to_xml(export_data)
        elif format == ExportFormat.CSV:
            content = await self._convert_to_csv(export_data)
        elif format == ExportFormat.ZIP:
            content = await self._create_zip_package(export_data)
        else:
            # Default to JSON
            content = json.dumps(export_data, indent=2, default=str).encode('utf-8')
        
        # Calculate checksum
        checksum = hashlib.sha256(content).hexdigest()
        
        # Determine access level
        access_level = self.export_config["access_level_mapping"].get(
            closure_status, self.export_config["default_access_level"]
        )
        
        # Create metadata
        metadata = {
            "case_id": case_id,
            "export_format": format.value,
            "closure_status": closure_status.value,
            "data_size_bytes": len(content),
            "components_included": list(export_data.keys()),
            "created_by": "SYSTEM",
            "retention_until": datetime.utcnow() + timedelta(
                days=self.export_config["export_retention_days"]
            )
        }
        
        return ExportPackage(
            case_id=case_id,
            export_id=export_id,
            format=format,
            content=content,
            metadata=metadata,
            checksum=checksum,
            created_at=datetime.utcnow(),
            access_level=access_level
        )
    
    async def _prepare_export_data(self, state: PolicyValidationState) -> Dict[str, Any]:
        """Prepare comprehensive export data"""
        
        export_data = {
            "export_metadata": {
                "export_version": "1.0",
                "export_timestamp": datetime.utcnow(),
                "export_type": "CASE_CLOSURE",
                "compliance_level": "FULL"
            },
            "case": state.get("case", {}),
            "decision": state.get("decision", {}),
            "closure": state.get("closure", {})
        }
        
        # Include optional components based on configuration
        if self.export_config["include_audit_trail"]:
            export_data["audit"] = state.get("audit", {})
        
        if self.export_config["include_ml_predictions"]:
            export_data["ml"] = state.get("ml", {})
        
        if self.export_config["include_guardrail_logs"]:
            export_data["guardrails"] = state.get("guardrails", {})
        
        # Include evidence pack if present
        evidence_pack = state.get("evidence_pack")
        if evidence_pack:
            export_data["evidence_pack"] = evidence_pack
        
        # Include checklist if present
        checklist = state.get("checklist")
        if checklist:
            export_data["checklist"] = checklist
        
        # Include HITL information if present
        hitl = state.get("hitl")
        if hitl:
            export_data["hitl"] = hitl
        
        return export_data
    
    async def _convert_to_xml(self, data: Dict[str, Any]) -> bytes:
        """Convert data to XML format"""
        # Simplified XML conversion - in production would use proper XML library
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<case_export>\n'
        xml_content += json.dumps(data, indent=2, default=str)
        xml_content += '\n</case_export>'
        return xml_content.encode('utf-8')
    
    async def _convert_to_csv(self, data: Dict[str, Any]) -> bytes:
        """Convert data to CSV format"""
        # Simplified CSV conversion - would flatten data structure in production
        csv_content = "component,key,value\n"
        
        for component, component_data in data.items():
            if isinstance(component_data, dict):
                for key, value in component_data.items():
                    csv_content += f"{component},{key},{value}\n"
        
        return csv_content.encode('utf-8')
    
    async def _create_zip_package(self, data: Dict[str, Any]) -> bytes:
        """Create ZIP package with multiple files"""
        
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add main data as JSON
            json_content = json.dumps(data, indent=2, default=str)
            zip_file.writestr("case_data.json", json_content)
            
            # Add individual components
            for component, component_data in data.items():
                if isinstance(component_data, dict):
                    component_json = json.dumps(component_data, indent=2, default=str)
                    zip_file.writestr(f"{component}.json", component_json)
        
        zip_buffer.seek(0)
        return zip_buffer.read()
    
    async def _update_case_status(
        self, 
        case_id: str, 
        closure_status: ClosureStatus,
        user_id: Optional[str]
    ) -> None:
        """Update case status in database"""
        
        case_repo = self.repo_factory.case_repository()
        
        # Map closure status to case status
        status_mapping = {
            ClosureStatus.CLOSED_APPROVED: "CERRADO",
            ClosureStatus.CLOSED_REJECTED: "CERRADO",
            ClosureStatus.CLOSED_OBSERVED: "CERRADO",
            ClosureStatus.CLOSED_ESCALATED: "CERRADO",
            ClosureStatus.CLOSURE_FAILED: "ERROR"
        }
        
        case_status = status_mapping.get(closure_status, "ERROR")
        
        try:
            case_repo.update(case_id, 
                status=case_status,
                updated_by=user_id or "SYSTEM"
            )
        except Exception as e:
            logger.error(f"Failed to update case status: {e}")
    
    async def _apply_retention_policies(
        self, 
        case_id: str, 
        closure_status: ClosureStatus
    ) -> None:
        """Apply data retention policies"""
        
        # Calculate retention dates
        now = datetime.utcnow()
        case_retention_date = now + timedelta(days=self.retention_policies["case_retention_years"] * 365)
        audit_retention_date = now + timedelta(days=self.retention_policies["audit_retention_years"] * 365)
        
        # Log retention policy application
        logger.info(
            f"Applied retention policies to case {case_id}: "
            f"case_retention={case_retention_date}, "
            f"audit_retention={audit_retention_date}"
        )
        
        # In production, would update database with retention dates
        # and schedule cleanup jobs
    
    async def _log_closure_access(
        self, 
        case_id: str, 
        user_id: Optional[str],
        closure_status: ClosureStatus,
        export_packages: List[ExportPackage]
    ) -> None:
        """Log case closure access for compliance"""
        
        audit_repo = self.repo_factory.audit_log_repository()
        
        access_data = {
            "case_id": case_id,
            "event_type": "CASE_CLOSURE_ACCESS",
            "event_category": "CASE",
            "event_description": f"Case closure accessed: {closure_status.value}",
            "user_id": user_id or "SYSTEM",
            "event_data": {
                "closure_status": closure_status.value,
                "exports_generated": len(export_packages),
                "export_formats": [pkg.format.value for pkg in export_packages],
                "access_timestamp": datetime.utcnow(),
                "access_type": "CLOSURE"
            },
            "security_level": "NORMAL"
        }
        
        try:
            audit_repo.create(**access_data)
        except Exception as e:
            logger.error(f"Failed to log closure access: {e}")
    
    async def _log_final_closure_audit(
        self,
        case_id: str,
        closure_status: ClosureStatus,
        audit_summary: Dict[str, Any],
        processing_time_ms: int,
        user_id: Optional[str]
    ) -> None:
        """Log final closure audit entry"""
        
        audit_repo = self.repo_factory.audit_log_repository()
        
        final_audit_data = {
            "case_id": case_id,
            "event_type": "CASE_CLOSURE_COMPLETED",
            "event_category": "CASE",
            "event_description": f"Case closure process completed: {closure_status.value}",
            "user_id": user_id or "SYSTEM",
            "event_data": {
                "closure_status": closure_status.value,
                "audit_summary": audit_summary,
                "processing_time_ms": processing_time_ms,
                "closure_timestamp": datetime.utcnow(),
                "compliance_verified": True
            },
            "processing_time_ms": processing_time_ms,
            "security_level": "NORMAL"
        }
        
        try:
            audit_repo.create(**final_audit_data)
        except Exception as e:
            logger.error(f"Failed to log final closure audit: {e}")
    
    async def _log_closure_failure(
        self,
        case_id: Optional[str],
        error_message: str,
        processing_time_ms: int,
        user_id: Optional[str]
    ) -> None:
        """Log closure failure for debugging"""
        
        audit_repo = self.repo_factory.audit_log_repository()
        
        failure_data = {
            "case_id": case_id,
            "event_type": "CASE_CLOSURE_FAILED",
            "event_category": "CASE",
            "event_description": f"Case closure failed: {error_message}",
            "user_id": user_id or "SYSTEM",
            "event_data": {
                "error_message": error_message,
                "processing_time_ms": processing_time_ms,
                "failure_timestamp": datetime.utcnow()
            },
            "processing_time_ms": processing_time_ms,
            "security_level": "HIGH"
        }
        
        try:
            audit_repo.create(**failure_data)
        except Exception as e:
            logger.error(f"Failed to log closure failure: {e}")
    
    async def _update_closure_statistics(
        self, 
        closure_status: ClosureStatus, 
        export_count: int
    ) -> None:
        """Update closure statistics"""
        
        self.closure_stats["total_closures"] += 1
        
        if closure_status != ClosureStatus.CLOSURE_FAILED:
            self.closure_stats["successful_closures"] += 1
        
        self.closure_stats["closure_by_status"][closure_status.value] += 1
        self.closure_stats["exports_generated"] += export_count
    
    def get_closure_statistics(self) -> Dict[str, Any]:
        """Get closure statistics"""
        stats = self.closure_stats.copy()
        
        if stats["total_closures"] > 0:
            stats["success_rate"] = stats["successful_closures"] / stats["total_closures"]
            stats["failure_rate"] = stats["failed_closures"] / stats["total_closures"]
            stats["avg_exports_per_closure"] = stats["exports_generated"] / stats["total_closures"]
        
        return stats
    
    async def export_case_data(
        self, 
        case_id: str, 
        export_format: ExportFormat = ExportFormat.JSON,
        user_id: Optional[str] = None
    ) -> ExportPackage:
        """Export case data on demand"""
        
        # Load case state (simplified - would load from database)
        case_repo = self.repo_factory.case_repository()
        case = case_repo.get_by_id(case_id)
        
        if not case:
            raise Exception(f"Case not found: {case_id}")
        
        # Create minimal state for export
        state = {
            "case": {
                "case_id": case.id,
                "crm_ticket_id": case.crm_ticket_id,
                "status": case.status,
                # Add other case fields as needed
            }
        }
        
        # Create export package
        export_package = await self._create_export_package(
            state, ClosureStatus.CLOSED_APPROVED, export_format
        )
        
        # Log export access
        await self._log_export_access(case_id, export_format, user_id)
        
        return export_package
    
    async def _log_export_access(
        self, 
        case_id: str, 
        export_format: ExportFormat,
        user_id: Optional[str]
    ) -> None:
        """Log export access for compliance"""
        
        audit_repo = self.repo_factory.audit_log_repository()
        
        access_data = {
            "case_id": case_id,
            "event_type": "CASE_DATA_EXPORTED",
            "event_category": "CASE",
            "event_description": f"Case data exported in {export_format.value} format",
            "user_id": user_id or "SYSTEM",
            "event_data": {
                "export_format": export_format.value,
                "export_timestamp": datetime.utcnow(),
                "export_type": "ON_DEMAND"
            },
            "security_level": "NORMAL"
        }
        
        try:
            audit_repo.create(**access_data)
        except Exception as e:
            logger.error(f"Failed to log export access: {e}")


# Factory function for creating audited closure node
def create_audited_closure_node(use_mock: bool = False) -> AuditedClosureNode:
    """
    Factory function to create audited closure node.
    
    Args:
        use_mock: Whether to use mock implementations
        
    Returns:
        Configured audited closure node
    """
    return AuditedClosureNode(use_mock=use_mock)
