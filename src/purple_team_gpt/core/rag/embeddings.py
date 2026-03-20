"""Embedding engine using sentence-transformers or OpenAI."""

import hashlib
import logging
import struct
from enum import Enum
from typing import List, Optional

from purple_team_gpt.config import LLMSettings

logger = logging.getLogger(__name__)


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    LOCAL = "local"
    OPENAI = "openai"


class EmbeddingEngine:
    """Generate embeddings for text using local or cloud models.
    
    Supports:
    - sentence-transformers (local, free)
    - OpenAI embeddings (cloud, requires API key)
    - Mock embeddings (for testing without dependencies)
    """
    
    # Default models for each provider
    DEFAULT_MODELS = {
        EmbeddingProvider.LOCAL: "all-MiniLM-L6-v2",
        EmbeddingProvider.OPENAI: "text-embedding-3-small",
    }
    
    # Embedding dimensions for each provider/model
    MODEL_DIMENSIONS = {
        "all-MiniLM-L6-v2": 384,
        "all-mpnet-base-v2": 768,
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        provider: EmbeddingProvider = EmbeddingProvider.LOCAL,
        openai_api_key: Optional[str] = None,
        llm_settings: Optional[LLMSettings] = None,
    ):
        """Initialize the embedding engine.
        
        Args:
            model_name: Name of the embedding model to use
            provider: Embedding provider (local or openai)
            openai_api_key: OpenAI API key (required if provider is openai)
            llm_settings: LLM settings object (alternative way to provide API key)
        """
        self.provider = provider
        
        # Determine model name
        if model_name is None:
            model_name = self.DEFAULT_MODELS.get(provider, "all-MiniLM-L6-v2")
        self.model_name = model_name
        
        # Get OpenAI API key from settings or parameter
        if llm_settings:
            self.openai_api_key = llm_settings.openai_api_key
        else:
            self.openai_api_key = openai_api_key
        
        # Initialize model
        self._model = None
        self._initialized = False
        
        if provider == EmbeddingProvider.LOCAL:
            self._load_local_model()
        
        logger.info(f"EmbeddingEngine initialized: provider={provider.value}, model={model_name}")
    
    def _load_local_model(self) -> None:
        """Load sentence-transformers model for local embeddings."""
        try:
            from sentence_transformers import SentenceTransformer
            logger.debug(f"Loading sentence-transformers model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            self._initialized = True
            logger.info(f"Successfully loaded local embedding model: {self.model_name}")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers. "
                "Falling back to mock embeddings."
            )
            self._model = None
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to load sentence-transformers model: {e}")
            self._model = None
            self._initialized = True
    
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors (each a list of floats)
        """
        if not texts:
            return []
        
        if self.provider == EmbeddingProvider.OPENAI and self.openai_api_key:
            return await self._embed_openai(texts)
        elif self._model is not None:
            return self._embed_local(texts)
        else:
            return self._embed_mock(texts)
    
    def embed_sync(self, texts: List[str]) -> List[List[float]]:
        """Synchronous embedding generation (for local model only).
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        if self.provider == EmbeddingProvider.OPENAI:
            raise RuntimeError("OpenAI embeddings require async. Use embed() instead.")
        elif self._model is not None:
            return self._embed_local(texts)
        else:
            return self._embed_mock(texts)
    
    def _embed_local(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local sentence-transformers model."""
        if self._model is None:
            return self._embed_mock(texts)
        
        logger.debug(f"Generating local embeddings for {len(texts)} texts")
        embeddings = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.tolist()
    
    async def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        try:
            import openai
        except ImportError:
            logger.error("openai package not installed. Install with: pip install openai")
            return self._embed_mock(texts)
        
        if not self.openai_api_key:
            logger.warning("OpenAI API key not provided, falling back to mock embeddings")
            return self._embed_mock(texts)
        
        logger.debug(f"Generating OpenAI embeddings for {len(texts)} texts using {self.model_name}")
        
        # OpenAI has a limit on batch size, process in chunks if needed
        batch_size = 2048  # OpenAI's recommended batch size
        all_embeddings = []
        
        client = openai.AsyncOpenAI(api_key=self.openai_api_key)
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                response = await client.embeddings.create(
                    model=self.model_name,
                    input=batch,
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"OpenAI embedding API error: {e}")
                # Fall back to mock for this batch
                all_embeddings.extend(self._embed_mock(batch))
        
        return all_embeddings
    
    def _embed_mock(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings for testing without dependencies.
        
        Creates deterministic pseudo-embeddings using SHA-256 hash.
        The embeddings are normalized to unit vectors.
        """
        logger.debug(f"Generating mock embeddings for {len(texts)} texts")
        
        mock_dimension = 128
        embeddings = []
        
        for text in texts:
            # Generate deterministic pseudo-embedding from hash
            h = hashlib.sha256(text.encode()).digest()
            # Create 32 floats from 32 bytes
            embedding = list(struct.unpack(f'{32}f', h))
            # Normalize to unit vector
            norm = sum(x**2 for x in embedding) ** 0.5
            if norm > 0:
                embedding = [x / norm for x in embedding]
            # Pad or truncate to mock dimension
            if len(embedding) < mock_dimension:
                embedding.extend([0.0] * (mock_dimension - len(embedding)))
            else:
                embedding = embedding[:mock_dimension]
            embeddings.append(embedding)
        
        return embeddings
    
    @property
    def dimension(self) -> int:
        """Return the embedding dimension for the current model."""
        # Check known model dimensions
        if self.model_name in self.MODEL_DIMENSIONS:
            return self.MODEL_DIMENSIONS[self.model_name]
        
        # For local models, ask the model directly
        if self._model is not None:
            return self._model.get_sentence_embedding_dimension()
        
        # Default fallback
        return 128
    
    def is_ready(self) -> bool:
        """Check if the embedding engine is ready to generate embeddings."""
        if self.provider == EmbeddingProvider.OPENAI:
            return bool(self.openai_api_key)
        return True  # Local model can always fall back to mock
    
    def __repr__(self) -> str:
        return f"EmbeddingEngine(provider={self.provider.value}, model={self.model_name}, dimension={self.dimension})"


def create_embedding_engine(
    use_openai: bool = False,
    model_name: Optional[str] = None,
    llm_settings: Optional[LLMSettings] = None,
) -> EmbeddingEngine:
    """Create an embedding engine instance.
    
    Args:
        use_openai: Whether to use OpenAI embeddings
        model_name: Specific model name to use
        llm_settings: LLM settings (for API key)
        
    Returns:
        Configured EmbeddingEngine instance
    """
    provider = EmbeddingProvider.OPENAI if use_openai else EmbeddingProvider.LOCAL
    
    if llm_settings is None:
        from purple_team_gpt.config import get_settings
        llm_settings = get_settings().llm
    
    return EmbeddingEngine(
        model_name=model_name,
        provider=provider,
        llm_settings=llm_settings,
    )