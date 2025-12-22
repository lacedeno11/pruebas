"""
Policy Retrieval Agent with RAG (UC-OP-06).

This module implements the Policy Retrieval Agent with semantic search,
evidence extraction with pointer references, coverage score calculation,
conflict detection, allowlist filtering, and retrieval audit trails.
"""

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

from langchain.embeddings.base import Embeddings
from langchain.vectorstores.base import VectorStore
from langchain.schema import Document
from pydantic import BaseModel, Field, validator

from ..models.case import Case
from ..models.evidence import (
    EvidencePack, EvidenceItem, ConflictDetection, 
    RetrievalLog, EvidenceValidation
)
from ..models.policy import PolicyDocument, PolicyScope, PolicyConflict
from ..models.guardrails import SourceAllowlistEntry
from ..models.base import DocumentPointer

logger = logging.getLogger(__name__)


class SemanticQuery(BaseModel):
    """Semantic query for policy retrieval."""
    
    query_text: str = Field(..., description="Natural language query")
    query_type: str = Field(..., description="Type of query (coverage, eligibility, exclusion)")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Search filters")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results to return")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity score")
    
    @validator('query_text')
    def validate_query_text(cls, v):
        if not v or not v.strip():
            raise ValueError("query_text cannot be empty")
        return v.strip()


class RetrievalResult(BaseModel):
    """Result from policy retrieval."""
    
    document_id: str
    version: str
    title: str
    section: Optional[str] = None
    excerpt: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    relevance_score: float = Field(ge=0.0, le=1.0)
    pointer: DocumentPointer
    metadata: Dict[str, Any] = Field(default_factory=dict)
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


class CoverageAnalysis(BaseModel):
    """Coverage analysis for retrieved evidence."""
    
    total_aspects: int = Field(ge=0)
    covered_aspects: int = Field(ge=0)
    coverage_score: float = Field(ge=0.0, le=1.0)
    missing_aspects: List[str] = Field(default_factory=list)
    coverage_gaps: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    
    @validator('covered_aspects')
    def validate_covered_aspects(cls, v, values):
        if 'total_aspects' in values and v > values['total_aspects']:
            raise ValueError("covered_aspects cannot exceed total_aspects")
        return v


class ConflictAnalysis(BaseModel):
    """Conflict analysis for retrieved policies."""
    
    conflicts_detected: bool
    conflict_count: int = Field(ge=0)
    conflicts: List[PolicyConflict] = Field(default_factory=list)
    resolution_strategy: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0)


