from __future__ import annotations

import argparse
import contextlib
import io
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.config import load_settings
from brain.emotion.text_encoder import TextEmotionEncoder
from brain.memory.embedder import MemoryEmbedder
from brain.normalizer.voice_adapter import VoiceAdapter
from brain.types import SessionId
from scripts.build_knowledge_store import KnowledgeStoreBuilder, _load_manifest

_MIN_VOICE_WARMUP_FREE_BYTES = 2 * 1024 * 1024 * 1024


@contextlib.contextmanager
def _silence(enabled: bool) -> Any:
    if not enabled:
        yield
        return
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        yield


def _warm_models(*, include_voice: bool, quiet: bool) -> dict[str, str]:
    settings = load_settings()
    embedder = MemoryEmbedder(settings.embedding_backend, settings.embedding_model_name)
    emotion = TextEmotionEncoder()
    with _silence(quiet):
        embedder.embed("download models warmup")
        emotion.encode(
            {
                "text": "download models warmup",
                "modality": "text",
                "metadata": {},
                "session_id": SessionId("download-models"),
            }
        )

    status = {
        "embedding_backend": embedder.backend_name(),
        "text_emotion": "ready",
    }
    if include_voice:
        free_bytes = shutil.disk_usage(Path.home()).free
        if free_bytes < _MIN_VOICE_WARMUP_FREE_BYTES:
            status["voice"] = "skipped: less than 2 GiB free for whisper cache"
            return status
        adapter = VoiceAdapter(settings=settings)
        with _silence(quiet):
            result = adapter.normalize(b"\x00\x00" * max(settings.voice_sample_rate // 4, 4000))
        status["voice"] = "ready" if result["ok"] else result["error"]
    return status


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download or warm real runtime assets and build the local knowledge store."
    )
    parser.add_argument(
        "--include-voice",
        action="store_true",
        help="Warm the voice model too.",
    )
    parser.add_argument(
        "--skip-model-warmup",
        action="store_true",
        help="Skip embedding/emotion/voice warmup.",
    )
    parser.add_argument(
        "--skip-knowledge-build",
        action="store_true",
        help="Skip fetching online knowledge packs.",
    )
    parser.add_argument(
        "--refresh-knowledge",
        action="store_true",
        help="Force re-fetching generated knowledge packs.",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=ROOT / "experts" / "knowledge-manifest.json",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "experts" / "bootstrap" / "generated",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show underlying library output during warmup/fetching.",
    )
    args = parser.parse_args()

    report: dict[str, Any] = {
        "settings": {
            "expert_dir": str(load_settings().expert_dir),
            "lora_dir": str(load_settings().lora_dir),
        }
    }

    if not args.skip_model_warmup:
        report["warmup"] = _warm_models(
            include_voice=args.include_voice,
            quiet=not args.verbose,
        )

    if not args.skip_knowledge_build:
        datasets = _load_manifest(args.manifest_path)
        report["knowledge_store"] = KnowledgeStoreBuilder().build(
            datasets,
            output_root=args.output_root,
            refresh=args.refresh_knowledge,
            quiet=not args.verbose,
        )

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
