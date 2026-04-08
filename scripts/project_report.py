from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.docker_smoke import run_docker_smoke
from scripts.guard_no_placeholders import ASSISTANT_REQUIRED_SNIPPETS
LOG_DIR = ROOT / 'logs'
JSON_REPORT_PATH = LOG_DIR / 'project_report.json'
MARKDOWN_REPORT_PATH = LOG_DIR / 'project_report.md'
EXCLUDED_DIRS = {
    '.git',
    '.mypy_cache',
    '.pytest_cache',
    '.ruff_cache',
    '.tmp_test',
    '__pycache__',
    'dist',
    'node_modules',
    'target',
    'tmp',
    'waseem_brain.egg-info',
}
COMMANDS = [
    ('build', ['npm', 'run', 'build'], 240),
    ('lint', ['npm', 'run', 'lint'], 240),
    ('guard:placeholders', ['npm', 'run', 'guard:placeholders'], 240),
    ('test:ts', ['npm', 'run', 'test:ts'], 240),
    ('test:python', ['npm', 'run', 'test:python'], 240),
]


def _iter_repo_files() -> list[Path]:
    files: list[Path] = []
    for current_root, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in EXCLUDED_DIRS and not dirname.startswith('.tmp_test')
        ]
        current_path = Path(current_root)
        for filename in filenames:
            path = current_path / filename
            if any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts[:-1]):
                continue
            files.append(path)
    return files


def _top_level_name(path: Path) -> str:
    relative = path.relative_to(ROOT)
    return relative.parts[0] if len(relative.parts) > 1 else '(root)'


def _collect_inventory() -> dict[str, Any]:
    files = _iter_repo_files()
    top_level_counts: Counter[str] = Counter()
    extension_counts: Counter[str] = Counter()
    python_function_count = 0
    python_async_function_count = 0
    python_class_count = 0
    python_parse_failures: list[str] = []

    for path in files:
        top_level_counts[_top_level_name(path)] += 1
        extension = path.suffix.lower() if path.suffix else '<no-extension>'
        extension_counts[extension] += 1
        if path.suffix.lower() != '.py':
            continue
        try:
            tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:
            python_parse_failures.append(f'{path.relative_to(ROOT)}: {exc}')
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                python_async_function_count += 1
            elif isinstance(node, ast.FunctionDef):
                python_function_count += 1
            elif isinstance(node, ast.ClassDef):
                python_class_count += 1

    python_test_files = sorted(
        str(path.relative_to(ROOT))
        for path in (ROOT / 'tests' / 'python').glob('test*.py')
        if path.is_file()
    )
    typescript_test_files = sorted(
        str(path.relative_to(ROOT))
        for path in (ROOT / 'tests' / 'typescript').glob('*.test.ts')
        if path.is_file()
    )

    package_data = json.loads((ROOT / 'package.json').read_text(encoding='utf-8-sig'))
    python_groups = package_data.get('pythonDependencyGroups', {})

    return {
        'total_files': len(files),
        'files_by_top_level': dict(sorted(top_level_counts.items())),
        'files_by_extension': dict(
            sorted(extension_counts.items(), key=lambda item: (-item[1], item[0]))[:25]
        ),
        'python_symbol_inventory': {
            'files': sum(1 for path in files if path.suffix.lower() == '.py'),
            'functions': python_function_count,
            'async_functions': python_async_function_count,
            'classes': python_class_count,
            'parse_failures': python_parse_failures[:20],
        },
        'tests': {
            'python_files': len(python_test_files),
            'typescript_files': len(typescript_test_files),
            'python_file_list': python_test_files,
            'typescript_file_list': typescript_test_files,
        },
        'dependency_inventory': {
            'node_runtime': len(package_data.get('dependencies', {})),
            'node_dev': len(package_data.get('devDependencies', {})),
            'python_groups': {key: len(value) for key, value in python_groups.items()},
        },
        'npm_scripts': sorted(package_data.get('scripts', {}).keys()),
    }


def _normalize_command(command: list[str]) -> list[str]:
    if os.name == 'nt' and command and command[0].lower() == 'npm':
        return ['cmd', '/d', '/c', *command]
    return command


