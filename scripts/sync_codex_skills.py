from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CODEX_HOME = Path.home() / ".codex"
DEFAULT_SKILLS_ROOT = DEFAULT_CODEX_HOME / "skills"

SYSTEM_OVERVIEW = """# System Overview

WaseemBrain is an offline-first low-RAM chat and coding brain with five hard rules:

1. No dense local LLM on the critical path.
2. No internet on the critical path.
3. Intelligence comes from compact classifiers, rankers, memory, retrieval, planners, and deterministic synthesis.
4. Every answer must be grounded in user input, workspace evidence, stored memory, explicit rules, or uncertainty.
5. If a capability is not real yet, the runtime must say so instead of pretending.
"""

PROJECT_REFERENCE = """# Project Structure Notes

- `brain/`: Python runtime, dialogue state, memory, learning, reasoning modules, routing, and synthesis.
- `interface/`: Fastify HTTP and WebSocket serving layer.
- `router-daemon/`: optional Rust policy daemon while it provides measurable latency value.
- `experts/`: compact artifacts, manifests, and datasets used by the runtime.
- `scripts/`: training, syncing, validation, diagnostics, and quality gates.
"""

ANTI_PLACEHOLDER_POLICY = """# Anti-Placeholder Policy

- No stub, demo, fake, echo, placeholder, or dead runtime branches.
- No hidden dense-local-model or hidden-network shortcuts presented as built-in intelligence.
- No canned filler presented as reasoning.
- If a subsystem cannot produce a real answer, fail or limit explicitly.
- Remove dead compatibility paths instead of hiding them behind config toggles.
"""

RUNTIME_EXPECTATIONS = """# Runtime Expectations

- Target: CPU-only, low-RAM, Windows and Linux.
- Prefer compact classifiers, rankers, retrieval, and planners over dense local generative models.
- Runtime should remain useful offline after artifacts and datasets are prepared.
- Responses stored in memory must carry provenance; generated summaries are not trusted facts by default.
- Any new route, planner, or memory path must pass the placeholder guard before merge.
"""

BRAIN_PLAN = """# Brain Plan

- Goal: behave like a compact chat and coding brain without a dense local LLM.
- Core loop: normalize input -> infer dialogue state -> recall memory/workspace -> build a response plan -> run bounded reasoning modules -> synthesize a grounded reply -> log traces for offline learning.
- Capability focus: repo-aware coding help, project chat, explanation, planning, and memory-backed follow-ups.
- Learning: collect traces and optionally prepare permissive datasets offline to train compact classifiers, rerankers, and response selectors. Runtime stays offline once artifacts exist.
- Non-goals: hidden API calls, giant local-model inference, fake empathy, fake knowledge, or generic filler dressed up as intelligence.
"""


@dataclass(frozen=True)
class SkillSpec:
    name: str
    display_name: str
    short_description: str
    default_prompt: str
    description: str
    source_markdown: Path | None
    body: str


def _component_body(action: str) -> str:
    return (
        f"# {action}\n\n"
        "1. Read `references/anti-placeholder.md`, `references/runtime-expectations.md`, "
        "`references/system-overview.md`, `references/brain-plan.md`, "
        "`references/project-structure.md`, and `references/component-guide.md`.\n"
        "2. Keep the runtime honest: no dense local LLM on the critical path, no hidden network dependency, "
        "no fake reasoning, and no dead branches that pretend a capability exists.\n"
        "3. Finish with targeted tests plus `python scripts/guard_no_placeholders.py`.\n\n"
        "## References\n"
        "- `references/anti-placeholder.md`\n"
        "- `references/runtime-expectations.md`\n"
        "- `references/system-overview.md`\n"
        "- `references/brain-plan.md`\n"
        "- `references/project-structure.md`\n"
        "- `references/component-guide.md`\n"
    )


