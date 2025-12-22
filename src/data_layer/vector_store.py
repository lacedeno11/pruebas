"""
Vector Store layer for Knowledge Base and RAG with ChromaDB

This module provides vector storage and retrieval capabilities for the Policy
Validation Copilot's knowledge base and RAG (Retrieval-Augmented Generation) system.

Features:
- Document embedding and indexing with ChromaDB
- Semantic search and similarity matching
- Metadata filtering and exact pointer references
- Policy document versioning and allowlist validation
- Fragment and table extraction with precise citations
- Coverage score calculation for evidence retrieval
- Multi-modal content support (text, tables, structured data)
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

import chromadb
import numpy as np
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class DocumentFragment:
    """Represents a document fragment with metadata and embeddings"""
    
    def __init__(self, fragment_id: str, doc_id: str, version: str,
                 content: str, fragment_type: str, pointer: str,
                 metadata: Dict = None, embedding: List[float] = None):
        self.fragment_id = fragment_id
        self.doc_id = doc_id
        self.version = version
        self.content = content
        self.fragment_type = fragment_type  # text, table, section, etc.
        self.pointer = pointer  # exact reference (page/cell/section)
        self.metadata = metadata or {}
        self.embedding = embedding
        self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'fragment_id': self.fragment_id,
            'doc_id': self.doc_id,
            'version': self.version,
            'content': self.content,
            'fragment_type': self.fragment_type,
            'pointer': self.pointer,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DocumentFragment':
        """Create from dictionary"""
        fragment = cls(
            fragment_id=data['fragment_id'],
            doc_id=data['doc_id'],
            version=data['version'],
            content=data['content'],
            fragment_type=data['fragment_type'],
            pointer=data['pointer'],
            metadata=data.get('metadata', {})
        )
        if 'created_at' in data:
            fragment.created_at = datetime.fromisoformat(data['created_at'])
        return fragment


class EmbeddingProvider:
    """Abstract base for embedding providers"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the embedding model"""
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Initialized embedding model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise
    
    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """Encode text(s) to embeddings"""
        if isinstance(texts, str):
            return self.model.encode([texts])[0].tolist()
        return [embedding.tolist() for embedding in self.model.encode(texts)]
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.model.get_sentence_embedding_dimension()