def _run_capture(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            _normalize_command(command),
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=False,
        )
    except OSError as exc:
        return f'unavailable ({exc})'
    output = (completed.stdout or '') + (completed.stderr or '')
    return output.strip()


def _environment_snapshot() -> dict[str, str]:
    return {
        'python': _run_capture([sys.executable, '--version']) or 'unknown',
        'node': _run_capture(['node', '--version']) or 'unknown',
        'npm': _run_capture(['npm', '--version']) or 'unknown',
    }


def _parse_test_stats(name: str, output: str) -> dict[str, int]:
    stats = {'passed': 0, 'failed': 0, 'warnings': 0}
    if name == 'test:ts':
        pass_match = re.search(r'\bpass\s+(\d+)\b', output)
        fail_match = re.search(r'\bfail\s+(\d+)\b', output)
        if pass_match:
            stats['passed'] = int(pass_match.group(1))
        if fail_match:
            stats['failed'] = int(fail_match.group(1))
        return stats

    if name == 'test:python':
        pass_match = re.search(r'(\d+) passed', output)
        fail_match = re.search(r'(\d+) failed', output)
        warning_match = re.search(r'(\d+) warnings?', output)
        if pass_match:
            stats['passed'] = int(pass_match.group(1))
        if fail_match:
            stats['failed'] = int(fail_match.group(1))
        if warning_match:
            stats['warnings'] = int(warning_match.group(1))
        return stats

    return stats


def _run_command(name: str, command: list[str], timeout_sec: int) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            _normalize_command(command),
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout_sec,
            check=False,
        )
        output = ((completed.stdout or '') + (completed.stderr or '')).strip()
        exit_code = completed.returncode
        status = 'pass' if exit_code == 0 else 'fail'
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or '') + (exc.stderr or '')).strip()
        exit_code = -1
        status = 'fail'
        output = (output + f'\nTimed out after {timeout_sec} seconds').strip()
    except OSError as exc:
        output = str(exc)
        exit_code = -1
        status = 'fail'

    duration = round(time.perf_counter() - started, 3)
    stats = _parse_test_stats(name, output)
    return {
        'name': name,
        'command': ' '.join(command),
        'status': status,
        'exit_code': exit_code,
        'duration_sec': duration,
        'passed': stats['passed'],
        'failed': stats['failed'],
        'warnings': stats['warnings'],
        'output_tail': '\n'.join(output.splitlines()[-25:]),
    }


def _runtime_health_snapshot() -> dict[str, Any]:
    try:
        sys.path.insert(0, str(ROOT))
        from brain.runtime import WaseemBrainRuntime  # noqa: PLC0415

        runtime = WaseemBrainRuntime()
        try:
            health = runtime.health()
        finally:
            runtime.close()
        return {
            'status': 'ok',
            'condition': health.get('condition'),
            'ready': health.get('ready'),
            'router_backend': health.get('router_backend'),
            'vector_backend': health.get('vector_backend'),
            'experts_available': health.get('experts_available'),
            'components': health.get('components'),
            'capabilities': health.get('capabilities'),
        }
    except Exception as exc:  # pragma: no cover
        return {'status': 'error', 'message': str(exc)}


def _assistant_surface_file_status(relative_path: str) -> dict[str, Any]:
    path = ROOT / relative_path
    snippets = ASSISTANT_REQUIRED_SNIPPETS.get(relative_path, ())
    if not path.exists():
        return {
            'status': 'missing',
            'path': relative_path,
            'missing_snippets': list(snippets),
        }
    text = path.read_text(encoding='utf-8')
    missing = [snippet for snippet in snippets if snippet not in text]
    return {
        'status': 'ready' if not missing else 'incomplete',
        'path': relative_path,
        'missing_snippets': missing,
    }


