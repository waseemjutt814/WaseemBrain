from __future__ import annotations

from typing import TypedDict

from ..types import EvidenceReference


class SearchResult(TypedDict):
    url: str
    title: str
    snippet: str


class FetchResult(TypedDict):
    url: str
    content: str
    title: str
    fetched_at: float


class InternetResult(TypedDict):
    query: str
    results: list[FetchResult]
    combined_content: str
    sources: list[str]
    retrieved_at: float
    citations: list[EvidenceReference]
