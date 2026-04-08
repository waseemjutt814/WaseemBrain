from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = ROOT / 'docker-compose.yml'
SMOKE_PROJECT = 'waseem-brain-smoke'
SMOKE_INTERFACE_PORT = '38080'
SMOKE_INTERFACE_URL = f'http://127.0.0.1:{SMOKE_INTERFACE_PORT}'
AUDIT_LOG_PATH = ROOT / 'logs' / 'assistant-actions.jsonl'


def _run_command(
    command: list[str],
    *,
    cwd: Path,
    timeout: int,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
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
    output = '\n'.join(part for part in [stdout.strip(), stderr.strip()] if part)
    return {
        'command': ' '.join(command),
        'exit_code': exit_code,
        'status': 'pass' if exit_code == 0 else 'fail',
        'duration_sec': duration,
        'stdout': stdout.strip(),
        'stderr': stderr.strip(),
        'output_tail': '\n'.join(output.splitlines()[-40:]),
    }


def _docker_env() -> dict[str, str]:
    return {
        **os.environ,
        'INTERFACE_PORT': SMOKE_INTERFACE_PORT,
    }


def _compose_command(*args: str) -> list[str]:
    return ['docker', 'compose', '-p', SMOKE_PROJECT, *args]


def _service_status_snapshot(env: dict[str, str]) -> list[dict[str, Any]]:
    result = _run_command(_compose_command('ps', '--format', 'json'), cwd=ROOT, timeout=60, env=env)
    if result['status'] != 'pass':
        return []
    stdout = str(result['stdout']).strip()
    if not stdout:
        return []
    try:
        payload = json.loads(stdout)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            return [payload]
    except json.JSONDecodeError:
        entries: list[dict[str, Any]] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                entries.append(payload)
        return entries
    return []


def _count_audit_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding='utf-8', errors='replace').splitlines() if line.strip())