def _assistant_surface_snapshot() -> dict[str, Any]:
    from scripts.runtime_client import DEFAULT_HOST, DEFAULT_PORT, is_runtime_daemon_running, load_runtime_daemon_state

    daemon_state = load_runtime_daemon_state() or {}
    host = str(daemon_state.get('host', DEFAULT_HOST))
    raw_port = daemon_state.get('port', DEFAULT_PORT)
    try:
        port = int(raw_port)
    except (TypeError, ValueError):
        port = DEFAULT_PORT
    compose_text = (ROOT / 'docker-compose.yml').read_text(encoding='utf-8') if (ROOT / 'docker-compose.yml').exists() else ''
    return {
        'primary_contract': '/ws/assistant',
        'web_console': _assistant_surface_file_status('interface/public/chat.html'),
        'browser_shell': _assistant_surface_file_status('interface/src/web/app.ts'),
        'assistant_ws_bridge': _assistant_surface_file_status('interface/src/ws/assistant.ts'),
        'catalog_route': _assistant_surface_file_status('interface/src/routes/catalog.ts'),
        'actions_route': _assistant_surface_file_status('interface/src/routes/actions.ts'),
        'terminal_console': {
            'status': 'ready'
            if (ROOT / 'scripts' / 'chat_cli.py').exists() and (ROOT / 'scripts' / 'launch_terminal.mjs').exists()
            else 'missing',
            'entrypoint': 'pnpm run chat',
            'autostart': (ROOT / 'scripts' / 'launch_terminal.mjs').exists(),
        },
        'discovery_routes': {
            'status': 'ready',
            'paths': ['/health', '/api/catalog', '/api/actions'],
        },
        'runtime_daemon': {
            'status': 'running' if is_runtime_daemon_running() else 'stopped',
            'host': host,
            'port': port,
        },
        'docker_compose': {
            'status': 'ready' if compose_text else 'missing',
            'path': 'docker-compose.yml',
            'interface_public_port': '8080:8080' in compose_text or '${INTERFACE_PORT:-8080}:8080' in compose_text,
            'runtime_internal_only': '55881:55881' not in compose_text,
            'persistent_data_mount': './data:/app/data' in compose_text or 'brain-data:' in compose_text,
            'persistent_logs_mount': './logs:/app/logs' in compose_text or 'brain-logs:' in compose_text,
            'persistent_tmp_mount': './tmp:/app/tmp' in compose_text or 'brain-tmp:' in compose_text,
        },
    }


def _build_markdown(report: dict[str, Any]) -> str:
    inventory = report['inventory']
    verification = report['verification']
    assistant_surfaces = report['assistant_surfaces']
    docker_smoke = report['docker_smoke']
    lines = [
        '# Waseem Brain Project Report',
        '',
        f"Generated: {report['generated_at']}",
        '',
        '## Summary',
        f"- Overall status: `{verification['overall_status']}`",
        f"- Files counted: `{inventory['total_files']}`",
        f"- Python test files: `{inventory['tests']['python_files']}`",
        f"- TypeScript test files: `{inventory['tests']['typescript_files']}`",
        f"- Python functions: `{inventory['python_symbol_inventory']['functions']}`",
        f"- Python async functions: `{inventory['python_symbol_inventory']['async_functions']}`",
        f"- Python classes: `{inventory['python_symbol_inventory']['classes']}`",
        f"- Primary assistant contract: `{assistant_surfaces['primary_contract']}`",
        f"- Docker smoke: `{docker_smoke['status']}`",
        '',
        '## Environment',
    ]
    for key, value in report['environment'].items():
        lines.append(f'- {key}: `{value}`')

    lines.extend([
        '',
        '## Verification Commands',
        '| Command | Status | Passed | Failed | Warnings | Duration (s) |',
        '| --- | --- | ---: | ---: | ---: | ---: |',
    ])
    for item in verification['commands']:
        lines.append(
            f"| `{item['name']}` | `{item['status']}` | {item['passed']} | {item['failed']} | {item['warnings']} | {item['duration_sec']} |"
        )

    lines.extend([
        '',
        '## Assistant Surfaces',
        f"- Web console: `{assistant_surfaces['web_console']['status']}` ({assistant_surfaces['web_console']['path']})",
        f"- Browser shell: `{assistant_surfaces['browser_shell']['status']}` ({assistant_surfaces['browser_shell']['path']})",
        f"- Assistant websocket bridge: `{assistant_surfaces['assistant_ws_bridge']['status']}` ({assistant_surfaces['assistant_ws_bridge']['path']})",
        f"- Terminal console: `{assistant_surfaces['terminal_console']['status']}` via `{assistant_surfaces['terminal_console']['entrypoint']}`",
        f"- Runtime daemon: `{assistant_surfaces['runtime_daemon']['status']}` on `{assistant_surfaces['runtime_daemon']['host']}:{assistant_surfaces['runtime_daemon']['port']}`",
        '',
        '## Docker Smoke',
        f"- Status: `{docker_smoke['status']}`",
        f"- Reason: {docker_smoke.get('reason', 'n/a')}",
    ])
    if docker_smoke.get('interface_url'):
        lines.append(f"- Interface URL: `{docker_smoke['interface_url']}`")
    if docker_smoke.get('audit_lines_after_restart') is not None:
        lines.append(
            f"- Audit lines after restart: `{docker_smoke['audit_lines_after_restart']}`"
        )

    lines.extend([
        '',
        '## File Inventory By Top-Level Directory',
        '| Directory | Files |',
        '| --- | ---: |',
    ])
    for name, count in inventory['files_by_top_level'].items():
        lines.append(f'| `{name}` | {count} |')

    lines.extend([
        '',
        '## File Inventory By Extension',
        '| Extension | Files |',
        '| --- | ---: |',
    ])
    for name, count in inventory['files_by_extension'].items():
        lines.append(f'| `{name}` | {count} |')

    lines.extend([
        '',
        '## Runtime Health Snapshot',
        '```json',
        json.dumps(report['runtime_health'], indent=2),
        '```',
        '',
        '## Generated Artifacts',
        f"- JSON report: `{JSON_REPORT_PATH.relative_to(ROOT)}`",
        f"- Markdown report: `{MARKDOWN_REPORT_PATH.relative_to(ROOT)}`",
    ])
    return '\n'.join(lines) + '\n'


