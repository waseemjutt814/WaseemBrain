# 01 - Design Principles

This repo started from an architecture idea, but the current codebase is shaped more by practical constraints than by theory alone. These principles explain why the implementation looks the way it does.

## 1. CPU-First And Local By Default

The runtime is built to work on ordinary Windows and Linux machines without assuming a GPU. That is why the critical path is centered on:

- compact routing artifacts
- persistent local memory
- small grounded experts
- optional, not mandatory, live internet access

## 2. Evidence Before Fluency

The system should not answer as if it "just knows." The preferred order is:

1. normalize the request
2. inspect memory and available evidence
3. route to the narrowest useful expert
4. assemble a grounded response

This is why the code invests heavily in memory, traces, and citations instead of a large free-form generator.

## 3. Modality Contracts Must Be Explicit

Input paths should behave according to the route or CLI flag the user chose. Current normalization logic treats the explicit modality hint as authoritative because hidden content sniffing caused incorrect behavior in earlier versions.

## 4. Memory Must Be Useful, Not Just Persistent

Persistent storage alone is not enough. The memory layer is designed around:

- recall quality
- provenance
- session continuity
- controlled decay
- relevance gating before reuse

That is why the live memory path combines SQLite text lookup, vector search, neighbor expansion, and scoring.

## 5. Honest Degradation Beats Fake Success

When a capability is unavailable, the runtime should report that truthfully instead of fabricating readiness. This principle already shapes parts of the repo:

- response-policy training is skipped until real traces exist
- voice warmup is skipped when disk space is too low
- placeholder guard scripts fail the build if fake logic returns

The remaining health-reporting gap is tracked in `PLAN.md`.

## 6. Offline Learning Must Stay Bounded

The project does support learning, but only through explicit offline artifacts:

- traces
- ranking features
- response-policy training
- expert correction jobs

There is no claim that the system self-improves magically during live inference.

## 7. Keep Interfaces Thin

The TypeScript layer should stay focused on transport, validation, and streaming. The Python runtime should hold decision logic. The Rust daemon should stay narrow and fast. This separation keeps debugging manageable.

## 8. No Fake Work

The repo should never drift into:

- placeholder experts
- dead code paths that pretend to be real
- made-up training outputs
- docs that describe architecture the code no longer matches

That last point is why the documentation set was refactored alongside the current implementation.
