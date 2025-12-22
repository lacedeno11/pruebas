"""
Policy Retrieval Agent (UC-OP-06) for Policy Validation Copilot

This module implements the rag_agent function that performs Retrieval-Augmented
Generation (RAG) for policy document retrieval. It implements:

- Semantic query construction from case data
- Vector similarity search against knowledge base
- Filtering by vigencia (validity) and allowlist sources
- Fragment and table extraction with exact pointers
- Coverage score calculation and evidence quality assessment
- Conflict detection between retrieved evidence
- State updates with evidence pack and scores

The agent ensures only verified, current policy documents are used for
validation while maintaining complete audit trails and evidence anchoring.
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

import numpy as np
from sentence_transformers import SentenceTransformer

from src.schemas.state import (
    PolicyValidationState,
    EvidenceItem,
    EvidenceScores,
    EvidenceConflict,
    EvidencePack,
    update_state_audit
)

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration and Constants
# ============================================================================

# Vector search configuration
VECTOR_CONFIG = {
    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
    "embedding_dimension": 384,
    "similarity_threshold": 0.7,
    "max_results": 50,
    "chunk_size": 512,
    "chunk_overlap": 50
}

# Coverage scoring weights
COVERAGE_WEIGHTS = {
    "relevance": 0.4,
    "completeness": 0.3,
    "recency": 0.2,
    "authority": 0.1
}

# Source allowlist configuration
ALLOWLIST_SOURCES = {
    "policy_documents": {
        "prefix": "POL_",
        "required_fields": ["doc_id", "version", "vigencia_start", "vigencia_end", "checksum"],
        "authority_levels": ["official", "approved", "draft"]
    },
    "exception_rules": {
        "prefix": "EXC_",
        "required_fields": ["rule_id", "version", "scope", "effective_date", "expiry_date"],
        "authority_levels": ["active", "pending", "superseded"]
    },
    "regulatory_updates": {
        "prefix": "REG_",
        "required_fields": ["regulation_id", "version", "publication_date", "effective_date"],
        "authority_levels": ["published", "draft", "withdrawn"]
    }
}

# Conflict detection patterns
CONFLICT_PATTERNS = {
    "contradiction": [
        r"(no|not|never|prohibit|forbid|deny).*(allow|permit|approve|accept)",
        r"(allow|permit|approve|accept).*(no|not|never|prohibit|forbid|deny)",
        r"(mandatory|required|must).*(optional|may|can)",
        r"(optional|may|can).*(mandatory|required|must)"
    ],
    "version_mismatch": [
        r"version\s+(\d+\.\d+)",
        r"v(\d+\.\d+)",
        r"revision\s+(\d+)"
    ],
    "scope_overlap": [
        r"applies to.*(all|any|every)",
        r"except.*(specific|particular|certain)",
        r"limited to.*(scope|range|area)"
    ]
}


# ============================================================================
# Mock Knowledge Base (Production: Replace with Vector Database)
# ============================================================================

class MockKnowledgeBase:
    """Mock knowledge base for policy documents and rules."""
    
    def __init__(self):
        self.documents = self._create_mock_documents()
        self.embeddings = {}
        self.model = None
    
    def _create_mock_documents(self) -> List[Dict[str, Any]]:
        """Create mock policy documents for testing."""
        return [
            {
                "doc_id": "POL_001",
                "version": "v2.1.0",
                "title": "General Medical Services Coverage Policy",
                "content": "This policy covers standard medical services including consultations, diagnostics, and basic treatments. Coverage applies to in-network providers with valid contracts. Pre-authorization required for procedures exceeding $5,000.",
                "vigencia_start": "2024-01-01T00:00:00Z",
                "vigencia_end": "2024-12-31T23:59:59Z",
                "checksum": "abc123def456",
                "source_type": "policy_documents",
                "authority_level": "official",
                "tags": ["medical", "coverage", "general"],
                "fragments": [
                    {
                        "fragment_id": "POL_001_F1",
                        "content": "Coverage applies to in-network providers with valid contracts.",
                        "pointer": "page:1,section:2.1,line:15-17",
                        "table_ref": None
                    },
                    {
                        "fragment_id": "POL_001_F2", 
                        "content": "Pre-authorization required for procedures exceeding $5,000.",
                        "pointer": "page:2,section:3.2,line:8-10",
                        "table_ref": "Table_3.2_Authorization_Limits"
                    }
                ]
            },
            {
                "doc_id": "POL_002",
                "version": "v1.5.2",
                "title": "Specialist Referral Requirements",
                "content": "Specialist referrals require primary care physician approval. Emergency cases exempt from referral requirements. Specialist must be in-network unless no in-network specialist available within 50 miles.",
                "vigencia_start": "2024-01-15T00:00:00Z",
                "vigencia_end": "2024-12-31T23:59:59Z",
                "checksum": "def456ghi789",
                "source_type": "policy_documents",
                "authority_level": "official",
                "tags": ["specialist", "referral", "network"],
                "fragments": [
                    {
                        "fragment_id": "POL_002_F1",
                        "content": "Specialist referrals require primary care physician approval.",
                        "pointer": "page:1,section:1.1,line:5-7",
                        "table_ref": None
                    },
                    {
                        "fragment_id": "POL_002_F2",
                        "content": "Emergency cases exempt from referral requirements.",
                        "pointer": "page:1,section:1.2,line:12-14",
                        "table_ref": None
                    }
                ]
            },
            {
                "doc_id": "EXC_001",
                "version": "v1.0.0",
                "title": "COVID-19 Emergency Exception Rules",
                "content": "During COVID-19 emergency period, telehealth services covered at same rate as in-person visits. Prior authorization waived for COVID-19 related treatments. Out-of-network providers covered for COVID-19 care when in-network unavailable.",
                "vigencia_start": "2024-01-01T00:00:00Z",
                "vigencia_end": "2024-06-30T23:59:59Z",
                "checksum": "ghi789jkl012",
                "source_type": "exception_rules",
                "authority_level": "active",
                "tags": ["covid", "emergency", "telehealth"],
                "fragments": [
                    {
                        "fragment_id": "EXC_001_F1",
                        "content": "Telehealth services covered at same rate as in-person visits.",
                        "pointer": "page:1,section:2.1,line:3-5",
                        "table_ref": "Table_2.1_Telehealth_Rates"
                    }
                ]
            },
            {
                "doc_id": "POL_003",
                "version": "v1.0.0",
                "title": "Dental Services Coverage Policy",
                "content": "Dental services covered include preventive care, basic restorative, and emergency treatments. Orthodontic services require pre-authorization. Annual maximum benefit of $2,000 per member.",
                "vigencia_start": "2024-02-01T00:00:00Z",
                "vigencia_end": "2024-12-31T23:59:59Z",
                "checksum": "jkl012mno345",
                "source_type": "policy_documents",
                "authority_level": "official",
                "tags": ["dental", "preventive", "orthodontic"],
                "fragments": [
                    {
                        "fragment_id": "POL_003_F1",
                        "content": "Annual maximum benefit of $2,000 per member.",
                        "pointer": "page:2,section:4.1,line:20-22",
                        "table_ref": "Table_4.1_Benefit_Limits"
                    }
                ]
            }
        ]
    
    def get_embedding_model(self):
        """Get or initialize the embedding model."""
        if self.model is None:
            self.model = SentenceTransformer(VECTOR_CONFIG["model_name"])
        return self.model
    
    def search_similar_documents(
        self,
        query_embedding: np.ndarray,
        filters: Dict[str, Any],
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity.
        
        Args:
            query_embedding: Query vector embedding
            filters: Search filters (vigencia, source_type, etc.)
            max_results: Maximum number of results
            
        Returns:
            List[Dict[str, Any]]: Matching documents with similarity scores
        """
        model = self.get_embedding_model()
        results = []
        
        for doc in self.documents:
            # Apply filters
            if not self._apply_filters(doc, filters):
                continue
            
            # Calculate similarity for document content
            doc_embedding = model.encode(doc["content"])
            similarity = np.dot(query_embedding, doc_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
            )
            
            if similarity >= VECTOR_CONFIG["similarity_threshold"]:
                doc_result = doc.copy()
                doc_result["similarity_score"] = float(similarity)
                results.append(doc_result)
        
        # Sort by similarity and return top results
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:max_results]
    
    def _apply_filters(self, doc: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Apply search filters to document."""
        # Check vigencia (validity period)
        if "current_date" in filters:
            current_date = datetime.fromisoformat(filters["current_date"].replace("Z", "+00:00"))
            vigencia_start = datetime.fromisoformat(doc["vigencia_start"].replace("Z", "+00:00"))
            vigencia_end = datetime.fromisoformat(doc["vigencia_end"].replace("Z", "+00:00"))
            
            if not (vigencia_start <= current_date <= vigencia_end):
                return False
        
        # Check source type allowlist
        if "allowed_sources" in filters:
            if doc["source_type"] not in filters["allowed_sources"]:
                return False
        
        # Check authority level
        if "min_authority" in filters:
            authority_levels = ["draft", "pending", "approved", "official", "active"]
            doc_level = authority_levels.index(doc["authority_level"])
            min_level = authority_levels.index(filters["min_authority"])
            if doc_level < min_level:
                return False
        
        # Check tags
        if "required_tags" in filters:
            doc_tags = set(doc.get("tags", []))
            required_tags = set(filters["required_tags"])
            if not required_tags.intersection(doc_tags):
                return False
        
        return True


# Global knowledge base instance
knowledge_base = MockKnowledgeBase()


# ============================================================================
# Query Construction
# ============================================================================

def construct_semantic_query(state: PolicyValidationState) -> str:
    """
    Construct semantic search query from case data and ML insights.
    
    Args:
        state: Current PolicyValidationState
        
    Returns:
        str: Semantic search query
    """
    case = state["case"]
    ml = state["ml"]
    
    # Base query components
    query_parts = []
    
    # Service-specific terms
    service_code = case.service_code
    if service_code.startswith("MED"):
        query_parts.append("medical services coverage")
    elif service_code.startswith("DEN"):
        query_parts.append("dental services coverage")
    elif service_code.startswith("SRV"):
        query_parts.append("specialist services")
    
    # Provider and network terms
    query_parts.append(f"provider {case.provider_id}")
    query_parts.append("network coverage")
    
    # Priority and urgency terms
    if case.priority.value == "HIGH":
        query_parts.append("emergency urgent care")
    
    # ML classification insights
    if ml.classification:
        if ml.classification.route == "specialist":
            query_parts.append("specialist referral requirements")
        elif ml.classification.route == "fraud":
            query_parts.append("fraud prevention validation")
        
        # Add candidate policy IDs as search terms
        for policy_id in ml.classification.candidate_policy_ids:
            query_parts.append(f"policy {policy_id}")
    
    # Anomaly insights
    if ml.anomaly and ml.anomaly.anomaly_flags:
        for flag in ml.anomaly.anomaly_flags:
            if "timing" in flag:
                query_parts.append("service timing requirements")
            elif "frequency" in flag:
                query_parts.append("frequency limitations")
    
    # Insurer-specific terms
    query_parts.append(f"insurer {case.insurer_id}")
    query_parts.append(f"plan {case.plan_id}")
    
    # Construct final query
    query = " ".join(query_parts)
    
    # Add context for better semantic matching
    context_query = f"""
    Case involves {service_code} service provided by {case.provider_id} 
    for insurer {case.insurer_id} plan {case.plan_id}. 
    Priority: {case.priority.value}. 
    Need coverage policies, authorization requirements, and validation rules.
    {query}
    """
    
    return context_query.strip()


def extract_search_filters(state: PolicyValidationState) -> Dict[str, Any]:
    """
    Extract search filters from case data for allowlist validation.
    
    Args:
        state: Current PolicyValidationState
        
    Returns:
        Dict[str, Any]: Search filters
    """
    case = state["case"]
    
    # Current date for vigencia filtering
    current_date = datetime.utcnow()
    
    # Determine allowed source types based on case characteristics
    allowed_sources = ["policy_documents"]
    
    # Add exception rules if case has special characteristics
    if case.priority.value == "HIGH":
        allowed_sources.append("exception_rules")
    
    # Add regulatory updates for compliance-sensitive cases
    if case.service_code.startswith("REG"):
        allowed_sources.append("regulatory_updates")
    
    # Determine required tags based on service code
    required_tags = []
    if case.service_code.startswith("MED"):
        required_tags.extend(["medical", "coverage"])
    elif case.service_code.startswith("DEN"):
        required_tags.extend(["dental"])
    elif case.service_code.startswith("SRV"):
        required_tags.extend(["specialist"])
    
    return {
        "current_date": current_date.isoformat(),
        "allowed_sources": allowed_sources,
        "min_authority": "approved",
        "required_tags": required_tags,
        "insurer_id": case.insurer_id,
        "plan_id": case.plan_id
    }


# ============================================================================
# Evidence Processing
# ============================================================================

def extract_evidence_fragments(
    documents: List[Dict[str, Any]],
    query: str
) -> List[Dict[str, Any]]:
    """
    Extract relevant fragments from retrieved documents.
    
    Args:
        documents: Retrieved documents
        query: Original search query
        
    Returns:
        List[Dict[str, Any]]: Extracted fragments with metadata
    """
    fragments = []
    
    for doc in documents:
        doc_fragments = doc.get("fragments", [])
        
        for fragment in doc_fragments:
            # Calculate fragment relevance to query
            relevance_score = calculate_fragment_relevance(
                fragment["content"],
                query
            )
            
            if relevance_score >= 0.5:  # Relevance threshold
                fragment_data = {
                    "doc_id": doc["doc_id"],
                    "version": doc["version"],
                    "checksum": doc["checksum"],
                    "fragment_id": fragment["fragment_id"],
                    "content": fragment["content"],
                    "pointer": fragment["pointer"],
                    "table_ref": fragment.get("table_ref"),
                    "relevance_score": relevance_score,
                    "doc_similarity": doc["similarity_score"],
                    "source_type": doc["source_type"],
                    "authority_level": doc["authority_level"],
                    "vigencia_start": doc["vigencia_start"],
                    "vigencia_end": doc["vigencia_end"]
                }
                fragments.append(fragment_data)
    
    return fragments


def calculate_fragment_relevance(fragment_content: str, query: str) -> float:
    """
    Calculate relevance score between fragment and query.
    
    Args:
        fragment_content: Fragment text content
        query: Search query
        
    Returns:
        float: Relevance score (0-1)
    """
    # Simple keyword-based relevance (production: use semantic similarity)
    query_terms = set(query.lower().split())
    fragment_terms = set(fragment_content.lower().split())
    
    # Calculate Jaccard similarity
    intersection = query_terms.intersection(fragment_terms)
    union = query_terms.union(fragment_terms)
    
    if not union:
        return 0.0
    
    jaccard_score = len(intersection) / len(union)
    
    # Boost score for exact phrase matches
    phrase_boost = 0.0
    query_phrases = [phrase.strip() for phrase in query.split(",")]
    for phrase in query_phrases:
        if phrase.lower() in fragment_content.lower():
            phrase_boost += 0.2
    
    return min(1.0, jaccard_score + phrase_boost)


def calculate_evidence_scores(fragment_data: Dict[str, Any]) -> EvidenceScores:
    """
    Calculate comprehensive evidence scores.
    
    Args:
        fragment_data: Fragment metadata
        
    Returns:
        EvidenceScores: Calculated scores
    """
    # Relevance score (from fragment matching)
    relevance_score = fragment_data["relevance_score"]
    
    # Quality score (based on source authority and completeness)
    authority_weights = {
        "draft": 0.3,
        "pending": 0.5,
        "approved": 0.8,
        "official": 1.0,
        "active": 1.0
    }
    authority_score = authority_weights.get(fragment_data["authority_level"], 0.5)
    
    # Completeness score (based on pointer specificity and table references)
    completeness_score = 0.7  # Base score
    if fragment_data.get("table_ref"):
        completeness_score += 0.2  # Bonus for table references
    if "line:" in fragment_data.get("pointer", ""):
        completeness_score += 0.1  # Bonus for line-level pointers
    
    quality_score = (authority_score + completeness_score) / 2
    
    # Confidence score (combination of relevance and quality)
    confidence_score = (relevance_score * 0.6 + quality_score * 0.4)
    
    # Coverage score (based on document similarity and fragment relevance)
    coverage_score = (fragment_data["doc_similarity"] * 0.4 + relevance_score * 0.6)
    
    return EvidenceScores(
        relevance_score=relevance_score,
        quality_score=min(1.0, quality_score),
        confidence_score=confidence_score,
        coverage_score=coverage_score
    )


def create_evidence_items(fragments: List[Dict[str, Any]]) -> List[EvidenceItem]:
    """
    Create EvidenceItem objects from processed fragments.
    
    Args:
        fragments: Processed fragment data
        
    Returns:
        List[EvidenceItem]: Evidence items
    """
    evidence_items = []
    
    for fragment in fragments:
        scores = calculate_evidence_scores(fragment)
        
        evidence_item = EvidenceItem(
            evidence_id=str(uuid4()),
            doc_id=fragment["doc_id"],
            version=fragment["version"],
            checksum=fragment["checksum"],
            pointer=fragment["pointer"],
            excerpt=fragment["content"],
            table_ref=fragment.get("table_ref"),
            scores=scores,
            extracted_at=datetime.utcnow(),
            source_type=fragment["source_type"]
        )
        
        evidence_items.append(evidence_item)
    
    return evidence_items


# ============================================================================
# Conflict Detection
# ============================================================================

def detect_evidence_conflicts(evidence_items: List[EvidenceItem]) -> List[EvidenceConflict]:
    """
    Detect conflicts between evidence items.
    
    Args:
        evidence_items: List of evidence items
        
    Returns:
        List[EvidenceConflict]: Detected conflicts
    """
    conflicts = []
    
    # Check for contradictions
    contradiction_conflicts = detect_contradictions(evidence_items)
    conflicts.extend(contradiction_conflicts)
    
    # Check for version mismatches
    version_conflicts = detect_version_conflicts(evidence_items)
    conflicts.extend(version_conflicts)
    
    # Check for scope overlaps
    scope_conflicts = detect_scope_conflicts(evidence_items)
    conflicts.extend(scope_conflicts)
    
    return conflicts


def detect_contradictions(evidence_items: List[EvidenceItem]) -> List[EvidenceConflict]:
    """Detect contradictory statements in evidence."""
    conflicts = []
    
    for i, item1 in enumerate(evidence_items):
        for j, item2 in enumerate(evidence_items[i+1:], i+1):
            # Check for contradiction patterns
            for pattern in CONFLICT_PATTERNS["contradiction"]:
                if (re.search(pattern, item1.excerpt.lower()) and 
                    re.search(pattern, item2.excerpt.lower())):
                    
                    conflict = EvidenceConflict(
                        evidence_ids=[item1.evidence_id, item2.evidence_id],
                        conflict_type="contradiction",
                        description=f"Contradictory statements detected between {item1.doc_id} and {item2.doc_id}",
                        severity="high"
                    )
                    conflicts.append(conflict)
    
    return conflicts


def detect_version_conflicts(evidence_items: List[EvidenceItem]) -> List[EvidenceConflict]:
    """Detect version conflicts in evidence."""
    conflicts = []
    doc_versions = {}
    
    # Group by document ID
    for item in evidence_items:
        if item.doc_id not in doc_versions:
            doc_versions[item.doc_id] = []
        doc_versions[item.doc_id].append(item)
    
    # Check for multiple versions of same document
    for doc_id, items in doc_versions.items():
        versions = set(item.version for item in items)
        if len(versions) > 1:
            conflict = EvidenceConflict(
                evidence_ids=[item.evidence_id for item in items],
                conflict_type="version_mismatch",
                description=f"Multiple versions found for document {doc_id}: {', '.join(versions)}",
                severity="medium"
            )
            conflicts.append(conflict)
    
    return conflicts


def detect_scope_conflicts(evidence_items: List[EvidenceItem]) -> List[EvidenceConflict]:
    """Detect scope overlap conflicts in evidence."""
    conflicts = []
    
    # Simple scope conflict detection based on content analysis
    scope_items = []
    for item in evidence_items:
        for pattern in CONFLICT_PATTERNS["scope_overlap"]:
            if re.search(pattern, item.excerpt.lower()):
                scope_items.append(item)
                break
    
    # Check for overlapping scopes
    if len(scope_items) > 1:
        conflict = EvidenceConflict(
            evidence_ids=[item.evidence_id for item in scope_items],
            conflict_type="scope_overlap",
            description="Potentially overlapping policy scopes detected",
            severity="low"
        )
        conflicts.append(conflict)
    
    return conflicts


# ============================================================================
# Coverage Calculation
# ============================================================================

def calculate_coverage_score(
    evidence_items: List[EvidenceItem],
    query: str,
    case_data: Dict[str, Any]
) -> float:
    """
    Calculate overall coverage score for retrieved evidence.
    
    Args:
        evidence_items: Retrieved evidence items
        query: Original search query
        case_data: Case information
        
    Returns:
        float: Coverage score (0-1)
    """
    if not evidence_items:
        return 0.0
    
    # Calculate component scores
    relevance_score = np.mean([item.scores.relevance_score for item in evidence_items])
    quality_score = np.mean([item.scores.quality_score for item in evidence_items])
    
    # Completeness score based on coverage of key case aspects
    completeness_score = calculate_completeness_score(evidence_items, case_data)
    
    # Recency score based on document currency
    recency_score = calculate_recency_score(evidence_items)
    
    # Weighted combination
    coverage_score = (
        COVERAGE_WEIGHTS["relevance"] * relevance_score +
        COVERAGE_WEIGHTS["completeness"] * completeness_score +
        COVERAGE_WEIGHTS["recency"] * recency_score +
        COVERAGE_WEIGHTS["authority"] * quality_score
    )
    
    return min(1.0, coverage_score)


def calculate_completeness_score(
    evidence_items: List[EvidenceItem],
    case_data: Dict[str, Any]
) -> float:
    """Calculate completeness score based on case coverage."""
    # Key aspects that should be covered
    key_aspects = [
        "coverage",
        "authorization",
        "network",
        "provider",
        "service",
        "benefit"
    ]
    
    covered_aspects = set()
    for item in evidence_items:
        content_lower = item.excerpt.lower()
        for aspect in key_aspects:
            if aspect in content_lower:
                covered_aspects.add(aspect)
    
    return len(covered_aspects) / len(key_aspects)


def calculate_recency_score(evidence_items: List[EvidenceItem]) -> float:
    """Calculate recency score based on document currency."""
    if not evidence_items:
        return 0.0
    
    current_date = datetime.utcnow()
    recency_scores = []
    
    for item in evidence_items:
        # Calculate days since extraction
        days_old = (current_date - item.extracted_at).days
        
        # Recency score decreases with age
        if days_old <= 30:
            recency_score = 1.0
        elif days_old <= 90:
            recency_score = 0.8
        elif days_old <= 180:
            recency_score = 0.6
        else:
            recency_score = 0.4
        
        recency_scores.append(recency_score)
    
    return np.mean(recency_scores)


# ============================================================================
# Main RAG Agent Function
# ============================================================================

async def rag_agent(state: PolicyValidationState) -> PolicyValidationState:
    """
    Policy Retrieval Agent (UC-OP-06) - RAG-based evidence retrieval.
    
    Implements:
    - Semantic query construction from case data and ML insights
    - Vector similarity search against knowledge base
    - Filtering by vigencia and allowlist sources
    - Fragment and table extraction with exact pointers
    - Coverage score calculation and evidence quality assessment
    - Conflict detection between retrieved evidence
    - State updates with evidence pack and scores
    
    Args:
        state: Current PolicyValidationState
        
    Returns:
        PolicyValidationState: Updated state with evidence pack
    """
    start_time = datetime.utcnow()
    node_name = "policy_retrieval"
    
    # Update audit trail - node started
    state = update_state_audit(
        state,
        node_name=node_name,
        status="started",
        input_hash=str(hash(str(state["case"])))
    )
    
    try:
        logger.info(f"Starting policy retrieval for case {state['case'].case_id}")
        
        # Step 1: Construct semantic search query
        query = construct_semantic_query(state)
        logger.info(f"Constructed query: {query[:100]}...")
        
        # Step 2: Extract search filters for allowlist validation
        filters = extract_search_filters(state)
        logger.info(f"Applied filters: {filters}")
        
        # Step 3: Perform vector similarity search
        model = knowledge_base.get_embedding_model()
        query_embedding = model.encode(query)
        
        documents = knowledge_base.search_similar_documents(
            query_embedding,
            filters,
            max_results=VECTOR_CONFIG["max_results"]
        )
        
        logger.info(f"Retrieved {len(documents)} documents")
        
        # Step 4: Extract relevant fragments with pointers
        fragments = extract_evidence_fragments(documents, query)
        logger.info(f"Extracted {len(fragments)} relevant fragments")
        
        # Step 5: Create evidence items with scores
        evidence_items = create_evidence_items(fragments)
        logger.info(f"Created {len(evidence_items)} evidence items")
        
        # Step 6: Detect conflicts between evidence
        conflicts = detect_evidence_conflicts(evidence_items)
        if conflicts:
            logger.warning(f"Detected {len(conflicts)} evidence conflicts")
        
        # Step 7: Calculate overall coverage score
        coverage_score = calculate_coverage_score(
            evidence_items,
            query,
            state["case"].dict()
        )
        logger.info(f"Calculated coverage score: {coverage_score:.3f}")
        
        # Step 8: Create evidence pack
        evidence_pack = EvidencePack(
            items=evidence_items,
            coverage_score=coverage_score,
            conflicts=conflicts,
            last_updated=datetime.utcnow()
        )
        
        # Step 9: Update state with evidence pack
        state["evidence_pack"] = evidence_pack
        
        # Step 10: Update audit timestamps
        state["audit"].timestamps.evidence_collected = datetime.utcnow()
        
        # Step 11: Add detailed audit information
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        state = update_state_audit(
            state,
            node_name=node_name,
            status="completed",
            input_hash=str(hash(query)),
            output_hash=str(hash(str(evidence_pack.dict()))),
            execution_time_ms=execution_time_ms
        )
        
        # Add data lineage information
        state["audit"].data_lineage[node_name] = {
            "query_constructed": query[:200] + "..." if len(query) > 200 else query,
            "documents_retrieved": len(documents),
            "fragments_extracted": len(fragments),
            "evidence_items_created": len(evidence_items),
            "conflicts_detected": len(conflicts),
            "coverage_score": coverage_score,
            "filters_applied": filters,
            "search_config": VECTOR_CONFIG
        }
        
        logger.info(f"Policy retrieval completed for case {state['case'].case_id}")
        logger.info(f"Evidence items: {len(evidence_items)}, Coverage: {coverage_score:.3f}, Conflicts: {len(conflicts)}")
        
        return state
        
    except Exception as e:
        # Update audit trail - node failed
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        state = update_state_audit(
            state,
            node_name=node_name,
            status="failed",
            input_hash=str(hash(str(state["case"]))),
            error_message=str(e),
            execution_time_ms=execution_time_ms
        )
        
        logger.error(f"Policy retrieval failed for case {state['case'].case_id}: {str(e)}")
        
        # Create empty evidence pack to allow workflow to continue
        state["evidence_pack"] = EvidencePack()
        
        # Log failure in compliance flags
        state["audit"].compliance_flags.append(f"EVIDENCE_RETRIEVAL_FAILED_{node_name}")
        
        raise


# ============================================================================
# Utility Functions for Testing and Monitoring
# ============================================================================

def get_knowledge_base_stats() -> Dict[str, Any]:
    """Get knowledge base statistics."""
    return {
        "total_documents": len(knowledge_base.documents),
        "source_types": list(set(doc["source_type"] for doc in knowledge_base.documents)),
        "authority_levels": list(set(doc["authority_level"] for doc in knowledge_base.documents)),
        "vector_config": VECTOR_CONFIG,
        "coverage_weights": COVERAGE_WEIGHTS
    }


def validate_evidence_quality(evidence_items: List[EvidenceItem]) -> List[str]:
    """
    Validate evidence quality and completeness.
    
    Args:
        evidence_items: Evidence items to validate
        
    Returns:
        List[str]: Quality issues found
    """
    issues = []
    
    for item in evidence_items:
        # Check for required fields
        if not item.pointer:
            issues.append(f"Evidence {item.evidence_id} missing pointer")
        
        if not item.checksum:
            issues.append(f"Evidence {item.evidence_id} missing checksum")
        
        # Check score validity
        if item.scores.relevance_score < 0.3:
            issues.append(f"Evidence {item.evidence_id} has low relevance score")
        
        if item.scores.quality_score < 0.5:
            issues.append(f"Evidence {item.evidence_id} has low quality score")
        
        # Check excerpt length
        if len(item.excerpt) < 20:
            issues.append(f"Evidence {item.evidence_id} has very short excerpt")
    
    return issues


def create_mock_evidence_pack(case_id: str) -> EvidencePack:
    """
    Create mock evidence pack for testing.
    
    Args:
        case_id: Case identifier
        
    Returns:
        EvidencePack: Mock evidence pack
    """
    # Create mock evidence items
    evidence_items = [
        EvidenceItem(
            evidence_id=str(uuid4()),
            doc_id="POL_001",
            version="v2.1.0",
            checksum="abc123def456",
            pointer="page:1,section:2.1,line:15-17",
            excerpt="Coverage applies to in-network providers with valid contracts.",
            scores=EvidenceScores(
                relevance_score=0.85,
                quality_score=0.90,
                confidence_score=0.87,
                coverage_score=0.82
            ),
            source_type="policy_documents"
        ),
        EvidenceItem(
            evidence_id=str(uuid4()),
            doc_id="POL_002",
            version="v1.5.2",
            checksum="def456ghi789",
            pointer="page:1,section:1.1,line:5-7",
            excerpt="Specialist referrals require primary care physician approval.",
            scores=EvidenceScores(
                relevance_score=0.78,
                quality_score=0.85,
                confidence_score=0.81,
                coverage_score=0.79
            ),
            source_type="policy_documents"
        )
    ]
    
    return EvidencePack(
        items=evidence_items,
        coverage_score=0.80,
        conflicts=[],
        last_updated=datetime.utcnow()
    )
