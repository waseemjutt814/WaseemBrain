from __future__ import annotations

import tempfile
import unittest
from concurrent import futures
from pathlib import Path

import grpc

from brain.router import HybridRouterClient, RouterDaemonClient
from brain.router.generated import router_pb2, router_pb2_grpc
from brain.runtime import LatticeBrainRuntime
from brain.types import SessionId
from tests.python.support import make_settings, seed_experts


class _RouterService(router_pb2_grpc.RouterServiceServicer):
    def Decide(self, request: router_pb2.RouterRequest, context: grpc.ServicerContext) -> router_pb2.RouterDecision:
        del context
        expert_ids = ["geography"] if "python" in request.text.lower() else ["language-en"]
        return router_pb2.RouterDecision(
            expert_ids=expert_ids,
            check_memory_first=True,
            internet_needed=False,
            confidence=0.91,
            reasoning_trace=f"grpc:{request.emotion_primary}",
            latency_ms=1.5,
        )


class _ExpertService(router_pb2_grpc.ExpertServiceServicer):
    def __init__(self) -> None:
        self.mapped: list[str] = []
        self.evicted: list[str] = []

    def MapExpert(self, request: router_pb2.MapRequest, context: grpc.ServicerContext) -> router_pb2.MapResponse:
        del context
        self.mapped.append(request.expert_id)
        return router_pb2.MapResponse(mapped=True, mapped_count=len(self.mapped))

    def EvictExpert(self, request: router_pb2.EvictRequest, context: grpc.ServicerContext) -> router_pb2.EvictResponse:
        del context
        self.evicted.append(request.expert_id)
        return router_pb2.EvictResponse(evicted=True, mapped_count=max(len(self.mapped) - len(self.evicted), 0))


class RouterGrpcTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
        self._expert_service = _ExpertService()
        router_pb2_grpc.add_RouterServiceServicer_to_server(_RouterService(), self._server)
        router_pb2_grpc.add_ExpertServiceServicer_to_server(self._expert_service, self._server)
        port = self._server.add_insecure_port("127.0.0.1:0")
        self._server.start()
        self._target = f"127.0.0.1:{port}"

    async def asyncTearDown(self) -> None:
        self._server.stop(grace=None)

    async def test_router_daemon_client_decide_and_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            seed_experts(settings)
            client = RouterDaemonClient(self._target, timeout_sec=1.0)
            decision = client.decide(
                {
                    "text": "tell me about python",
                    "modality": "text",
                    "metadata": {},
                    "session_id": SessionId("grpc-1"),
                },
                {
                    "primary_emotion": "calm",
                    "valence": 0.0,
                    "arousal": 0.0,
                    "confidence": 1.0,
                    "source": "text",
                },
            )
            self.assertTrue(decision["ok"])
            self.assertEqual(decision["value"]["experts_needed"], ["geography"])

            mapped = client.map_expert(
                "language-en",
                settings.expert_dir / "language-en" / "manifest.json",
            )
            self.assertTrue(mapped["ok"])
            evicted = client.evict_expert("language-en")
            self.assertTrue(evicted["ok"])
            client.close()

    async def test_hybrid_router_falls_back_when_daemon_is_unavailable(self) -> None:
        class _FallbackRouter:
            def decide(self, signal: object, emotion_context: object) -> dict[str, object]:
                del signal, emotion_context
                return {
                    "ok": True,
                    "value": {
                        "experts_needed": ["language-en"],
                        "check_memory_first": True,
                        "internet_needed": False,
                        "confidence": 0.5,
                        "reasoning_trace": "fallback",
                    },
                }

        hybrid = HybridRouterClient(
            RouterDaemonClient("127.0.0.1:1", timeout_sec=0.05, cooldown_sec=0.01),
            _FallbackRouter(),
        )
        result = hybrid.decide(
            {
                "text": "hello world",
                "modality": "text",
                "metadata": {},
                "session_id": SessionId("fallback-1"),
            },
            {
                "primary_emotion": "calm",
                "valence": 0.0,
                "arousal": 0.0,
                "confidence": 1.0,
                "source": "text",
            },
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["value"]["reasoning_trace"], "fallback")

    async def test_runtime_uses_grpc_router_and_mapper(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            settings = settings.__class__(
                **{
                    **settings.__dict__,
                    "router_backend": "grpc",
                    "grpc_host": "127.0.0.1",
                    "grpc_port": int(self._target.rsplit(":", 1)[1]),
                    "grpc_timeout_sec": 1.0,
                    "internet_enabled": False,
                }
            )
            seed_experts(settings)
            runtime = LatticeBrainRuntime(settings=settings)
            try:
                chunks = []
                async for chunk in runtime.query(
                    "tell me about python",
                    "text",
                    SessionId("runtime-grpc"),
                ):
                    chunks.append(chunk)
                self.assertTrue("".join(chunks).strip())
                self.assertEqual(runtime.experts()["loaded"], ["geography"])
                self.assertIn("geography", self._expert_service.mapped)
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
