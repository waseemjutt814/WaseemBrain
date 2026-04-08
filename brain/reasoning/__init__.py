"""Reasoning and Intelligence Subsystem for Waseem Brain.

High-level reasoner combining chain-of-thought, logical inference,
knowledge datasets, and quality evaluation.
"""

from .chain_of_thought import ChainOfThoughtReasoner, ReasoningType, ReasoningResult
from .logical_inference import (
    LogicalKnowledgeBase,
    ForwardChainingEngine,
    BackwardChainingEngine,
    ConstraintSatisfactionEngine,
)
from ..knowledge.knowledge_datasets import (
    get_logic_dataset,
    get_math_dataset,
    get_programming_dataset,
    get_science_dataset,
    get_all_datasets,
)
from ..quality.quality_evaluator import ReasoningQualityEvaluator, ReasoningQualityReport

__all__ = [
    "ChainOfThoughtReasoner",
    "ReasoningType",
    "ReasoningResult",
    "LogicalKnowledgeBase",
    "ForwardChainingEngine",
    "BackwardChainingEngine",
    "ConstraintSatisfactionEngine",
    "get_logic_dataset",
    "get_math_dataset",
    "get_programming_dataset",
    "get_science_dataset",
    "get_all_datasets",
    "ReasoningQualityEvaluator",
    "ReasoningQualityReport",
]
