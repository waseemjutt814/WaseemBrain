from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "tmp" / "router-daemon"
STATE_PATH = STATE_DIR / "state.json"
LOG_PATH = STATE_DIR / "router-daemon.log"
PREFERRED_TOOLCHAIN_ROOT = Path(r"D:\rustup\toolchains\stable-x86_64-pc-windows-msvc\bin")
PREFERRED_CARGO_HOME = Path(r"D:\cargo-home")
PREFERRED_RUSTUP_HOME = Path(r"D:\rustup")


def _binary_path(root: Path) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    return root / "target" / "debug" / f"router-daemon{suffix}"


def _preferred_cargo() -> str:
    candidates = []
    if os.name == "nt":
        candidates.append(str(PREFERRED_TOOLCHAIN_ROOT / "cargo.exe"))
    cargo = shutil.which("cargo")
    if cargo:
        candidates.append(cargo)
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise RuntimeError("cargo was not found; install Rust or add cargo to PATH")


def _toolchain_env() -> dict[str, str]:
    env = dict(os.environ)
    if os.name != "nt":
        return env
    if PREFERRED_TOOLCHAIN_ROOT.exists():
        env["PATH"] = f"{PREFERRED_TOOLCHAIN_ROOT}{os.pathsep}{env.get('PATH', '')}"
        env["RUSTC"] = str(PREFERRED_TOOLCHAIN_ROOT / "rustc.exe")
    if PREFERRED_CARGO_HOME.exists():
        env["CARGO_HOME"] = str(PREFERRED_CARGO_HOME)
    if PREFERRED_RUSTUP_HOME.exists():
        env["RUSTUP_HOME"] = str(PREFERRED_RUSTUP_HOME)
    return env


def _load_state() -> dict[str, Any] | None:
    if not STATE_PATH.exists():
        return None
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


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


def _build_router(cargo_path: str, root: Path) -> None:
    subprocess.run(
        [cargo_path, "build", "--manifest-path", str(root / "router-daemon" / "Cargo.toml")],
        cwd=root,
        env=_toolchain_env(),
        check=True,
    )


def start_router(root: Path, port: int, build: bool) -> None:
    existing = _load_state()
    if existing is not None and _is_running(int(existing["pid"])):
        print(f"Router daemon already running on port {existing['port']} with pid {existing['pid']}")
        print(f"Log: {existing['log_path']}")
        return
    _remove_state()

    cargo_path = _preferred_cargo()
    if build:
        _build_router(cargo_path, root)

    binary_path = _binary_path(root)
    if not binary_path.exists():
        raise RuntimeError(f"router daemon binary not found at {binary_path}")

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("ab") as log_file:
        env = {
            **_toolchain_env(),
            "GRPC_PORT": str(port),
            "ROUTER_MODEL_PATH": str(root / "experts" / "router.json"),
        }
        popen_kwargs: dict[str, Any] = {
            "cwd": str(root),
            "env": env,
            "stdout": log_file,
            "stderr": subprocess.STDOUT,
            "stdin": subprocess.DEVNULL,
        }
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        else:
            popen_kwargs["start_new_session"] = True

        process = subprocess.Popen([str(binary_path)], **popen_kwargs)

    time.sleep(1.0)
    if not _is_running(process.pid):
        tail = LOG_PATH.read_text(encoding="utf-8", errors="replace")[-4000:]
        raise RuntimeError(f"router daemon failed to start\n{tail}")

    _write_state(
        {
            "pid": process.pid,
            "port": port,
            "binary_path": str(binary_path),
            "log_path": str(LOG_PATH),
            "started_at": time.time(),
        }
    )
    print(f"Started router daemon on port {port} with pid {process.pid}")
    print(f"Log: {LOG_PATH}")


def stop_router() -> None:
    state = _load_state()
    if state is None:
        print("Router daemon is not running")
        return
    pid = int(state["pid"])
    if _is_running(pid):
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False)
        else:
            os.kill(pid, signal.SIGTERM)
    _remove_state()
    print(f"Stopped router daemon pid {pid}")


def status_router() -> None:
    state = _load_state()
    if state is None:
        print("Router daemon is not running")
        return
    pid = int(state["pid"])
    if _is_running(pid):
        print(f"Router daemon is running on port {state['port']} with pid {pid}")
        print(f"Log: {state['log_path']}")
        return
    _remove_state()
    print("Router daemon state was stale and has been cleared")


def main() -> None:
    parser = argparse.ArgumentParser(description="Start, stop, or inspect the local router daemon.")
    parser.add_argument("command", choices=("start", "stop", "status"))
    parser.add_argument("--port", type=int, default=50051)
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()

    if args.command == "start":
        start_router(ROOT, args.port, build=not args.skip_build)
        return
    if args.command == "stop":
        stop_router()
        return
    status_router()


if __name__ == "__main__":
    main()
