from __future__ import annotations

import hashlib
import math
import threading
from collections import OrderedDict
from typing import ClassVar, Protocol, cast

from ..types import SYSTEM, EmbeddingVector

# Cache settings
_CACHE_MAX_SIZE = 1000  # LRU cache max entries
_CACHE_KEY_LENGTH = 16  # Truncated hash for key


class _SentenceTransformerModel(Protocol):
    def encode(
        self, text: str, *, normalize_embeddings: bool
    ) -> list[float] | tuple[float, ...]: ...


class MemoryEmbedder:
    """Memory embedder with LRU cache and metrics tracking."""
    _model: ClassVar[_SentenceTransformerModel | None] = None
    _loaded_model_name: ClassVar[str | None] = None
    _cache: ClassVar[OrderedDict[str, EmbeddingVector]] = OrderedDict()
    _cache_lock: ClassVar[threading.Lock] = threading.Lock()
    _cache_hits: ClassVar[int] = 0
    _cache_misses: ClassVar[int] = 0
    _cache_max_size: ClassVar[int] = _CACHE_MAX_SIZE

    def __init__(
        self,
        backend_preference: str = "auto",
        model_name: str = "all-MiniLM-L6-v2",
        cache_max_size: int | None = None,
    ) -> None:
        self._backend_preference = backend_preference
        self._model_name = model_name
        self._backend_name = "hash"
        if cache_max_size is not None:
            MemoryEmbedder._cache_max_size = cache_max_size

    def embed(self, text: str) -> EmbeddingVector:
        """Embed text with LRU caching for efficiency."""
        # Use truncated hash for cache key (saves memory)
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()[:_CACHE_KEY_LENGTH]
        
        with self._cache_lock:
            cached = self._cache.get(key)
            if cached is not None:
                self._cache.move_to_end(key)
                self.__class__._cache_hits += 1
                return cached
        
        # Compute embedding outside lock
        vector = self._embed_with_backend(text)
        
        with self._cache_lock:
            # Check again in case another thread added it
            if key in self._cache:
                return self._cache[key]
            
            self._cache[key] = vector
            self.__class__._cache_misses += 1
            
            # LRU eviction: remove oldest entries if over limit
            while len(self._cache) > self._cache_max_size:
                self._cache.popitem(last=False)
        
        return vector

    def embed_batch(self, texts: list[str]) -> list[EmbeddingVector]:
        """Embed multiple texts efficiently using batch processing if available."""
        if not texts:
            return []
        
        # Check cache for all texts first
        results: list[EmbeddingVector | None] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []
        
        with self._cache_lock:
            for idx, text in enumerate(texts):
                key = hashlib.sha256(text.encode("utf-8")).hexdigest()[:_CACHE_KEY_LENGTH]
                cached = self._cache.get(key)
                if cached is not None:
                    self._cache.move_to_end(key)
                    self.__class__._cache_hits += 1
                    results[idx] = cached
                else:
                    uncached_indices.append(idx)
                    uncached_texts.append(text)
        
        # Batch compute uncached embeddings
        if uncached_texts:
            # Try batch embedding with sentence-transformers
            if self._backend_preference != "hash" and self._model is not None:
                try:
                    batch_embeddings = self._model.encode(uncached_texts, normalize_embeddings=True)
                    for i, (idx, embedding) in enumerate(zip(uncached_indices, batch_embeddings)):
                        vector = EmbeddingVector(float(v) for v in embedding)
                        results[idx] = vector
                        key = hashlib.sha256(uncached_texts[i].encode("utf-8")).hexdigest()[:_CACHE_KEY_LENGTH]
                        with self._cache_lock:
                            self._cache[key] = vector
                            self.__class__._cache_misses += 1
                            while len(self._cache) > self._cache_max_size:
                                self._cache.popitem(last=False)
                    return [r for r in results if r is not None]
                except Exception:
                    pass  # Fall back to individual embedding
            
            # Individual embedding fallback
            for idx, text in zip(uncached_indices, uncached_texts):
                results[idx] = self.embed(text)
        
        
        return [r for r in results if r is not None]

    def backend_name(self) -> str:
        return self._backend_name
    
    @classmethod
    def cache_stats(cls) -> dict[str, int | float]:
        """Return cache statistics for monitoring."""
        with cls._cache_lock:
            total_requests = cls._cache_hits + cls._cache_misses
            hit_rate = cls._cache_hits / total_requests if total_requests > 0 else 0.0
            return {
                "cache_size": len(cls._cache),
                "cache_max_size": cls._cache_max_size,
                "cache_hits": cls._cache_hits,
                "cache_misses": cls._cache_misses,
                "hit_rate": hit_rate,
            }
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear the embedding cache."""
        with cls._cache_lock:
            cls._cache.clear()
            cls._cache_hits = 0
            cls._cache_misses = 0

    def _embed_with_backend(self, text: str) -> EmbeddingVector:
        if self._backend_preference == "hash":
            self._backend_name = "hash"
            return self._hash_embed(text)
        try:
            from sentence_transformers import SentenceTransformer
        except Exception:
            self._backend_name = "hash"
            return self._hash_embed(text)

        if (
            self.__class__._model is None
            or self.__class__._loaded_model_name != self._model_name
        ):
            try:
                self.__class__._model = cast(
                    _SentenceTransformerModel,
                    SentenceTransformer(self._model_name),
                )
                self.__class__._loaded_model_name = self._model_name
            except Exception:
                self.__class__._model = None
                self.__class__._loaded_model_name = None
                self._backend_name = "hash"
                return self._hash_embed(text)
        model = self.__class__._model
        if model is None:
            self._backend_name = "hash"
            return self._hash_embed(text)
        try:
            embedding = model.encode(text, normalize_embeddings=True)
        except Exception:
            self._backend_name = "hash"
            return self._hash_embed(text)
        self._backend_name = "sentence-transformers"
        return EmbeddingVector(float(value) for value in embedding)

    def _hash_embed(self, text: str) -> EmbeddingVector:
        dimensions = SYSTEM.embedding_dimensions
        vector = [0.0] * dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index in range(0, len(digest), 2):
                bucket = digest[index] % dimensions
                direction = -1.0 if digest[index + 1] % 2 else 1.0
                vector[bucket] += direction
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return EmbeddingVector(value / norm for value in vector)
