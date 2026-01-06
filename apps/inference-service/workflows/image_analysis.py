"""
DERCAS-ONCO-XAI V1 - ImageAnalysisGraph LangGraph Workflow

LangGraph workflow for medical image analysis with 9 processing nodes:
ValidateInput → LoadImage → RunPatternModel → RunMutationModel → 
GenerateXAI → AssembleResultBundle → PolicyCheck → PersistAndAudit → Finalize
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict
from uuid import uuid4

from langgraph import StateGraph, END
from langgraph.graph import Graph

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')

from packages.langgraph_workflows.state import BaseGraphState
from packages.langgraph_workflows.base import BaseWorkflow, WorkflowNode
from packages.common.errors import ValidationError, BusinessLogicError, ExternalServiceError

from ..config import get_settings, get_clinical_guardrails, get_xai_config
from ..models_ml import model_registry, predict_patterns, predict_mutations, calculate_overall_confidence

logger = logging.getLogger(__name__)


class ImageAnalysisState(BaseGraphState):
    """State for ImageAnalysisGraph workflow."""
    
    # Input data
    job_id: str
    image_id: str
    case_id: str
    image_data: Optional[bytes] = None
    processing_options: Dict[str, Any] = {}
    
    # Processing state
    current_step: str = "validate_input"
    progress_percentage: int = 0
    
    # Image validation results
    image_valid: bool = False
    validation_errors: List[str] = []
    image_metadata: Dict[str, Any] = {}
    
    # ML prediction results
    pattern_predictions: List[Dict[str, Any]] = []
    mutation_predictions: List[Dict[str, Any]] = []
    
    # XAI artifacts
    xai_artifacts: List[Dict[str, Any]] = []
    
    # Result assembly
    result_bundle: Optional[Dict[str, Any]] = None
    overall_confidence: float = 0.0
    
    # Policy and clinical decisions
    policy_decisions: List[Dict[str, Any]] = []
    requires_hitl: bool = False
    hitl_reason: Optional[str] = None
    
    # Final results
    result_bundle_id: Optional[str] = None
    processing_complete: bool = False
    processing_error: Optional[str] = None
    
    # Audit information
    audit_events: List[Dict[str, Any]] = []
    
    def update_progress(self, step: str, percentage: int):
        """Update processing progress."""
        self.current_step = step
        self.progress_percentage = min(100, max(0, percentage))
        logger.info(f"Job {self.job_id}: {step} ({percentage}%)")


class ValidateInputNode(WorkflowNode):
    """Node 1: Validate input parameters and image availability."""
    
    async def execute(self, state: ImageAnalysisState) -> ImageAnalysisState:
        """Validate input data and parameters."""
        state.update_progress("validate_input", 5)
        
        try:
            # Validate required fields
            if not state.job_id:
                raise ValidationError("Job ID is required")
            if not state.image_id:
                raise ValidationError("Image ID is required")
            if not state.case_id:
                raise ValidationError("Case ID is required")
            
            # Validate processing options
            options = state.processing_options
            
            # Check pattern analysis options
            if options.get("enable_pattern_analysis", True):
                pattern_models = options.get("pattern_models")
                if pattern_models:
                    supported_patterns = model_registry.get_supported_patterns()
                    invalid_patterns = [p for p in pattern_models if p not in supported_patterns]
                    if invalid_patterns:
                        raise ValidationError(f"Unsupported pattern models: {invalid_patterns}")
            
            # Check mutation analysis options
            if options.get("enable_mutation_analysis", True):
                mutation_models = options.get("mutation_models")
                if mutation_models:
                    supported_mutations = model_registry.get_supported_mutations()
                    invalid_mutations = [m for m in mutation_models if m not in supported_mutations]
                    if invalid_mutations:
                        raise ValidationError(f"Unsupported mutation models: {invalid_mutations}")
            
            # Validate confidence thresholds
            pattern_threshold = options.get("pattern_confidence_threshold")
            if pattern_threshold is not None and not (0.0 <= pattern_threshold <= 1.0):
                raise ValidationError("Pattern confidence threshold must be between 0.0 and 1.0")
            
            mutation_threshold = options.get("mutation_confidence_threshold")
            if mutation_threshold is not None and not (0.0 <= mutation_threshold <= 1.0):
                raise ValidationError("Mutation confidence threshold must be between 0.0 and 1.0")
            
            # Add audit event
            state.audit_events.append({
                "event_type": "input_validated",
                "timestamp": datetime.utcnow(),
                "details": {
                    "job_id": state.job_id,
                    "image_id": state.image_id,
                    "case_id": state.case_id,
                    "processing_options": state.processing_options
                }
            })
            
            logger.info(f"Input validation successful for job {state.job_id}")
            return state
            
        except Exception as e:
            state.processing_error = f"Input validation failed: {str(e)}"
            state.validation_errors.append(str(e))
            logger.error(f"Input validation failed for job {state.job_id}: {e}")
            raise


class LoadImageNode(WorkflowNode):
    """Node 2: Load and validate image data."""
    
    async def execute(self, state: ImageAnalysisState) -> ImageAnalysisState:
        """Load image data and validate format."""
        state.update_progress("load_image", 15)
        
        try:
            # In a real implementation, this would load from the image service
            # For mock purposes, we'll simulate image loading
            
            # Simulate image loading delay
            await asyncio.sleep(0.5)
            
            # Mock image data (in real implementation, fetch from image service)
            # For now, create mock image data
            mock_image_size = 5 * 1024 * 1024  # 5MB mock image
            state.image_data = b"mock_image_data" * (mock_image_size // 15)
            
            # Validate image format and extract metadata
            state.image_metadata = {
                "width": 2048,
                "height": 2048,
                "channels": 3,
                "format": "png",
                "file_size": len(state.image_data),
                "bit_depth": 8,
                "color_space": "RGB"
            }
            
            # Validate image properties
            width = state.image_metadata.get("width", 0)
            height = state.image_metadata.get("height", 0)
            
            if width < 512 or height < 512:
                raise ValidationError("Image dimensions too small for analysis")
            
            if width > 10000 or height > 10000:
                raise ValidationError("Image dimensions too large for processing")
            
            state.image_valid = True
            
            # Add audit event
            state.audit_events.append({
                "event_type": "image_loaded",
                "timestamp": datetime.utcnow(),
                "details": {
                    "image_id": state.image_id,
                    "image_metadata": state.image_metadata,
                    "validation_status": "valid"
                }
            })
            
            logger.info(f"Image loaded successfully for job {state.job_id}")
            return state
            
        except Exception as e:
            state.processing_error = f"Image loading failed: {str(e)}"
            state.validation_errors.append(str(e))
            state.image_valid = False
            logger.error(f"Image loading failed for job {state.job_id}: {e}")
            raise


class RunPatternModelNode(WorkflowNode):
    """Node 3: Run histological pattern recognition models."""
    
    async def execute(self, state: ImageAnalysisState) -> ImageAnalysisState:
        """Execute pattern recognition models."""
        state.update_progress("run_pattern_model", 35)
        
        try:
            # Check if pattern analysis is enabled
            if not state.processing_options.get("enable_pattern_analysis", True):
                logger.info(f"Pattern analysis disabled for job {state.job_id}")
                return state
            
            # Get pattern models to run
            pattern_models = state.processing_options.get("pattern_models")
            if not pattern_models:
                pattern_models = model_registry.get_supported_patterns()
            
            # Run pattern predictions
            state.pattern_predictions = await predict_patterns(
                image_data=state.image_data,
                pattern_types=pattern_models
            )
            
            # Apply confidence threshold filtering
            pattern_threshold = state.processing_options.get("pattern_confidence_threshold")
            if pattern_threshold is not None:
                state.pattern_predictions = [
                    pred for pred in state.pattern_predictions
                    if pred.get("confidence_score", 0.0) >= pattern_threshold
                ]
            
            # Add audit event
            state.audit_events.append({
                "event_type": "pattern_analysis_completed",
                "timestamp": datetime.utcnow(),
                "details": {
                    "patterns_analyzed": len(state.pattern_predictions),
                    "models_used": pattern_models,
                    "threshold_applied": pattern_threshold
                }
            })
            
            logger.info(f"Pattern analysis completed for job {state.job_id}: {len(state.pattern_predictions)} results")
            return state
            
        except Exception as e:
            state.processing_error = f"Pattern analysis failed: {str(e)}"
            logger.error(f"Pattern analysis failed for job {state.job_id}: {e}")
            raise


class RunMutationModelNode(WorkflowNode):
    """Node 4: Run genetic mutation detection models."""
    
    async def execute(self, state: ImageAnalysisState) -> ImageAnalysisState:
        """Execute mutation detection models."""
        state.update_progress("run_mutation_model", 55)
        
        try:
            # Check if mutation analysis is enabled
            if not state.processing_options.get("enable_mutation_analysis", True):
                logger.info(f"Mutation analysis disabled for job {state.job_id}")
                return state
            
            # Get mutation models to run
            mutation_models = state.processing_options.get("mutation_models")
            if not mutation_models:
                mutation_models = model_registry.get_supported_mutations()
            
            # Run mutation predictions
            state.mutation_predictions = await predict_mutations(
                image_data=state.image_data,
                mutation_types=mutation_models
            )
            
            # Apply confidence threshold filtering
            mutation_threshold = state.processing_options.get("mutation_confidence_threshold")
            if mutation_threshold is not None:
                state.mutation_predictions = [
                    pred for pred in state.mutation_predictions
                    if pred.get("confidence_score", 0.0) >= mutation_threshold
                ]
            
            # Add audit event
            state.audit_events.append({
                "event_type": "mutation_analysis_completed",
                "timestamp": datetime.utcnow(),
                "details": {
                    "mutations_analyzed": len(state.mutation_predictions),
                    "models_used": mutation_models,
                    "threshold_applied": mutation_threshold
                }
            })
            
            logger.info(f"Mutation analysis completed for job {state.job_id}: {len(state.mutation_predictions)} results")
            return state
            
        except Exception as e:
            state.processing_error = f"Mutation analysis failed: {str(e)}"
            logger.error(f"Mutation analysis failed for job {state.job_id}: {e}")
            raise


class GenerateXAINode(WorkflowNode):
    """Node 5: Generate explainable AI artifacts."""
    
    async def execute(self, state: ImageAnalysisState) -> ImageAnalysisState:
        """Generate XAI artifacts for model explanations."""
        state.update_progress("generate_xai", 70)
        
        try:
            # Check if XAI generation is enabled
            if not state.processing_options.get("enable_xai_generation", True):
                logger.info(f"XAI generation disabled for job {state.job_id}")
                return state
            
            xai_config = get_xai_config()
            xai_methods = state.processing_options.get("xai_methods", xai_config["methods"])
            
            # Generate XAI artifacts for pattern predictions
            for pattern_pred in state.pattern_predictions:
                pattern_type = pattern_pred.get("pattern_type")
                confidence = pattern_pred.get("confidence_score", 0.0)
                
                # Only generate XAI for significant predictions
                if confidence >= 0.6:
                    for method in xai_methods:
                        artifact = await self._generate_xai_artifact(
                            method=method,
                            target_type="pattern",
                            target_name=pattern_type,
                            prediction_data=pattern_pred,
                            image_metadata=state.image_metadata
                        )
                        state.xai_artifacts.append(artifact)
            
            # Generate XAI artifacts for mutation predictions
            for mutation_pred in state.mutation_predictions:
                mutation_type = mutation_pred.get("mutation_type")
                confidence = mutation_pred.get("confidence_score", 0.0)
                
                # Only generate XAI for significant predictions
                if confidence >= 0.7:
                    for method in xai_methods:
                        artifact = await self._generate_xai_artifact(
                            method=method,
                            target_type="mutation",
                            target_name=mutation_type,
                            prediction_data=mutation_pred,
                            image_metadata=state.image_metadata
                        )
                        state.xai_artifacts.append(artifact)
            
            # Add audit event
            state.audit_events.append({
                "event_type": "xai_generation_completed",
                "timestamp": datetime.utcnow(),
                "details": {
                    "artifacts_generated": len(state.xai_artifacts),
                    "methods_used": xai_methods
                }
            })
            
            logger.info(f"XAI generation completed for job {state.job_id}: {len(state.xai_artifacts)} artifacts")
            return state
            
        except Exception as e:
            state.processing_error = f"XAI generation failed: {str(e)}"
            logger.error(f"XAI generation failed for job {state.job_id}: {e}")
            raise
    
    async def _generate_xai_artifact(
        self,
        method: str,
        target_type: str,
        target_name: str,
        prediction_data: Dict[str, Any],
        image_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a single XAI artifact."""
        # Simulate XAI generation delay
        await asyncio.sleep(0.2)
        
        artifact_id = str(uuid4())
        storage_path = f"xai_artifacts/{target_type}/{target_name}/{method}/{artifact_id}.png"
        
        # Mock artifact generation
        artifact = {
            "artifact_id": artifact_id,
            "artifact_type": method,
            "artifact_name": f"{method.upper()} explanation for {target_name}",
            "target_type": target_type,
            "target_name": target_name,
            "storage_path": storage_path,
            "file_format": "png",
            "file_size": 1024 * 512,  # Mock 512KB file
            "generation_method": method,
            "generation_parameters": {
                "method": method,
                "target_confidence": prediction_data.get("confidence_score"),
                "image_dimensions": [image_metadata.get("width"), image_metadata.get("height")]
            },
            "relevance_score": min(0.95, prediction_data.get("confidence_score", 0.0) + 0.1),
            "quality_score": 0.85 + (prediction_data.get("confidence_score", 0.0) * 0.1),
            "created_at": datetime.utcnow()
        }
        
        return artifact