def build_report(run_commands: bool) -> dict[str, Any]:
    inventory = _collect_inventory()
    verification_commands: list[dict[str, Any]] = []
    if run_commands:
        for name, command, timeout_sec in COMMANDS:
            verification_commands.append(_run_command(name, command, timeout_sec))

    docker_smoke = (
        run_docker_smoke(require_docker=False)
        if run_commands
        else {'status': 'skipped', 'reason': 'docker smoke not run in inventory-only mode'}
    )

    overall_status = 'pass'
    if any(item['status'] != 'pass' for item in verification_commands):
        overall_status = 'fail'
    if docker_smoke.get('status') == 'fail':
        overall_status = 'fail'
    if not verification_commands:
        overall_status = 'not-run'

    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'root': str(ROOT),
        'environment': _environment_snapshot(),
        'inventory': inventory,
        'verification': {
            'overall_status': overall_status,
            'commands': verification_commands,
            'commands_passed': sum(1 for item in verification_commands if item['status'] == 'pass'),
            'commands_failed': sum(1 for item in verification_commands if item['status'] == 'fail'),
        },
        'assistant_surfaces': _assistant_surface_snapshot(),
        'docker_smoke': docker_smoke,
        'runtime_health': _runtime_health_snapshot(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Generate a professional project inventory and verification report'
    )
    parser.add_argument(
        '--inventory-only',
        action='store_true',
        help='Collect file and dependency inventory without running build, lint, tests, and Docker smoke verification.',
    )
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report(run_commands=not args.inventory_only)
    JSON_REPORT_PATH.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    MARKDOWN_REPORT_PATH.write_text(_build_markdown(report), encoding='utf-8')

    print(f'Project report written to {JSON_REPORT_PATH}')
    print(f'Markdown summary written to {MARKDOWN_REPORT_PATH}')
    print(f"Files counted: {report['inventory']['total_files']}")
    print(
        'Verification status: '
        f"{report['verification']['overall_status']} "
        f"({report['verification']['commands_passed']} passed / "
        f"{report['verification']['commands_failed']} failed)"
    )
    print(f"Assistant surface contract: {report['assistant_surfaces']['primary_contract']}")
    print(f"Docker smoke status: {report['docker_smoke']['status']}")


if __name__ == '__main__':
    main()