from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TypedDict

from ..config import BrainSettings, load_settings
from ..experts.system_ops import SystemOperations
from ..locale import LocaleEngine
from ..types import EvidenceReference
from .types import AssistantRoute

try:
    from agents_and_runners.reasoning_engine import ReasoningDepth, ReasoningEngine
except Exception:
    ReasoningDepth = None  # type: ignore[assignment]
    ReasoningEngine = None  # type: ignore[assignment]

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_./-]{2,}")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "bat",
    "bro",
    "can",
    "code",
    "compile",
    "difference",
    "do",
    "explain",
    "failure",
    "feature",
    "fix",
    "for",
    "give",
    "hai",
    "he",
    "help",
    "how",
    "i",
    "implement",
    "is",
    "ka",
    "ke",
    "ki",
    "kya",
    "list",
    "main",
    "me",
    "my",
    "name",
    "of",
    "or",
    "refactor",
    "related",
    "tell",
    "test",
    "the",
    "to",
    "ur",
    "what",
    "whats",
    "who",
    "write",
    "you",
    "your",
}


class LocalResponderResult(TypedDict):
    content: str
    citations: list[EvidenceReference]
    tools: list[str]


class RepoHit(TypedDict):
    raw: str
    path: str
    line_number: int | None
    snippet: str
    category: str


class RepoContextFile(TypedDict):
    path: str
    line_number: int | None
    snippet: str
    content: str
    category: str