SOURCE_SKILLS = [
    SkillSpec(
        name="waseem-brain-build-orchestrator",
        display_name="LB Orchestrator",
        short_description="Drive repo work in algorithmic-brain order.",
        default_prompt="Use $waseem-brain-build-orchestrator to implement the next offline WaseemBrain subsystem without placeholders.",
        description="Coordinate repo-wide work for WaseemBrain's offline-first algorithmic brain plan. Use when Codex needs subsystem order, cross-cutting guardrails, or the repo-specific execution map for real runtime changes.",
        source_markdown=None,
        body="""# Drive The Repo

1. Read `references/anti-placeholder.md`, `references/runtime-expectations.md`, `references/system-overview.md`, `references/brain-plan.md`, `references/project-structure.md`, and `references/source-skills.md`.
2. Move in dependency order: contracts, normalization, dialogue state, memory, reasoning modules, learning pipeline, decision engine, interface, quality gates.
3. Keep every merge measurable by running subsystem tests, adding benchmarks when behavior changes, and running `python scripts/guard_no_placeholders.py`.

## References
- `references/anti-placeholder.md`
- `references/runtime-expectations.md`
- `references/system-overview.md`
- `references/brain-plan.md`
- `references/project-structure.md`
- `references/source-skills.md`
""",
    ),
    SkillSpec(
        name="waseem-brain-shared-types",
        display_name="LB Shared Types",
        short_description="Maintain dialogue and evidence contracts.",
        default_prompt="Use $waseem-brain-shared-types to update `brain/types.py` and related contracts.",
        description="Build or revise the shared WaseemBrain contracts. Use when Codex is working on IDs, response plans, dialogue state, evidence types, provenance, or cross-subsystem payload shapes in this repo.",
        source_markdown=ROOT / "skills" / "component-01-shared-types.md",
        body=_component_body("Maintain Shared Contracts"),
    ),
    SkillSpec(
        name="waseem-brain-input-normalizer",
        display_name="LB Input Normalizer",
        short_description="Normalize text, file, and voice input.",
        default_prompt="Use $waseem-brain-input-normalizer to update input adapters and normalized signal handling in this repo.",
        description="Implement or refine WaseemBrain input normalization. Use when Codex needs to convert text, documents, or voice input into the repo's canonical `NormalizedSignal` contract.",
        source_markdown=ROOT / "skills" / "component-02-input-normalizer.md",
        body=_component_body("Maintain Input Normalization"),
    ),
    SkillSpec(
        name="waseem-brain-dialogue-state",
        display_name="LB Dialogue",
        short_description="Maintain compact dialogue and tone state.",
        default_prompt="Use $waseem-brain-dialogue-state to work on dialogue-state inference and tone fusion in this repo.",
        description="Implement or refine the WaseemBrain dialogue-state layer. Use when Codex is updating tone, urgency, clarification signals, or compact session-state logic that influences planning and response behavior.",
        source_markdown=ROOT / "skills" / "component-03-dialogue-state.md",
        body=_component_body("Maintain Dialogue State"),
    ),
    SkillSpec(
        name="waseem-brain-memory-graph",
        display_name="LB Memory",
        short_description="Work on SQLite plus HNSW grounded memory.",
        default_prompt="Use $waseem-brain-memory-graph to update the hardened memory stack in this repo.",
        description="Implement or refine the WaseemBrain memory subsystem. Use when Codex is working on SQLite metadata, HNSW vector recall, session edges, workspace facts, provenance, or grounded memory ranking.",
        source_markdown=ROOT / "skills" / "component-04-memory-graph.md",
        body=_component_body("Maintain Memory Graph"),
    ),
    SkillSpec(
        name="waseem-brain-reasoning-modules",
        display_name="LB Reasoning",
        short_description="Maintain bounded reasoning modules.",
        default_prompt="Use $waseem-brain-reasoning-modules to work on planning, retrieval-backed reasoning, and synthesis in this repo.",
        description="Implement or refine the WaseemBrain reasoning layer. Use when Codex is working on bounded reasoning modules, workspace retrieval, patch planning, contradiction checks, or grounded response assembly.",
        source_markdown=ROOT / "skills" / "component-05-reasoning-modules.md",
        body=_component_body("Maintain Reasoning Modules"),
    ),
    SkillSpec(
        name="waseem-brain-learning-pipeline",
        display_name="LB Learning",
        short_description="Maintain offline learning artifacts.",
        default_prompt="Use $waseem-brain-learning-pipeline to work on offline training, feedback scoring, and artifact generation in this repo.",
        description="Implement or refine the WaseemBrain learning pipeline. Use when Codex is working on offline dataset preparation, feedback scoring, artifact training, trace collection, or reproducible export for compact runtime components.",
        source_markdown=ROOT / "skills" / "component-06-learning-pipeline.md",
        body=_component_body("Maintain Learning Pipeline"),
    ),
    SkillSpec(
        name="waseem-brain-decision-engine",
        display_name="LB Decision",
        short_description="Maintain fast intent and policy selection.",
        default_prompt="Use $waseem-brain-decision-engine to work on routing, policy artifacts, or the optional Rust daemon in this repo.",
        description="Implement or refine the WaseemBrain decision engine. Use when Codex is updating policy labels, routing artifacts, Rust inference, gRPC routing, or action-selection behavior.",
        source_markdown=ROOT / "skills" / "component-07-decision-engine.md",
        body=_component_body("Maintain Decision Engine"),
    ),
    SkillSpec(
        name="waseem-brain-interface-bridge",
        display_name="LB Interface",
        short_description="Maintain Fastify and Python bridge serving.",
        default_prompt="Use $waseem-brain-interface-bridge to update the Fastify surface or Python bridge for this repo.",
        description="Implement or refine the WaseemBrain serving surface. Use when Codex is working on Fastify routes, WebSocket streaming, concurrent Python bridge behavior, or multimodal request contracts for the offline brain.",
        source_markdown=ROOT / "skills" / "component-08-interface-bridge.md",
        body=_component_body("Maintain Interface And Bridge"),
    ),
    SkillSpec(
        name="waseem-brain-quality-gates",
        display_name="LB Quality Gates",
        short_description="Maintain CI, guards, and skill validation.",
        default_prompt="Use $waseem-brain-quality-gates to update quality gates, requirements splits, or skill validation in this repo.",
        description="Implement or refine the WaseemBrain quality gates. Use when Codex is working on dependency grouping, placeholder guards, skill sync/validation, offline-first rules, or anti-regression checks for this repo.",
        source_markdown=ROOT / "skills" / "component-09-quality-gates.md",
        body=_component_body("Maintain Quality Gates"),
    ),
]


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_skill_markdown(spec: SkillSpec) -> str:
    return f"---\nname: {spec.name}\ndescription: {spec.description}\n---\n\n{spec.body}"


