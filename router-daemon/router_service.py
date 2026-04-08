"""Deprecated experimental Python router shim.

This file is preserved only as a historical artifact.
The supported runtime contract uses:
- local artifact routing by default, or
- the optional Rust gRPC router daemon when acceleration is desired.

Do not use this module as a production router implementation.
"""

from __future__ import annotations


def main() -> None:
    raise SystemExit(
        "router-daemon/router_service.py is deprecated. Use local artifact routing or the optional Rust router daemon instead."
    )


if __name__ == "__main__":
    main()
