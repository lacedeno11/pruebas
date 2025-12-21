"""
ChromaDB Vector Store for DERCAS 01 Policy Validation Copilot

Implements vector database integration for policy document embeddings and RAG functionality.
Supports policy document storage, similarity search, and evidence retrieval for UC-OP-06.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import chromadb
import numpy as np
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer

from ..models.entities import PolicyDocument
from ..models.enums import DocumentType

logger = logging.getLogger(__name__)


class VectorStoreConfig:
    """Configuration for ChromaDB vector store."""
    
    def __init__(
        self,
        persist_directory: str = "./data/chromadb",
        collection_name: str = "policy_documents",
        embedding_model: str = "all-MiniLM-L6-v2",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        similarity_threshold: float = 0.7,
        max_results: int = 10,
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.similarity_threshold = similarity_threshold
        self.max_results = max_results


class DocumentChunk:
    """Represents a document chunk with metadata."""
    
    def __init__(
        self,
        chunk_id: str,
        doc_id: str,
        version: str,
        content: str,
        metadata: Dict[str, Any],
        page_number: Optional[int] = None,
        section: Optional[str] = None,
        table_ref: Optional[str] = None,
    ):
        self.chunk_id = chunk_id
        self.doc_id = doc_id
        self.version = version
        self.content = content
        self.metadata = metadata
        self.page_number = page_number
        self.section = section
        self.table_ref = table_ref
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary for storage."""
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "version": self.version,
            "content": self.content,
            "metadata": self.metadata,
            "page_number": self.page_number,
            "section": self.section,
            "table_ref": self.table_ref,
        }


