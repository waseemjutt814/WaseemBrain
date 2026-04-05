from __future__ import annotations

import hashlib
import math
from collections import OrderedDict
from typing import ClassVar, Protocol, cast

from ..types import SYSTEM, EmbeddingVector


class _SentenceTransformerModel(Protocol):
    def encode(
        self, text: str, *, normalize_embeddings: bool
    ) -> list[float] | tuple[float, ...]: ...


class MemoryEmbedder:
    _model: ClassVar[_SentenceTransformerModel | None] = None
    _loaded_model_name: ClassVar[str | None] = None
    _cache: ClassVar[OrderedDict[str, EmbeddingVector]] = OrderedDict()

    def __init__(
        self,
        backend_preference: str = "auto",
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self._backend_preference = backend_preference
        self._model_name = model_name
        self._backend_name = "hash"

    def embed(self, text: str) -> EmbeddingVector:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        cached = self._cache.get(key)
        if cached is not None:
            self._cache.move_to_end(key)
            return cached

        vector = self._embed_with_backend(text)
        self._cache[key] = vector
        if len(self._cache) > 10_000:
            self._cache.clear()
        return vector

    def embed_batch(self, texts: list[str]) -> list[EmbeddingVector]:
        return [self.embed(text) for text in texts]

    def backend_name(self) -> str:
        return self._backend_name

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
