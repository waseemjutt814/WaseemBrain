from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast

from ..types import ExpertId, RouterDecision

_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_./-]{2,}")
_FNV_OFFSET = 1469598103934665603
_FNV_PRIME = 1099511628211

# Schema version for router artifact
ROUTER_ARTIFACT_VERSION = 2
ROUTER_ARTIFACT_MIN_VERSION = 1


@dataclass(frozen=True)
class SparseMatrix:
    """Memory-efficient sparse matrix representation using COO format."""
    indices: tuple[tuple[int, int], ...]  # (row, col) pairs for non-zero values
    values: tuple[float, ...]  # Corresponding non-zero values
    shape: tuple[int, int]  # (rows, cols)
    
    def dot(self, vector: list[float], row_index: int) -> float:
        """Compute dot product of a specific row with a vector."""
        result = 0.0
        for (row, col), value in zip(self.indices, self.values, strict=True):
            if row == row_index and col < len(vector):
                result += value * vector[col]
        return result
    
    def to_dense(self) -> tuple[tuple[float, ...], ...]:
        """Convert to dense matrix for backward compatibility."""
        rows, cols = self.shape
        dense = [[0.0] * cols for _ in range(rows)]
        for (row, col), value in zip(self.indices, self.values, strict=True):
            dense[row][col] = value
        return tuple(tuple(row) for row in dense)
    
    @classmethod
    def from_dense(cls, dense: tuple[tuple[float, ...], ...]) -> SparseMatrix:
        """Create sparse matrix from dense representation."""
        indices: list[tuple[int, int]] = []
        values: list[float] = []
        for row_idx, row in enumerate(dense):
            for col_idx, value in enumerate(row):
                if value != 0.0:
                    indices.append((row_idx, col_idx))
                    values.append(value)
        return cls(
            indices=tuple(indices),
            values=tuple(values),
            shape=(len(dense), len(dense[0]) if dense else 0),
        )
    
    def sparsity(self) -> float:
        """Return the sparsity ratio (fraction of zeros)."""
        total_elements = self.shape[0] * self.shape[1]
        if total_elements == 0:
            return 0.0
        return 1.0 - (len(self.values) / total_elements)