class AssembleResultBundleNode(WorkflowNode):
    """Node 6: Assemble complete result bundle."""
    
    async def execute(self, state: ImageAnalysisState) -> ImageAnalysisState:
        """Assemble all results into a comprehensive bundle."""
        state.update_progress("assemble_result_bundle", 80)
        
        try:
            # Calculate overall confidence
            state.overall_confidence = calculate_overall_confidence(
                state.pattern_predictions,
                state.mutation_predictions
            )
            
            # Generate result bundle ID
            state.result_bundle_id = f"rb_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid4())[:8]}"
            
            # Assemble result bundle
            state.result_bundle = {
                "result_bundle_id": state.result_bundle_id,
                "job_id": state.job_id,
                "image_id": state.image_id,
                "case_id": state.case_id,
                "overall_confidence": state.overall_confidence,
                "model_versions": self._get_model_versions(),
                "processing_metadata": {
                    "processing_options": state.processing_options,
                    "image_metadata": state.image_metadata,
                    "processing_time": datetime.utcnow(),
                    "workflow_version": "1.0"
                },
                "pattern_results": state.pattern_predictions,
                "genetic_results": state.mutation_predictions,
                "xai_artifacts": state.xai_artifacts,
                "quality_metrics": {
                    "image_quality_score": 0.9,
                    "prediction_uncertainty": 1.0 - state.overall_confidence,
                    "artifact_count": len(state.xai_artifacts)
                }
            }
            
            # Generate analysis summary
            state.result_bundle["analysis_summary"] = self._generate_analysis_summary(state)
            
            # Add audit event
            state.audit_events.append({
                "event_type": "result_bundle_assembled",
                "timestamp": datetime.utcnow(),
                "details": {
                    "result_bundle_id": state.result_bundle_id,
                    "overall_confidence": state.overall_confidence,
                    "pattern_count": len(state.pattern_predictions),
                    "mutation_count": len(state.mutation_predictions),
                    "artifact_count": len(state.xai_artifacts)
                }
            })
            
            logger.info(f"Result bundle assembled for job {state.job_id}: {state.result_bundle_id}")
            return state
            
        except Exception as e:
            state.processing_error = f"Result assembly failed: {str(e)}"
            logger.error(f"Result assembly failed for job {state.job_id}: {e}")
            raise
    
    def _get_model_versions(self) -> Dict[str, str]:
        """Get versions of all models used."""
        versions = {}
        
        # Get pattern model versions
        for pattern_type in model_registry.get_supported_patterns():
            model = model_registry.get_pattern_model(pattern_type)
            if model:
                versions[f"pattern_{pattern_type}"] = model.version
        
        # Get mutation model versions
        for mutation_type in model_registry.get_supported_mutations():
            model = model_registry.get_mutation_model(mutation_type)
            if model:
                versions[f"mutation_{mutation_type}"] = model.version
        
        return versions
    
    def _generate_analysis_summary(self, state: ImageAnalysisState) -> str:
        """Generate human-readable analysis summary."""
        summary_parts = []
        
        # Pattern analysis summary
        if state.pattern_predictions:
            dominant_pattern = max(state.pattern_predictions, key=lambda x: x.get("confidence_score", 0))
            pattern_type = dominant_pattern.get("pattern_type")
            confidence = dominant_pattern.get("confidence_score", 0)
            summary_parts.append(f"Dominant histological pattern: {pattern_type} (confidence: {confidence:.2f})")
        
        # Mutation analysis summary
        significant_mutations = [
            pred for pred in state.mutation_predictions
            if pred.get("confidence_score", 0) >= 0.7 and pred.get("mutation_status") == "positive"
        ]
        
        if significant_mutations:
            mutation_names = [pred.get("mutation_type") for pred in significant_mutations]
            summary_parts.append(f"Detected mutations: {', '.join(mutation_names)}")
        else:
            summary_parts.append("No significant mutations detected")
        
        # Overall confidence
        summary_parts.append(f"Overall analysis confidence: {state.overall_confidence:.2f}")
        
        return ". ".join(summary_parts) + "."


