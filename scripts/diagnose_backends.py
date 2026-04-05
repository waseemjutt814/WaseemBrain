from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.config import load_settings
from brain.experts.expert import Expert
from brain.experts.registry import ExpertRegistry
from brain.learning.corrector import ExpertCorrector
from brain.memory.graph import MemoryGraph
from brain.router import ArtifactRouterClient, RouterDaemonClient
from brain.types import ExpertId, SessionId


def is_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def main() -> None:
    settings = load_settings()
    with tempfile.TemporaryDirectory() as temp_dir:
        probe_root = Path(temp_dir)
        probe_settings = settings.__class__(
            **{
                **settings.__dict__,
                "chroma_dir": probe_root / "data" / "vector",
                "sqlite_dir": probe_root / "data" / "sqlite",
                "vector_index_path": probe_root / "data" / "vector" / "memory.index",
                "lora_dir": probe_root / "experts" / "lora",
            }
        )
        registry = ExpertRegistry(settings=probe_settings)
        validation = registry.validate()
        memory_graph = MemoryGraph(settings=probe_settings)
        corrector = ExpertCorrector(settings=probe_settings)

        print("Optional runtime availability:")
        for module_name in (
            "onnxruntime",
            "hnswlib",
            "faster_whisper",
            "sentence_transformers",
            "duckduckgo_search",
            "grpc",
        ):
            print(f"- {module_name}: {'yes' if is_available(module_name) else 'no'}")

        print("\nConfigured runtime:")
        print(f"- embedding_backend: {probe_settings.embedding_backend}")
        print(f"- embedding_model_name: {probe_settings.embedding_model_name}")
        print(f"- memory_vector_backend: {probe_settings.memory_vector_backend}")
        print(f"- learning_backend: {probe_settings.learning_backend}")
        print(f"- router_backend: {probe_settings.router_backend}")
        print(f"- router_model_path: {probe_settings.router_model_path}")
        print(f"- strict_runtime: {probe_settings.strict_runtime}")
        print(f"- probe_storage_root: {probe_root}")

        print("\nResolved state:")
        print(f"- registry_valid: {validation['ok']}")
        if not validation["ok"]:
            print(f"- registry_error: {validation['error']}")
        print(f"- vector_backend: {memory_graph.vector_backend_name()}")
        print(f"- corrector: {corrector.backend_name()}")

        experts = registry.all()
        if experts:
            probe_expert = Expert(
                experts[0],
                probe_settings.expert_dir / experts[0]["artifact_root"],
                settings=probe_settings,
            )
            probe_result = probe_expert.infer(
                "what is the capital of France",
                context={
                    "query": "what is the capital of France",
                    "session_id": SessionId("diagnose-session"),
                    "memory_nodes": [],
                    "internet_citations": [
                        {
                            "id": "dataset://probe",
                            "source_type": "dataset",
                            "label": "probe dataset",
                            "snippet": "France -> Paris",
                            "uri": "dataset://probe",
                        }
                    ],
                },
            )
            print(f"- expert_runtime: {probe_expert.runtime_backend_name()}")
            print(f"- expert_probe_ok: {probe_result['ok']}")
            probe_expert.unload()
        else:
            print("- expert_runtime: unavailable (registry is empty)")

        probe_corrector = ExpertCorrector(settings=probe_settings)
        probe_corrector.correct(ExpertId("probe-expert"), [("probe", "bad output")])
        print(f"- corrector_probe_backend: {probe_corrector.backend_name()}")

        artifact_router = ArtifactRouterClient(settings=probe_settings)
        router_probe = artifact_router.decide(
            {
                "text": "what is the capital of France",
                "modality": "text",
                "metadata": {},
                "session_id": "diagnose-session",
            },
            {
                "primary_emotion": "calm",
                "valence": 0.0,
                "arousal": 0.0,
                "confidence": 1.0,
                "source": "text",
            },
        )
        if router_probe["ok"]:
            print(f"- local_router: {list(router_probe['value']['experts_needed'])}")
        else:
            print(f"- local_router_error: {router_probe['error']}")

        router_client = RouterDaemonClient(
            target=f"{probe_settings.grpc_host}:{probe_settings.grpc_port}",
            timeout_sec=min(probe_settings.grpc_timeout_sec, 0.2),
        )
        daemon_probe = router_client.decide(
            {
                "text": "what is the capital of France",
                "modality": "text",
                "metadata": {},
                "session_id": "diagnose-session",
            },
            {
                "primary_emotion": "calm",
                "valence": 0.0,
                "arousal": 0.0,
                "confidence": 1.0,
                "source": "text",
            },
        )
        if daemon_probe["ok"]:
            print(
                f"- router_daemon: reachable ({router_client.target()}) "
                f"-> {list(daemon_probe['value']['experts_needed'])}"
            )
        else:
            print(f"- router_daemon: unavailable ({router_client.target()})")
            print("- router_daemon_hint: run `python scripts/manage_router_daemon.py start`")

        memory_graph.close()
        artifact_router.close()
        router_client.close()


if __name__ == "__main__":
    main()
