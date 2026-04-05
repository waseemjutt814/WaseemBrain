from __future__ import annotations

from .memory.sqlite_store import SqliteMetaStore
from .types import Result, SessionId


class SessionManager:
    def __init__(self, sqlite_store: SqliteMetaStore) -> None:
        self._sqlite_store = sqlite_store

    def start(self, session_id: SessionId) -> Result[None, str]:
        return self._sqlite_store.create_session(session_id)

    def end(self, session_id: SessionId) -> Result[None, str]:
        return self._sqlite_store.mark_session_ended(session_id)
