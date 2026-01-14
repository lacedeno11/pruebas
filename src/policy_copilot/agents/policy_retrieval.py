"""
Policy Retrieval Agent (RAG) for Policy Validation Copilot

This module implements UC-OP-06 with vector database integration, semantic search,
evidence extraction with exact pointers, coverage score calculation, conflict detection,
and Evidence Pack construction with allowlist filtering and retrieval metrics.
"""

import hashlib
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

import numpy as np
from pydantic import BaseModel, Field

from ..models.base import DocumentPointer
from ..models.evidence import ConflictDetection, EvidenceItem, EvidencePack
from ..models.state import PolicyValidationState

logger = logging.getLogger(__name__)


class VectorSearchResult(BaseModel):
    """Result from vector database search."""
    
    document_id: str = Field(..., description="Document identifier")
    chunk_id: str = Field(..., description="Document chunk identifier")
    content: str = Field(..., description="Retrieved content")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    
    # Document location information
    page_number: Optional[int] = Field(None, description="Page number in document")
    section: Optional[str] = Field(None, description="Document section")
    paragraph: Optional[int] = Field(None, description="Paragraph number")
    
    # Content context
    surrounding_context: Optional[str] = Field(None, description="Surrounding context")
    document_title: Optional[str] = Field(None, description="Document title")
    document_version: Optional[str] = Field(None, description="Document version")


class RetrievalQuery(BaseModel):
    """Query for policy retrieval."""
    
    query_text: str = Field(..., description="Query text for semantic search")
    query_type: str = Field("semantic", description="Type of query (semantic, keyword, hybrid)")
    
    # Filtering criteria
    document_types: Optional[List[str]] = Field(None, description="Filter by document types")
    policy_areas: Optional[List[str]] = Field(None, description="Filter by policy areas")
    date_range: Optional[Tuple[datetime, datetime]] = Field(None, description="Filter by date range")
    
    # Search parameters
    max_results: int = Field(10, ge=1, le=100, description="Maximum number of results")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")
    
    # Context expansion
    include_context: bool = Field(True, description="Include surrounding context")
    context_window: int = Field(200, description="Context window size in characters")


class PolicyRetrievalConfig(BaseModel):
    """Configuration for Policy Retrieval Agent."""
    
    # Vector database settings
    vector_db_url: str = "http://localhost:8000"
    vector_db_collection: str = "policy_documents"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    
    # Search settings
    default_similarity_threshold: float = 0.7
    max_results_per_query: int = 20
    context_window_size: int = 300
    
    # Evidence extraction settings
    min_evidence_length: int = 50
    max_evidence_length: int = 2000
    evidence_overlap_threshold: float = 0.8
    
    # Coverage calculation settings
    coverage_weights: Dict[str, float] = {
        "relevance": 0.4,
        "completeness": 0.3,
        "specificity": 0.2,
        "recency": 0.1
    }
    
    # Conflict detection settings
    conflict_similarity_threshold: float = 0.9
    contradiction_keywords: List[str] = [
        "not", "except", "unless", "however", "but", "although", 
        "nevertheless", "contrary", "opposite", "different"
    ]
    
    # Allowlist settings
    allowed_document_sources: Set[str] = {
        "policy_documents_v2.1",
        "medical_guidelines_v1.3",
        "regulatory_framework_v3.0",
        "approved_procedures_v2.0",
        "coverage_definitions_v1.8",
        "exclusions_list_v2.2"
    }
    
    # Performance settings
    cache_ttl_seconds: int = 3600
    max_concurrent_searches: int = 5
    search_timeout_seconds: int = 30
    
    # Quality thresholds
    min_coverage_score: float = 0.6
    max_conflicts_allowed: int = 2
    evidence_quality_threshold: float = 0.8