def _fetch_json(url: str, timeout: float = 3.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


def _wait_for_http(url: str, *, timeout_sec: float) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    last_error = 'not attempted'
    while time.time() < deadline:
        try:
            payload = _fetch_json(url)
            return {'status': 'pass', 'payload': payload}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            last_error = str(exc)
            time.sleep(1.0)
    return {'status': 'fail', 'error': last_error}


def _assistant_exec_script() -> str:
    return (
        "const WebSocket = require('ws');"
        "const socket = new WebSocket('ws://127.0.0.1:8080/ws/assistant');"
        "const timer = setTimeout(() => { console.error('assistant websocket timeout'); process.exit(2); }, 12000);"
        "socket.on('open', () => socket.send(JSON.stringify({ type: 'action.confirm', session_id: 'docker-smoke', action_id: 'system.runtime.status', inputs: {}, confirmed: true })) );"
        "socket.on('message', (payload) => { const event = JSON.parse(String(payload)); if (event.type === 'message.done') { clearTimeout(timer); socket.close(); process.exit(0); } if (event.type === 'error') { clearTimeout(timer); console.error(event.content || 'assistant websocket error'); socket.close(); process.exit(1); } });"
        "socket.on('error', (error) => { clearTimeout(timer); console.error(String(error)); process.exit(1); });"
    )


def _assistant_ws_probe(env: dict[str, str]) -> dict[str, Any]:
    return _run_command(
        _compose_command('exec', '-T', 'interface', 'node', '-e', _assistant_exec_script()),
        cwd=ROOT,
        timeout=90,
        env=env,
    )


def run_docker_smoke(*, require_docker: bool = False) -> dict[str, Any]:
    if not COMPOSE_PATH.exists():
        return {'status': 'fail', 'reason': f'Missing compose file at {COMPOSE_PATH}'}

    docker_cli = shutil.which('docker')
    if not docker_cli:
        status = 'fail' if require_docker else 'skipped'
        return {'status': status, 'reason': 'docker CLI is not available on PATH'}

    env = _docker_env()
    compose_version = _run_command(_compose_command('version'), cwd=ROOT, timeout=30, env=env)
    if compose_version['status'] != 'pass':
        status = 'fail' if require_docker else 'skipped'
        return {
            'status': status,
            'reason': 'docker compose is unavailable or the Docker daemon is unreachable',
            'detail': compose_version,
        }

    steps: list[dict[str, Any]] = []
    services_result = _run_command(_compose_command('config', '--services'), cwd=ROOT, timeout=30, env=env)
    if services_result['status'] != 'pass':
        return {
            'status': 'fail',
            'reason': 'docker compose service resolution failed',
            'steps': [services_result],
        }
    services = [line.strip() for line in str(services_result['stdout']).splitlines() if line.strip()]

    before_lines = _count_audit_lines(AUDIT_LOG_PATH)
    started = False
    try:
        up_result = _run_command(_compose_command('up', '--build', '-d'), cwd=ROOT, timeout=900, env=env)
        steps.append({'name': 'compose-up', **up_result})
        if up_result['status'] != 'pass':
            return {
                'status': 'fail',
                'reason': 'docker compose up failed',
                'services': services,
                'steps': steps,
            }
        started = True

        health_result = _wait_for_http(f'{SMOKE_INTERFACE_URL}/health', timeout_sec=120.0)
        steps.append({'name': 'interface-health', **health_result})
        if health_result['status'] != 'pass':
            return {
                'status': 'fail',
                'reason': 'interface health endpoint did not become ready',
                'services': services,
                'steps': steps,
            }

        catalog_result = _wait_for_http(f'{SMOKE_INTERFACE_URL}/api/catalog', timeout_sec=30.0)
        steps.append({'name': 'assistant-catalog', **catalog_result})
        if catalog_result['status'] != 'pass':
            return {
                'status': 'fail',
                'reason': 'assistant catalog endpoint did not respond cleanly',
                'services': services,
                'steps': steps,
            }

        actions_result = _wait_for_http(f'{SMOKE_INTERFACE_URL}/api/actions', timeout_sec=30.0)
        steps.append({'name': 'assistant-actions', **actions_result})
        if actions_result['status'] != 'pass':
            return {
                'status': 'fail',
                'reason': 'assistant actions endpoint did not respond cleanly',
                'services': services,
                'steps': steps,
            }

        ws_result = _assistant_ws_probe(env)
        steps.append({'name': 'assistant-websocket', **ws_result})
        if ws_result['status'] != 'pass':
            return {
                'status': 'fail',
                'reason': 'assistant websocket probe failed',
                'services': services,
                'steps': steps,
            }

        after_action_lines = _count_audit_lines(AUDIT_LOG_PATH)
        if after_action_lines <= before_lines:
            return {
                'status': 'fail',
                'reason': 'assistant action did not persist an audit entry into the shared logs volume',
                'services': services,
                'steps': steps,
                'audit_lines_before': before_lines,
                'audit_lines_after_action': after_action_lines,
            }

        restart_result = _run_command(_compose_command('restart', 'brain-runtime'), cwd=ROOT, timeout=240, env=env)
        steps.append({'name': 'runtime-restart', **restart_result})
        if restart_result['status'] != 'pass':
            return {
                'status': 'fail',
                'reason': 'brain-runtime restart failed during smoke verification',
                'services': services,
                'steps': steps,
            }

        post_restart_health = _wait_for_http(f'{SMOKE_INTERFACE_URL}/health', timeout_sec=120.0)
        steps.append({'name': 'post-restart-health', **post_restart_health})
        if post_restart_health['status'] != 'pass':
            return {
                'status': 'fail',
                'reason': 'interface did not recover after restarting the runtime service',
                'services': services,
                'steps': steps,
            }

        after_restart_lines = _count_audit_lines(AUDIT_LOG_PATH)
        if after_restart_lines < after_action_lines:
            return {
                'status': 'fail',
                'reason': 'shared audit log state did not persist across runtime restart',
                'services': services,
                'steps': steps,
                'audit_lines_before': before_lines,
                'audit_lines_after_action': after_action_lines,
                'audit_lines_after_restart': after_restart_lines,
            }

        return {
            'status': 'pass',
            'reason': 'docker compose booted cleanly, the assistant surface responded, and shared state persisted across runtime restart',
            'project': SMOKE_PROJECT,
            'interface_url': SMOKE_INTERFACE_URL,
            'services': services,
            'service_status': _service_status_snapshot(env),
            'audit_lines_before': before_lines,
            'audit_lines_after_action': after_action_lines,
            'audit_lines_after_restart': after_restart_lines,
            'steps': steps,
        }
    finally:
        if started:
            _run_command(_compose_command('down', '--remove-orphans'), cwd=ROOT, timeout=240, env=env)


def main() -> None:
    parser = argparse.ArgumentParser(description='Run the Waseem Brain Docker smoke verification.')
    parser.add_argument('--require-docker', action='store_true', help='Fail when Docker is unavailable instead of returning a skipped status.')
    args = parser.parse_args()

    result = run_docker_smoke(require_docker=args.require_docker)
    print(json.dumps(result, indent=2))
    if result['status'] == 'fail':
        raise SystemExit(1)
    if args.require_docker and result['status'] == 'skipped':
        raise SystemExit(1)


if __name__ == '__main__':
    main()