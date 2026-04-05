# Component 06 Skill: Internet Access Module

## Purpose
Provide controlled, rate-limited, cached internet retrieval that augments memory when internal confidence is low.

## Dependencies
- `duckduckgo_search`
- `httpx` (async client)
- `trafilatura`
- `asyncio`

## Required Files
- `brain/internet/search.py`
- `brain/internet/fetcher.py`
- `brain/internet/module.py`
- `tests/python/test_internet.py`

## Implementation Checklist
1. `search.py`:
   - Define `SearchResult` TypedDict: `url`, `title`, `snippet`.
   - Build `DuckDuckGoSearch.search(query, max_results) -> Result[list[SearchResult], str]`.
   - Apply token-bucket rate limit: max 5 searches/minute.
   - If `INTERNET_ALLOWED_DOMAINS` configured, filter result domains.
2. `fetcher.py`:
   - Define `FetchResult` TypedDict: `url`, `content`, `title`, `fetched_at`.
   - Build `ContentFetcher.fetch(url) -> Result[FetchResult, str]`.
   - Maintain in-memory cache keyed by URL hash with TTL (`INTERNET_CACHE_TTL_SECONDS`).
   - On cache hit, return cached result immediately.
   - On miss:
     - fetch with 10s timeout using `httpx.AsyncClient`.
     - extract main content via `trafilatura`.
     - if extraction returns `None`, return `err("Could not extract content from URL")`.
   - Distinct errors for timeout, HTTP errors, and extractor failures.
3. `module.py`:
   - Public class `InternetModule(enabled: bool)`.
   - `query(search_query, context) -> Result[InternetResult, str]`:
     - if disabled, `err("Internet access is disabled")`.
     - reformulate search query using context.
     - call search with `max_results=5`.
     - fetch top 3 URLs concurrently via `asyncio.gather`.
     - combine outputs into `InternetResult` with:
       - `query`
       - `results`
       - `combined_content`
       - `sources`
       - `retrieved_at`
   - `is_needed(memory_result, confidence_threshold) -> bool`:
     - true if no memory results or max confidence below threshold.

## Test Checklist
- Rate limiting: 6th search inside same minute is delayed/throttled.
- Fetch cache: second fetch same URL does not hit network.
- Disabled module returns immediate `err`.
- Integration test with mocked search/fetch combines content correctly.

## Pass Criteria
- Rate limiting and cache behavior are deterministic and test-covered.
- Internet module never throws bare exceptions on expected failures.
- Return shapes are stable typed dicts wrapped in `Result`.

## Premium Quality Gates (CLI)
- Static checks:
  - `python -m ruff check brain tests`
  - `python -m mypy brain`
- Targeted tests:
  - `python -m pytest tests/python/test_internet.py -q`
- Network-mocked reliability run:
  - run internet tests with `respx`/`pytest-httpx` only; avoid live network in CI.
- Merge gate:
  - 6th request rate-limit behavior is asserted.
  - cache-hit path proves second call avoids outbound HTTP.
