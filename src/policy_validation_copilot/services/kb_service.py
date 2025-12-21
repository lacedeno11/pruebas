"""
Knowledge Base Service.

Handles RAG operations against the policy document index.
Based on UC-OP-06 Policy Retrieval Agent.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from policy_validation_copilot.models.evidence import (
    EvidenceItem,
    EvidencePack,
    EvidenceType,
    ConflictFlag,
)

logger = logging.getLogger(__name__)


class KBServiceError(Exception):
    """Error in KB operations."""

    pass


class KnowledgeBaseService:
    """
    Knowledge Base service for policy retrieval (RAG).

    Provides semantic search over indexed policy documents
    with evidence extraction and conflict detection.
    """

    def __init__(
        self,
        collection_name: str = "policy_embeddings",
        vector_db_url: Optional[str] = None,
    ):
        self.collection_name = collection_name
        self.vector_db_url = vector_db_url
        # In production, this would connect to a vector database
        # like Pinecone, Weaviate, Milvus, or pgvector
        self._mock_index: list[dict] = []

    async def index_document(
        self,
        doc_id: str,
        version: str,
        chunks: list[dict],
        metadata: dict,
    ) -> dict:
        """
        Index document chunks for retrieval.

        Each chunk includes text, embedding, and location pointer.
        """
        indexed_count = 0
        for chunk in chunks:
            self._mock_index.append({
                "doc_id": doc_id,
                "version": version,
                "chunk_id": str(uuid4()),
                "text": chunk.get("text", ""),
                "pointer": chunk.get("pointer", ""),
                "page_number": chunk.get("page_number"),
                "section_id": chunk.get("section_id"),
                "metadata": {**metadata, **chunk.get("metadata", {})},
            })
            indexed_count += 1

        logger.info(f"Indexed {indexed_count} chunks for document {doc_id}")
        return {"doc_id": doc_id, "indexed_chunks": indexed_count}

    async def search(
        self,
        query: str,
        filters: Optional[dict] = None,
        top_k: int = 10,
        min_relevance: float = 0.5,
    ) -> list[dict]:
        """
        Semantic search over indexed documents.

        Returns ranked results with relevance scores.
        """
        # In production, this would:
        # 1. Embed the query
        # 2. Search vector index
        # 3. Apply metadata filters
        # 4. Return ranked results

        # Mock implementation for demonstration
        results = []
        for item in self._mock_index:
            # Simple keyword matching for mock
            if query.lower() in item["text"].lower():
                results.append({
                    **item,
                    "relevance_score": 0.85,
                    "confidence_score": 0.9,
                })

        # Apply filters
        if filters:
            if filters.get("insurer_id"):
                results = [
                    r for r in results
                    if r.get("metadata", {}).get("insurer_id") == filters["insurer_id"]
                ]
            if filters.get("effective_before"):
                pass  # Would filter by date

        return results[:top_k]

    async def retrieve_evidence(
        self,
        query: str,
        case_context: dict,
        allowlist: Optional[list[str]] = None,
        top_k: int = 10,
    ) -> EvidencePack:
        """
        Retrieve evidence pack for a case query.

        UC-OP-06: Builds complete evidence pack with pointers and coverage.
        """
        start_time = datetime.utcnow()
        pack_id = str(uuid4())

        # Build search filters from case context
        filters = {
            "insurer_id": case_context.get("insurer_id"),
            "plan_id": case_context.get("plan_id"),
        }

        # Execute search
        results = await self.search(query, filters=filters, top_k=top_k)

        # Convert to evidence items
        items: list[EvidenceItem] = []
        for result in results:
            # Check allowlist
            is_allowlisted = True
            if allowlist:
                is_allowlisted = result["doc_id"] in allowlist

            item = EvidenceItem(
                evidence_id=str(uuid4()),
                doc_id=result["doc_id"],
                doc_version=result["version"],
                checksum=result.get("metadata", {}).get("checksum", ""),
                pointer=result["pointer"],
                page_number=result.get("page_number"),
                section_id=result.get("section_id"),
                evidence_type=EvidenceType.POLICY_TEXT,
                excerpt=result["text"][:500] if result["text"] else None,
                relevance_score=result["relevance_score"],
                confidence_score=result["confidence_score"],
                is_allowlisted=is_allowlisted,
                retrieval_query=query,
            )
            items.append(item)

        # Calculate coverage score
        coverage_score = self._calculate_coverage(items, case_context)

        # Detect conflicts
        conflicts = self._detect_conflicts(items)

        duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return EvidencePack(
            pack_id=pack_id,
            case_id=case_context.get("case_id", ""),
            items=items,
            coverage_score=coverage_score,
            missing_sources=self._identify_missing_sources(items, case_context),
            conflicts=conflicts,
            conflicts_detected=len(conflicts) > 0,
            retrieval_duration_ms=duration,
            total_documents_searched=len(self._mock_index),
        )

    def _calculate_coverage(
        self,
        items: list[EvidenceItem],
        case_context: dict,
    ) -> float:
        """Calculate coverage score based on evidence relevance and completeness."""
        if not items:
            return 0.0

        # Average relevance of top items
        top_items = sorted(items, key=lambda x: x.relevance_score, reverse=True)[:5]
        avg_relevance = sum(i.relevance_score for i in top_items) / len(top_items)

        # Check for allowlisted sources
        allowlisted_ratio = sum(1 for i in items if i.is_allowlisted) / len(items)

        # Combined score
        return min(1.0, avg_relevance * 0.7 + allowlisted_ratio * 0.3)

    def _detect_conflicts(self, items: list[EvidenceItem]) -> list[ConflictFlag]:
        """Detect conflicts between evidence items."""
        conflicts: list[ConflictFlag] = []

        # In production, this would:
        # 1. Compare coverage statements
        # 2. Check for contradictory exclusions
        # 3. Validate date ranges
        # 4. Check limit conflicts

        # For now, return empty (no conflicts detected in mock)
        return conflicts

    def _identify_missing_sources(
        self,
        items: list[EvidenceItem],
        case_context: dict,
    ) -> list[str]:
        """Identify expected but missing policy sources."""
        missing = []

        # In production, would check:
        # - Expected policy docs for insurer/plan
        # - Required coverage areas
        # - Mandatory exclusion lists

        if not items:
            missing.append(f"No policies found for plan {case_context.get('plan_id')}")

        return missing
