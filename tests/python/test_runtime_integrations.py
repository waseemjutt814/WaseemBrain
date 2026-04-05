from __future__ import annotations

import asyncio
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from typing import cast

from brain.experts.expert import Expert
from brain.internet.fetcher import ContentFetcher
from brain.learning.corrector import ExpertCorrector
from brain.memory.embedder import MemoryEmbedder
from brain.memory.vector_store import ChromaVectorStore
from brain.normalizer.url_adapter import UrlAdapter
from brain.normalizer.voice_adapter import VoiceAdapter
from brain.types import EmbeddingVector, ExpertId, MemoryNodeId, SessionId
from tests.python.support import make_settings


class _FakeEmbedder:
    def embed(self, text: str) -> EmbeddingVector:
        if "capital" in text.lower():
            return EmbeddingVector([1.0, 0.0, 0.0])
        return EmbeddingVector([0.0, 1.0, 0.0])


class _FakeCollection:
    def __init__(self) -> None:
        self._records: dict[str, dict[str, object]] = {}

    def upsert(
        self,
        *,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, object]],
    ) -> None:
        for node_id, document, embedding, metadata in zip(
            ids, documents, embeddings, metadatas, strict=True
        ):
            self._records[node_id] = {
                "document": document,
                "embedding": embedding,
                "metadata": metadata,
            }

    def query(
        self,
        *,
        query_embeddings: list[list[float]],
        n_results: int,
        include: list[str],
    ) -> dict[str, object]:
        del include
        query_embedding = query_embeddings[0]
        scored = sorted(
            self._records.items(),
            key=lambda item: sum(
                left * right
                for left, right in zip(
                    query_embedding,
                    item[1]["embedding"],  # type: ignore[index]
                    strict=True,
                )
            ),
            reverse=True,
        )[:n_results]
        return {
            "ids": [[node_id for node_id, _ in scored]],
            "documents": [[record["document"] for _, record in scored]],
            "embeddings": [[record["embedding"] for _, record in scored]],
            "metadatas": [[record["metadata"] for _, record in scored]],
        }

    def get(
        self,
        *,
        ids: list[str] | None = None,
        include: list[str],
    ) -> dict[str, object]:
        del include
        selected_ids = ids or list(self._records)
        records = [self._records[node_id] for node_id in selected_ids if node_id in self._records]
        ids_payload = [node_id for node_id in selected_ids if node_id in self._records]
        return {
            "ids": ids_payload,
            "documents": [record["document"] for record in records],
            "embeddings": [record["embedding"] for record in records],
            "metadatas": [record["metadata"] for record in records],
        }

    def delete(self, *, ids: list[str]) -> None:
        for node_id in ids:
            self._records.pop(node_id, None)

    def count(self) -> int:
        return len(self._records)


class _FakeClient:
    def __init__(self, *, path: str) -> None:
        self._path = path
        self._collection = _FakeCollection()

    def get_or_create_collection(self, *, name: str, metadata: dict[str, object]) -> _FakeCollection:
        del name, metadata
        return self._collection


class RuntimeIntegrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        MemoryEmbedder._model = None
        MemoryEmbedder._loaded_model_name = None
        VoiceAdapter._model = None
        VoiceAdapter._loaded_model_name = None

    def _memory_node(
        self,
        index: int,
        *,
        content: str | None = None,
        embedding: EmbeddingVector | None = None,
    ) -> dict[str, object]:
        return {
            "id": MemoryNodeId(f"mem-{index}"),
            "content": content or f"Node {index}",
            "embedding": embedding if embedding is not None else EmbeddingVector([1.0, 0.0, 0.0]),
            "tags": ["test"],
            "source": "test",
            "created_at": float(index),
            "last_accessed": float(index),
            "access_count": 1,
            "confidence": 1.0,
            "session_id": SessionId("session-1"),
            "source_type": "dataset",
            "provenance": [
                {
                    "source_type": "dataset",
                    "source_id": "test-dataset",
                    "label": "test dataset",
                    "uri": "dataset://test",
                    "snippet": content or f"Node {index}",
                }
            ],
        }

    def _workspace_temp_root(self, name: str) -> Path:
        root = Path.cwd() / ".tmp_test" / name
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        return root

    def test_embedder_respects_forced_hash_backend(self) -> None:
        embedder = MemoryEmbedder(backend_preference="hash")
        vector = embedder.embed("forced hash backend")
        self.assertEqual(embedder.backend_name(), "hash")
        self.assertTrue(vector)

    def test_embedder_falls_back_when_sentence_transformer_load_fails(self) -> None:
        class BrokenSentenceTransformerModule:
            class SentenceTransformer:
                def __init__(self, _model_name: str) -> None:
                    raise RuntimeError("cannot load model")

        with patch.dict(sys.modules, {"sentence_transformers": BrokenSentenceTransformerModule}):
            embedder = MemoryEmbedder(backend_preference="auto")
            vector = embedder.embed("fallback on load error")
        self.assertEqual(embedder.backend_name(), "hash")
        self.assertTrue(vector)

    def test_embedder_uses_sentence_transformers_when_available(self) -> None:
        class WorkingSentenceTransformerModule:
            class SentenceTransformer:
                def __init__(self, _model_name: str) -> None:
                    pass

                def encode(
                    self,
                    _text: str,
                    *,
                    normalize_embeddings: bool,
                ) -> list[float]:
                    self.last_normalized = normalize_embeddings
                    return [0.1, 0.2, 0.3]

        with patch.dict(sys.modules, {"sentence_transformers": WorkingSentenceTransformerModule}):
            embedder = MemoryEmbedder(backend_preference="auto")
            vector = embedder.embed("live encoder")
        self.assertEqual(embedder.backend_name(), "sentence-transformers")
        self.assertEqual(vector, EmbeddingVector([0.1, 0.2, 0.3]))

    def test_vector_store_uses_chromadb_backend_when_available(self) -> None:
        fake_chromadb = types.SimpleNamespace(PersistentClient=_FakeClient)
        with patch.dict(sys.modules, {"chromadb": fake_chromadb}):
            root = self._workspace_temp_root("vector-store-basic")
            try:
                store = ChromaVectorStore(root, embedder=_FakeEmbedder(), dimensions=3)
                node = {
                    "id": MemoryNodeId("mem-1"),
                    "content": "Paris is the capital of France",
                    "embedding": EmbeddingVector([1.0, 0.0, 0.0]),
                    "tags": ["geography"],
                    "source": "test",
                    "created_at": 1.0,
                    "last_accessed": 1.0,
                    "access_count": 1,
                    "confidence": 1.0,
                    "session_id": SessionId("session-1"),
                    "source_type": "dataset",
                    "provenance": [
                        {
                            "source_type": "dataset",
                            "source_id": "countries",
                            "label": "countries dataset",
                            "uri": "dataset://countries",
                            "snippet": "Paris is the capital of France",
                        }
                    ],
                }
                self.assertEqual(store.backend_name(), "hnsw")
                self.assertTrue(store.add(node)["ok"])
                search_result = store.search("capital city", 1)
                self.assertTrue(search_result["ok"])
                self.assertEqual(search_result["value"][0]["id"], MemoryNodeId("mem-1"))
            finally:
                shutil.rmtree(root, ignore_errors=True)

    def test_vector_store_respects_forced_json_backend(self) -> None:
        fake_chromadb = types.SimpleNamespace(PersistentClient=_FakeClient)
        with patch.dict(sys.modules, {"chromadb": fake_chromadb}):
            root = self._workspace_temp_root("vector-store-forced-json")
            try:
                store = ChromaVectorStore(
                    root,
                    embedder=_FakeEmbedder(),
                    backend_preference="json",
                    dimensions=3,
                )
                self.assertEqual(store.backend_name(), "hnsw")
            finally:
                shutil.rmtree(root, ignore_errors=True)

    def test_vector_store_rebuilds_stale_index_before_search(self) -> None:
        root = self._workspace_temp_root("vector-store-stale-index")
        try:
            store = ChromaVectorStore(root, embedder=_FakeEmbedder(), dimensions=3)
            self.assertTrue(
                store.add(
                    self._memory_node(0, content="Paris is the capital of France")
                )["ok"]
            )
            store.close()
            shutil.copyfile(root / "memory.index", root / "memory.index.snapshot")

            store = ChromaVectorStore(root, embedder=_FakeEmbedder(), dimensions=3)
            for index in range(1, 12):
                self.assertTrue(
                    store.add(self._memory_node(index, content=f"Capital fact {index}"))["ok"]
                )
            store.close()
            shutil.copyfile(root / "memory.index.snapshot", root / "memory.index")

            repaired = ChromaVectorStore(root, embedder=_FakeEmbedder(), dimensions=3)
            search_result = repaired.search("capital city", 5)
            rebuilt_count = repaired._index.get_current_count()
            repaired.close()
        finally:
            shutil.rmtree(root, ignore_errors=True)

        self.assertEqual(rebuilt_count, 12)
        self.assertTrue(search_result["ok"])
        self.assertEqual(len(search_result["value"]), 5)

    def test_vector_store_resizes_index_before_capacity_is_exhausted(self) -> None:
        with patch("brain.memory.vector_store._MIN_INDEX_CAPACITY", 4):
            root = self._workspace_temp_root("vector-store-capacity")
            try:
                store = ChromaVectorStore(root, embedder=_FakeEmbedder(), dimensions=3)
                for index in range(10):
                    self.assertTrue(
                        store.add(self._memory_node(index, content=f"Capital fact {index}"))["ok"]
                    )
                search_result = store.search("capital city", 5)
                max_elements = store._index.get_max_elements()
                store.close()
            finally:
                shutil.rmtree(root, ignore_errors=True)

        self.assertGreaterEqual(max_elements, 10)
        self.assertTrue(search_result["ok"])
        self.assertEqual(len(search_result["value"]), 5)

    def test_url_adapter_rejects_insecure_tls_fallback_by_default(self) -> None:
        client_configs: list[dict[str, object]] = []

        class FakeConnectError(Exception):
            pass

        class FakeResponse:
            text = "<html><title>Unsafe</title><body>Unsafe page</body></html>"

            def raise_for_status(self) -> None:
                return None

        class FakeClient:
            def __init__(self, **kwargs: object) -> None:
                client_configs.append(kwargs)
                self._verify = kwargs.get("verify", True)

            def __enter__(self) -> FakeClient:
                return self

            def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
                return False

            def get(self, _url: str) -> FakeResponse:
                if self._verify:
                    raise FakeConnectError("CERTIFICATE_VERIFY_FAILED")
                return FakeResponse()

        fake_httpx = types.SimpleNamespace(Client=FakeClient, ConnectError=FakeConnectError)
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            adapter = UrlAdapter(settings=settings)
            with patch.dict(sys.modules, {"httpx": fake_httpx}):
                result = adapter.normalize("https://example.com")
        self.assertFalse(result["ok"])
        self.assertEqual(len(client_configs), 1)

    def test_url_adapter_allows_insecure_tls_fallback_when_enabled(self) -> None:
        client_configs: list[dict[str, object]] = []

        class FakeConnectError(Exception):
            pass

        class FakeResponse:
            text = "<html><title>Unsafe</title><body>Unsafe page</body></html>"

            def raise_for_status(self) -> None:
                return None

        class FakeClient:
            def __init__(self, **kwargs: object) -> None:
                client_configs.append(kwargs)
                self._verify = kwargs.get("verify", True)

            def __enter__(self) -> FakeClient:
                return self

            def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
                return False

            def get(self, _url: str) -> FakeResponse:
                if self._verify:
                    raise FakeConnectError("CERTIFICATE_VERIFY_FAILED")
                return FakeResponse()

        fake_httpx = types.SimpleNamespace(Client=FakeClient, ConnectError=FakeConnectError)
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            settings = settings.__class__(**{**settings.__dict__, "http_allow_insecure_tls": True})
            adapter = UrlAdapter(settings=settings)
            with patch.dict(sys.modules, {"httpx": fake_httpx}):
                result = adapter.normalize("https://example.com")
        self.assertTrue(result["ok"])
        self.assertEqual(len(client_configs), 2)
        self.assertFalse(bool(client_configs[1]["verify"]))

    def test_content_fetcher_allows_insecure_tls_fallback_when_enabled(self) -> None:
        client_configs: list[dict[str, object]] = []

        class FakeConnectError(Exception):
            pass

        class FakeResponse:
            text = "<html><title>Unsafe</title><body>Fetched page</body></html>"

            def raise_for_status(self) -> None:
                return None

        class FakeClient:
            def __init__(self, **kwargs: object) -> None:
                client_configs.append(kwargs)
                self._verify = kwargs.get("verify", True)

            def __enter__(self) -> FakeClient:
                return self

            def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
                return False

            def get(self, _url: str) -> FakeResponse:
                if self._verify:
                    raise FakeConnectError("CERTIFICATE_VERIFY_FAILED")
                return FakeResponse()

        fake_httpx = types.SimpleNamespace(Client=FakeClient, ConnectError=FakeConnectError)
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            settings = settings.__class__(**{**settings.__dict__, "http_allow_insecure_tls": True})
            fetcher = ContentFetcher(settings=settings)
            with patch.dict(sys.modules, {"httpx": fake_httpx}):
                result = asyncio.run(fetcher.fetch("https://example.com"))
        self.assertTrue(result["ok"])
        self.assertEqual(len(client_configs), 2)
        self.assertFalse(bool(client_configs[1]["verify"]))

    def test_voice_adapter_converts_pcm_and_caches_whisper_model(self) -> None:
        created_models: list[tuple[str, str, str]] = []
        transcribed_audio: list[object] = []

        class FakeSegment:
            def __init__(self, text: str) -> None:
                self.text = text

        class FakeWhisperModel:
            def __init__(self, model_name: str, *, device: str, compute_type: str) -> None:
                created_models.append((model_name, device, compute_type))

            def transcribe(self, audio: object) -> tuple[list[FakeSegment], object]:
                transcribed_audio.append(audio)
                return [FakeSegment("hello"), FakeSegment("world")], object()

        fake_module = types.SimpleNamespace(WhisperModel=FakeWhisperModel)
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            with patch.dict(sys.modules, {"faster_whisper": fake_module}):
                first = VoiceAdapter(settings=settings).normalize((b"\x00\x10") * 32)
                second = VoiceAdapter(settings=settings).normalize((b"\x00\x10") * 32)
        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(created_models, [("base.en", "cpu", "int8")])
        self.assertEqual(first["value"]["text"], "hello world")
        self.assertEqual(second["value"]["text"], "hello world")
        self.assertEqual(transcribed_audio[0].dtype.name, "float32")
        self.assertEqual(len(transcribed_audio[0].shape), 1)

    def test_grounded_language_expert_requires_real_evidence(self) -> None:
        meta = {
            "id": ExpertId("language-en"),
            "name": "Language Expert",
            "domains": ["language"],
            "kind": "grounded-language",
            "artifact_root": "language-en",
            "artifacts": [{"name": "manifest", "path": "manifest.json", "kind": "config"}],
            "capabilities": ["grounded-answering"],
            "load_strategy": "lazy",
            "description": "test",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            expert = Expert(meta, Path(temp_dir), settings=settings)
            unsupported = expert.infer("hello world")
            self.assertFalse(unsupported["ok"])

            grounded = expert.infer(
                "hello world",
                context={
                    "query": "hello world",
                    "session_id": SessionId("session-1"),
                    "memory_nodes": [],
                    "internet_citations": [
                        {
                            "id": "doc-1",
                            "source_type": "internet",
                            "label": "example.com",
                            "snippet": "hello from grounded evidence",
                            "uri": "https://example.com",
                        }
                    ],
                    "dialogue_state": {
                        "intent": "general",
                        "style": "concise",
                        "needs_clarification": False,
                        "prefers_steps": False,
                        "references_workspace": False,
                        "references_memory": False,
                        "asks_for_reasoning": False,
                        "confidence": 0.9,
                        "signals": [],
                    },
                    "response_plan": {
                        "mode": "answer",
                        "lead_style": "concise",
                        "include_sources": True,
                        "include_next_step": False,
                        "max_citations": 2,
                        "rationale": "test",
                    },
                },
            )
            expert.unload()
            self.assertTrue(grounded["ok"])
            self.assertIn("grounded answer", grounded["value"]["content"])
            self.assertEqual(expert.runtime_backend_name(), "grounded-evidence")

    def test_repo_code_expert_searches_workspace_files(self) -> None:
        meta = {
            "id": ExpertId("code-general"),
            "name": "Code Expert",
            "domains": ["code"],
            "kind": "repo-code",
            "artifact_root": "code-general",
            "artifacts": [{"name": "manifest", "path": "manifest.json", "kind": "config"}],
            "capabilities": ["workspace-search"],
            "load_strategy": "lazy",
            "description": "test",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings(root)
            target = root / "src" / "python_gateway.ts"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                "export async function queryPythonGateway() { return 'gateway'; }\n",
                encoding="utf-8",
            )
            expert = Expert(meta, root, settings=settings)
            result = expert.infer("python gateway query")
            expert.unload()
            self.assertTrue(result["ok"])
            self.assertIn("python_gateway.ts", result["value"]["content"])
            self.assertEqual(expert.runtime_backend_name(), "repo-search")

    def test_geography_expert_reads_offline_dataset(self) -> None:
        meta = {
            "id": ExpertId("geography"),
            "name": "Geography Expert",
            "domains": ["geography"],
            "kind": "geography-dataset",
            "artifact_root": "geography",
            "artifacts": [
                {"name": "manifest", "path": "manifest.json", "kind": "config"},
                {"name": "countries", "path": "countries.json", "kind": "dataset"},
            ],
            "capabilities": ["capital-lookup"],
            "load_strategy": "lazy",
            "description": "test",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "countries.json").write_text(
                json.dumps([{"country": "France", "capital": "Paris", "region": "Europe"}]),
                encoding="utf-8",
            )
            expert = Expert(meta, root)
            result = expert.infer("what is the capital of France")
            expert.unload()
            self.assertTrue(result["ok"])
            self.assertIn("Paris", result["value"]["content"])
            self.assertEqual(expert.runtime_backend_name(), "dataset-lookup")

    def test_corrector_writes_dataset_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            corrector = ExpertCorrector(settings=settings)
            result = corrector.correct(
                ExpertId("language-en"),
                [("q1", "bad response"), ("q2", "wrong answer")],
                positive_examples=[("q3", "good response")],
                turn_traces=[
                    {
                        "session_id": SessionId("session-1"),
                        "expert_id": ExpertId("language-en"),
                        "query": "q3",
                        "response": "good response",
                        "dialogue_intent": "general",
                        "response_mode": "answer",
                        "render_strategy": "grounded",
                        "citations_count": 1,
                        "has_next_step": False,
                        "query_coverage": 0.0,
                        "entity_match_score": 0.0,
                        "response_length_tokens": 2,
                        "confidence": 0.9,
                        "decision_trace": "trace",
                        "outcome": "answered",
                        "timestamp": 1.0,
                    }
                ],
            )
            self.assertTrue(result["ok"])
            dataset_path = settings.lora_dir / "datasets" / "language-en.jsonl"
            manifest_path = settings.lora_dir / "language-en.training-job.json"
            trace_path = settings.lora_dir / "experts" / "language-en.jsonl"
            self.assertTrue(dataset_path.exists())
            self.assertTrue(manifest_path.exists())
            self.assertTrue(trace_path.exists())
            dataset_text = dataset_path.read_text(encoding="utf-8")
            manifest_text = manifest_path.read_text(encoding="utf-8")
            self.assertIn("bad response", dataset_text)
            self.assertIn("good response", dataset_text)
            self.assertIn("negative_example_count", manifest_text)
            self.assertIn("positive_example_count", manifest_text)
            self.assertIn("trace_dataset_path", manifest_text)
            self.assertIn("pending-training", manifest_text)

    def test_corrector_respects_forced_fallback_backend(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            settings = settings.__class__(**{**settings.__dict__, "learning_backend": "fallback"})
            corrector = ExpertCorrector(settings=settings)
            result = corrector.correct(ExpertId("language-en"), [("q1", "bad response")])
            self.assertTrue(result["ok"])
            self.assertEqual(corrector.backend_name(), "offline-job-manifest")


if __name__ == "__main__":
    unittest.main()