class PolicyCheckNode(WorkflowNode):
    """Node 7: Apply clinical policies and guardrails."""
    
    async def execute(self, state: ImageAnalysisState) -> ImageAnalysisState:
        """Apply clinical policies and determine if HITL is required."""
        state.update_progress("policy_check", 85)
        
        try:
            guardrails = get_clinical_guardrails()
            
            # Check confidence thresholds
            confidence_decisions = self._check_confidence_thresholds(state, guardrails)
            state.policy_decisions.extend(confidence_decisions)
            
            # Check for conflicting predictions
            conflict_decisions = self._check_prediction_conflicts(state, guardrails)
            state.policy_decisions.extend(conflict_decisions)
            
            # Check mutation-specific policies
            mutation_decisions = self._check_mutation_policies(state, guardrails)
            state.policy_decisions.extend(mutation_decisions)
            
            # Determine if HITL is required
            state.requires_hitl = any(decision.get("requires_hitl", False) for decision in state.policy_decisions)
            
            if state.requires_hitl:
                hitl_reasons = [
                    decision.get("decision_reason", "")
                    for decision in state.policy_decisions
                    if decision.get("requires_hitl", False)
                ]
                state.hitl_reason = "; ".join(hitl_reasons)
            
            # Update result bundle with policy information
            if state.result_bundle:
                state.result_bundle["requires_review"] = state.requires_hitl
                state.result_bundle["review_reason"] = state.hitl_reason
                state.result_bundle["policy_decisions"] = state.policy_decisions
            
            # Add audit event
            state.audit_events.append({
                "event_type": "policy_check_completed",
                "timestamp": datetime.utcnow(),
                "details": {
                    "requires_hitl": state.requires_hitl,
                    "hitl_reason": state.hitl_reason,
                    "policy_decisions_count": len(state.policy_decisions)
                }
            })
            
            logger.info(f"Policy check completed for job {state.job_id}: HITL required={state.requires_hitl}")
            return state
            
        except Exception as e:
            state.processing_error = f"Policy check failed: {str(e)}"
            logger.error(f"Policy check failed for job {state.job_id}: {e}")
            raise
    
    def _check_confidence_thresholds(self, state: ImageAnalysisState, guardrails: Dict) -> List[Dict]:
        """Check confidence threshold policies."""
        decisions = []
        thresholds = guardrails["confidence_thresholds"]
        
        # Check pattern confidence
        for pred in state.pattern_predictions:
            confidence = pred.get("confidence_score", 0.0)
            pattern_type = pred.get("pattern_type")
            
            if confidence < thresholds["pattern_low"]:
                decisions.append({
                    "policy_type": "confidence_threshold",
                    "policy_version": "1.0",
                    "decision": "require_review",
                    "decision_reason": f"Low confidence for pattern {pattern_type}: {confidence:.3f}",
                    "confidence_threshold_used": thresholds["pattern_low"],
                    "requires_hitl": True,
                    "target_type": "pattern",
                    "target_name": pattern_type
                })
        
        # Check mutation confidence
        for pred in state.mutation_predictions:
            confidence = pred.get("confidence_score", 0.0)
            mutation_type = pred.get("mutation_type")
            
            if confidence < thresholds["mutation_low"]:
                decisions.append({
                    "policy_type": "confidence_threshold",
                    "policy_version": "1.0",
                    "decision": "require_review",
                    "decision_reason": f"Low confidence for mutation {mutation_type}: {confidence:.3f}",
                    "confidence_threshold_used": thresholds["mutation_low"],
                    "requires_hitl": True,
                    "target_type": "mutation",
                    "target_name": mutation_type
                })
        
        return decisions
    
    def _check_prediction_conflicts(self, state: ImageAnalysisState, guardrails: Dict) -> List[Dict]:
        """Check for conflicting predictions."""
        decisions = []
        conflict_threshold = guardrails["hitl_conflict_threshold"]
        
        # Check for conflicting pattern predictions
        if len(state.pattern_predictions) >= 2:
            confidences = [pred.get("confidence_score", 0.0) for pred in state.pattern_predictions]
            confidences.sort(reverse=True)
            
            if len(confidences) >= 2 and (confidences[0] - confidences[1]) < conflict_threshold:
                decisions.append({
                    "policy_type": "conflict_detection",
                    "policy_version": "1.0",
                    "decision": "require_review",
                    "decision_reason": f"Conflicting pattern predictions: {confidences[0]:.3f} vs {confidences[1]:.3f}",
                    "confidence_threshold_used": conflict_threshold,
                    "requires_hitl": True,
                    "target_type": "pattern",
                    "target_name": "multiple"
                })
        
        return decisions
    
    def _check_mutation_policies(self, state: ImageAnalysisState, guardrails: Dict) -> List[Dict]:
        """Check mutation-specific policies."""
        decisions = []
        
        # Check if HITL is required for all mutations
        if guardrails["require_hitl_for_mutations"]:
            positive_mutations = [
                pred for pred in state.mutation_predictions
                if pred.get("mutation_status") == "positive"
            ]
            
            for pred in positive_mutations:
                mutation_type = pred.get("mutation_type")
                confidence = pred.get("confidence_score", 0.0)
                
                decisions.append({
                    "policy_type": "mutation_hitl_policy",
                    "policy_version": "1.0",
                    "decision": "require_review",
                    "decision_reason": f"Positive mutation {mutation_type} requires human review",
                    "confidence_threshold_used": 0.0,
                    "requires_hitl": True,
                    "target_type": "mutation",
                    "target_name": mutation_type
                })
        
        return decisions


