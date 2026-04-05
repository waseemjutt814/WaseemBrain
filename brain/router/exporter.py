from __future__ import annotations

import json
from pathlib import Path

from .trainer import TrainedRouterModel


class RouterExporter:
    def export_model(self, output_path: Path, model: TrainedRouterModel) -> Path:
        payload = {
            "version": 1,
            "labels": model.labels,
            "feature_count": model.feature_count,
            "expert_weights": model.expert_weights,
            "expert_bias": model.expert_bias,
            "internet_weights": model.internet_weights,
            "internet_bias": model.internet_bias,
            "confidence_floor": model.confidence_floor,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return output_path