class VectorDatabase:
    """Vector database interface for semantic search."""
    
    def __init__(self, config: PolicyRetrievalConfig):
        self.config = config
        self.client = None  # Would be initialized with actual vector DB client
        self.embedding_cache = {}
        
    def initialize(self) -> None:
        """Initialize vector database connection."""
        # In a real implementation, this would initialize ChromaDB, Pinecone, etc.
        logger.info(f"Initializing vector database: {self.config.vector_db_url}")
        
    def embed_text(self, text: str) -> List[float]:
        """Generate embeddings for text."""
        # Mock embedding generation (would use actual embedding model)
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.embedding_cache:
            return self.embedding_cache[text_hash]
        
        # Generate mock embedding
        np.random.seed(hash(text) % 2**32)
        embedding = np.random.normal(0, 1, self.config.embedding_dimension).tolist()
        
        self.embedding_cache[text_hash] = embedding
        return embedding
    
    def search(self, query: RetrievalQuery) -> List[VectorSearchResult]:
        """Perform semantic search in vector database."""
        # Generate query embedding
        query_embedding = self.embed_text(query.query_text)
        
        # Mock search results (would query actual vector database)
        mock_results = self._generate_mock_results(query)
        
        # Filter by similarity threshold
        filtered_results = [
            result for result in mock_results 
            if result.similarity_score >= query.similarity_threshold
        ]
        
        # Sort by similarity score
        filtered_results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Limit results
        return filtered_results[:query.max_results]
    
    def _generate_mock_results(self, query: RetrievalQuery) -> List[VectorSearchResult]:
        """Generate mock search results for development."""
        mock_documents = [
            {
                "document_id": "policy_doc_001",
                "content": f"Medical coverage includes emergency services, hospitalization, and outpatient care as defined in section 4.2. Coverage applies when services are medically necessary and provided by network providers.",
                "similarity_score": 0.92,
                "page_number": 15,
                "section": "Coverage Definitions",
                "document_title": "Medical Policy Guidelines v2.1",
                "document_version": "2.1.0"
            },
            {
                "document_id": "policy_doc_002", 
                "content": f"Prior authorization is required for specialist consultations, advanced imaging, and surgical procedures exceeding $5,000. Authorization requests must be submitted within 48 hours of service recommendation.",
                "similarity_score": 0.88,
                "page_number": 23,
                "section": "Prior Authorization Requirements",
                "document_title": "Prior Authorization Policy v1.9",
                "document_version": "1.9.0"
            },
            {
                "document_id": "policy_doc_003",
                "content": f"Emergency services are covered 24/7 without prior authorization when provided at in-network facilities. Out-of-network emergency services are covered at in-network benefit levels.",
                "similarity_score": 0.85,
                "page_number": 8,
                "section": "Emergency Coverage",
                "document_title": "Emergency Services Policy v1.6",
                "document_version": "1.6.0"
            },
            {
                "document_id": "policy_doc_004",
                "content": f"Preventive care services including annual checkups, vaccinations, and screenings are covered at 100% when provided by network providers. No deductible applies to preventive services.",
                "similarity_score": 0.82,
                "page_number": 12,
                "section": "Preventive Care Benefits",
                "document_title": "Preventive Care Policy v1.4",
                "document_version": "1.4.0"
            },
            {
                "document_id": "policy_doc_005",
                "content": f"Experimental and investigational treatments are excluded from coverage unless specifically approved through the clinical trial coverage program. Coverage decisions require medical director review.",
                "similarity_score": 0.78,
                "page_number": 45,
                "section": "Coverage Exclusions",
                "document_title": "Coverage Exclusions List v2.2",
                "document_version": "2.2.0"
            }
        ]
        
        results = []
        for i, doc in enumerate(mock_documents):
            if i >= query.max_results:
                break
                
            result = VectorSearchResult(
                document_id=doc["document_id"],
                chunk_id=f"{doc['document_id']}_chunk_{i+1}",
                content=doc["content"],
                similarity_score=doc["similarity_score"],
                metadata={
                    "source": doc["document_id"],
                    "indexed_at": datetime.utcnow().isoformat()
                },
                page_number=doc.get("page_number"),
                section=doc.get("section"),
                document_title=doc.get("document_title"),
                document_version=doc.get("document_version")
            )
            results.append(result)
        
        return results


