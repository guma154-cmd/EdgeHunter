"""Minimal OddsHistorian bootstrap for STORY-01-002."""

from __future__ import annotations

from ..database.schema import ensure_schema


class OddsHistorian:
    """Bootstrap the SQLite schema required by the historical odds layer."""

    def __init__(self, db_path: str = "edge_hunter.db") -> None:
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        if not ensure_schema(self.db_path):
            raise RuntimeError(f"failed to initialize OddsHistorian schema at {self.db_path}")
