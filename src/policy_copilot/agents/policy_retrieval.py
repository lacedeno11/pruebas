"""
Policy Retrieval Agent (UC-OP-06)

This module implements the Policy Retrieval Agent for the Policy Validation Copilot system,
providing RAG (Retrieval-Augmented Generation) functionality for evidence pack construction,
document version validation, coverage score calculation, and conflict detection.
"""

from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
import logging
import asyncio
import hashlib
import re
from dataclasses import dataclass

from ..state import PolicyValidationState, EvidencePack, EvidenceItem
from ..database import (
    PolicyRepository, PolicyExceptionRepository, EvidencePackRepository,
    EvidenceItemRepository, get_repository_factory
)
from ..guardrails import SourceAllowlistGuardrail, create_security_context
from ..ml_services import MLClassificationService, get_classification_service

logger = logging.getLogger(__name__)


@dataclass
class RetrievalQuery:
    """Query structure for policy retrieval"""
    case_id: str
    service_code: str
    insurer_id: str
    plan_id: str
    customer_attributes: Dict[str, Any]
    service_attributes: Dict[str, Any]
    query_text: str
    max_results: int = 10
    min_relevance_score: float = 0.6


@dataclass
class DocumentReference:
    """Document reference with metadata"""
    doc_id: str
    version: str
    title: str
    content: str
    checksum: str
    source_url: str
    last_updated: datetime
    policy_type: str
    category: str
    tags: List[str]


@dataclass
class RetrievalResult:
    """Individual retrieval result"""
    document: DocumentReference
    relevance_score: float
    confidence_score: float
    excerpt: str
    pointer: str
    table_ref: Optional[str] = None
    conflict_indicators: List[str] = None