@dataclass(frozen=True)
class RouterArtifact:
    """Router artifact with optional sparse weight representation."""
    labels: tuple[str, ...]
    feature_count: int
    expert_weights: tuple[tuple[float, ...], ...]  # Dense format (backward compat)
    expert_bias: tuple[float, ...]
    internet_weights: tuple[float, ...]
    internet_bias: float
    confidence_floor: float
    # Sparse representation (optional, for memory efficiency)
    expert_weights_sparse: SparseMatrix | None = field(default=None, compare=False)
    internet_weights_sparse: SparseMatrix | None = field(default=None, compare=False)
    # Metadata
    version: int = 1
    checksum: str = ""
    
    @classmethod
    def load(cls, path: Path) -> RouterArtifact:
        """Load and validate router artifact from JSON file."""
        if not path.exists():
            raise RouterArtifactError(f"Router artifact not found: {path}")
        
        raw_content = path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()[:16]
        
        try:
            payload = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise RouterArtifactError(f"Invalid JSON in router artifact: {exc}") from exc
        
        # Validate version
        version = int(payload.get("version", 1))
        if version < ROUTER_ARTIFACT_MIN_VERSION or version > ROUTER_ARTIFACT_VERSION:
            raise RouterArtifactError(
                f"Unsupported router artifact version: {version} "
                f"(expected {ROUTER_ARTIFACT_MIN_VERSION}-{ROUTER_ARTIFACT_VERSION})"
            )
        
        
        # Validate required fields
        required_fields = ["labels", "feature_count", "expert_weights", "expert_bias"]
        for field_name in required_fields:
            if field_name not in payload:
                raise RouterArtifactError(f"Missing required field: {field_name}")
        
        
        # Validate labels
        labels = tuple(str(item) for item in payload["labels"])
        if not labels:
            raise RouterArtifactError("Labels cannot be empty")
        
        # Validate feature_count
        feature_count = int(payload["feature_count"])
        if feature_count <= 0 or feature_count > 10000:
            raise RouterArtifactError(f"Invalid feature_count: {feature_count}")
        
        # Load weights (support both dense and sparse formats)
        expert_weights, expert_weights_sparse = cls._load_weights(
            payload, "expert_weights", feature_count, labels
        )
        internet_weights, internet_weights_sparse = cls._load_internet_weights(
            payload, feature_count
        )
        
        # Validate biases
        expert_bias = tuple(float(value) for value in payload["expert_bias"])
        if len(expert_bias) != len(labels):
            raise RouterArtifactError(
                f"Expert bias count ({len(expert_bias)}) doesn't match labels ({len(labels)})"
            )
        
        
        internet_bias = float(payload.get("internet_bias", 0.0))
        confidence_floor = float(payload.get("confidence_floor", 0.5))
        
        return cls(
            labels=labels,
            feature_count=feature_count,
            expert_weights=expert_weights,
            expert_bias=expert_bias,
            internet_weights=internet_weights,
            internet_bias=internet_bias,
            confidence_floor=confidence_floor,
            expert_weights_sparse=expert_weights_sparse,
            internet_weights_sparse=internet_weights_sparse,
            version=version,
            checksum=checksum,
        )
    
    @classmethod
    def _load_weights(
        cls,
        payload: dict,
        field_name: str,
        feature_count: int,
        labels: tuple[str, ...],
    ) -> tuple[tuple[tuple[float, ...], ...], SparseMatrix | None]:
        """Load weights from either dense or sparse format."""
        data = payload.get(field_name, [])
        
        # Check for sparse format
        if isinstance(data, dict) and "indices" in data and "values" in data:
            # Sparse format
            indices = tuple(
                (int(idx[0]), int(idx[1])) 
                for idx in data["indices"]
            )
            values = tuple(float(v) for v in data["values"])
            sparse = SparseMatrix(
                indices=indices,
                values=values,
                shape=(len(labels), feature_count),
            )
            dense = sparse.to_dense()
            return dense, sparse
        
        
        # Dense format
        if not isinstance(data, list):
            raise RouterArtifactError(f"Invalid {field_name} format")
        
        dense = tuple(
            tuple(float(value) for value in row)
            for row in data
        )
        
        # Validate dimensions
        if len(dense) != len(labels):
            raise RouterArtifactError(
                f"{field_name} row count ({len(dense)}) doesn't match labels ({len(labels)})"
            )
        for row_idx, row in enumerate(dense):
            if len(row) != feature_count:
                raise RouterArtifactError(
                    f"{field_name} row {row_idx} has {len(row)} columns, expected {feature_count}"
                )
        
        # Create sparse representation for memory efficiency
        sparse = SparseMatrix.from_dense(dense)
        
        return dense, sparse
    
    
    @classmethod
    def _load_internet_weights(
        cls,
        payload: dict,
        feature_count: int,
    ) -> tuple[tuple[float, ...], SparseMatrix | None]:
        """Load internet weights (1D vector)."""
        data = payload.get("internet_weights", [])
        
        if isinstance(data, dict) and "indices" in data and "values" in data:
            # Sparse format
            indices = tuple(
                (0, int(idx)) for idx in data["indices"]
            )
            values = tuple(float(v) for v in data["values"])
            sparse = SparseMatrix(
                indices=indices,
                values=values,
                shape=(1, feature_count),
            )
            dense = tuple(sparse.to_dense()[0])
            return dense, sparse
        
        
        # Dense format
        dense = tuple(float(value) for value in data)
        if len(dense) != feature_count:
            raise RouterArtifactError(
                f"internet_weights has {len(dense)} elements, expected {feature_count}"
            )
        
        sparse = SparseMatrix.from_dense((dense,))
        return dense, sparse

    def decide(self, text: str) -> RouterDecision:
        """Make routing decision using sparse matrix for efficiency."""
        features = build_feature_vector(text, self.feature_count)
        
        # Use sparse matrix for dot product if available (faster for sparse data)
        if self.expert_weights_sparse is not None:
            scores = [
                self.expert_weights_sparse.dot(features, row_idx) + bias
                for row_idx, bias in enumerate(self.expert_bias)
            ]
        else:
            scores = [
                _dot(row, features) + bias
                for row, bias in zip(self.expert_weights, self.expert_bias, strict=True)
            ]
        
        
        best_index = max(range(len(scores)), key=scores.__getitem__)
        probabilities = _softmax(scores)
        
        # Internet prediction
        if self.internet_weights_sparse is not None:
            internet_logit = self.internet_weights_sparse.dot(features, 0) + self.internet_bias
        else:
            internet_logit = _dot(self.internet_weights, features) + self.internet_bias
        internet_probability = _sigmoid(internet_logit)
        
        return {
            "experts_needed": [ExpertId(self.labels[best_index])],
            "check_memory_first": True,
            "internet_needed": internet_probability >= 0.5,
            "confidence": max(self.confidence_floor, probabilities[best_index]),
            "reasoning_trace": (
                f"artifact-router:label={self.labels[best_index]}:"
                f"internet={internet_probability:.3f}:"
                f"sparsity={self.sparsity():.2%}"
            ),
        }
    
    def sparsity(self) -> float:
        """Return the sparsity ratio of the weight matrices."""
        if self.expert_weights_sparse is not None:
            return self.expert_weights_sparse.sparsity()
        # Calculate from dense
        total = sum(len(row) for row in self.expert_weights)
        zeros = sum(sum(1 for v in row if v == 0.0) for row in self.expert_weights)
        return zeros / total if total > 0 else 0.0
    
    def memory_savings(self) -> dict[str, float]:
        """Calculate memory savings from sparse representation."""
        dense_size = sum(
            len(row) * 8  # 8 bytes per float
            for row in self.expert_weights
        )
        dense_size += len(self.internet_weights) * 8
        
        sparse_size = 0
        if self.expert_weights_sparse is not None:
            # 8 bytes per value + 8 bytes per index pair (2 ints)
            sparse_size += len(self.expert_weights_sparse.values) * 8
            sparse_size += len(self.expert_weights_sparse.indices) * 8
        if self.internet_weights_sparse is not None:
            sparse_size += len(self.internet_weights_sparse.values) * 8
            sparse_size += len(self.internet_weights_sparse.indices) * 8
        
        savings = dense_size - sparse_size
        return {
            "dense_bytes": dense_size,
            "sparse_bytes": sparse_size,
            "savings_bytes": savings,
            "savings_percent": (savings / dense_size * 100) if dense_size > 0 else 0.0,
        }


