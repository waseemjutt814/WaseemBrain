"""Knowledge system for Waseem Brain.

Structured knowledge datasets for logic, mathematics, programming,
science, and reasoning patterns.
"""

from .knowledge_datasets import (
    get_logic_dataset,
    get_math_dataset,
    get_programming_dataset,
    get_science_dataset,
    get_all_datasets,
    get_dataset_summary,
)

__all__ = [
    "get_logic_dataset",
    "get_math_dataset",
    "get_programming_dataset",
    "get_science_dataset",
    "get_all_datasets",
    "get_dataset_summary",
]
