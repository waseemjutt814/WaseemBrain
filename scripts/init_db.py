from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.config import load_settings
from brain.memory.sqlite_store import SqliteMetaStore


def main() -> None:
    settings = load_settings()
    store = SqliteMetaStore(settings.sqlite_dir)
    print(f"Initialized SQLite metadata store at {store._db_path}")


if __name__ == "__main__":
    main()
