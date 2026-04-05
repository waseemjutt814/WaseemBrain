from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.runtime_client import DEFAULT_HOST, DEFAULT_PORT, LOG_PATH, STATE_DIR, STATE_PATH


def _load_state() -> dict[str, Any] | None:
    if not STATE_PATH.exists():
        return None
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_state(payload: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _remove_state() -> None:
    STATE_PATH.unlink(missing_ok=True)


def _is_running(pid: int) -> bool:
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                check=False,
            )
            return str(pid) in result.stdout
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _command_line_for_pid(pid: int) -> str:
    if pid <= 0:
        return ""
    try:
        if os.name == "nt":
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    (
                        f"$p = Get-CimInstance Win32_Process -Filter \"ProcessId = {pid}\"; "
                        "if ($p) { $p.CommandLine }"
                    ),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.stdout.strip()
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "args="],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip()
    except OSError:
        return ""


def _pid_matches_runtime_daemon(pid: int) -> bool:
    command_line = _command_line_for_pid(pid).lower()
    return "runtime_daemon.py" in command_line


def _find_listener_pid(port: int) -> int | None:
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"],
                capture_output=True,
                text=True,
                check=False,
            )
            for line in result.stdout.splitlines():
                normalized = " ".join(line.split())
                if "LISTENING" not in normalized:
                    continue
                if f":{port} " not in normalized and not normalized.endswith(f":{port}"):
                    continue
                parts = normalized.split(" ")
                if len(parts) >= 5:
                    try:
                        return int(parts[-1])
                    except ValueError:
                        continue
            return None
        result = subprocess.run(
            ["ss", "-ltnp"],
            capture_output=True,
            text=True,
            check=False,
        )
        pattern = re.compile(rf":{port}\s+.*pid=(\d+),")
        for line in result.stdout.splitlines():
            match = pattern.search(line)
            if match:
                return int(match.group(1))
    except OSError:
        return None
    return None


def _listener_is_ready(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def _adopt_running_listener(host: str, port: int) -> dict[str, Any] | None:
    pid = _find_listener_pid(port)
    if pid is None or not _is_running(pid) or not _pid_matches_runtime_daemon(pid):
        return None
    payload = {
        "pid": pid,
        "host": host,
        "port": port,
        "log_path": str(LOG_PATH),
        "started_at": time.time(),
    }
    _write_state(payload)
    return payload


async def _send_shutdown(host: str, port: int) -> bool:
    try:
        reader, writer = await asyncio.open_connection(host, port)
    except OSError:
        return False
    try:
        writer.write(
            (
                json.dumps({"id": "runtime-shutdown", "command": "shutdown", "payload": {}}) + "\n"
            ).encode("utf-8")
        )
        await writer.drain()
        await asyncio.wait_for(reader.readline(), timeout=5.0)
        return True
    except (OSError, asyncio.TimeoutError):
        return False
    finally:
        writer.close()
        await writer.wait_closed()


def start_runtime(host: str, port: int) -> None:
    existing = _load_state()
    if existing is not None and _is_running(int(existing.get("pid", 0))):
        print(
            f"Runtime daemon already running on {existing.get('host', host)}:{existing.get('port', port)} "
            f"with pid {existing.get('pid')}"
        )
        print(f"Log: {existing.get('log_path', LOG_PATH)}")
        return
    adopted = _adopt_running_listener(host, port)
    if adopted is not None:
        print(
            f"Runtime daemon already running on {adopted.get('host', host)}:{adopted.get('port', port)} "
            f"with pid {adopted.get('pid')}"
        )
        print(f"Log: {adopted.get('log_path', LOG_PATH)}")
        return
    _remove_state()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("ab") as log_file:
        popen_kwargs: dict[str, Any] = {
            "cwd": str(ROOT),
            "env": {
                **os.environ,
                "PYTHONUNBUFFERED": "1",
                "RUNTIME_DAEMON_HOST": host,
                "RUNTIME_DAEMON_PORT": str(port),
            },
            "stdout": log_file,
            "stderr": subprocess.STDOUT,
            "stdin": subprocess.DEVNULL,
        }
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        else:
            popen_kwargs["start_new_session"] = True
        process = subprocess.Popen(
            [sys.executable, str(ROOT / "scripts" / "runtime_daemon.py"), host, str(port)],
            **popen_kwargs,
        )
    deadline = time.time() + 12.0
    ready = False
    while time.time() < deadline:
        if not _is_running(process.pid):
            break
        listener_pid = _find_listener_pid(port)
        if listener_pid == process.pid and _listener_is_ready(host, port):
            ready = True
            break
        time.sleep(0.25)
    if not ready:
        tail = LOG_PATH.read_text(encoding="utf-8", errors="replace")[-4000:]
        raise RuntimeError(f"runtime daemon failed to start cleanly\n{tail}")
    _write_state(
        {
            "pid": process.pid,
            "host": host,
            "port": port,
            "log_path": str(LOG_PATH),
            "started_at": time.time(),
        }
    )
    print(f"Started runtime daemon on {host}:{port} with pid {process.pid}")
    print(f"Log: {LOG_PATH}")


def stop_runtime() -> None:
    state = _load_state()
    if state is None or not _is_running(int(state.get("pid", 0))):
        state = _adopt_running_listener(DEFAULT_HOST, DEFAULT_PORT)
    if state is None:
        print("Runtime daemon is not running")
        return
    pid = int(state.get("pid", 0))
    host = str(state.get("host", DEFAULT_HOST))
    port = int(state.get("port", DEFAULT_PORT))
    if _is_running(pid):
        shutdown_ok = asyncio.run(_send_shutdown(host, port))
        if not shutdown_ok:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False)
            else:
                os.kill(pid, signal.SIGTERM)
    _remove_state()
    print(f"Stopped runtime daemon pid {pid}")


def status_runtime() -> None:
    state = _load_state()
    if state is None or not _is_running(int(state.get("pid", 0))):
        state = _adopt_running_listener(DEFAULT_HOST, DEFAULT_PORT)
    if state is None:
        print("Runtime daemon is not running")
        return
    pid = int(state.get("pid", 0))
    if _is_running(pid):
        print(
            f"Runtime daemon is running on {state.get('host', DEFAULT_HOST)}:{state.get('port', DEFAULT_PORT)} "
            f"with pid {pid}"
        )
        print(f"Log: {state.get('log_path', LOG_PATH)}")
        return
    _remove_state()
    print("Runtime daemon state was stale and has been cleared")


def main() -> None:
    parser = argparse.ArgumentParser(description="Start, stop, or inspect the Python runtime daemon.")
    parser.add_argument("command", choices=("start", "stop", "status"))
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    if args.command == "start":
        start_runtime(args.host, args.port)
        return
    if args.command == "stop":
        stop_runtime()
        return
    status_runtime()


if __name__ == "__main__":
    main()