class PersistAndAuditNode(WorkflowNode):
    """Node 8: Persist results and create audit trail."""
    
    async def execute(self, state: ImageAnalysisState) -> ImageAnalysisState:
        """Persist results to database and create audit trail."""
        state.update_progress("persist_and_audit", 95)
        
        try:
            # In a real implementation, this would persist to the database
            # For mock purposes, we'll simulate the persistence
            
            # Simulate database persistence delay
            await asyncio.sleep(0.3)
            
            # Add final audit event
            state.audit_events.append({
                "event_type": "results_persisted",
                "timestamp": datetime.utcnow(),
                "details": {
                    "result_bundle_id": state.result_bundle_id,
                    "persistence_status": "success",
                    "database_records_created": {
                        "result_bundle": 1,
                        "pattern_results": len(state.pattern_predictions),
                        "genetic_results": len(state.mutation_predictions),
                        "xai_artifacts": len(state.xai_artifacts),
                        "policy_decisions": len(state.policy_decisions)
                    }
                }
            })
            
            # Create comprehensive audit summary
            audit_summary = {
                "job_id": state.job_id,
                "result_bundle_id": state.result_bundle_id,
                "processing_start": state.audit_events[0]["timestamp"] if state.audit_events else datetime.utcnow(),
                "processing_end": datetime.utcnow(),
                "total_events": len(state.audit_events),
                "requires_hitl": state.requires_hitl,
                "overall_confidence": state.overall_confidence,
                "events": state.audit_events
            }
            
            # In real implementation, this would be sent to audit service
            logger.info(f"Audit trail created for job {state.job_id}: {len(state.audit_events)} events")
            
            return state
            
        except Exception as e:
            state.processing_error = f"Persistence failed: {str(e)}"
            logger.error(f"Persistence failed for job {state.job_id}: {e}")
            raise


