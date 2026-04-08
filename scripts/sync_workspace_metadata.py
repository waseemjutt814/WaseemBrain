from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "package.json"
PYPROJECT_PATH = ROOT / "pyproject.toml"


def _read_package() -> dict[str, Any]:
    return json.loads(PACKAGE_PATH.read_text(encoding="utf-8-sig"))


def _read_pyproject() -> dict[str, Any]:
    return tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))


def _license_value(package: dict[str, Any], project: dict[str, Any]) -> str:
    license_info = project.get("license")
    if isinstance(license_info, dict):
        text = license_info.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        file_name = license_info.get("file")
        if isinstance(file_name, str) and file_name.strip():
            return f"SEE LICENSE IN {file_name.strip()}"
    if isinstance(license_info, str) and license_info.strip():
        return license_info.strip()
    existing = package.get("license")
    return str(existing) if existing else "SEE LICENSE IN LICENSE.md"


def _build_project_metadata(optional_dependencies: dict[str, list[str]]) -> dict[str, Any]:
    return {
        "runtimeContract": {
            "offlineFirst": True,
            "modelFreeCore": True,
            "apiKeysRequired": False,
            "defaultRouterBackend": "local",
            "selfImprovementScope": "knowledge-only",
            "optionalAccelerators": [
                "router-daemon",
                "grpc router client",
                "native hnswlib backend",
            ],
        },
        "manifests": {
            "node": "package.json",
            "python": "pyproject.toml",
            "project": "waseem.manifest.json",
            "environment": ".env.example",
        },
        "directories": {
            "runtime": "brain",
            "interface": "interface",
            "experts": "experts",
            "routerRust": "router-daemon",
            "routerPython": "router_daemon",
            "scripts": "scripts",
            "testsPython": "tests/python",
            "testsTypescript": "tests/typescript",
            "docs": "docs",
            "data": "data",
            "logs": "logs",
        },
        "reports": {
            "projectJson": "logs/project_report.json",
            "projectMarkdown": "logs/project_report.md",
            "knowledgeEvolution": "logs/knowledge_evolution_report.json",
        },
        "dependencySources": {
            "node": "package.json dependencies/devDependencies",
            "python": "pyproject.toml project.optional-dependencies",
            "mirroredPythonGroups": list(optional_dependencies.keys()),
        },
        "lockfiles": {
            "npm": "package-lock.json",
            "pnpm": "pnpm-lock.yaml",
            "cargo": "Cargo.lock",
        },
        "documentation": {
            "rootReadme": "README.md",
            "canonicalDocs": [
                "docs/README.md",
                "docs/INDUSTRIAL_REBUILD_PLAN.md",
                "docs/architecture.md",
                "docs/api.md",
                "docs/build.md",
                "docs/components.md",
                "docs/testing.md",
                "docs/CAPABILITY_MATRIX.md",
            ],
        },
    }


def _build_command_metadata() -> dict[str, dict[str, str]]:
    return {
        "build": {
            "category": "build",
            "description": "Build the app dist and copy the required static assets.",
        },
        "build:ts": {
            "category": "build",
            "description": "Compile the app-only TypeScript sources into dist.",
        },
        "build:python": {
            "category": "build",
            "description": "Build the Python wheel into dist/python.",
        },
        "build:rust": {
            "category": "build",
            "description": "Build the optional Rust router accelerator.",
        },
        "setup:python": {
            "category": "setup",
            "description": "Install the maintained runtime and development Python extras.",
        },
        "setup:python:full": {
            "category": "setup",
            "description": "Install runtime, development, and training Python extras.",
        },
        "sync:metadata": {
            "category": "metadata",
            "description": "Mirror pyproject metadata and dependency groups into package.json.",
        },
        "report:inventory": {
            "category": "reporting",
            "description": "Write a file and dependency inventory without running verification commands.",
        },
        "report:project": {
            "category": "reporting",
            "description": "Generate inventory, verification summaries, assistant-surface readiness, and Docker smoke status.",
        },
        "verify:project": {
            "category": "verification",
            "description": "Sync metadata, then generate the full project report artifacts and Docker smoke status.",
        },
        "docker:smoke": {
            "category": "verification",
            "description": "Run the industrial Docker smoke verification for compose boot, assistant reachability, and restart persistence.",
        },
        "lint": {
            "category": "verification",
            "description": "Run the maintained-core Python lint and type gate.",
        },
        "typecheck:ts": {
            "category": "verification",
            "description": "Typecheck the interface and TypeScript tests without emitting dist files.",
        },
        "test:python": {
            "category": "verification",
            "description": "Run the Python runtime and integration test suite.",
        },
        "test:ts": {
            "category": "verification",
            "description": "Typecheck and run the TypeScript interface test suite.",
        },
        "test:all": {
            "category": "verification",
            "description": "Run the TypeScript and Python baseline verification suites.",
        },
        "test:coverage": {
            "category": "verification",
            "description": "Run Python tests with coverage output.",
        },
        "runtime:start": {
            "category": "runtime",
            "description": "Start the detached Python runtime daemon.",
        },
        "runtime:stop": {
            "category": "runtime",
            "description": "Stop the detached Python runtime daemon.",
        },
        "runtime:status": {
            "category": "runtime",
            "description": "Show the detached Python runtime daemon status.",
        },
        "chat": {
            "category": "runtime",
            "description": "Start the terminal chat against the hot runtime daemon.",
        },
        "start:python": {
            "category": "runtime",
            "description": "Start the Python runtime module directly.",
        },
        "dev": {
            "category": "runtime",
            "description": "Open the interactive dev launcher for interface, terminal, and backend.",
        },
        "dev:interface": {
            "category": "runtime",
            "description": "Start the browser interface and auto-start the backend daemon.",
        },
        "dev:terminal": {
            "category": "runtime",
            "description": "Start the terminal chat and auto-start the backend daemon.",
        },
        "dev:both": {
            "category": "runtime",
            "description": "Start the browser interface and terminal chat on the same hot backend.",
        },
        "dev:backend": {
            "category": "runtime",
            "description": "Start the backend daemon only and leave the UI selection for later.",
        },
    }


def main() -> None:
    package = _read_package()
    pyproject = _read_pyproject()
    project = pyproject.get("project", {})
    optional_dependencies = {
        key: list(value)
        for key, value in project.get("optional-dependencies", {}).items()
        if isinstance(value, list)
    }

    authors = project.get("authors", [])
    author_name = package.get("author", "")
    if authors and isinstance(authors, list) and isinstance(authors[0], dict):
        author_name = str(authors[0].get("name", author_name))

    package["name"] = str(project.get("name", package.get("name", "waseem-brain")))
    package["version"] = str(project.get("version", package.get("version", "0.1.0")))
    package["description"] = str(project.get("description", package.get("description", "")))
    package["author"] = author_name
    package["license"] = _license_value(package, project)
    package["engines"] = {
        "node": str(package.get("engines", {}).get("node", ">=20")),
        "python": str(
            project.get(
                "requires-python",
                package.get("engines", {}).get("python", ">=3.11"),
            )
        ),
    }
    package["pythonDependencyGroups"] = optional_dependencies
    package["projectMetadata"] = _build_project_metadata(optional_dependencies)
    package["commandMetadata"] = _build_command_metadata()

    PACKAGE_PATH.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    print("Synchronized package.json metadata from pyproject.toml")


if __name__ == "__main__":
    main()