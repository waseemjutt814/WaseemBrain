from __future__ import annotations

from dataclasses import dataclass

from .trainer import RouterTrainingSample


@dataclass
class RouterLabeler:
    labels: list[str]

    def label(
        self,
        text: str,
        labels: list[str],
        *,
        internet_needed: bool = False,
    ) -> RouterTrainingSample:
        selected = [label for label in labels if label in self.labels]
        return RouterTrainingSample(
            text=text,
            labels=selected,
            internet_needed=internet_needed,
        )
