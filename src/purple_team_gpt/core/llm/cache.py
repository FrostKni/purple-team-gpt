"""Response caching for LLM API calls."""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CachedResponse:
    """Cached LLM response."""

    prompt_hash: str
    prompt: str
    embedding: List[float]
    response: str
    created_at: float = field(default_factory=time.time)
    ttl: int = 3600

    def is_expired(self) -> bool:
        """Check if this cached response has expired."""
        return time.time() - self.created_at > self.ttl


class SemanticCache:
    """Cache LLM responses by prompt similarity."""

    def __init__(self, similarity_threshold: float = 0.95, ttl: int = 3600, max_size: int = 1000):
        """Initialize the semantic cache.

        Args:
            similarity_threshold: Threshold for semantic similarity matching (not used in current impl)
            ttl: Time-to-live in seconds for cached responses
            max_size: Maximum number of cached responses
        """
        self.similarity_threshold = similarity_threshold
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, CachedResponse] = {}

    def _hash_prompt(self, prompt: str) -> str:
        """Generate a hash for the prompt.

        Args:
            prompt: The prompt text

        Returns:
            A hash string for the prompt
        """
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    async def get_cached(
        self, prompt: str, embedding: Optional[List[float]] = None
    ) -> Optional[str]:
        """Return cached response if available and not expired.

        Args:
            prompt: The prompt text
            embedding: Optional embedding for semantic matching (not used in current impl)

        Returns:
            The cached response if found and not expired, None otherwise
        """
        prompt_hash = self._hash_prompt(prompt)
        cached = self._cache.get(prompt_hash)

        if cached is None:
            return None

        if cached.is_expired():
            del self._cache[prompt_hash]
            return None

        logger.debug(f"Cache hit for prompt: {prompt[:50]}...")
        return cached.response

    async def cache_response(
        self, prompt: str, embedding: Optional[List[float]], response: str
    ) -> None:
        """Store response in cache.

        Args:
            prompt: The prompt text
            embedding: Optional embedding for semantic matching (not used in current impl)
            response: The response to cache
        """
        if len(self._cache) >= self.max_size:
            self._evict_oldest()

        prompt_hash = self._hash_prompt(prompt)
        self._cache[prompt_hash] = CachedResponse(
            prompt_hash=prompt_hash,
            prompt=prompt,
            embedding=embedding or [],
            response=response,
            ttl=self.ttl,
        )
        logger.debug(f"Cached response for prompt: {prompt[:50]}...")

    def _evict_oldest(self) -> None:
        """Evict the oldest cached entry."""
        if not self._cache:
            return
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]

    async def clear_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of expired entries removed
        """
        expired = [k for k, v in self._cache.items() if v.is_expired()]
        for k in expired:
            del self._cache[k]
        return len(expired)

    @property
    def size(self) -> int:
        """Return current cache size."""
        return len(self._cache)