class EvidenceExtractor:
    """Extract evidence items from search results."""
    
    def __init__(self, config: PolicyRetrievalConfig):
        self.config = config
    
    def extract_evidence(
        self, 
        search_results: List[VectorSearchResult],
        query_context: str
    ) -> List[EvidenceItem]:
        """Extract evidence items from search results."""
        evidence_items = []
        
        for result in search_results:
            # Create document pointer
            pointer = self._create_document_pointer(result)
            
            # Extract relevant excerpt
            excerpt = self._extract_excerpt(result, query_context)
            
            # Calculate verification score
            verification_score = self._calculate_verification_score(result, query_context)
            
            # Create evidence item
            evidence_item = EvidenceItem(
                id=uuid4(),
                doc_id=result.document_id,
                doc_version=result.document_version or "1.0.0",
                doc_checksum=self._calculate_checksum(result.content),
                pointer=pointer,
                excerpt=excerpt,
                verified=verification_score > self.config.evidence_quality_threshold,
                verification_method="semantic_similarity",
                relevance_score=result.similarity_score,
                extraction_confidence=verification_score,
                source_metadata={
                    "document_title": result.document_title,
                    "section": result.section,
                    "similarity_score": result.similarity_score,
                    "extraction_method": "vector_search"
                }
            )
            
            evidence_items.append(evidence_item)
        
        return evidence_items
    
    def _create_document_pointer(self, result: VectorSearchResult) -> DocumentPointer:
        """Create document pointer from search result."""
        return DocumentPointer(
            page_number=result.page_number,
            section_title=result.section,
            paragraph_number=result.paragraph,
            line_number=None,
            character_offset=None,
            table_reference=None,
            cell_reference=None,
            exact_quote=result.content[:200] + "..." if len(result.content) > 200 else result.content
        )
    
    def _extract_excerpt(self, result: VectorSearchResult, query_context: str) -> str:
        """Extract relevant excerpt from search result."""
        content = result.content
        
        # Ensure excerpt is within length limits
        if len(content) < self.config.min_evidence_length:
            # Add surrounding context if available
            if result.surrounding_context:
                content = result.surrounding_context
        
        if len(content) > self.config.max_evidence_length:
            # Truncate to max length, trying to preserve sentence boundaries
            truncated = content[:self.config.max_evidence_length]
            last_period = truncated.rfind('.')
            if last_period > self.config.max_evidence_length * 0.8:
                content = truncated[:last_period + 1]
            else:
                content = truncated + "..."
        
        return content
    
    def _calculate_verification_score(self, result: VectorSearchResult, query_context: str) -> float:
        """Calculate verification score for evidence item."""
        score = 0.0
        
        # Base score from similarity
        score += result.similarity_score * 0.6
        
        # Bonus for having metadata
        if result.document_title:
            score += 0.1
        if result.section:
            score += 0.1
        if result.page_number:
            score += 0.1
        
        # Bonus for content quality
        content_length = len(result.content)
        if self.config.min_evidence_length <= content_length <= self.config.max_evidence_length:
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_checksum(self, content: str) -> str:
        """Calculate checksum for content."""
        return hashlib.sha256(content.encode()).hexdigest()


