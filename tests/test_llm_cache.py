"""Tests for LLM response caching."""

import asyncio
import time

import pytest

from purple_team_gpt.core.llm.cache import CachedResponse, SemanticCache


class TestSemanticCache:
    """Test suite for SemanticCache."""

    def test_cached_response_is_expired(self):
        """Test that expired responses are detected correctly."""
        # Create a response with a very short TTL
        cached = CachedResponse(
            prompt_hash="test_hash",
            prompt="test prompt",
            embedding=[0.1, 0.2, 0.3],
            response="test response",
            created_at=time.time() - 10,  # Created 10 seconds ago
            ttl=5,  # TTL is 5 seconds
        )

        assert cached.is_expired() is True

    def test_cached_response_not_expired(self):
        """Test that non-expired responses are detected correctly."""
        cached = CachedResponse(
            prompt_hash="test_hash",
            prompt="test prompt",
            embedding=[0.1, 0.2, 0.3],
            response="test response",
            created_at=time.time(),
            ttl=3600,
        )

        assert cached.is_expired() is False

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss when prompt is not in cache."""
        cache = SemanticCache()

        result = await cache.get_cached("new prompt", embedding=[0.1, 0.2])

        assert result is None
        assert cache.size == 0

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test cache hit when prompt is cached."""
        cache = SemanticCache()
        prompt = "test prompt"
        response = "test response"

        # Cache the response
        await cache.cache_response(prompt, embedding=[0.1, 0.2], response=response)

        # Retrieve it
        result = await cache.get_cached(prompt, embedding=[0.1, 0.2])

        assert result == response
        assert cache.size == 1

    @pytest.mark.asyncio
    async def test_cache_expiry(self):
        """Test that expired cache entries are not returned."""
        cache = SemanticCache(ttl=1)  # 1 second TTL
        prompt = "test prompt"
        response = "test response"

        # Cache the response
        await cache.cache_response(prompt, embedding=[0.1, 0.2], response=response)

        # Wait for it to expire
        await asyncio.sleep(1.5)

        # Try to retrieve it - should return None
        result = await cache.get_cached(prompt, embedding=[0.1, 0.2])

        assert result is None
        assert cache.size == 0  # Expired entry should be removed

    @pytest.mark.asyncio
    async def test_cache_clear_expired(self):
        """Test clearing expired cache entries."""
        cache = SemanticCache(ttl=1)

        # Cache multiple responses
        await cache.cache_response("prompt1", embedding=[0.1], response="response1")
        await cache.cache_response("prompt2", embedding=[0.2], response="response2")

        # Wait for them to expire
        await asyncio.sleep(1.5)

        # Add a fresh one
        await cache.cache_response("prompt3", embedding=[0.3], response="response3")

        # Clear expired
        expired_count = await cache.clear_expired()

        assert expired_count == 2
        assert cache.size == 1

    @pytest.mark.asyncio
    async def test_cache_max_size_lru_eviction(self):
        """Test LRU eviction when cache reaches max size."""
        cache = SemanticCache(max_size=3)

        # Add 3 entries
        await cache.cache_response("prompt1", embedding=[0.1], response="response1")
        await cache.cache_response("prompt2", embedding=[0.2], response="response2")
        await cache.cache_response("prompt3", embedding=[0.3], response="response3")

        assert cache.size == 3

        # Add one more - should evict oldest
        await cache.cache_response("prompt4", embedding=[0.4], response="response4")

        assert cache.size == 3

        # First prompt should be evicted
        result = await cache.get_cached("prompt1", embedding=[0.1])
        assert result is None

        # Others should still be there
        result = await cache.get_cached("prompt2", embedding=[0.2])
        assert result == "response2"

    @pytest.mark.asyncio
    async def test_cache_same_prompt_overwrites(self):
        """Test that caching the same prompt overwrites the old entry."""
        cache = SemanticCache()
        prompt = "test prompt"

        # Cache first response
        await cache.cache_response(prompt, embedding=[0.1], response="response1")

        # Cache again with same prompt
        await cache.cache_response(prompt, embedding=[0.1], response="response2")

        # Should only have one entry
        assert cache.size == 1

        # Should return the latest response
        result = await cache.get_cached(prompt, embedding=[0.1])
        assert result == "response2"

    @pytest.mark.asyncio
    async def test_cache_with_none_embedding(self):
        """Test that cache works with None embedding."""
        cache = SemanticCache()
        prompt = "test prompt"

        # Cache without embedding
        await cache.cache_response(prompt, embedding=None, response="response")

        # Retrieve it
        result = await cache.get_cached(prompt, embedding=None)

        assert result == "response"

    @pytest.mark.asyncio
    async def test_cache_different_prompts_different_hashes(self):
        """Test that different prompts get different cache entries."""
        cache = SemanticCache()

        await cache.cache_response("prompt1", embedding=[0.1], response="response1")
        await cache.cache_response("prompt2", embedding=[0.2], response="response2")

        assert cache.size == 2

        result1 = await cache.get_cached("prompt1", embedding=[0.1])
        result2 = await cache.get_cached("prompt2", embedding=[0.2])

        assert result1 == "response1"
        assert result2 == "response2"
