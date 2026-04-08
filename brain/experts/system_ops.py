from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, List, Literal, Optional, TypedDict

from loguru import logger


_EXCLUDED_REPO_DIRS = {
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


class FirewallRule(TypedDict):
    name: str
    direction: str
    action: str
    protocol: str
    local_port: Optional[str]


class CommandResult(TypedDict):
    status: Literal['pass', 'fail']
    exit_code: int
    duration_sec: float
    command: str
    stdout: str
    stderr: str
    output_tail: str


class RuntimeDaemonStatus(TypedDict):
    running: bool
    host: str
    port: int
    pid: int
    log_path: str
    message: str


class SystemOperations:
    """Allowlisted system operations for Waseem Brain."""

    @staticmethod
    def get_firewall_rules(name_filter: Optional[str] = None) -> List[str]:
        if os.name != 'nt':
            return ['Windows firewall inspection is only available on Windows hosts.']
        cmd = ['netsh', 'advfirewall', 'firewall', 'show', 'rule', 'name=all']
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            lines = result.stdout.splitlines()
            if name_filter:
                return [line for line in lines if name_filter.lower() in line.lower()]
            return lines
        except Exception as exc:
            logger.error(f'Failed to fetch firewall rules: {exc}')
            return [f'Error: {exc}']

    @staticmethod
    def preview_firewall_rule(rule: FirewallRule) -> str:
        command = SystemOperations.build_firewall_rule_command(rule)
        return ' '.join(command)

    @staticmethod
    def build_firewall_rule_command(rule: FirewallRule) -> List[str]:
        command = [
            'netsh',
            'advfirewall',
            'firewall',
            'add',
            'rule',
            f"name={rule['name']}",
            f"dir={rule['direction']}",
            f"action={rule['action']}",
            f"protocol={rule['protocol']}",
        ]
        local_port = rule.get('local_port')
        if local_port:
            command.append(f'localport={local_port}')
        return command

    @staticmethod
    def add_firewall_rule(rule: FirewallRule) -> str:
        if os.name != 'nt':
            return 'Firewall rule execution is only supported on Windows hosts.'
        command = SystemOperations.build_firewall_rule_command(rule)
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            return f"Successfully added firewall rule: {rule['name']}"
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else str(exc)
            return f'Failed to add firewall rule: {stderr}'

    @staticmethod
    def repo_summary(repo_root: Path) -> dict[str, Any]:
        repo_root = repo_root.resolve()
        top_level_counts: Counter[str] = Counter()
        total_files = 0
        for current_root, dirnames, filenames in os.walk(repo_root):
            dirnames[:] = [
                dirname
                for dirname in dirnames
                if dirname not in _EXCLUDED_REPO_DIRS and not dirname.startswith('.tmp_test')
            ]
            current_path = Path(current_root)
            for filename in filenames:
                path = current_path / filename
                relative = path.relative_to(repo_root)
                if any(part in _EXCLUDED_REPO_DIRS for part in relative.parts[:-1]):
                    continue
                top_level = relative.parts[0] if len(relative.parts) > 1 else '(root)'
                top_level_counts[top_level] += 1
                total_files += 1

        branch_result = SystemOperations._run_command(
            ['git', '-C', str(repo_root), 'branch', '--show-current'],
            cwd=repo_root,
            timeout=10,
        )
        status_result = SystemOperations._run_command(
            ['git', '-C', str(repo_root), 'status', '--short'],
            cwd=repo_root,
            timeout=10,
        )
        modified_files = [line for line in status_result['stdout'].splitlines() if line.strip()]
        return {
            'root': str(repo_root),
            'branch': branch_result['stdout'].strip() or 'unknown',
            'git_status': 'dirty' if modified_files else 'clean',
            'modified_files': len(modified_files),
            'modified_preview': modified_files[:10],
            'total_files': total_files,
            'top_level_counts': dict(sorted(top_level_counts.items())),
        }

    @staticmethod
    def search_repo(repo_root: Path, pattern: str, max_hits: int = 25) -> dict[str, Any]:
        cleaned = pattern.strip()
        if not cleaned:
            raise ValueError('A search pattern is required')
        repo_root = repo_root.resolve()
        rg_path = shutil.which('rg')
        hits: list[str]
        if rg_path:
            command = [
                rg_path,
                '-n',
                '--hidden',
                '--glob',
                '!node_modules/**',
                '--glob',
                '!dist/**',
                '--glob',
                '!target/**',
                '--glob',
                '!build/**',
                '--glob',
                '!waseem_brain.egg-info/**',
                '--glob',
                '!.git/**',
                cleaned,
                '.',
            ]
            result = SystemOperations._run_command(command, cwd=repo_root, timeout=20)
            output = result['stdout'] if result['stdout'].strip() else result['stderr']
            hits = [line for line in output.splitlines() if line.strip()][:max_hits]
        else:
            hits = []
            lowered = cleaned.lower()
            for current_root, dirnames, filenames in os.walk(repo_root):
                dirnames[:] = [
                    dirname
                    for dirname in dirnames
                    if dirname not in _EXCLUDED_REPO_DIRS and not dirname.startswith('.tmp_test')
                ]
                current_path = Path(current_root)
                for filename in filenames:
                    path = current_path / filename
                    try:
                        text = path.read_text(encoding='utf-8')
                    except (OSError, UnicodeDecodeError):
                        continue
                    for line_number, line in enumerate(text.splitlines(), start=1):
                        if lowered in line.lower():
                            hits.append(f"{path.relative_to(repo_root)}:{line_number}: {line.strip()}")
                            if len(hits) >= max_hits:
                                break
                    if len(hits) >= max_hits:
                        break
                if len(hits) >= max_hits:
                    break
        return {
            'pattern': cleaned,
            'match_count': len(hits),
            'matches': hits,
        }

    @staticmethod
    @staticmethod
    def read_workspace_file(
        repo_root: Path,
        relative_path: str,
        *,
        start_line: int = 1,
        end_line: int | None = None,
        max_lines: int = 160,
    ) -> dict[str, Any]:
        cleaned = relative_path.strip().replace('\\', '/')
        if not cleaned:
            raise ValueError('A file path is required')
        repo_root = repo_root.resolve()
        target = (repo_root / cleaned).resolve()
        try:
            target.relative_to(repo_root)
        except ValueError as exc:
            raise ValueError('File path must stay inside the workspace') from exc
        if not target.exists() or not target.is_file():
            raise ValueError(f'Workspace file not found: {cleaned}')

        raw_start = start_line if start_line > 0 else 1
        if end_line is not None and end_line < raw_start:
            raise ValueError('end_line must be greater than or equal to start_line')

        try:
            lines = target.read_text(encoding='utf-8', errors='replace').splitlines()
        except OSError as exc:
            raise ValueError(f'Unable to read workspace file: {cleaned}') from exc

        total_lines = len(lines)
        start_index = max(raw_start - 1, 0)
        if end_line is None:
            stop_index = min(start_index + max_lines, total_lines)
        else:
            stop_index = min(end_line, total_lines, start_index + max_lines)
        excerpt_lines = lines[start_index:stop_index]
        numbered_excerpt = [
            f"{index}: {line}"
            for index, line in enumerate(excerpt_lines, start=start_index + 1)
        ]
        return {
            'path': str(target.relative_to(repo_root)).replace('\\', '/'),
            'start_line': start_index + 1 if total_lines else 0,
            'end_line': start_index + len(excerpt_lines),
            'total_lines': total_lines,
            'excerpt': numbered_excerpt,
            'message': 'Workspace file excerpt loaded.',
        }

    @staticmethod
    def audit_log_tail(path: Path, line_count: int = 20) -> dict[str, Any]:
        if line_count <= 0:
            line_count = 20
        if not path.exists():
            return {
                'path': str(path),
                'line_count': 0,
                'lines': [],
                'message': 'Audit log has not been created yet.',
            }
        lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
        tail = lines[-line_count:]
        return {
            'path': str(path),
            'line_count': len(tail),
            'lines': tail,
            'message': 'Audit log tail loaded.',
        }

    @staticmethod
    def runtime_daemon_status(repo_root: Path) -> RuntimeDaemonStatus:
        from scripts.runtime_client import DEFAULT_HOST, DEFAULT_PORT, is_runtime_daemon_running, load_runtime_daemon_state

        state = load_runtime_daemon_state() or {}
        running = is_runtime_daemon_running()
        host = str(state.get('host', DEFAULT_HOST))
        raw_port = state.get('port', DEFAULT_PORT)
        try:
            port = int(raw_port)
        except (TypeError, ValueError):
            port = DEFAULT_PORT
        raw_pid = state.get('pid', 0)
        try:
            pid = int(raw_pid)
        except (TypeError, ValueError):
            pid = 0
        log_path = str(state.get('log_path', repo_root / 'tmp' / 'runtime-daemon' / 'runtime-daemon.log'))
        message = (
            f'Runtime daemon is running on {host}:{port} with pid {pid}.'
            if running
            else 'Runtime daemon is not running.'
        )
        return {
            'running': running,
            'host': host,
            'port': port,
            'pid': pid,
            'log_path': log_path,
            'message': message,
        }

    @staticmethod
    def preview_runtime_daemon_command(repo_root: Path, operation: str) -> str:
        return ' '.join(SystemOperations._runtime_daemon_command(repo_root, operation))

    @staticmethod
    def manage_runtime_daemon(repo_root: Path, operation: str) -> dict[str, Any]:
        normalized = operation.strip().lower()
        if normalized not in {'start', 'stop', 'restart'}:
            raise ValueError("Runtime daemon operation must be start, stop, or restart")
        results: list[CommandResult] = []
        if normalized == 'restart':
            results.append(
                SystemOperations._run_command(
                    SystemOperations._runtime_daemon_command(repo_root, 'stop'),
                    cwd=repo_root,
                    timeout=30,
                )
            )
            results.append(
                SystemOperations._run_command(
                    SystemOperations._runtime_daemon_command(repo_root, 'start'),
                    cwd=repo_root,
                    timeout=45,
                )
            )
        else:
            results.append(
                SystemOperations._run_command(
                    SystemOperations._runtime_daemon_command(repo_root, normalized),
                    cwd=repo_root,
                    timeout=45,
                )
            )
        failed = next((result for result in results if result['status'] != 'pass'), None)
        return {
            'operation': normalized,
            'status': 'pass' if failed is None else 'fail',
            'message': (
                f'Runtime daemon {normalized} completed successfully.'
                if failed is None
                else f'Runtime daemon {normalized} failed.'
            ),
            'results': results,
            'state': SystemOperations.runtime_daemon_status(repo_root),
        }

    @staticmethod
    def run_project_command(repo_root: Path, target: str) -> dict[str, Any]:
        mapping = {
            'fast': ['test'],
            'full': ['run', 'verify:project'],
            'docker-smoke': ['run', 'docker:smoke'],
        }
        if target not in mapping:
            raise ValueError(f'Unknown project command target: {target}')
        result = SystemOperations._run_command(
            SystemOperations._pnpm_command(mapping[target]),
            cwd=repo_root,
            timeout=600 if target != 'fast' else 300,
        )
        return {
            'target': target,
            'status': result['status'],
            'message': f"Project command {target} {result['status']}.",
            'result': result,
        }

    @staticmethod
    def run_in_sandbox(command: str, timeout: int = 10) -> str:
        try:
            result = subprocess.run(
                command,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={},
            )
            return result.stdout if result.stdout else result.stderr
        except subprocess.TimeoutExpired:
            return 'Sandbox Execution Timeout: Process terminated for safety.'
        except Exception as exc:
            return f'Sandbox Error: {exc}'

    @staticmethod
    def _runtime_daemon_command(repo_root: Path, operation: str) -> list[str]:
        return [sys.executable, str(repo_root / 'scripts' / 'manage_runtime_daemon.py'), operation]

    @staticmethod
    def _pnpm_command(args: list[str]) -> list[str]:
        if os.name == 'nt':
            return ['cmd', '/d', '/c', 'pnpm', *args]
        return ['pnpm', *args]

    @staticmethod
    def _run_command(
        command: list[str],
        *,
        cwd: Path,
        timeout: int,
        env: Optional[dict[str, str]] = None,
    ) -> CommandResult:
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout,
                check=False,
                env=env,
            )
            stdout = completed.stdout or ''
            stderr = completed.stderr or ''
            exit_code = completed.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ''
            stderr = ((exc.stderr or '') + f'\nTimed out after {timeout} seconds').strip()
            exit_code = -1
        duration = round(time.perf_counter() - started, 3)
        output = '\n'.join(line for line in [stdout.strip(), stderr.strip()] if line)
        output_tail = '\n'.join(output.splitlines()[-40:])
        return {
            'status': 'pass' if exit_code == 0 else 'fail',
            'exit_code': exit_code,
            'duration_sec': duration,
            'command': ' '.join(command),
            'stdout': stdout.strip(),
            'stderr': stderr.strip(),
            'output_tail': output_tail,
        }
