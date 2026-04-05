from __future__ import annotations

import re

from ..code_symbols import extract_inline_symbols, identifier_terms, query_terms

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_./-]{2,}")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "be",
    "bro",
    "by",
    "do",
    "for",
    "from",
    "he",
    "hello",
    "help",
    "hi",
    "how",
    "i",
    "in",
    "is",
    "it",
    "jani",
    "me",
    "my",
    "of",
    "on",
    "or",
    "please",
    "same",
    "that",
    "the",
    "this",
    "to",
    "we",
    "what",
    "where",
    "who",
    "why",
    "with",
    "you",
    "your",
}


def query_coverage_score(query: str, response: str) -> float:
    query_terms = _informative_query_terms(query)
    if not query_terms:
        return 0.0
    response_terms = set(_tokenize(response))
    hits = sum(1 for term in query_terms if term in response_terms)
    return round(hits / len(query_terms), 4)


def entity_match_score(query: str, response: str) -> float:
    anchor_terms = _anchor_terms(query)
    if not anchor_terms:
        return 0.0
    response_terms = set(_tokenize(response))
    hits = sum(1 for term in anchor_terms if term in response_terms)
    return round(hits / len(anchor_terms), 4)


def symbol_anchor_score(query: str, response: str) -> float:
    query_term_set = {term for term in query_terms(query) if term not in _STOPWORDS}
    if not query_term_set:
        return 0.0
    best_score = 0.0
    for symbol in extract_inline_symbols(response):
        symbol_terms = identifier_terms(symbol)
        if not symbol_terms:
            continue
        overlap = len(query_term_set & symbol_terms)
        if overlap <= 0:
            continue
        coverage = overlap / len(symbol_terms)
        best_score = max(best_score, coverage)
    return round(best_score, 4)


def _informative_query_terms(query: str) -> list[str]:
    terms: list[str] = []
    for token in _tokenize(query):
        if token in _STOPWORDS:
            continue
        if len(token) >= 3 or _looks_like_anchor(token):
            if token not in terms:
                terms.append(token)
    return terms


def _anchor_terms(query: str) -> list[str]:
    terms: list[str] = []
    for token in _tokenize(query):
        if _looks_like_anchor(token) and token not in terms:
            terms.append(token)
    return terms


def _looks_like_anchor(token: str) -> bool:
    return any(marker in token for marker in ("_", ".", "/", "-")) or any(
        character.isdigit() for character in token
    )


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_PATTERN.findall(text)]
