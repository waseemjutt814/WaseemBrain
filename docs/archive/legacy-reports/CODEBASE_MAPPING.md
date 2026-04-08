# Waseem Brain Codebase Mapping

**Project:** Waseem Brain AI - CPU-first local AI stack  
**Date:** April 2026  
**Scope:** Comprehensive Python module, class, and function inventory with data flow analysis

---

## Table of Contents

1. [Core Runtime Module](#core-runtime-module)
2. [Coordinator & Orchestration](#coordinator--orchestration)
3. [Router Module](#router-module)
4. [Experts Module](#experts-module)
5. [Memory Subsystem](#memory-subsystem)
6. [Learning & Optimization](#learning--optimization)
7. [Internet & Retrieval](#internet--retrieval)
8. [Emotion Encoding](#emotion-encoding)
9. [Input Normalization](#input-normalization)
10. [Helper Utilities](#helper-utilities)
11. [Scripts & CLI](#scripts--cli)
12. [Data Flow](#data-flow)

---

## Core Runtime Module

**File:** `brain/runtime.py`

### Class: `WaseemBrainRuntime`

**Purpose:** Main entry point for the entire system. Orchestrates initialization of all subsystems and provides public query interface.

**`__init__(self, settings: BrainSettings | None = None, memory_graph: MemoryGraph | None = None, expert_pool: ExpertPool | None = None, registry: ExpertRegistry | None = None, internet_module: InternetModule | None = None, coordinator: WaseemBrainCoordinator | None = None)`**

- Initializes all core systems (memory, router, experts, internet)
- Validates expert registry and runtime configuration
- Sets up router client (artifact-based or gRPC daemon)
- Seeds bootstrap knowledge into memory
- Records initialization metrics

**Key Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `query()` | `async def query(self, raw_input: object, modality_hint: str, session_id: SessionId) -> AsyncIterator[str]` | Main query entry point; streams response tokens |
| `health()` | `def health(self) -> HealthSnapshot` | Returns system health status with component readiness |
| `recall()` | `def recall(self, query: str, limit: int = 5) -> list[MemoryNodeSummary]` | Direct memory recall without expert routing |
| `experts()` | `def experts(self) -> ExpertsStatus` | Returns loaded expert count and IDs |
| `flush_session_traces()` | `def flush_session_traces(self, session_id: SessionId) -> list[TurnTrace]` | Exports session traces and triggers learning pipeline |
| `close()` | `def close(self) -> None` | Cleanup: closes expert pool, memory graph, router daemon |
| `_build_router_daemon_client()` | `def _build_router_daemon_client(self) -> RouterDaemonClient \| None` | Optional gRPC daemon client based on settings |
| `_build_router_client()` | `def _build_router_client(self, router_daemon_client: RouterDaemonClient \| None) -> RouterClientProtocol` | Selects router backend: artifact, gRPC, or hybrid |

**Key TypedDicts:**

- `HealthSnapshot` - Status, condition, component readiness, knowledge/router/learning snapshots
- `MemoryNodeSummary` - id, content, confidence, source
- `ExpertsStatus` - loaded (list), count (int)

**Dependencies:**
- `WaseemBrainCoordinator` - Core orchestrator
- `ExpertPool` - Expert loading/execution
- `ExpertRegistry` - Expert metadata
- `MemoryGraph` - Memory storage/recall
- `InternetModule` - Optional web integration
- `BuiltinKnowledgeBootstrap` - Seeding initial knowledge
- Various router clients (artifact, daemon, hybrid)

---

## Coordinator & Orchestration

**File:** `brain/coordinator.py`

### Class: `WaseemBrainCoordinator`

**Purpose:** Main control loop for query orchestration. Manages the complete request pipeline: normalization → emotion encoding → routing → memory recall → expert execution → response assembly.

**`__init__(self, memory_graph: MemoryGraph, expert_pool: ExpertPool, router_client: RouterClientProtocol | None = None, internet_module: InternetModule | None = None, feedback_collector: FeedbackCollector | None = None, response_assembler: ResponseAssembler | None = None, dialogue_planner: DialoguePlanner | None = None, settings: BrainSettings | None = None, normalizer: Callable[[object, str | None, SessionId | None], Result[NormalizedSignal, str]] = normalize, emotion_encoder: Callable[[NormalizedSignal], EmotionContext] = encode_emotion, recall_limit: int = 10)`**

**Core Processing Method:**

`async def process(self, raw_input: object, modality_hint: str, session_id: SessionId) -> AsyncIterator[str]`

**Processing Pipeline:**
1. **Normalize** input (text/url/voice/file) → `NormalizedSignal`
2. **Encode Emotion** from signal → `EmotionContext` (valence, arousal, confidence)
3. **Route** query through learned router → `RouterDecision` (experts needed, memory check, internet flag)
4. **Recall Memory** (if `check_memory_first=true`) → filter by relevance threshold (0.15)
5. **Plan Dialogue** state and response mode (answer/clarify/plan/memory-recall)
6. **Short-circuit** if high-confidence memory (confidence ≥0.8, relevance ≥0.35)
7. **Execute Experts** via pool with context (memory nodes, citations, dialogue state)
8. **Assemble Response** from multiple expert outputs with grounding/citations
9. **Record Turn Trace** for learning pipeline
10. **Stream Response** tokens to client

**Key Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `flush_session_traces()` | `def flush_session_traces(self, session_id: SessionId) -> list[TurnTrace]` | Extract all traces for session |
| `reload_learned_policies()` | `def reload_learned_policies(self) -> None` | Refresh dialogue planner & response assembler policies |
| `_stream_text()` | `async def _stream_text(self, text: str) -> AsyncIterator[str]` | Token-streaming helper with async yields |
| `_memory_to_output()` | `def _memory_to_output(self, node: MemoryNode) -> ExpertOutput` | Convert memory node to expert output format |

**Supporting Functions:**

`def _memory_relevance(query: str, content: str) -> float`
- Combines `query_coverage_score()` and `entity_match_score()`
- Falls back to token overlap for greeting-like queries

**Protocols:**

`class RouterClientProtocol(Protocol)`
- `decide(signal: NormalizedSignal, emotion_context: EmotionContext) -> Result[RouterDecision, str]`

**Dependencies:**
- `DialoguePlanner` - State/plan inference
- `ResponseAssembler` - Multi-output grounding
- `FeedbackCollector` - Trace recording
- `MemoryGraph` - Recall operations
- `ExpertPool` - Expert inference
- `InternetModule` - Live retrieval
- Router client (artifact or daemon)

---

## Router Module

**File:** `brain/router/`

### File: `model.py`

**Class: `RouterArtifact`** (Frozen dataclass)

**Purpose:** Compact in-memory routing model using learned feature vectors and weights.

**Fields:**
- `labels: tuple[str, ...]` - Expert IDs
- `feature_count: int` - Feature vector dimension
- `expert_weights: tuple[tuple[float, ...], ...]` - One row per expert
- `expert_bias: tuple[float, ...]` - Per-expert bias
- `internet_weights: tuple[float, ...]` - Internet decision weights
- `internet_bias: float` - Internet decision bias
- `confidence_floor: float` - Minimum confidence threshold

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `load()` | `@classmethod load(cls, path: Path) -> RouterArtifact` | Load artifact from JSON |
| `decide()` | `def decide(self, text: str) -> RouterDecision` | Route query to expert + determine internet need |

**Helper Functions:**

| Function | Signature | Purpose |
|----------|-----------|---------|
| `tokenize()` | `def tokenize(text: str) -> list[str]` | Lowercase alphanumeric tokens (len ≥2) |
| `build_feature_vector()` | `def build_feature_vector(text: str, feature_count: int) -> list[float]` | FNV-1a hashing to sparse feature vector |
| `_fnv1a()` | `def _fnv1a(token: str) -> int` | FNV-1a hash (64-bit) |
| `_dot()` | `def _dot(left: tuple\|list, right: list) -> float` | Dot product |
| `_sigmoid()` | `def _sigmoid(value: float) -> float` | Sigmoid activation |
| `_softmax()` | `def _softmax(values: list) -> list` | Softmax over scores |

### File: `client.py`

**Class: `ArtifactRouterClient`**

**Purpose:** Local artifact-based router using loaded JSON model.

**`__init__(self, settings: BrainSettings | None = None, artifact_path: Path | None = None)`**

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `decide()` | `def decide(self, signal: NormalizedSignal, emotion_context: EmotionContext) -> Result[RouterDecision, str]` | Route using artifact; emotion ignored |
| `_ensure_artifact()` | `def _ensure_artifact(self) -> RouterArtifact` | Lazy-load artifact on first use |

**Class: `RouterDaemonClient`**

**Purpose:** Remote gRPC-based router with cooldown/fallback logic.

**`__init__(self, target: str, timeout_sec: float = 0.5, cooldown_sec: float = 5.0, channel_factory: Callable[[str], object] | None = None)`**
- Manages gRPC channel lifecycle
- Tracks availability with cooldown on failures

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `decide()` | `def decide(self, signal: NormalizedSignal, emotion_context: EmotionContext) -> Result[RouterDecision, str]` | gRPC call with timeout; handles daemon unavailability |
| `_check_availability()` | `def _check_availability(self) -> str \| None` | Returns error if in cooldown or already failed |
| `_mark_unavailable()` | `def _mark_unavailable(self, exc: Exception) -> None` | Records failure and starts cooldown |

**Class: `HybridRouterClient`** (from `client.py` imports)

**Purpose:** Fallback strategy—tries gRPC first, falls back to artifact.

### File: `trainer.py`

**Class: `RouterTrainer`**

**Purpose:** Offline training of router using labeled samples via scikit-learn SGDClassifier.

**`__init__(self, feature_count: int = 1024)`**

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `prepare_dataset()` | `def prepare_dataset(self, samples: list[RouterTrainingSample]) -> list[RouterTrainingSample]` | Filter samples: non-empty text, ≥1 label |
| `fit()` | `def fit(self, samples: list[RouterTrainingSample]) -> TrainedRouterModel` | Train SGDClassifier on feature matrix; returns model |

**`RouterTrainingSample` (dataclass):**
- `text: str` - Query text
- `labels: list[str]` - Expert IDs (uses first label)
- `internet_needed: bool` - Binary internet flag

**`TrainedRouterModel` (dataclass):**
- `labels: list[str]` - Expert IDs
- `feature_count: int`
- `expert_weights: list[list[float]]` - SGD coef_
- `expert_bias: list[float]` - SGD intercept_
- `internet_weights: list[float]`
- `internet_bias: float`
- `confidence_floor: float`

### File: `exporter.py`

**Class: `RouterExporter`**

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `export_model()` | `def export_model(self, output_path: Path, model: TrainedRouterModel) -> Path` | Serialize to JSON artifact |

---

## Experts Module

**File:** `brain/experts/`

### File: `registry.py`

**Class: `ExpertRegistry`**

**Purpose:** Loads and validates expert metadata from manifest JSON.

**`__init__(self, settings: BrainSettings | None = None, registry_path: Path | None = None)`**

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `get()` | `def get(self, expert_id: ExpertId) -> Result[ExpertMeta, str]` | Lookup expert by ID |
| `find_by_domain()` | `def find_by_domain(self, domain: str) -> list[ExpertMeta]` | Find experts serving domain (case-insensitive) |
| `all()` | `def all(self) -> list[ExpertMeta]` | List all registered experts |
| `validate()` | `def validate(self) -> Result[None, str]` | Check all artifact files exist; returns error list |

**`ExpertMeta` (TypedDict):**
- `id: ExpertId`
- `name: str`
- `domains: list[str]`
- `kind: Literal["grounded-language", "repo-code", "geography-dataset"]`
- `artifact_root: str` - Relative path under `expert_dir`
- `artifacts: list[ExpertArtifact]` - List of artifact definitions
- `capabilities: list[str]`
- `load_strategy: Literal["lazy", "pinned"]`
- `description: str`

**`ExpertArtifact` (TypedDict):**
- `name: str`
- `path: str` - Relative to `artifact_root`
- `kind: str` - e.g., "pickle", "json"

### File: `expert.py`

**Class: `Expert`**

**Purpose:** Typed executor for a single expert. Loads/unloads artifacts, executes inference with context.

**`__init__(self, meta: ExpertMeta, artifact_root: Path, settings: BrainSettings | None = None)`**

**Attributes:**
- `_meta: ExpertMeta` - Metadata
- `_artifact_root: Path` - Root directory
- `_session: _ExpertSession | None` - Lazy-loaded backend
- `_last_used_at: float` - For LRU eviction
- `last_latency_ms: float` - Execution latency

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `infer()` | `def infer(self, text: str, max_tokens: int = 256, context: ExpertRequest \| None = None) -> Result[ExpertOutput, str]` | Execute expert inference with memory/internet context |
| `preload()` | `def preload(self) -> None` | Eagerly load session backend |
| `unload()` | `def unload(self) -> None` | Release backend resources |
| `last_used_at()` | `def last_used_at(self) -> float` | Timestamp for LRU eviction |

**`ExpertOutput` (TypedDict):**
- `expert_id: ExpertId`
- `content: str` - Response text
- `confidence: float`
- `sources: list[str]`
- `latency_ms: float`
- `citations: list[EvidenceReference]`
- `render_strategy: RenderStrategy`
- `summary: str`

### File: `pool.py`

**Class: `ExpertPool`**

**Purpose:** Manages loading, caching, and execution of experts with LRU eviction.

**`__init__(self, settings: BrainSettings | None = None, registry: ExpertRegistry | None = None, executor: ThreadPoolExecutor | None = None, mapper: ExpertMapperProtocol | None = None)`**
- Max loaded experts: `settings.expert_max_loaded`
- Idle timeout: `settings.expert_idle_timeout_sec`

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `load()` | `def load(self, expert_id: ExpertId) -> Result[Expert, str]` | Load expert; evict LRU if at capacity |
| `infer()` | `async def infer(self, expert_ids: list[ExpertId], request: ExpertRequest) -> Result[list[ExpertOutput], str]` | Execute multiple experts in parallel |
| `loaded_ids()` | `def loaded_ids(self) -> list[ExpertId]` | List currently loaded expert IDs |
| `loaded_count()` | `def loaded_count(self) -> int` | Count loaded experts |
| `close()` | `def close(self) -> None` | Cleanup thread pool |
| `_evict_expert()` | `def _evict_expert(self, expert_id: ExpertId) -> None` | Notify mapper + unload |
| `_run_idle_evictor()` | `async def _run_idle_evictor(self) -> None` | Background task: evict idle experts periodically |

**Protocol: `ExpertMapperProtocol`**
- `map_expert(expert_id: ExpertId, file_path: Path) -> Result[bool, str]`
- `evict_expert(expert_id: ExpertId) -> Result[bool, str]`

**`ExpertRequest` (TypedDict):**
- `query: str`
- `session_id: SessionId`
- `memory_nodes: list[MemoryNode]`
- `internet_citations: list[EvidenceReference]`
- `dialogue_state: DialogueState`
- `response_plan: ResponsePlan`

### File: `assembler.py`

**Class: `ResponseAssembler`**

**Purpose:** Combines multiple expert outputs into a single grounded, ranked response using learned policies.

**`__init__(self, settings: BrainSettings | None = None, policy: ResponsePolicyArtifact | None = None)`**

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `assemble()` | `def assemble(self, outputs: list[ExpertOutput], *, query: str = "", dialogue_state: DialogueState \| None = None, response_plan: ResponsePlan \| None = None) -> Result[ExpertOutput, str]` | Select best output or synthesize from multiple |
| `reload_policy()` | `def reload_policy(self) -> None` | Reload response policy artifact |

**Assembly Strategy:**
- Single output: realize with learned styling
- Multiple outputs: rank by custom scoring (citations, next steps, confidence, entity match, length, query coverage)
- Select best candidate (direct, grounded, or stepwise)
- Deduplicate citations

**Helper Methods:**
- `_direct_candidate()` - First expert's content
- `_grounded_candidate()` - Synthesized with citations
- `_stepwise_candidate()` - Step-by-step guide format
- `_token_overlap()` - Measure redundancy
- `_dedupe_citations()` - Remove duplicate citations
- `_realize_single()` - Apply dialogue style to single output

---

## Memory Subsystem

**File:** `brain/memory/`

### File: `graph.py`

**Class: `MemoryGraph`**

**Purpose:** Unified interface for memory storage and retrieval. Combines SQLite metadata + vector search.

**`__init__(self, settings: BrainSettings | None = None, vector_store: ChromaVectorStore | None = None, sqlite_store: SqliteMetaStore | None = None, embedder: MemoryEmbedder | None = None)`**

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `store()` | `def store(self, content: str, source: str, tags: list[str], session_id: SessionId, *, source_type: str = "memory", citations: list[EvidenceReference] \| None = None) -> Result[MemoryNodeId, str]` | Store content with provenance; dedup check; returns node ID |
| `recall()` | `def recall(self, query: str, limit: int = 10, session_id: SessionId \| None = None) -> Result[list[MemoryNode], str]` | Retrieve top-K nodes by vector + FTS relevance |
| `recall_session()` | `def recall_session(self, session_id: SessionId, limit: int = 10) -> Result[list[MemoryNode], str]` | Retrieve nodes from specific session only |
| `ensure_session()` | `def ensure_session(self, session_id: SessionId) -> Result[None, str]` | Create session record if missing |
| `close()` | `def close(self) -> None` | Cleanup backends |
| `node_count()` | `def node_count(self) -> int` | Total nodes in vector store |
| `vector_backend_name()` | `def vector_backend_name(self) -> str` | Current backend name (hnswlib or text-fts-only) |
| `get_config()` | `def get_config(self, key: str, default: str = "") -> str` | Retrieve config key from SQLite |
| `set_config()` | `def set_config(self, key: str, value: str) -> Result[None, str]` | Store config key in SQLite |

**`MemoryNode` (TypedDict):**
- `id: MemoryNodeId`
- `content: str`
- `embedding: EmbeddingVector`
- `tags: list[str]`
- `source: str`
- `created_at: float`
- `last_accessed: float`
- `access_count: int`
- `confidence: float`
- `session_id: SessionId`
- `source_type: EvidenceSourceType`
- `provenance: list[ProvenanceRecord]`

**`ProvenanceRecord` (TypedDict):**
- `source_type: EvidenceSourceType` - "memory", "internet", "dataset", "workspace", "session", "user"
- `source_id: str`
- `label: str`
- `uri: str`
- `snippet: str`

### File: `sqlite_store.py`

**Class: `SqliteMetaStore`**

**Purpose:** SQLite-backed metadata store and FTS search for memory.

**`__init__(self, sqlite_dir: Path)`**

**Database Schema:**
- `node_meta` - Memory node metadata (FTS-indexed content)
- `sessions` - Session tracking (id, started_at, ended_at, query_count)
- `config` - Key-value store

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `create_session()` | `def create_session(self, session_id: SessionId) -> Result[None, str]` | INSERT OR IGNORE |
| `mark_session_ended()` | `def mark_session_ended(self, session_id: SessionId, ended_at: float \| None = None) -> Result[None, str]` | Update session end time |
| `increment_query_count()` | `def increment_query_count(self, session_id: SessionId) -> Result[None, str]` | Increment query counter |
| `upsert_node()` | `def upsert_node(self, node: MemoryNode, *, vector_label: int) -> Result[None, str]` | INSERT OR UPDATE with vector label |
| `search_text()` | `def search_text(self, query: str, limit: int) -> list[MemoryNodeId]` | FTS MATCH query; returns node IDs |
| `get_node()` | `def get_node(self, node_id: MemoryNodeId) -> MemoryNode \| None` | Fetch single node by ID |
| `get_nodes()` | `def get_nodes(self, node_ids: list[MemoryNodeId]) -> list[MemoryNode]` | Fetch multiple nodes |
| `list_nodes()` | `def list_nodes(self) -> list[MemoryNode]` | All nodes |
| `log_node_access()` | `def log_node_access(self, node_id: MemoryNodeId) -> Result[None, str]` | Update last_accessed & access_count |
| `get_config()` | `def get_config(self, key: str, default: str = "") -> str` | Get config value |
| `set_config()` | `def set_config(self, key: str, value: str) -> Result[None, str]` | Set config value |
| `get_ended_sessions()` | `def get_ended_sessions(self, within_seconds: int) -> list[SessionId]` | Sessions ended in time window |
| `log_correction_job()` | `def log_correction_job(self, session_id: SessionId, expert_id: str, score: float) -> None` | Log correction job for learning |

### File: `vector_store.py`

**Class: `ChromaVectorStore`**

**Purpose:** Vector search using HNSW (hnswlib) or fallback to text-only FTS.

**`__init__(self, storage_dir: Path, embedder: MemoryEmbedder | None = None, backend_preference: str = "auto", sqlite_store: SqliteMetaStore | None = None, dimensions: int = 384)`**

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `add()` | `def add(self, node: MemoryNode) -> Result[None, str]` | Index node in vector space |
| `search()` | `def search(self, query_text: str, limit: int) -> Result[list[MemoryNode], str]` | Vector + FTS search; returns top-K |
| `get()` | `def get(self, node_id: MemoryNodeId) -> Result[MemoryNode, str]` | Fetch by ID |
| `delete()` | `def delete(self, node_id: MemoryNodeId) -> Result[None, str]` | Not implemented |
| `update_access()` | `def update_access(self, node_id: MemoryNodeId) -> Result[None, str]` | Log access |
| `all_nodes()` | `def all_nodes(self) -> list[MemoryNode]` | All indexed nodes |
| `persist_node()` | `def persist_node(self, node: MemoryNode) -> None` | Write to SQLite |
| `count()` | `def count(self) -> int` | Total node count |
| `backend_name()` | `def backend_name(self) -> str` | "hnswlib" or "text-fts-only" |
| `close()` | `def close(self) -> None` | Cleanup |

**Fallback: `_TextOnlyVectorStore`**
- Uses SQLite FTS when hnswlib unavailable
- Same interface, FTS-only search

**Index Parameters:**
- `_MIN_INDEX_CAPACITY = 1024`
- `_DEFAULT_SEARCH_EF = 100`
- `_INDEX_CONSTRUCTION_EF = 200`
- `_INDEX_M = 16`

### File: `embedder.py`

**Class: `MemoryEmbedder`**

**Purpose:** Vectorization of text using all-MiniLM-L6-v2 (384-dim).

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `embed()` | `def embed(self, text: str) -> EmbeddingVector` | Text → 384-dim vector |
| `backend_name()` | `def backend_name(self) -> str` | Current backend ("sentence-transformers", etc.) |

---

## Learning & Optimization

**File:** `brain/learning/`

### File: `policy.py`

**Class: `ResponsePolicyArtifact`** (Frozen dataclass)

**Purpose:** Learned offline policy for response ranking and mode selection.

**Fields:**
- `version: int` - Artifact version
- `clarification_confidence_floor: float` - Threshold for triggering clarification
- `intent_mode_bias: dict[str, dict[str, float]]` - Per-intent/mode scores
- `intent_strategy_bias: dict[str, dict[str, dict[str, float]]]` - Per-intent/mode/style scores
- `candidate_ranker_profiles: dict[str, CandidateRankerProfile]` - Ranker configurations
- `next_step_intents: tuple[str, ...]` - Intents that include next steps
- `supportive_intents: tuple[str, ...]` - Intents using supportive style
- `trained_trace_count: int` - Number of traces used in training

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `load()` | `@classmethod load(cls, path: Path) -> ResponsePolicyArtifact` | Load from JSON |

**Class: `CandidateRankerProfile`** (Frozen dataclass)

**Purpose:** Weights for scoring response candidates.

**Fields:**
- `citation_weight: float` - Citations in response
- `next_step_weight: float` - Includes next step
- `confidence_weight: float` - Expert confidence
- `entity_match_weight: float` - Entity match to query
- `length_weight: float` - Response length fitness
- `query_coverage_weight: float` - Query terms coverage
- `symbol_anchor_weight: float` - Code symbol match
- `target_length_tokens: int` - Ideal response length
- `length_tolerance_tokens: int` - Expected variance

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `adjustment()` | `def adjustment(self, *, citations_count: int, has_next_step: bool, confidence: float, entity_match_score: float, query_coverage: float, symbol_anchor_score: float, response_length_tokens: int) -> float` | Compute ranking adjustment score |

**Function: `load_response_policy(path: Path) -> ResponsePolicyArtifact`**

**Class: `ResponsePolicyTrainer`**

**Purpose:** Offline training of response policy from session traces.

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `fit()` | `def fit(self, traces: list[TurnTrace]) -> ResponsePolicyArtifact` | Train from turn traces; return artifact |

**Class: `ResponsePolicyExporter`**

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `export_model()` | `def export_model(self, output_path: Path, artifact: ResponsePolicyArtifact) -> Path` | Serialize artifact to JSON |

### File: `feedback.py`

**Class: `FeedbackCollector`**

**Purpose:** Collects explicit/implicit feedback and turn traces for learning pipeline.

**`__init__(self)`**

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `record_explicit()` | `def record_explicit(self, session_id: SessionId, expert_id: ExpertId, is_positive: bool) -> None` | Record user positive/negative feedback |
| `record_implicit()` | `def record_implicit(self, session_id: SessionId, expert_id: ExpertId, signal_type: str, evidence: str, *, query: str = "", response: str = "") -> None` | Record inferred feedback (accepted_and_continued, clarification_needed, etc.) |
| `record_turn()` | `def record_turn(self, session_id: SessionId, expert_id: ExpertId, *, query: str, response: str, dialogue_intent: str, response_mode: str, render_strategy: RenderStrategy, citations_count: int, confidence: float, decision_trace: str, outcome: Literal["answered", "memory_answered", "clarification_requested", "unsupported"]) -> None` | Record full turn with quality metrics |
| `flush()` | `def flush(self, session_id: SessionId) -> list[FeedbackSignal]` | Extract and clear signals for session |
| `flush_traces()` | `def flush_traces(self, session_id: SessionId) -> list[TurnTrace]` | Extract and clear traces for session |

**`FeedbackSignal` (TypedDict):**
- `session_id: SessionId`
- `expert_id: ExpertId`
- `query: str`
- `response: str`
- `signal_type: Literal["positive", "negative", "neutral"]`
- `strength: float`
- `timestamp: float`
- `evidence: str`

**`TurnTrace` (TypedDict):**
- `session_id: SessionId`
- `expert_id: ExpertId`
- `query: str`
- `response: str`
- `dialogue_intent: str`
- `response_mode: str`
- `render_strategy: RenderStrategy`
- `citations_count: int`
- `has_next_step: bool`
- `query_coverage: float`
- `entity_match_score: float`
- `symbol_anchor_score: float`
- `response_length_tokens: int`
- `confidence: float`
- `decision_trace: str`
- `outcome: Literal["answered", "memory_answered", "clarification_requested", "unsupported"]`
- `timestamp: float`

### File: `corrector.py`

**Class: `ExpertCorrector`**

**Purpose:** Records correction jobs and turn traces for offline training.

**`__init__(self, settings: BrainSettings | None = None)`**

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `correct()` | `def correct(self, expert_id: ExpertId, negative_examples: list[tuple[str, str]], *, positive_examples: list[tuple[str, str]] \| None = None, turn_traces: list[TurnTrace] \| None = None) -> Result[None, str]` | Write correction job manifest; create datasets |
| `record_session_traces()` | `def record_session_traces(self, session_id: str, turn_traces: list[TurnTrace]) -> Result[None, str]` | Export traces to JSONL file |
| `_write_expert_traces()` | `def _write_expert_traces(self, expert_id: ExpertId, turn_traces: list[TurnTrace]) -> Path \| None` | Write expert-specific traces |

**Artifacts Created:**
- `experts/lora/datasets/{expert_id}.jsonl` - Training examples
- `experts/lora/traces/{session_id}.jsonl` - Turn traces
- `experts/lora/{expert_id}.training-job.json` - Correction manifest

### File: `features.py`

**Purpose:** Quality metrics for response ranking.

**Functions:**

| Function | Signature | Purpose |
|----------|-----------|---------|
| `query_coverage_score()` | `def query_coverage_score(query: str, response: str) -> float` | Fraction of query terms in response |
| `entity_match_score()` | `def entity_match_score(query: str, response: str) -> float` | Fraction of anchor terms (non-stopwords) in response |
| `symbol_anchor_score()` | `def symbol_anchor_score(query: str, response: str) -> float` | Best match of extracted code symbols |

### File: `loop.py`

**Class: `SelfLearningLoop`**

**Purpose:** Async background task that processes session feedback and triggers corrections.

**`__init__(self, sqlite_store: SqliteMetaStore, feedback_collector: FeedbackCollector, memory_graph: MemoryGraph, scorer: ResponseScorer | None = None, corrector: ExpertCorrector | None = None, executor: ThreadPoolExecutor | None = None)`**

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `start()` | `def start(self) -> None` | Create background task |
| `stop()` | `async def stop(self) -> None` | Cancel task |

**Background Behavior:**
- Every 60 seconds, check for ended sessions (past 5 minutes)
- Score expert performance from feedback signals
- Generate correction jobs if score indicates need
- Record traces to LoRA dataset

### File: `scorer.py`

**Class: `ResponseScorer`**

**Purpose:** Evaluates expert response quality from feedback signals.

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `score()` | `def score(self, signals: list[FeedbackSignal], traces: list[TurnTrace]) -> float` | Aggregate quality score |
| `needs_correction()` | `def needs_correction(self, score: float) -> bool` | Threshold check for triggering correction |

---

## Internet & Retrieval

**File:** `brain/internet/`

### File: `module.py`

**Class: `InternetModule`**

**Purpose:** Optional web search and content fetching.

**`__init__(self, enabled: bool | None = None, settings: BrainSettings | None = None, search: DuckDuckGoSearch | None = None, fetcher: ContentFetcher | None = None)`**

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `query()` | `async def query(self, search_query: str, context: str) -> Result[InternetResult, str]` | Search + fetch top 3 results → combined content |
| `is_needed()` | `def is_needed(self, memory_result: list[MemoryNode], confidence_threshold: float) -> bool` | Returns true if memory confidence below threshold |
| `_refine_query()` | `def _refine_query(self, search_query: str, context: str) -> str` | Augment query with context tokens (first 6) |

**`InternetResult` (TypedDict):**
- `query: str` - Refined search query
- `results: list[dict]` - Content chunks
- `combined_content: str` - All results joined
- `sources: list[str]` - URLs
- `retrieved_at: float` - Timestamp
- `citations: list[EvidenceReference]` - Citation objects

### File: `search.py`

**Class: `DuckDuckGoSearch`**

**Purpose:** DuckDuckGo search API wrapper.

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `search()` | `async def search(self, query: str, result_count: int) -> Result[list[SearchResult], str]` | Query DuckDuckGo; return results |

### File: `fetcher.py`

**Class: `ContentFetcher`**

**Purpose:** Fetch and parse web page content.

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `fetch()` | `async def fetch(self, url: str) -> Result[FetchedContent, str]` | GET request + text extraction |

---

## Emotion Encoding

**File:** `brain/emotion/`

### File: `text_encoder.py`

**Class: `TextEmotionEncoder`**

**Purpose:** Estimate valence, arousal, and primary emotion from text.

**`__init__(self, vader_backend: Callable[[str], float] | None = None, classifier_backend: Callable[[str], dict[str, float]] | None = None, backend_preference: str | None = None)`**
- VADER for valence (compound score)
- Transformer classifier for emotion (zero-shot or finetuned)

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `encode()` | `def encode(self, signal: NormalizedSignal) -> EmotionContext` | Text → emotion context |
| `_default_valence()` | `def _default_valence(self, text: str) -> float` | VADER or heuristic polarity |
| `_default_probabilities()` | `def _default_probabilities(self, text: str) -> dict[str, float]` | Classifier or heuristic emotion probabilities |
| `_heuristic_probabilities()` | `def _heuristic_probabilities(self, text: str) -> dict[str, float]` | Keyword-based fallback |
| `_normalize_scores()` | `def _normalize_scores(self, raw_scores: dict[str, float]) -> dict[str, float]` | L2 normalization |
| `_emotion_to_valence()` | `def _emotion_to_valence(self, emotion: str) -> float` | Proxy valence from emotion label |

**Emotions Recognized:**
- joy, sadness, anger, fear, surprise, disgust, confused, calm, happy, excited, urgent, neutral

### File: `voice_encoder.py`

**Class: `VoiceEmotionEncoder`**

**Purpose:** Estimate emotion from audio features (pitch, energy, spectral, etc.).

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `encode()` | `def encode(self, signal: NormalizedSignal) -> EmotionContext` | Audio → emotion context |

### File: `fusion.py`

**Class: `EmotionFuser`**

**Purpose:** Combine text and voice emotion contexts.

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `fuse()` | `def fuse(self, text_context: EmotionContext \| None, voice_context: EmotionContext \| None) -> EmotionContext` | Weighted average; dominant emotion |

---

## Input Normalization

**File:** `brain/normalizer/`

### File: `base.py`

**Abstract Class: `InputAdapter`**

**Purpose:** Base protocol for input adapters.

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `normalize()` | `@abstractmethod def normalize(self, raw_input: Any) -> Result[NormalizedSignal, str]` | Convert input to standardized form |

### File: `__init__.py`

**Function: `normalize(raw_input: object, modality_hint: str | None = None, session_id: SessionId | None = None) -> Result[NormalizedSignal, str]`**

**Purpose:** Main entry point for input normalization.

**Logic:**
1. Determine adapter based on hint (text/url/voice) or content sniffing
2. Normalize input
3. Attach session ID

**Adapters:**
- `TextAdapter` - Plain text strings
- `UrlAdapter` - HTTP/HTTPS URLs
- `VoiceAdapter` - Audio bytes (WAV, MP3, etc.)
- `DocumentAdapter` - PDF, DOCX, plaintext files

### File: `text_adapter.py`

**Class: `TextAdapter`** extends `InputAdapter`

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `normalize()` | `def normalize(self, raw_input: object) -> Result[NormalizedSignal, str]` | Validate string, normalize whitespace |

### File: `url_adapter.py`

**Class: `UrlAdapter`** extends `InputAdapter`

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `normalize()` | `def normalize(self, raw_input: object) -> Result[NormalizedSignal, str]` | Fetch URL, extract title+body |

### File: `voice_adapter.py`

**Class: `VoiceAdapter`** extends `InputAdapter`

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `normalize()` | `def normalize(self, raw_input: object) -> Result[NormalizedSignal, str]` | Decode audio, transcribe via Whisper |

**Dependencies:**
- `openai-whisper` for speech-to-text
- `librosa` for audio processing

### File: `document_adapter.py`

**Class: `DocumentAdapter`** extends `InputAdapter`

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `normalize()` | `def normalize(self, raw_input: object) -> Result[NormalizedSignal, str]` | Extract text from PDF/DOCX/plaintext |
| `_extract_pdf_text()` | `def _extract_pdf_text(self, raw_bytes: bytes) -> str` | pypdf → PdfReader.extract_text() |
| `_extract_docx_text()` | `def _extract_docx_text(self, raw_bytes: bytes) -> str` | python-docx → Document.paragraphs |
| `_extract_docx_xml()` | `def _extract_docx_xml(self, raw_bytes: bytes) -> str` | Fallback: regex strip XML tags |
| `_extract_plaintext()` | `def _extract_plaintext(self, raw_bytes: bytes) -> str` | UTF-8 decode with error handling |
| `_extract_printable_strings()` | `def _extract_printable_strings(self, raw_bytes: bytes) -> str` | Regex extract printable sequences |

**Max text length:** 4000 chars (truncated with `[truncated]` marker)

---

## Helper Utilities

**File:** `brain/helpers/`

### File: `common.py`

**Functions:**

| Function | Signature | Purpose |
|----------|-----------|---------|
| `safe_json_loads()` | `def safe_json_loads(text: str, default: Optional[Any] = None) -> Any` | JSON parse with fallback |
| `safe_json_dumps()` | `def safe_json_dumps(obj: Any, default: str = "{}") -> str` | JSON serialize with fallback |
| `deep_get()` | `def deep_get(obj: dict[str, Any], path: str, default: Any = None) -> Any` | Dot-notation nested get (e.g., "users.0.name") |

### File: `logger.py`

**Functions:**

| Function | Signature | Purpose |
|----------|-----------|---------|
| `get_logger()` | `def get_logger(name: str) -> logging.Logger` | Cached logger by name |
| `configure_logging()` | `def configure_logging(level: int = logging.INFO, format_str: Optional[str] = None, file_path: Optional[str] = None) -> None` | Root logger setup |

### File: `validation.py`

**Functions:**

| Function | Signature | Purpose |
|----------|-----------|---------|
| `validate_text()` | `def validate_text(text: str, min_length: int = 1, max_length: int = 10000) -> str` | Normalize + bounds check |
| `validate_modality()` | `def validate_modality(modality: str) -> Modality` | Enum validation |
| `validate_response_style()` | `def validate_response_style(style: str) -> ResponseStyle` | Enum validation |

**Exception: `ValidationError`** - Custom validation exception with field name

### File: `errors.py`

**Custom Exceptions:**

| Exception | Purpose |
|-----------|---------|
| `ValidationError` | Field validation failures |
| `ConfigurationError` | Settings/routing issues |
| `RuntimeError` | Execution failures |

### File: `formatting.py`

**Functions for response formatting:**

| Function | Signature | Purpose |
|----------|-----------|---------|
| `format_markdown()` | `def format_markdown(text: str) -> str` | Markdown formatting |
| `format_code_block()` | `def format_code_block(code: str, language: str = "") -> str` | Code formatting with syntax hints |

### File: `timing.py`

**Functions:**

| Function | Signature | Purpose |
|----------|-----------|---------|
| `timed()` | `@decorator def timed(func) -> Callable` | Execution time logging |
| `measure()` | `def measure(name: str, func: Callable) -> float` | Time a function; return duration (sec) |

### File: `decorators.py`

**Decorators:**

| Decorator | Purpose |
|-----------|---------|
| `@memoize()` | Cache function results by args |
| `@retry(max_attempts=3, backoff=1.5)` | Exponential backoff retry |
| `@async_timeout(seconds=10)` | Async function timeout |

### File: `testing.py`

**Test Utilities:**

| Function | Purpose |
|----------|---------|
| `MockMemoryGraph` | In-memory mock for unit tests |
| `MockExpertPool` | Stubbed pool for testing |
| `MockRouter` | Deterministic router for tests |

---

## Scripts & CLI

**File:** `scripts/`

### File: `chat_cli.py`

**Purpose:** Interactive and one-shot CLI interface.

**Main Functions:**

| Function | Signature | Purpose |
|----------|-----------|---------|
| `main()` | `def main() -> None` | CLI entry point |

**Modes:**
- `--once "query"` - One-shot query
- Interactive chat with `/commands`:
  - `/health` - System health
  - `/experts` - Loaded experts list
  - `/recall "query"` - Direct memory recall
  - `/status` - Session metrics
  - `/learning` - Learning status
  - `/project` - Project info

**Features:**
- Modality selection (text/voice/file/url)
- Real-time response streaming
- Per-turn metrics
- ANSI colorized output
- Voice input warmup detection

### File: `prepare_runtime.py`

**Purpose:** System preparation and warmup.

**Main Functions:**

| Function | Signature | Purpose |
|----------|-----------|---------|
| `main()` | `def main() -> None` | Preparation entry point |

**Tasks:**
1. Load settings and initialize runtime
2. Warmup embedder
3. Warmup emotion encoders (text + voice)
4. Initialize voice transcription (Whisper)
5. Eagerly pin critical experts
6. Verify internet connectivity
7. Print readiness report

### File: `coordinator_bridge.py`

**Purpose:** JSON-line IPC bridge for runtime daemon mode.

**Main Async Function:**

`async def main() -> None`

**Protocol:**
- Read JSON-line requests from stdin
- Execute via runtime
- Write JSON-line responses to stdout

**Commands:**
- `shutdown` - Graceful shutdown
- `health` - System health
- `recall` - Memory recall
- `query` - Process query
- `flush-traces` - Export session traces

### File: `runtime_client.py`

**Purpose:** Client for local or daemon runtime.

**Protocols:**

**`RuntimeHandleProtocol`**
- `async def query(text: str, modality_hint: str, session_id: SessionId) -> AsyncIterator[str]`
- `def health() -> HealthSnapshot`
- `def close()`

**Classes:**

**`LocalRuntimeHandle`** - In-process runtime

**`RuntimeDaemonClient`** - JSON-line IPC via subprocess

**Functions:**

| Function | Signature | Purpose |
|----------|-----------|---------|
| `is_runtime_daemon_running()` | `def is_runtime_daemon_running() -> bool` | Check daemon status |
| `load_runtime_daemon_state()` | `def load_runtime_daemon_state() -> dict[str, Any]` | Load daemon state |

### File: `train_router.py`

**Purpose:** Train and export router artifact.

**Arguments:**
- `input_path` - JSONL training data (default: `experts/router-samples.jsonl`)
- `--output-path` - Output artifact (default: `experts/router.json`)
- `--feature-count` - Feature vector dimension (default: 1024)

**Workflow:**
1. Load RouterTrainingSample objects from JSONL
2. Train RouterTrainer
3. Export via RouterExporter

### File: `train_response_policy.py`

**Purpose:** Train and export response policy artifact.

**Arguments:**
- `input_path` - Traces directory (default: `experts/lora/traces/`)
- `--output-path` - Output artifact (default: `experts/response-policy.json`)

**Workflow:**
1. Load TurnTrace objects from JSONL files
2. Train ResponsePolicyTrainer
3. Export via ResponsePolicyExporter

### File: `init_db.py`

**Purpose:** Initialize SQLite metadata store.

**Task:** Create SQLite database with schema migrations.

### File: `inspect_memory.py`

**Purpose:** Query and inspect memory graph.

**Arguments:**
- `query` - Search text (optional)
- `--session-id` - Session filter (default: "cli-session")

**Behavior:**
- If query provided: `graph.recall(query, limit=5)`
- Else: `graph.recall_session(session_id)`

### File: `label_data.py`

**Purpose:** Generate training labels for router/policy from session traces.

**Workflow:**
1. Load turn traces
2. Extract features (entity match, coverage, symbols)
3. Output labeled JSONL for training

### File: `create_expert.py`

**Purpose:** Scaffold a new expert with manifest and artifacts.

### File: `export_expert.py`

**Purpose:** Export trained expert LoRA artifacts.

### File: `diagnose_backends.py`

**Purpose:** Check availability of optional backends (embedder, models, etc.).

### File: `download_models.py`

**Purpose:** Pre-download transformer models for offline use.

### File: `validate_codex_skills.py`

**Purpose:** Validate expert skill manifests against schema.

### File: `sync_codex_skills.py`

**Purpose:** Sync expert definitions with knowledge store.

### File: `manage_router_daemon.py`

**Purpose:** Start/stop router gRPC daemon.

### File: `manage_runtime_daemon.py`

**Purpose:** Start/stop coordinator_bridge daemon.

### File: `benchmark.py`

**Purpose:** Performance benchmarking suite.

### File: `guard_no_placeholders.py`

**Purpose:** Ensure no placeholder experts or dummy code (CI/CD requirement).

---

## Configuration Module

**File:** `brain/config.py`

**Class: `BrainSettings`** (Frozen dataclass)

**Purpose:** Centralized configuration loaded from environment variables.

**Key Settings:**

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `repo_root` | Path | cwd | Project root |
| `expert_dir` | Path | `./experts/base` | Expert artifact directory |
| `expert_registry_path` | Path | `./experts/registry.json` | Registry manifest |
| `lora_dir` | Path | `./experts/lora` | LoRA training artifacts |
| `chroma_dir` | Path | `./data/chroma` | Vector store directory |
| `sqlite_dir` | Path | `./data/sqlite` | SQLite metadata directory |
| `embedding_backend` | str | "auto" | Embedding model backend |
| `embedding_model_name` | str | "all-MiniLM-L6-v2" | Sentence transformer model |
| `embedding_dimensions` | int | 384 | Vector dimension |
| `memory_vector_backend` | str | "auto" | Vector search (hnswlib or text-fts) |
| `learning_backend` | str | "auto" | Learning/correction backend |
| `internet_enabled` | bool | true | Web search enabled |
| `internet_max_requests_per_query` | int | 5 | Max search results to fetch |
| `whisper_model` | str | "base" | Speech recognition model |
| `expert_max_loaded` | int | 4 | Max experts in memory |
| `expert_idle_timeout_sec` | int | 300 | Eviction timeout |
| `memory_recall_limit` | int | 10 | Default recall size |
| `memory_decay_days` | int | 30 | Memory expiration window |
| `learning_enabled` | bool | true | Learning pipeline enabled |
| `router_backend` | str | "auto" | Router mode (local/grpc/auto) |
| `router_model_path` | Path | `./experts/router.json` | Router artifact |
| `grpc_host` | str | "127.0.0.1" | Router daemon host |
| `grpc_port` | int | 50051 | Router daemon port |
| `api_port` | int | 3000 | HTTP API port |
| `log_level` | str | "INFO" | Log level |

**Function: `load_settings(env: Mapping[str, str] | None = None) -> BrainSettings`**

---

## Dialogue & Session Management

**File:** `brain/dialogue.py`

**Class: `DialoguePlanner`**

**Purpose:** Infer dialogue state (intent, style, clarity) and response plan (mode, style, format).

**`__init__(self, settings: BrainSettings | None = None, policy: ResponsePolicyArtifact | None = None)`**

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `build_state()` | `def build_state(self, signal: NormalizedSignal, emotion: EmotionContext, memory_nodes: list[MemoryNode]) -> DialogueState` | Infer intent, style, confidence from signal |
| `build_plan()` | `def build_plan(self, signal: NormalizedSignal, dialogue_state: DialogueState, router_confidence: float, has_evidence: bool, has_memory_answer: bool) -> ResponsePlan` | Determine response mode/style using policy |
| `clarification_prompt()` | `def clarification_prompt(self, signal: NormalizedSignal, dialogue_state: DialogueState) -> str` | Generate clarification request message |
| `reload_policy()` | `def reload_policy(self) -> None` | Reload response policy artifact |

**Intents Recognized:**
- `greeting` - Hi/hello
- `code` - Programming/repo code  
- `factual` - What/where/who/when questions
- `planning` - How/steps/roadmap
- `follow_up` - It/that/same/continue/more
- `general` - Catch-all

### File: `brain/session.py`

**Class: `SessionManager`**

**Purpose:** Session lifecycle management (start, end).

**`__init__(self, sqlite_store: SqliteMetaStore)`**

**Methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `start()` | `def start(self, session_id: SessionId) -> Result[None, str]` | Record session start |
| `end()` | `def end(self, session_id: SessionId) -> Result[None, str]` | Mark session ended |

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            CLIENT INTERFACE                             │
│  (HTTP/WebSocket via Fastify or CLI or JSON-line daemon)               │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             │ raw_input, modality_hint, session_id
                             ▼
        ┌──────────────────────────────────────────────────────────┐
        │         WASEEMBRAIN RUNTIME (runtime.py)               │
        │                                                          │
        │  • Initializes all subsystems (memory, router, experts) │
        │  • Provides health() / recall() / query() interfaces    │
        │  • Coordinates flow through Coordinator                 │
        └──────────┬───────────────────────────────────────────────┘
                   │
                   │ raw_input, modality_hint, session_id
                   ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              INPUT NORMALIZATION (normalizer/)              │
    │                                                             │
    │  • Dispatches to TextAdapter / UrlAdapter / VoiceAdapter / │
    │    DocumentAdapter based on modality hint or content       │
    │  • Returns: NormalizedSignal (text, modality, metadata)    │
    └────────────┬──────────────────────────────────────────────┘
                 │
                 │ NormalizedSignal
                 ▼
    ┌─────────────────────────────────────────────────────────────┐
    │           EMOTION ENCODING (emotion/)                       │
    │                                                             │
    │  • TextEmotionEncoder: VADER + transformer classification  │
    │  • VoiceEmotionEncoder: Audio features (pitch, energy)     │
    │  • EmotionFuser: Combine multimodal signals                │
    │  • Returns: EmotionContext (valence, arousal, confidence)  │
    └────────────┬──────────────────────────────────────────────┘
                 │
                 │ NormalizedSignal, EmotionContext
                 ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              ROUTER DECISION (router/)                      │
    │                                                             │
    │  • ArtifactRouterClient: Load learned JSON model           │
    │  • RouterDaemonClient: gRPC remote router (with fallback)   │
    │  • Model: Feature extraction → softmax over experts        │
    │           + sigmoid for internet need                       │
    │  • Returns: RouterDecision (experts, memory_check,          │
    │             internet_needed, confidence)                   │
    └────────────┬──────────────────────────────────────────────┘
                 │
                 │ RouterDecision
                 ▼
    ┌─────────────────────────────────────────────────────────────┐
    │         OPTIONAL MEMORY RECALL (memory/)                    │
    │                                                             │
    │  if check_memory_first:                                    │
    │    • MemoryGraph.recall(query_text, limit=10)             │
    │    • Filter by relevance threshold (≥0.15)                │
    │    • High-confidence memory (conf≥0.8, rel≥0.35)          │
    │      can short-circuit to response assembly                │
    │  • ChromaVectorStore: Vector + FTS search                 │
    │  • SqliteMetaStore: Metadata + provenance                 │
    │  • Returns: list[MemoryNode]                              │
    └────────────┬──────────────────────────────────────────────┘
                 │
                 │ MemoryNode list (or empty)
                 ▼
    ┌─────────────────────────────────────────────────────────────┐
    │         DIALOGUE STATE & PLAN (dialogue.py)                 │
    │                                                             │
    │  • DialoguePlanner.build_state():                          │
    │    - Infer intent (greeting/code/factual/planning/follow-up)│
    │    - Style (concise/supportive/stepwise)                   │
    │    - Confidence                                             │
    │  • DialoguePlanner.build_plan():                           │
    │    - Mode (answer/clarify/plan/memory-recall)             │
    │    - Response style                                        │
    │    - Include sources? Next step?                           │
    │  • Returns: DialogueState, ResponsePlan                    │
    └────────────┬──────────────────────────────────────────────┘
                 │
                 │ DialogueState, ResponsePlan
                 ▼
    ┌─────────────────────────────────────────────────────────────┐
    │        OPTIONAL CLARIFICATION PATH                          │
    │                                                             │
    │  if response_plan["mode"] == "clarify":                   │
    │    • Generate clarification message                        │
    │    • Record turn trace                                     │
    │    • Stream response → return                              │
    │    • GOTO feedback & streaming                             │
    └────────────┬──────────────────────────────────────────────┘
                 │
                 │ (continue to internet/expert if not clarified)
                 ▼
    ┌─────────────────────────────────────────────────────────────┐
    │      OPTIONAL INTERNET RETRIEVAL (internet/)                │
    │                                                             │
    │  if decision["internet_needed"]:                           │
    │    • DuckDuckGoSearch: Query search engine                 │
    │    • ContentFetcher: GET + parse top 3 results             │
    │    • Combine content → citations                           │
    │  • Returns: InternetResult (content, citations)            │
    └────────────┬──────────────────────────────────────────────┘
                 │
                 │ InternetResult (or empty)
                 ▼
    ┌─────────────────────────────────────────────────────────────┐
    │        EXPERT POOL & EXECUTION (experts/)                   │
    │                                                             │
    │  • ExpertPool.load(): Load, cache, LRU evict              │
    │  • Expert.infer(): Execute inference with context          │
    │    - Query + memory nodes + internet citations            │
    │    - Dialogue state + response plan                       │
    │  • Returns: list[ExpertOutput]                            │
    │    (content, confidence, sources, citations, latency)     │
    └────────────┬──────────────────────────────────────────────┘
                 │
                 │ list[ExpertOutput]
                 ▼
    ┌─────────────────────────────────────────────────────────────┐
    │      RESPONSE ASSEMBLY (experts/assembler.py)               │
    │                                                             │
    │  • Single output: Realize styling                          │
    │  • Multiple outputs:                                       │
    │    - Rank by custom scorer (citations, next steps,        │
    │      confidence, entity match, length, query coverage)    │
    │    - Select best candidate (direct/grounded/stepwise)     │
    │    - Deduplicate citations                                │
    │  • Returns: final ExpertOutput (assembled + grounded)     │
    └────────────┬──────────────────────────────────────────────┘
                 │
                 │ ExpertOutput (final response)
                 ▼
    ┌─────────────────────────────────────────────────────────────┐
    │       LEARNING & FEEDBACK (learning/)                       │
    │                                                             │
    │  • FeedbackCollector.record_turn():                        │
    │    - Query coverage, entity match, symbol anchors         │
    │    - Citation count, response length                      │
    │    - Confidence, dialogue intent, outcome                 │
    │  • TurnTrace: Captured for offline training               │
    │  • ExpertCorrector: Build correction jobs if needed       │
    │  • ResponsePolicyTrainer: Fit policy from traces          │
    └────────────┬──────────────────────────────────────────────┘
                 │
                 │ Turn recorded in session buffer
                 ▼
    ┌─────────────────────────────────────────────────────────────┐
    │          RESPONSE STREAMING & OUTPUT                        │
    │                                                             │
    │  • _stream_text(): Split response into tokens              │
    │  • Yield token-by-token to client (AsyncIterator)         │
    │  • Client receives streamed response                       │
    └─────────────────────────────────────────────────────────────┘
                 │
                 │ Stream complete
                 ▼
    ┌─────────────────────────────────────────────────────────────┐
    │        SESSION TRACE FLUSH (runtime.py)                    │
    │                                                             │
    │  • flush_session_traces(session_id):                       │
    │    - Extract all turn traces from session                  │
    │    - Persist to LoRA dataset (.jsonl)                      │
    │    - Trigger response policy refresh (optional)           │
    │  • Learning loop (async background):                      │
    │    - Process ended sessions                               │
    │    - Score responses + generate corrections              │
    │    - Retrain router/policy models                        │
    └─────────────────────────────────────────────────────────────┘
```

---

## Critical Integration Points

### Memory & Learning Feedback Loop

1. **Coordinator.process()** records turn trace via `FeedbackCollector.record_turn()`
2. **WaseemBrainRuntime.flush_session_traces()** extracts traces
3. **ExpertCorrector.record_session_traces()** persists to `experts/lora/traces/{session_id}.jsonl`
4. **ResponsePolicyTrainer.fit()** loads traces, computes features, trains policy
5. **ResponsePolicyExporter.export_model()** writes `experts/response-policy.json`
6. **ResponseAssembler.reload_policy()** refreshes in-memory policy

### Router Training Pipeline

1. Collect labeled samples in `experts/router-samples.jsonl` (text, labels, internet_needed)
2. **scripts/train_router.py** loads samples
3. **RouterTrainer.fit()** → feature extraction + SGDClassifier
4. **RouterExporter.export_model()** → `experts/router.json`
5. **ArtifactRouterClient** loads and uses in production

### Expert Lifecycle

1. **ExpertRegistry** loads manifest from `experts/registry.json`
2. **ExpertPool.load()** creates Expert instance if needed
3. **Expert.preload()** initializes session backend (lazy or eager)
4. **Expert.infer()** executes with context (memory, internet, dialogue state)
5. **ExpertPool** maintains LRU cache; **_run_idle_evictor()** cleanup
6. **ExpertMapperProtocol** notifies gRPC daemon of loaded experts (optional)

### Internet Integration

1. **Coordinator** checks router decision's `internet_needed` flag
2. **InternetModule.query()** → DuckDuckGoSearch + ContentFetcher
3. Results added to **ExpertRequest** as `internet_citations`
4. Expert and Assembler use citations for grounding
5. Citations stored in **MemoryGraph** for future recall

### Emotion-Based Routing (Future)

1. **TextEmotionEncoder** + **VoiceEmotionEncoder** → multimodal sentiment
2. **EmotionFuser** combines text + voice emotion
3. **RouterDaemonClient.decide()** passes emotion to gRPC (if available)
4. Router can use emotion context for biased routing (currently artifact-only)

---

## Type System Architecture

**Core Type Hierarchy:**

```
Result[T, E] = OkResult[T] | ErrResult[E]
├── ok(value: T) → {"ok": True, "value": value}
└── err(error: E) → {"ok": False, "error": error}

NormalizedSignal (TypedDict)
├── text: str
├── modality: Modality (text/voice/image/file/url)
├── raw_audio: bytes (optional)
├── metadata: dict[str, Any]
├── session_id: SessionId
├── filename: str (optional)
└── mime_type: str (optional)

EmotionContext (TypedDict)
├── primary_emotion: EmotionName
├── valence: float [-1..1]
├── arousal: float [0..1]
├── confidence: float [0..1]
└── source: EmotionSource (text/voice/both)

RouterDecision (TypedDict)
├── experts_needed: list[ExpertId]
├── check_memory_first: bool
├── internet_needed: bool
├── confidence: float
└── reasoning_trace: str

DialogueState (TypedDict)
├── intent: DialogueIntent
├── style: ResponseStyle
├── needs_clarification: bool
├── prefers_steps: bool
├── references_workspace: bool
├── references_memory: bool
├── asks_for_reasoning: bool
├── confidence: float
├── signals: list[str]
└── locale: str

ResponsePlan (TypedDict)
├── mode: ResponseMode (answer/clarify/plan/memory-recall)
├── lead_style: ResponseStyle
├── include_sources: bool
├── include_next_step: bool
├── max_citations: int
├── rationale: str
└── locale: str

ExpertOutput (TypedDict)
├── expert_id: ExpertId
├── content: str
├── confidence: float
├── sources: list[str]
├── latency_ms: float
├── citations: list[EvidenceReference]
├── render_strategy: RenderStrategy
└── summary: str

MemoryNode (TypedDict)
├── id: MemoryNodeId
├── content: str
├── embedding: EmbeddingVector
├── tags: list[str]
├── source: str
├── created_at: float
├── last_accessed: float
├── access_count: int
├── confidence: float
├── session_id: SessionId
├── source_type: EvidenceSourceType
└── provenance: list[ProvenanceRecord]

TurnTrace (TypedDict)
├── session_id: SessionId
├── expert_id: ExpertId
├── query: str
├── response: str
├── dialogue_intent: str
├── response_mode: str
├── render_strategy: RenderStrategy
├── citations_count: int
├── has_next_step: bool
├── query_coverage: float
├── entity_match_score: float
├── symbol_anchor_score: float
├── response_length_tokens: int
├── confidence: float
├── decision_trace: str
├── outcome: Literal[...]
└── timestamp: float
```

---

## Summary

The Waseem Brain codebase is architecturally organized as:

1. **Runtime** (`runtime.py`) - Entry point orchestrating all subsystems
2. **Coordinator** (`coordinator.py`) - Main control loop and query pipeline
3. **Router** (`router/`) - Learned routing model (artifact or gRPC)
4. **Experts** (`experts/`) - Execution pool with lazy loading & LRU caching
5. **Memory** (`memory/`) - Hybrid SQLite + vector search
6. **Learning** (`learning/`) - Offline training of router & response policy
7. **Internet** (`internet/`) - Optional web search & retrieval
8. **Emotion** (`emotion/`) - Multimodal sentiment encoding
9. **Normalizer** (`normalizer/`) - Input adaptation (text/url/voice/file)
10. **Dialogue** (`dialogue.py`) - State & plan inference
11. **Helpers** (`helpers/`) - Common utilities & validation
12. **Scripts** (`scripts/`) - CLI, training, diagnostics

**Key Design Principles:**
- **No placeholders** - All experts, backends, and features are real
- **Offline learning only** - Training via persisted traces, no live self-modification
- **CPU-first** - Compact models, no dense LLM in critical path
- **Explicit grounding** - Citations and provenance tracked throughout
- **Bounded resources** - Expert LRU eviction, vector index capacity management
- **Honest degradation** - Reports truth, skips unavailable features

