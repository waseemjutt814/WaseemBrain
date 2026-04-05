from __future__ import annotations

import re
from collections.abc import Sequence

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_./-]{2,}")
_IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CAMEL_BOUNDARY_PATTERN = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_GENERIC_SYMBOL_PATTERNS = (
    re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*(?:[._/-][A-Za-z0-9_]+)+)\b"),
    re.compile(r"\b([A-Z][A-Za-z0-9]+(?:[A-Z][A-Za-z0-9]+)+)\b"),
    re.compile(r"\b([a-z]+(?:[A-Z][A-Za-z0-9]+)+)\b"),
)
_DECLARATION_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    ".py": (
        re.compile(r"^\s*(?:async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("),
        re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
    ),
    ".ts": (
        re.compile(
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\("
        ),
        re.compile(
            r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*="
        ),
        re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][A-Za-z0-9_$]*)\b"),
        re.compile(r"^\s*(?:export\s+)?interface\s+([A-Za-z_$][A-Za-z0-9_$]*)\b"),
        re.compile(r"^\s*(?:export\s+)?type\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*="),
    ),
    ".tsx": (
        re.compile(
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\("
        ),
        re.compile(
            r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*="
        ),
        re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][A-Za-z0-9_$]*)\b"),
    ),
    ".js": (
        re.compile(
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\("
        ),
        re.compile(
            r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*="
        ),
        re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][A-Za-z0-9_$]*)\b"),
    ),
    ".jsx": (
        re.compile(
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\("
        ),
        re.compile(
            r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*="
        ),
        re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][A-Za-z0-9_$]*)\b"),
    ),
    ".rs": (
        re.compile(r"^\s*(?:pub\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*[<(]"),
        re.compile(r"^\s*(?:pub\s+)?struct\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
        re.compile(r"^\s*(?:pub\s+)?enum\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
        re.compile(r"^\s*(?:pub\s+)?trait\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
        re.compile(r"^\s*impl\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
    ),
}


def extract_workspace_symbols(text: str, suffix: str) -> list[str]:
    patterns = _DECLARATION_PATTERNS.get(suffix.lower(), ())
    seen: set[str] = set()
    symbols: list[str] = []
    for line in text.splitlines()[:2000]:
        for pattern in patterns:
            match = pattern.search(line)
            if not match:
                continue
            symbol = match.group(1)
            if symbol not in seen:
                seen.add(symbol)
                symbols.append(symbol)
    return symbols[:32]


def extract_inline_symbols(text: str) -> list[str]:
    seen: set[str] = set()
    symbols: list[str] = []
    for pattern in _GENERIC_SYMBOL_PATTERNS:
        for match in pattern.finditer(text):
            symbol = match.group(1)
            if symbol in seen:
                continue
            seen.add(symbol)
            symbols.append(symbol)
    return symbols[:32]


def query_terms(text: str) -> set[str]:
    terms: set[str] = set()
    for token in _TOKEN_PATTERN.findall(text):
        lowered = token.lower()
        terms.add(lowered)
        terms.update(identifier_terms(token))
    return {term for term in terms if len(term) >= 2}


def identifier_terms(identifier: str) -> set[str]:
    normalized = identifier.replace("\\", "/").replace("-", " ").replace("/", " ")
    normalized = normalized.replace(".", " ").replace("_", " ")
    split_parts = _CAMEL_BOUNDARY_PATTERN.sub(" ", normalized)
    parts = {
        match.group(0).lower()
        for match in _IDENTIFIER_PATTERN.finditer(split_parts)
        if len(match.group(0)) >= 2
    }
    return parts


def match_symbols(query_text: str | set[str], symbols: Sequence[str], *, limit: int = 3) -> list[str]:
    query_term_set = query_text if isinstance(query_text, set) else query_terms(query_text)
    ranked: list[tuple[float, str]] = []
    for symbol in symbols:
        terms = identifier_terms(symbol)
        if not terms:
            continue
        overlap = len(query_term_set & terms)
        if overlap <= 0:
            continue
        score = overlap + (0.25 if symbol.lower() in query_term_set else 0.0)
        ranked.append((score, symbol))
    ranked.sort(key=lambda item: (-item[0], item[1].lower()))
    return [symbol for _, symbol in ranked[:limit]]