class ChromaDBVectorStore:
    """ChromaDB-based vector store for document fragments"""
    
    def __init__(self, collection_name: str = "policy_documents",
                 persist_directory: str = "data/chromadb",
                 embedding_provider: EmbeddingProvider = None):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_provider = embedding_provider or EmbeddingProvider()
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create or get collection
        self.collection = self._get_or_create_collection()
        
        logger.info(f"Initialized ChromaDB vector store: {collection_name}")
    
    def _get_or_create_collection(self):
        """Get or create ChromaDB collection"""
        try:
            # Try to get existing collection
            collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=self.embedding_provider.model_name
                )
            )
            logger.info(f"Retrieved existing collection: {self.collection_name}")
        except Exception:
            # Create new collection
            collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=self.embedding_provider.model_name
                ),
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new collection: {self.collection_name}")
        
        return collection
    
    def add_fragment(self, fragment: DocumentFragment) -> bool:
        """Add document fragment to vector store"""
        try:
            # Generate embedding if not provided
            if fragment.embedding is None:
                fragment.embedding = self.embedding_provider.encode(fragment.content)
            
            # Prepare metadata for ChromaDB
            metadata = {
                'doc_id': fragment.doc_id,
                'version': fragment.version,
                'fragment_type': fragment.fragment_type,
                'pointer': fragment.pointer,
                'created_at': fragment.created_at.isoformat(),
                **fragment.metadata
            }
            
            # Add to collection
            self.collection.add(
                ids=[fragment.fragment_id],
                embeddings=[fragment.embedding],
                documents=[fragment.content],
                metadatas=[metadata]
            )
            
            logger.debug(f"Added fragment {fragment.fragment_id} to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add fragment {fragment.fragment_id}: {e}")
            return False
    
    def add_fragments_batch(self, fragments: List[DocumentFragment]) -> int:
        """Add multiple fragments in batch"""
        if not fragments:
            return 0
        
        try:
            # Prepare batch data
            ids = []
            embeddings = []
            documents = []
            metadatas = []
            
            for fragment in fragments:
                # Generate embedding if not provided
                if fragment.embedding is None:
                    fragment.embedding = self.embedding_provider.encode(fragment.content)
                
                ids.append(fragment.fragment_id)
                embeddings.append(fragment.embedding)
                documents.append(fragment.content)
                
                metadata = {
                    'doc_id': fragment.doc_id,
                    'version': fragment.version,
                    'fragment_type': fragment.fragment_type,
                    'pointer': fragment.pointer,
                    'created_at': fragment.created_at.isoformat(),
                    **fragment.metadata
                }
                metadatas.append(metadata)
            
            # Add batch to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Added {len(fragments)} fragments to vector store")
            return len(fragments)
            
        except Exception as e:
            logger.error(f"Failed to add fragments batch: {e}")
            return 0
    
    def search_fragments(self, query: str, n_results: int = 10,
                        filters: Dict = None, include_distances: bool = True) -> List[Dict]:
        """Search for similar fragments"""
        try:
            # Prepare where clause for filtering
            where_clause = {}
            if filters:
                for key, value in filters.items():
                    if isinstance(value, list):
                        where_clause[key] = {"$in": value}
                    else:
                        where_clause[key] = value
            
            # Perform search
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_clause if where_clause else None,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                result = {
                    'fragment_id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if include_distances else None
                }
                formatted_results.append(result)
            
            logger.debug(f"Found {len(formatted_results)} fragments for query")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search fragments: {e}")
            return []
    
    def get_fragment(self, fragment_id: str) -> Optional[Dict]:
        """Get specific fragment by ID"""
        try:
            results = self.collection.get(
                ids=[fragment_id],
                include=['documents', 'metadatas']
            )
            
            if results['ids']:
                return {
                    'fragment_id': results['ids'][0],
                    'content': results['documents'][0],
                    'metadata': results['metadatas'][0]
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get fragment {fragment_id}: {e}")
            return None
    
    def delete_fragment(self, fragment_id: str) -> bool:
        """Delete fragment by ID"""
        try:
            self.collection.delete(ids=[fragment_id])
            logger.debug(f"Deleted fragment {fragment_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete fragment {fragment_id}: {e}")
            return False
    
    def delete_document_fragments(self, doc_id: str, version: str = None) -> int:
        """Delete all fragments for a document"""
        try:
            where_clause = {"doc_id": doc_id}
            if version:
                where_clause["version"] = version
            
            # Get fragments to delete
            results = self.collection.get(
                where=where_clause,
                include=['documents', 'metadatas']
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} fragments for doc {doc_id}")
                return len(results['ids'])
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to delete fragments for doc {doc_id}: {e}")
            return 0
    
    def update_fragment(self, fragment_id: str, content: str = None,
                       metadata: Dict = None) -> bool:
        """Update fragment content and/or metadata"""
        try:
            update_data = {}
            
            if content is not None:
                # Generate new embedding for updated content
                embedding = self.embedding_provider.encode(content)
                update_data['documents'] = [content]
                update_data['embeddings'] = [embedding]
            
            if metadata is not None:
                update_data['metadatas'] = [metadata]
            
            if update_data:
                self.collection.update(
                    ids=[fragment_id],
                    **update_data
                )
                logger.debug(f"Updated fragment {fragment_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update fragment {fragment_id}: {e}")
            return False
    
    def get_collection_stats(self) -> Dict:
        """Get collection statistics"""
        try:
            count = self.collection.count()
            return {
                'total_fragments': count,
                'collection_name': self.collection_name,
                'embedding_model': self.embedding_provider.model_name,
                'embedding_dimension': self.embedding_provider.get_dimension()
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}


class PolicyKnowledgeBase:
    """High-level knowledge base for policy documents with RAG capabilities"""
    
    def __init__(self, vector_store: ChromaDBVectorStore,
                 allowlist_docs: List[str] = None):
        self.vector_store = vector_store
        self.allowlist_docs = set(allowlist_docs or [])
        self.fragment_cache = {}
        
        logger.info("Initialized Policy Knowledge Base")
    
    def index_policy_document(self, doc_id: str, version: str, content: str,
                             document_type: str = "policy", metadata: Dict = None,
                             chunk_size: int = 512, chunk_overlap: int = 50) -> int:
        """Index a policy document by chunking and embedding"""
        try:
            # Validate allowlist
            if self.allowlist_docs and doc_id not in self.allowlist_docs:
                logger.warning(f"Document {doc_id} not in allowlist, skipping indexing")
                return 0
            
            # Remove existing fragments for this document version
            self.vector_store.delete_document_fragments(doc_id, version)
            
            # Chunk the document
            fragments = self._chunk_document(
                doc_id=doc_id,
                version=version,
                content=content,
                document_type=document_type,
                metadata=metadata or {},
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            # Add fragments to vector store
            added_count = self.vector_store.add_fragments_batch(fragments)
            
            logger.info(f"Indexed document {doc_id} v{version}: {added_count} fragments")
            return added_count
            
        except Exception as e:
            logger.error(f"Failed to index document {doc_id}: {e}")
            return 0
    
    def _chunk_document(self, doc_id: str, version: str, content: str,
                       document_type: str, metadata: Dict,
                       chunk_size: int, chunk_overlap: int) -> List[DocumentFragment]:
        """Chunk document into fragments"""
        fragments = []
        
        # Simple text chunking (can be enhanced with more sophisticated methods)
        words = content.split()
        
        for i in range(0, len(words), chunk_size - chunk_overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_content = ' '.join(chunk_words)
            
            if len(chunk_content.strip()) < 50:  # Skip very short chunks
                continue
            
            fragment_id = f"{doc_id}_{version}_{i // (chunk_size - chunk_overlap)}"
            pointer = f"chunk_{i // (chunk_size - chunk_overlap)}"
            
            fragment = DocumentFragment(
                fragment_id=fragment_id,
                doc_id=doc_id,
                version=version,
                content=chunk_content,
                fragment_type="text_chunk",
                pointer=pointer,
                metadata={
                    'document_type': document_type,
                    'chunk_index': i // (chunk_size - chunk_overlap),
                    'word_start': i,
                    'word_end': min(i + chunk_size, len(words)),
                    **metadata
                }
            )
            
            fragments.append(fragment)
        
        return fragments
    
    def search_policy_evidence(self, query: str, case_context: Dict = None,
                              max_results: int = 10, min_relevance: float = 0.7) -> Dict:
        """Search for policy evidence with coverage calculation"""
        try:
            # Prepare search filters
            filters = {}
            if self.allowlist_docs:
                filters['doc_id'] = list(self.allowlist_docs)
            
            # Add case-specific filters if provided
            if case_context:
                if 'insurer_id' in case_context:
                    filters['insurer_id'] = case_context['insurer_id']
                if 'service_code' in case_context:
                    filters['service_code'] = case_context['service_code']
            
            # Search for relevant fragments
            search_results = self.vector_store.search_fragments(
                query=query,
                n_results=max_results * 2,  # Get more results for filtering
                filters=filters,
                include_distances=True
            )
            
            # Filter by relevance threshold
            relevant_fragments = []
            for result in search_results:
                relevance_score = 1.0 - result['distance']  # Convert distance to similarity
                if relevance_score >= min_relevance:
                    result['relevance_score'] = relevance_score
                    relevant_fragments.append(result)
            
            # Limit to max_results
            relevant_fragments = relevant_fragments[:max_results]
            
            # Calculate coverage score
            coverage_score = self._calculate_coverage_score(query, relevant_fragments)
            
            # Identify missing sources
            missing_sources = self._identify_missing_sources(query, case_context)
            
            # Build evidence pack
            evidence_pack = {
                'query': query,
                'fragments': relevant_fragments,
                'coverage_score': coverage_score,
                'missing_sources': missing_sources,
                'search_timestamp': datetime.utcnow().isoformat(),
                'allowlist_validated': bool(self.allowlist_docs)
            }
            
            logger.info(f"Found {len(relevant_fragments)} relevant fragments with coverage {coverage_score:.2f}")
            return evidence_pack
            
        except Exception as e:
            logger.error(f"Failed to search policy evidence: {e}")
            return {
                'query': query,
                'fragments': [],
                'coverage_score': 0.0,
                'missing_sources': [],
                'error': str(e)
            }
    
    def _calculate_coverage_score(self, query: str, fragments: List[Dict]) -> float:
        """Calculate coverage score based on query and retrieved fragments"""
        if not fragments:
            return 0.0
        
        # Simple coverage calculation based on relevance scores
        total_relevance = sum(fragment.get('relevance_score', 0.0) for fragment in fragments)
        max_possible_relevance = len(fragments) * 1.0
        
        # Normalize to 0-1 range
        coverage = min(total_relevance / max_possible_relevance, 1.0) if max_possible_relevance > 0 else 0.0
        
        # Apply penalty for low number of fragments
        fragment_penalty = min(len(fragments) / 5.0, 1.0)  # Assume 5 fragments is ideal
        
        return coverage * fragment_penalty
    
    def _identify_missing_sources(self, query: str, case_context: Dict = None) -> List[str]:
        """Identify potentially missing sources for the query"""
        missing_sources = []
        
        # This is a simplified implementation
        # In practice, this would use more sophisticated analysis
        
        if case_context:
            # Check for service-specific policies
            service_code = case_context.get('service_code')
            if service_code:
                service_fragments = self.vector_store.search_fragments(
                    query=f"service {service_code}",
                    n_results=1,
                    filters={'service_code': service_code}
                )
                if not service_fragments:
                    missing_sources.append(f"service_policy_{service_code}")
            
            # Check for insurer-specific policies
            insurer_id = case_context.get('insurer_id')
            if insurer_id:
                insurer_fragments = self.vector_store.search_fragments(
                    query=f"insurer {insurer_id}",
                    n_results=1,
                    filters={'insurer_id': insurer_id}
                )
                if not insurer_fragments:
                    missing_sources.append(f"insurer_policy_{insurer_id}")
        
        return missing_sources
    
    def get_exact_reference(self, fragment_id: str) -> Optional[Dict]:
        """Get exact reference for a fragment with pointer details"""
        fragment = self.vector_store.get_fragment(fragment_id)
        if not fragment:
            return None
        
        return {
            'fragment_id': fragment_id,
            'doc_id': fragment['metadata']['doc_id'],
            'version': fragment['metadata']['version'],
            'pointer': fragment['metadata']['pointer'],
            'content': fragment['content'],
            'exact_reference': self._build_exact_reference(fragment)
        }
    
    def _build_exact_reference(self, fragment: Dict) -> str:
        """Build exact reference string for citation"""
        metadata = fragment['metadata']
        doc_id = metadata['doc_id']
        version = metadata['version']
        pointer = metadata['pointer']
        
        # Build citation format: "Document_ID v.Version, Section/Page/Chunk"
        return f"{doc_id} v.{version}, {pointer}"
    
    def validate_allowlist(self, doc_ids: List[str]) -> Dict[str, bool]:
        """Validate if documents are in allowlist"""
        if not self.allowlist_docs:
            return {doc_id: True for doc_id in doc_ids}  # No allowlist = all allowed
        
        return {doc_id: doc_id in self.allowlist_docs for doc_id in doc_ids}
    
    def update_allowlist(self, doc_ids: List[str], replace: bool = False):
        """Update allowlist of approved documents"""
        if replace:
            self.allowlist_docs = set(doc_ids)
        else:
            self.allowlist_docs.update(doc_ids)
        
        logger.info(f"Updated allowlist: {len(self.allowlist_docs)} documents")
    
    def get_knowledge_base_stats(self) -> Dict:
        """Get knowledge base statistics"""
        vector_stats = self.vector_store.get_collection_stats()
        
        return {
            **vector_stats,
            'allowlist_size': len(self.allowlist_docs),
            'allowlist_enabled': bool(self.allowlist_docs)
        }


# Factory function for creating knowledge base
def create_knowledge_base(collection_name: str = "policy_documents",
                         persist_directory: str = "data/chromadb",
                         embedding_model: str = "all-MiniLM-L6-v2",
                         allowlist_docs: List[str] = None) -> PolicyKnowledgeBase:
    """Factory function to create policy knowledge base"""
    
    # Create embedding provider
    embedding_provider = EmbeddingProvider(embedding_model)
    
    # Create vector store
    vector_store = ChromaDBVectorStore(
        collection_name=collection_name,
        persist_directory=persist_directory,
        embedding_provider=embedding_provider
    )
    
    # Create knowledge base
    knowledge_base = PolicyKnowledgeBase(
        vector_store=vector_store,
        allowlist_docs=allowlist_docs
    )
    
    return knowledge_base


# Utility functions for document processing
def extract_tables_from_text(content: str) -> List[Dict]:
    """Extract table-like structures from text content"""
    tables = []
    lines = content.split('\n')
    
    current_table = []
    in_table = False
    
    for i, line in enumerate(lines):
        # Simple heuristic: lines with multiple tabs or pipes might be tables
        if '\t' in line or '|' in line:
            if not in_table:
                in_table = True
                current_table = []
            current_table.append(line.strip())
        else:
            if in_table and current_table:
                # End of table
                tables.append({
                    'content': '\n'.join(current_table),
                    'start_line': i - len(current_table),
                    'end_line': i - 1,
                    'pointer': f"table_lines_{i - len(current_table)}_{i - 1}"
                })
                current_table = []
                in_table = False
    
    # Handle table at end of document
    if in_table and current_table:
        tables.append({
            'content': '\n'.join(current_table),
            'start_line': len(lines) - len(current_table),
            'end_line': len(lines) - 1,
            'pointer': f"table_lines_{len(lines) - len(current_table)}_{len(lines) - 1}"
        })
    
    return tables


def create_table_fragments(doc_id: str, version: str, tables: List[Dict],
                          metadata: Dict = None) -> List[DocumentFragment]:
    """Create document fragments from extracted tables"""
    fragments = []
    
    for i, table in enumerate(tables):
        fragment_id = f"{doc_id}_{version}_table_{i}"
        
        fragment = DocumentFragment(
            fragment_id=fragment_id,
            doc_id=doc_id,
            version=version,
            content=table['content'],
            fragment_type="table",
            pointer=table['pointer'],
            metadata={
                'table_index': i,
                'start_line': table['start_line'],
                'end_line': table['end_line'],
                **(metadata or {})
            }
        )
        
        fragments.append(fragment)
    
    return fragments
