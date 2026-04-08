from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import asyncio
import statistics
import time

from brain.runtime import WaseemBrainRuntime
from brain.types import SessionId


async def run_benchmark(text: str, iterations: int) -> None:
    runtime = WaseemBrainRuntime()
    latencies = []
    try:
        for index in range(iterations):
            started = time.perf_counter()
            async for _chunk in runtime.query(text, "text", SessionId(f"benchmark-{index}")):
                pass
            latencies.append((time.perf_counter() - started) * 1000.0)
        print(
            {
                "iterations": iterations,
                "mean_ms": statistics.mean(latencies),
                "p95_ms": sorted(latencies)[max(0, int(iterations * 0.95) - 1)],
                "health": runtime.health(),
            }
        )
    finally:
        runtime.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark the coordinator pipeline.")
    parser.add_argument("text", nargs="?", default="hello world")
    parser.add_argument("--iterations", type=int, default=3)
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.text, args.iterations))


if __name__ == "__main__":
    main()
