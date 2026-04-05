from __future__ import annotations

import asyncio
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from ..memory.graph import MemoryGraph
from ..memory.sqlite_store import SqliteMetaStore
from ..types import SessionId
from .corrector import ExpertCorrector
from .feedback import FeedbackCollector
from .scorer import ResponseScorer
from .types import FeedbackSignal


class SelfLearningLoop:
    def __init__(
        self,
        sqlite_store: SqliteMetaStore,
        feedback_collector: FeedbackCollector,
        memory_graph: MemoryGraph,
        scorer: ResponseScorer | None = None,
        corrector: ExpertCorrector | None = None,
        executor: ThreadPoolExecutor | None = None,
    ) -> None:
        self._sqlite_store = sqlite_store
        self._feedback_collector = feedback_collector
        self._memory_graph = memory_graph
        self._scorer = scorer or ResponseScorer()
        self._corrector = corrector or ExpertCorrector()
        self._executor = executor or ThreadPoolExecutor(max_workers=2)
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass

    async def _run_loop(self) -> None:
        while True:
            await asyncio.sleep(60)
            sessions = self._sqlite_store.get_ended_sessions(300)
            for session_id in sessions:
                await self._handle_session(session_id)

    async def _handle_session(self, session_id: SessionId) -> None:
        signals = self._feedback_collector.flush(session_id)
        traces = self._feedback_collector.flush_traces(session_id)
        if traces:
            await asyncio.get_running_loop().run_in_executor(
                self._executor,
                self._corrector.record_session_traces,
                str(session_id),
                traces,
            )
        if not signals:
            return
        grouped: dict[str, list[FeedbackSignal]] = defaultdict(list)
        for signal in signals:
            grouped[str(signal["expert_id"])].append(signal)

        for expert_id, expert_signals in grouped.items():
            expert_traces = [trace for trace in traces if str(trace["expert_id"]) == expert_id]
            score = self._scorer.score(expert_signals, expert_traces)
            if not self._scorer.needs_correction(score):
                continue
            negative_examples = [
                (signal["query"], signal["response"])
                for signal in expert_signals
                if signal["signal_type"] == "negative"
            ]
            positive_examples = [
                (signal["query"], signal["response"])
                for signal in expert_signals
                if signal["signal_type"] == "positive" and signal["query"] and signal["response"]
            ]
            await asyncio.get_running_loop().run_in_executor(
                self._executor,
                partial(
                    self._corrector.correct,
                    expert_signals[0]["expert_id"],
                    negative_examples,
                    positive_examples=positive_examples,
                    turn_traces=expert_traces,
                ),
            )
            self._sqlite_store.log_correction_job(session_id, expert_id, score)
