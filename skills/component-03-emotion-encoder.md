# Component 03 Skill: Emotion and Tone Encoder

## Purpose
Infer emotional context from normalized text/voice signals and produce `EmotionContext` for routing and response shaping.

## Dependencies
- `vaderSentiment`
- `transformers` (emotion model: `j-hartmann/emotion-english-distilroberta-base`)
- Optional quantization: `bitsandbytes`
- Optional voice classifier: `pyAudioAnalysis`

## Required Files
- `brain/emotion/text_encoder.py`
- `brain/emotion/voice_encoder.py`
- `brain/emotion/fusion.py`
- `brain/emotion/__init__.py`
- `tests/python/test_emotion.py`

## Implementation Checklist
1. `text_encoder.py`:
   - Stage 1 (VADER): compute `compound` sentiment; map to valence; set arousal via `abs(compound)`.
   - Stage 2 (Transformer pipeline): classify emotions with full probability set.
   - Try INT8 quantization via `BitsAndBytesConfig`; fallback cleanly to full precision.
   - Fusion in encoder:
     - `primary_emotion` = top transformer label.
     - final valence = weighted blend of VADER + transformer valence proxy.
     - confidence = top label probability.
2. `voice_encoder.py`:
   - Read `prosodic_features` from signal metadata.
   - Missing features -> neutral context, confidence 0.0, source `"voice"`, note in metadata/aux path.
   - If features present, map heuristically:
     - high pitch std + high amplitude -> excited/angry.
     - low pitch mean + low amplitude -> sad.
     - high onset variance -> confused.
     - high speaking rate + high amplitude -> urgent.
   - If `pyAudioAnalysis` available, use improved classification; fallback remains heuristic.
3. `fusion.py`:
   - If only one context exists, return it.
   - If both exist:
     - pick `primary_emotion` from higher-confidence context.
     - valence weighted by confidence.
     - arousal = `max(text.arousal, voice.arousal)`.
     - source = `"both"`.
     - confidence = geometric mean.
4. `__init__.py`:
   - Export `encode_emotion(signal: NormalizedSignal) -> EmotionContext`.
   - Route text-only, voice-only, or fused outputs appropriately.

## Test Checklist
- Text cases:
  - `"I am so happy today!"`
  - `"This is terrible"`
  - `"How does this work?"`
- Voice cases:
  - Synthetic prosodic feature dictionaries.
- Fusion cases:
  - conflicting contexts (voice angry vs text calm).
- Integration:
  - full `NormalizedSignal` through `encode_emotion`.

## Pass Criteria
- Outputs are deterministic for heuristic branches.
- Optional dependencies fail gracefully.
- Fusion behavior matches confidence-weighted rules.

## Premium Quality Gates (CLI)
- Static checks:
  - `python -m ruff check brain tests`
  - `python -m mypy brain`
- Targeted tests:
  - `python -m pytest tests/python/test_emotion.py -q`
- Determinism check (recommended):
  - run `test_emotion.py` twice and confirm same branch outcomes for heuristic inputs.
- Merge gate:
  - Fusion conflict scenario passes reliably.
  - Missing-feature voice path returns safe neutral context.
