from __future__ import annotations

import importlib
import json
import re
import time
from pathlib import Path
from typing import Protocol, cast

from ..code_symbols import extract_workspace_symbols, match_symbols, query_terms
from ..config import BrainSettings, load_settings
from ..locale import LocaleEngine
from ..types import EvidenceReference, ExpertOutput, Result, err, ok
from .types import ExpertMeta, ExpertRequest

_EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "data",
    "dist",
    "node_modules",
    "target",
    "tmp",
}
_KNOWLEDGE_MODULES = {
    "security-knowledge": ("experts.base.cybersecurity_expert", "CybersecurityExpert"),
    "crypto-knowledge": ("experts.base.cryptography_expert", "CryptographyExpert"),
    "algorithms-knowledge": ("experts.base.algorithms_expert", "AlgorithmsExpert"),
    "engineering-knowledge": ("experts.base.engineering_expert", "SystemEngineeringExpert"),
    "advanced-security-knowledge": ("experts.base.advanced_security_expert", "AdvancedSecurityExpert"),
}

_TEXT_EXTENSIONS = {
    ".cjs",
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".rs",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


class UnsupportedQueryError(RuntimeError):
    pass


class _ExpertSession(Protocol):
    runtime_backend_name: str

    def run(
        self,
        query: str,
        *,
        max_tokens: int,
        context: ExpertRequest | None,
    ) -> tuple[str, list[EvidenceReference], str]: ...


class Expert:
    def __init__(
        self,
        meta: ExpertMeta,
        artifact_root: Path,
        settings: BrainSettings | None = None,
    ) -> None:
        self._meta = meta
        self._artifact_root = Path(artifact_root)
        self._settings = settings or load_settings()
        self._session: _ExpertSession | None = None
        self._last_used_at = 0.0
        self.last_latency_ms = 0.0
        self._runtime_backend_name = "uninitialized"

    def infer(
        self,
        text: str,
        max_tokens: int = 256,
        context: ExpertRequest | None = None,
    ) -> Result[ExpertOutput, str]:
        if not text.strip():
            return err(f"Expert {self._meta['id']} cannot infer on empty text")
        started_at = time.perf_counter()
        try:
            session = self._ensure_loaded()
            content, citations, summary = session.run(text, max_tokens=max_tokens, context=context)
        except UnsupportedQueryError as exc:
            return err(f"Expert {self._meta['id']} cannot answer: {exc}")
        except Exception as exc:
            return err(f"Expert inference failed for {self._meta['id']}: {exc}")
        finally:
            self._last_used_at = time.time()
            self.last_latency_ms = (time.perf_counter() - started_at) * 1000.0

        return ok(
            {
                "expert_id": self._meta["id"],
                "content": content,
                "confidence": _confidence_for_citations(citations),
                "sources": [citation["label"] for citation in citations],
                "latency_ms": self.last_latency_ms,
                "citations": citations[: self._settings.max_citations],
                "render_strategy": "grounded",
                "summary": summary,
            }
        )

    def preload(self) -> None:
        self._ensure_loaded()
        self._last_used_at = time.time()

    def unload(self) -> None:
        self._session = None

    def is_loaded(self) -> bool:
        return self._session is not None

    def __del__(self) -> None:
        self.unload()

    def last_used_at(self) -> float:
        return self._last_used_at

    def runtime_backend_name(self) -> str:
        return self._runtime_backend_name

    def _ensure_loaded(self) -> _ExpertSession:
        if self._session is not None:
            return self._session
        self._session = self._build_session()
        self._runtime_backend_name = self._session.runtime_backend_name
        return self._session

    def _build_session(self) -> _ExpertSession:
        kind = self._meta["kind"]
        if kind == "grounded-language":
            return _GroundedLanguageExpert(self._meta)
        if kind == "repo-code":
            return _RepoCodeExpert(self._meta, self._settings)
        if kind == "geography-dataset":
            return _GeographyExpert(self._meta, self._artifact_root)
        if kind in _KNOWLEDGE_MODULES:
            return _KnowledgeModuleExpert(self._meta, self._artifact_root)
        if kind == "system-automation":
            from .system_ops import SystemOperations
            return _SystemAutomationExpert(self._meta, SystemOperations())
        raise RuntimeError(f"Unsupported expert kind: {kind}")


class _KnowledgeModuleExpert:
    runtime_backend_name = "offline-knowledge"

    def __init__(self, meta: ExpertMeta, artifact_root: Path) -> None:
        self._meta = meta
        module_path, class_name = _KNOWLEDGE_MODULES[meta["kind"]]
        module = importlib.import_module(module_path)
        expert_cls = getattr(module, class_name)
        self._expert = expert_cls()
        self._artifact_path = artifact_root / meta["artifacts"][0]["path"]

    def run(
        self,
        query: str,
        *,
        max_tokens: int,
        context: ExpertRequest | None,
    ) -> tuple[str, list[EvidenceReference], str]:
        del max_tokens
        if hasattr(self._expert, "answer_query"):
            content = str(self._expert.answer_query(query))
        else:
            content = str(self._expert.get_summary())
        if not content.strip():
            raise UnsupportedQueryError(f"{self._meta['name']} returned an empty answer")
        if context is not None and context["response_plan"]["include_next_step"]:
            content = f"{content}\nNext useful step: ask for a deeper scenario, comparison, or implementation checklist."
        citation: EvidenceReference = {
            "id": str(self._meta["id"]),
            "source_type": "workspace",
            "label": self._meta["name"],
            "snippet": _clip(content, 180),
            "uri": str(self._artifact_path),
        }
        return (content, [citation], f"{self._meta['name']} offline knowledge response")


class _SystemAutomationExpert:
    runtime_backend_name = "system-ops"

    def __init__(self, meta: ExpertMeta, ops: object) -> None:
        self._meta = meta
        self._ops = ops

    def run(
        self,
        query: str,
        *,
        max_tokens: int,
        context: ExpertRequest | None,
    ) -> tuple[str, list[EvidenceReference], str]:
        # The model-free runtime keeps this expert deterministic.
        # It reports observable system state and runs only explicitly scoped safe actions.
        from .system_ops import SystemOperations
        
        q = query.lower()
        if "firewall" in q:
            rules = SystemOperations.get_firewall_rules("Waseem")
            content = f"WaseemBrain System Ops: Retrieved Firewall Context.\n" + "\n".join(rules[:5])
        elif "sandbox" in q:
            # Safe test command
            res = SystemOperations.run_in_sandbox("cmd /c echo Sandbox Activated")
            content = f"WaseemBrain Sandbox Result: {res}"
        else:
            content = "WaseemBrain System Automation active. No direct command detected; ask for a safe system task or status check."
            
        return (content, [], "System Operations Execution")


class _GroundedLanguageExpert:
    runtime_backend_name = "grounded-evidence"

    def __init__(self, meta: ExpertMeta) -> None:
        self._meta = meta

    def run(
        self,
        query: str,
        *,
        max_tokens: int,
        context: ExpertRequest | None,
    ) -> tuple[str, list[EvidenceReference], str]:
        citations: list[EvidenceReference] = []
        plan_mode = "answer"
        if context is not None:
            citations.extend(context["internet_citations"])
            plan_mode = context["response_plan"]["mode"]
            for node in context["memory_nodes"]:
                citations.extend(
                    {
                        "id": provenance["source_id"],
                        "source_type": provenance["source_type"],
                        "label": provenance["label"],
                        "snippet": provenance["snippet"],
                        "uri": provenance["uri"],
                    }
                    for provenance in node["provenance"]
                )
        loc = context["dialogue_state"].get("locale", "en") if context and "dialogue_state" in context else "en"
        deduped = _dedupe_citations(citations)
        if not deduped:
            raise UnsupportedQueryError(LocaleEngine.t(loc, "no_evidence"))
        lead = LocaleEngine.t(loc, "grounded_answer_lead")
        if plan_mode == "plan":
            lead = LocaleEngine.t(loc, "grounded_plan_lead")
        evidence_lines = []
        for citation in deduped[:3]:
            evidence_lines.append(
                f"- {citation['label']}: {_clip(citation['snippet'], 180)}"
            )
        return (
            "\n".join(
                [
                    lead,
                    *evidence_lines,
                ]
            ),
            deduped,
            "Evidence-backed synthesis",
        )


class _RepoCodeExpert:
    runtime_backend_name = "repo-search"

    def __init__(self, meta: ExpertMeta, settings: BrainSettings) -> None:
        self._meta = meta
        self._settings = settings
        self._documents = self._load_documents()

    def run(
        self,
        query: str,
        *,
        max_tokens: int,
        context: ExpertRequest | None,
    ) -> tuple[str, list[EvidenceReference], str]:
        query_token_set = query_terms(query)
        if not query_token_set:
            raise UnsupportedQueryError("query does not contain searchable code terms")

        ranked = sorted(
            self._documents,
            key=lambda item: _score_document(
                query_token_set,
                str(item["path"]),
                str(item["text"]),
                cast(list[str], item["symbol_terms"]),
                cast(list[str], item["symbols"]),
            ),
            reverse=True,
        )
        top_matches = [
            item
            for item in ranked[:3]
            if _score_document(
                query_token_set,
                str(item["path"]),
                str(item["text"]),
                cast(list[str], item["symbol_terms"]),
                cast(list[str], item["symbols"]),
            )
            > 0
        ]
        loc = context["dialogue_state"].get("locale", "en") if context and "dialogue_state" in context else "en"
        if not top_matches:
            raise UnsupportedQueryError(LocaleEngine.t(loc, "no_workspace_matches"))

        citations = [_document_to_citation(query_token_set, item) for item in top_matches]
        content_lines = [LocaleEngine.t(loc, "code_expert_lead")]
        content_lines.append(f"{LocaleEngine.t(loc, 'query_focus')} {query.strip()[:max_tokens]}")
        for citation, item in zip(citations, top_matches, strict=True):
            symbols_for_match = cast(list[str], item["symbols"])
            matched = match_symbols(query_token_set, symbols_for_match)
            suffix = ""
            if matched:
                suffix = f" ({LocaleEngine.t(loc, 'matched_symbols')} {', '.join(matched)})"
            content_lines.append(
                f"- {citation['label']}{suffix}: {citation['snippet']}"
            )
        if context is not None and context["response_plan"]["include_next_step"]:
            content_lines.append(
                f"{LocaleEngine.t(loc, 'code_expert_next_step')} {citations[0]['label']}."
            )
        return ("\n".join(content_lines), citations, "Workspace-grounded code retrieval")

    def _load_documents(self) -> list[dict[str, object]]:
        documents: list[dict[str, object]] = []
        for path in sorted(self._settings.repo_root.rglob("*")):
            if not path.is_file():
                continue
            if any(part in _EXCLUDED_DIRS for part in path.parts if not part.startswith(".tmp_test")):
                continue
            if path.suffix.lower() not in _TEXT_EXTENSIONS:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if not text.strip():
                continue
            clipped_text = text[:64_000]
            symbols = extract_workspace_symbols(clipped_text, path.suffix)
            documents.append(
                {
                    "path": str(path),
                    "text": clipped_text,
                    "symbols": symbols,
                    "symbol_terms": sorted(
                        {term for symbol in symbols for term in query_terms(symbol)}
                    ),
                }
            )
        return documents


class _GeographyExpert:
    runtime_backend_name = "dataset-lookup"

    def __init__(self, meta: ExpertMeta, artifact_root: Path) -> None:
        self._meta = meta
        dataset_path = artifact_root / "countries.json"
        payload = json.loads(dataset_path.read_text(encoding="utf-8"))
        self._rows = [
            {
                "country": str(item["country"]),
                "capital": str(item["capital"]),
                "region": str(item.get("region", "")),
            }
            for item in payload
        ]

    def run(
        self,
        query: str,
        *,
        max_tokens: int,
        context: ExpertRequest | None,
    ) -> tuple[str, list[EvidenceReference], str]:
        del max_tokens, context
        normalized_query = query.strip().lower()
        if not normalized_query:
            raise UnsupportedQueryError("empty geography query")

        for row in self._rows:
            country = row["country"].lower()
            capital = row["capital"].lower()
            if country in normalized_query or capital in normalized_query:
                citation: EvidenceReference = {
                    "id": row["country"],
                    "source_type": "dataset",
                    "label": f"{row['country']} dataset",
                    "snippet": (
                        f"{row['country']} -> capital: {row['capital']}, "
                        f"region: {row['region']}"
                    ),
                    "uri": "dataset://countries",
                }
                return (
                    (
                        f"The capital of {row['country']} is {row['capital']}. "
                        f"Region: {row['region']}."
                    ),
                    [citation],
                    "Offline geography dataset lookup",
                )
        raise UnsupportedQueryError("country or capital not found in offline dataset")


def _confidence_for_citations(citations: list[EvidenceReference]) -> float:
    if not citations:
        return 0.0
    return min(0.98, 0.45 + (len(citations) * 0.15))


def _dedupe_citations(citations: list[EvidenceReference]) -> list[EvidenceReference]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[EvidenceReference] = []
    for citation in citations:
        key = (citation["source_type"], citation["label"], citation["snippet"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(citation)
    return deduped


# Tokenization is now handled via query_terms in code_symbols.py


def _score_document(
    query_tokens: set[str],
    path: str,
    text: str,
    symbol_terms: list[str],
    symbols: list[str],
) -> float:
    path_lower = path.lower()
    path_bonus = sum(0.5 for token in query_tokens if token in path_lower)
    text_tokens = query_terms(text[:4_000])
    overlap = len(query_tokens & text_tokens)
    symbol_overlap = len(query_tokens & set(symbol_terms)) * 1.5
    matched_syms = match_symbols(query_tokens, symbols, limit=2)
    exact_symbol_bonus = len(matched_syms) * 2.0
    return overlap + path_bonus + symbol_overlap + exact_symbol_bonus


def _document_to_citation(query_tokens: set[str], item: dict[str, object]) -> EvidenceReference:
    path = str(item["path"])
    text = str(item["text"])
    symbols_obj = item.get("symbols", [])
    symbols = cast(list[str], symbols_obj) if isinstance(symbols_obj, list) else []
    snippet = _extract_snippet(text, query_tokens, symbols, path)
    return {
        "id": str(path),
        "source_type": "workspace",
        "label": Path(str(path)).name,
        "snippet": snippet,
        "uri": str(path),
    }


def _extract_snippet(text: str, query_tokens: set[str], symbols: list[str], path: str = "") -> str:
    # Use native Algorithmic AST Intelligence for Python files
    if path.endswith(".py"):
        try:
            from .ast_coder import extract_ast_snippet
            ast_snip = extract_ast_snippet(text, query_tokens, symbols)
            if ast_snip is not None:
                return ast_snip
        except Exception:
            pass  # fallback to standard regex window if parsing fails

    lines = text.splitlines()
    matched_symbols = match_symbols(query_tokens, symbols, limit=2)
    for line_number, line in enumerate(lines):
        if any(symbol in line for symbol in matched_symbols):
            window = lines[max(0, line_number - 1) : line_number + 2]
            return " ".join(part.strip() for part in window if part.strip())
    for line_number, line in enumerate(lines):
        lowered = line.lower()
        if any(token in lowered for token in query_tokens):
            window = lines[max(0, line_number - 1) : line_number + 2]
            return " ".join(part.strip() for part in window if part.strip())
    return _clip(" ".join(line.strip() for line in lines[:3] if line.strip()), 200)


def _clip(text: str, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."



