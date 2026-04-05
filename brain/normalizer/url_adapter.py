from __future__ import annotations

import re
import time
from collections.abc import Callable
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..config import BrainSettings, load_settings
from ..types import NormalizedSignal, Result, err, ok
from .base import InputAdapter


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.title: str = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        cleaned = data.strip()
        if not cleaned:
            return
        self.parts.append(cleaned)
        if self._in_title and not self.title:
            self.title = cleaned


class UrlAdapter(InputAdapter):
    def __init__(
        self,
        settings: BrainSettings | None = None,
        fetcher: Callable[[str], str] | None = None,
        extractor: Callable[[str], tuple[str, str | None]] | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        self._fetcher = fetcher or self._fetch_html
        self._extractor = extractor or self._extract_content

    def normalize(self, raw_input: object) -> Result[NormalizedSignal, str]:
        if not isinstance(raw_input, str):
            return err("UrlAdapter expects a URL string")
        try:
            html = self._fetcher(raw_input)
        except TimeoutError:
            return err("URL fetch timed out after 10 seconds")
        except HTTPError as exc:
            return err(f"URL fetch failed with HTTP status {exc.code}")
        except URLError as exc:
            return err(f"URL fetch failed: {exc.reason}")
        except Exception as exc:
            return err(f"URL fetch failed: {exc}")

        try:
            content, title = self._extractor(html)
        except Exception as exc:
            return err(f"URL content extraction failed: {exc}")
        if not content.strip():
            return err("Could not extract content from URL")

        return ok(
            {
                "text": content.strip(),
                "modality": "url",
                "metadata": {
                    "title": title,
                    "fetched_at": time.time(),
                    "source_url": raw_input,
                },
            }
        )

    def _fetch_html(self, url: str) -> str:
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

    def _extract_content(self, html: str) -> tuple[str, str | None]:
        try:
            import trafilatura  # type: ignore
        except Exception:
            parser = _TextExtractor()
            parser.feed(html)
            text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
            return text, parser.title or None

        extracted = trafilatura.extract(html, include_comments=False, include_tables=True)
        metadata = trafilatura.extract_metadata(html)
        title = None if metadata is None else getattr(metadata, "title", None)
        return (extracted or ""), title
