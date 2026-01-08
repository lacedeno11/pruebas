"""
Knowledge Base Interface

This module implements knowledge base interfaces for policy document retrieval
and vector search, supporting multiple vector database backends.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class VectorBackend(str, Enum):
    """Vector database backend types"""
    CHROMADB = "chromadb"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    QDRANT = "qdrant"


@dataclass
class VectorSearchConfig:
    """Vector search configuration"""
    backend: VectorBackend
    collection_name: str
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimension: int = 384
    similarity_metric: str = "cosine"
    api_key: Optional[str] = None
    endpoint_url: Optional[str] = None
    index_name: Optional[str] = None
    environment: Optional[str] = None


@dataclass
class Document:
    """Document metadata and content"""
    doc_id: str
    title: str
    content: str
    version: str
    checksum: str
    document_type: str
    source: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
    tags: List[str]
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """Vector search result"""
    document: Document
    score: float
    excerpt: str
    relevance_score: float
    confidence_score: float


@dataclass
class SearchQuery:
    """Search query parameters"""
    query_text: str
    filters: Optional[Dict[str, Any]] = None
    top_k: int = 10
    score_threshold: float = 0.7
    include_metadata: bool = True


class KnowledgeBaseInterface(ABC):
    """Abstract interface for knowledge base operations"""
    
    def __init__(self, config: VectorSearchConfig):
        self.config = config
        self.stats = {
            "searches": 0,
            "documents_indexed": 0,
            "documents_retrieved": 0,
            "avg_search_time_ms": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    @abstractmethod
    async def index_document(self, document: Document) -> bool:
        """Index document in knowledge base"""
        pass
    
    @abstractmethod
    async def search_documents(self, query: SearchQuery) -> List[SearchResult]:
        """Search documents by vector similarity"""
        pass
    
    @abstractmethod
    async def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document by ID"""
        pass
    
    @abstractmethod
    async def update_document(self, document: Document) -> bool:
        """Update existing document"""
        pass
    
    @abstractmethod
    async def delete_document(self, doc_id: str) -> bool:
        """Delete document from knowledge base"""
        pass
    
    @abstractmethod
    async def list_documents(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Document]:
        """List documents with optional filters"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check knowledge base health"""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        return self.stats.copy()
    
    def _update_search_stats(self, search_time_ms: int) -> None:
        """Update search statistics"""
        self.stats["searches"] += 1
        
        # Update average search time
        current_avg = self.stats["avg_search_time_ms"]
        total_searches = self.stats["searches"]
        new_avg = ((current_avg * (total_searches - 1)) + search_time_ms) / total_searches
        self.stats["avg_search_time_ms"] = int(new_avg)