class FinalizeNode(WorkflowNode):
    """Node 9: Finalize processing and update job status."""
    
    async def execute(self, state: ImageAnalysisState) -> ImageAnalysisState:
        """Finalize processing and set completion status."""
        state.update_progress("finalize", 100)
        
        try:
            # Mark processing as complete
            state.processing_complete = True
            
            # Final validation
            if not state.result_bundle_id:
                raise BusinessLogicError("Result bundle ID not generated")
            
            if not state.result_bundle:
                raise BusinessLogicError("Result bundle not assembled")
            
            # Add final audit event
            state.audit_events.append({
                "event_type": "processing_finalized",
                "timestamp": datetime.utcnow(),
                "details": {
                    "job_id": state.job_id,
                    "result_bundle_id": state.result_bundle_id,
                    "processing_status": "completed",
                    "requires_hitl": state.requires_hitl,
                    "final_confidence": state.overall_confidence
                }
            })
            
            logger.info(f"Processing finalized for job {state.job_id}: {state.result_bundle_id}")
            return state
            
        except Exception as e:
            state.processing_error = f"Finalization failed: {str(e)}"
            state.processing_complete = False
            logger.error(f"Finalization failed for job {state.job_id}: {e}")
            raise


class ImageAnalysisGraph(BaseWorkflow):
    """
    ImageAnalysisGraph LangGraph workflow for medical image analysis.
    
    Implements the complete workflow with 9 nodes:
    ValidateInput → LoadImage → RunPatternModel → RunMutationModel → 
    GenerateXAI → AssembleResultBundle → PolicyCheck → PersistAndAudit → Finalize
    """
    
    def __init__(self):
        super().__init__("ImageAnalysisGraph", "1.0")
        self.graph = self._build_graph()
    
    def _build_graph(self) -> Graph:
        """Build the LangGraph workflow."""
        # Create workflow graph
        workflow = StateGraph(ImageAnalysisState)
        
        # Add nodes
        workflow.add_node("validate_input", ValidateInputNode())
        workflow.add_node("load_image", LoadImageNode())
        workflow.add_node("run_pattern_model", RunPatternModelNode())
        workflow.add_node("run_mutation_model", RunMutationModelNode())
        workflow.add_node("generate_xai", GenerateXAINode())
        workflow.add_node("assemble_result_bundle", AssembleResultBundleNode())
        workflow.add_node("policy_check", PolicyCheckNode())
        workflow.add_node("persist_and_audit", PersistAndAuditNode())
        workflow.add_node("finalize", FinalizeNode())
        
        # Define workflow edges
        workflow.set_entry_point("validate_input")
        workflow.add_edge("validate_input", "load_image")
        workflow.add_edge("load_image", "run_pattern_model")
        workflow.add_edge("run_pattern_model", "run_mutation_model")
        workflow.add_edge("run_mutation_model", "generate_xai")
        workflow.add_edge("generate_xai", "assemble_result_bundle")
        workflow.add_edge("assemble_result_bundle", "policy_check")
        workflow.add_edge("policy_check", "persist_and_audit")
        workflow.add_edge("persist_and_audit", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    async def execute(self, initial_state: ImageAnalysisState) -> ImageAnalysisState:
        """Execute the complete workflow."""
        try:
            logger.info(f"Starting ImageAnalysisGraph workflow for job {initial_state.job_id}")
            
            # Execute the workflow
            result = await self.graph.ainvoke(initial_state)
            
            if result.processing_complete and not result.processing_error:
                logger.info(f"ImageAnalysisGraph workflow completed successfully for job {initial_state.job_id}")
            else:
                logger.error(f"ImageAnalysisGraph workflow failed for job {initial_state.job_id}: {result.processing_error}")
            
            return result
            
        except Exception as e:
            logger.error(f"ImageAnalysisGraph workflow execution failed for job {initial_state.job_id}: {e}")
            initial_state.processing_error = str(e)
            initial_state.processing_complete = False
            return initial_state
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get workflow information."""
        return {
            "workflow_name": self.name,
            "workflow_version": self.version,
            "node_count": 9,
            "nodes": [
                "validate_input",
                "load_image", 
                "run_pattern_model",
                "run_mutation_model",
                "generate_xai",
                "assemble_result_bundle",
                "policy_check",
                "persist_and_audit",
                "finalize"
            ],
            "supports_patterns": model_registry.get_supported_patterns(),
            "supports_mutations": model_registry.get_supported_mutations(),
            "clinical_guardrails_enabled": True,
            "hitl_policies_enabled": True
        }
