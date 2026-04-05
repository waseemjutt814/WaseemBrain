from __future__ import annotations

from .fetcher import ContentFetcher
from .module import InternetModule
from .search import DuckDuckGoSearch
from .types import FetchResult, InternetResult, SearchResult

__all__ = [
    "ContentFetcher",
    "DuckDuckGoSearch",
    "FetchResult",
    "InternetModule",
    "InternetResult",
    "SearchResult",
]