def tokenize(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())


def build_feature_vector(text: str, feature_count: int) -> list[float]:
    vector = [0.0] * feature_count
    for token in tokenize(text):
        digest = _fnv1a(token)
        index = digest % feature_count
        sign = -1.0 if digest & (1 << 63) else 1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _fnv1a(token: str) -> int:
    value = _FNV_OFFSET
    for byte in token.encode("utf-8"):
        value ^= byte
        value = (value * _FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
    return value


def _dot(left: tuple[float, ...] | list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def _softmax(values: list[float]) -> list[float]:
    maximum = max(values)
    scaled = [math.exp(value - maximum) for value in values]
    total = sum(scaled) or 1.0
    return [value / total for value in scaled]


class RouterArtifactError(Exception):
    """Raised when router artifact validation fails."""
    pass


def convert_to_sparse_format(dense_payload: dict) -> dict:
    """Convert dense router payload to sparse format for storage."""
    result = {"version": ROUTER_ARTIFACT_VERSION}
    result["labels"] = dense_payload["labels"]
    result["feature_count"] = dense_payload["feature_count"]
    
    # Convert expert_weights to sparse
    expert_weights = dense_payload["expert_weights"]
    indices = []
    values = []
    for row_idx, row in enumerate(expert_weights):
        for col_idx, value in enumerate(row):
            if value != 0.0:
                indices.append([row_idx, col_idx])
                values.append(value)
    result["expert_weights"] = {"indices": indices, "values": values}
    
    # Convert internet_weights to sparse
    internet_weights = dense_payload.get("internet_weights", [])
    indices = []
    values = []
    for idx, value in enumerate(internet_weights):
        if value != 0.0:
            indices.append(idx)
            values.append(value)
    result["internet_weights"] = {"indices": indices, "values": values}
    
    result["expert_bias"] = dense_payload["expert_bias"]
    result["internet_bias"] = dense_payload.get("internet_bias", 0.0)
    result["confidence_floor"] = dense_payload.get("confidence_floor", 0.5)
    
    return result