class LocalResponder:
    def __init__(self, *, settings: BrainSettings | None = None) -> None:
        self._settings = settings or load_settings()
        self._knowledge_cards = self._load_general_knowledge()
        self._reasoning_engine = self._build_reasoning_engine()

    def respond(self, query: str, route: AssistantRoute) -> LocalResponderResult | None:
        text = query.strip()
        if not text:
            return None

        direct = self._direct_response(text)
        if direct is not None:
            return direct

        if route in {"general_chat", "grounded_answer"}:
            knowledge = self._knowledge_response(text)
            if knowledge is not None:
                return knowledge

        if route in {"coding", "repo_work"}:
            return self._workspace_response(text, route)

        if route == "general_chat":
            return self._conversational_response(text)

        return None

    def _direct_response(self, query: str) -> LocalResponderResult | None:
        locale = LocaleEngine.detect_locale(query)
        lowered = query.lower()
        if self._is_identity_query(lowered):
            return self._identity_response(locale)
        if self._is_capabilities_query(lowered):
            return self._capabilities_response(locale)
        if self._is_greeting_or_wellbeing(lowered):
            return self._greeting_response(locale)
        if any(token in lowered for token in ("thanks", "thank you", "shukria", "jazak")):
            return self._thanks_response(locale)
        return None

    def _knowledge_response(self, query: str) -> LocalResponderResult | None:
        query_terms = self._informative_terms(query)
        if not query_terms or not self._knowledge_cards:
            return None

        matches: list[tuple[float, dict[str, object]]] = []
        for card in self._knowledge_cards:
            title = str(card.get("title", ""))
            content = str(card.get("content", ""))
            tags = [str(tag) for tag in card.get("tags", []) if isinstance(tag, str)]
            haystack = " ".join([title, content, *tags]).lower()
            overlap = sum(1 for term in query_terms if term in haystack)
            if overlap <= 0:
                continue
            score = overlap / len(query_terms)
            if score >= 0.34:
                matches.append((score, card))

        if not matches:
            return None

        matches.sort(key=lambda item: item[0], reverse=True)
        top_cards = [card for _, card in matches[:2]]
        citations = [self._knowledge_citation(card) for card in top_cards]
        locale = LocaleEngine.detect_locale(query)
        if locale == "ur":
            lead = "Mere built-in local knowledge se ye relevant grounded info mili:"
            closing = "Agar aap chahein to main is topic ko simple explanation, comparison, ya coding context me bhi convert kar sakta hoon."
        else:
            lead = "I found a relevant answer in the built-in local knowledge cards:"
            closing = "If you want, I can turn this into a simpler explanation, a comparison, or connect it back to the current codebase."
        return {
            "content": "\n".join(
                [lead, *[f"- {self._summarise_card(card)}" for card in top_cards], closing]
            ),
            "citations": citations,
            "tools": ["local-knowledge"],
        }

    def _workspace_response(self, query: str, route: AssistantRoute) -> LocalResponderResult:
        locale = LocaleEngine.detect_locale(query)
        summary = SystemOperations.repo_summary(self._settings.repo_root)
        explicit_file = self._explicit_file_context(query)
        if explicit_file is not None:
            context_files = [explicit_file]
            citations = [self._file_context_citation(explicit_file)]
            hits: list[RepoHit] = []
        else:
            hits = self._collect_repo_hits(query)
            context_files = self._read_hit_contexts(hits[:3])
            citations = [self._repo_citation(hit["raw"]) for hit in hits[:4]]
        reasoning = self._reason_about_repo(query, context_files)
        top_level = summary.get("top_level_counts", {})
        top_level_preview = ", ".join(
            f"{name}={count}" for name, count in list(top_level.items())[:4]
        )

        if locale == "ur":
            lead = "Main ne guess karne ke bajaye workspace ke against inspect kiya."
            if context_files:
                detail_title = "Mere liye abhi sab se relevant touch points ye hain:"
                why_title = "Meri logic:"
                next_title = "Practical next move:"
                next_step = self._next_step_text(locale, route, context_files)
                lines = [
                    lead,
                    detail_title,
                    *[f"- {self._format_context_file(item)}" for item in context_files],
                    why_title,
                    f"- {reasoning}",
                    next_title,
                    f"- {next_step}",
                    f"Repo snapshot: branch {summary.get('branch', 'unknown')}, {summary.get('total_files', 0)} files, top areas {top_level_preview or 'n/a'}.",
                ]
            else:
                lines = [
                    lead,
                    f'Main ne "{query}" ke liye repo search chalayi lekin strong source-level match nahi mila.',
                    f"Repo snapshot: branch {summary.get('branch', 'unknown')}, {summary.get('total_files', 0)} files, top areas {top_level_preview or 'n/a'}.",
                    "Agar aap file name, function, error text, ya feature area dein to main us par focused coding help dunga.",
                ]
        else:
            lead = "I inspected the workspace instead of guessing."
            if context_files:
                detail_title = "These look like the best touch points right now:"
                why_title = "Why I think these matter:"
                next_title = "Practical next move:"
                next_step = self._next_step_text(locale, route, context_files)
                lines = [
                    lead,
                    detail_title,
                    *[f"- {self._format_context_file(item)}" for item in context_files],
                    why_title,
                    f"- {reasoning}",
                    next_title,
                    f"- {next_step}",
                    f"Repo snapshot: branch {summary.get('branch', 'unknown')}, {summary.get('total_files', 0)} files, top areas {top_level_preview or 'n/a'}.",
                ]
            else:
                lines = [
                    lead,
                    f'I ran a repo search for "{query}" but did not find a strong source-level match yet.',
                    f"Repo snapshot: branch {summary.get('branch', 'unknown')}, {summary.get('total_files', 0)} files, top areas {top_level_preview or 'n/a'}.",
                    "Give me a file name, function, error, or feature area and I can turn this into a focused coding investigation.",
                ]

        tools = ["workspace-search", "workspace-summary"]
        if self._reasoning_engine is not None and context_files:
            tools.append("local-reasoning")
        return {
            "content": "\n".join(lines),
            "citations": citations,
            "tools": tools,
        }

    def _conversational_response(self, query: str) -> LocalResponderResult:
        locale = LocaleEngine.detect_locale(query)
        summary = SystemOperations.repo_summary(self._settings.repo_root)
        top_level = summary.get("top_level_counts", {})
        top_level_preview = ", ".join(
            f"{name}={count}" for name, count in list(top_level.items())[:4]
        )
        if locale == "ur":
            content = (
                f"Main aap ke sath hoon. Local mode me main vague filler ke bajaye logic ke sath jawab deta hoon. "
                f"Abhi repo me {summary.get('total_files', 0)} files hain aur top areas {top_level_preview or 'n/a'} hain. "
                f"Agar aap brainstorming, explanation, ya coding task ko practical step me convert karna chahein to main usko structure kar dunga."
            )
        else:
            content = (
                f"I am with you. In local mode I focus on logic instead of filler. "
                f"Right now the repo has {summary.get('total_files', 0)} files and top areas {top_level_preview or 'n/a'}. "
                f"If you want to brainstorm, explain an idea, or turn a vague coding task into concrete steps, I can structure it with you."
            )
        return {
            "content": content,
            "citations": [],
            "tools": ["workspace-summary"],
        }

    def _identity_response(self, locale: str) -> LocalResponderResult:
        citation = self._find_knowledge_citation("capabilities")
        content = (
            "Main Waseem Brain hoon. Main local-first assistant runtime hoon jo chat, coding help, repo inspection, planning, memory recall, aur protected system actions me help karta hai."
            if locale == "ur"
            else "I am Waseem Brain, a local-first assistant runtime for conversation, coding help, repo inspection, planning, memory recall, and protected system actions."
        )
        return {
            "content": content,
            "citations": [citation] if citation is not None else [],
            "tools": ["local-identity"],
        }

    def _capabilities_response(self, locale: str) -> LocalResponderResult:
        citation = self._find_knowledge_citation("capabilities")
        content = (
            "Main workspace-grounded coding help, repo search, file explanation, memory recall, planning, aur approved system actions preview/execute kar sakta hoon."
            if locale == "ur"
            else "I can do workspace-grounded coding help, repo search, file explanation, memory recall, planning, and approved system actions with preview and confirmation."
        )
        return {
            "content": content,
            "citations": [citation] if citation is not None else [],
            "tools": ["local-capabilities"],
        }

    def _greeting_response(self, locale: str) -> LocalResponderResult:
        citation = self._find_knowledge_citation("greeting")
        content = (
            "Main yahan hoon aur ready hoon. Seedha bol dein kya banana, kya samajhna, ya kis file me jana hai, phir main wahi se kaam start karunga."
            if locale == "ur"
            else "I am here and ready. Tell me what to build, what to explain, or which file to enter, and I will start from there."
        )
        return {
            "content": content,
            "citations": [citation] if citation is not None else [],
            "tools": ["local-greeting"],
        }

    def _thanks_response(self, locale: str) -> LocalResponderResult:
        content = (
            "Khushi hui. Agla step bol dein, main wahi se continue karta hoon."
            if locale == "ur"
            else "Happy to help. Tell me the next step and I will continue from there."
        )
        return {
            "content": content,
            "citations": [],
            "tools": ["local-conversation"],
        }

    def _build_reasoning_engine(self) -> ReasoningEngine | None:
        if ReasoningEngine is None:
            return None
        try:
            return ReasoningEngine(self._settings.repo_root)
        except Exception:
            return None

    def _collect_repo_hits(self, query: str) -> list[RepoHit]:
        query_terms = self._informative_terms(query)
        search_patterns = self._search_patterns(query)
        hits: list[RepoHit] = []
        seen_hits: set[str] = set()

        for pattern in search_patterns:
            try:
                result = SystemOperations.search_repo(self._settings.repo_root, pattern, max_hits=20)
            except ValueError:
                continue
            pattern_hits = []
            for raw_hit in result["matches"]:
                parsed = self._parse_hit(raw_hit)
                if self._skip_hit(parsed) or parsed["raw"] in seen_hits:
                    continue
                pattern_hits.append(parsed)
            pattern_hits.sort(key=lambda item: self._candidate_rank(item, query_terms))
            inserted = 0
            for parsed in pattern_hits:
                seen_hits.add(parsed["raw"])
                hits.append(parsed)
                inserted += 1
                if inserted >= 2 or len(hits) >= 12:
                    break
            if len(hits) >= 12:
                break

        hits.sort(key=lambda item: self._candidate_rank(item, query_terms))
        return hits

    def _explicit_file_context(self, query: str) -> RepoContextFile | None:
        for match in re.finditer(r'[A-Za-z0-9_./\\-]+\.[A-Za-z0-9_]+', query):
            candidate = match.group(0).strip().replace('\\', '/')
            try:
                payload = SystemOperations.read_workspace_file(self._settings.repo_root, candidate, start_line=1, end_line=80)
            except ValueError:
                continue
            excerpt = payload.get('excerpt', [])
            if not isinstance(excerpt, list):
                excerpt = []
            joined_excerpt = ' '.join(str(line).split(': ', 1)[-1].strip() for line in excerpt if str(line).strip())
            return {
                'path': str(payload.get('path', candidate)),
                'line_number': int(payload.get('start_line', 1)) or 1,
                'snippet': self._trim(joined_excerpt, limit=140),
                'content': joined_excerpt,
                'category': self._path_category(str(payload.get('path', candidate))),
            }
        return None

    def _read_hit_contexts(self, hits: list[RepoHit]) -> list[RepoContextFile]:
        contexts: list[RepoContextFile] = []
        for hit in hits:
            relative_path = Path(hit["path"])
            absolute_path = self._settings.repo_root / relative_path
            if not absolute_path.exists() or not absolute_path.is_file():
                continue
            try:
                lines = absolute_path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            line_number = hit["line_number"]
            if line_number is None or line_number <= 0:
                window = lines[:16]
            else:
                start = max(line_number - 3, 0)
                end = min(line_number + 3, len(lines))
                window = lines[start:end]
            snippet = " ".join(line.strip() for line in window if line.strip())
            contexts.append(
                {
                    "path": hit["path"],
                    "line_number": hit["line_number"],
                    "snippet": hit["snippet"],
                    "content": snippet,
                    "category": hit["category"],
                }
            )
        return contexts

    def _reason_about_repo(self, query: str, context_files: list[RepoContextFile]) -> str:
        if not context_files:
            return "I do not have enough grounded source context yet, so I would want a file name, function, or error next."

        if self._reasoning_engine is not None and ReasoningDepth is not None:
            try:
                reasoning = self._reasoning_engine.analyze(
                    query,
                    context={
                        "files": [
                            {
                                "path": item["path"],
                                "content": item["content"],
                            }
                            for item in context_files
                        ]
                    },
                    depth=ReasoningDepth.STANDARD,
                )
                if reasoning.conclusion.strip():
                    recommendation = reasoning.recommendations[0] if reasoning.recommendations else ""
                    pieces = [reasoning.conclusion.strip()]
                    if recommendation:
                        pieces.append(recommendation.strip())
                    return " ".join(piece for piece in pieces if piece)
            except Exception:
                pass

        top = context_files[0]
        return (
            f'The query overlaps most strongly with {top["path"]}'
            + (f' near line {top["line_number"]}' if top["line_number"] else "")
            + f' because the local text mentions: {self._trim(top["snippet"], limit=140)}.'
        )

    def _next_step_text(self, locale: str, route: AssistantRoute, context_files: list[RepoContextFile]) -> str:
        target = context_files[0]["path"] if context_files else "the strongest matching file"
        if locale == "ur":
            if route == "coding":
                return f"Start {target} se karein, phir exact function ya change bata kar implementation side par jayen."
            return f"Start {target} se karein aur phir main isi context me detail explain kar dunga."
        if route == "coding":
            return f"Start with {target}, then name the exact function or change and I can turn this into implementation work."
        return f"Start with {target}, and I can keep the explanation grounded in that context."

    def _load_general_knowledge(self) -> list[dict[str, object]]:
        knowledge_path = self._settings.expert_dir.parent / "bootstrap" / "general-knowledge.json"
        if not knowledge_path.exists():
            return []
        try:
            payload = json.loads(knowledge_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        cards = payload.get("cards", [])
        return [card for card in cards if isinstance(card, dict)]

    def _find_knowledge_citation(self, keyword: str) -> EvidenceReference | None:
        lowered = keyword.lower()
        for card in self._knowledge_cards:
            title = str(card.get("title", "")).lower()
            tags = [str(tag).lower() for tag in card.get("tags", []) if isinstance(tag, str)]
            if lowered in title or lowered in tags:
                return self._knowledge_citation(card)
        return None

    def _knowledge_citation(self, card: dict[str, object]) -> EvidenceReference:
        title = str(card.get("title", "Local Knowledge"))
        card_id = str(card.get("id", title))
        content = str(card.get("content", "")).strip()
        return {
            "id": card_id,
            "source_type": "knowledge",
            "label": title,
            "snippet": self._trim(content),
            "uri": f"knowledge://general-knowledge/{card_id}",
        }

    def _skip_hit(self, hit: RepoHit) -> bool:
        path = hit["path"].replace("\\", "/").lower()
        return any(marker in path for marker in ("/logs/", "/dist/", "/build/", ".egg-info/"))

    def _hit_priority(self, hit: str) -> tuple[int, str]:
        path = hit.split(":", 2)[0].replace("\\", "/").lower()
        if any(marker in path for marker in ("/brain/", "/interface/", "/scripts/", "/agents_and_runners/", "/src/")):
            return (0, path)
        if "/tests/" in path:
            return (15, path)
        if any(marker in path for marker in ("/docs/", "/readme", "/README")):
            return (25, path)
        return (5, path)

    def _candidate_rank(self, hit: RepoHit, query_terms: list[str]) -> tuple[int, int, str]:
        overlap = self._hit_overlap_score(hit, query_terms)
        priority, path = self._hit_priority(hit["raw"])
        return (-overlap, priority, path)

    def _hit_overlap_score(self, hit: RepoHit, query_terms: list[str]) -> int:
        haystack = f"{hit['path']} {hit['snippet']}".lower()
        return sum(1 for term in query_terms if term in haystack)

    def _parse_hit(self, raw_hit: str) -> RepoHit:
        parts = raw_hit.split(":", 2)
        if len(parts) == 3 and parts[1].isdigit():
            path, raw_line, snippet = parts
            line_number = int(raw_line)
        else:
            path, line_number, snippet = raw_hit, None, raw_hit
        category = self._path_category(path)
        return {
            "raw": raw_hit,
            "path": path,
            "line_number": line_number,
            "snippet": snippet.strip(),
            "category": category,
        }

    def _path_category(self, path: str) -> str:
        normalized = path.replace("\\", "/").lower()
        if "/tests/" in normalized:
            return "test"
        if any(marker in normalized for marker in ("/docs/", "readme")):
            return "docs"
        if any(marker in normalized for marker in ("/brain/", "/interface/", "/scripts/", "/agents_and_runners/", "/src/")):
            return "source"
        return "other"

    def _file_context_citation(self, item: RepoContextFile) -> EvidenceReference:
        label = f"{item['path']}:{item['line_number']}" if item.get('line_number') else item['path']
        return {
            'id': label,
            'source_type': 'workspace',
            'label': label,
            'snippet': self._trim(item.get('snippet', '')),
            'uri': item['path'],
        }

    def _repo_citation(self, raw_hit: str) -> EvidenceReference:
        parts = raw_hit.split(":", 2)
        if len(parts) == 3 and parts[1].isdigit():
            path, line_number, snippet = parts
            label = f"{path}:{line_number}"
            uri = path
        else:
            label = raw_hit
            snippet = raw_hit
            uri = raw_hit
        return {
            "id": label,
            "source_type": "workspace",
            "label": label,
            "snippet": self._trim(snippet.strip()),
            "uri": uri,
        }

    def _format_context_file(self, item: RepoContextFile) -> str:
        location = f'{item["path"]}:{item["line_number"]}' if item["line_number"] else item["path"]
        return f'{location} ({item["category"]}) -> {self._trim(item["snippet"], limit=120)}'

    def _summarise_card(self, card: dict[str, object]) -> str:
        title = str(card.get("title", "Knowledge Card")).strip()
        content = self._trim(str(card.get("content", "")).strip(), limit=220)
        return f"{title}: {content}"

    def _search_patterns(self, query: str) -> list[str]:
        patterns: list[str] = []
        quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', query)
        for left, right in quoted:
            value = (left or right).strip()
            if value:
                patterns.append(value)
        terms = self._informative_terms(query)
        if len(terms) >= 2:
            patterns.append(" ".join(terms[:2]))
        if len(terms) >= 3:
            patterns.append(" ".join(terms[:3]))
        for term in terms[:6]:
            if term not in patterns:
                patterns.append(term)
        deduped: list[str] = []
        seen: set[str] = set()
        for pattern in patterns:
            normalized = pattern.strip()
            lowered = normalized.lower()
            if not normalized or lowered in seen:
                continue
            seen.add(lowered)
            deduped.append(normalized)
        return deduped

    def _informative_terms(self, query: str) -> list[str]:
        terms: list[str] = []
        for token in _TOKEN_PATTERN.findall(query):
            lowered = token.lower()
            if lowered in _STOPWORDS:
                continue
            if len(lowered) < 3 and "." not in lowered and "/" not in lowered:
                continue
            if lowered not in terms:
                terms.append(lowered)
        return terms

    def _is_identity_query(self, lowered: str) -> bool:
        return any(
            phrase in lowered
            for phrase in ("what is your name", "what's your name", "whats ur name", "who are you", "your name")
        )

    def _is_capabilities_query(self, lowered: str) -> bool:
        return any(
            phrase in lowered
            for phrase in ("what can you do", "help me", "capabilities", "how to use", "what do you do", "can you code")
        )

    def _is_greeting_or_wellbeing(self, lowered: str) -> bool:
        return any(token in lowered for token in ("hello", "hi", "hey", "salam", "assalam", "how are you", "r u", "are you there"))

    def _trim(self, text: str, *, limit: int = 180) -> str:
        collapsed = " ".join(text.split())
        if len(collapsed) <= limit:
            return collapsed
        return f"{collapsed[: limit - 3].rstrip()}..."

