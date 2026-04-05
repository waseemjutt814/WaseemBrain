# Learning Pipeline

## Purpose
Maintain the offline learning loop that turns traces, curated datasets, and feedback into compact artifacts for classifiers, rerankers, and planners.

## Focus Files
- `brain/learning/feedback.py`
- `brain/learning/scorer.py`
- `brain/learning/loop.py`
- `brain/router/trainer.py`
- `scripts/train_router.py`
- `scripts/create_expert.py`
- `tests/python/test_learning.py`

## Rules
- Runtime must stay fully useful without network access once artifacts are prepared.
- Dataset download, cleaning, labeling, and artifact export belong to offline jobs, not request-time code.
- Only keep compact artifacts with a measurable runtime role; do not emit fake finetune bundles.
- Training inputs and transforms must be documented enough to reproduce them later.

## Checks
- `python -m pytest tests/python/test_learning.py -q`
- `python scripts/guard_no_placeholders.py`
