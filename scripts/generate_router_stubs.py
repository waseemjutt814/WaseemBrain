from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    proto_dir = root / "router-daemon" / "proto"
    output_dir = root / "brain" / "router" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{proto_dir}",
        f"--python_out={output_dir}",
        f"--grpc_python_out={output_dir}",
        str(proto_dir / "router.proto"),
    ]
    subprocess.run(command, check=True)
    grpc_file = output_dir / "router_pb2_grpc.py"
    grpc_text = grpc_file.read_text(encoding="utf-8")
    grpc_text = grpc_text.replace(
        "import router_pb2 as router__pb2",
        "from . import router_pb2 as router__pb2",
    )
    grpc_file.write_text(grpc_text, encoding="utf-8")
    (output_dir / "__init__.py").write_text(
        "from __future__ import annotations\n\n"
        "from . import router_pb2, router_pb2_grpc\n\n"
        "__all__ = ['router_pb2', 'router_pb2_grpc']\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
