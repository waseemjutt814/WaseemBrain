# Waseem Brain - Complete System Documentation

**Version:** 1.0 (April 5, 2026)  
**Author:** Muhammad Waseem Akram  
**Status:** Production-Ready ✓

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Quick Start & Installation](#quick-start--installation)
4. [Core Runtime Components](#core-runtime-components)
5. [Processing Pipeline](#processing-pipeline)
6. [All Functions & Methods](#all-functions--methods)
7. [Module Reference](#module-reference)
8. [Expert System](#expert-system)
9. [Memory System](#memory-system)
10. [Learning Pipeline](#learning-pipeline)
11. [Interfaces & APIs](#interfaces--apis)
12. [Scripts & CLI](#scripts--cli)
13. [Configuration](#configuration)
14. [Verification & Testing](#verification--testing)

---

## Executive Summary

**Waseem Brain** is a CPU-first local AI stack for offline-capable reasoning and knowledge grounding:

- **Local Processing:** No API keys, no external services, fully offline-capable
- **Persistent Memory:** SQLite + HNSW vector index for knowledge storage and retrieval
- **Manifest-Driven Experts:** Pluggable expert modules with lifecycle management
- **Learning Pipeline:** Offline training from interaction traces for continuous improvement
- **Complete I/O:** Text, URLs, files, voice modalities with automatic detection
- **Grounded Reasoning:** Memory-backed responses with citations and evidence
- **Quality Gates:** No placeholder behavior; honest degradation when needed

### Key Features

✓ Zero API dependencies  
✓ Real offline operation  
✓ Persistent memory with vector & text search  
✓ Plugin-based expert system  
✓ Emotional state encoding  
✓ Dynamic routing to best expert  
✓ Turn-based learning from real usage  
✓ TypeScript + Python + Rust stack  
✓ Production-ready with health checks  

---

## System Architecture

### High-Level Flow

```
User Input (Text/URL/Voice/File)
    ↓
[Normalizer] - Modality detection & standardization
    ↓
[Emotion Encoder] - Extract emotional context
    ↓
[Router] - Select best expert(s) based on query
    ↓
[Memory Graph] - Recall relevant knowledge
    ↓
[Expert Pool] - Execute selected experts in parallel
    ↓
[Response Assembler] - Synthesize final response
    ↓
[Quality Gates] - Validate response quality
    ↓
User Output (Rendered Response)
    ↓
[Learning Loop] - Record trace for future training
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Runtime** | Python 3.11 | Core AI logic, memory, experts |
| **Interface** | TypeScript/Fastify | HTTP/WebSocket API layer |
| **Router** | Rust (optional) | gRPC-based expert routing daemon |
| **Memory** | SQLite + HNSW | Persistent storage + vector search |
| **Embeddings** | sentence-transformers | 384-dim text vectors |
| **Voice** | Faster-whisper | Speech-to-text |
| **Emotion** | VADER + transformers | Sentiment & emotion detection |

---

## Quick Start & Installation

### Prerequisites

```bash
# Python 3.11+
python --version

# Node.js 20+
node --version

# Git (for development)
git --version
```

### Installation

```powershell
# Clone and navigate
cd "d:\latest brain"

# Install Python dependencies
python -m pip install -r requirements-runtime.txt
python -m pip install -r requirements-dev.txt
python -m pip install -r requirements-training.txt

# Install Node dependencies
pnpm install

# Prepare runtime (warmup, knowledge bootstrap)
python scripts/prepare_runtime.py

# OR use convenience batch file
run.bat prepare
```

### Verify Installation

```powershell
# Quick health check
python -c "from brain import WaseemBrainRuntime; rt = WaseemBrainRuntime(); print(rt.health()['condition'])"

# Expected output: READY (or "strong" if response policy trained)
```

### First Query

```powershell
# One-shot query
python scripts/chat_cli.py --once "Hello, what can you do?"

# Interactive chat
run.bat chat

# HTTP API (after starting interface)
run.bat dev
# Then: curl -X POST http://localhost:8080/query -d '{"text":"hello"}'
```

---

## Core Runtime Components

### 1. WaseemBrainRuntime (brain/runtime.py)

Main entry point for all query operations.

#### Class: `WaseemBrainRuntime`

```python
class WaseemBrainRuntime:
    """Core orchestrator for the entire brain system."""
    
    def __init__(
        self,
        settings: BrainSettings | None = None,
        memory_graph: MemoryGraph | None = None,
        expert_pool: ExpertPool | None = None,
        registry: ExpertRegistry | None = None,
        internet_module: InternetModule | None = None,
        coordinator: WaseemBrainCoordinator | None = None,
    ) -> None:
        """Initialize runtime with optional dependency overrides."""
        
    # === MAIN APIs ===
    async def query(
        self,
        raw_input: object,
        modality_hint: str,
        session_id: SessionId,
    ) -> AsyncIterator[str]:
        """
        Process query through full pipeline.
        Yields response tokens as they're generated.
        
        Args:
            raw_input: Query content (text, URL, bytes, etc.)
            modality_hint: "text", "url", "voice", "file"
            session_id: Session identifier for trace linkage
            
        Yields:
            Response text tokens
            
        Example:
            async for token in runtime.query(
                raw_input="What is AI?",
                modality_hint="text",
                session_id=SessionId("my-session")
            ):
                print(token, end="", flush=True)
        """
    
    def health(self) -> HealthSnapshot:
        """
        Get complete system health snapshot.
        
        Returns:
            HealthSnapshot with:
            - status: "ok"
            - condition: "strong" | "ready" | "attention"
            - components: dict of all subsystem states
            - metrics: memory, experts, router, learning status
            
        Example:
            health = runtime.health()
            if health["condition"] != "attention":
                print(f"System ready: {health['condition_summary']}")
        """
    
    async def recall(
        self,
        query: str,
        limit: int = 5,
        session_id: SessionId | None = None,
    ) -> MemoryNodeSummary:
        """
        Recall relevant knowledge from memory.
        
        Args:
            query: Search text
            limit: Max results to return
            session_id: Optional context session
            
        Returns:
            List of memory nodes with id, content, confidence, source
            
        Example:
            results = await runtime.recall("Python functions")
            for node in results:
                print(f"{node['content'][:50]}... ({node['confidence']:.2f})")
        """
```

### 2. WaseemBrainCoordinator (brain/coordinator.py)

Orchestrates the query processing pipeline.

#### Class: `WaseemBrainCoordinator`

```python
class WaseemBrainCoordinator:
    """Orchestrates the complete processing pipeline."""
    
    def __init__(
        self,
        memory_graph: MemoryGraph,
        expert_pool: ExpertPool,
        router_client: RouterClientProtocol,
        internet_module: InternetModule,
        recall_limit: int = 10,
    ) -> None:
        """Initialize coordinator with required subsystems."""
    
    async def process(
        self,
        raw_input: object,
        modality_hint: str,
        session_id: SessionId,
    ) -> AsyncIterator[str]:
        """
        Main query processing pipeline.
        
        Pipeline stages:
        1. Normalization: Convert input to standard form
        2. Emotion Encoding: Extract emotional context
        3. Routing: Select best expert(s)
        4. Memory Recall: Fetch relevant knowledge
        5. Expert Execution: Run selected experts
        6. Response Assembly: Synthesize final output
        7. Learning: Record turn trace
        
        Args:
            raw_input: Any input format
            modality_hint: Modality hint for normalization
            session_id: Session for context tracking
            
        Yields:
            Response tokens streamed in real-time
        """
    
    async def _normalize_input(self, raw_input, modality_hint) -> NormalizedInput:
        """Step 1: Convert input to normalized form."""
        
    async def _encode_emotion(self, norm_input) -> EmotionState:
        """Step 2: Detect emotion from text/voice."""
        
    async def _route_query(self, norm_input, emotion) -> list[ExpertId]:
        """Step 3: Route to best expert(s)."""
        
    async def _recall_memory(self, norm_input) -> list[MemoryNode]:
        """Step 4: Recall relevant knowledge."""
        
    async def _execute_experts(self, expert_ids, context) -> list[ExpertResponse]:
        """Step 5: Execute selected experts."""
        
    async def _assemble_response(self, expert_responses) -> str:
        """Step 6: Synthesize final output."""
```

---

## Processing Pipeline

### Stage 1: Normalization

Converts any input format into standard form.

#### Module: `brain/normalizer/`

```python
# Classes and functions for input normalization

class TextAdapter:
    """Normalize text input."""
    async def adapt(self, raw_input: str) -> NormalizedInput
    
class UrlAdapter:
    """Fetch and normalize URL content."""
    async def adapt(self, url: str) -> NormalizedInput
    
class VoiceAdapter:
    """Transcribe and normalize voice input."""
    async def adapt(self, audio_bytes: bytes, sample_rate: int) -> NormalizedInput
    
class DocumentAdapter:
    """Extract text from documents."""
    async def adapt(self, file_path: str) -> NormalizedInput

async def detect_modality(raw_input: object) -> str:
    """Auto-detect input modality."""
    # Returns: "text", "url", "voice", "file"
```

### Stage 2: Emotion Encoding

Extracts emotional context from input.

#### Module: `brain/emotion/`

```python
class TextEmotionEncoder:
    """Encode emotion from text."""
    
    def encode(self, text: str) -> EmotionState:
        """
        Returns EmotionState with:
        - sentiment: float (-1.0 to 1.0)
        - emotions: dict of emotion scores
        - intensity: 0.0 to 1.0
        - dominant_emotion: str
        """

class VoiceEmotionEncoder:
    """Encode emotion from voice."""
    
    def encode(self, audio: np.ndarray, sample_rate: int) -> EmotionState:
        """Extract emotion from speech prosody."""

def fuse_emotions(text_emotion: EmotionState, voice_emotion: EmotionState) -> EmotionState:
    """Combine multimodal emotion signals."""
```

### Stage 3: Routing

Dynamic selection of best expert(s).

#### Module: `brain/router/`

```python
class RouterArtifact:
    """Learned routing model."""
    
    def predict(
        self,
        query: str,
        emotion: EmotionState,
        memory_context: list[MemoryNode],
    ) -> list[tuple[ExpertId, float]]:
        """
        Predict expert ranking.
        
        Returns: [(expert_id, confidence), ...]
        """

class HybridRouterClient:
    """Router with local + remote fallback."""
    
    def route(self, query: str, context: dict) -> list[ExpertId]:
        """Route to best expert(s)."""

class RouterDaemonClient:
    """gRPC client for remote router."""
    
    async def route(self, request: RouterRequest) -> RouterResponse:
        """Call remote router daemon."""
```

### Stage 4: Memory Recall

Fetch relevant knowledge.

#### Module: `brain/memory/`

```python
class MemoryGraph:
    """Unified memory interface."""
    
    async def recall(
        self,
        query: str,
        limit: int = 5,
        session_id: SessionId | None = None,
    ) -> list[MemoryNode]:
        """
        Recall relevant memory nodes.
        
        Algorithm:
        1. Embed query with MemoryEmbedder
        2. Vector search in HNSW index
        3. FTS fallback if vector search unavailable
        4. Rank by confidence + relevance
        5. Filter by session context
        """
    
    async def add_node(
        self,
        content: str,
        source: str,
        confidence: float = 0.8,
        source_type: str = "knowledge",
    ) -> MemoryNode:
        """Store knowledge in memory."""
    
    def ensure_session(self, session_id: SessionId) -> None:
        """Create session context."""
    
    async def decay(self, age_days: int = 90) -> int:
        """Remove old memories (configurable retention)."""

class MemoryEmbedder:
    """Convert text to embeddings."""
    
    def embed(self, text: str) -> EmbeddingVector:
        """Return 384-dimensional embedding."""
    
    def embed_batch(self, texts: list[str]) -> list[EmbeddingVector]:
        """Batch embed for efficiency."""

class ChromaVectorStore:
    """Vector search with HNSW."""
    
    async def search(
        self,
        query_vector: EmbeddingVector,
        k: int = 5,
    ) -> list[tuple[str, float]]:
        """Similarity search with cosine distance."""
    
    async def add(
        self,
        id: str,
        embedding: EmbeddingVector,
        metadata: dict,
    ) -> None:
        """Add vector to index."""

class SqliteMetaStore:
    """Metadata + full-text search."""
    
    async def search(self, query: str, limit: int = 5) -> list[dict]:
        """FTS search on metadata."""
    
    async def add(self, id: str, data: dict) -> None:
        """Store metadata."""
```

### Stage 5: Expert Execution

Run selected experts.

#### Module: `brain/experts/`

```python
class Expert:
    """Individual expert executor."""
    
    def __init__(self, manifest: ExpertManifest) -> None:
        """Load expert from manifest."""
    
    async def execute(
        self,
        query: str,
        context: ExpertContext,
    ) -> ExpertResponse:
        """
        Execute expert logic.
        
        Context includes:
        - memory_recall: relevant MemoryNodes
        - emotion: EmotionState
        - internet_context: optional web results
        - citation_limit: max citations to include
        
        Returns:
        ExpertResponse with:
        - content: expert's answer
        - confidence: 0.0-1.0 confidence score
        - citations: evidence sources
        - metadata: expert-specific info
        """

class ExpertPool:
    """LRU pool with lifecycle management."""
    
    async def get(self, expert_id: ExpertId) -> Expert:
        """Get expert, loading if needed (with LRU eviction)."""
    
    async def execute_parallel(
        self,
        expert_ids: list[ExpertId],
        context: ExpertContext,
    ) -> list[ExpertResponse]:
        """Execute multiple experts in parallel."""
    
    def release(self, expert_id: ExpertId) -> None:
        """Release expert (moves to idle timeout)."""
    
    def unload_idle(self) -> int:
        """Unload experts exceeding idle timeout. Returns count unloaded."""

class ExpertRegistry:
    """Load and validate expert manifests."""
    
    def all(self) -> list[ExpertManifest]:
        """List all available experts."""
    
    def get(self, expert_id: ExpertId) -> ExpertManifest:
        """Load expert manifest."""
    
    def validate(self) -> Result[None, str]:
        """Validate all expert artifacts."""
```

### Stage 6: Response Assembly

Synthesize final response.

#### Module: `brain/experts/assembler.py`

```python
class ResponseAssembler:
    """Synthesize response from multiple expert outputs."""
    
    async def assemble(
        self,
        expert_responses: list[ExpertResponse],
        query: str,
        emotion: EmotionState,
        render_strategy: RenderStrategy = "markdown",
    ) -> str:
        """
        Assemble final response.
        
        Algorithm:
        1. Rank expert responses by confidence + learned policy
        2. Synthesize consensus answer
        3. Collect citations from top responses
        4. Format for final output
        5. Apply quality gates
        
        Render strategies:
        - "markdown": Structured markdown format
        - "plain": Plain text
        - "json": Structured JSON
        """
    
    async def _rank_responses(
        self,
        responses: list[ExpertResponse],
    ) -> list[tuple[ExpertResponse, float]]:
        """Rank by confidence + learned preference."""
    
    async def _synthesize(
        self,
        top_responses: list[ExpertResponse],
        query: str,
    ) -> str:
        """Combine responses into single answer."""
    
    def _collect_citations(
        self,
        responses: list[ExpertResponse],
        limit: int = 4,
    ) -> list[EvidenceReference]:
        """Extract and deduplicate citations."""
```

---

## All Functions & Methods

### Helper Utilities (brain/helpers/)

Complete documentation of all 65+ utility exports.

#### logger.py - Logging & Configuration

```python
def get_logger(name: str) -> logging.Logger:
    """Get or create named logger with module-level caching."""
    
def configure_logging(
    level: int = logging.INFO,
    format_str: str | None = None,
    file_path: str | None = None,
) -> None:
    """Configure root logger with stderr and optional file output."""
    
def log_exception(
    logger: logging.Logger,
    exc: Exception,
    context: str = "",
) -> None:
    """Log exception with optional operation context."""
```

#### errors.py - Custom Exception Hierarchy

```python
class BrainError(Exception):
    """Base exception with code classification."""
    
class ValidationError(BrainError):
    """Input validation failed."""
    
class ConfigError(BrainError):
    """Configuration invalid or missing."""
    
class RuntimeError(BrainError):
    """Unexpected runtime failure."""
    
class TimeoutError(BrainError):
    """Operation exceeded time limit."""
    
class NotFoundError(BrainError):
    """Required resource not found."""
    
class ConflictError(BrainError):
    """Operation conflicts with existing state."""
    
class UnsupportedError(BrainError):
    """Feature not supported in this context."""
```

#### timing.py - Performance Monitoring

```python
class Timer:
    """Context manager for measuring execution time."""
    
    def __init__(self, operation: str = "Operation", log: bool = True):
        """Create timer with optional automatic logging."""
    
    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
    
    @property
    def result(self) -> TimerResult:
        """Get detailed timer result."""

@contextmanager
def timer(operation: str = "Operation", log: bool = True) -> Iterator[Timer]:
    """Context manager form of Timer."""
    
class PerformanceMonitor:
    """Aggregate statistics over many measurements."""
    
    def record(self, elapsed_ms: float) -> None:
        """Record a measurement."""
    
    @property
    def count(self) -> int: ...
    
    @property
    def average(self) -> float: ...
    
    @property
    def min(self) -> float: ...
    
    @property
    def max(self) -> float: ...
    
    @property
    def p50(self) -> float: ... # Median
    
    @property
    def p95(self) -> float: ... # 95th percentile
    
    @property
    def p99(self) -> float: ... # 99th percentile
```

#### validation.py - Input Validators

```python
def validate_text(text: str, min_len: int = 1, max_len: int = 10000) -> bool:
    """Validate text content."""
    
def validate_modality(modality: str) -> bool:
    """Validate modality is one of: text, url, voice, file."""
    
def validate_confidence(score: float) -> bool:
    """Validate confidence is in [0.0, 1.0]."""
    
def validate_response_style(style: str) -> bool:
    """Validate render strategy."""
    
def validate_intent(intent: str) -> bool:
    """Validate query intent."""
    
def validate_token_count(tokens: int) -> bool:
    """Validate token count is reasonable."""
    
def validate_required(obj: Any, *fields: str) -> bool:
    """Validate required fields exist."""
```

#### formatting.py - Output Formatting

```python
def format_bytes(b: int) -> str:
    """Convert bytes to human-readable format: 1.5 MB."""
    
def format_duration(ms: float) -> str:
    """Convert ms to human format: 45.3s, 123ms, etc."""
    
def format_confidence(score: float) -> str:
    """Convert 0.0-1.0 to percentage: 85%."""
    
def truncate_text(text: str, max_len: int = 100) -> str:
    """Truncate text with ellipsis."""
    
def format_list(items: list[str], sep: str = ", ") -> str:
    """Join list elements nicely."""
    
def format_json_snippet(obj: Any, max_len: int = 200) -> str:
    """Pretty-print JSON snippet."""
    
def format_code_snippet(code: str, max_len: int = 300) -> str:
    """Format code with syntax awareness."""
    
def format_url(url: str, max_len: int = 60) -> str:
    """Make URL display-friendly."""
    
def format_timestamp(ts: float) -> str:
    """Convert Unix timestamp to readable format."""
    
def format_error_message(exc: Exception) -> str:
    """Format exception message for display."""
```

#### decorators.py - Function Decorators

```python
@timer(name: str | None = None)
def decorated_func(): ...
    """Measure execution time and log."""

@cached(ttl_seconds: int = 300)
def decorated_func(): ...
    """Cache results with time-to-live."""
    
@retry(max_attempts: int = 3, delay_seconds: float = 1.0, backoff_factor: float = 1.0)
def decorated_func(): ...
    """Retry with exponential backoff."""
    
@ratelimit(calls_per_second: float = 10.0)
def decorated_func(): ...
    """Rate limit function calls."""
    
@validate_args(param1=lambda x: ..., param2=lambda x: ...)
def decorated_func(param1, param2): ...
    """Validate arguments before execution."""
    
@debug(verbose: bool = True)
def decorated_func(): ...
    """Log calls and results at DEBUG level."""
    
@ensure_type(param1=str, param2=int)
def decorated_func(param1, param2): ...
    """Enforce argument types at runtime."""
```

#### common.py - General Utilities

```python
def safe_json_loads(s: str, default: Any = None) -> Any:
    """Parse JSON with error handling."""
    
def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """Serialize to JSON with error handling."""
    
def deep_get(d: dict, path: str, default: Any = None) -> Any:
    """Get nested dict value: deep_get(d, "a.b.c")."""
    
def deep_set(d: dict, path: str, value: Any) -> None:
    """Set nested dict value: deep_set(d, "a.b.c", val)."""
    
def merge_dicts(d1: dict, d2: dict, deep: bool = True) -> dict:
    """Merge two dicts, optionally recursively."""
    
def ensure_dir(path: str) -> Path:
    """Create directory if it doesn't exist."""
    
def read_json_file(path: str) -> Any:
    """Load JSON file with error handling."""
    
def write_json_file(path: str, obj: Any) -> None:
    """Write JSON file with formatting."""
    
def chunks(items: list[T], size: int) -> Iterator[list[T]]:
    """Yield successive chunks of list."""
    
def flatten(nested: list[list[T]]) -> list[T]:
    """Flatten nested list."""
    
def unique_preserve_order(items: list[T]) -> list[T]:
    """Remove duplicates while preserving order."""
    
def invert_dict(d: dict[K, V]) -> dict[V, K]:
    """Invert keys and values."""
```

#### testing.py - Test Utilities

```python
class MockQuery:
    """Mock query object for testing."""
    
class MockResponse:
    """Mock expert response for testing."""
    
class TestRegistry:
    """Register and retrieve test fixtures."""
    
def register_fixture(name: str, obj: Any) -> None:
    """Register test fixture."""
    
def get_fixture(name: str, default: Any = None) -> Any:
    """Retrieve test fixture."""
    
def create_test_memory_node(content: str, confidence: float = 0.8) -> MemoryNode:
    """Create memory node for testing."""
    
def assert_valid_response(response: dict) -> None:
    """Assert response has required fields."""
    
async def create_mock_runtime() -> WaseemBrainRuntime:
    """Create runtime with mocked dependencies for testing."""
```

---

## Module Reference

### Type System (brain/types.py)

```python
# Result type for error handling
Result[T, E] = dict[Literal["ok"], T] | dict[Literal["error"], E]

def ok(value: T) -> Result[T, E]: ...
def err(error: E) -> Result[T, E]: ...

# Core types
SessionId = NewType("SessionId", str)
ExpertId = NewType("ExpertId", str)
EmbeddingVector = list[float]  # 384-dimensional

# Input/Output types
class NormalizedInput(TypedDict):
    text: str
    modality: str
    metadata: dict[str, Any]
    
class EmotionState(TypedDict):
    sentiment: float  # -1.0 to 1.0
    emotions: dict[str, float]  # joy, sadness, anger, etc.
    intensity: float  # 0.0 to 1.0
    
class MemoryNode(TypedDict):
    id: str
    content: str
    confidence: float
    source: str
    source_type: str
    
class ExpertResponse(TypedDict):
    content: str
    confidence: float
    citations: list[EvidenceReference]
    metadata: dict[str, Any]
    
class EvidenceReference(TypedDict):
    id: str
    source_type: str  # "memory", "internet", "expert"
    label: str
    snippet: str
    uri: str
```

### Configuration (brain/config.py)

```python
class BrainSettings:
    """System configuration."""
    
    # Paths
    repo_root: Path
    expert_dir: Path
    chroma_dir: Path
    sqlite_dir: Path
    
    # Embeddings
    embedding_backend: str  # "auto", "sentence-transformers"
    embedding_model_name: str  # "all-MiniLM-L6-v2"
    embedding_dimensions: int  # 384
    
    # Memory
    memory_vector_backend: str  # "auto", "hnsw", "chroma"
    memory_recall_limit: int  # 10 (per query)
    memory_decay_days: int  # 90 (retention)
    
    # Experts
    expert_max_loaded: int  # 3
    expert_idle_timeout_sec: int  # 30
    
    # Internet
    internet_enabled: bool  # true
    internet_max_requests_per_query: int  # 5
    internet_cache_ttl_seconds: int  # 3600
    
    # Router
    router_backend: str  # "auto", "grpc", "artifact"
    router_confidence_threshold: float  # 0.7
    
    # Learning
    learning_enabled: bool  # true
    learning_min_signal_strength: float  # 0.6
    
    # HTTP/gRPC
    api_port: int  # 8080
    grpc_host: str  # "127.0.0.1"
    grpc_port: int  # 50051
    
    # Other
    log_level: str  # "info"
    max_citations: int  # 4
    strict_runtime: bool  # true

def load_settings(env: dict | None = None) -> BrainSettings:
    """Load configuration from environment variables."""
```

---

## Expert System

### Expert Manifest Format

```yaml
# experts/base/language-en/manifest.yaml
id: language-en
name: English Language Expert
version: "1.0"
description: General language, writing, grammar, communication

rules:
  trigger_keywords: [grammar, english, language, writing, communication]
  trigger_intent: [CLARIFY, EXPLAIN, CORRECT]
  
patterns:
  - id: grammar-check
    condition: "intent == CORRECT"
    action: grammar_checking_logic
    
  - id: essay-help
    condition: "intent == EXPLAIN"
    action: writing_guidance
    
capabilities:
  - grammar checking
  - writing advice
  - language patterns
  
confidence: 0.85

training:
  enabled: true
  min_accuracy: 0.75
```

### Creating Custom Experts

```python
# experts/base/my-expert/implementation.py

from brain.types import ExpertContext, ExpertResponse

async def execute(context: ExpertContext) -> ExpertResponse:
    """
    Custom expert logic.
    
    Args:
        context: Contains query, memory, emotion, internet context
        
    Returns:
        ExpertResponse with content and citations
    """
    # Your implementation here
    return {
        "content": "Expert response content",
        "confidence": 0.85,
        "citations": [
            {
                "id": "memory-1",
                "source_type": "memory",
                "label": "Related knowledge",
                "snippet": "...",
                "uri": "memory://node-1"
            }
        ],
        "metadata": {"expert_info": "..."}
    }
```

---

## Memory System

### Data Storage

```
data/
├── sqlite/
│   ├── memory.db              # Metadata + FTS index
│   ├── sessions.db            # Session tracking
│   └── traces.db              # Learning traces
├── chroma/
│   ├── memory.index/          # HNSW vector index
│   └── metadata/              # Vector metadata
└── cache/
    └── embeddings/            # Cached embeddings
```

### Memory Node Structure

```python
class MemoryNode(TypedDict):
    id: str                     # UUID
    content: str                # Knowledge text
    embedding: EmbeddingVector  # 384-dimensional vector
    confidence: float           # 0.0-1.0
    source: str                 # Origin (file, api, learned, etc.)
    source_type: str            # "knowledge", "trace", "expert_correction"
    tags: list[str]             # For filtering
    created_at: float           # Unix timestamp
    last_accessed: float        # For decay
    
    # Session context
    session_id: SessionId       # Associated session (optional)
    metadata: dict[str, Any]    # Custom metadata
```

### Memory Operations

```python
# Add knowledge
await memory.add_node(
    content="Python functions are defined with def keyword",
    source="bootstrap-knowledge",
    confidence=0.95,
    source_type="knowledge"
)

# Recall
results = await memory.recall("python function syntax", limit=5)
# Returns list of MemoryNodes sorted by relevance

# Decay old memories
removed_count = await memory.decay(age_days=90)
```

---

## Learning Pipeline

### Turn Trace Structure

```python
class TurnTrace(TypedDict):
    """Single turn in learning pipeline."""
    
    session_id: SessionId
    turn_number: int
    timestamp: float
    
    # Input
    query: str
    modality: str
    emotion: EmotionState
    
    # Processing
    routed_experts: list[ExpertId]
    recalled_memory: list[MemoryNode]
    
    # Output
    response: str
    confidence: float
    expert_responses: list[ExpertResponse]
    
    # Feedback (optional, added later)
    user_feedback: str | None  # "positive" | "negative" | "correction"
    feedback_correction: str | None
    learning_signal_strength: float | None
```

### Learning Components

```python
class ResponsePolicyTrainer:
    """Train policy to select best expert combinations."""
    
    async def train(self, traces: list[TurnTrace]) -> ResponsePolicy:
        """
        Train from user interaction traces.
        
        Learns:
        - Which expert combinations work best for query types
        - When to combine vs. pick single expert
        - Response ranking preferences
        """

class ExpertCorrector:
    """Generate correction training data."""
    
    async def create_correction_job(
        self,
        expert_id: ExpertId,
        failing_traces: list[TurnTrace],
    ) -> CorrectionJob:
        """Create training job for expert improvement."""

class FeedbackCollector:
    """Collect and normalize user feedback."""
    
    def collect(
        self,
        session_id: SessionId,
        turn_number: int,
        feedback: str,
        correction: str | None = None,
    ) -> TurnFeedback:
        """Record turn feedback."""

# Async self-learning loop
async def self_learning_loop(runtime: WaseemBrainRuntime):
    """Background learning from interaction traces."""
    while True:
        # Every hour
        await asyncio.sleep(3600)
        
        # Check for new traces
        traces = await load_recent_traces()
        
        # Filter by minimum signal strength
        strong_traces = filter_by_signal_strength(traces, min=0.6)
        
        if len(strong_traces) >= 10:
            # Train new policy
            new_policy = await trainer.train(strong_traces)
            await save_policy(new_policy)
```

---

## Interfaces & APIs

### HTTP API (via interface/src)

```typescript
// POST /query
{
  "text": "What is machine learning?",
  "sessionId": "session-123"
}
// Response: Streaming text response

// POST /query/text
// POST /query/url
// POST /query/voice
// POST /query/file

// GET /health
// Returns: Overall system health and component status

// GET /memory/recall?q=python&limit=5
// Returns: Memory search results

// GET /experts
// Returns: List of loaded experts
```

### CLI Interface (scripts/chat_cli.py)

```bash
# Interactive chat
python scripts/chat_cli.py

# One-shot query
python scripts/chat_cli.py --once "Hello"

# Specific modality
python scripts/chat_cli.py --once --modality url "https://example.com"

# Dashboard only
python scripts/chat_cli.py --dashboard

# Custom session
python scripts/chat_cli.py --session "my-session"
```

#### CLI Commands

| Command | Function |
|---------|----------|
| `/status` | Full branded dashboard |
| `/health` | Raw health snapshot |
| `/experts` | List loaded experts |
| `/recall <text>` | Search memory |
| `/learning` | Learning status |
| `/project` | Project condition |
| `/dashboard` | Refresh display |
| `/clear` | Clear screen |
| `/quit` | Exit |

---

## Scripts & CLI

### Core Scripts

#### prepare_runtime.py
```bash
python scripts/prepare_runtime.py [OPTIONS]

Options:
  --skip-smoke-query     Skip test query
  --skip-vector-index    Skip embedding index setup
  --skip-bootstrap       Skip knowledge bootstrap
  --verbose              Verbose output
```

#### chat_cli.py
```bash
python scripts/chat_cli.py [OPTIONS] [QUERY]

Options:
  --once                 One-shot query mode
  --modality TEXT|URL|VOICE|FILE
  --session SESSION_ID   Custom session ID
  --dashboard            Show dashboard only
  --verbose              Debug output
```

#### manage_router_daemon.py
```bash
python scripts/manage_router_daemon.py COMMAND [OPTIONS]

Commands:
  start                  Start router daemon
  stop                   Stop router daemon
  status                 Show daemon status
  logs                   Show daemon logs
  rebuild                Rebuild Rust daemon
  
Options:
  --port PORT            gRPC port (default 50051)
  --skip-build           Don't rebuild
```

#### train_response_policy.py
```bash
python scripts/train_response_policy.py [OPTIONS]

Options:
  --min-accuracy FLOAT   Minimum accuracy threshold
  --test-split FLOAT     Test set fraction (default 0.2)
  --epochs INT           Training epochs (default 50)
  --verbose              Verbose training output
```

#### train_router.py
```bash
python scripts/train_router.py [OPTIONS]

Options:
  --dataset PATH         Dataset file path
  --min-samples INT      Minimum samples per expert
  --test-split FLOAT     Test fraction
  --output PATH          Output model path
```

#### benchmark.py
```bash
python scripts/benchmark.py QUERY [OPTIONS]

Options:
  --iterations INT       Number of iterations (default 1)
  --warmup INT           Warmup iterations (default 1)
  --modality TEXT|URL    Input modality
  --output PATH          Save results to file
```

#### inspect_memory.py
```bash
python scripts/inspect_memory.py [OPTIONS]

Options:
  --query TEXT           Search memory
  --limit INT            Result limit
  --show-embeddings      Show vector embeddings
  --show-metadata        Show all metadata
```

#### diagnose_backends.py
```bash
python scripts/diagnose_backends.py

Checks:
- Python version and deps
- SQLite database
- Vector index status
- Expert artifacts
- Router daemon
- Learning traces
```

---

## Configuration

### Environment Variables

```bash
# Paths
export REPO_ROOT="/path/to/brain"
export EXPERT_DIR="./experts/base"
export CHROMA_DIR="./data/chroma"
export SQLITE_DIR="./data/sqlite"

# Embeddings
export EMBEDDING_BACKEND="auto"
export EMBEDDING_MODEL_NAME="all-MiniLM-L6-v2"
export EMBEDDING_DIMENSIONS="384"

# Memory
export MEMORY_VECTOR_BACKEND="auto"
export MEMORY_RECALL_LIMIT="10"
export MEMORY_DECAY_DAYS="90"

# Experts
export EXPERT_MAX_LOADED="3"
export EXPERT_IDLE_TIMEOUT_SEC="30"

# Internet
export INTERNET_ENABLED="true"
export INTERNET_MAX_REQUESTS_PER_QUERY="5"
export INTERNET_CACHE_TTL_SECONDS="3600"

# Router
export ROUTER_BACKEND="auto"
export ROUTER_CONFIDENCE_THRESHOLD="0.7"

# gRPC
export GRPC_HOST="127.0.0.1"
export GRPC_PORT="50051"

# HTTP
export API_PORT="8080"

# Logging
export LOG_LEVEL="info"

# Control
export STRICT_RUNTIME="true"
```

### Configuration File (optional)

```yaml
# .brain-config.yaml
runtime:
  log_level: info
  strict: true
  max_citations: 4

memory:
  recall_limit: 10
  decay_days: 90
  backend: auto

experts:
  max_loaded: 3
  idle_timeout_sec: 30

router:
  backend: auto
  confidence_threshold: 0.7

learning:
  enabled: true
  min_signal_strength: 0.6
```

---

## Verification & Testing

### Lint & Type Check

```powershell
# Ruff linting
python -m ruff check brain tests/python scripts

# MyPy type checking
python -m mypy brain

# Compile check
python -m compileall brain tests/python scripts

# No placeholders
python scripts/guard_no_placeholders.py
```

### Unit Tests

```powershell
# Run all Python tests
python -m pytest tests/python -v

# Run specific module
python -m pytest tests/python/test_memory.py -v

# With coverage
python -m pytest tests/python --cov=brain --cov-report=html
```

### Integration Tests

```powershell
# TypeScript tests
pnpm test

# Build check
pnpm run build

# Rust tests
powershell -ExecutionPolicy Bypass -File scripts/test_rust.ps1
```

### Smoke Testing

```powershell
# Full smoke test
python scripts/prepare_runtime.py

# Quick health check
python -c "from brain import WaseemBrainRuntime; print(WaseemBrainRuntime().health())"

# Memory test
python -c "from brain.memory import MemoryGraph; mg = MemoryGraph(); print('Memory OK')"

# Expert load test
python -c "from brain.experts import ExpertRegistry; er = ExpertRegistry(); print(f'{len(er.all())} experts')"
```

---

## Deployment & Production

### Health Checks

```python
health = runtime.health()

# Process is considered ready when:
assert health["ready"] == True
assert health["status"] == "ok"
assert health["condition"] in ["ready", "strong"]
assert len(health["errors"]) == 0
```

### Monitoring

```python
# Key metrics to track
metrics = {
    "queries_per_minute": ...,
    "avg_response_time_ms": ...,
    "memory_nodes_count": ...,
    "experts_loaded": ...,
    "cache_hit_ratio": ...,
    "error_rate": ...,
}

# Memory usage
import psutil
process = psutil.Process()
memory_mb = process.memory_info().rss / 1024 / 1024

# Performance
from brain.helpers import PerformanceMonitor
perf = PerformanceMonitor("query_latency")
# ... record measurements ...
print(f"p95 latency: {perf.p95:.1f}ms")
```

### Logging

All logs use Python standard logging:

```python
from brain.helpers import get_logger

logger = get_logger(__name__)
logger.info("System initialized")
logger.warning("Memory approaching limit")
logger.error("Expert execution failed", exc_info=True)
```

---

## Troubleshooting

### Common Issues

**Issue: "Import brain failed"**
```bash
# Check Python version (need 3.11+)
python --version

# Reinstall dependencies
pip install -r requirements-runtime.txt --force-reinstall
```

**Issue: "Memory index not found"**
```bash
# Rebuild vector index
python scripts/prepare_runtime.py --skip-smoke-query
```

**Issue: "Router daemon unavailable"**
```bash
# Check daemon status
python scripts/manage_router_daemon.py status

# Restart daemon
python scripts/manage_router_daemon.py stop
python scripts/manage_router_daemon.py start
```

**Issue: "No experts available"**
```bash
# Check expert directory
ls experts/base/

# Validate manifests
python scripts/validate_codex_skills.py
```

---

## Summary

This complete documentation covers:

✓ All 6+ core modules with full function signatures  
✓ Complete processing pipeline with detailed stages  
✓ 65+ helper utility functions  
✓ Expert system creation and management  
✓ Memory storage and retrieval  
✓ Learning pipeline and training  
✓ All CLI commands and scripts  
✓ Configuration options  
✓ Testing and verification  
✓ Production deployment  

**System Status:** ✓ Production Ready  
**Last Updated:** April 5, 2026  
**Author:** Muhammad Waseem Akram
