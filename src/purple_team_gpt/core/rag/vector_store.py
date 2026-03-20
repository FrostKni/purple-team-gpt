"""ChromaDB vector store for RAG."""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import chromadb
from chromadb.api.types import EmbeddingFunction

from purple_team_gpt.config import ChromaSettings
from purple_team_gpt.core.rag.embeddings import EmbeddingEngine

logger = logging.getLogger(__name__)


class CollectionName(str):
    """Predefined collection names for Purple Team GPT."""
    ATTACK_PATTERNS = "attack_patterns"
    DEFENSE_PATTERNS = "defense_patterns"
    FEEDBACK_STORE = "feedback_store"
    SESSION_LOGS = "session_logs"


class EmbeddingFunctionWrapper(EmbeddingFunction):
    """Wrapper to make EmbeddingEngine compatible with ChromaDB's EmbeddingFunction."""
    
    def __init__(self, engine: EmbeddingEngine):
        self.engine = engine
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        """Generate embeddings (synchronous wrapper)."""
        # Use the synchronous method for local embeddings
        return self.engine.embed_sync(input)


class VectorStore:
    """ChromaDB-based vector store for RAG.
    
    Collections:
    - attack_patterns: Red team attack techniques and patterns
    - defense_patterns: Blue team defense strategies and patterns
    - feedback_store: Feedback from previous operations for learning
    - session_logs: Logs from security testing sessions
    """
    
    # Default collections
    COLLECTIONS = [
        CollectionName.ATTACK_PATTERNS,
        CollectionName.DEFENSE_PATTERNS,
        CollectionName.FEEDBACK_STORE,
        CollectionName.SESSION_LOGS,
    ]
    
    # Similarity threshold for RAG context
    DEFAULT_SIMILARITY_THRESHOLD = 0.5
    
    def __init__(
        self,
        settings: ChromaSettings,
        embedding_engine: EmbeddingEngine,
    ):
        """Initialize the vector store.
        
        Args:
            settings: ChromaDB settings from configuration
            embedding_engine: Engine for generating embeddings
        """
        self.settings = settings
        self.embedding_engine = embedding_engine
        self._client: Optional[chromadb.ClientAPI] = None
        self._collections: Dict[str, chromadb.Collection] = {}
        
        logger.info(f"VectorStore initialized with persist_dir={settings.persist_dir}")
    
    def _get_client(self) -> chromadb.ClientAPI:
        """Get or create ChromaDB client."""
        if self._client is None:
            if self.settings.host == "localhost" or self.settings.host == "127.0.0.1":
                # Local persistent client
                logger.debug(f"Creating persistent ChromaDB client at {self.settings.persist_dir}")
                self._client = chromadb.PersistentClient(
                    path=self.settings.persist_dir,
                )
            else:
                # Remote HTTP client
                logger.debug(f"Creating HTTP ChromaDB client at {self.settings.host}:{self.settings.port}")
                self._client = chromadb.HttpClient(
                    host=self.settings.host,
                    port=self.settings.port,
                )
        return self._client
    
    def get_collection(self, name: str, create_if_missing: bool = True) -> chromadb.Collection:
        """Get or create a collection.
        
        Args:
            name: Collection name
            create_if_missing: Create collection if it doesn't exist
            
        Returns:
            ChromaDB Collection object
        """
        if name not in self._collections:
            client = self._get_client()
            
            if create_if_missing:
                self._collections[name] = client.get_or_create_collection(
                    name=name,
                    metadata={"hnsw:space": "cosine"},
                )
            else:
                self._collections[name] = client.get_collection(name=name)
            
            logger.debug(f"Retrieved collection: {name} with {self._collections[name].count()} documents")
        
        return self._collections[name]
    
    def initialize_collections(self) -> None:
        """Initialize all default collections."""
        for collection_name in self.COLLECTIONS:
            self.get_collection(collection_name)
        logger.info(f"Initialized {len(self.COLLECTIONS)} collections")
    
    async def add(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add documents to a collection.
        
        Args:
            collection_name: Name of the collection
            documents: List of document texts to add
            metadatas: Optional metadata for each document
            ids: Optional IDs for each document (generated if not provided)
            
        Returns:
            List of document IDs
        """
        if not documents:
            return []
        
        collection = self.get_collection(collection_name)
        
        # Generate embeddings
        embeddings = await self.embedding_engine.embed(documents)
        
        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        
        # Ensure metadatas is a list
        if metadatas is None:
            metadatas = [{} for _ in documents]
        
        # Add timestamp to each metadata
        timestamp = datetime.utcnow().isoformat()
        for meta in metadatas:
            if "timestamp" not in meta:
                meta["timestamp"] = timestamp
        
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        
        logger.debug(f"Added {len(documents)} documents to {collection_name}")
        return ids
    
    async def add_single(
        self,
        collection_name: str,
        document: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None,
    ) -> str:
        """Add a single document to a collection.
        
        Args:
            collection_name: Name of the collection
            document: Document text
            metadata: Optional metadata dictionary
            doc_id: Optional document ID
            
        Returns:
            Document ID
        """
        ids = await self.add(
            collection_name=collection_name,
            documents=[document],
            metadatas=[metadata] if metadata else None,
            ids=[doc_id] if doc_id else None,
        )
        return ids[0]
    
    async def query(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query a collection for similar documents.
        
        Args:
            collection_name: Name of the collection
            query_text: Query text string
            n_results: Number of results to return
            where: Metadata filter (e.g., {"severity": "high"})
            where_document: Document content filter
            
        Returns:
            Dictionary with ids, documents, metadatas, and distances
        """
        collection = self.get_collection(collection_name)
        
        # Generate query embedding
        query_embeddings = await self.embedding_engine.embed([query_text])
        if not query_embeddings:
            return {"ids": [], "documents": [], "metadatas": [], "distances": []}
        
        results = collection.query(
            query_embeddings=[query_embeddings[0]],
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=["documents", "metadatas", "distances"],
        )
        
        return {
            "ids": results["ids"][0] if results["ids"] else [],
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
        }
    
    async def query_by_embedding(
        self,
        collection_name: str,
        embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query a collection using a pre-computed embedding.
        
        Args:
            collection_name: Name of the collection
            embedding: Pre-computed embedding vector
            n_results: Number of results to return
            where: Metadata filter
            
        Returns:
            Dictionary with ids, documents, metadatas, and distances
        """
        collection = self.get_collection(collection_name)
        
        results = collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        
        return {
            "ids": results["ids"][0] if results["ids"] else [],
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
        }
    
    async def get_context(
        self,
        query: str,
        collections: Optional[List[str]] = None,
        n_results_per_collection: int = 3,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> str:
        """Get aggregated context from multiple collections for RAG.
        
        Args:
            query: Query text
            collections: List of collections to search (defaults to all)
            n_results_per_collection: Max results per collection
            similarity_threshold: Maximum distance threshold (lower = more similar)
            
        Returns:
            Aggregated context string from all collections
        """
        if collections is None:
            collections = self.COLLECTIONS
        
        contexts = []
        
        for collection_name in collections:
            try:
                results = await self.query(
                    collection_name,
                    query,
                    n_results=n_results_per_collection,
                )
                
                for doc, meta, dist in zip(
                    results["documents"],
                    results["metadatas"],
                    results["distances"],
                ):
                    # Filter by similarity threshold (lower distance = more similar)
                    if dist <= similarity_threshold:
                        source = meta.get("source", "unknown")
                        contexts.append(f"[{collection_name}] ({source}) {doc}")
                        
            except Exception as e:
                logger.debug(f"Query {collection_name} failed: {e}")
        
        return "\n\n".join(contexts) if contexts else ""
    
    async def get_relevant_patterns(
        self,
        query: str,
        pattern_type: str = "attack",
        n_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get relevant patterns from attack or defense collections.
        
        Args:
            query: Query text
            pattern_type: "attack" or "defense"
            n_results: Number of results
            
        Returns:
            List of pattern dictionaries with document, metadata, and similarity
        """
        collection_name = (
            CollectionName.ATTACK_PATTERNS if pattern_type == "attack"
            else CollectionName.DEFENSE_PATTERNS
        )
        
        results = await self.query(collection_name, query, n_results=n_results)
        
        patterns = []
        for doc, meta, dist in zip(
            results["documents"],
            results["metadatas"],
            results["distances"],
        ):
            patterns.append({
                "document": doc,
                "metadata": meta,
                "similarity": 1 - dist,  # Convert distance to similarity
            })
        
        return patterns
    
    async def store_session_log(
        self,
        session_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a session log entry.
        
        Args:
            session_id: Session identifier
            content: Log content
            metadata: Additional metadata
            
        Returns:
            Document ID
        """
        if metadata is None:
            metadata = {}
        metadata["session_id"] = session_id
        
        return await self.add_single(
            collection_name=CollectionName.SESSION_LOGS,
            document=content,
            metadata=metadata,
        )
    
    async def store_feedback(
        self,
        content: str,
        feedback_type: str,
        rating: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store feedback for learning.
        
        Args:
            content: Feedback content
            feedback_type: Type of feedback (e.g., "correction", "approval")
            rating: Optional rating (1-5)
            metadata: Additional metadata
            
        Returns:
            Document ID
        """
        if metadata is None:
            metadata = {}
        metadata["feedback_type"] = feedback_type
        if rating is not None:
            metadata["rating"] = rating
        
        return await self.add_single(
            collection_name=CollectionName.FEEDBACK_STORE,
            document=content,
            metadata=metadata,
        )
    
    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Delete documents from a collection.
        
        Args:
            collection_name: Name of the collection
            ids: List of document IDs to delete
            where: Metadata filter for documents to delete
        """
        collection = self.get_collection(collection_name, create_if_missing=False)
        collection.delete(ids=ids, where=where)
        logger.debug(f"Deleted documents from {collection_name}")
    
    def count(self, collection_name: str) -> int:
        """Get document count in a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Number of documents
        """
        try:
            collection = self.get_collection(collection_name, create_if_missing=False)
            return collection.count()
        except Exception:
            return 0
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics for all collections.
        
        Returns:
            Dictionary with collection names and document counts
        """
        stats = {}
        for collection_name in self.COLLECTIONS:
            stats[collection_name] = self.count(collection_name)
        return stats
    
    def clear_collection(self, collection_name: str) -> None:
        """Clear all documents from a collection.
        
        Args:
            collection_name: Name of the collection to clear
        """
        client = self._get_client()
        try:
            client.delete_collection(collection_name)
            if collection_name in self._collections:
                del self._collections[collection_name]
            logger.info(f"Cleared collection: {collection_name}")
        except Exception as e:
            logger.debug(f"Could not clear collection {collection_name}: {e}")
    
    def __repr__(self) -> str:
        stats = self.get_stats()
        return f"VectorStore(collections={stats})"


def create_vector_store(
    embedding_engine: Optional[EmbeddingEngine] = None,
    settings: Optional[ChromaSettings] = None,
) -> VectorStore:
    """Create a vector store instance.
    
    Args:
        embedding_engine: Embedding engine (created if not provided)
        settings: ChromaDB settings (uses defaults if not provided)
        
    Returns:
        Configured VectorStore instance
    """
    if settings is None:
        from purple_team_gpt.config import get_settings
        settings = get_settings().chroma
    
    if embedding_engine is None:
        from purple_team_gpt.core.rag.embeddings import create_embedding_engine
        embedding_engine = create_embedding_engine()
    
    return VectorStore(settings=settings, embedding_engine=embedding_engine)