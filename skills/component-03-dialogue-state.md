# Dialogue State

## Purpose
Produce compact dialogue and tone state that the planner can consume without pretending to do human-like feelings or hidden large-model reasoning.

## Focus Files
- `brain/emotion/text_encoder.py`
- `brain/emotion/voice_encoder.py`
- `brain/emotion/fusion.py`
- `brain/session.py`
- `brain/coordinator.py`
- `tests/python/test_emotion.py`

## Rules
- Keep emitted state small and actionable: tone, urgency, uncertainty, follow-up pressure, and user preference hints.
- Deterministic rules and compact classifiers are allowed; fake empathy outputs are not.
- Text, voice, and fusion paths should stay independently testable.
- Dialogue state must help planning and clarification, not inflate the surface with decorative labels.

## Checks
- `python -m pytest tests/python/test_emotion.py -q`