def build_openai_yaml(spec: SkillSpec) -> str:
    return (
        "interface:\n"
        f'  display_name: "{spec.display_name}"\n'
        f'  short_description: "{spec.short_description}"\n'
        f'  default_prompt: "{spec.default_prompt}"\n'
        "policy:\n"
        "  allow_implicit_invocation: false\n"
    )


def sync_skill(spec: SkillSpec, output_root: Path) -> None:
    skill_dir = output_root / spec.name
    if skill_dir.exists():
        shutil.rmtree(skill_dir)
    write_text(skill_dir / "SKILL.md", build_skill_markdown(spec))
    write_text(skill_dir / "agents" / "openai.yaml", build_openai_yaml(spec))
    write_text(skill_dir / "references" / "anti-placeholder.md", ANTI_PLACEHOLDER_POLICY)
    write_text(skill_dir / "references" / "runtime-expectations.md", RUNTIME_EXPECTATIONS)
    write_text(skill_dir / "references" / "system-overview.md", SYSTEM_OVERVIEW)
    write_text(skill_dir / "references" / "brain-plan.md", BRAIN_PLAN)
    write_text(skill_dir / "references" / "project-structure.md", PROJECT_REFERENCE)
    if spec.source_markdown is None:
        source_index = "\n".join(
            f"- `{item.source_markdown.name}`"
            for item in SOURCE_SKILLS
            if item.source_markdown is not None
        )
        write_text(
            skill_dir / "references" / "source-skills.md",
            f"# Source Skills\n\n{source_index}\n",
        )
    else:
        write_text(
            skill_dir / "references" / "component-guide.md",
            spec.source_markdown.read_text(encoding="utf-8"),
        )


def sync_all_skills(output_root: Path) -> int:
    output_root.mkdir(parents=True, exist_ok=True)
    for spec in SOURCE_SKILLS:
        sync_skill(spec, output_root)
    return len(SOURCE_SKILLS)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync repo markdown skills into Codex skill folders."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_SKILLS_ROOT)
    args = parser.parse_args()
    count = sync_all_skills(args.output_root)
    print(f"Synced {count} skills into {args.output_root}")


if __name__ == "__main__":
    main()