class PolicyRetrievalAgent:
    """Policy Retrieval Agent with RAG capabilities (UC-OP-06)."""
    
    def __init__(
        self,
        vector_store: VectorStore,
        embeddings: Embeddings,
        source_allowlist: List[SourceAllowlistEntry],
        enable_audit_logging: bool = True
    ):
        """
        Initialize the Policy Retrieval Agent.
        
        Args:
            vector_store: Vector store for semantic search
            embeddings: Embeddings model for query encoding
            source_allowlist: List of allowed policy sources
            enable_audit_logging: Whether to enable audit logging
        """
        self.vector_store = vector_store
        self.embeddings = embeddings
        self.source_allowlist = {entry.source_id: entry for entry in source_allowlist}
        self.enable_audit_logging = enable_audit_logging
        self.retrieval_logs: List[RetrievalLog] = []
        
        # Policy coverage aspects for different query types
        self.coverage_aspects = {
            "eligibility": [
                "age_requirements", "membership_status", "plan_type",
                "geographic_coverage", "enrollment_period", "waiting_periods"
            ],
            "coverage": [
                "covered_services", "benefit_limits", "copayments",
                "deductibles", "network_requirements", "prior_authorization"
            ],
            "exclusions": [
                "excluded_services", "experimental_treatments", "cosmetic_procedures",
                "pre_existing_conditions", "geographic_exclusions", "time_limits"
            ],
            "claims": [
                "claim_procedures", "documentation_requirements", "time_limits",
                "appeal_process", "payment_terms", "provider_requirements"
            ]
        }
        
        logger.info("PolicyRetrievalAgent initialized with RAG capabilities")
    
    async def retrieve_evidence(
        self,
        case: Case,
        query: SemanticQuery,
        policy_scope: Optional[PolicyScope] = None
    ) -> EvidencePack:
        """
        Retrieve evidence for a case using semantic search.
        
        Args:
            case: Case to retrieve evidence for
            query: Semantic query for retrieval
            policy_scope: Optional policy scope for filtering
            
        Returns:
            EvidencePack with retrieved evidence
        """
        start_time = datetime.utcnow()
        logger.info(f"Retrieving evidence for case {case.case_id} with query: {query.query_text[:100]}...")
        
        try:
            # 1. Perform semantic search
            search_results = await self._semantic_search(query, policy_scope)
            
            # 2. Filter by source allowlist
            filtered_results = await self._filter_by_allowlist(search_results)
            
            # 3. Extract evidence items with pointers
            evidence_items = await self._extract_evidence_items(filtered_results, case)
            
            # 4. Calculate coverage score
            coverage_analysis = await self._analyze_coverage(evidence_items, query)
            
            # 5. Detect conflicts
            conflict_analysis = await self._detect_conflicts(evidence_items)
            
            # 6. Create evidence pack
            evidence_pack = EvidencePack(
                case_id=case.case_id,
                items=evidence_items,
                coverage_score=coverage_analysis.coverage_score,
                conflicts=conflict_analysis.conflicts,
                retrieval_metadata={
                    "query_type": query.query_type,
                    "total_results": len(search_results),
                    "filtered_results": len(filtered_results),
                    "coverage_analysis": coverage_analysis.dict(),
                    "conflict_analysis": conflict_analysis.dict()
                }
            )
            
            # 7. Log retrieval operation
            if self.enable_audit_logging:
                await self._log_retrieval_operation(case, query, evidence_pack, start_time)
            
            logger.info(
                f"Evidence retrieval completed for case {case.case_id}: "
                f"{len(evidence_items)} items, coverage={coverage_analysis.coverage_score:.3f}, "
                f"conflicts={conflict_analysis.conflict_count}"
            )
            
            return evidence_pack
            
        except Exception as e:
            logger.error(f"Error retrieving evidence for case {case.case_id}: {e}")
            
            # Create empty evidence pack with error
            error_pack = EvidencePack(
                case_id=case.case_id,
                items=[],
                coverage_score=0.0,
                conflicts=[],
                retrieval_metadata={
                    "error": str(e),
                    "query_type": query.query_type,
                    "retrieval_failed": True
                }
            )
            
            if self.enable_audit_logging:
                await self._log_retrieval_operation(case, query, error_pack, start_time, error=str(e))
            
            return error_pack
    
    async def _semantic_search(
        self,
        query: SemanticQuery,
        policy_scope: Optional[PolicyScope] = None
    ) -> List[RetrievalResult]:
        """
        Perform semantic search in the vector store.
        
        Args:
            query: Semantic query
            policy_scope: Optional policy scope for filtering
            
        Returns:
            List of retrieval results
        """
        logger.debug(f"Performing semantic search for: {query.query_text}")
        
        # Prepare search filters
        search_filters = query.filters.copy()
        
        if policy_scope:
            # Add policy scope filters
            if policy_scope.insurer_ids:
                search_filters["insurer_id"] = {"$in": policy_scope.insurer_ids}
            
            if policy_scope.plan_ids:
                search_filters["plan_id"] = {"$in": policy_scope.plan_ids}
            
            if policy_scope.service_codes:
                search_filters["service_code"] = {"$in": policy_scope.service_codes}
            
            if policy_scope.effective_date_start:
                search_filters["effective_date"] = {"$gte": policy_scope.effective_date_start}
            
            if policy_scope.effective_date_end:
                if "effective_date" not in search_filters:
                    search_filters["effective_date"] = {}
                search_filters["effective_date"]["$lte"] = policy_scope.effective_date_end
        
        try:
            # Perform similarity search
            docs_and_scores = await asyncio.to_thread(
                self.vector_store.similarity_search_with_score,
                query.query_text,
                k=query.max_results,
                filter=search_filters if search_filters else None
            )
            
            results = []
            for doc, score in docs_and_scores:
                if score >= query.similarity_threshold:
                    # Calculate relevance score (combination of similarity and metadata)
                    relevance_score = self._calculate_relevance_score(doc, query, score)
                    
                    # Create document pointer
                    pointer = DocumentPointer(
                        document_id=doc.metadata.get("document_id", "unknown"),
                        version=doc.metadata.get("version", "1.0"),
                        section=doc.metadata.get("section"),
                        page_number=doc.metadata.get("page_number"),
                        paragraph=doc.metadata.get("paragraph"),
                        line_number=doc.metadata.get("line_number")
                    )
                    
                    result = RetrievalResult(
                        document_id=doc.metadata.get("document_id", "unknown"),
                        version=doc.metadata.get("version", "1.0"),
                        title=doc.metadata.get("title", "Unknown Document"),
                        section=doc.metadata.get("section"),
                        excerpt=doc.page_content,
                        similarity_score=score,
                        relevance_score=relevance_score,
                        pointer=pointer,
                        metadata=doc.metadata
                    )
                    
                    results.append(result)
            
            # Sort by relevance score (descending)
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            logger.debug(f"Semantic search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    def _calculate_relevance_score(
        self,
        doc: Document,
        query: SemanticQuery,
        similarity_score: float
    ) -> float:
        """
        Calculate relevance score combining similarity and metadata.
        
        Args:
            doc: Retrieved document
            query: Original query
            similarity_score: Similarity score from vector search
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        relevance = similarity_score
        
        # Boost score based on document metadata
        metadata = doc.metadata
        
        # Boost for exact query type match
        if metadata.get("document_type") == query.query_type:
            relevance = min(1.0, relevance + 0.1)
        
        # Boost for recent documents
        if "last_updated" in metadata:
            try:
                last_updated = datetime.fromisoformat(metadata["last_updated"])
                days_old = (datetime.utcnow() - last_updated).days
                if days_old < 30:  # Recent documents get boost
                    relevance = min(1.0, relevance + 0.05)
            except:
                pass
        
        # Boost for high-priority documents
        if metadata.get("priority") == "HIGH":
            relevance = min(1.0, relevance + 0.05)
        
        # Boost for official policy documents
        if metadata.get("document_category") == "OFFICIAL_POLICY":
            relevance = min(1.0, relevance + 0.1)
        
        return relevance
    
    async def _filter_by_allowlist(
        self,
        results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """
        Filter results by source allowlist.
        
        Args:
            results: Retrieval results to filter
            
        Returns:
            Filtered results
        """
        logger.debug(f"Filtering {len(results)} results by allowlist")
        
        filtered_results = []
        
        for result in results:
            allowlist_entry = self.source_allowlist.get(result.document_id)
            
            if not allowlist_entry:
                logger.debug(f"Document {result.document_id} not in allowlist, skipping")
                continue
            
            if not allowlist_entry.is_active:
                logger.debug(f"Document {result.document_id} is inactive, skipping")
                continue
            
            if allowlist_entry.expiry_date and allowlist_entry.expiry_date < datetime.utcnow():
                logger.debug(f"Document {result.document_id} has expired, skipping")
                continue
            
            if (allowlist_entry.allowed_versions and 
                result.version not in allowlist_entry.allowed_versions):
                logger.debug(f"Version {result.version} not allowed for {result.document_id}, skipping")
                continue
            
            # Add allowlist metadata to result
            result.metadata["allowlist_verified"] = True
            result.metadata["allowlist_entry"] = allowlist_entry.dict()
            
            filtered_results.append(result)
        
        logger.debug(f"Allowlist filtering returned {len(filtered_results)} results")
        return filtered_results
    
    async def _extract_evidence_items(
        self,
        results: List[RetrievalResult],
        case: Case
    ) -> List[EvidenceItem]:
        """
        Extract evidence items from retrieval results.
        
        Args:
            results: Retrieval results
            case: Case context
            
        Returns:
            List of evidence items
        """
        logger.debug(f"Extracting evidence items from {len(results)} results")
        
        evidence_items = []
        
        for result in results:
            # Create checksum for content integrity
            content_hash = hashlib.sha256(result.excerpt.encode()).hexdigest()
            
            # Extract key information from the excerpt
            extracted_info = await self._extract_key_information(result.excerpt, case)
            
            evidence_item = EvidenceItem(
                case_id=case.case_id,
                document_id=result.document_id,
                version=result.version,
                section=result.section,
                excerpt=result.excerpt,
                pointer=result.pointer,
                similarity_score=result.similarity_score,
                relevance_score=result.relevance_score,
                extraction_confidence=min(result.similarity_score + 0.1, 1.0),
                checksum=content_hash,
                extracted_info=extracted_info,
                metadata=result.metadata
            )
            
            evidence_items.append(evidence_item)
        
        logger.debug(f"Extracted {len(evidence_items)} evidence items")
        return evidence_items
    
    async def _extract_key_information(
        self,
        excerpt: str,
        case: Case
    ) -> Dict[str, Any]:
        """
        Extract key information from an excerpt.
        
        Args:
            excerpt: Text excerpt
            case: Case context
            
        Returns:
            Dictionary of extracted information
        """
        # Simple key information extraction
        # In a real implementation, this would use NLP/LLM for structured extraction
        
        extracted = {
            "excerpt_length": len(excerpt),
            "contains_amounts": bool(re.search(r'\$[\d,]+', excerpt)),
            "contains_dates": bool(re.search(r'\d{1,2}/\d{1,2}/\d{4}', excerpt)),
            "contains_percentages": bool(re.search(r'\d+%', excerpt)),
            "key_terms": []
        }
        
        # Extract key terms related to the case
        key_terms = [
            case.service_code,
            case.insurer_id,
            case.plan_id
        ]
        
        for term in key_terms:
            if term and term.lower() in excerpt.lower():
                extracted["key_terms"].append(term)
        
        return extracted
    
    async def _analyze_coverage(
        self,
        evidence_items: List[EvidenceItem],
        query: SemanticQuery
    ) -> CoverageAnalysis:
        """
        Analyze coverage of retrieved evidence.
        
        Args:
            evidence_items: Retrieved evidence items
            query: Original query
            
        Returns:
            Coverage analysis
        """
        logger.debug(f"Analyzing coverage for {len(evidence_items)} evidence items")
        
        # Get expected aspects for this query type
        expected_aspects = self.coverage_aspects.get(query.query_type, [])
        
        if not expected_aspects:
            # If no specific aspects defined, use general coverage
            return CoverageAnalysis(
                total_aspects=1,
                covered_aspects=1 if evidence_items else 0,
                coverage_score=1.0 if evidence_items else 0.0,
                confidence_score=0.8
            )
        
        # Check which aspects are covered
        covered_aspects = set()
        
        for item in evidence_items:
            excerpt_lower = item.excerpt.lower()
            
            for aspect in expected_aspects:
                # Simple keyword matching - in real implementation would use NLP
                aspect_keywords = aspect.replace("_", " ").split()
                
                if any(keyword in excerpt_lower for keyword in aspect_keywords):
                    covered_aspects.add(aspect)
        
        # Calculate coverage metrics
        total_aspects = len(expected_aspects)
        covered_count = len(covered_aspects)
        coverage_score = covered_count / total_aspects if total_aspects > 0 else 0.0
        
        missing_aspects = [aspect for aspect in expected_aspects if aspect not in covered_aspects]
        
        # Calculate confidence based on evidence quality
        avg_relevance = sum(item.relevance_score for item in evidence_items) / len(evidence_items) if evidence_items else 0.0
        confidence_score = min(coverage_score + avg_relevance * 0.2, 1.0)
        
        return CoverageAnalysis(
            total_aspects=total_aspects,
            covered_aspects=covered_count,
            coverage_score=coverage_score,
            missing_aspects=missing_aspects,
            coverage_gaps=[f"Missing coverage for {aspect}" for aspect in missing_aspects],
            confidence_score=confidence_score
        )
    
    async def _detect_conflicts(
        self,
        evidence_items: List[EvidenceItem]
    ) -> ConflictAnalysis:
        """
        Detect conflicts between evidence items.
        
        Args:
            evidence_items: Evidence items to analyze
            
        Returns:
            Conflict analysis
        """
        logger.debug(f"Detecting conflicts in {len(evidence_items)} evidence items")
        
        conflicts = []
        
        # Simple conflict detection based on contradictory statements
        # In real implementation, this would use advanced NLP/semantic analysis
        
        for i, item1 in enumerate(evidence_items):
            for j, item2 in enumerate(evidence_items[i+1:], i+1):
                conflict = await self._check_item_conflict(item1, item2)
                if conflict:
                    conflicts.append(conflict)
        
        conflicts_detected = len(conflicts) > 0
        confidence_score = 0.8 if not conflicts_detected else max(0.3, 1.0 - len(conflicts) * 0.2)
        
        return ConflictAnalysis(
            conflicts_detected=conflicts_detected,
            conflict_count=len(conflicts),
            conflicts=conflicts,
            resolution_strategy="MANUAL_REVIEW" if conflicts_detected else None,
            confidence_score=confidence_score
        )
    
    async def _check_item_conflict(
        self,
        item1: EvidenceItem,
        item2: EvidenceItem
    ) -> Optional[PolicyConflict]:
        """
        Check for conflicts between two evidence items.
        
        Args:
            item1: First evidence item
            item2: Second evidence item
            
        Returns:
            PolicyConflict if conflict detected, None otherwise
        """
        # Simple conflict detection - look for contradictory keywords
        conflict_indicators = [
            ("covered", "not covered"),
            ("eligible", "not eligible"),
            ("included", "excluded"),
            ("allowed", "prohibited"),
            ("required", "not required")
        ]
        
        excerpt1_lower = item1.excerpt.lower()
        excerpt2_lower = item2.excerpt.lower()
        
        for positive, negative in conflict_indicators:
            if positive in excerpt1_lower and negative in excerpt2_lower:
                return PolicyConflict(
                    policy_id_1=item1.document_id,
                    policy_id_2=item2.document_id,
                    conflict_type="CONTRADICTORY_STATEMENTS",
                    description=f"Conflict detected: '{positive}' vs '{negative}'",
                    severity="MEDIUM",
                    resolution_required=True,
                    detected_by="POLICY_RETRIEVAL_AGENT",
                    confidence_score=0.7
                )
            
            if negative in excerpt1_lower and positive in excerpt2_lower:
                return PolicyConflict(
                    policy_id_1=item1.document_id,
                    policy_id_2=item2.document_id,
                    conflict_type="CONTRADICTORY_STATEMENTS",
                    description=f"Conflict detected: '{negative}' vs '{positive}'",
                    severity="MEDIUM",
                    resolution_required=True,
                    detected_by="POLICY_RETRIEVAL_AGENT",
                    confidence_score=0.7
                )
        
        return None
    
    async def _log_retrieval_operation(
        self,
        case: Case,
        query: SemanticQuery,
        evidence_pack: EvidencePack,
        start_time: datetime,
        error: Optional[str] = None
    ):
        """
        Log retrieval operation for audit trail.
        
        Args:
            case: Case context
            query: Original query
            evidence_pack: Retrieved evidence pack
            start_time: Operation start time
            error: Optional error message
        """
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds() * 1000
        
        retrieval_log = RetrievalLog(
            case_id=case.case_id,
            query_text=query.query_text,
            query_type=query.query_type,
            results_count=len(evidence_pack.items),
            coverage_score=evidence_pack.coverage_score,
            processing_time_ms=processing_time,
            success=error is None,
            error_message=error,
            retrieval_metadata={
                "query_filters": query.filters,
                "max_results": query.max_results,
                "similarity_threshold": query.similarity_threshold,
                "conflicts_detected": len(evidence_pack.conflicts),
                "evidence_pack_id": evidence_pack.pack_id
            }
        )
        
        self.retrieval_logs.append(retrieval_log)
        
        logger.info(
            f"Retrieval operation logged: case={case.case_id}, "
            f"results={len(evidence_pack.items)}, time={processing_time:.1f}ms, "
            f"success={error is None}"
        )
    
    async def validate_evidence_pack(
        self,
        evidence_pack: EvidencePack
    ) -> EvidenceValidation:
        """
        Validate an evidence pack for quality and completeness.
        
        Args:
            evidence_pack: Evidence pack to validate
            
        Returns:
            Evidence validation result
        """
        logger.debug(f"Validating evidence pack {evidence_pack.pack_id}")
        
        validation_errors = []
        validation_warnings = []
        quality_score = 1.0
        
        # Check minimum evidence count
        if len(evidence_pack.items) == 0:
            validation_errors.append("No evidence items found")
            quality_score = 0.0
        elif len(evidence_pack.items) < 2:
            validation_warnings.append("Low evidence count - consider additional sources")
            quality_score -= 0.2
        
        # Check coverage score
        if evidence_pack.coverage_score < 0.5:
            validation_warnings.append(f"Low coverage score: {evidence_pack.coverage_score:.2f}")
            quality_score -= 0.3
        
        # Check for conflicts
        if evidence_pack.has_critical_conflicts():
            validation_errors.append("Critical conflicts detected in evidence")
            quality_score -= 0.5
        elif len(evidence_pack.conflicts) > 0:
            validation_warnings.append(f"{len(evidence_pack.conflicts)} conflicts detected")
            quality_score -= 0.2
        
        # Check evidence quality
        low_quality_items = [
            item for item in evidence_pack.items 
            if item.relevance_score < 0.6
        ]
        
        if low_quality_items:
            validation_warnings.append(f"{len(low_quality_items)} low-quality evidence items")
            quality_score -= 0.1
        
        # Ensure quality score is within bounds
        quality_score = max(0.0, min(1.0, quality_score))
        
        is_valid = len(validation_errors) == 0
        
        return EvidenceValidation(
            evidence_pack_id=evidence_pack.pack_id,
            is_valid=is_valid,
            quality_score=quality_score,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
            completeness_score=evidence_pack.coverage_score,
            consistency_score=1.0 - (len(evidence_pack.conflicts) * 0.2),
            recommendations=[
                "Add more evidence sources" if len(evidence_pack.items) < 3 else None,
                "Resolve conflicts before proceeding" if evidence_pack.conflicts else None,
                "Improve evidence quality" if low_quality_items else None
            ]
        )
    
    def get_retrieval_metrics(self) -> Dict[str, Any]:
        """
        Get retrieval performance metrics.
        
        Returns:
            Dictionary of metrics
        """
        if not self.retrieval_logs:
            return {
                "total_retrievals": 0,
                "success_rate": 0.0,
                "average_processing_time": 0.0,
                "average_coverage_score": 0.0
            }
        
        total_retrievals = len(self.retrieval_logs)
        successful_retrievals = sum(1 for log in self.retrieval_logs if log.success)
        success_rate = successful_retrievals / total_retrievals
        
        avg_processing_time = sum(log.processing_time_ms for log in self.retrieval_logs) / total_retrievals
        avg_coverage_score = sum(log.coverage_score for log in self.retrieval_logs) / total_retrievals
        
        return {
            "total_retrievals": total_retrievals,
            "successful_retrievals": successful_retrievals,
            "success_rate": success_rate,
            "average_processing_time": avg_processing_time,
            "average_coverage_score": avg_coverage_score,
            "last_retrieval": self.retrieval_logs[-1].retrieved_at.isoformat()
        }


# Utility functions for creating and configuring the agent

def create_policy_retrieval_agent(
    vector_store: VectorStore,
    embeddings: Embeddings,
    source_allowlist: List[SourceAllowlistEntry],
    enable_audit_logging: bool = True
) -> PolicyRetrievalAgent:
    """
    Create a Policy Retrieval Agent instance.
    
    Args:
        vector_store: Vector store for semantic search
        embeddings: Embeddings model
        source_allowlist: List of allowed sources
        enable_audit_logging: Whether to enable audit logging
        
    Returns:
        Configured PolicyRetrievalAgent
    """
    return PolicyRetrievalAgent(
        vector_store=vector_store,
        embeddings=embeddings,
        source_allowlist=source_allowlist,
        enable_audit_logging=enable_audit_logging
    )


# Import required regex module
import re