class PolicyVectorStore:
    """
    ChromaDB-based vector store for policy documents.
    
    Provides functionality for:
    - Document ingestion and chunking
    - Vector embedding generation
    - Similarity search for RAG
    - Evidence retrieval with metadata
    """
    
    def __init__(self, config: VectorStoreConfig):
        self.config = config
        self.client = None
        self.collection = None
        self.embedding_function = None
        self._initialize_client()
        
    def _initialize_client(self):
        """Initialize ChromaDB client and collection."""
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=self.config.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )
            
            # Initialize embedding function
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.config.embedding_model
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(
                    name=self.config.collection_name,
                    embedding_function=self.embedding_function
                )
                logger.info(f"Connected to existing collection: {self.config.collection_name}")
            except ValueError:
                # Collection doesn't exist, create it
                self.collection = self.client.create_collection(
                    name=self.config.collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"description": "Policy documents for DERCAS 01 validation"}
                )
                logger.info(f"Created new collection: {self.config.collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise
    
    def _chunk_document(self, content: str, doc_metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """
        Split document content into chunks for embedding.
        
        Args:
            content: Document text content
            doc_metadata: Document metadata
            
        Returns:
            List of document chunks
        """
        chunks = []
        
        # Simple chunking strategy - can be enhanced with more sophisticated methods
        words = content.split()
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_content = " ".join(chunk_words)
            
            if len(chunk_content.strip()) < 50:  # Skip very short chunks
                continue
                
            chunk_id = f"{doc_metadata['doc_id']}_{doc_metadata['version']}_chunk_{i // (chunk_size - overlap)}"
            
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                doc_id=doc_metadata["doc_id"],
                version=doc_metadata["version"],
                content=chunk_content,
                metadata={
                    **doc_metadata,
                    "chunk_index": i // (chunk_size - overlap),
                    "chunk_start_word": i,
                    "chunk_end_word": min(i + chunk_size, len(words)),
                    "total_words": len(words),
                }
            )
            chunks.append(chunk)
            
        return chunks
    
    def add_document(
        self,
        doc_id: str,
        version: str,
        content: str,
        metadata: Dict[str, Any],
        replace_existing: bool = False,
    ) -> bool:
        """
        Add a document to the vector store.
        
        Args:
            doc_id: Document identifier
            version: Document version
            content: Document text content
            metadata: Document metadata
            replace_existing: Whether to replace existing document
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if document already exists
            existing_docs = self.collection.get(
                where={"doc_id": doc_id, "version": version}
            )
            
            if existing_docs["ids"] and not replace_existing:
                logger.warning(f"Document {doc_id} version {version} already exists")
                return False
            
            # Remove existing document if replacing
            if existing_docs["ids"] and replace_existing:
                self.remove_document(doc_id, version)
            
            # Prepare document metadata
            doc_metadata = {
                "doc_id": doc_id,
                "version": version,
                "document_type": metadata.get("document_type", DocumentType.POLICY),
                "insurer_id": metadata.get("insurer_id", ""),
                "plan_ids": json.dumps(metadata.get("plan_ids", [])),
                "service_codes": json.dumps(metadata.get("service_codes", [])),
                "effective_date": metadata.get("effective_date", "").isoformat() if metadata.get("effective_date") else "",
                "status": metadata.get("status", ""),
                "title": metadata.get("title", ""),
                "checksum": metadata.get("checksum", ""),
                "added_at": datetime.utcnow().isoformat(),
            }
            
            # Chunk the document
            chunks = self._chunk_document(content, doc_metadata)
            
            if not chunks:
                logger.warning(f"No chunks generated for document {doc_id}")
                return False
            
            # Prepare data for ChromaDB
            chunk_ids = [chunk.chunk_id for chunk in chunks]
            chunk_contents = [chunk.content for chunk in chunks]
            chunk_metadatas = [chunk.metadata for chunk in chunks]
            
            # Add to collection
            self.collection.add(
                ids=chunk_ids,
                documents=chunk_contents,
                metadatas=chunk_metadatas
            )
            
            logger.info(f"Added document {doc_id} version {version} with {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add document {doc_id}: {e}")
            return False
    
    def remove_document(self, doc_id: str, version: Optional[str] = None) -> bool:
        """
        Remove a document from the vector store.
        
        Args:
            doc_id: Document identifier
            version: Document version (if None, removes all versions)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            where_clause = {"doc_id": doc_id}
            if version:
                where_clause["version"] = version
            
            # Get existing chunks
            existing_chunks = self.collection.get(where=where_clause)
            
            if not existing_chunks["ids"]:
                logger.warning(f"No chunks found for document {doc_id}")
                return False
            
            # Delete chunks
            self.collection.delete(ids=existing_chunks["ids"])
            
            logger.info(f"Removed document {doc_id} version {version or 'all'}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove document {doc_id}: {e}")
            return False
    
    def search_similar(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        max_results: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar document chunks.
        
        Args:
            query: Search query text
            filters: Metadata filters
            max_results: Maximum number of results
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            List of similar chunks with metadata and scores
        """
        try:
            max_results = max_results or self.config.max_results
            similarity_threshold = similarity_threshold or self.config.similarity_threshold
            
            # Perform similarity search
            results = self.collection.query(
                query_texts=[query],
                n_results=max_results,
                where=filters,
                include=["documents", "metadatas", "distances"]
            )
            
            # Process results
            similar_chunks = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0], 
                results["distances"][0]
            )):
                # Convert distance to similarity score (ChromaDB uses cosine distance)
                similarity_score = 1.0 - distance
                
                if similarity_score >= similarity_threshold:
                    chunk_result = {
                        "chunk_id": results["ids"][0][i],
                        "content": doc,
                        "metadata": metadata,
                        "similarity_score": similarity_score,
                        "distance": distance,
                    }
                    similar_chunks.append(chunk_result)
            
            logger.info(f"Found {len(similar_chunks)} similar chunks for query")
            return similar_chunks
            
        except Exception as e:
            logger.error(f"Failed to search similar chunks: {e}")
            return []
    
    def retrieve_evidence(
        self,
        query: str,
        case_context: Dict[str, Any],
        max_evidence_items: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve evidence for a specific case query.
        
        Args:
            query: Evidence search query
            case_context: Case context for filtering
            max_evidence_items: Maximum evidence items to return
            
        Returns:
            List of evidence items with relevance scores
        """
        try:
            # Build filters based on case context
            filters = {}
            
            if case_context.get("insurer_id"):
                filters["insurer_id"] = case_context["insurer_id"]
            
            # Search for relevant chunks
            similar_chunks = self.search_similar(
                query=query,
                filters=filters,
                max_results=max_evidence_items * 2,  # Get more to filter
                similarity_threshold=0.6,  # Lower threshold for evidence
            )
            
            # Process chunks into evidence items
            evidence_items = []
            seen_docs = set()
            
            for chunk in similar_chunks:
                if len(evidence_items) >= max_evidence_items:
                    break
                
                metadata = chunk["metadata"]
                doc_key = f"{metadata['doc_id']}_{metadata['version']}"
                
                # Avoid duplicate documents in evidence
                if doc_key in seen_docs:
                    continue
                seen_docs.add(doc_key)
                
                # Create evidence item
                evidence_item = {
                    "doc_id": metadata["doc_id"],
                    "version": metadata["version"],
                    "checksum": metadata.get("checksum", ""),
                    "pointer": f"chunk_{metadata.get('chunk_index', 0)}",
                    "excerpt": chunk["content"][:500] + "..." if len(chunk["content"]) > 500 else chunk["content"],
                    "table_ref": metadata.get("table_ref"),
                    "relevance_score": chunk["similarity_score"],
                    "confidence_score": min(chunk["similarity_score"] * 1.2, 1.0),  # Boost confidence slightly
                    "metadata": {
                        "title": metadata.get("title", ""),
                        "document_type": metadata.get("document_type", ""),
                        "effective_date": metadata.get("effective_date", ""),
                        "page_number": metadata.get("page_number"),
                        "section": metadata.get("section"),
                    }
                }
                evidence_items.append(evidence_item)
            
            logger.info(f"Retrieved {len(evidence_items)} evidence items for query")
            return evidence_items
            
        except Exception as e:
            logger.error(f"Failed to retrieve evidence: {e}")
            return []
    
    def get_document_info(self, doc_id: str, version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get information about a document.
        
        Args:
            doc_id: Document identifier
            version: Document version (if None, gets all versions)
            
        Returns:
            List of document information
        """
        try:
            where_clause = {"doc_id": doc_id}
            if version:
                where_clause["version"] = version
            
            results = self.collection.get(
                where=where_clause,
                include=["metadatas"]
            )
            
            # Group by version
            doc_info = {}
            for metadata in results["metadatas"]:
                doc_version = metadata["version"]
                if doc_version not in doc_info:
                    doc_info[doc_version] = {
                        "doc_id": metadata["doc_id"],
                        "version": metadata["version"],
                        "title": metadata.get("title", ""),
                        "document_type": metadata.get("document_type", ""),
                        "insurer_id": metadata.get("insurer_id", ""),
                        "status": metadata.get("status", ""),
                        "effective_date": metadata.get("effective_date", ""),
                        "checksum": metadata.get("checksum", ""),
                        "added_at": metadata.get("added_at", ""),
                        "chunk_count": 0,
                    }
                doc_info[doc_version]["chunk_count"] += 1
            
            return list(doc_info.values())
            
        except Exception as e:
            logger.error(f"Failed to get document info for {doc_id}: {e}")
            return []
    
    def list_documents(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all documents in the vector store.
        
        Args:
            filters: Metadata filters
            limit: Maximum number of documents to return
            
        Returns:
            List of document summaries
        """
        try:
            results = self.collection.get(
                where=filters,
                limit=limit,
                include=["metadatas"]
            )
            
            # Group by document and version
            documents = {}
            for metadata in results["metadatas"]:
                doc_key = f"{metadata['doc_id']}_{metadata['version']}"
                if doc_key not in documents:
                    documents[doc_key] = {
                        "doc_id": metadata["doc_id"],
                        "version": metadata["version"],
                        "title": metadata.get("title", ""),
                        "document_type": metadata.get("document_type", ""),
                        "insurer_id": metadata.get("insurer_id", ""),
                        "status": metadata.get("status", ""),
                        "effective_date": metadata.get("effective_date", ""),
                        "added_at": metadata.get("added_at", ""),
                        "chunk_count": 0,
                    }
                documents[doc_key]["chunk_count"] += 1
            
            return list(documents.values())
            
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store collection.
        
        Returns:
            Collection statistics
        """
        try:
            # Get collection info
            collection_info = self.collection.get(include=["metadatas"])
            
            total_chunks = len(collection_info["ids"])
            
            # Count unique documents
            unique_docs = set()
            doc_types = {}
            insurers = set()
            
            for metadata in collection_info["metadatas"]:
                doc_key = f"{metadata['doc_id']}_{metadata['version']}"
                unique_docs.add(doc_key)
                
                doc_type = metadata.get("document_type", "UNKNOWN")
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                
                if metadata.get("insurer_id"):
                    insurers.add(metadata["insurer_id"])
            
            stats = {
                "total_chunks": total_chunks,
                "unique_documents": len(unique_docs),
                "document_types": doc_types,
                "unique_insurers": len(insurers),
                "collection_name": self.config.collection_name,
                "embedding_model": self.config.embedding_model,
                "last_updated": datetime.utcnow().isoformat(),
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the vector store.
        
        Returns:
            Health check results
        """
        try:
            # Test basic operations
            test_results = {
                "client_connected": False,
                "collection_accessible": False,
                "embedding_function_working": False,
                "search_working": False,
                "error_message": None,
            }
            
            # Check client connection
            if self.client:
                test_results["client_connected"] = True
            
            # Check collection access
            if self.collection:
                test_results["collection_accessible"] = True
                
                # Test embedding function
                try:
                    test_embedding = self.embedding_function(["test"])
                    if test_embedding:
                        test_results["embedding_function_working"] = True
                except Exception as e:
                    test_results["error_message"] = f"Embedding function error: {e}"
                
                # Test search
                try:
                    search_results = self.collection.query(
                        query_texts=["test query"],
                        n_results=1
                    )
                    if search_results:
                        test_results["search_working"] = True
                except Exception as e:
                    test_results["error_message"] = f"Search error: {e}"
            
            # Overall health
            test_results["healthy"] = all([
                test_results["client_connected"],
                test_results["collection_accessible"],
                test_results["embedding_function_working"],
                test_results["search_working"],
            ])
            
            return test_results
            
        except Exception as e:
            return {
                "healthy": False,
                "error_message": str(e),
                "client_connected": False,
                "collection_accessible": False,
                "embedding_function_working": False,
                "search_working": False,
            }
    
    def reset_collection(self) -> bool:
        """
        Reset the collection (delete all data).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete_collection(self.config.collection_name)
            self.collection = self.client.create_collection(
                name=self.config.collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "Policy documents for DERCAS 01 validation"}
            )
            logger.info(f"Reset collection: {self.config.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            return False


# Utility functions

def create_vector_store(config: Optional[VectorStoreConfig] = None) -> PolicyVectorStore:
    """
    Create a PolicyVectorStore instance with default or custom configuration.
    
    Args:
        config: Optional custom configuration
        
    Returns:
        PolicyVectorStore instance
    """
    if config is None:
        config = VectorStoreConfig()
    
    return PolicyVectorStore(config)


def calculate_coverage_score(evidence_items: List[Dict[str, Any]], query: str) -> float:
    """
    Calculate coverage score for evidence items.
    
    Args:
        evidence_items: List of evidence items
        query: Original query
        
    Returns:
        Coverage score between 0.0 and 1.0
    """
    if not evidence_items:
        return 0.0
    
    # Simple coverage calculation based on relevance scores
    total_relevance = sum(item.get("relevance_score", 0.0) for item in evidence_items)
    max_possible_relevance = len(evidence_items) * 1.0
    
    coverage_score = min(total_relevance / max_possible_relevance, 1.0)
    
    # Boost score if we have multiple high-quality evidence items
    high_quality_items = sum(1 for item in evidence_items if item.get("relevance_score", 0.0) > 0.8)
    if high_quality_items >= 2:
        coverage_score = min(coverage_score * 1.1, 1.0)
    
    return coverage_score
