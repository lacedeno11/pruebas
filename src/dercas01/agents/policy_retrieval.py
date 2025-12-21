"""
Policy Retrieval Agent for DERCAS 01 Policy Validation Copilot

Implements UC-OP-06: Policy retrieval using RAG (Retrieval-Augmented Generation)
and Evidence Pack construction for policy validation decisions.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field

from ..models.state import PolicyValidationState, EvidencePackState, update_audit_log
from ..models.entities import EvidenceItem, EvidencePack, PolicyDocument
from ..models.enums import CaseStatus, DocumentType
from ..storage.repositories import RepositoryManager
from ..storage.vector_store import PolicyVectorStore, VectorStoreConfig, calculate_coverage_score
from ..storage.object_store import ObjectStore
from ..guardrails.source_validation import SourceValidator, SourceType, ValidationResult

logger = logging.getLogger(__name__)


class PolicyRetrievalConfig(BaseModel):
    """Configuration for policy retrieval agent."""
    
    # RAG settings
    max_retrieved_policies: int = 10
    min_relevance_threshold: float = 0.6
    max_evidence_items: int = 20
    
    # Evidence pack settings
    min_coverage_score: float = 0.7
    require_multiple_sources: bool = True
    min_sources_count: int = 2
    
    # Query enhancement
    enable_query_expansion: bool = True
    include_case_context: bool = True
    use_semantic_search: bool = True
    
    # Source validation
    validate_policy_sources: bool = True
    require_active_policies: bool = True
    check_policy_scope: bool = True
    
    # Conflict detection
    enable_conflict_detection: bool = True
    conflict_threshold: float = 0.3
    
    # Performance settings
    max_retrieval_time_seconds: float = 10.0
    enable_caching: bool = True
    cache_ttl_minutes: int = 30


class PolicyRetrievalResult(BaseModel):
    """Result of policy retrieval process."""
    
    success: bool
    evidence_pack_id: Optional[str] = None
    
    # Retrieval metrics
    policies_found: int = 0
    evidence_items_created: int = 0
    coverage_score: float = 0.0
    
    # Quality indicators
    conflicts_detected: bool = False
    missing_sources: List[str] = Field(default_factory=list)
    quality_warnings: List[str] = Field(default_factory=list)
    
    # Processing metadata
    retrieval_time_ms: float = 0.0
    query_used: str = ""
    sources_validated: int = 0
    
    # Error information
    error_message: Optional[str] = None
    fallback_used: bool = False


class PolicyRetrievalAgent:
    """
    Policy retrieval agent implementing UC-OP-06.
    
    Responsibilities:
    - Construct search queries from case data
    - Retrieve relevant policy documents using RAG
    - Validate policy sources and scope
    - Build Evidence Pack with supporting documentation
    - Detect conflicts between policies
    - Calculate coverage scores
    """
    
    def __init__(
        self,
        config: PolicyRetrievalConfig,
        repo_manager: RepositoryManager,
        vector_store: PolicyVectorStore,
        object_store: ObjectStore,
        source_validator: SourceValidator
    ):
        self.config = config
        self.repo_manager = repo_manager
        self.vector_store = vector_store
        self.object_store = object_store
        self.source_validator = source_validator
        
        # Query builders
        self.query_builders = self._initialize_query_builders()
        
        # Evidence extractors
        self.evidence_extractors = self._initialize_evidence_extractors()
        
        # Conflict detectors
        self.conflict_detectors = self._initialize_conflict_detectors()
    
    def __call__(self, state: PolicyValidationState) -> PolicyValidationState:
        """
        Execute policy retrieval agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with evidence pack
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Starting policy retrieval for case: {state['case']['case_id']}")
            
            # Step 1: Build search query from case data
            search_query = self._build_search_query(state["case"])
            
            # Step 2: Retrieve relevant policies using RAG
            retrieved_policies = self._retrieve_policies(search_query, state["case"])
            
            # Step 3: Validate policy sources
            validated_policies = self._validate_policy_sources(retrieved_policies)
            
            # Step 4: Filter policies by scope and applicability
            applicable_policies = self._filter_applicable_policies(validated_policies, state["case"])
            
            # Step 5: Extract evidence items from policies
            evidence_items = self._extract_evidence_items(applicable_policies, search_query)
            
            # Step 6: Detect conflicts between policies
            conflicts_detected = self._detect_policy_conflicts(evidence_items)
            
            # Step 7: Calculate coverage score
            coverage_score = self._calculate_coverage_score(evidence_items, search_query)
            
            # Step 8: Build Evidence Pack
            evidence_pack = self._build_evidence_pack(
                state["case"]["case_id"],
                evidence_items,
                coverage_score,
                conflicts_detected,
                search_query
            )
            
            # Step 9: Store Evidence Pack
            stored_evidence_pack = self.repo_manager.evidence_packs.create(evidence_pack)
            
            # Step 10: Update state
            updated_state = self._update_state_with_evidence_pack(
                state,
                stored_evidence_pack,
                PolicyRetrievalResult(
                    success=True,
                    evidence_pack_id=str(stored_evidence_pack.id),
                    policies_found=len(applicable_policies),
                    evidence_items_created=len(evidence_items),
                    coverage_score=coverage_score,
                    conflicts_detected=conflicts_detected,
                    retrieval_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                    query_used=search_query,
                    sources_validated=len(validated_policies)
                ),
                start_time
            )
            
            logger.info(f"Policy retrieval completed successfully: {stored_evidence_pack.id}")
            return updated_state
            
        except Exception as e:
            logger.error(f"Policy retrieval failed: {e}")
            return self._handle_retrieval_error(state, str(e), start_time)
    
    def _initialize_query_builders(self) -> Dict[str, callable]:
        """Initialize query building functions."""
        return {
            "basic": self._build_basic_query,
            "enhanced": self._build_enhanced_query,
            "semantic": self._build_semantic_query,
        }
    
    def _initialize_evidence_extractors(self) -> Dict[str, callable]:
        """Initialize evidence extraction functions."""
        return {
            "policy_text": self._extract_policy_text_evidence,
            "tables": self._extract_table_evidence,
            "rules": self._extract_rule_evidence,
        }
    
    def _initialize_conflict_detectors(self) -> List[callable]:
        """Initialize conflict detection functions."""
        return [
            self._detect_coverage_conflicts,
            self._detect_eligibility_conflicts,
            self._detect_amount_conflicts,
            self._detect_temporal_conflicts,
        ]
    
    def _build_search_query(self, case_data: Dict[str, Any]) -> str:
        """Build search query from case data."""
        try:
            if self.config.enable_query_expansion:
                return self._build_enhanced_query(case_data)
            else:
                return self._build_basic_query(case_data)
                
        except Exception as e:
            logger.error(f"Query building failed: {e}")
            return self._build_basic_query(case_data)
    
    def _build_basic_query(self, case_data: Dict[str, Any]) -> str:
        """Build basic search query."""
        query_parts = []
        
        # Add service information
        if case_data.get("service_code"):
            query_parts.append(f"service code {case_data['service_code']}")
        
        if case_data.get("service_description"):
            query_parts.append(case_data["service_description"])
        
        # Add plan information
        if case_data.get("plan_id"):
            query_parts.append(f"plan {case_data['plan_id']}")
        
        # Add insurer information
        if case_data.get("insurer_id"):
            query_parts.append(f"insurer {case_data['insurer_id']}")
        
        return " ".join(query_parts)
    
    def _build_enhanced_query(self, case_data: Dict[str, Any]) -> str:
        """Build enhanced search query with context."""
        query_parts = []
        
        # Core service information
        if case_data.get("service_code"):
            query_parts.append(f"service code {case_data['service_code']}")
        
        if case_data.get("service_description"):
            query_parts.append(case_data["service_description"])
        
        # Plan and coverage information
        if case_data.get("plan_id"):
            query_parts.append(f"plan {case_data['plan_id']} coverage benefits")
        
        # Provider information
        if case_data.get("provider_id"):
            query_parts.append(f"provider {case_data['provider_id']} authorization")
        
        # Add context keywords
        if self.config.include_case_context:
            context_keywords = [
                "eligibility", "coverage", "benefits", "exclusions",
                "prior authorization", "medical necessity", "limitations"
            ]
            query_parts.extend(context_keywords)
        
        return " ".join(query_parts)
    
    def _build_semantic_query(self, case_data: Dict[str, Any]) -> str:
        """Build semantic search query."""
        # For semantic search, we want more natural language
        service_desc = case_data.get("service_description", "")
        service_code = case_data.get("service_code", "")
        plan_id = case_data.get("plan_id", "")
        
        if service_desc:
            return f"What are the coverage policies for {service_desc} under plan {plan_id}?"
        elif service_code:
            return f"What are the policies for service code {service_code} under plan {plan_id}?"
        else:
            return f"What are the general coverage policies for plan {plan_id}?"
    
    def _retrieve_policies(self, search_query: str, case_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Retrieve relevant policies using vector search."""
        try:
            # Build filters for the search
            filters = self._build_search_filters(case_data)
            
            # Perform vector search
            search_results = self.vector_store.search_similar(
                query=search_query,
                filters=filters,
                max_results=self.config.max_retrieved_policies,
                similarity_threshold=self.config.min_relevance_threshold
            )
            
            # Convert search results to policy format
            policies = []
            for result in search_results:
                policy_info = {
                    "doc_id": result["metadata"]["doc_id"],
                    "version": result["metadata"]["version"],
                    "title": result["metadata"].get("title", ""),
                    "content": result["content"],
                    "relevance_score": result["similarity_score"],
                    "chunk_id": result["chunk_id"],
                    "metadata": result["metadata"]
                }
                policies.append(policy_info)
            
            logger.info(f"Retrieved {len(policies)} relevant policies")
            return policies
            
        except Exception as e:
            logger.error(f"Policy retrieval failed: {e}")
            return []
    
    def _build_search_filters(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build search filters from case data."""
        filters = {}
        
        # Filter by insurer
        if case_data.get("insurer_id"):
            filters["insurer_id"] = case_data["insurer_id"]
        
        # Filter by document status
        if self.config.require_active_policies:
            filters["status"] = "ACTIVE"
        
        return filters
    
    def _validate_policy_sources(self, policies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate policy sources using source validator."""
        if not self.config.validate_policy_sources:
            return policies
        
        validated_policies = []
        
        for policy in policies:
            try:
                # Validate the policy source
                validation_result = self.source_validator.validate_source(
                    source_id=policy["doc_id"],
                    source_type=SourceType.POLICY_DOCUMENT,
                    source_location=f"policy://{policy['doc_id']}/{policy['version']}",
                    metadata=policy["metadata"]
                )
                
                if validation_result.validation_result == ValidationResult.ALLOWED:
                    policy["source_validated"] = True
                    policy["trust_score"] = validation_result.trust_score
                    validated_policies.append(policy)
                else:
                    logger.warning(f"Policy source validation failed: {policy['doc_id']}")
                    policy["source_validated"] = False
                    policy["validation_issues"] = validation_result.security_issues
                    
            except Exception as e:
                logger.error(f"Source validation error for policy {policy['doc_id']}: {e}")
                policy["source_validated"] = False
                policy["validation_error"] = str(e)
        
        logger.info(f"Validated {len(validated_policies)} out of {len(policies)} policies")
        return validated_policies
    
    def _filter_applicable_policies(self, policies: List[Dict[str, Any]], case_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter policies by scope and applicability."""
        if not self.config.check_policy_scope:
            return policies
        
        applicable_policies = []
        
        for policy in policies:
            try:
                if self._is_policy_applicable(policy, case_data):
                    applicable_policies.append(policy)
                else:
                    logger.debug(f"Policy {policy['doc_id']} not applicable to case")
                    
            except Exception as e:
                logger.error(f"Policy applicability check failed: {e}")
                # Include policy if check fails (fail open)
                applicable_policies.append(policy)
        
        logger.info(f"Found {len(applicable_policies)} applicable policies")
        return applicable_policies
    
    def _is_policy_applicable(self, policy: Dict[str, Any], case_data: Dict[str, Any]) -> bool:
        """Check if policy is applicable to the case."""
        metadata = policy.get("metadata", {})
        
        # Check insurer match
        policy_insurer = metadata.get("insurer_id")
        if policy_insurer and policy_insurer != case_data.get("insurer_id"):
            return False
        
        # Check plan match
        policy_plans = metadata.get("plan_ids", [])
        if isinstance(policy_plans, str):
            import json
            try:
                policy_plans = json.loads(policy_plans)
            except:
                policy_plans = [policy_plans]
        
        case_plan = case_data.get("plan_id")
        if policy_plans and case_plan and case_plan not in policy_plans:
            return False
        
        # Check service code match
        policy_services = metadata.get("service_codes", [])
        if isinstance(policy_services, str):
            import json
            try:
                policy_services = json.loads(policy_services)
            except:
                policy_services = [policy_services]
        
        case_service = case_data.get("service_code")
        if policy_services and case_service and case_service not in policy_services:
            return False
        
        # Check effective date
        effective_date = metadata.get("effective_date")
        if effective_date:
            try:
                effective_dt = datetime.fromisoformat(effective_date)
                if effective_dt > datetime.utcnow():
                    return False
            except:
                pass
        
        return True
    
    def _extract_evidence_items(self, policies: List[Dict[str, Any]], search_query: str) -> List[EvidenceItem]:
        """Extract evidence items from policies."""
        evidence_items = []
        
        for policy in policies:
            try:
                # Extract different types of evidence
                for extractor_name, extractor_func in self.evidence_extractors.items():
                    items = extractor_func(policy, search_query)
                    evidence_items.extend(items)
                    
            except Exception as e:
                logger.error(f"Evidence extraction failed for policy {policy['doc_id']}: {e}")
        
        # Remove duplicates and sort by relevance
        unique_items = self._deduplicate_evidence_items(evidence_items)
        sorted_items = sorted(unique_items, key=lambda x: x.relevance_score, reverse=True)
        
        # Limit to max items
        limited_items = sorted_items[:self.config.max_evidence_items]
        
        logger.info(f"Extracted {len(limited_items)} evidence items")
        return limited_items
    
    def _extract_policy_text_evidence(self, policy: Dict[str, Any], search_query: str) -> List[EvidenceItem]:
        """Extract text-based evidence from policy."""
        evidence_items = []
        
        try:
            content = policy["content"]
            doc_id = policy["doc_id"]
            version = policy["version"]
            relevance_score = policy["relevance_score"]
            
            # Create evidence item for the policy content
            evidence_item = EvidenceItem(
                doc_id=doc_id,
                version=version,
                checksum=policy["metadata"].get("checksum", ""),
                pointer=policy.get("chunk_id", "full_document"),
                excerpt=content[:500] + "..." if len(content) > 500 else content,
                relevance_score=relevance_score,
                confidence_score=min(relevance_score * 1.1, 1.0)
            )
            
            evidence_items.append(evidence_item)
            
        except Exception as e:
            logger.error(f"Text evidence extraction failed: {e}")
        
        return evidence_items
    
    def _extract_table_evidence(self, policy: Dict[str, Any], search_query: str) -> List[EvidenceItem]:
        """Extract table-based evidence from policy."""
        evidence_items = []
        
        try:
            content = policy["content"]
            
            # Simple table detection (in production, would use more sophisticated parsing)
            if "table" in content.lower() or "|" in content:
                doc_id = policy["doc_id"]
                version = policy["version"]
                
                evidence_item = EvidenceItem(
                    doc_id=doc_id,
                    version=version,
                    checksum=policy["metadata"].get("checksum", ""),
                    pointer="table_reference",
                    excerpt="Table data found in policy document",
                    table_ref="Table 1",
                    relevance_score=policy["relevance_score"] * 0.9,
                    confidence_score=policy["relevance_score"] * 0.8
                )
                
                evidence_items.append(evidence_item)
                
        except Exception as e:
            logger.error(f"Table evidence extraction failed: {e}")
        
        return evidence_items
    
    def _extract_rule_evidence(self, policy: Dict[str, Any], search_query: str) -> List[EvidenceItem]:
        """Extract rule-based evidence from policy."""
        evidence_items = []
        
        try:
            content = policy["content"]
            
            # Look for rule-like content
            rule_keywords = ["must", "shall", "required", "prohibited", "excluded", "covered"]
            if any(keyword in content.lower() for keyword in rule_keywords):
                doc_id = policy["doc_id"]
                version = policy["version"]
                
                evidence_item = EvidenceItem(
                    doc_id=doc_id,
                    version=version,
                    checksum=policy["metadata"].get("checksum", ""),
                    pointer="rule_reference",
                    excerpt="Policy rule found",
                    relevance_score=policy["relevance_score"] * 1.1,
                    confidence_score=policy["relevance_score"]
                )
                
                evidence_items.append(evidence_item)
                
        except Exception as e:
            logger.error(f"Rule evidence extraction failed: {e}")
        
        return evidence_items
    
    def _deduplicate_evidence_items(self, evidence_items: List[EvidenceItem]) -> List[EvidenceItem]:
        """Remove duplicate evidence items."""
        seen = set()
        unique_items = []
        
        for item in evidence_items:
            # Create a key for deduplication
            key = f"{item.doc_id}:{item.version}:{item.pointer}"
            
            if key not in seen:
                seen.add(key)
                unique_items.append(item)
        
        return unique_items
    
    def _detect_policy_conflicts(self, evidence_items: List[EvidenceItem]) -> bool:
        """Detect conflicts between policies."""
        if not self.config.enable_conflict_detection:
            return False
        
        try:
            for detector in self.conflict_detectors:
                if detector(evidence_items):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Conflict detection failed: {e}")
            return False
    
    def _detect_coverage_conflicts(self, evidence_items: List[EvidenceItem]) -> bool:
        """Detect coverage conflicts between policies."""
        # Simplified conflict detection
        coverage_statements = []
        
        for item in evidence_items:
            excerpt = item.excerpt.lower()
            if "covered" in excerpt or "not covered" in excerpt:
                coverage_statements.append(excerpt)
        
        # Check for contradictory statements
        has_covered = any("covered" in stmt and "not covered" not in stmt for stmt in coverage_statements)
        has_not_covered = any("not covered" in stmt for stmt in coverage_statements)
        
        return has_covered and has_not_covered
    
    def _detect_eligibility_conflicts(self, evidence_items: List[EvidenceItem]) -> bool:
        """Detect eligibility conflicts."""
        return False  # Simplified implementation
    
    def _detect_amount_conflicts(self, evidence_items: List[EvidenceItem]) -> bool:
        """Detect amount/limit conflicts."""
        return False  # Simplified implementation
    
    def _detect_temporal_conflicts(self, evidence_items: List[EvidenceItem]) -> bool:
        """Detect temporal conflicts."""
        return False  # Simplified implementation
    
    def _calculate_coverage_score(self, evidence_items: List[EvidenceItem], search_query: str) -> float:
        """Calculate coverage score for evidence pack."""
        if not evidence_items:
            return 0.0
        
        # Use the utility function from vector store
        evidence_dicts = [item.dict() for item in evidence_items]
        return calculate_coverage_score(evidence_dicts, search_query)
    
    def _build_evidence_pack(
        self,
        case_id: str,
        evidence_items: List[EvidenceItem],
        coverage_score: float,
        conflicts_detected: bool,
        search_query: str
    ) -> EvidencePack:
        """Build Evidence Pack entity."""
        try:
            # Identify missing sources
            missing_sources = []
            if self.config.require_multiple_sources and len(evidence_items) < self.config.min_sources_count:
                missing_sources.append("insufficient_sources")
            
            if coverage_score < self.config.min_coverage_score:
                missing_sources.append("insufficient_coverage")
            
            # Create Evidence Pack
            evidence_pack = EvidencePack(
                case_id=case_id,
                items=[item.dict() for item in evidence_items],
                coverage_score=coverage_score,
                conflicts_detected=conflicts_detected,
                missing_sources=missing_sources,
                retrieval_query=search_query,
                retrieval_timestamp=datetime.utcnow(),
                retrieval_model_version="vector_store_v1.0"
            )
            
            return evidence_pack
            
        except Exception as e:
            logger.error(f"Evidence pack creation failed: {e}")
            raise
    
    def _update_state_with_evidence_pack(
        self,
        state: PolicyValidationState,
        evidence_pack: EvidencePack,
        result: PolicyRetrievalResult,
        start_time: datetime
    ) -> PolicyValidationState:
        """Update state with evidence pack."""
        
        # Update evidence pack state
        state["evidence_pack"] = EvidencePackState(
            items=evidence_pack.items,
            coverage_score=evidence_pack.coverage_score,
            conflicts_detected=evidence_pack.conflicts_detected,
            missing_sources=evidence_pack.missing_sources,
            retrieval_timestamp=evidence_pack.retrieval_timestamp,
            retrieval_model_version=evidence_pack.retrieval_model_version
        )
        
        # Update case status
        state["case"]["state"] = CaseStatus.RETRIEVING_POLICY
        
        # Update audit log
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        state = update_audit_log(
            state,
            node_name="policy_retrieval",
            node_input={
                "case_id": state["case"]["case_id"],
                "query": result.query_used
            },
            node_output={
                "success": result.success,
                "evidence_pack_id": result.evidence_pack_id,
                "policies_found": result.policies_found,
                "evidence_items_created": result.evidence_items_created,
                "coverage_score": result.coverage_score,
                "conflicts_detected": result.conflicts_detected,
                "sources_validated": result.sources_validated
            },
            execution_time_ms=processing_time
        )
        
        # Set next node
        state["next_node"] = "rules_builder"
        
        return state
    
    def _handle_retrieval_error(
        self,
        state: PolicyValidationState,
        error_message: str,
        start_time: datetime
    ) -> PolicyValidationState:
        """Handle policy retrieval error."""
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Update case status
        state["case"]["state"] = CaseStatus.ERROR
        
        # Create empty evidence pack
        state["evidence_pack"] = EvidencePackState(
            items=[],
            coverage_score=0.0,
            conflicts_detected=False,
            missing_sources=["retrieval_error"],
            retrieval_timestamp=datetime.utcnow()
        )
        
        # Log audit event
        state = update_audit_log(
            state,
            node_name="policy_retrieval",
            node_input={"case_id": state["case"]["case_id"]},
            node_output={"success": False},
            execution_time_ms=processing_time,
            error=error_message
        )
        
        # Set error state
        state["error_occurred"] = True
        state["error_message"] = f"Policy retrieval error: {error_message}"
        
        # Try to continue with empty evidence pack
        state["next_node"] = "rules_builder"
        
        return state


# Factory function
def create_policy_retrieval_agent(
    config: Optional[PolicyRetrievalConfig] = None,
    repo_manager: Optional[RepositoryManager] = None,
    vector_store: Optional[PolicyVectorStore] = None,
    object_store: Optional[ObjectStore] = None,
    source_validator: Optional[SourceValidator] = None
) -> PolicyRetrievalAgent:
    """Create a policy retrieval agent with default or custom configuration."""
    if config is None:
        config = PolicyRetrievalConfig()
    
    if repo_manager is None:
        raise ValueError("Repository manager is required")
    
    if vector_store is None:
        raise ValueError("Vector store is required")
    
    if object_store is None:
        raise ValueError("Object store is required")
    
    if source_validator is None:
        raise ValueError("Source validator is required")
    
    return PolicyRetrievalAgent(config, repo_manager, vector_store, object_store, source_validator)