class ConflictDetector:
    """Detect conflicts between evidence items."""
    
    def __init__(self, config: PolicyRetrievalConfig):
        self.config = config
    
    def detect_conflicts(self, evidence_items: List[EvidenceItem]) -> List[ConflictDetection]:
        """Detect conflicts between evidence items."""
        conflicts = []
        
        for i, item1 in enumerate(evidence_items):
            for j, item2 in enumerate(evidence_items[i+1:], i+1):
                conflict = self._check_conflict_pair(item1, item2)
                if conflict:
                    conflicts.append(conflict)
        
        return conflicts
    
    def _check_conflict_pair(self, item1: EvidenceItem, item2: EvidenceItem) -> Optional[ConflictDetection]:
        """Check for conflicts between two evidence items."""
        # Calculate content similarity
        similarity = self._calculate_content_similarity(item1.excerpt, item2.excerpt)
        
        # If content is very similar, check for contradictions
        if similarity > self.config.conflict_similarity_threshold:
            contradiction_score = self._detect_contradiction(item1.excerpt, item2.excerpt)
            
            if contradiction_score > 0.5:
                return ConflictDetection(
                    id=uuid4(),
                    evidence_item_1_id=item1.id,
                    evidence_item_2_id=item2.id,
                    conflict_type="CONTRADICTION",
                    conflict_score=contradiction_score,
                    description=f"Contradictory statements detected between {item1.doc_id} and {item2.doc_id}",
                    resolution_strategy="MANUAL_REVIEW",
                    detected_by="CONFLICT_DETECTOR",
                    resolution_notes=f"Similarity: {similarity:.3f}, Contradiction: {contradiction_score:.3f}"
                )
        
        # Check for policy version conflicts
        if item1.doc_id == item2.doc_id and item1.doc_version != item2.doc_version:
            return ConflictDetection(
                id=uuid4(),
                evidence_item_1_id=item1.id,
                evidence_item_2_id=item2.id,
                conflict_type="VERSION_CONFLICT",
                conflict_score=0.8,
                description=f"Different versions of same document: {item1.doc_version} vs {item2.doc_version}",
                resolution_strategy="USE_LATEST_VERSION",
                detected_by="CONFLICT_DETECTOR",
                resolution_notes=f"Document: {item1.doc_id}"
            )
        
        return None
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings."""
        # Simple word-based similarity (would use embeddings in real implementation)
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _detect_contradiction(self, content1: str, content2: str) -> float:
        """Detect contradiction between two content strings."""
        contradiction_score = 0.0
        
        # Check for contradiction keywords
        content1_lower = content1.lower()
        content2_lower = content2.lower()
        
        contradiction_indicators = 0
        for keyword in self.config.contradiction_keywords:
            if keyword in content1_lower or keyword in content2_lower:
                contradiction_indicators += 1
        
        # Base contradiction score from keywords
        contradiction_score += min(contradiction_indicators * 0.2, 0.6)
        
        # Check for opposing statements (simplified)
        opposing_pairs = [
            ("covered", "not covered"),
            ("included", "excluded"),
            ("required", "not required"),
            ("allowed", "prohibited"),
            ("eligible", "ineligible")
        ]
        
        for positive, negative in opposing_pairs:
            if positive in content1_lower and negative in content2_lower:
                contradiction_score += 0.4
            elif negative in content1_lower and positive in content2_lower:
                contradiction_score += 0.4
        
        return min(contradiction_score, 1.0)


class CoverageCalculator:
    """Calculate coverage score for evidence pack."""
    
    def __init__(self, config: PolicyRetrievalConfig):
        self.config = config
    
    def calculate_coverage_score(
        self, 
        evidence_items: List[EvidenceItem],
        query_context: str,
        case_requirements: List[str]
    ) -> float:
        """Calculate overall coverage score for evidence pack."""
        if not evidence_items:
            return 0.0
        
        # Calculate individual coverage components
        relevance_score = self._calculate_relevance_score(evidence_items, query_context)
        completeness_score = self._calculate_completeness_score(evidence_items, case_requirements)
        specificity_score = self._calculate_specificity_score(evidence_items)
        recency_score = self._calculate_recency_score(evidence_items)
        
        # Weighted combination
        weights = self.config.coverage_weights
        coverage_score = (
            weights["relevance"] * relevance_score +
            weights["completeness"] * completeness_score +
            weights["specificity"] * specificity_score +
            weights["recency"] * recency_score
        )
        
        return min(coverage_score, 1.0)
    
    def _calculate_relevance_score(self, evidence_items: List[EvidenceItem], query_context: str) -> float:
        """Calculate relevance score based on similarity scores."""
        if not evidence_items:
            return 0.0
        
        # Average of top relevance scores
        relevance_scores = [item.relevance_score for item in evidence_items]
        relevance_scores.sort(reverse=True)
        
        # Take top 5 scores or all if fewer
        top_scores = relevance_scores[:5]
        return sum(top_scores) / len(top_scores)
    
    def _calculate_completeness_score(self, evidence_items: List[EvidenceItem], case_requirements: List[str]) -> float:
        """Calculate completeness score based on coverage of requirements."""
        if not case_requirements:
            return 1.0
        
        covered_requirements = 0
        for requirement in case_requirements:
            requirement_lower = requirement.lower()
            for item in evidence_items:
                if requirement_lower in item.excerpt.lower():
                    covered_requirements += 1
                    break
        
        return covered_requirements / len(case_requirements)
    
    def _calculate_specificity_score(self, evidence_items: List[EvidenceItem]) -> float:
        """Calculate specificity score based on evidence detail level."""
        if not evidence_items:
            return 0.0
        
        specificity_scores = []
        for item in evidence_items:
            # Score based on excerpt length and detail
            excerpt_length = len(item.excerpt)
            if excerpt_length < 100:
                specificity = 0.3
            elif excerpt_length < 300:
                specificity = 0.6
            elif excerpt_length < 600:
                specificity = 0.8
            else:
                specificity = 1.0
            
            # Bonus for having specific references
            if item.pointer.page_number:
                specificity += 0.1
            if item.pointer.section_title:
                specificity += 0.1
            
            specificity_scores.append(min(specificity, 1.0))
        
        return sum(specificity_scores) / len(specificity_scores)
    
    def _calculate_recency_score(self, evidence_items: List[EvidenceItem]) -> float:
        """Calculate recency score based on document versions and dates."""
        if not evidence_items:
            return 0.0
        
        # Simple recency calculation (would use actual document dates in real implementation)
        recency_scores = []
        for item in evidence_items:
            # Mock recency based on version number
            try:
                version_parts = item.doc_version.split('.')
                major_version = int(version_parts[0])
                minor_version = int(version_parts[1]) if len(version_parts) > 1 else 0
                
                # Higher versions get higher recency scores
                recency = min((major_version * 0.3 + minor_version * 0.1), 1.0)
                recency_scores.append(recency)
            except (ValueError, IndexError):
                recency_scores.append(0.5)  # Default for unparseable versions
        
        return sum(recency_scores) / len(recency_scores)


class PolicyRetrievalAgent:
    """
    Policy Retrieval Agent implementing UC-OP-06.
    
    Provides vector database integration, semantic search, evidence extraction
    with exact pointers, coverage score calculation, conflict detection, and
    Evidence Pack construction with allowlist filtering and retrieval metrics.
    """
    
    def __init__(self, config: PolicyRetrievalConfig = None):
        self.config = config or PolicyRetrievalConfig()
        
        # Initialize components
        self.vector_db = VectorDatabase(self.config)
        self.evidence_extractor = EvidenceExtractor(self.config)
        self.conflict_detector = ConflictDetector(self.config)
        self.coverage_calculator = CoverageCalculator(self.config)
        
        # Performance metrics
        self.metrics = {
            "total_queries": 0,
            "successful_retrievals": 0,
            "failed_retrievals": 0,
            "average_response_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # Query cache
        self.query_cache = {}
        
        # Initialize vector database
        self.vector_db.initialize()
    
    def retrieve_policy_evidence(
        self,
        state: PolicyValidationState,
        candidate_policy_ids: Optional[List[str]] = None
    ) -> PolicyValidationState:
        """
        Main policy retrieval method.
        
        Retrieves relevant policy evidence for a case and constructs Evidence Pack.
        """
        start_time = time.time()
        case_id = state.case.case_id
        
        logger.info(f"Starting policy retrieval for case {case_id}")
        
        try:
            # Update metrics
            self.metrics["total_queries"] += 1
            
            # Generate retrieval queries from case data
            queries = self._generate_retrieval_queries(state, candidate_policy_ids)
            
            # Perform searches
            all_search_results = []
            for query in queries:
                search_results = self._perform_search(query)
                all_search_results.extend(search_results)
            
            # Apply allowlist filtering
            filtered_results = self._apply_allowlist_filtering(all_search_results)
            
            # Extract evidence items
            evidence_items = self.evidence_extractor.extract_evidence(
                filtered_results, 
                self._get_query_context(state)
            )
            
            # Detect conflicts
            conflicts = self.conflict_detector.detect_conflicts(evidence_items)
            
            # Calculate coverage score
            case_requirements = self._extract_case_requirements(state)
            coverage_score = self.coverage_calculator.calculate_coverage_score(
                evidence_items,
                self._get_query_context(state),
                case_requirements
            )
            
            # Create Evidence Pack
            evidence_pack = EvidencePack(
                case_id=case_id,
                items=evidence_items,
                conflicts=conflicts,
                coverage_score=coverage_score,
                total_items=len(evidence_items),
                verified_items=len([item for item in evidence_items if item.verified]),
                retrieval_metadata={
                    "queries_executed": len(queries),
                    "total_results_found": len(all_search_results),
                    "filtered_results": len(filtered_results),
                    "conflicts_detected": len(conflicts),
                    "retrieval_time_ms": int((time.time() - start_time) * 1000),
                    "allowlist_applied": True,
                    "coverage_threshold_met": coverage_score >= self.config.min_coverage_score
                }
            )
            
            # Update state
            state.evidence_pack = evidence_pack
            
            # Update metrics
            self.metrics["successful_retrievals"] += 1
            self._update_response_time_metric(time.time() - start_time)
            
            logger.info(f"Policy retrieval completed for case {case_id}: "
                       f"{len(evidence_items)} items, coverage={coverage_score:.3f}")
            
            return state
            
        except Exception as e:
            logger.error(f"Policy retrieval failed for case {case_id}: {e}")
            self.metrics["failed_retrievals"] += 1
            
            # Create empty evidence pack on failure
            state.evidence_pack = EvidencePack(
                case_id=case_id,
                items=[],
                conflicts=[],
                coverage_score=0.0,
                total_items=0,
                verified_items=0,
                retrieval_metadata={
                    "error": str(e),
                    "retrieval_time_ms": int((time.time() - start_time) * 1000),
                    "success": False
                }
            )
            
            return state
    
    def _generate_retrieval_queries(
        self, 
        state: PolicyValidationState,
        candidate_policy_ids: Optional[List[str]] = None
    ) -> List[RetrievalQuery]:
        """Generate retrieval queries from case data."""
        queries = []
        
        # Primary query from service description
        service_query = RetrievalQuery(
            query_text=state.case.service,
            query_type="semantic",
            max_results=self.config.max_results_per_query,
            similarity_threshold=self.config.default_similarity_threshold
        )
        queries.append(service_query)
        
        # Additional queries from case metadata
        additional_data = state.case.additional_data or {}
        
        # Query for specific conditions or procedures
        if "diagnosis" in additional_data:
            diagnosis_query = RetrievalQuery(
                query_text=f"coverage for {additional_data['diagnosis']}",
                query_type="semantic",
                max_results=10,
                similarity_threshold=0.75
            )
            queries.append(diagnosis_query)
        
        # Query for provider network requirements
        if "provider_id" in additional_data:
            network_query = RetrievalQuery(
                query_text="network provider requirements coverage",
                query_type="semantic",
                max_results=5,
                similarity_threshold=0.7
            )
            queries.append(network_query)
        
        # Query for prior authorization requirements
        if state.case.priority in ["HIGH", "CRITICAL"]:
            auth_query = RetrievalQuery(
                query_text="prior authorization requirements emergency",
                query_type="semantic",
                max_results=5,
                similarity_threshold=0.7
            )
            queries.append(auth_query)
        
        # Queries based on candidate policy IDs
        if candidate_policy_ids:
            for policy_id in candidate_policy_ids[:3]:  # Limit to top 3
                policy_query = RetrievalQuery(
                    query_text=f"{state.case.service} {policy_id}",
                    query_type="hybrid",
                    document_types=[policy_id],
                    max_results=8,
                    similarity_threshold=0.65
                )
                queries.append(policy_query)
        
        return queries
    
    def _perform_search(self, query: RetrievalQuery) -> List[VectorSearchResult]:
        """Perform search with caching."""
        # Create cache key
        cache_key = self._create_cache_key(query)
        
        # Check cache
        if cache_key in self.query_cache:
            cache_entry = self.query_cache[cache_key]
            if (datetime.utcnow() - cache_entry["timestamp"]).total_seconds() < self.config.cache_ttl_seconds:
                self.metrics["cache_hits"] += 1
                return cache_entry["results"]
        
        # Perform search
        self.metrics["cache_misses"] += 1
        results = self.vector_db.search(query)
        
        # Cache results
        self.query_cache[cache_key] = {
            "results": results,
            "timestamp": datetime.utcnow()
        }
        
        return results
    
    def _apply_allowlist_filtering(self, search_results: List[VectorSearchResult]) -> List[VectorSearchResult]:
        """Apply allowlist filtering to search results."""
        filtered_results = []
        
        for result in search_results:
            # Check if document source is in allowlist
            doc_source = result.metadata.get("source", result.document_id)
            
            # Extract base document identifier
            base_doc_id = doc_source.split("_")[0] + "_" + doc_source.split("_")[1] if "_" in doc_source else doc_source
            
            if any(allowed in doc_source or allowed in base_doc_id for allowed in self.config.allowed_document_sources):
                filtered_results.append(result)
            else:
                logger.warning(f"Document {doc_source} not in allowlist, filtering out")
        
        logger.info(f"Allowlist filtering: {len(search_results)} -> {len(filtered_results)} results")
        return filtered_results
    
    def _get_query_context(self, state: PolicyValidationState) -> str:
        """Get query context from case state."""
        context_parts = [state.case.service]
        
        if state.case.additional_data:
            additional_data = state.case.additional_data
            if "diagnosis" in additional_data:
                context_parts.append(additional_data["diagnosis"])
            if "procedure" in additional_data:
                context_parts.append(additional_data["procedure"])
        
        return " ".join(context_parts)
    
    def _extract_case_requirements(self, state: PolicyValidationState) -> List[str]:
        """Extract case requirements for completeness checking."""
        requirements = []
        
        # Basic requirements
        requirements.append("coverage eligibility")
        requirements.append("benefit determination")
        
        # Service-specific requirements
        service_lower = state.case.service.lower()
        if "emergency" in service_lower:
            requirements.extend(["emergency coverage", "network requirements"])
        if "surgery" in service_lower or "procedure" in service_lower:
            requirements.extend(["prior authorization", "medical necessity"])
        if "specialist" in service_lower:
            requirements.extend(["referral requirements", "specialist network"])
        
        # Priority-based requirements
        if state.case.priority in ["HIGH", "CRITICAL"]:
            requirements.append("expedited processing")
        
        return requirements
    
    def _create_cache_key(self, query: RetrievalQuery) -> str:
        """Create cache key for query."""
        key_data = f"{query.query_text}_{query.query_type}_{query.similarity_threshold}_{query.max_results}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _update_response_time_metric(self, response_time: float) -> None:
        """Update average response time metric."""
        current_avg = self.metrics["average_response_time"]
        total_queries = self.metrics["total_queries"]
        
        # Exponential moving average
        alpha = 0.1
        self.metrics["average_response_time"] = alpha * response_time + (1 - alpha) * current_avg
    
    def get_retrieval_metrics(self) -> Dict[str, Any]:
        """Get retrieval performance metrics."""
        total_queries = self.metrics["total_queries"]
        success_rate = (
            self.metrics["successful_retrievals"] / total_queries 
            if total_queries > 0 else 0.0
        )
        
        cache_total = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        cache_hit_rate = (
            self.metrics["cache_hits"] / cache_total 
            if cache_total > 0 else 0.0
        )
        
        return {
            "total_queries": total_queries,
            "success_rate": success_rate,
            "average_response_time_ms": self.metrics["average_response_time"] * 1000,
            "cache_hit_rate": cache_hit_rate,
            "cache_size": len(self.query_cache),
            "vector_db_status": "connected",  # Would check actual DB status
            "allowlist_sources_count": len(self.config.allowed_document_sources)
        }
    
    def clear_cache(self) -> None:
        """Clear query cache."""
        self.query_cache.clear()
        logger.info("Query cache cleared")
    
    def update_allowlist(self, new_sources: Set[str]) -> None:
        """Update allowlist of document sources."""
        old_count = len(self.config.allowed_document_sources)
        self.config.allowed_document_sources = new_sources
        new_count = len(new_sources)
        
        logger.info(f"Allowlist updated: {old_count} -> {new_count} sources")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check of retrieval agent."""
        return {
            "status": "healthy",
            "vector_db_connected": True,  # Would check actual connection
            "cache_size": len(self.query_cache),
            "metrics": self.get_retrieval_metrics(),
            "config": {
                "similarity_threshold": self.config.default_similarity_threshold,
                "max_results": self.config.max_results_per_query,
                "allowlist_size": len(self.config.allowed_document_sources)
            }
        }


# Factory function for easy instantiation
def create_policy_retrieval_agent(config: PolicyRetrievalConfig = None) -> PolicyRetrievalAgent:
    """Create a policy retrieval agent instance."""
    return PolicyRetrievalAgent(config)
