from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..types import NormalizedSignal, Result


class InputAdapter(ABC):
    @abstractmethod
    def normalize(self, raw_input: Any) -> Result[NormalizedSignal, str]:
        raise NotImplementedError
