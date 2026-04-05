from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sync_codex_skills import SOURCE_SKILLS

REQUIRED_AGENT_FIELDS = (
    "interface:",
    "display_name:",
    "short_description:",
    "default_prompt:",
    "policy:",
    "allow_implicit_invocation: false",
)

COMMON_REFERENCES = (
    "anti-placeholder.md",
    "runtime-expectations.md",
    "system-overview.md",
    "brain-plan.md",
    "project-structure.md",
)

REQUIRED_SKILL_MARKERS = (
    "references/anti-placeholder.md",
    "references/runtime-expectations.md",
    "references/brain-plan.md",
    "python scripts/guard_no_placeholders.py",
)


def parse_frontmatter(path: Path) -> tuple[dict[str, str], list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    errors: list[str] = []
    if not lines or lines[0] != "---":
        return {}, [f"{path}: missing opening frontmatter delimiter"]
    try:
        closing_index = lines.index("---", 1)
    except ValueError:
        return {}, [f"{path}: missing closing frontmatter delimiter"]

    entries: dict[str, str] = {}
    for line in lines[1:closing_index]:
        if ": " not in line:
            errors.append(f"{path}: invalid frontmatter line {line!r}")
            continue
        key, value = line.split(": ", 1)
        entries[key.strip()] = value.strip()
    return entries, errors


def validate_skill_dir(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    spec_names = {spec.name for spec in SOURCE_SKILLS}
    if skill_dir.name not in spec_names:
        errors.append(f"{skill_dir}: unknown skill directory")
        return errors

    skill_md = skill_dir / "SKILL.md"
    openai_yaml = skill_dir / "agents" / "openai.yaml"
    references_dir = skill_dir / "references"

    if not skill_md.exists():
        return [f"{skill_dir}: missing SKILL.md"]
    if not openai_yaml.exists():
        errors.append(f"{skill_dir}: missing agents/openai.yaml")
    if not references_dir.exists():
        errors.append(f"{skill_dir}: missing references directory")

    frontmatter, frontmatter_errors = parse_frontmatter(skill_md)
    errors.extend(frontmatter_errors)
    if frontmatter.get("name") != skill_dir.name:
        errors.append(f"{skill_md}: name does not match directory")
    if not frontmatter.get("description"):
        errors.append(f"{skill_md}: description is required")

    skill_text = skill_md.read_text(encoding="utf-8")
    for marker in REQUIRED_SKILL_MARKERS:
        if marker not in skill_text:
            errors.append(f"{skill_md}: missing required marker {marker!r}")

    if openai_yaml.exists():
        yaml_text = openai_yaml.read_text(encoding="utf-8")
        for field in REQUIRED_AGENT_FIELDS:
            if field not in yaml_text:
                errors.append(f"{openai_yaml}: missing required field {field!r}")

    for reference_name in COMMON_REFERENCES:
        reference_path = references_dir / reference_name
        if not reference_path.exists():
            errors.append(f"{reference_path}: required reference is missing")

    if skill_dir.name == "lattice-brain-build-orchestrator":
        if not (references_dir / "source-skills.md").exists():
            errors.append(f"{references_dir / 'source-skills.md'}: missing orchestrator index")
        if (references_dir / "component-guide.md").exists():
            errors.append(
                f"{references_dir / 'component-guide.md'}: orchestrator should not bundle a component guide"
            )
    else:
        if not (references_dir / "component-guide.md").exists():
            errors.append(f"{references_dir / 'component-guide.md'}: missing component reference")
        if (references_dir / "source-skills.md").exists():
            errors.append(
                f"{references_dir / 'source-skills.md'}: component skills should not bundle the source index"
            )

    return errors


def validate_skills_root(skills_root: Path) -> list[str]:
    errors: list[str] = []
    expected = {spec.name for spec in SOURCE_SKILLS}
    actual = {path.name for path in skills_root.iterdir() if path.is_dir()}

    missing = sorted(expected - actual)
    for name in missing:
        errors.append(f"{skills_root}: missing generated skill {name}")

    for skill_dir in sorted(
        path for path in skills_root.iterdir() if path.is_dir() and path.name in expected
    ):
        errors.extend(validate_skill_dir(skill_dir))
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate generated Codex skill folders.")
    parser.add_argument("skills_root", type=Path)
    args = parser.parse_args()

    errors = validate_skills_root(args.skills_root)
    if errors:
        print("Skill validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"Validated {len(SOURCE_SKILLS)} skills in {args.skills_root}")


if __name__ == "__main__":
    main()