class PolicyRetrievalAgent:
    """
    Policy Retrieval Agent implementing UC-OP-06.
    
    Provides RAG functionality for retrieving relevant policy documents,
    constructing evidence packs, validating document versions, calculating
    coverage scores, and detecting conflicts.
    """
    
    def __init__(
        self,
        vector_store_client=None,
        knowledge_base_client=None,
        classification_service: MLClassificationService = None,
        use_mock: bool = False
    ):
        self.vector_store_client = vector_store_client
        self.knowledge_base_client = knowledge_base_client
        self.classification_service = classification_service or get_classification_service(use_mock)
        self.source_allowlist = SourceAllowlistGuardrail()
        
        # Repository factory for database access
        self.repo_factory = get_repository_factory()
        
        # Configuration
        self.max_retrieval_results = 20
        self.min_coverage_threshold = 0.8
        self.conflict_detection_enabled = True
        self.version_validation_enabled = True
        
        # Caching for performance
        self._document_cache = {}
        self._policy_cache = {}
        
    async def retrieve_evidence(
        self, 
        state: PolicyValidationState,
        query: RetrievalQuery = None
    ) -> PolicyValidationState:
        """
        Main entry point for policy retrieval and evidence pack construction.
        
        Args:
            state: Current policy validation state
            query: Optional custom retrieval query
            
        Returns:
            Updated state with evidence pack
        """
        start_time = datetime.utcnow()
        
        try:
            # Extract case information
            case = state["case"]
            case_id = case["case_id"]
            
            logger.info(f"Starting policy retrieval for case {case_id}")
            
            # Build retrieval query if not provided
            if not query:
                query = await self._build_retrieval_query(case)
            
            # Perform ML classification for intelligent routing
            ml_classification = await self._get_ml_classification(case)
            
            # Retrieve relevant documents using RAG
            retrieval_results = await self._retrieve_documents(query, ml_classification)
            
            # Validate document versions and allowlist compliance
            validated_results = await self._validate_documents(retrieval_results)
            
            # Apply policy exceptions (RB-03)
            exception_filtered_results = await self._apply_policy_exceptions(
                validated_results, case
            )
            
            # Detect conflicts between documents
            conflict_analysis = await self._detect_conflicts(exception_filtered_results)
            
            # Calculate coverage score
            coverage_score = await self._calculate_coverage_score(
                exception_filtered_results, query
            )
            
            # Construct evidence pack
            evidence_pack = await self._construct_evidence_pack(
                case_id,
                exception_filtered_results,
                coverage_score,
                conflict_analysis
            )
            
            # Update state
            state["evidence_pack"] = evidence_pack
            
            # Log retrieval metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            await self._log_retrieval_metrics(
                case_id, len(retrieval_results), len(validated_results),
                coverage_score, processing_time
            )
            
            logger.info(
                f"Policy retrieval completed for case {case_id}: "
                f"{len(validated_results)} documents, coverage: {coverage_score:.3f}"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"Policy retrieval failed for case {case.get('case_id', 'unknown')}: {e}")
            
            # Create empty evidence pack on failure
            state["evidence_pack"] = {
                "items": [],
                "coverage_score": 0.0,
                "conflicts_detected": False,
                "missing_sources": [],
                "retrieval_method": "FAILED",
                "retrieval_timestamp": datetime.utcnow(),
                "retrieval_duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000)
            }
            
            raise
    
    async def _build_retrieval_query(self, case: Dict[str, Any]) -> RetrievalQuery:
        """Build retrieval query from case information"""
        
        # Extract service information
        service_code = case.get("service_code", "")
        insurer_id = case.get("insurer_id", "")
        plan_id = case.get("plan_id", "")
        
        # Build customer attributes
        customer_attributes = {
            "customer_id": case.get("customer_id"),
            "age_group": self._calculate_age_group(case.get("customer_age")),
            "plan_type": plan_id,
            "coverage_level": self._extract_coverage_level(plan_id)
        }
        
        # Build service attributes
        service_attributes = {
            "service_code": service_code,
            "service_amount": case.get("service_amount", 0.0),
            "provider_type": case.get("provider_type"),
            "urgency": case.get("service_urgency", "NORMAL"),
            "diagnosis_codes": case.get("diagnosis_codes", []),
            "procedure_codes": case.get("procedure_codes", [])
        }
        
        # Build query text
        query_text = self._build_query_text(service_code, service_attributes)
        
        return RetrievalQuery(
            case_id=case["case_id"],
            service_code=service_code,
            insurer_id=insurer_id,
            plan_id=plan_id,
            customer_attributes=customer_attributes,
            service_attributes=service_attributes,
            query_text=query_text,
            max_results=self.max_retrieval_results
        )
    
    def _calculate_age_group(self, age: Optional[int]) -> str:
        """Calculate age group from age"""
        if not age:
            return "UNKNOWN"
        
        if age < 18:
            return "MINOR"
        elif age < 65:
            return "ADULT"
        else:
            return "SENIOR"
    
    def _extract_coverage_level(self, plan_id: str) -> str:
        """Extract coverage level from plan ID"""
        if not plan_id:
            return "UNKNOWN"
        
        plan_lower = plan_id.lower()
        if "basic" in plan_lower:
            return "BASIC"
        elif "premium" in plan_lower or "plus" in plan_lower:
            return "PREMIUM"
        elif "standard" in plan_lower:
            return "STANDARD"
        else:
            return "UNKNOWN"
    
    def _build_query_text(self, service_code: str, service_attributes: Dict[str, Any]) -> str:
        """Build natural language query text"""
        query_parts = []
        
        # Add service code
        if service_code:
            query_parts.append(f"service code {service_code}")
        
        # Add diagnosis codes
        diagnosis_codes = service_attributes.get("diagnosis_codes", [])
        if diagnosis_codes:
            query_parts.append(f"diagnosis {' '.join(diagnosis_codes[:3])}")
        
        # Add procedure codes
        procedure_codes = service_attributes.get("procedure_codes", [])
        if procedure_codes:
            query_parts.append(f"procedure {' '.join(procedure_codes[:3])}")
        
        # Add provider type
        provider_type = service_attributes.get("provider_type")
        if provider_type:
            query_parts.append(f"provider {provider_type}")
        
        # Add urgency
        urgency = service_attributes.get("urgency")
        if urgency and urgency != "NORMAL":
            query_parts.append(f"urgency {urgency}")
        
        return " ".join(query_parts) if query_parts else service_code
    
    async def _get_ml_classification(self, case: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get ML classification for intelligent retrieval"""
        try:
            from ..ml_services import MLClassificationRequest
            
            # Build features for classification
            features = {
                "insurer_id": case.get("insurer_id"),
                "plan_id": case.get("plan_id"),
                "service_code": case.get("service_code"),
                "service_amount": case.get("service_amount", 0.0),
                "provider_type": case.get("provider_type"),
                "customer_age": case.get("customer_age"),
                "service_urgency": case.get("service_urgency", "NORMAL"),
                "diagnosis_codes": case.get("diagnosis_codes", []),
                "procedure_codes": case.get("procedure_codes", [])
            }
            
            # Make classification request
            request = MLClassificationRequest(
                case_id=case["case_id"],
                features=features
            )
            
            response = await self.classification_service.predict(request)
            
            return {
                "request_type": response.request_type,
                "candidate_policy_ids": response.candidate_policy_ids,
                "route": response.route,
                "risk_prior": response.risk_prior,
                "probabilities": response.probabilities
            }
            
        except Exception as e:
            logger.warning(f"ML classification failed: {e}")
            return None
    
    async def _retrieve_documents(
        self, 
        query: RetrievalQuery, 
        ml_classification: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """Retrieve relevant documents using RAG"""
        
        # If we have real vector store, use it
        if self.vector_store_client:
            return await self._retrieve_from_vector_store(query, ml_classification)
        
        # Otherwise, use database-based retrieval
        return await self._retrieve_from_database(query, ml_classification)
    
    async def _retrieve_from_vector_store(
        self, 
        query: RetrievalQuery, 
        ml_classification: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """Retrieve documents from vector store (ChromaDB, Pinecone, etc.)"""
        
        # This would integrate with actual vector store
        # For now, implement a mock version
        
        results = []
        
        # Use ML classification to filter candidate policies
        candidate_policy_ids = []
        if ml_classification:
            candidate_policy_ids = ml_classification.get("candidate_policy_ids", [])
        
        # Build vector search query
        search_query = {
            "query_text": query.query_text,
            "filter": {
                "insurer_id": query.insurer_id,
                "plan_id": query.plan_id,
                "service_codes": [query.service_code],
                "policy_ids": candidate_policy_ids if candidate_policy_ids else None
            },
            "top_k": query.max_results,
            "min_score": query.min_relevance_score
        }
        
        # Mock vector search results
        mock_results = await self._mock_vector_search(search_query)
        
        for result in mock_results:
            retrieval_result = RetrievalResult(
                document=result["document"],
                relevance_score=result["score"],
                confidence_score=result["confidence"],
                excerpt=result["excerpt"],
                pointer=result["pointer"],
                table_ref=result.get("table_ref")
            )
            results.append(retrieval_result)
        
        return results
    
    async def _retrieve_from_database(
        self, 
        query: RetrievalQuery, 
        ml_classification: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """Retrieve documents from database using text search"""
        
        results = []
        
        # Get policy repository
        policy_repo = self.repo_factory.policy_repository()
        
        # Search for relevant policies
        policies = policy_repo.search_policies(
            policy_type=self._map_service_to_policy_type(query.service_code),
            status="ACTIVE"
        )
        
        # Score and rank policies
        for policy in policies:
            relevance_score = self._calculate_text_relevance(
                query.query_text, policy.content or ""
            )
            
            if relevance_score >= query.min_relevance_score:
                # Extract relevant excerpt
                excerpt = self._extract_relevant_excerpt(
                    policy.content or "", query.query_text
                )
                
                # Create document reference
                document = DocumentReference(
                    doc_id=policy.policy_id,
                    version=policy.version,
                    title=policy.name,
                    content=policy.content or "",
                    checksum=policy.content_hash,
                    source_url=f"policy://{policy.policy_id}/{policy.version}",
                    last_updated=policy.updated_at,
                    policy_type=policy.policy_type,
                    category=policy.category or "",
                    tags=policy.tags or []
                )
                
                # Create retrieval result
                result = RetrievalResult(
                    document=document,
                    relevance_score=relevance_score,
                    confidence_score=min(relevance_score + 0.1, 1.0),
                    excerpt=excerpt,
                    pointer=f"policy://{policy.policy_id}/{policy.version}#content"
                )
                
                results.append(result)
        
        # Sort by relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results[:query.max_results]
    
    async def _mock_vector_search(self, search_query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Mock vector search for development/testing"""
        
        # Simulate vector search results
        mock_documents = [
            {
                "doc_id": "POL_MED_001",
                "version": "v2.1.0",
                "title": "Medical Coverage Policy",
                "content": "This policy covers medical consultations, diagnostic tests, and emergency care...",
                "policy_type": "MEDICAL",
                "category": "COVERAGE"
            },
            {
                "doc_id": "POL_DENTAL_001", 
                "version": "v1.5.0",
                "title": "Dental Care Policy",
                "content": "This policy covers dental procedures, cleanings, and orthodontic care...",
                "policy_type": "DENTAL",
                "category": "COVERAGE"
            },
            {
                "doc_id": "POL_EMERGENCY_001",
                "version": "v1.8.0", 
                "title": "Emergency Care Policy",
                "content": "This policy covers emergency room visits, ambulance services, and urgent care...",
                "policy_type": "EMERGENCY",
                "category": "COVERAGE"
            }
        ]
        
        results = []
        query_text = search_query["query_text"].lower()
        
        for doc in mock_documents:
            # Simple text matching for mock
            content_lower = doc["content"].lower()
            title_lower = doc["title"].lower()
            
            # Calculate mock relevance score
            score = 0.0
            if any(word in content_lower for word in query_text.split()):
                score += 0.6
            if any(word in title_lower for word in query_text.split()):
                score += 0.3
            
            if score >= search_query.get("min_score", 0.5):
                # Create document reference
                document = DocumentReference(
                    doc_id=doc["doc_id"],
                    version=doc["version"],
                    title=doc["title"],
                    content=doc["content"],
                    checksum=hashlib.sha256(doc["content"].encode()).hexdigest(),
                    source_url=f"policy://{doc['doc_id']}/{doc['version']}",
                    last_updated=datetime.utcnow(),
                    policy_type=doc["policy_type"],
                    category=doc["category"],
                    tags=[]
                )
                
                # Extract excerpt
                excerpt = doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"]
                
                results.append({
                    "document": document,
                    "score": min(score, 1.0),
                    "confidence": min(score + 0.1, 1.0),
                    "excerpt": excerpt,
                    "pointer": f"policy://{doc['doc_id']}/{doc['version']}#content"
                })
        
        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results[:search_query.get("top_k", 10)]
    
    def _map_service_to_policy_type(self, service_code: str) -> Optional[str]:
        """Map service code to policy type"""
        if not service_code:
            return None
        
        service_lower = service_code.lower()
        
        if "dental" in service_lower:
            return "DENTAL"
        elif "emergency" in service_lower:
            return "EMERGENCY"
        elif "surgery" in service_lower:
            return "SURGICAL"
        elif "consultation" in service_lower:
            return "MEDICAL"
        elif "diagnostic" in service_lower:
            return "DIAGNOSTIC"
        else:
            return "MEDICAL"  # Default
    
    def _calculate_text_relevance(self, query: str, content: str) -> float:
        """Calculate text relevance score using simple matching"""
        if not query or not content:
            return 0.0
        
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = query_words.intersection(content_words)
        union = query_words.union(content_words)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _extract_relevant_excerpt(self, content: str, query: str, max_length: int = 300) -> str:
        """Extract relevant excerpt from content"""
        if not content or not query:
            return content[:max_length] if content else ""
        
        # Find sentences containing query words
        query_words = query.lower().split()
        sentences = content.split('.')
        
        relevant_sentences = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(word in sentence_lower for word in query_words):
                relevant_sentences.append(sentence.strip())
        
        if relevant_sentences:
            excerpt = '. '.join(relevant_sentences[:2])
            if len(excerpt) > max_length:
                excerpt = excerpt[:max_length] + "..."
            return excerpt
        
        # Fallback to beginning of content
        return content[:max_length] + "..." if len(content) > max_length else content
    
    async def _validate_documents(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Validate documents against allowlist and version requirements"""
        
        if not self.version_validation_enabled:
            return results
        
        validated_results = []
        
        for result in results:
            try:
                # Validate against source allowlist (RB-02)
                is_valid, errors = self.source_allowlist.validate_source_reference(
                    result.document.doc_id,
                    result.document.version,
                    result.document.checksum
                )
                
                if is_valid:
                    validated_results.append(result)
                else:
                    logger.warning(
                        f"Document {result.document.doc_id} v{result.document.version} "
                        f"failed validation: {errors}"
                    )
            
            except Exception as e:
                logger.error(f"Document validation failed for {result.document.doc_id}: {e}")
        
        return validated_results
    
    async def _apply_policy_exceptions(
        self, 
        results: List[RetrievalResult], 
        case: Dict[str, Any]
    ) -> List[RetrievalResult]:
        """Apply policy exceptions per RB-03"""
        
        # Get active policy exceptions
        exception_repo = self.repo_factory.policy_exception_repository()
        active_exceptions = exception_repo.get_active_exceptions()
        
        if not active_exceptions:
            return results
        
        # Check each result against exceptions
        modified_results = []
        
        for result in results:
            # Check if any exception applies to this case and document
            applicable_exceptions = []
            
            for exception in active_exceptions:
                if self._exception_applies_to_case(exception, case, result.document):
                    applicable_exceptions.append(exception)
            
            if applicable_exceptions:
                # Apply exception overrides
                modified_result = await self._apply_exception_overrides(
                    result, applicable_exceptions
                )
                modified_results.append(modified_result)
                
                # Log exception usage
                for exception in applicable_exceptions:
                    exception_repo.increment_usage(exception.exception_id)
                    logger.info(
                        f"Applied policy exception {exception.exception_id} "
                        f"to document {result.document.doc_id}"
                    )
            else:
                modified_results.append(result)
        
        return modified_results
    
    def _exception_applies_to_case(
        self, 
        exception: Any, 
        case: Dict[str, Any], 
        document: DocumentReference
    ) -> bool:
        """Check if policy exception applies to case and document"""
        
        scope_criteria = exception.scope_criteria or {}
        
        # Check document criteria
        if "policy_ids" in scope_criteria:
            if document.doc_id not in scope_criteria["policy_ids"]:
                return False
        
        if "policy_types" in scope_criteria:
            if document.policy_type not in scope_criteria["policy_types"]:
                return False
        
        # Check case criteria
        if "service_codes" in scope_criteria:
            if case.get("service_code") not in scope_criteria["service_codes"]:
                return False
        
        if "insurer_ids" in scope_criteria:
            if case.get("insurer_id") not in scope_criteria["insurer_ids"]:
                return False
        
        if "plan_ids" in scope_criteria:
            if case.get("plan_id") not in scope_criteria["plan_ids"]:
                return False
        
        # Check amount criteria
        if "min_amount" in scope_criteria:
            if case.get("service_amount", 0) < scope_criteria["min_amount"]:
                return False
        
        if "max_amount" in scope_criteria:
            if case.get("service_amount", 0) > scope_criteria["max_amount"]:
                return False
        
        return True
    
    async def _apply_exception_overrides(
        self, 
        result: RetrievalResult, 
        exceptions: List[Any]
    ) -> RetrievalResult:
        """Apply exception overrides to retrieval result"""
        
        # Create modified result
        modified_result = RetrievalResult(
            document=result.document,
            relevance_score=result.relevance_score,
            confidence_score=result.confidence_score,
            excerpt=result.excerpt,
            pointer=result.pointer,
            table_ref=result.table_ref,
            conflict_indicators=result.conflict_indicators or []
        )
        
        # Apply overrides from exceptions
        for exception in exceptions:
            override_rules = exception.override_rules or {}
            
            # Override relevance score
            if "relevance_score" in override_rules:
                modified_result.relevance_score = override_rules["relevance_score"]
            
            # Override confidence score
            if "confidence_score" in override_rules:
                modified_result.confidence_score = override_rules["confidence_score"]
            
            # Add exception indicator
            modified_result.conflict_indicators.append(f"EXCEPTION:{exception.exception_id}")
        
        return modified_result
    
    async def _detect_conflicts(self, results: List[RetrievalResult]) -> Dict[str, Any]:
        """Detect conflicts between retrieved documents"""
        
        if not self.conflict_detection_enabled or len(results) < 2:
            return {"conflicts_detected": False, "conflict_details": []}
        
        conflicts = []
        
        # Check for conflicting policies
        for i, result1 in enumerate(results):
            for j, result2 in enumerate(results[i+1:], i+1):
                conflict = await self._check_document_conflict(result1, result2)
                if conflict:
                    conflicts.append(conflict)
        
        return {
            "conflicts_detected": len(conflicts) > 0,
            "conflict_details": conflicts,
            "conflict_count": len(conflicts)
        }
    
    async def _check_document_conflict(
        self, 
        result1: RetrievalResult, 
        result2: RetrievalResult
    ) -> Optional[Dict[str, Any]]:
        """Check for conflict between two documents"""
        
        doc1 = result1.document
        doc2 = result2.document
        
        # Same document, different versions
        if doc1.doc_id == doc2.doc_id and doc1.version != doc2.version:
            return {
                "type": "VERSION_CONFLICT",
                "description": f"Multiple versions of {doc1.doc_id}: {doc1.version} vs {doc2.version}",
                "documents": [
                    {"doc_id": doc1.doc_id, "version": doc1.version},
                    {"doc_id": doc2.doc_id, "version": doc2.version}
                ],
                "severity": "HIGH"
            }
        
        # Conflicting policy types
        if doc1.policy_type == doc2.policy_type and doc1.category == doc2.category:
            # Check for conflicting content (simplified)
            if self._has_conflicting_content(result1.excerpt, result2.excerpt):
                return {
                    "type": "CONTENT_CONFLICT",
                    "description": f"Conflicting content between {doc1.doc_id} and {doc2.doc_id}",
                    "documents": [
                        {"doc_id": doc1.doc_id, "version": doc1.version},
                        {"doc_id": doc2.doc_id, "version": doc2.version}
                    ],
                    "severity": "MEDIUM"
                }
        
        return None
    
    def _has_conflicting_content(self, excerpt1: str, excerpt2: str) -> bool:
        """Check if two excerpts have conflicting content (simplified)"""
        
        # Look for conflicting keywords
        conflict_patterns = [
            (r'\bnot\s+covered\b', r'\bcovered\b'),
            (r'\bexcluded\b', r'\bincluded\b'),
            (r'\bdenied\b', r'\bapproved\b'),
            (r'\bineligible\b', r'\beligible\b')
        ]
        
        excerpt1_lower = excerpt1.lower()
        excerpt2_lower = excerpt2.lower()
        
        for negative_pattern, positive_pattern in conflict_patterns:
            if (re.search(negative_pattern, excerpt1_lower) and 
                re.search(positive_pattern, excerpt2_lower)) or \
               (re.search(positive_pattern, excerpt1_lower) and 
                re.search(negative_pattern, excerpt2_lower)):
                return True
        
        return False
    
    async def _calculate_coverage_score(
        self, 
        results: List[RetrievalResult], 
        query: RetrievalQuery
    ) -> float:
        """Calculate coverage score for retrieved evidence"""
        
        if not results:
            return 0.0
        
        # Factors for coverage calculation
        relevance_factor = 0.4
        confidence_factor = 0.3
        completeness_factor = 0.2
        diversity_factor = 0.1
        
        # Calculate average relevance
        avg_relevance = sum(r.relevance_score for r in results) / len(results)
        
        # Calculate average confidence
        avg_confidence = sum(r.confidence_score for r in results) / len(results)
        
        # Calculate completeness (based on expected document types)
        expected_types = self._get_expected_document_types(query)
        found_types = set(r.document.policy_type for r in results)
        completeness = len(found_types.intersection(expected_types)) / len(expected_types) if expected_types else 1.0
        
        # Calculate diversity (different document sources)
        unique_docs = len(set(r.document.doc_id for r in results))
        diversity = min(unique_docs / 3, 1.0)  # Normalize to max 3 different documents
        
        # Calculate weighted coverage score
        coverage_score = (
            avg_relevance * relevance_factor +
            avg_confidence * confidence_factor +
            completeness * completeness_factor +
            diversity * diversity_factor
        )
        
        return min(coverage_score, 1.0)
    
    def _get_expected_document_types(self, query: RetrievalQuery) -> Set[str]:
        """Get expected document types for a query"""
        
        service_code = query.service_code.lower()
        expected_types = {"MEDICAL"}  # Always expect general medical policy
        
        if "dental" in service_code:
            expected_types.add("DENTAL")
        elif "emergency" in service_code:
            expected_types.add("EMERGENCY")
        elif "surgery" in service_code:
            expected_types.add("SURGICAL")
        elif "diagnostic" in service_code:
            expected_types.add("DIAGNOSTIC")
        
        return expected_types
    
    async def _construct_evidence_pack(
        self,
        case_id: str,
        results: List[RetrievalResult],
        coverage_score: float,
        conflict_analysis: Dict[str, Any]
    ) -> EvidencePack:
        """Construct evidence pack from retrieval results"""
        
        # Convert results to evidence items
        evidence_items = []
        
        for result in results:
            evidence_item = {
                "doc_id": result.document.doc_id,
                "version": result.document.version,
                "checksum": result.document.checksum,
                "pointer": result.pointer,
                "excerpt": result.excerpt,
                "table_ref": result.table_ref,
                "relevance_score": result.relevance_score,
                "confidence_score": result.confidence_score
            }
            evidence_items.append(evidence_item)
        
        # Identify missing sources
        missing_sources = []
        if coverage_score < self.min_coverage_threshold:
            missing_sources = await self._identify_missing_sources(case_id, results)
        
        # Create evidence pack
        evidence_pack = {
            "items": evidence_items,
            "coverage_score": coverage_score,
            "conflicts_detected": conflict_analysis["conflicts_detected"],
            "missing_sources": missing_sources,
            "retrieval_method": "RAG",
            "retrieval_timestamp": datetime.utcnow(),
            "retrieval_duration_ms": None  # Will be set by caller
        }
        
        return evidence_pack
    
    async def _identify_missing_sources(
        self, 
        case_id: str, 
        results: List[RetrievalResult]
    ) -> List[str]:
        """Identify missing sources that should be included"""
        
        missing = []
        
        # Check for missing policy types based on service
        # This is a simplified implementation
        found_types = set(r.document.policy_type for r in results)
        
        if "MEDICAL" not in found_types:
            missing.append("MEDICAL_POLICY")
        
        if len(results) < 2:
            missing.append("ADDITIONAL_COVERAGE_POLICIES")
        
        return missing
    
    async def _log_retrieval_metrics(
        self,
        case_id: str,
        total_retrieved: int,
        validated_count: int,
        coverage_score: float,
        processing_time_ms: int
    ) -> None:
        """Log retrieval metrics for monitoring"""
        
        logger.info(
            f"Policy retrieval metrics for case {case_id}: "
            f"retrieved={total_retrieved}, validated={validated_count}, "
            f"coverage={coverage_score:.3f}, time={processing_time_ms}ms"
        )
        
        # TODO: Send metrics to monitoring system
        # await self.metrics_client.record_retrieval_metrics(...)


# Factory function for creating policy retrieval agent
def create_policy_retrieval_agent(
    vector_store_client=None,
    knowledge_base_client=None,
    classification_service: MLClassificationService = None,
    use_mock: bool = False
) -> PolicyRetrievalAgent:
    """
    Factory function to create policy retrieval agent.
    
    Args:
        vector_store_client: Vector store client (ChromaDB, Pinecone, etc.)
        knowledge_base_client: Knowledge base client
        classification_service: ML classification service
        use_mock: Whether to use mock implementations
        
    Returns:
        Configured policy retrieval agent
    """
    return PolicyRetrievalAgent(
        vector_store_client=vector_store_client,
        knowledge_base_client=knowledge_base_client,
        classification_service=classification_service,
        use_mock=use_mock
    )
