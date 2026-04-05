from __future__ import annotations

import asyncio
import hashlib
import re
import time
from collections.abc import Callable
from html.parser import HTMLParser
from urllib.request import Request, urlopen

from ..config import BrainSettings, load_settings
from ..types import Result, err, ok
from .types import FetchResult


class _HtmlTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        self.parts.append(text)
        if self._in_title and not self.title:
            self.title = text


class ContentFetcher:
    def __init__(
        self,
        settings: BrainSettings | None = None,
        fetch_backend: Callable[[str], str] | None = None,
        extractor: Callable[[str], tuple[str, str]] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        self._fetch_backend = fetch_backend or self._fetch_with_available_backend
        self._extractor = extractor or self._extract_content
        self._clock = clock or time.time
        self._cache: dict[str, tuple[FetchResult, float]] = {}

    async def fetch(self, url: str) -> Result[FetchResult, str]:
        cache_key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        now = self._clock()
        cached = self._cache.get(cache_key)
        if cached is not None and now - cached[1] <= self._settings.internet_cache_ttl_seconds:
            return ok(cached[0])

        try:
            html = await asyncio.to_thread(self._fetch_backend, url)
        except TimeoutError:
            return err("Timed out while fetching URL")
        except Exception as exc:
            return err(f"HTTP fetch failed: {exc}")

        try:
            content, title = self._extractor(html)
        except Exception as exc:
            return err(f"Content extraction failed: {exc}")
        if not content.strip():
            return err("Could not extract content from URL")

        result: FetchResult = {
            "url": url,
            "content": content.strip(),
            "title": title,
            "fetched_at": now,
        }
        self._cache[cache_key] = (result, now)
        return ok(result)

    def _fetch_with_available_backend(self, url: str) -> str:
        try:
            import httpx
        except Exception:
            request = Request(url, headers={"User-Agent": self._settings.http_user_agent})
            with urlopen(request, timeout=self._settings.http_timeout_sec) as response:
                return response.read().decode("utf-8", errors="ignore")

        with httpx.Client(
            timeout=self._settings.http_timeout_sec,
            follow_redirects=True,
            headers={"User-Agent": self._settings.http_user_agent},
        ) as client:
            try:
                response = client.get(url)
                response.raise_for_status()
                return response.text
            except httpx.ConnectError as exc:
                if not self._settings.http_allow_insecure_tls or not self._is_tls_error(exc):
                    raise

        with httpx.Client(
            timeout=self._settings.http_timeout_sec,
            follow_redirects=True,
            verify=False,
            headers={"User-Agent": self._settings.http_user_agent},
        ) as fallback_client:
            response = fallback_client.get(url)
            response.raise_for_status()
            return response.text

    def _is_tls_error(self, exc: Exception) -> bool:
        return "CERTIFICATE_VERIFY_FAILED" in str(exc).upper()

    def _extract_content(self, html: str) -> tuple[str, str]:
        try:
            import trafilatura  # type: ignore
        except Exception:
            parser = _HtmlTextParser()
            parser.feed(html)
            text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
            return text, parser.title

        content = trafilatura.extract(html, include_tables=True, include_comments=False)
        metadata = trafilatura.extract_metadata(html)
        title = "" if metadata is None else str(getattr(metadata, "title", "") or "")
        return content or "", title
