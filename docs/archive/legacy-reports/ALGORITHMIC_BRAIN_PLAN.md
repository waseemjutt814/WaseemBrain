# WaseemBrain Algorithmic Brain Plan

This file describes the longer-range direction for the project. It is not a promise that every item already exists. It is the target shape the current runtime is moving toward.

## Product Direction

Build WaseemBrain into an offline-first chat and coding system that stays useful without depending on a dense local LLM or request-time internet access.

The system should be strongest at:

- repo-aware coding help
- memory-backed follow-up handling
- grounded factual answers
- task planning and decomposition
- concise, honest, inspectable responses

## Non-Negotiable Rules

- No fake runtime branches, dummy artifacts, or placeholder experts.
- No hidden dense model on the critical path.
- No pretending the system saw evidence it did not inspect.
- No fabricated learning claims.
- Every answer path should remain explainable from rules, memory, evidence, or explicit uncertainty.

## Current Foundation

The repo already has the base pieces for this direction:

- normalized multimodal input
- dialogue planning
- memory recall with provenance
- hybrid routing
- manifest-driven experts
- optional internet retrieval
- offline response-policy training from traces

## Strategic Algorithm

### 1. Normalize Input Once

Every request should become a compact `NormalizedSignal` with text, modality, metadata, session identity, and any extracted file or voice context.

### 2. Build Dialogue State

The system should infer a bounded, inspectable state:

- intent
- preferred answer style
- clarification need
- workspace relevance
- memory relevance
- confidence

### 3. Recall Evidence Before Answering

Memory recall and workspace evidence should be treated as first-class inputs. Cached or recalled content is evidence only when it survives relevance and provenance checks.

### 4. Use Small Decision Artifacts

Routing, clarification behavior, and response selection should come from compact artifacts and rules:

- router artifact
- dialogue planner
- response policy
- ranking features

### 5. Keep Experts Narrow And Grounded

Experts should keep doing one measurable job well:

- grounded language synthesis
- repo-aware code evidence
- offline datasets such as geography

Future experts should follow the same constraint.

### 6. Learn Offline From Real Traces

Learning should stay outside the critical path:

- collect traces
- score outcomes
- label failures
- train compact artifacts
- export new artifacts
- rerun benchmarks and honesty checks

## Implementation Phases

### Phase 1: Strong Runtime Honesty

- tighten health reporting
- keep docs and config aligned with the real runtime
- preserve no-placeholder guardrails

### Phase 2: Better Evidence Retrieval

- improve workspace retrieval and symbol anchoring
- keep memory provenance explicit
- strengthen follow-up resolution

### Phase 3: Better Response Selection

- train response-policy artifacts on real traces
- improve mode and strategy ranking
- expand contradiction checks before output

### Phase 4: Better Coding Help

- strengthen repo evidence gathering
- improve file and snippet selection
- make coding answers cite actual workspace evidence more consistently

### Phase 5: Offline Learning Pipeline

- formalize trace collection
- curate permissive datasets only when they justify a concrete artifact
- automate retraining for small measurable components

## Success Criteria

- useful offline after preparation
- low idle RAM and bounded cold-start behavior
- reliable CLI and HTTP chat for grounded tasks
- strong repo-aware help backed by inspected files
- clear limits instead of generic hallucinated filler

## Honest Limits

Without a dense generative model, WaseemBrain will not match frontier LLMs on unconstrained creativity or open-world knowledge.

That trade-off is intentional. The project is optimizing for:

- local execution
- inspectability
- stable follow-up behavior
- evidence-based responses
- honest capability boundaries
