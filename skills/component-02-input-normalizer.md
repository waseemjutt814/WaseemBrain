# Component 02 Skill: Sensory Input Normalizer

## Purpose
Build adapters in `brain/normalizer/` to convert raw text, voice, documents, and URLs into a common `NormalizedSignal`.

## Dependencies
- Python libs: `langdetect`, `faster-whisper`, `librosa`, `pypdf`, `python-docx`, `httpx`, `trafilatura`.

## Required Files
- `brain/normalizer/base.py`
- `brain/normalizer/text_adapter.py`
- `brain/normalizer/voice_adapter.py`
- `brain/normalizer/document_adapter.py`
- `brain/normalizer/url_adapter.py`
- `brain/normalizer/__init__.py`
- `tests/python/test_normalizer.py`

## Implementation Checklist
1. `base.py`:
   - Create abstract `InputAdapter`.
   - One abstract method: `normalize(raw_input: Any) -> Result[NormalizedSignal, str]`.
2. `text_adapter.py`:
   - Accept raw string.
   - Strip whitespace, normalize unicode, detect language via `langdetect`.
   - Return `NormalizedSignal` with `modality="text"`.
3. `voice_adapter.py`:
   - Accept PCM16 bytes.
   - Transcribe with `faster-whisper` (`small`).
   - Extract prosody via `librosa`: pitch mean/std, speaking rate (onset density), amplitude envelope mean.
   - Put features in `metadata["prosodic_features"]`.
   - Return `modality="voice"` with `text` and `raw_audio`.
   - If `faster-whisper` missing, return explicit `err(...)`.
4. `document_adapter.py`:
   - Accept bytes + filename hint.
   - `.pdf` -> `pypdf` page extraction.
   - `.docx` -> `python-docx` paragraph extraction.
   - If text > 4000 chars, truncate and append `[truncated]`.
   - Return `modality="file"` and include filename in metadata.
5. `url_adapter.py`:
   - Accept URL string.
   - Fetch with `httpx` (10s timeout).
   - Extract content with `trafilatura`.
   - Include `metadata["title"]` if available and `metadata["fetched_at"]`.
   - Distinct error messages for timeout, network/http failure, extraction failure.
6. `__init__.py`:
   - Export `normalize(raw_input, modality_hint) -> Result[NormalizedSignal, str]`.
   - Routing rules:
     - bytes + filename hint `.pdf/.docx` -> document.
     - URL string (`http://` or `https://`) -> URL adapter.
     - bytes without filename -> voice.
     - any other string -> text.

## Test Checklist
- Text adapter:
  - Unicode input.
  - Empty/whitespace input.
  - Very long string.
- Voice adapter:
  - Synthetic 16kHz PCM bytes (NumPy generated).
- Document adapter:
  - Minimal generated PDF bytes.
- URL adapter:
  - Mocked `httpx` responses via `pytest-httpx` or `respx`.
- Top-level `normalize()` routing:
  - Assert correct adapter path for each input kind.

## Pass Criteria
- All adapters return `Result` consistently.
- Error paths are explicit and component-specific.
- Auto-routing is deterministic and test-covered.

## Premium Quality Gates (CLI)
- Static quality:
  - `python -m ruff check brain tests`
  - `python -m mypy brain`
- Targeted tests:
  - `python -m pytest tests/python/test_normalizer.py -q`
- Optional heavy-dependency run (if voice/doc/url extras installed):
  - `python -m pytest tests/python/test_normalizer.py -q -k "voice or document or url"`
- Merge gate:
  - All adapter tests pass.
  - Distinct error messages asserted in URL and voice failure paths.