class ChromaDBAdapter(KnowledgeBaseInterface):
    """
    ChromaDB adapter for vector search.
    
    Provides local and cloud-based vector search using ChromaDB.
    """
    
    def __init__(self, config: VectorSearchConfig):
        super().__init__(config)
        
        if config.backend != VectorBackend.CHROMADB:
            raise ValueError("ChromaDBAdapter requires CHROMADB backend configuration")
        
        self.client = None
        self.collection = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize ChromaDB client"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            if self.config.endpoint_url:
                # Remote ChromaDB instance
                self.client = chromadb.HttpClient(
                    host=self.config.endpoint_url.split("://")[1].split(":")[0],
                    port=int(self.config.endpoint_url.split(":")[-1]) if ":" in self.config.endpoint_url.split("://")[1] else 8000
                )
            else:
                # Local ChromaDB instance
                self.client = chromadb.Client(Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory="./chroma_db"
                ))
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.config.collection_name,
                metadata={"hnsw:space": self.config.similarity_metric}
            )
            
            logger.info(f"ChromaDB client initialized for collection: {self.config.collection_name}")
            
        except ImportError:
            logger.error("ChromaDB not installed. Install with: pip install chromadb")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise
    
    async def index_document(self, document: Document) -> bool:
        """Index document in ChromaDB"""
        try:
            # Generate embedding if not provided
            if not document.embedding:
                document.embedding = await self._generate_embedding(document.content)
            
            # Prepare metadata
            metadata = {
                "title": document.title,
                "version": document.version,
                "checksum": document.checksum,
                "document_type": document.document_type,
                "source": document.source,
                "created_at": document.created_at.isoformat(),
                "updated_at": document.updated_at.isoformat(),
                **document.metadata
            }
            
            # Add document to collection
            self.collection.add(
                ids=[document.doc_id],
                embeddings=[document.embedding],
                documents=[document.content],
                metadatas=[metadata]
            )
            
            self.stats["documents_indexed"] += 1
            logger.info(f"Document indexed in ChromaDB: {document.doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index document in ChromaDB: {e}")
            return False
    
    async def search_documents(self, query: SearchQuery) -> List[SearchResult]:
        """Search documents in ChromaDB"""
        start_time = datetime.utcnow()
        
        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query.query_text)
            
            # Prepare where clause for filters
            where_clause = None
            if query.filters:
                where_clause = query.filters
            
            # Search collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=query.top_k,
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
            
            # Process results
            search_results = []
            
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i]
                    score = 1 - distance  # Convert distance to similarity score
                    
                    if score < query.score_threshold:
                        continue
                    
                    metadata = results["metadatas"][0][i]
                    content = results["documents"][0][i]
                    
                    # Create document object
                    document = Document(
                        doc_id=doc_id,
                        title=metadata.get("title", ""),
                        content=content,
                        version=metadata.get("version", ""),
                        checksum=metadata.get("checksum", ""),
                        document_type=metadata.get("document_type", ""),
                        source=metadata.get("source", ""),
                        created_at=datetime.fromisoformat(metadata.get("created_at", datetime.utcnow().isoformat())),
                        updated_at=datetime.fromisoformat(metadata.get("updated_at", datetime.utcnow().isoformat())),
                        metadata={k: v for k, v in metadata.items() if k not in [
                            "title", "version", "checksum", "document_type", "source", "created_at", "updated_at"
                        ]},
                        tags=metadata.get("tags", [])
                    )
                    
                    # Generate excerpt
                    excerpt = self._generate_excerpt(content, query.query_text)
                    
                    search_result = SearchResult(
                        document=document,
                        score=score,
                        excerpt=excerpt,
                        relevance_score=score,
                        confidence_score=min(score * 1.2, 1.0)  # Boost confidence slightly
                    )
                    
                    search_results.append(search_result)
            
            # Update statistics
            search_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._update_search_stats(int(search_time))
            self.stats["documents_retrieved"] += len(search_results)
            
            logger.info(f"ChromaDB search completed: {len(search_results)} results in {search_time:.2f}ms")
            
            return search_results
            
        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
            return []
    
    async def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document by ID from ChromaDB"""
        try:
            results = self.collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"]
            )
            
            if not results["ids"] or not results["ids"]:
                return None
            
            metadata = results["metadatas"][0]
            content = results["documents"][0]
            
            document = Document(
                doc_id=doc_id,
                title=metadata.get("title", ""),
                content=content,
                version=metadata.get("version", ""),
                checksum=metadata.get("checksum", ""),
                document_type=metadata.get("document_type", ""),
                source=metadata.get("source", ""),
                created_at=datetime.fromisoformat(metadata.get("created_at", datetime.utcnow().isoformat())),
                updated_at=datetime.fromisoformat(metadata.get("updated_at", datetime.utcnow().isoformat())),
                metadata={k: v for k, v in metadata.items() if k not in [
                    "title", "version", "checksum", "document_type", "source", "created_at", "updated_at"
                ]},
                tags=metadata.get("tags", [])
            )
            
            return document
            
        except Exception as e:
            logger.error(f"Failed to get document from ChromaDB: {e}")
            return None
    
    async def update_document(self, document: Document) -> bool:
        """Update document in ChromaDB"""
        try:
            # Delete existing document
            await self.delete_document(document.doc_id)
            
            # Re-index updated document
            return await self.index_document(document)
            
        except Exception as e:
            logger.error(f"Failed to update document in ChromaDB: {e}")
            return False
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete document from ChromaDB"""
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"Document deleted from ChromaDB: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document from ChromaDB: {e}")
            return False
    
    async def list_documents(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Document]:
        """List documents in ChromaDB"""
        try:
            results = self.collection.get(
                where=filters,
                limit=limit,
                include=["documents", "metadatas"]
            )
            
            documents = []
            
            if results["ids"]:
                for i, doc_id in enumerate(results["ids"]):
                    metadata = results["metadatas"][i]
                    content = results["documents"][i]
                    
                    document = Document(
                        doc_id=doc_id,
                        title=metadata.get("title", ""),
                        content=content,
                        version=metadata.get("version", ""),
                        checksum=metadata.get("checksum", ""),
                        document_type=metadata.get("document_type", ""),
                        source=metadata.get("source", ""),
                        created_at=datetime.fromisoformat(metadata.get("created_at", datetime.utcnow().isoformat())),
                        updated_at=datetime.fromisoformat(metadata.get("updated_at", datetime.utcnow().isoformat())),
                        metadata={k: v for k, v in metadata.items() if k not in [
                            "title", "version", "checksum", "document_type", "source", "created_at", "updated_at"
                        ]},
                        tags=metadata.get("tags", [])
                    )
                    
                    documents.append(document)
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to list documents from ChromaDB: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Check ChromaDB health"""
        try:
            # Try to get collection info
            collection_count = self.collection.count()
            
            return {
                "status": "healthy",
                "backend": "chromadb",
                "collection": self.config.collection_name,
                "document_count": collection_count,
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "chromadb",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        try:
            # Use sentence-transformers for embedding generation
            from sentence_transformers import SentenceTransformer
            
            # Load model (would cache in production)
            model = SentenceTransformer(self.config.embedding_model)
            
            # Generate embedding
            embedding = model.encode(text)
            
            return embedding.tolist()
            
        except ImportError:
            logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
            # Return dummy embedding for testing
            return [0.0] * self.config.dimension
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return [0.0] * self.config.dimension
    
    def _generate_excerpt(self, content: str, query: str, max_length: int = 200) -> str:
        """Generate relevant excerpt from content"""
        try:
            # Simple excerpt generation - find query terms in content
            query_terms = query.lower().split()
            content_lower = content.lower()
            
            # Find best position for excerpt
            best_pos = 0
            best_score = 0
            
            for i in range(0, len(content) - max_length, 50):
                excerpt_text = content[i:i + max_length].lower()
                score = sum(1 for term in query_terms if term in excerpt_text)
                
                if score > best_score:
                    best_score = score
                    best_pos = i
            
            # Extract excerpt
            excerpt = content[best_pos:best_pos + max_length]
            
            # Clean up excerpt boundaries
            if best_pos > 0:
                excerpt = "..." + excerpt
            if best_pos + max_length < len(content):
                excerpt = excerpt + "..."
            
            return excerpt.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate excerpt: {e}")
            return content[:max_length] + "..." if len(content) > max_length else content


class PineconeAdapter(KnowledgeBaseInterface):
    """
    Pinecone adapter for vector search.
    
    Provides cloud-based vector search using Pinecone.
    """
    
    def __init__(self, config: VectorSearchConfig):
        super().__init__(config)
        
        if config.backend != VectorBackend.PINECONE:
            raise ValueError("PineconeAdapter requires PINECONE backend configuration")
        
        self.index = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Pinecone client"""
        try:
            import pinecone
            
            # Initialize Pinecone
            pinecone.init(
                api_key=self.config.api_key,
                environment=self.config.environment
            )
            
            # Connect to index
            self.index = pinecone.Index(self.config.index_name)
            
            logger.info(f"Pinecone client initialized for index: {self.config.index_name}")
            
        except ImportError:
            logger.error("Pinecone not installed. Install with: pip install pinecone-client")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone client: {e}")
            raise
    
    async def index_document(self, document: Document) -> bool:
        """Index document in Pinecone"""
        try:
            # Generate embedding if not provided
            if not document.embedding:
                document.embedding = await self._generate_embedding(document.content)
            
            # Prepare metadata
            metadata = {
                "title": document.title,
                "content": document.content[:1000],  # Pinecone metadata size limit
                "version": document.version,
                "checksum": document.checksum,
                "document_type": document.document_type,
                "source": document.source,
                "created_at": document.created_at.isoformat(),
                "updated_at": document.updated_at.isoformat()
            }
            
            # Upsert to Pinecone
            self.index.upsert(
                vectors=[(document.doc_id, document.embedding, metadata)]
            )
            
            self.stats["documents_indexed"] += 1
            logger.info(f"Document indexed in Pinecone: {document.doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index document in Pinecone: {e}")
            return False
    
    async def search_documents(self, query: SearchQuery) -> List[SearchResult]:
        """Search documents in Pinecone"""
        start_time = datetime.utcnow()
        
        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query.query_text)
            
            # Search Pinecone
            search_response = self.index.query(
                vector=query_embedding,
                top_k=query.top_k,
                include_metadata=True,
                filter=query.filters
            )
            
            # Process results
            search_results = []
            
            for match in search_response.matches:
                score = match.score
                
                if score < query.score_threshold:
                    continue
                
                metadata = match.metadata
                
                # Create document object
                document = Document(
                    doc_id=match.id,
                    title=metadata.get("title", ""),
                    content=metadata.get("content", ""),
                    version=metadata.get("version", ""),
                    checksum=metadata.get("checksum", ""),
                    document_type=metadata.get("document_type", ""),
                    source=metadata.get("source", ""),
                    created_at=datetime.fromisoformat(metadata.get("created_at", datetime.utcnow().isoformat())),
                    updated_at=datetime.fromisoformat(metadata.get("updated_at", datetime.utcnow().isoformat())),
                    metadata={},
                    tags=[]
                )
                
                # Generate excerpt
                excerpt = self._generate_excerpt(document.content, query.query_text)
                
                search_result = SearchResult(
                    document=document,
                    score=score,
                    excerpt=excerpt,
                    relevance_score=score,
                    confidence_score=score
                )
                
                search_results.append(search_result)
            
            # Update statistics
            search_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._update_search_stats(int(search_time))
            self.stats["documents_retrieved"] += len(search_results)
            
            logger.info(f"Pinecone search completed: {len(search_results)} results in {search_time:.2f}ms")
            
            return search_results
            
        except Exception as e:
            logger.error(f"Pinecone search failed: {e}")
            return []
    
    async def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document by ID from Pinecone"""
        try:
            response = self.index.fetch(ids=[doc_id])
            
            if doc_id not in response.vectors:
                return None
            
            vector_data = response.vectors[doc_id]
            metadata = vector_data.metadata
            
            document = Document(
                doc_id=doc_id,
                title=metadata.get("title", ""),
                content=metadata.get("content", ""),
                version=metadata.get("version", ""),
                checksum=metadata.get("checksum", ""),
                document_type=metadata.get("document_type", ""),
                source=metadata.get("source", ""),
                created_at=datetime.fromisoformat(metadata.get("created_at", datetime.utcnow().isoformat())),
                updated_at=datetime.fromisoformat(metadata.get("updated_at", datetime.utcnow().isoformat())),
                metadata={},
                tags=[],
                embedding=vector_data.values
            )
            
            return document
            
        except Exception as e:
            logger.error(f"Failed to get document from Pinecone: {e}")
            return None
    
    async def update_document(self, document: Document) -> bool:
        """Update document in Pinecone"""
        # Pinecone upsert handles both insert and update
        return await self.index_document(document)
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete document from Pinecone"""
        try:
            self.index.delete(ids=[doc_id])
            logger.info(f"Document deleted from Pinecone: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document from Pinecone: {e}")
            return False
    
    async def list_documents(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Document]:
        """List documents in Pinecone (limited functionality)"""
        logger.warning("Pinecone does not support efficient document listing")
        return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Pinecone health"""
        try:
            # Try to get index stats
            stats = self.index.describe_index_stats()
            
            return {
                "status": "healthy",
                "backend": "pinecone",
                "index": self.config.index_name,
                "dimension": stats.dimension,
                "total_vector_count": stats.total_vector_count,
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "pinecone",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        try:
            from sentence_transformers import SentenceTransformer
            
            model = SentenceTransformer(self.config.embedding_model)
            embedding = model.encode(text)
            
            return embedding.tolist()
            
        except ImportError:
            logger.error("sentence-transformers not installed")
            return [0.0] * self.config.dimension
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return [0.0] * self.config.dimension
    
    def _generate_excerpt(self, content: str, query: str, max_length: int = 200) -> str:
        """Generate relevant excerpt from content"""
        # Same implementation as ChromaDB adapter
        try:
            query_terms = query.lower().split()
            content_lower = content.lower()
            
            best_pos = 0
            best_score = 0
            
            for i in range(0, len(content) - max_length, 50):
                excerpt_text = content[i:i + max_length].lower()
                score = sum(1 for term in query_terms if term in excerpt_text)
                
                if score > best_score:
                    best_score = score
                    best_pos = i
            
            excerpt = content[best_pos:best_pos + max_length]
            
            if best_pos > 0:
                excerpt = "..." + excerpt
            if best_pos + max_length < len(content):
                excerpt = excerpt + "..."
            
            return excerpt.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate excerpt: {e}")
            return content[:max_length] + "..." if len(content) > max_length else content


# Factory functions

def create_knowledge_base(config: VectorSearchConfig) -> KnowledgeBaseInterface:
    """
    Factory function to create knowledge base adapter.
    
    Args:
        config: Vector search configuration
        
    Returns:
        Knowledge base adapter instance
    """
    if config.backend == VectorBackend.CHROMADB:
        return ChromaDBAdapter(config)
    elif config.backend == VectorBackend.PINECONE:
        return PineconeAdapter(config)
    else:
        raise ValueError(f"Unsupported vector backend: {config.backend}")


def create_chromadb_knowledge_base(
    collection_name: str = "policy_documents",
    endpoint_url: Optional[str] = None
) -> ChromaDBAdapter:
    """Create ChromaDB knowledge base adapter"""
    config = VectorSearchConfig(
        backend=VectorBackend.CHROMADB,
        collection_name=collection_name,
        endpoint_url=endpoint_url
    )
    return ChromaDBAdapter(config)


def create_pinecone_knowledge_base(
    index_name: str,
    api_key: str,
    environment: str,
    dimension: int = 384
) -> PineconeAdapter:
    """Create Pinecone knowledge base adapter"""
    config = VectorSearchConfig(
        backend=VectorBackend.PINECONE,
        collection_name="",  # Not used for Pinecone
        index_name=index_name,
        api_key=api_key,
        environment=environment,
        dimension=dimension
    )
    return PineconeAdapter(config)
